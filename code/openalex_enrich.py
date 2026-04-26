"""OpenAlex enrichment for merged Scopus + ACM DL search results.

Task 2.3: Merges the two raw search CSVs, queries OpenAlex for every
unique DOI to capture cross-database metadata and abstracts, flags
IC3 disagreements and preprints, and writes an enriched CSV.

Usage:
    python code/openalex_enrich.py
    python code/openalex_enrich.py --scopus path/to/scopus.csv --acm path/to/acm.csv
    python code/openalex_enrich.py --resume

Consumes:
    artifacts/search/raw/scopus_YYYYMMDD.csv
    artifacts/search/raw/acm_YYYYMMDD.csv
    .env  OPENALEX_EMAIL (optional, for polite pool)

Produces:
    artifacts/search/enriched/merged_openalex.csv
    artifacts/search/enriched/merged_openalex.csv.meta.json
    Appends one row to decision_register.csv
"""

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

# ---------------------------------------------------------------------------
# Resolve project root and configure stdout
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, str(ROOT))
from code.utils import write_with_meta

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RAW_DIR = ROOT / "artifacts" / "search" / "raw"
OUTPUT_DIR = ROOT / "artifacts" / "search" / "enriched"
CHECKPOINT_PATH = OUTPUT_DIR / ".openalex_checkpoint.json"

# OpenAlex API
OPENALEX_WORKS_URL = "https://api.openalex.org/works"
BATCH_SIZE = 50             # DOIs per batch request
REQUEST_DELAY = 0.1         # 100ms between batch requests (polite pool allows 10/s)
REQUEST_TIMEOUT = 30        # Seconds per request
MAX_RETRIES = 3
BACKOFF_BASE = 2
CHECKPOINT_INTERVAL = 10    # Save checkpoint every N batches


# ---------------------------------------------------------------------------
# Email Loading
# ---------------------------------------------------------------------------

def load_email(cli_override: str | None = None) -> str | None:
    """Load OpenAlex polite-pool email from CLI arg, env var, or .env file.

    Returns None if not found (script will use anonymous pool — slower).
    """
    if cli_override:
        return cli_override

    email = os.environ.get("OPENALEX_EMAIL")
    if email:
        return email

    env_path = ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line.startswith("OPENALEX_EMAIL=") and len(line) > len("OPENALEX_EMAIL="):
                return line.split("=", 1)[1].strip()

    return None


# ---------------------------------------------------------------------------
# Phase 1: Load & Merge
# ---------------------------------------------------------------------------

def discover_latest_csv(prefix: str) -> Path | None:
    """Find the most recent CSV matching a prefix in the raw directory.

    Looks for files like scopus_YYYYMMDD.csv or acm_YYYYMMDD.csv.
    """
    matches = sorted(RAW_DIR.glob(f"{prefix}_*.csv"), reverse=True)
    # Filter out .meta.json files
    matches = [m for m in matches if not m.name.endswith(".meta.json")]
    return matches[0] if matches else None


def load_and_merge(scopus_path: Path, acm_path: Path) -> pd.DataFrame:
    """Load both raw CSVs and concatenate into a single DataFrame.

    Preserves the search_path column to track provenance.
    """
    print("Phase 1: Loading raw CSVs...")

    # Load Scopus
    if not scopus_path.exists():
        print(f"  ERROR: Scopus CSV not found: {scopus_path}", file=sys.stderr)
        sys.exit(1)
    scopus = pd.read_csv(scopus_path, dtype=str)
    print(f"  Scopus: {len(scopus)} rows loaded from {scopus_path.name}")

    # Load ACM DL
    if not acm_path.exists():
        print(f"  ERROR: ACM DL CSV not found: {acm_path}", file=sys.stderr)
        sys.exit(1)
    acm = pd.read_csv(acm_path, dtype=str)
    print(f"  ACM DL: {len(acm)} rows loaded from {acm_path.name}")

    # Concatenate
    combined = pd.concat([scopus, acm], ignore_index=True)
    print(f"  Combined: {len(combined)} rows")

    return combined


def extract_unique_dois(df: pd.DataFrame) -> list[str]:
    """Extract unique, non-null DOIs from the combined DataFrame.

    Normalises DOIs to lowercase for consistent lookup.
    """
    dois = df["doi"].dropna().str.strip().str.lower().unique().tolist()
    null_count = df["doi"].isna().sum()
    print(f"  Unique DOIs: {len(dois)} ({null_count} rows have no DOI)")
    return dois


# ---------------------------------------------------------------------------
# Phase 2: OpenAlex Batch Lookup
# ---------------------------------------------------------------------------

def _openalex_batch_request(
    dois: list[str],
    email: str | None,
) -> list[dict]:
    """Execute a single OpenAlex batch request for a list of DOIs.

    Uses the filter API: /works?filter=doi:X|Y|Z&per_page=50
    Returns list of work dicts from the response.
    Implements retry with exponential backoff.
    """
    # Build the pipe-separated DOI filter
    doi_filter = "|".join(f"https://doi.org/{d}" for d in dois)
    params = {
        "filter": f"doi:{doi_filter}",
        "per_page": len(dois),
        "select": (
            "doi,title,type,is_paratext,is_retracted,"
            "cited_by_count,open_access,"
            "primary_location,abstract_inverted_index"
        ),
    }
    if email:
        params["mailto"] = email

    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(
                OPENALEX_WORKS_URL,
                params=params,
                timeout=REQUEST_TIMEOUT,
            )

            if resp.status_code == 200:
                data = resp.json()
                return data.get("results", [])

            if resp.status_code == 429:
                wait = BACKOFF_BASE ** attempt
                print(f"    Rate limited (429). Waiting {wait}s (retry {attempt + 1}/{MAX_RETRIES})...")
                time.sleep(wait)
                continue

            if resp.status_code >= 500:
                wait = 5
                print(f"    Server error ({resp.status_code}). Waiting {wait}s (retry {attempt + 1}/{MAX_RETRIES})...")
                time.sleep(wait)
                continue

            # Other errors
            print(f"    Unexpected HTTP {resp.status_code}: {resp.text[:200]}")
            return []

        except requests.exceptions.Timeout:
            wait = BACKOFF_BASE ** attempt
            print(f"    Timeout. Waiting {wait}s (retry {attempt + 1}/{MAX_RETRIES})...")
            time.sleep(wait)
            continue

        except requests.exceptions.ConnectionError as e:
            wait = BACKOFF_BASE ** attempt
            print(f"    Connection error. Waiting {wait}s (retry {attempt + 1}/{MAX_RETRIES})...")
            time.sleep(wait)
            continue

    print(f"    All retries exhausted for batch of {len(dois)} DOIs")
    return []


def _parse_openalex_work(work: dict) -> dict:
    """Parse a single OpenAlex work dict into enrichment fields.

    Extracts the fields specified in the design document §4.3.
    Reconstructs abstract from inverted index if available.
    """
    # Extract primary location fields safely
    pl = work.get("primary_location") or {}
    source = pl.get("source") or {}

    # Reconstruct abstract from inverted index
    abstract = None
    inv_idx = work.get("abstract_inverted_index")
    if inv_idx and isinstance(inv_idx, dict):
        try:
            word_positions = []
            for word, positions in inv_idx.items():
                for pos in positions:
                    word_positions.append((pos, word))
            word_positions.sort()
            abstract = " ".join(w for _, w in word_positions)
        except Exception:
            abstract = None

    # Extract open_access safely
    oa = work.get("open_access") or {}

    # Normalise DOI to lowercase without URL prefix for matching
    raw_doi = work.get("doi") or ""
    doi_normalised = raw_doi.replace("https://doi.org/", "").lower().strip()

    return {
        "doi_normalised": doi_normalised,
        "oa_source_type": source.get("type"),
        "oa_version": pl.get("version"),
        "oa_raw_type": pl.get("raw_type"),
        "oa_is_paratext": work.get("is_paratext"),
        "oa_is_retracted": work.get("is_retracted"),
        "oa_type": work.get("type"),
        "oa_cited_by_count": work.get("cited_by_count"),
        "oa_is_oa": oa.get("is_oa"),
        "oa_abstract": abstract,
    }


def query_openalex_all(
    dois: list[str],
    email: str | None,
    checkpoint: dict | None = None,
) -> dict[str, dict]:
    """Query OpenAlex for all DOIs using batch requests.

    Returns a dict mapping normalised DOI → enrichment data dict.
    Saves checkpoints periodically for resilience.
    """
    # Determine which DOIs still need processing
    already_processed = set()
    enrichment_data = {}

    if checkpoint:
        already_processed = set(checkpoint.get("processed_dois", []))
        enrichment_data = checkpoint.get("enrichment_data", {})
        print(f"  Resuming from checkpoint: {len(already_processed)} DOIs already processed")

    remaining = [d for d in dois if d not in already_processed]

    if not remaining:
        print("  All DOIs already processed (from checkpoint)")
        return enrichment_data

    # Split into batches
    batches = [remaining[i:i + BATCH_SIZE] for i in range(0, len(remaining), BATCH_SIZE)]
    total_batches = len(batches)

    print(f"\nPhase 2: Querying OpenAlex ({total_batches} batches of up to {BATCH_SIZE})...")

    total_matched = 0
    total_not_found = 0

    for batch_idx, batch_dois in enumerate(batches, start=1):
        # Polite delay between requests
        if batch_idx > 1:
            time.sleep(REQUEST_DELAY)

        # Execute batch request
        results = _openalex_batch_request(batch_dois, email)

        # Parse results and build lookup by normalised DOI
        batch_matched = 0
        found_dois = set()

        for work in results:
            parsed = _parse_openalex_work(work)
            norm_doi = parsed["doi_normalised"]
            if norm_doi:
                enrichment_data[norm_doi] = parsed
                found_dois.add(norm_doi)
                batch_matched += 1

        # DOIs in this batch that weren't found
        batch_not_found = len(batch_dois) - batch_matched
        total_matched += batch_matched
        total_not_found += batch_not_found

        # Track processed DOIs (whether found or not)
        already_processed.update(batch_dois)

        # Progress report
        print(f"  Batch {batch_idx}/{total_batches}: "
              f"fetched {batch_matched}/{len(batch_dois)} "
              f"({batch_not_found} not found)")

        # Save checkpoint periodically
        if batch_idx % CHECKPOINT_INTERVAL == 0:
            save_checkpoint(enrichment_data, list(already_processed))
            print(f"  [Checkpoint saved: {len(already_processed)} DOIs processed]")

    # Final stats
    total_queried = total_matched + total_not_found
    print(f"\n  OpenAlex lookup complete: "
          f"{total_matched}/{total_queried} matched "
          f"({total_matched / total_queried * 100:.1f}%), "
          f"{total_not_found} not found")

    return enrichment_data


# ---------------------------------------------------------------------------
# Phase 3: Enrichment Merge
# ---------------------------------------------------------------------------

def enrich_dataframe(
    df: pd.DataFrame,
    oa_data: dict[str, dict],
) -> pd.DataFrame:
    """Left-join OpenAlex enrichment data onto the combined DataFrame.

    Backfills missing abstracts from OpenAlex.
    Sets openalex_lookup status for each row.
    """
    print("\nPhase 3: Enrichment merge...")

    # Normalise DOIs in the DataFrame for matching
    df["_doi_norm"] = df["doi"].fillna("").str.strip().str.lower()

    # Initialize enrichment columns
    enrich_cols = [
        "oa_source_type", "oa_version", "oa_raw_type",
        "oa_is_paratext", "oa_is_retracted", "oa_type",
        "oa_cited_by_count", "oa_is_oa", "openalex_lookup",
    ]
    for col in enrich_cols:
        df[col] = None

    # Track statistics
    abstracts_backfilled = 0
    matched_count = 0
    no_match_count = 0
    no_doi_count = 0

    for idx, row in df.iterrows():
        doi_norm = row["_doi_norm"]

        # No DOI — can't look up
        if not doi_norm:
            df.at[idx, "openalex_lookup"] = "no_doi"
            no_doi_count += 1
            continue

        # Look up in enrichment data
        oa = oa_data.get(doi_norm)
        if not oa:
            df.at[idx, "openalex_lookup"] = "no_match"
            no_match_count += 1
            continue

        # Matched — populate enrichment columns
        df.at[idx, "openalex_lookup"] = "matched"
        matched_count += 1
        df.at[idx, "oa_source_type"] = oa.get("oa_source_type")
        df.at[idx, "oa_version"] = oa.get("oa_version")
        df.at[idx, "oa_raw_type"] = oa.get("oa_raw_type")
        df.at[idx, "oa_is_paratext"] = oa.get("oa_is_paratext")
        df.at[idx, "oa_is_retracted"] = oa.get("oa_is_retracted")
        df.at[idx, "oa_type"] = oa.get("oa_type")
        df.at[idx, "oa_cited_by_count"] = oa.get("oa_cited_by_count")
        df.at[idx, "oa_is_oa"] = oa.get("oa_is_oa")

        # Backfill abstract if currently null
        current_abstract = row.get("abstract")
        oa_abstract = oa.get("oa_abstract")
        if (pd.isna(current_abstract) or current_abstract == "") and oa_abstract:
            df.at[idx, "abstract"] = oa_abstract
            abstracts_backfilled += 1

    # Drop temporary column
    df = df.drop(columns=["_doi_norm"])

    # Report
    total_with_abstract = df["abstract"].notna().sum()
    print(f"  Matched: {matched_count}, No match: {no_match_count}, No DOI: {no_doi_count}")
    print(f"  Abstracts backfilled: {abstracts_backfilled}")
    print(f"  Total abstracts non-null: {total_with_abstract}/{len(df)}")

    return df


# ---------------------------------------------------------------------------
# Phase 4: Flagging
# ---------------------------------------------------------------------------

def apply_flags(df: pd.DataFrame) -> pd.DataFrame:
    """Apply IC3, preprint, retracted, and paratext flags.

    Flagged records go to manual review during Task 2.5 screening.
    They are NOT auto-excluded.
    """
    print("\nPhase 4: Flagging...")

    # IC3 source type mismatch:
    # Scopus says journal (j) or conference proceedings (p) but OpenAlex says repository
    df["ic3_flag"] = None
    source_type_col = df["source_type"].fillna("").str.lower()
    oa_source_col = df["oa_source_type"].fillna("").str.lower()

    ic3_mask = (
        source_type_col.isin(["j", "p", "journal", "conference proceeding"])
        & (oa_source_col == "repository")
    )
    df.loc[ic3_mask, "ic3_flag"] = "review_source_type_mismatch"
    ic3_count = ic3_mask.sum()

    # Preprint flag: version is submittedVersion
    df["preprint_flag"] = (
        df["oa_version"].fillna("").str.lower() == "submittedversion"
    )
    preprint_count = df["preprint_flag"].sum()

    # Retracted flag — use pd.isna() to avoid FutureWarning on fillna downcasting
    df["retracted_flag"] = df["oa_is_retracted"].apply(lambda x: bool(x) if pd.notna(x) else False)
    retracted_count = df["retracted_flag"].sum()

    # Paratext flag
    df["paratext_flag"] = df["oa_is_paratext"].apply(lambda x: bool(x) if pd.notna(x) else False)
    paratext_count = df["paratext_flag"].sum()

    # Report
    total_flagged = ic3_count + preprint_count + retracted_count + paratext_count
    print(f"  IC3 source_type disagreements: {ic3_count}")
    print(f"  Preprints (submittedVersion): {preprint_count}")
    print(f"  Retracted papers: {retracted_count}")
    print(f"  Paratext: {paratext_count}")
    print(f"  Total flagged for manual review: {total_flagged}")

    return df


# ---------------------------------------------------------------------------
# Checkpoint System
# ---------------------------------------------------------------------------

def save_checkpoint(enrichment_data: dict, processed_dois: list[str]) -> None:
    """Save enrichment progress to a checkpoint file."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    checkpoint = {
        "processed_dois": processed_dois,
        "enrichment_data": enrichment_data,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    CHECKPOINT_PATH.write_text(
        json.dumps(checkpoint, default=str), encoding="utf-8"
    )


def load_checkpoint() -> dict | None:
    """Load checkpoint file if it exists. Returns None if not found."""
    if CHECKPOINT_PATH.exists():
        try:
            data = json.loads(CHECKPOINT_PATH.read_text(encoding="utf-8"))
            print(f"  Checkpoint found: {len(data.get('processed_dois', []))} DOIs "
                  f"(saved {data.get('timestamp', 'unknown')})")
            return data
        except (json.JSONDecodeError, KeyError) as e:
            print(f"  WARNING: Corrupt checkpoint file, starting fresh: {e}")
            return None
    return None


def delete_checkpoint() -> None:
    """Remove checkpoint file after successful completion."""
    if CHECKPOINT_PATH.exists():
        CHECKPOINT_PATH.unlink()


# ---------------------------------------------------------------------------
# Decision Register Logging
# ---------------------------------------------------------------------------

def log_to_decision_register(
    match_rate: float,
    flag_counts: dict,
    row_count: int,
    output_path: Path,
) -> None:
    """Append an openalex_enrichment_executed row to decision_register.csv."""
    register_path = ROOT / "decision_register.csv"
    timestamp = datetime.now(timezone.utc).isoformat()

    flags_summary = ", ".join(f"{k}={v}" for k, v in flag_counts.items())

    row = {
        "timestamp": timestamp,
        "phase": "2",
        "paper_id": "N/A",
        "decision": "openalex_enrichment_executed",
        "rule_applied": "Petersen 2015 §5 (cross-database validation)",
        "rationale": (
            f"OpenAlex enrichment: match rate {match_rate:.1%}, "
            f"flags: [{flags_summary}], "
            f"output rows: {row_count}, "
            f"output: {output_path.relative_to(ROOT)}"
        ),
        "rater_initials": "AT",
    }

    with open(register_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        writer.writerow(row)

    print(f"  Logged to decision_register.csv")


# ---------------------------------------------------------------------------
# CLI Argument Parsing
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="OpenAlex enrichment for merged Scopus + ACM DL search results",
        epilog="Example: python code/openalex_enrich.py",
    )
    parser.add_argument(
        "--scopus", type=Path, default=None,
        help="Scopus CSV path (default: auto-discover latest in artifacts/search/raw/)",
    )
    parser.add_argument(
        "--acm", type=Path, default=None,
        help="ACM DL CSV path (default: auto-discover latest in artifacts/search/raw/)",
    )
    parser.add_argument(
        "--output", type=Path,
        default=OUTPUT_DIR / "merged_openalex.csv",
        help="Output CSV path",
    )
    parser.add_argument(
        "--email", type=str, default=None,
        help="OpenAlex polite-pool email (default: reads from .env)",
    )
    parser.add_argument(
        "--resume", action="store_true", default=False,
        help="Resume from checkpoint if previous run was interrupted",
    )
    parser.add_argument(
        "--batch-size", type=int, default=BATCH_SIZE,
        help=f"DOIs per batch request (default: {BATCH_SIZE})",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """Entry point: load, merge, enrich, flag, write."""
    args = parse_args()

    # Override batch size if provided
    global BATCH_SIZE
    BATCH_SIZE = args.batch_size

    # ----- Load email for polite pool -----
    email = load_email(args.email)
    if email:
        print(f"OpenAlex polite pool: {email}")
    else:
        print("WARNING: No OPENALEX_EMAIL set — using anonymous pool (slower, less reliable)")

    # ----- Phase 1: Load & Merge -----
    scopus_path = args.scopus or discover_latest_csv("scopus")
    acm_path = args.acm or discover_latest_csv("acm")

    if not scopus_path:
        print("ERROR: No Scopus CSV found. Provide --scopus or place in artifacts/search/raw/", file=sys.stderr)
        sys.exit(1)
    if not acm_path:
        print("ERROR: No ACM DL CSV found. Provide --acm or place in artifacts/search/raw/", file=sys.stderr)
        sys.exit(1)

    # Resolve relative paths
    scopus_path = scopus_path.resolve() if not scopus_path.is_absolute() else scopus_path
    acm_path = acm_path.resolve() if not acm_path.is_absolute() else acm_path

    df = load_and_merge(scopus_path, acm_path)
    unique_dois = extract_unique_dois(df)

    # ----- Phase 2: OpenAlex Batch Lookup -----
    checkpoint = None
    if args.resume:
        checkpoint = load_checkpoint()

    oa_data = query_openalex_all(unique_dois, email, checkpoint)

    # ----- Phase 3: Enrichment Merge -----
    df = enrich_dataframe(df, oa_data)

    # ----- Phase 4: Flagging -----
    df = apply_flags(df)

    # ----- Phase 5: Write Output -----
    print("\nPhase 5: Writing output...")
    output_path = args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(output_path, index=False, quoting=csv.QUOTE_ALL)
    print(f"  Written: {output_path} ({len(df)} rows)")

    # Compute statistics before writing meta
    scopus_count = len(df[df["search_path"] == "A"])
    acm_count = len(df[df["search_path"] == "ACM_DL"])
    total_dois = len(unique_dois)
    null_doi_count = df["doi"].isna().sum()
    matched_dois = df[df["openalex_lookup"] == "matched"]["doi"].str.lower().str.strip().nunique()
    match_rate = matched_dois / total_dois if total_dois > 0 else 0.0
    abstracts_nonnull = int(df["abstract"].notna().sum())

    # Flag counts
    flag_counts = {
        "ic3_mismatch": int((df["ic3_flag"].notna()).sum()),
        "preprint": int((df["preprint_flag"] == True).sum()),
        "retracted": int((df["retracted_flag"] == True).sum()),
        "paratext": int((df["paratext_flag"] == True).sum()),
    }

    # Lookup status distribution
    lookup_counts = df["openalex_lookup"].value_counts().to_dict()

    # Write standard .meta.json first
    input_files = [
        str(scopus_path.relative_to(ROOT)),
        str(acm_path.relative_to(ROOT)),
    ]
    write_with_meta(
        target_path=output_path,
        script="code/openalex_enrich.py",
        inputs=input_files,
        seed=42,
    )

    # Extend .meta.json with pipeline_stats
    # Note: all values cast to native Python types to avoid numpy int64 JSON error
    meta_path = output_path.with_suffix(output_path.suffix + ".meta.json")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["pipeline_stats"] = {
        "scopus_rows": int(scopus_count),
        "acm_dl_rows": int(acm_count),
        "combined_rows": int(len(df)),
        "unique_dois_queried": int(total_dois),
        "null_doi_rows": int(null_doi_count),
        "openalex_match_rate": round(float(match_rate), 4),
        "openalex_lookup_status": {str(k): int(v) for k, v in lookup_counts.items()},
        "abstracts_nonnull": int(abstracts_nonnull),
        "abstracts_total": int(len(df)),
        "abstracts_fill_rate": round(float(abstracts_nonnull / len(df)), 4) if len(df) > 0 else 0.0,
        "flags": {str(k): int(v) for k, v in flag_counts.items()},
        "flags_total": int(sum(flag_counts.values())),
    }
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(f"  Written: {meta_path}")

    # Log to decision register
    log_to_decision_register(match_rate, flag_counts, len(df), output_path)

    # Clean up checkpoint on success
    delete_checkpoint()

    # ----- Final Summary -----
    print(f"\n{'=' * 50}")
    print(f"  Final Summary")
    print(f"{'=' * 50}")
    print(f"  Total rows: {len(df)}")
    print(f"  Unique DOIs queried: {total_dois}")
    print(f"  OpenAlex match rate: {match_rate:.1%} (DoD threshold: ≥95%)")
    if match_rate < 0.95:
        print(f"  ⚠ WARNING: Match rate below 95% threshold")
    else:
        print(f"  ✓ Match rate meets DoD threshold")
    print(f"  Abstracts non-null: {df['abstract'].notna().sum()}/{len(df)}")
    print(f"  Flagged for manual review: {sum(flag_counts.values())}")
    for flag_name, count in flag_counts.items():
        if count > 0:
            print(f"    {flag_name}: {count}")
    print(f"  Output: {output_path}")


if __name__ == "__main__":
    main()
