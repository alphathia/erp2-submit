"""Page filter for IC5/EC5 — ≥4 pages required.

Pipeline step 6: Parses pageRange and assigns ic5_status for each row.
Does NOT drop rows — only adds page_count and ic5_status columns.

Task 2.4.3 — per rewritten Appendix A.2 IC5 (page filter). Missing page
metadata routes to 'manual_review' (not auto-excluded) to prevent losing
legitimate long papers that lack pageRange in their source CSV.

Usage:
    python code/page_filter.py
    python code/page_filter.py --input path/to/dedup.csv --output path/to/post_filtered.csv

Consumes:
    artifacts/search/enriched/dedup.csv

Produces:
    artifacts/search/post_filtered.csv (same rows, +page_count, +ic5_status cols)
    artifacts/search/post_filtered.csv.meta.json
    Appends row to decision_register.csv
"""

import argparse
import csv
import json
import re
import sys
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

DEFAULT_INPUT = ROOT / "artifacts" / "search" / "enriched" / "dedup.csv"
DEFAULT_OUTPUT = ROOT / "artifacts" / "search" / "post_filtered.csv"

# IC5 threshold: minimum page count for a paper to be considered a full paper
MIN_PAGES = 4

# ic5_status values
STATUS_PASS = "pass"
STATUS_FAIL = "fail"
STATUS_MANUAL = "manual_review"

# Progress reporting
PROGRESS_EVERY = 1000


# ---------------------------------------------------------------------------
# Page Range Parsing
# ---------------------------------------------------------------------------

def parse_page_count(page_range) -> int | None:
    """Parse a pageRange string and return the page count.

    Handles multiple formats observed across Scopus, ACM, and OpenAlex:
      - "45-55"        → 11   (standard range with hyphen)
      - "45–55"        → 11   (range with en-dash)
      - "45--55"       → 11   (range with double-dash)
      - "12"           → 1    (single page)
      - "art1164:17pp" → 17   (ACM articleno fallback from acm_bib2csv.py)
      - ":8pp"         → 8    (ACM fallback without articleno)
      - "e12345"       → None (article identifier, not pages)
      - "iii-xxii"     → None (Roman numerals, can't compute)
      - null / ""      → None (missing metadata)

    Returns None for unparseable or missing input — these route to
    manual_review (not auto-excluded) per Petersen 2015 §6.
    """
    # Null or empty → can't parse
    if page_range is None or pd.isna(page_range):
        return None

    s = str(page_range).strip()
    if not s:
        return None

    # ACM fallback format: "art1164:17pp" or ":8pp" or "17pp"
    # Match the number followed by 'pp' (page count)
    m = re.search(r"(\d+)\s*pp\b", s, re.IGNORECASE)
    if m:
        return int(m.group(1))

    # Normalise dash variants to single hyphen
    s_norm = s.replace("–", "-")  # en-dash → hyphen
    s_norm = s_norm.replace("—", "-")  # em-dash → hyphen
    s_norm = re.sub(r"-+", "-", s_norm)  # collapse multi-dashes

    # Standard range: "45-55" (digits only, no letters)
    m = re.match(r"^\s*(\d+)\s*-\s*(\d+)\s*$", s_norm)
    if m:
        start, end = int(m.group(1)), int(m.group(2))
        if end >= start:
            # Inclusive count: e.g., 45-55 → 11 pages (55 - 45 + 1)
            return end - start + 1
        # Invalid range (end < start) — unparseable
        return None

    # Single page number: "12"
    m = re.match(r"^\s*(\d+)\s*$", s_norm)
    if m:
        return 1

    # Article identifier (e.g., "e12345") or Roman numerals or anything else
    # → can't compute page count
    return None


# ---------------------------------------------------------------------------
# IC5 Status Assignment
# ---------------------------------------------------------------------------

def assign_ic5_status(page_count: int | None) -> str:
    """Map page count to ic5_status.

    - None (unparseable) → manual_review
    - page_count >= 4    → pass
    - page_count < 4     → fail

    Per inclusion_exclusion.md IC5: paper must be at least 4 pages.
    """
    if page_count is None:
        return STATUS_MANUAL
    if page_count >= MIN_PAGES:
        return STATUS_PASS
    return STATUS_FAIL


# ---------------------------------------------------------------------------
# Filtering Pipeline
# ---------------------------------------------------------------------------

def apply_filter(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Apply page_count parsing and ic5_status assignment to each row.

    Returns (filtered_df, stats) where stats contains counts by status.
    """
    print(f"\nPhase 2: Parsing page ranges for {len(df)} rows...")

    # Pre-allocate columns
    df["page_count"] = pd.Series(dtype="Int64")  # nullable integer
    df["ic5_status"] = ""

    stats = {
        "total":         len(df),
        "pass":          0,
        "fail":          0,
        "manual_review": 0,
        "page_counts":   [],  # for stats computation later
    }

    for idx in df.index:
        raw_pr = df.at[idx, "pageRange"]

        # Parse the page range
        pc = parse_page_count(raw_pr)

        # Store page_count (nullable int)
        if pc is not None:
            df.at[idx, "page_count"] = pc
            stats["page_counts"].append(pc)

        # Assign status
        status = assign_ic5_status(pc)
        df.at[idx, "ic5_status"] = status
        stats[status] += 1

        # Progress report
        processed = idx + 1
        if processed % PROGRESS_EVERY == 0 or processed == len(df):
            pct = processed / len(df) * 100
            print(f"  {processed:5d}/{len(df)} rows ({pct:5.1f}%) — "
                  f"pass: {stats['pass']:4d}, "
                  f"fail: {stats['fail']:4d}, "
                  f"manual_review: {stats['manual_review']:4d}")

    return df, stats


# ---------------------------------------------------------------------------
# Decision Register Logging
# ---------------------------------------------------------------------------

def log_to_decision_register(stats: dict, output_path: Path) -> None:
    """Append page_filter_executed row to decision_register.csv."""
    register_path = ROOT / "decision_register.csv"
    timestamp = datetime.now(timezone.utc).isoformat()

    row = {
        "timestamp": timestamp,
        "phase": "2",
        "paper_id": "N/A",
        "decision": "page_filter_executed",
        "rule_applied": "Rewritten Appendix A.2 IC5 (≥4 pages); Petersen 2015 §6",
        "rationale": (
            f"IC5 page filter: {stats['total']} rows processed. "
            f"pass={stats['pass']}, fail={stats['fail']}, "
            f"manual_review={stats['manual_review']} "
            f"(missing pageRange routed to manual_review, not auto-excluded). "
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
        description="Page filter (IC5/EC5) — ≥4 pages required",
        epilog="Example: python code/page_filter.py",
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

    # ----- Phase 2: Apply page filter -----
    df, stats = apply_filter(df)

    # Compute page count statistics (for pass rows only)
    page_counts = stats.pop("page_counts")  # not JSON-serialisable in meta
    if page_counts:
        pc_min = min(page_counts)
        pc_max = max(page_counts)
        pc_mean = sum(page_counts) / len(page_counts)
        page_counts_sorted = sorted(page_counts)
        pc_median = page_counts_sorted[len(page_counts_sorted) // 2]
    else:
        pc_min = pc_max = pc_mean = pc_median = None

    # ----- Phase 3: Write output -----
    print("\nPhase 3: Writing output...")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, quoting=csv.QUOTE_ALL)
    print(f"  Written: {output_path.relative_to(ROOT)} ({len(df)} rows, {len(df.columns)} cols)")

    # Write .meta.json
    write_with_meta(
        target_path=output_path,
        script="code/page_filter.py",
        inputs=[str(input_path.relative_to(ROOT))],
        seed=42,
    )
    meta_path = output_path.with_suffix(output_path.suffix + ".meta.json")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["pipeline_stats"] = {
        "total_rows": int(stats["total"]),
        "ic5_status": {
            "pass":          int(stats["pass"]),
            "fail":          int(stats["fail"]),
            "manual_review": int(stats["manual_review"]),
        },
        "ic5_threshold_pages": MIN_PAGES,
        "page_count_stats": {
            "min":    int(pc_min) if pc_min is not None else None,
            "max":    int(pc_max) if pc_max is not None else None,
            "mean":   round(float(pc_mean), 2) if pc_mean is not None else None,
            "median": int(pc_median) if pc_median is not None else None,
            "parsed_count": int(len(page_counts)),
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
    print(f"  Total rows: {stats['total']}")
    print(f"\n  ic5_status distribution:")
    total = stats["total"]
    for status_key, label in [
        ("pass", "pass"),
        ("fail", "fail"),
        ("manual_review", "manual_review"),
    ]:
        count = stats[status_key]
        pct = count / total * 100 if total > 0 else 0
        print(f"    {label:<15s}: {count:5d} ({pct:5.1f}%)")
    print()
    if page_counts:
        print(f"  Page count statistics (parsed rows only):")
        print(f"    min:    {pc_min}")
        print(f"    median: {pc_median}")
        print(f"    mean:   {pc_mean:.1f}")
        print(f"    max:    {pc_max}")
    print(f"\n  Output: {output_path}")


if __name__ == "__main__":
    main()
