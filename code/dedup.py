"""Deduplicate search results across Scopus + ACM DL.

Pipeline step 5: Collapses duplicate entries so each paper appears once.
Primary rule: group by normalised DOI. Fallback: title + year + first author.

Task 2.4.2 — per Petersen (2015) §5.4, dedup is mandatory before screening.

Usage:
    python code/dedup.py
    python code/dedup.py --input path/to/scis_enriched.csv --output path/to/dedup.csv

Consumes:
    artifacts/search/enriched/scis_enriched.csv (4625 rows, 33 cols)

Produces:
    artifacts/search/enriched/dedup.csv (unique rows, 34 cols)
    artifacts/search/enriched/dedup.csv.meta.json
    Appends row to decision_register.csv
"""

import argparse
import csv
import hashlib
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

DEFAULT_INPUT = ROOT / "artifacts" / "search" / "enriched" / "scis_enriched.csv"
DEFAULT_OUTPUT = ROOT / "artifacts" / "search" / "enriched" / "dedup.csv"

# DOI URL prefixes to strip during normalisation
DOI_URL_PREFIXES = (
    "https://doi.org/",
    "http://doi.org/",
    "https://dx.doi.org/",
    "http://dx.doi.org/",
    "doi:",
    "DOI:",
)

# SCIS rank ordering — higher score = better rank
RANK_SCORE = {"A*": 3, "A": 2, "B": 1, "Not found": 0}


# ---------------------------------------------------------------------------
# Normalisation Helpers
# ---------------------------------------------------------------------------

def normalise_doi(raw) -> str | None:
    """Normalise a DOI for deduplication grouping.

    - Strip URL prefixes (https://doi.org/, etc.)
    - Lowercase
    - Strip whitespace
    Returns None if input is null/empty.
    """
    if raw is None or pd.isna(raw):
        return None
    s = str(raw).strip()
    if not s:
        return None
    # Strip URL prefixes case-insensitively
    s_lower = s.lower()
    for prefix in DOI_URL_PREFIXES:
        if s_lower.startswith(prefix.lower()):
            s = s[len(prefix):]
            break
    return s.lower().strip() or None


def normalise_title(raw) -> str:
    """Normalise a title for fallback duplicate matching.

    Lowercase, strip accents, remove punctuation, collapse whitespace.
    """
    if raw is None or pd.isna(raw):
        return ""
    s = str(raw).strip().lower()
    # Unicode NFKD to strip accents
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    # Remove non-word characters (keep spaces)
    s = re.sub(r"[^\w\s]", " ", s)
    # Collapse whitespace
    s = re.sub(r"\s+", " ", s).strip()
    return s


def normalise_first_author_surname(authors_str) -> str:
    """Extract normalised surname of the first author.

    Input authors format: "Surname, First; Surname, First; ..."
    Returns lowercase surname of first author, or empty string.
    """
    if authors_str is None or pd.isna(authors_str):
        return ""
    first = str(authors_str).split(";")[0].strip()
    # If format is "Surname, First", take the part before the comma
    if "," in first:
        surname = first.split(",")[0].strip()
    else:
        # Fallback: take the last word as the surname
        surname = first.split()[-1] if first else ""
    surname = unicodedata.normalize("NFKD", surname.lower())
    surname = "".join(c for c in surname if not unicodedata.combining(c))
    return surname


def fallback_key(row: pd.Series) -> str:
    """Build a stable hash key from title + year + first author surname.

    Used when DOI is missing. Returns a deterministic hash so matching rows
    produce identical keys.
    """
    title = normalise_title(row.get("title"))
    year_raw = row.get("year")
    try:
        year = int(float(year_raw)) if year_raw and not pd.isna(year_raw) else 0
    except (ValueError, TypeError):
        year = 0
    surname = normalise_first_author_surname(row.get("authors"))
    # Compose key and hash for compactness
    composite = f"{title}||{year}||{surname}"
    digest = hashlib.md5(composite.encode("utf-8")).hexdigest()[:12]
    return digest


# ---------------------------------------------------------------------------
# Leader Selection (tiebreaker)
# ---------------------------------------------------------------------------

def score_row(row: pd.Series) -> tuple:
    """Score a row for leader selection (higher tuple = preferred).

    Priority order (each element of the returned tuple):
      1. Has non-null abstract (1 or 0)
      2. Has non-null pageRange (1 or 0)
      3. SCIS rank score (3/2/1/0)
      4. Prefer Scopus over ACM_DL (Scopus="A" → 1, ACM_DL → 0)
    Ties broken by lower row index (handled by stable sort in caller).
    """
    has_abstract = 1 if pd.notna(row.get("abstract")) and row.get("abstract") != "" else 0
    has_pages = 1 if pd.notna(row.get("pageRange")) and row.get("pageRange") != "" else 0
    rank = str(row.get("scis_rank", "Not found")).strip()
    rank_score = RANK_SCORE.get(rank, 0)
    search_path = str(row.get("search_path", "")).strip()
    # Scopus (encoded as "A") is preferred over ACM_DL
    src_score = 1 if search_path == "A" else 0
    return (has_abstract, has_pages, rank_score, src_score)


def pick_leader_idx(group: pd.DataFrame) -> int:
    """Pick the index of the best row in a dedup group.

    Uses score_row() to rank; returns the DataFrame index of the winner.
    """
    best_idx = group.index[0]
    best_score = score_row(group.loc[best_idx])
    for idx in group.index[1:]:
        this_score = score_row(group.loc[idx])
        if this_score > best_score:
            best_idx = idx
            best_score = this_score
    return best_idx


def merge_provenance(group: pd.DataFrame) -> str:
    """Combine search_path values across a dedup group.

    If multiple sources (e.g., Scopus + ACM), join with '+'.
    """
    sources = sorted(set(str(s).strip() for s in group["search_path"].dropna()))
    sources = [s for s in sources if s]  # drop empty
    return "+".join(sources) if sources else ""


# ---------------------------------------------------------------------------
# Deduplication Core
# ---------------------------------------------------------------------------

def dedup_by_doi(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Deduplicate rows that have DOIs. Returns (dedup_df, stats).

    Strategy:
      1. Split df into has_doi and no_doi
      2. For has_doi: group by normalised DOI, pick leader per group,
         merge provenance
      3. Return (leaders + no_doi_rows) — no_doi will be further deduped
         by dedup_fallback() in the caller.
    """
    # Normalise DOI column
    df["_doi_norm"] = df["doi"].apply(normalise_doi)

    has_doi = df[df["_doi_norm"].notna()].copy()
    no_doi = df[df["_doi_norm"].isna()].copy()

    print(f"  Rows with DOI:    {len(has_doi):5d} ({len(has_doi)/len(df)*100:.1f}%)")
    print(f"  Rows without DOI: {len(no_doi):5d} ({len(no_doi)/len(df)*100:.1f}%)")

    # Group by normalised DOI
    grouped = has_doi.groupby("_doi_norm", sort=False)
    unique_dois = len(grouped)
    duplicate_groups = sum(1 for _, g in grouped if len(g) > 1)
    total_rows_in_dups = sum(len(g) for _, g in grouped if len(g) > 1)
    merged_provenance_count = 0

    print(f"  Unique DOIs:      {unique_dois:5d}")
    print(f"  Duplicate groups: {duplicate_groups:5d} "
          f"(covering {total_rows_in_dups} rows)")

    # Build the dedup'd has_doi portion
    leaders = []
    for doi_norm, group in grouped:
        if len(group) == 1:
            # Singleton — just take the only row
            leaders.append(group.iloc[0].copy())
            continue

        # Multiple rows — pick leader, merge provenance
        leader_idx = pick_leader_idx(group)
        leader_row = group.loc[leader_idx].copy()

        # Merge search_path from all rows in the group
        merged = merge_provenance(group)
        if merged and merged != leader_row.get("search_path"):
            leader_row["search_path"] = merged
            merged_provenance_count += 1

        leaders.append(leader_row)

    leaders_df = pd.DataFrame(leaders).reset_index(drop=True)

    # Tag each leader with dedup_group
    leaders_df["dedup_group"] = "doi:" + leaders_df["_doi_norm"].astype(str)

    # Also tag no_doi rows (will be re-grouped in fallback)
    no_doi = no_doi.copy()
    no_doi["dedup_group"] = None

    stats = {
        "rows_in":              len(df),
        "rows_with_doi":        len(has_doi),
        "rows_without_doi":     len(no_doi),
        "unique_dois":          unique_dois,
        "duplicate_groups":     duplicate_groups,
        "rows_merged":          total_rows_in_dups - duplicate_groups,
        "provenance_merged":    merged_provenance_count,
    }

    # Combine leaders (has_doi) + no_doi rows for further processing
    combined = pd.concat([leaders_df, no_doi], ignore_index=True)
    combined = combined.drop(columns=["_doi_norm"], errors="ignore")
    return combined, stats


def dedup_fallback(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Deduplicate rows without DOIs using (title, year, first_author_surname).

    Only rows where dedup_group is null (i.e., no DOI) are processed.
    Returns (final_df, stats).
    """
    no_doi_mask = df["dedup_group"].isna()
    with_doi = df[~no_doi_mask].copy()
    no_doi = df[no_doi_mask].copy()

    if len(no_doi) == 0:
        print(f"  No rows without DOI — fallback dedup skipped")
        return with_doi, {"fallback_groups": 0, "fallback_duplicates": 0}

    # Build fallback keys
    no_doi["_fb_key"] = no_doi.apply(fallback_key, axis=1)

    grouped = no_doi.groupby("_fb_key", sort=False)
    unique_groups = len(grouped)
    dup_groups = sum(1 for _, g in grouped if len(g) > 1)
    total_rows_in_dups = sum(len(g) for _, g in grouped if len(g) > 1)

    print(f"  Fallback groups (title+year+author): {unique_groups:4d}")
    print(f"  Duplicate fallback groups:           {dup_groups:4d} "
          f"(covering {total_rows_in_dups} rows)")

    leaders = []
    for fb_key, group in grouped:
        if len(group) == 1:
            leaders.append(group.iloc[0].copy())
            continue

        leader_idx = pick_leader_idx(group)
        leader_row = group.loc[leader_idx].copy()
        merged = merge_provenance(group)
        if merged:
            leader_row["search_path"] = merged
        leaders.append(leader_row)

    leaders_df = pd.DataFrame(leaders).reset_index(drop=True)
    leaders_df["dedup_group"] = "fallback:" + leaders_df["_fb_key"].astype(str)
    leaders_df = leaders_df.drop(columns=["_fb_key"])

    # Combine with has_doi
    final = pd.concat([with_doi, leaders_df], ignore_index=True)

    stats = {
        "fallback_groups":    unique_groups,
        "fallback_duplicates": total_rows_in_dups - dup_groups,
    }
    return final, stats


# ---------------------------------------------------------------------------
# Decision Register Logging
# ---------------------------------------------------------------------------

def log_to_decision_register(stats: dict, output_path: Path) -> None:
    """Append dedup_executed row to decision_register.csv."""
    register_path = ROOT / "decision_register.csv"
    timestamp = datetime.now(timezone.utc).isoformat()

    row = {
        "timestamp": timestamp,
        "phase": "2",
        "paper_id": "N/A",
        "decision": "dedup_executed",
        "rule_applied": "Petersen 2015 §5.4 (duplicate removal)",
        "rationale": (
            f"Dedup: {stats['rows_in']} input → {stats['rows_out']} output "
            f"({stats['rows_in'] - stats['rows_out']} duplicates removed). "
            f"DOI-based: {stats['unique_dois']} unique DOIs "
            f"({stats['duplicate_groups']} groups with 2+ rows, "
            f"{stats['provenance_merged']} cross-database merges). "
            f"Fallback (no-DOI): {stats['fallback_groups']} groups, "
            f"{stats['fallback_duplicates']} duplicates removed. "
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
        description="Deduplicate merged search results (Scopus + ACM DL)",
        epilog="Example: python code/dedup.py",
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT,
                        help=f"Input CSV (default: {DEFAULT_INPUT.relative_to(ROOT)})")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                        help=f"Output CSV (default: {DEFAULT_OUTPUT.relative_to(ROOT)})")
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    args = parse_args()
    input_path = args.input.resolve()
    output_path = args.output.resolve()

    if not input_path.exists():
        print(f"ERROR: Input CSV not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    # ----- Phase 1: Load -----
    print("Phase 1: Loading input...")
    df = pd.read_csv(input_path, dtype=str)
    print(f"  Loaded: {len(df)} rows, {len(df.columns)} cols from {input_path.name}")

    # ----- Phase 2: DOI-based dedup -----
    print("\nPhase 2: DOI-based deduplication...")
    df, doi_stats = dedup_by_doi(df)

    # ----- Phase 3: Fallback dedup for no-DOI rows -----
    print("\nPhase 3: Fallback deduplication (title + year + author)...")
    df, fb_stats = dedup_fallback(df)

    # Combine stats
    stats = {**doi_stats, **fb_stats, "rows_out": len(df)}

    # ----- Phase 4: Write output -----
    print("\nPhase 4: Writing output...")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, quoting=csv.QUOTE_ALL)
    print(f"  Written: {output_path.relative_to(ROOT)} ({len(df)} rows, {len(df.columns)} cols)")

    # Write .meta.json
    write_with_meta(
        target_path=output_path,
        script="code/dedup.py",
        inputs=[str(input_path.relative_to(ROOT))],
        seed=42,
    )
    meta_path = output_path.with_suffix(output_path.suffix + ".meta.json")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["pipeline_stats"] = {
        "rows_in":            int(stats["rows_in"]),
        "rows_out":           int(stats["rows_out"]),
        "rows_removed":       int(stats["rows_in"] - stats["rows_out"]),
        "reduction_rate":     round((stats["rows_in"] - stats["rows_out"]) / stats["rows_in"], 4)
                                if stats["rows_in"] > 0 else 0,
        "doi_stats": {
            "rows_with_doi":    int(stats["rows_with_doi"]),
            "rows_without_doi": int(stats["rows_without_doi"]),
            "unique_dois":      int(stats["unique_dois"]),
            "duplicate_groups": int(stats["duplicate_groups"]),
            "provenance_merged": int(stats["provenance_merged"]),
        },
        "fallback_stats": {
            "fallback_groups":     int(stats["fallback_groups"]),
            "fallback_duplicates": int(stats["fallback_duplicates"]),
        },
    }
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(f"  Written: {meta_path.name}")

    # Log to decision register
    log_to_decision_register(stats, output_path)

    # ----- Final Summary -----
    print("\n" + "=" * 60)
    print("  Final Summary")
    print("=" * 60)
    print(f"  Input rows:     {stats['rows_in']:5d}")
    print(f"  Output rows:    {stats['rows_out']:5d}")
    removed = stats['rows_in'] - stats['rows_out']
    pct = removed / stats['rows_in'] * 100 if stats['rows_in'] > 0 else 0
    print(f"  Removed:        {removed:5d} ({pct:.1f}%)")
    print()
    print(f"  DOI-based:")
    print(f"    Unique DOIs:       {stats['unique_dois']:5d}")
    print(f"    Duplicate groups:  {stats['duplicate_groups']:5d}")
    print(f"    Provenance merged: {stats['provenance_merged']:5d} (A+ACM_DL overlap)")
    print(f"  Fallback (no-DOI):")
    print(f"    Unique groups:     {stats['fallback_groups']:5d}")
    print(f"    Duplicates merged: {stats['fallback_duplicates']:5d}")
    print(f"\n  Output: {output_path}")


if __name__ == "__main__":
    main()
