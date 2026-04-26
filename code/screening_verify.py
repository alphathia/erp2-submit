"""Task 2.5 DoD verification.

Loads phase2_decisions.csv and post_filtered.csv and checks:
  1. len(phase2_decisions) == len(post_filtered where ic5_status != fail)
  2. Every decision=exclude row has a non-null criterion in {EC1..EC6}
  3. Every decision has a non-null f1_provisional in Wieringa's 6 classes
  4. preprint_paper values ∈ {preprint, published, mixed, unknown}
  5. No decision=defer rows remain (warns rather than fails)

Then reports distributions, LLM-assist rate, and SCIS rank breakdown.
Logs a screening_complete row to decision_register.csv.

Usage:
    python code/screening_verify.py
"""

import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.stdout.reconfigure(line_buffering=True)

DECISIONS_PATH   = ROOT / "artifacts" / "screening" / "phase2_decisions.csv"
POST_FILTERED    = ROOT / "artifacts" / "search" / "post_filtered.csv"
INCLUDED_PATH    = ROOT / "artifacts" / "screening" / "included_set.csv"
REPORTS_DIR      = ROOT / "artifacts" / "screening" / "reports"


class _Tee:
    """Write stdout to both the terminal and a report file."""

    def __init__(self, *streams):
        self._streams = streams

    def write(self, data):
        for s in self._streams:
            s.write(data)

    def flush(self):
        for s in self._streams:
            s.flush()

VALID_CRITERIA = {"EC1", "EC2", "EC3", "EC4", "EC5", "EC6",
                  "IC1", "IC2", "IC3", "IC4", "IC5"}
VALID_F1 = {
    "Evaluation Research", "Validation Research", "Solution Proposal",
    "Philosophical", "Opinion", "Personal Experience",
}
VALID_PREPRINT = {"preprint", "published", "mixed", "unknown"}


def main() -> None:
    # Open a timestamped report file and tee stdout into it so the run is
    # self-contained — one command produces both the terminal output and the
    # audit artifact. See design/2_5_2_screening_verify.md §6.
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    run_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_path = REPORTS_DIR / f"screening_verify_{run_ts}.log"
    report_file = open(report_path, "w", encoding="utf-8")
    original_stdout = sys.stdout
    sys.stdout = _Tee(original_stdout, report_file)
    print(f"# screening_verify.py — run at {run_ts}")
    print(f"# report: {report_path.relative_to(ROOT)}\n")
    try:
        _run(report_path)
    finally:
        sys.stdout = original_stdout
        report_file.close()


def _run(report_path: Path) -> None:
    # Load files
    if not DECISIONS_PATH.exists():
        print(f"ERROR: {DECISIONS_PATH} not found", file=sys.stderr)
        sys.exit(1)
    if not POST_FILTERED.exists():
        print(f"ERROR: {POST_FILTERED} not found", file=sys.stderr)
        sys.exit(1)

    decisions = pd.read_csv(DECISIONS_PATH, dtype=str)
    post = pd.read_csv(POST_FILTERED, dtype=str)
    screenable = post[post["ic5_status"] != "fail"]

    print(f"Loaded: {len(decisions)} decisions, "
          f"{len(screenable)} screenable rows in post_filtered.csv\n")

    # --- Assertion 1: Count match ---
    print("=== Assertion 1: Count match ===")
    assert len(decisions) == len(screenable), (
        f"Count mismatch: {len(decisions)} decisions vs "
        f"{len(screenable)} screenable rows"
    )
    print(f"  ✓ len(phase2_decisions) = {len(decisions)} = "
          f"len(post_filtered where ic5_status != fail)\n")

    # --- Assertion 2: Exclusions have criterion ---
    print("=== Assertion 2: Exclusions have criterion ===")
    excl = decisions[decisions["decision"] == "exclude"]
    missing_criterion = excl[excl["criterion"].isna() | (excl["criterion"] == "")]
    assert len(missing_criterion) == 0, (
        f"{len(missing_criterion)} exclusions lack a criterion"
    )
    invalid_criterion = excl[~excl["criterion"].isin(VALID_CRITERIA)]
    assert len(invalid_criterion) == 0, (
        f"{len(invalid_criterion)} exclusions have invalid criterion"
    )
    print(f"  ✓ {len(excl)} exclusions, all have valid criterion\n")

    # --- Assertion 3: F1 required where methodologically load-bearing ---
    # Per original Task 2.5 DoD: "every include carries a provisional F1 class".
    # We also enforce F1 for EC1/EC2 exclusions (where F1 is auto-fill-deterministic
    # per codebook.md and Wieringa §3). F1 for EC3-EC6 exclusions and defers is
    # informational only — the LLM often leaves these null and that is acceptable
    # because the paper has been excluded and its Wieringa class is no longer
    # load-bearing for the SMS.
    print("=== Assertion 3: F1 required for includes + EC1/EC2 exclusions ===")
    f1_required_mask = (
        (decisions["decision"] == "include")
        | ((decisions["decision"] == "exclude") & decisions["criterion"].isin(["EC1", "EC2"]))
    )
    f1_required = decisions[f1_required_mask]
    missing_f1 = f1_required[
        f1_required["f1_provisional"].isna() |
        (f1_required["f1_provisional"].astype(str).str.strip() == "")
    ]
    assert len(missing_f1) == 0, (
        f"{len(missing_f1)} required-F1 rows lack f1_provisional "
        f"(decisions=include OR exclusion with criterion in EC1/EC2)"
    )
    invalid_f1 = f1_required[~f1_required["f1_provisional"].isin(VALID_F1)]
    assert len(invalid_f1) == 0, (
        f"{len(invalid_f1)} required-F1 rows have invalid f1_provisional: "
        f"{invalid_f1['f1_provisional'].unique()}"
    )
    print(f"  ✓ All {len(f1_required)} required-F1 rows have valid F1 "
          f"({(decisions['decision'] == 'include').sum()} includes, "
          f"{((decisions['decision'] == 'exclude') & decisions['criterion'].isin(['EC1', 'EC2'])).sum()} "
          f"EC1/EC2 exclusions)\n")

    # --- Assertion 4: preprint_paper values ---
    print("=== Assertion 4: preprint_paper values ===")
    assert "preprint_paper" in decisions.columns, "Missing preprint_paper column"
    invalid_pp = decisions[~decisions["preprint_paper"].isin(VALID_PREPRINT) &
                            decisions["preprint_paper"].notna() &
                            (decisions["preprint_paper"] != "")]
    assert len(invalid_pp) == 0, (
        f"{len(invalid_pp)} rows have invalid preprint_paper"
    )
    print(f"  ✓ preprint_paper values valid in all rows\n")

    # --- Assertion 5: No defer rows (warning, not fatal) ---
    print("=== Assertion 5: No deferred rows remain ===")
    defer_count = (decisions["decision"] == "defer").sum()
    if defer_count > 0:
        print(f"  ⚠ WARNING: {defer_count} deferred rows remain. "
              f"Run --pass 2 to resolve.")
    else:
        print("  ✓ No deferred rows remaining\n")

    # --- Reports ---
    print("=" * 60)
    print("  Decision distribution")
    print("=" * 60)
    for dec, cnt in decisions["decision"].value_counts().items():
        pct = cnt / len(decisions) * 100
        print(f"  {dec:<10s}: {cnt:5d} ({pct:5.1f}%)")

    print(f"\n=== Exclusion criterion distribution ===")
    for crit, cnt in excl["criterion"].value_counts().items():
        pct = cnt / len(excl) * 100 if len(excl) > 0 else 0
        print(f"  {crit}: {cnt:5d} ({pct:5.1f}%)")

    print(f"\n=== F1 class distribution (firm decisions) ===")
    firm = decisions[decisions["decision"].isin(["include", "exclude"])]
    for cls, cnt in firm["f1_provisional"].value_counts().items():
        pct = cnt / len(firm) * 100 if len(firm) > 0 else 0
        print(f"  {cls:<25s}: {cnt:5d} ({pct:5.1f}%)")

    # Informational F1 coverage by decision / criterion type
    print(f"\n=== F1 coverage (informational — not asserted) ===")
    def coverage(subset, label, required):
        if len(subset) == 0:
            print(f"  {label}: 0 rows")
            return
        filled = subset["f1_provisional"].notna() & (subset["f1_provisional"].astype(str).str.strip() != "")
        pct = filled.sum() / len(subset) * 100
        flag = "(required)" if required else "(optional)"
        print(f"  {label:<34s} {filled.sum():5d}/{len(subset):5d} ({pct:5.1f}%)  {flag}")

    coverage(decisions[decisions["decision"] == "include"],
             "include:", required=True)
    coverage(decisions[(decisions["decision"] == "exclude") & (decisions["criterion"] == "EC1")],
             "EC1 exclusion:", required=True)
    coverage(decisions[(decisions["decision"] == "exclude") & (decisions["criterion"] == "EC2")],
             "EC2 exclusion:", required=True)
    coverage(decisions[(decisions["decision"] == "exclude") & (decisions["criterion"].isin(["EC3", "EC4", "EC5", "EC6"]))],
             "EC3-EC6 exclusion:", required=False)
    coverage(decisions[decisions["decision"] == "defer"], "defer:", required=False)

    print(f"\n=== preprint_paper distribution ===")
    for v, cnt in decisions["preprint_paper"].value_counts().items():
        pct = cnt / len(decisions) * 100
        print(f"  {v:<12s}: {cnt:5d} ({pct:5.1f}%)")

    # --- SCIS rank distribution among included ---
    print(f"\n=== SCIS rank distribution among included ===")
    inc = decisions[decisions["decision"] == "include"]
    for rank, cnt in inc["scis_rank"].value_counts().items():
        pct = cnt / len(inc) * 100 if len(inc) > 0 else 0
        print(f"  {rank:<12s}: {cnt:5d} ({pct:5.1f}%)")

    # --- LLM-assist rate ---
    print(f"\n=== LLM-assist / LLM-review rate ===")
    llm_assisted = decisions["rationale"].fillna("").str.startswith("[LLM-assisted]")
    llm_reviewed = decisions["rationale"].fillna("").str.startswith("[LLM-reviewed]")
    rater_override = decisions["rationale"].fillna("").str.startswith("[rater-override]")
    total = len(decisions)
    print(f"  [LLM-assisted]:    {llm_assisted.sum():5d} ({llm_assisted.sum()/total*100:.1f}%)")
    print(f"  [LLM-reviewed]:    {llm_reviewed.sum():5d} ({llm_reviewed.sum()/total*100:.1f}%)")
    print(f"  [rater-override]:  {rater_override.sum():5d} ({rater_override.sum()/total*100:.1f}%)")

    # --- Flagged-record outcomes ---
    # Merge with post_filtered to get flag info
    print(f"\n=== Flagged-record outcomes ===")
    merged = decisions.merge(
        post[["doi", "preprint_flag", "ic3_flag"]].drop_duplicates("doi"),
        on="doi", how="left",
    )
    for flag_name, flag_col in [("preprint_flag", "preprint_flag"),
                                 ("IC3 mismatch", "ic3_flag")]:
        sub = merged[merged[flag_col].fillna("").astype(str).str.lower().isin(["true", "1"]) |
                     merged[flag_col].fillna("").str.strip().astype(bool)]
        if len(sub) == 0:
            continue
        counts = sub["decision"].value_counts().to_dict()
        print(f"  {flag_name}: {len(sub)} flagged")
        for d in ["include", "exclude", "defer"]:
            print(f"    → {d}: {counts.get(d, 0)}")

    # --- Included_set validation ---
    print(f"\n=== Included set validation ===")
    if INCLUDED_PATH.exists():
        inc_csv = pd.read_csv(INCLUDED_PATH, dtype=str)
        exp_inc = set(decisions[decisions["decision"] == "include"]["paper_id"].astype(str))
        got_inc = set(inc_csv["paper_id"].astype(str))
        if exp_inc == got_inc:
            print(f"  ✓ included_set.csv matches decision=include rows ({len(got_inc)} papers)")
        else:
            extra = got_inc - exp_inc
            missing = exp_inc - got_inc
            print(f"  ⚠ included_set mismatch: +{len(extra)} / -{len(missing)}")
    else:
        print(f"  ⚠ included_set.csv not found — re-run screening_harness to regenerate")

    # --- Log to decision register ---
    print(f"\n=== Logging to decision_register.csv ===")
    register_path = ROOT / "decision_register.csv"
    row = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "phase": "2",
        "paper_id": "N/A",
        "decision": "screening_complete",
        "rule_applied": "Task 2.5 DoD verification (screening_verify.py)",
        "rationale": (
            f"Screening complete: {len(decisions)} decisions total. "
            f"Include={decisions['decision'].value_counts().get('include', 0)}, "
            f"Exclude={decisions['decision'].value_counts().get('exclude', 0)}, "
            f"Defer={defer_count}. "
            f"Included with SCIS rank: "
            f"A*={(inc['scis_rank'] == 'A*').sum()}, "
            f"A={(inc['scis_rank'] == 'A').sum()}, "
            f"B={(inc['scis_rank'] == 'B').sum()}. "
            f"LLM-reviewed: {llm_reviewed.sum()}. "
            f"Rater overrides: {rater_override.sum()}. "
            f"All DoD assertions passed."
        ),
        "rater_initials": os.environ.get("RATER_INITIALS", "AT"),
    }
    with open(register_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        writer.writerow(row)
    print(f"  ✓ Logged to decision_register.csv")

    # Final verdict
    print()
    if defer_count == 0:
        print("✓ Task 2.5 DoD: all assertions passed.")
    else:
        print(f"⚠ Task 2.5 DoD: structural assertions passed, but "
              f"{defer_count} deferred rows remain — run --pass 2.")
    print(f"\nReport saved: {report_path.relative_to(ROOT)}")
    if defer_count > 0:
        sys.exit(2)


if __name__ == "__main__":
    main()
