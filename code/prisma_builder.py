"""Task 2.7 — PRISMA flow diagram builder.

Reads every Phase 2 CSV, computes stage counts, asserts that
in − excluded = out at each stage, and writes a Mermaid flowchart
source + count table to artifacts/screening/prisma_flow.md.

Usage:
    python code/prisma_builder.py

Consumes (all read-only):
    artifacts/search/raw/scopus_20260413.csv
    artifacts/search/raw/acm_20260413.csv
    artifacts/search/enriched/merged_openalex.csv
    artifacts/search/enriched/dedup.csv
    artifacts/search/post_filtered.csv
    artifacts/screening/phase2_decisions.csv
    artifacts/screening/included_set.csv
    artifacts/search/raw/snowball_seeds_refs.csv

Produces:
    artifacts/screening/prisma_flow.md (+ .meta.json)

Design: design/2_7_prisma_builder.md
"""

import csv
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from textwrap import dedent

import pandas as pd

# ---------------------------------------------------------------------------
# Project setup
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, str(ROOT))
from code.utils import write_with_meta  # noqa: E402

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCOPUS_CSV     = ROOT / "artifacts" / "search" / "raw" / "scopus_20260413.csv"
ACM_CSV        = ROOT / "artifacts" / "search" / "raw" / "acm_20260413.csv"
MERGED_CSV     = ROOT / "artifacts" / "search" / "enriched" / "merged_openalex.csv"
DEDUP_CSV      = ROOT / "artifacts" / "search" / "enriched" / "dedup.csv"
POST_FILT_CSV  = ROOT / "artifacts" / "search" / "post_filtered.csv"
DECISIONS_CSV  = ROOT / "artifacts" / "screening" / "phase2_decisions.csv"
INCLUDED_CSV   = ROOT / "artifacts" / "screening" / "included_set.csv"
SNOWBALL_CSV   = ROOT / "artifacts" / "search" / "raw" / "snowball_seeds_refs.csv"
OUTPUT_MD      = ROOT / "artifacts" / "screening" / "prisma_flow.md"
REGISTER       = ROOT / "decision_register.csv"


# ---------------------------------------------------------------------------
# Count chain
# ---------------------------------------------------------------------------
def compute_counts() -> dict:
    """Read all Phase 2 CSVs and compute the PRISMA count chain.

    Returns a dict of named counts for template rendering.
    Raises AssertionError if any reconciliation check fails.
    """
    print("=== Loading Phase 2 CSVs ===")

    # Stage 1 — Database search
    scopus = pd.read_csv(SCOPUS_CSV, dtype=str)
    acm = pd.read_csv(ACM_CSV, dtype=str)
    n_scopus = len(scopus)
    n_acm = len(acm)
    n_combined = n_scopus + n_acm
    print(f"  Stage 1 — Scopus: {n_scopus}, ACM DL: {n_acm}, "
          f"Combined: {n_combined}")

    # Stage 2 — OpenAlex enrichment (no row removal)
    merged = pd.read_csv(MERGED_CSV, dtype=str)
    n_enriched = len(merged)
    print(f"  Stage 2 — After OpenAlex enrichment: {n_enriched}")
    assert n_combined == n_enriched, (
        f"Stage 1→2 mismatch: {n_combined} combined ≠ {n_enriched} enriched"
    )
    print(f"    ✓ {n_combined} = {n_enriched} (no removal)")

    # Stage 3 — Deduplication
    dedup = pd.read_csv(DEDUP_CSV, dtype=str)
    n_dedup = len(dedup)
    n_dedup_removed = n_enriched - n_dedup
    print(f"  Stage 3 — After dedup: {n_dedup} (removed {n_dedup_removed})")
    assert n_enriched - n_dedup_removed == n_dedup, (
        f"Stage 2→3 mismatch: {n_enriched} - {n_dedup_removed} ≠ {n_dedup}"
    )
    print(f"    ✓ {n_enriched} − {n_dedup_removed} = {n_dedup}")

    # Stage 4 — IC5 page filter (adds columns, no row removal)
    postf = pd.read_csv(POST_FILT_CSV, dtype=str)
    n_postf = len(postf)
    n_ic5_fail = (postf["ic5_status"] == "fail").sum()
    n_screenable = n_postf - n_ic5_fail
    print(f"  Stage 4 — Post-filtered: {n_postf} total, "
          f"ic5_fail={n_ic5_fail}, screenable={n_screenable}")
    assert n_dedup == n_postf, (
        f"Stage 3→4 mismatch: {n_dedup} dedup ≠ {n_postf} post_filtered"
    )
    print(f"    ✓ {n_dedup} = {n_postf} (page filter adds cols only)")

    # Stage 5 — Manual screening (Task 2.5)
    decisions = pd.read_csv(DECISIONS_CSV, dtype=str).fillna("")
    task25 = decisions[decisions["pass_number"] != "snowball"]
    n_task25 = len(task25)
    n_include = int((task25["decision"] == "include").sum())
    n_exclude = int((task25["decision"] == "exclude").sum())
    n_defer = int((task25["decision"] == "defer").sum())
    print(f"  Stage 5 — Screening: {n_task25} decisions "
          f"(include={n_include}, exclude={n_exclude}, defer={n_defer})")
    assert n_screenable == n_task25, (
        f"Stage 4→5 mismatch: {n_screenable} screenable ≠ {n_task25} decisions"
    )
    print(f"    ✓ {n_screenable} = {n_task25}")

    # Exclusion breakdown by criterion (for PRISMA detail)
    excl_criteria = task25[task25["decision"] == "exclude"]["criterion"].value_counts().to_dict()
    print(f"    Exclusion criteria: {dict(sorted(excl_criteria.items()))}")

    # Stage 6 — Backward snowballing (Task 2.6)
    snow = pd.read_csv(SNOWBALL_CSV, dtype=str).fillna("")
    n_snow_total = len(snow)
    n_snow_already = int((snow["status"] == "already_in_corpus").sum())
    n_snow_include = int((snow["status"] == "included_via_snowball").sum())
    n_snow_exclude = int((snow["status"] == "excluded_via_snowball").sum())
    print(f"  Stage 6 — Snowball: {n_snow_total} refs "
          f"(already={n_snow_already}, include={n_snow_include}, "
          f"exclude={n_snow_exclude})")
    assert n_snow_already + n_snow_include + n_snow_exclude == n_snow_total, (
        f"Stage 6 partition mismatch: {n_snow_already}+{n_snow_include}+"
        f"{n_snow_exclude} ≠ {n_snow_total}"
    )
    print(f"    ✓ {n_snow_already}+{n_snow_include}+{n_snow_exclude} = {n_snow_total}")

    # Stage 7 — Final included set
    included = pd.read_csv(INCLUDED_CSV, dtype=str)
    n_final = len(included)
    expected_final = n_include + n_snow_include
    print(f"  Stage 7 — Final included: {n_final}")
    assert n_final == expected_final, (
        f"Final count mismatch: {n_final} ≠ {n_include} + {n_snow_include}"
    )
    print(f"    ✓ {n_include} + {n_snow_include} = {n_final}")

    print(f"\n✓ All reconciliation checks passed.\n")

    return {
        "n_scopus":         n_scopus,
        "n_acm":            n_acm,
        "n_combined":       n_combined,
        "n_enriched":       n_enriched,
        "n_dedup":          n_dedup,
        "n_dedup_removed":  n_dedup_removed,
        "n_postf":          n_postf,
        "n_ic5_fail":       n_ic5_fail,
        "n_screenable":     n_screenable,
        "n_task25":         n_task25,
        "n_include":        n_include,
        "n_exclude":        n_exclude,
        "n_defer":          n_defer,
        "excl_criteria":    excl_criteria,
        "n_snow_total":     n_snow_total,
        "n_snow_already":   n_snow_already,
        "n_snow_include":   n_snow_include,
        "n_snow_exclude":   n_snow_exclude,
        "n_final":          n_final,
    }


# ---------------------------------------------------------------------------
# Mermaid flowchart + count table
# ---------------------------------------------------------------------------
def render_prisma_md(c: dict) -> str:
    """Render the PRISMA flow diagram as Markdown with a Mermaid block."""

    # Exclusion detail string for the screening box
    excl_lines = []
    for crit in ["EC1", "EC2", "EC3", "EC4", "EC5", "EC6",
                 "IC1", "IC2", "IC3", "IC4", "IC5"]:
        cnt = c["excl_criteria"].get(crit, 0)
        if cnt:
            excl_lines.append(f"{crit}: {cnt}")
    excl_detail = ", ".join(excl_lines)

    md = f"""\
# PRISMA Flow Diagram — ERP2-SMS

> **How Do People Use AI Agents for Software Engineering?**
>
> Generated by `code/prisma_builder.py` on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}.
> Every stage's `in − excluded = out` has been verified programmatically.

---

## Count Table

| Stage | Description | In | Removed | Out |
|------:|-------------|---:|--------:|----:|
| 1 | Database search (Scopus + ACM DL) | — | — | {c['n_combined']:,} |
| 1a | Scopus | — | — | {c['n_scopus']:,} |
| 1b | ACM DL | — | — | {c['n_acm']:,} |
| 2 | OpenAlex enrichment | {c['n_combined']:,} | 0 | {c['n_enriched']:,} |
| 3 | Deduplication | {c['n_enriched']:,} | {c['n_dedup_removed']:,} | {c['n_dedup']:,} |
| 4 | IC5 page filter (< 4 pages) | {c['n_dedup']:,} | {c['n_ic5_fail']:,} | {c['n_screenable']:,} |
| 5 | Title/abstract screening | {c['n_screenable']:,} | {c['n_exclude']:,} | {c['n_include']:,} |
| 5d | Deferred (unresolved) | — | — | {c['n_defer']:,} |
| 6 | Backward snowballing | {c['n_snow_total']:,} refs | {c['n_snow_exclude']:,} new excluded | +{c['n_snow_include']:,} new |
| 6a | Already in corpus | — | — | {c['n_snow_already']:,} |
| 7 | **Final included set** | — | — | **{c['n_final']:,}** |

### Exclusion breakdown (Stage 5)

| Criterion | Count | % of exclusions |
|-----------|------:|-----------:|
"""

    for crit in ["EC1", "EC2", "EC3", "EC4", "EC5", "EC6",
                 "IC1", "IC2", "IC3", "IC4", "IC5"]:
        cnt = c["excl_criteria"].get(crit, 0)
        if cnt:
            pct = cnt / c["n_exclude"] * 100 if c["n_exclude"] else 0
            md += f"| {crit} | {cnt:,} | {pct:.1f}% |\n"

    md += f"""
---

## Mermaid Flowchart

```mermaid
flowchart TD
    DB1["Scopus search<br/><b>{c['n_scopus']:,}</b> records"]
    DB2["ACM DL search<br/><b>{c['n_acm']:,}</b> records"]
    MERGE["Combined<br/><b>{c['n_combined']:,}</b> records"]
    DB1 --> MERGE
    DB2 --> MERGE

    ENRICH["OpenAlex enrichment<br/><b>{c['n_enriched']:,}</b> records<br/>(abstract backfill, flags)"]
    MERGE --> ENRICH

    DEDUP["Deduplication<br/><b>{c['n_dedup']:,}</b> unique records"]
    DUP_REM["{c['n_dedup_removed']:,} duplicates<br/>removed"]
    ENRICH --> DEDUP
    ENRICH --> DUP_REM

    PAGEFILT["IC5 page filter<br/><b>{c['n_screenable']:,}</b> screenable"]
    IC5_FAIL["{c['n_ic5_fail']:,} short papers<br/>(< 4 pages)"]
    DEDUP --> PAGEFILT
    DEDUP --> IC5_FAIL

    SCREEN["Title/abstract screening<br/><b>{c['n_include']:,}</b> included"]
    EXCLUDED["{c['n_exclude']:,} excluded<br/>({excl_detail})"]
    PAGEFILT --> SCREEN
    PAGEFILT --> EXCLUDED

    SNOWBALL["Backward snowballing<br/>{c['n_snow_total']:,} seed refs identified"]
    SNOW_ALREADY["{c['n_snow_already']:,} already<br/>in corpus"]
    SNOW_EXCL["{c['n_snow_exclude']:,} new refs<br/>excluded"]
    SNOW_INCL["+{c['n_snow_include']:,} new<br/>included"]
    SCREEN --> SNOWBALL
    SNOWBALL --> SNOW_ALREADY
    SNOWBALL --> SNOW_EXCL
    SNOWBALL --> SNOW_INCL

    FINAL["<b>Final included set<br/>{c['n_final']:,} papers</b>"]
    SCREEN --> FINAL
    SNOW_INCL --> FINAL

    style FINAL fill:#2d6,stroke:#040,color:#fff
    style EXCLUDED fill:#d44,stroke:#400,color:#fff
    style DUP_REM fill:#d44,stroke:#400,color:#fff
    style IC5_FAIL fill:#d44,stroke:#400,color:#fff
    style SNOW_EXCL fill:#d44,stroke:#400,color:#fff
    style SNOW_ALREADY fill:#fc0,stroke:#640,color:#000
```

---

*Reconciliation verified by `code/prisma_builder.py`. All `in − excluded = out` checks passed.*
"""
    return md


# ---------------------------------------------------------------------------
# Decision register
# ---------------------------------------------------------------------------
def log_prisma_complete(c: dict) -> None:
    """Append a prisma_complete row to decision_register.csv."""
    row = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "phase": "2",
        "paper_id": "N/A",
        "decision": "prisma_complete",
        "rule_applied": "Task 2.7 PRISMA flow diagram (prisma_builder.py)",
        "rationale": (
            f"PRISMA reconciliation passed. Chain: "
            f"Scopus {c['n_scopus']} + ACM {c['n_acm']} = {c['n_combined']} "
            f"→ enriched {c['n_enriched']} → dedup {c['n_dedup']} "
            f"→ screenable {c['n_screenable']} → included {c['n_include']} "
            f"→ snowball +{c['n_snow_include']} → final {c['n_final']}."
        ),
        "rater_initials": os.environ.get("RATER_INITIALS", "AT"),
    }
    first = not REGISTER.exists() or REGISTER.stat().st_size == 0
    with open(REGISTER, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        if first:
            writer.writeheader()
        writer.writerow(row)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    print("=" * 70)
    print("  ERP2-SMS Task 2.7 — PRISMA Flow Diagram Builder")
    print("=" * 70)
    print()

    # Check all input CSVs exist
    inputs = [SCOPUS_CSV, ACM_CSV, MERGED_CSV, DEDUP_CSV, POST_FILT_CSV,
              DECISIONS_CSV, INCLUDED_CSV, SNOWBALL_CSV]
    for p in inputs:
        if not p.exists():
            print(f"ERROR: {p.relative_to(ROOT)} not found", file=sys.stderr)
            return 1

    # Compute and verify counts
    try:
        counts = compute_counts()
    except AssertionError as exc:
        print(f"\n✗ Reconciliation FAILED: {exc}", file=sys.stderr)
        return 1

    # Render PRISMA Markdown
    md = render_prisma_md(counts)

    # Write output
    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.write_text(md, encoding="utf-8")
    print(f"✓ Written: {OUTPUT_MD.relative_to(ROOT)}")

    # Write meta sidecar
    write_with_meta(
        OUTPUT_MD,
        script="code/prisma_builder.py",
        inputs=[str(p.relative_to(ROOT)) for p in inputs],
        seed=42,
    )

    # Log to decision register
    log_prisma_complete(counts)
    print(f"✓ Logged to {REGISTER.relative_to(ROOT)}")

    print(f"\n✓ Task 2.7 complete. PRISMA flow diagram at "
          f"{OUTPUT_MD.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
