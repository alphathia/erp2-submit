"""Phase 6 trace checker — verifies coverage invariants across trustworthiness docs.

Design: `task6_tracker.md §3.7`; invoked by `code/dod_checks.py::check_phase6_task6_1`.

The six invariants:
    1. confirmability_annex.md mentions >=2 distinct passage IDs per mode 1-5.
    2. Every is_gap=True (capability_id, sdlc_activity) pair appears in
       confirmability_annex.md OR dependability_audit.md.
    3. credibility_statement.md has all 6 Wieringa criterion sub-headings.
    4. threshold_sensitivity.md mentions P20, P25, P33, P40.
    5. transferability.md names >=7 boundary condition sub-sections.
    6. contribution_novelty.md references all 4 research objectives AND all
       3 reference surveys ([9], [15], [16]).

Utility functions are exported so the DoD function in dod_checks.py can call
each check individually and aggregate results.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRUSTWORTHINESS = ROOT / "artifacts" / "trustworthiness"

PASSAGE_ID_RE = re.compile(r"doi:[^\s,\)`]+:P\d{3}")
MODE_HEADING_RE = re.compile(r"^### Mode (\d) ", re.MULTILINE)
WIERINGA_CRITERIA = [
    "Problem clarity",
    "Causal / logical property clarity",
    "Method soundness",
    "Knowledge claim validity",
    "Significance of lessons",
    "Related work",
]
REQUIRED_THRESHOLDS = ["P20", "P25", "P33", "P40"]
REFERENCE_SURVEY_IDS = ["[9]", "[15]", "[16]"]
RESEARCH_OBJECTIVES = [
    # Match on distinctive phrase fragments from proposal §1.3 / contribution_novelty.md
    "landscape",
    "interaction",  # mode taxonomy
    "gap",          # gap analysis
    "agenda",       # research agenda
]


# ---------------------------------------------------------------------------
# Invariant 1 — confirmability: passage IDs per mode
# ---------------------------------------------------------------------------

def check_confirmability_mode_traces() -> tuple[bool, str]:
    path = TRUSTWORTHINESS / "confirmability_annex.md"
    if not path.exists():
        return False, f"missing file: {path}"
    text = path.read_text(encoding="utf-8")
    # Split by mode headings; one section per mode
    sections = re.split(r"^### Mode (\d) ", text, flags=re.MULTILINE)
    # sections[0] = preamble; then pairs of (mode_num, body)
    mode_passage_counts: dict[str, int] = {}
    for i in range(1, len(sections), 2):
        if i + 1 >= len(sections):
            break
        mode_num = sections[i]
        body = sections[i + 1]
        ids = set(PASSAGE_ID_RE.findall(body))
        mode_passage_counts[mode_num] = len(ids)
    missing = [m for m in ("1", "2", "3", "4", "5") if mode_passage_counts.get(m, 0) < 2]
    if missing:
        return False, (
            f"confirmability modes with <2 passage IDs: {missing}; "
            f"counts: {mode_passage_counts}"
        )
    return True, f"all 5 modes have >=2 passage IDs: {mode_passage_counts}"


# ---------------------------------------------------------------------------
# Invariant 2 — gap pair coverage
# ---------------------------------------------------------------------------

def check_gap_pair_coverage() -> tuple[bool, str]:
    gap_matrix_path = ROOT / "artifacts" / "analysis" / "rq3_gap_matrix" / "gap_matrix.csv"
    if not gap_matrix_path.exists():
        return False, f"missing file: {gap_matrix_path}"
    with open(gap_matrix_path) as f:
        gaps = [
            (row["capability_id"], row["sdlc_activity"])
            for row in csv.DictReader(f)
            if row["is_gap"] == "True"
        ]
    confirm_text = (TRUSTWORTHINESS / "confirmability_annex.md").read_text(
        encoding="utf-8"
    )
    depend_text = (TRUSTWORTHINESS / "dependability_audit.md").read_text(
        encoding="utf-8"
    )
    combined = confirm_text + "\n" + depend_text
    missing = []
    for cap, sdlc in gaps:
        if cap not in combined or sdlc not in combined:
            missing.append((cap, sdlc))
    if missing:
        return False, f"{len(missing)} gap pairs missing from confirmability+dependability: first 3: {missing[:3]}"
    return True, f"all {len(gaps)} gap pairs covered in confirmability+dependability"


# ---------------------------------------------------------------------------
# Invariant 3 — credibility Wieringa sub-headings
# ---------------------------------------------------------------------------

def check_credibility_wieringa() -> tuple[bool, str]:
    path = TRUSTWORTHINESS / "credibility_statement.md"
    if not path.exists():
        return False, f"missing file: {path}"
    text = path.read_text(encoding="utf-8")
    missing = [c for c in WIERINGA_CRITERIA if c not in text]
    if missing:
        return False, f"credibility missing Wieringa criteria: {missing}"
    return True, "all 6 Wieringa criteria present"


# ---------------------------------------------------------------------------
# Invariant 4 — threshold sensitivity names all 4 percentiles
# ---------------------------------------------------------------------------

def check_threshold_sensitivity() -> tuple[bool, str]:
    path = TRUSTWORTHINESS / "threshold_sensitivity.md"
    if not path.exists():
        return False, f"missing file: {path}"
    text = path.read_text(encoding="utf-8")
    missing = [t for t in REQUIRED_THRESHOLDS if t not in text]
    if missing:
        return False, f"threshold_sensitivity missing: {missing}"
    return True, f"all 4 thresholds mentioned: {REQUIRED_THRESHOLDS}"


# ---------------------------------------------------------------------------
# Invariant 5 — transferability boundary count
# ---------------------------------------------------------------------------

def check_transferability_boundaries() -> tuple[bool, str]:
    path = TRUSTWORTHINESS / "transferability.md"
    if not path.exists():
        return False, f"missing file: {path}"
    text = path.read_text(encoding="utf-8")
    boundary_re = re.compile(r"^## Boundary \d", re.MULTILINE)
    count = len(boundary_re.findall(text))
    if count < 7:
        return False, f"transferability has only {count} Boundary N sub-sections (need >=7)"
    return True, f"{count} boundary sub-sections (>=7 required)"


# ---------------------------------------------------------------------------
# Invariant 6 — contribution & novelty covers 4 objectives + 3 surveys
# ---------------------------------------------------------------------------

def check_contribution_novelty() -> tuple[bool, str]:
    path = TRUSTWORTHINESS / "contribution_novelty.md"
    if not path.exists():
        return False, f"missing file: {path}"
    text = path.read_text(encoding="utf-8")
    missing_surveys = [s for s in REFERENCE_SURVEY_IDS if s not in text]
    missing_objectives = [o for o in RESEARCH_OBJECTIVES if o not in text.lower()]
    errs = []
    if missing_surveys:
        errs.append(f"missing surveys: {missing_surveys}")
    if missing_objectives:
        errs.append(f"missing objective keywords: {missing_objectives}")
    if errs:
        return False, "; ".join(errs)
    return True, f"all 3 surveys + 4 objective keywords present"


# ---------------------------------------------------------------------------
# Orchestrator — run all 6 invariants and report
# ---------------------------------------------------------------------------

def run_all() -> tuple[bool, list[tuple[str, bool, str]]]:
    checks = [
        ("1. confirmability_annex — >=2 passage IDs per mode 1-5", check_confirmability_mode_traces),
        ("2. gap pairs — every is_gap appears in confirmability+dependability", check_gap_pair_coverage),
        ("3. credibility_statement — all 6 Wieringa criteria present", check_credibility_wieringa),
        ("4. threshold_sensitivity — mentions P20, P25, P33, P40", check_threshold_sensitivity),
        ("5. transferability — >=7 boundary sub-sections", check_transferability_boundaries),
        ("6. contribution_novelty — 3 surveys + 4 objective keywords", check_contribution_novelty),
    ]
    results = []
    overall_ok = True
    for name, fn in checks:
        ok, msg = fn()
        results.append((name, ok, msg))
        if not ok:
            overall_ok = False
    return overall_ok, results


if __name__ == "__main__":
    ok, results = run_all()
    for name, passed, msg in results:
        mark = "✓" if passed else "✗"
        print(f"  {mark} {name}")
        print(f"      {msg}")
    if ok:
        print("\n✓ phase6_task6_1: all 6 trace-checker invariants pass.")
    else:
        print("\n✗ phase6_task6_1: one or more invariants FAILED.")
        raise SystemExit(1)
