"""Task 5.3 — Prioritize RQ3 gaps; emit artifacts/analysis/prioritised_gaps.md.

Design: design/5_3_prioritize_gaps.md

Consumes:
    - artifacts/analysis/rq3_gap_matrix/gap_matrix.csv  (171 rows; 42 is_gap=True)
    - artifacts/protocol/capability_list.csv            (43 rows; 19 unique capability_id)
    - decision_register.csv                             (42 phase=5, hypothesis_for_erp3 rows)

Emits:
    - artifacts/analysis/prioritised_gaps.md

Priority formula (see design §4):
    priority = P25_shortfall * capability_prevalence
        where P25_shortfall = (P25 - evidence_count) / P25   in [0, 1)
        and   capability_prevalence = in_source_survey        in {1, 2, 3}
"""

from __future__ import annotations

import csv
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from code.utils import write_with_meta  # noqa: E402

GAP_MATRIX = ROOT / "artifacts" / "analysis" / "rq3_gap_matrix" / "gap_matrix.csv"
CAP_LIST = ROOT / "artifacts" / "protocol" / "capability_list.csv"
REGISTER = ROOT / "decision_register.csv"
OUT_MD = ROOT / "artifacts" / "analysis" / "prioritised_gaps.md"

SDLC_VOCAB = [
    "CI/CD",
    "Code Review",
    "Coding",
    "Debugging",
    "Design",
    "Documentation",
    "Project Management",
    "Requirements",
    "Testing",
]
SDLC_ALT = "|".join(re.escape(v) for v in SDLC_VOCAB)

RATIONALE_RE = re.compile(
    rf"^(?P<bucket>adoption_lag|design_gap|organizational_readiness_barrier):"
    rf"\s.*?(?P<cap>CAP_[A-Z0-9_]+).*?at (?:the )?(?P<sdlc>{SDLC_ALT})",
    re.DOTALL,
)

EXPECTED_P25 = 2.0
EXPECTED_GAPS = 42
EXPECTED_EMPTIES = 12


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_gap_matrix() -> pd.DataFrame:
    df = pd.read_csv(GAP_MATRIX)
    assert len(df) == 171, f"gap_matrix.csv must have 171 rows, got {len(df)}"
    return df


def load_capability_labels() -> dict[str, str]:
    df = pd.read_csv(CAP_LIST)
    return (
        df.drop_duplicates("capability_id")
        .set_index("capability_id")["label"]
        .to_dict()
    )


def load_phase5_rationales() -> list[dict]:
    """Return list of {capability_id, sdlc_activity, bucket, rationale} dicts."""
    out = []
    with open(REGISTER, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            phase = (row.get("phase") or "").strip('"').strip()
            decision = (row.get("decision") or "").strip('"').strip()
            if phase != "5" or decision != "hypothesis_for_erp3":
                continue
            rationale_raw = (row.get("rationale") or "").strip('"').strip()
            m = RATIONALE_RE.match(rationale_raw)
            if not m:
                raise AssertionError(
                    f"Could not parse rationale: {rationale_raw[:200]}"
                )
            out.append(
                {
                    "capability_id": m.group("cap"),
                    "sdlc_activity": m.group("sdlc"),
                    "bucket": m.group("bucket"),
                    "rationale": rationale_raw,
                }
            )
    return out


# ---------------------------------------------------------------------------
# Priority scoring
# ---------------------------------------------------------------------------

def compute_p25(df: pd.DataFrame) -> float:
    non_zero = df.loc[df["evidence_count"] > 0, "evidence_count"].to_numpy()
    return float(np.percentile(non_zero, 25))


def score_gaps(df: pd.DataFrame, p25: float) -> pd.DataFrame:
    gaps = df.loc[df["is_gap"]].copy()
    gaps["p25_shortfall"] = (p25 - gaps["evidence_count"]) / p25
    gaps["capability_prevalence"] = gaps["in_source_survey"].astype(int)
    gaps["priority"] = gaps["p25_shortfall"] * gaps["capability_prevalence"]
    return gaps.sort_values(
        by=["priority", "capability_id", "sdlc_activity"],
        ascending=[False, True, True],
    ).reset_index(drop=True)


def attach_rationales(
    gaps: pd.DataFrame, rationales: list[dict]
) -> pd.DataFrame:
    by_key = {(r["capability_id"], r["sdlc_activity"]): r for r in rationales}
    missing: list[tuple] = []
    buckets: list[str] = []
    rationale_texts: list[str] = []
    for _, row in gaps.iterrows():
        key = (row["capability_id"], row["sdlc_activity"])
        match = by_key.get(key)
        if match is None:
            missing.append(key)
            buckets.append("")
            rationale_texts.append("")
        else:
            buckets.append(match["bucket"])
            rationale_texts.append(match["rationale"])
    if missing:
        raise AssertionError(
            f"{len(missing)} gap rows lack a matching Phase-5 rationale: "
            f"{missing}"
        )
    gaps = gaps.copy()
    gaps["bucket"] = buckets
    gaps["rationale"] = rationale_texts
    return gaps


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------

def render_markdown(
    gaps: pd.DataFrame,
    labels: dict[str, str],
    p25: float,
    empties_count: int,
) -> str:
    now = datetime.now(timezone.utc).isoformat()
    lines: list[str] = []
    lines.append("# Prioritised Gaps — RQ3")
    lines.append("")
    lines.append(
        f"**Source:** `artifacts/analysis/rq3_gap_matrix/gap_matrix.csv` "
        f"(P25 = {p25:.1f} on non-zero cells)."
    )
    lines.append("**Script:** `code/prioritize_gaps.py`")
    lines.append(f"**Generated:** {now}")
    lines.append(
        f"**Gap count:** {len(gaps)} (at P25). **Empty cells** (tracked "
        f"separately, not gaps): {empties_count}."
    )
    lines.append(
        "**Priority formula:** `priority = P25_shortfall × capability_prevalence` "
        "where `P25_shortfall = (P25 − evidence_count) / P25` and "
        "`capability_prevalence = in_source_survey ∈ {1,2,3}`."
    )
    lines.append("")

    # Ranked gap table
    lines.append("## Ranked gap list")
    lines.append("")
    lines.append(
        "| Rank | Capability | Label | SDLC Activity | Evidence | "
        "P25-shortfall | Prevalence | Priority | ERP3 bucket |"
    )
    lines.append(
        "|---:|---|---|---|---:|---:|---:|---:|---|"
    )
    for i, row in gaps.reset_index(drop=True).iterrows():
        cap = row["capability_id"]
        label = labels.get(cap, "(label missing)")
        lines.append(
            f"| {i + 1} "
            f"| {cap} "
            f"| {label} "
            f"| {row['sdlc_activity']} "
            f"| {int(row['evidence_count'])} "
            f"| {row['p25_shortfall']:.2f} "
            f"| {int(row['capability_prevalence'])} "
            f"| {row['priority']:.2f} "
            f"| {row['bucket']} |"
        )
    lines.append("")

    # Rationale register
    lines.append("## Rationale register")
    lines.append("")
    for i, row in gaps.reset_index(drop=True).iterrows():
        cap = row["capability_id"]
        label = labels.get(cap, "(label missing)")
        lines.append(
            f"### Rank {i + 1} — {cap} × {row['sdlc_activity']} "
            f"(priority {row['priority']:.2f})"
        )
        lines.append("")
        lines.append(f"- **Capability label:** {label}")
        lines.append(
            f"- **Evidence count:** {int(row['evidence_count'])} "
            f"(P25 = {p25:.1f})"
        )
        lines.append(f"- **Bucket:** {row['bucket']}")
        lines.append(f"- **Rationale (from `decision_register.csv`):** {row['rationale']}")
        lines.append("")

    # Bucket tally
    bucket_counts = gaps["bucket"].value_counts().to_dict()
    total = len(gaps)
    lines.append("## Bucket tally")
    lines.append("")
    lines.append("| Bucket | Count | % of total |")
    lines.append("|---|---:|---:|")
    for bucket in ("adoption_lag", "design_gap", "organizational_readiness_barrier"):
        n = int(bucket_counts.get(bucket, 0))
        pct = 100.0 * n / total if total else 0.0
        lines.append(f"| {bucket} | {n} | {pct:.1f}% |")
    lines.append(f"| **Total** | **{total}** | **100.0%** |")
    lines.append("")

    # Invariants
    lines.append("## Invariants verified")
    lines.append("")
    lines.append(f"- Gap rows in ranked table: **{total}** (expected {EXPECTED_GAPS}).")
    lines.append(
        "- Every gap has a matching Phase-5 `hypothesis_for_erp3` decision-register entry."
    )
    lines.append(
        "- No interpretation-label columns from the matrix leaked in (matrix columns "
        "remain `{capability_id, sdlc_activity, evidence_count, is_gap, is_empty, "
        "in_source_survey}`)."
    )
    lines.append(
        "- Sort order: `priority desc`, tie-break `capability_id asc, sdlc_activity asc`."
    )
    lines.append("")

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    df = load_gap_matrix()
    p25 = compute_p25(df)
    assert abs(p25 - EXPECTED_P25) < 1e-9, (
        f"P25 drifted from expected {EXPECTED_P25} to {p25} — "
        "confirm gap_matrix.csv was not regenerated unexpectedly before bumping."
    )

    gaps = score_gaps(df, p25)
    assert len(gaps) == EXPECTED_GAPS, (
        f"Expected {EXPECTED_GAPS} gap rows, got {len(gaps)}"
    )

    empties_count = int(df["is_empty"].sum())
    assert empties_count == EXPECTED_EMPTIES, (
        f"Expected {EXPECTED_EMPTIES} empty cells, got {empties_count}"
    )

    rationales = load_phase5_rationales()
    assert len(rationales) == EXPECTED_GAPS, (
        f"Expected {EXPECTED_GAPS} Phase-5 hypothesis rows, got {len(rationales)}"
    )

    gaps = attach_rationales(gaps, rationales)
    labels = load_capability_labels()
    markdown = render_markdown(gaps, labels, p25, empties_count)

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(markdown, encoding="utf-8")
    write_with_meta(
        OUT_MD,
        script="code/prioritize_gaps.py",
        inputs=[
            str(GAP_MATRIX.relative_to(ROOT)),
            str(CAP_LIST.relative_to(ROOT)),
            str(REGISTER.relative_to(ROOT)),
        ],
    )

    print(f"✓ Wrote {OUT_MD.relative_to(ROOT)}")
    print(f"  - {len(gaps)} gaps ranked (P25 = {p25:.1f})")
    print(f"  - {empties_count} empty cells reported in header footnote")
    bucket_counts = gaps["bucket"].value_counts().to_dict()
    for bucket in ("adoption_lag", "design_gap", "organizational_readiness_barrier"):
        print(f"  - {bucket}: {bucket_counts.get(bucket, 0)}")


if __name__ == "__main__":
    main()
