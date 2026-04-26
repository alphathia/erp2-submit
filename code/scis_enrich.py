"""SCIS ranking enrichment for merged search results.

Pipeline step 4: Adds three columns (scis_acronym, scis_venue_type, scis_rank)
to the enriched CSV based on venue lookup in ERP_SCISList.xlsx.

Task 2.4.1 — matches each paper's venue against the SCIS approved venue list
using three fields in priority order: ISSN/ISBN → Name → Acronym.

Usage:
    python code/scis_enrich.py
    python code/scis_enrich.py --input path/to/merged_openalex.csv --scis path/to/ERP_SCISList.xlsx

Consumes:
    artifacts/search/enriched/merged_openalex.csv (4625 rows, 30 cols)
    ERP_SCISList.xlsx (Journal + Conference worksheets)

Produces:
    artifacts/search/enriched/scis_enriched.csv (4625 rows, 33 cols)
    artifacts/search/enriched/scis_enriched.csv.meta.json
    Appends row to decision_register.csv
"""

import argparse
import csv
import json
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Project setup
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, str(ROOT))
from code.utils import write_with_meta

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_INPUT = ROOT / "artifacts" / "search" / "enriched" / "merged_openalex.csv"
DEFAULT_SCIS = ROOT / "ERP_SCISList.xlsx"
DEFAULT_OUTPUT = ROOT / "artifacts" / "search" / "enriched" / "scis_enriched.csv"

NOT_FOUND = "Not found"

# Progress reporting interval
PROGRESS_EVERY = 500


# ---------------------------------------------------------------------------
# Normalisation Helpers
# ---------------------------------------------------------------------------

def normalise_issn(raw: str) -> str:
    """Normalise an ISSN/ISBN for matching.

    Strips whitespace, hyphens, and lowercases. Returns empty string on null.
    E.g., "1553-734X" → "1553734x"
    """
    if not raw or pd.isna(raw):
        return ""
    s = str(raw).strip().replace("-", "").replace(" ", "").lower()
    return s


def normalise_name(raw: str) -> str:
    """Normalise a venue name for matching.

    - Lowercase
    - Unicode NFKD normalisation (strip accents)
    - Strip leading "proceedings of the", "the"
    - Remove punctuation (except word chars and spaces)
    - Collapse multiple spaces
    """
    if not raw or pd.isna(raw):
        return ""
    s = str(raw).strip().lower()
    # Unicode normalisation to strip accents
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    # Strip common leading phrases
    for prefix in ("proceedings of the ", "proceedings of ", "the "):
        if s.startswith(prefix):
            s = s[len(prefix):]
    # Remove non-word characters except spaces
    s = re.sub(r"[^\w\s]", " ", s)
    # Collapse whitespace
    s = re.sub(r"\s+", " ", s).strip()
    return s


def normalise_acronym(raw: str) -> str:
    """Normalise an acronym for matching — uppercase, strip whitespace."""
    if not raw or pd.isna(raw):
        return ""
    return str(raw).strip().upper()


def clean_acronym_for_output(raw, name_fallback: str = "") -> str:
    """Sanitise an acronym value for storage.

    SCIS list has some rows with empty/NaN Acronym cells (e.g., some
    journals without established acronyms). To keep output CSV free of
    nulls, substitute a short form of the name, or a placeholder.

    Returns a non-empty string suitable for the scis_acronym column.
    """
    if raw is None or pd.isna(raw):
        s = ""
    else:
        s = str(raw).strip()

    # Treat these as missing
    if not s or s.lower() in ("nan", "none", "n/a"):
        # Use the journal/conference name as fallback acronym
        # (cleaned: strip "Journal of", keep first meaningful words)
        if name_fallback:
            fb = name_fallback.strip()
            # Take up to the first 30 chars as placeholder acronym
            return fb[:30] if fb else "(no acronym)"
        return "(no acronym)"

    return s


# ---------------------------------------------------------------------------
# Build Lookup Tables from ERP_SCISList.xlsx
# ---------------------------------------------------------------------------

def build_lookups(scis_path: Path) -> tuple[dict, dict, dict]:
    """Load the SCIS Excel file and build three lookup dictionaries.

    Returns:
        issn_idx:    {normalised_issn: (acronym, rank, 'Journal')}
        name_idx:    {normalised_name: (acronym, rank, worksheet_name)}
        acronym_idx: {uppercase_acronym: (acronym, rank, worksheet_name)}
    """
    print(f"  Loading SCIS list from {scis_path.relative_to(ROOT)}...")

    # Read both worksheets
    journals = pd.read_excel(scis_path, sheet_name="Journal")
    conferences = pd.read_excel(scis_path, sheet_name="Conference")

    issn_idx = {}
    name_idx = {}
    acronym_idx = {}

    # --- Journal worksheet — has ISSN/ISBN ---
    for _, row in journals.iterrows():
        raw_acronym = row.get("Acronym")
        rank = str(row.get("2025 SCIS Ranking", "")).strip()
        name = str(row.get("Name", "")).strip()
        issn = str(row.get("ISSN/ISBN", "")).strip()

        # Skip rows missing essential data
        if not name or not rank or rank.lower() == "nan":
            continue

        # Sanitise acronym for storage — never NaN/empty in output
        clean_acr = clean_acronym_for_output(raw_acronym, name_fallback=name)

        # ISSN index (Journals only)
        if issn and issn.lower() not in ("n/a", "nan", ""):
            issn_norm = normalise_issn(issn)
            if issn_norm:
                issn_idx[issn_norm] = (clean_acr, rank, "Journal")

        # Name index
        name_norm = normalise_name(name)
        if name_norm:
            name_idx[name_norm] = (clean_acr, rank, "Journal")

        # Acronym index (only if non-empty and not 'nan' — used for acronym lookup)
        acr_norm = normalise_acronym(raw_acronym)
        if acr_norm and acr_norm.lower() != "nan":
            acronym_idx[acr_norm] = (clean_acr, rank, "Journal")

    # --- Conference worksheet — no ISSN ---
    for _, row in conferences.iterrows():
        raw_acronym = row.get("Acronym")
        rank = str(row.get("2025 SCIS Ranking", "")).strip()
        name = str(row.get("Name", "")).strip()

        if not name or not rank or rank.lower() == "nan":
            continue

        clean_acr = clean_acronym_for_output(raw_acronym, name_fallback=name)

        name_norm = normalise_name(name)
        if name_norm:
            # Conference name index — don't overwrite journal entries
            if name_norm not in name_idx:
                name_idx[name_norm] = (clean_acr, rank, "Conference")

        acr_norm = normalise_acronym(raw_acronym)
        if acr_norm and acr_norm.lower() != "nan":
            if acr_norm not in acronym_idx:
                acronym_idx[acr_norm] = (clean_acr, rank, "Conference")

    print(f"  ISSN index:    {len(issn_idx):4d} entries")
    print(f"  Name index:    {len(name_idx):4d} entries")
    print(f"  Acronym index: {len(acronym_idx):4d} entries")

    return issn_idx, name_idx, acronym_idx


# ---------------------------------------------------------------------------
# Row Matching
# ---------------------------------------------------------------------------

def match_row(
    row: pd.Series,
    issn_idx: dict,
    name_idx: dict,
    acronym_idx: dict,
) -> tuple[str, str, str, str]:
    """Match a single row against SCIS lookups.

    Returns (acronym, venue_type, rank, match_method) where match_method is
    one of: 'issn', 'name', 'acronym', 'none'.

    Priority order:
        1. ISSN match (Journal only, highest precision)
        2. Name match (both worksheets, fuzzy-normalised)
        3. Acronym match (both worksheets, last resort, log for spot-check)
    """

    # --- Priority 1: ISSN ---
    issn_raw = row.get("issn")
    if issn_raw and pd.notna(issn_raw):
        # Scopus sometimes returns multiple ISSNs separated by space
        # (print + electronic). Try each.
        for issn_part in str(issn_raw).split():
            issn_norm = normalise_issn(issn_part)
            if issn_norm and issn_norm in issn_idx:
                acronym, rank, vtype = issn_idx[issn_norm]
                return (acronym, vtype, rank, "issn")

    # --- Priority 2: Name ---
    source_raw = row.get("source")
    if source_raw and pd.notna(source_raw):
        name_norm = normalise_name(source_raw)
        if name_norm and name_norm in name_idx:
            acronym, rank, vtype = name_idx[name_norm]
            return (acronym, vtype, rank, "name")

    # --- Priority 3: Acronym (extract from source, last resort) ---
    # Look for standalone acronyms in the venue name, e.g.
    # "...ICSE 2024..." or "...CHI '25..."
    if source_raw and pd.notna(source_raw):
        # Find all uppercase tokens of length 2-8
        candidates = re.findall(r"\b[A-Z]{2,8}\b", str(source_raw))
        for cand in candidates:
            if cand in acronym_idx:
                acronym, rank, vtype = acronym_idx[cand]
                return (acronym, vtype, rank, "acronym")

    # --- No match ---
    return (NOT_FOUND, NOT_FOUND, NOT_FOUND, "none")


# ---------------------------------------------------------------------------
# Enrichment Loop
# ---------------------------------------------------------------------------

def enrich(
    df: pd.DataFrame,
    issn_idx: dict,
    name_idx: dict,
    acronym_idx: dict,
) -> tuple[pd.DataFrame, dict]:
    """Apply SCIS lookups to every row. Returns enriched DataFrame + stats."""

    print(f"\nPhase 3: Enriching {len(df)} rows...")

    # Pre-allocate new columns
    df["scis_acronym"] = NOT_FOUND
    df["scis_venue_type"] = NOT_FOUND
    df["scis_rank"] = NOT_FOUND

    stats = {
        "total_rows": len(df),
        "match_issn": 0,
        "match_name": 0,
        "match_acronym": 0,
        "not_found": 0,
        "by_rank": {"A*": 0, "A": 0, "B": 0, "Not found": 0},
        "by_venue_type": {"Journal": 0, "Conference": 0, "Not found": 0},
    }

    for idx, row in df.iterrows():
        acronym, vtype, rank, method = match_row(row, issn_idx, name_idx, acronym_idx)

        df.at[idx, "scis_acronym"] = acronym
        df.at[idx, "scis_venue_type"] = vtype
        df.at[idx, "scis_rank"] = rank

        # Update stats
        if method == "issn":
            stats["match_issn"] += 1
        elif method == "name":
            stats["match_name"] += 1
        elif method == "acronym":
            stats["match_acronym"] += 1
        else:
            stats["not_found"] += 1

        if rank in stats["by_rank"]:
            stats["by_rank"][rank] += 1
        if vtype in stats["by_venue_type"]:
            stats["by_venue_type"][vtype] += 1

        # Progress report every N rows
        if (idx + 1) % PROGRESS_EVERY == 0 or (idx + 1) == len(df):
            matched = stats["match_issn"] + stats["match_name"] + stats["match_acronym"]
            pct = (idx + 1) / len(df) * 100
            print(f"  {idx + 1:5d}/{len(df)} rows ({pct:5.1f}%) — "
                  f"matched: {matched:4d}, not found: {stats['not_found']:4d}")

    return df, stats


# ---------------------------------------------------------------------------
# Decision Register Logging
# ---------------------------------------------------------------------------

def log_to_decision_register(stats: dict, output_path: Path) -> None:
    """Append scis_enrichment_executed row to decision_register.csv."""
    register_path = ROOT / "decision_register.csv"
    timestamp = datetime.now(timezone.utc).isoformat()
    total_matched = stats["match_issn"] + stats["match_name"] + stats["match_acronym"]
    rate = total_matched / stats["total_rows"] if stats["total_rows"] > 0 else 0

    row = {
        "timestamp": timestamp,
        "phase": "2",
        "paper_id": "N/A",
        "decision": "scis_enrichment_executed",
        "rule_applied": "SMU SCIS 2025 venue ranking list",
        "rationale": (
            f"SCIS enrichment: {total_matched}/{stats['total_rows']} matched "
            f"({rate:.1%}). "
            f"By method: issn={stats['match_issn']}, "
            f"name={stats['match_name']}, "
            f"acronym={stats['match_acronym']}. "
            f"By rank: A*={stats['by_rank']['A*']}, "
            f"A={stats['by_rank']['A']}, "
            f"B={stats['by_rank']['B']}. "
            f"By type: Journal={stats['by_venue_type']['Journal']}, "
            f"Conference={stats['by_venue_type']['Conference']}. "
            f"Output: {output_path.relative_to(ROOT)}"
        ),
        "rater_initials": "AT",
    }

    with open(register_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        writer.writerow(row)
    print(f"  Logged to decision_register.csv")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="SCIS ranking enrichment for merged search results",
        epilog="Example: python code/scis_enrich.py",
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT,
                        help=f"Input CSV (default: {DEFAULT_INPUT.relative_to(ROOT)})")
    parser.add_argument("--scis", type=Path, default=DEFAULT_SCIS,
                        help=f"SCIS ranking spreadsheet (default: {DEFAULT_SCIS.name})")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                        help=f"Output CSV (default: {DEFAULT_OUTPUT.relative_to(ROOT)})")
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    args = parse_args()

    input_path = args.input.resolve()
    scis_path = args.scis.resolve()
    output_path = args.output.resolve()

    # Validate inputs
    if not input_path.exists():
        print(f"ERROR: Input CSV not found: {input_path}", file=sys.stderr)
        sys.exit(1)
    if not scis_path.exists():
        print(f"ERROR: SCIS spreadsheet not found: {scis_path}", file=sys.stderr)
        sys.exit(1)

    # ----- Phase 1: Load inputs -----
    print("Phase 1: Loading inputs...")
    df = pd.read_csv(input_path, dtype=str)
    print(f"  Input CSV: {len(df)} rows, {len(df.columns)} cols loaded")

    # ----- Phase 2: Build lookups -----
    print("\nPhase 2: Building lookup tables...")
    issn_idx, name_idx, acronym_idx = build_lookups(scis_path)

    # ----- Phase 3: Enrich rows -----
    df, stats = enrich(df, issn_idx, name_idx, acronym_idx)

    # ----- Phase 4: Write output -----
    print("\nPhase 4: Writing output...")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, quoting=csv.QUOTE_ALL)
    print(f"  Written: {output_path.relative_to(ROOT)} ({len(df)} rows, {len(df.columns)} cols)")

    # Write .meta.json with pipeline_stats
    total_matched = stats["match_issn"] + stats["match_name"] + stats["match_acronym"]
    input_files = [str(input_path.relative_to(ROOT)), str(scis_path.relative_to(ROOT))]
    write_with_meta(
        target_path=output_path,
        script="code/scis_enrich.py",
        inputs=input_files,
        seed=42,
    )
    meta_path = output_path.with_suffix(output_path.suffix + ".meta.json")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["pipeline_stats"] = {
        "input_rows": int(stats["total_rows"]),
        "output_rows": int(len(df)),
        "output_cols": int(len(df.columns)),
        "scis_matched": int(total_matched),
        "scis_match_rate": round(total_matched / stats["total_rows"], 4)
                            if stats["total_rows"] > 0 else 0,
        "match_by_method": {
            "issn": int(stats["match_issn"]),
            "name": int(stats["match_name"]),
            "acronym": int(stats["match_acronym"]),
            "not_found": int(stats["not_found"]),
        },
        "match_by_rank": {k: int(v) for k, v in stats["by_rank"].items()},
        "match_by_venue_type": {k: int(v) for k, v in stats["by_venue_type"].items()},
    }
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(f"  Written: {meta_path.name}")

    # Log to decision register
    log_to_decision_register(stats, output_path)

    # ----- Final Summary -----
    print("\n" + "=" * 60)
    print("  Final Summary")
    print("=" * 60)
    print(f"  Total rows: {stats['total_rows']}")
    print(f"  SCIS matches: {total_matched} ({total_matched/stats['total_rows']*100:.1f}%)")
    print(f"\n  By match method:")
    print(f"    ISSN:    {stats['match_issn']:4d}")
    print(f"    Name:    {stats['match_name']:4d}")
    print(f"    Acronym: {stats['match_acronym']:4d}")
    print(f"    Not found: {stats['not_found']:4d}")
    print(f"\n  By venue type:")
    for vtype, count in stats["by_venue_type"].items():
        print(f"    {vtype:<12s}: {count:4d}")
    print(f"\n  By rank:")
    for rank, count in stats["by_rank"].items():
        print(f"    {rank:<12s}: {count:4d}")
    print(f"\n  Output: {output_path}")


if __name__ == "__main__":
    main()
