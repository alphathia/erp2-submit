"""Task 5.2 — RQ3 capability × SDLC gap matrix.

Implements proposal §3.5 RQ3:
    Build a 19 capability × 9 SDLC activity matrix of distinct-paper evidence
    counts, flag gaps by the 25th-percentile-of-non-zero-cells rule, render a
    heatmap, emit a sensitivity narrative at P25 vs P33, split by tool paradigm,
    and append one hypothesis row to decision_register.csv per gap cell.

Design: design/5_2_analysis_rq3.md
"""

from __future__ import annotations

import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

# Make utils importable whether run as script or module.
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from utils import write_with_meta  # noqa: E402

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
CAP_ANNOT = ROOT / "artifacts" / "extraction" / "capability_annotations.csv"
CAP_LIST = ROOT / "artifacts" / "protocol" / "capability_list.csv"
EXTRACTION = ROOT / "artifacts" / "extraction" / "extraction_matrix.csv"

OUT_DIR = ROOT / "artifacts" / "analysis" / "rq3_gap_matrix"
OUT_MATRIX = OUT_DIR / "gap_matrix.csv"
OUT_HEATMAP = OUT_DIR / "gap_heatmap.png"
OUT_SENS = OUT_DIR / "sensitivity_25_33.md"
OUT_PARADIGM_DIR = OUT_DIR / "gap_matrix_by_paradigm"
OUT_PROCODE = OUT_PARADIGM_DIR / "procode.csv"
OUT_LOWCODE = OUT_PARADIGM_DIR / "lowcode.csv"
OUT_NOCODE = OUT_PARADIGM_DIR / "nocode.csv"

REGISTER = ROOT / "decision_register.csv"

# Canonical SDLC order per proposal §3.5.
SDLC_ORDER = [
    "Requirements",
    "Design",
    "Coding",
    "Testing",
    "Code Review",
    "Debugging",
    "Documentation",
    "CI/CD",
    "Project Management",
]

# Rationale label vocabulary.
DESIGN_GAP_CAPS = {"CAP_REQENG", "CAP_SYSDESIGN"}
ADOPTION_LAG_CAPS = {"CAP_MULTIAGENT", "CAP_PLANNING", "CAP_SELFREFLECT"}


# ---------------------------------------------------------------------------
# Matrix construction
# ---------------------------------------------------------------------------
def build_matrix(
    annotations: pd.DataFrame,
    extraction: pd.DataFrame,
    capability_ids: list[str],
    sdlc_activities: list[str],
) -> pd.DataFrame:
    """Return long-format (capability_id, sdlc_activity, evidence_count) frame.

    Inner-joins annotations to extraction, explodes pipe-separated
    f4_sdlc_activity, counts distinct papers per (capability_id, sdlc_activity),
    then zero-fills to the full 19×9 cartesian.
    """
    merged = annotations.merge(
        extraction[["paper_id", "f4_sdlc_activity"]],
        on="paper_id",
        how="inner",
    )
    # Drop rows with missing sdlc activity so str.split doesn't choke.
    merged = merged[merged["f4_sdlc_activity"].notna()].copy()
    merged["f4_sdlc_activity"] = merged["f4_sdlc_activity"].str.split("|")
    exploded = merged.explode("f4_sdlc_activity")
    exploded["f4_sdlc_activity"] = exploded["f4_sdlc_activity"].str.strip()

    grouped = (
        exploded.groupby(["capability_id", "f4_sdlc_activity"])["paper_id"]
        .nunique()
        .reset_index(name="evidence_count")
    )

    # Cartesian completion.
    grid = pd.MultiIndex.from_product(
        [capability_ids, sdlc_activities],
        names=["capability_id", "sdlc_activity"],
    ).to_frame(index=False)
    grouped = grouped.rename(columns={"f4_sdlc_activity": "sdlc_activity"})
    full = grid.merge(grouped, on=["capability_id", "sdlc_activity"], how="left")
    full["evidence_count"] = full["evidence_count"].fillna(0).astype(int)
    return full


def apply_flags(
    matrix: pd.DataFrame, threshold: float
) -> pd.DataFrame:
    """Add is_gap and is_empty columns given a P-threshold."""
    matrix = matrix.copy()
    matrix["is_gap"] = (matrix["evidence_count"] > 0) & (
        matrix["evidence_count"] <= threshold
    )
    matrix["is_empty"] = matrix["evidence_count"] == 0
    # Invariant: mutually exclusive.
    assert not (matrix["is_gap"] & matrix["is_empty"]).any(), (
        "Invariant violation: is_gap AND is_empty must be False in every cell"
    )
    return matrix


def compute_percentile(matrix: pd.DataFrame, p: float) -> float:
    non_zero = matrix.loc[matrix["evidence_count"] > 0, "evidence_count"].values
    if len(non_zero) == 0:
        return 0.0
    return float(np.percentile(non_zero, p))


def compute_in_source_survey(cap_list: pd.DataFrame) -> dict[str, int]:
    """Map capability_id -> count of distinct source_paper in capability_list."""
    return (
        cap_list.groupby("capability_id")["source_paper"]
        .nunique()
        .to_dict()
    )


# ---------------------------------------------------------------------------
# Heatmap
# ---------------------------------------------------------------------------
def render_heatmap(
    matrix: pd.DataFrame,
    capability_ids: list[str],
    sdlc_activities: list[str],
    out_path: Path,
) -> None:
    """Render 19×9 heatmap with gap borders and empty-cell hatching."""
    pivot = matrix.pivot(
        index="capability_id", columns="sdlc_activity", values="evidence_count"
    )
    pivot = pivot.reindex(index=capability_ids, columns=sdlc_activities)

    flag_pivot = matrix.pivot(
        index="capability_id", columns="sdlc_activity", values="is_gap"
    ).reindex(index=capability_ids, columns=sdlc_activities)
    empty_pivot = matrix.pivot(
        index="capability_id", columns="sdlc_activity", values="is_empty"
    ).reindex(index=capability_ids, columns=sdlc_activities)

    fig, ax = plt.subplots(figsize=(11, 9))
    sns.heatmap(
        pivot,
        ax=ax,
        cmap="YlGnBu",
        annot=True,
        fmt="d",
        cbar_kws={"label": "distinct paper count"},
        linewidths=0.5,
        linecolor="white",
    )

    # Overlay gap borders (red rectangles) and empty hatching.
    for i, cap in enumerate(capability_ids):
        for j, act in enumerate(sdlc_activities):
            if bool(flag_pivot.iloc[i, j]):
                ax.add_patch(
                    mpatches.Rectangle(
                        (j, i), 1, 1,
                        fill=False,
                        edgecolor="red",
                        linewidth=2.5,
                        zorder=5,
                    )
                )
            if bool(empty_pivot.iloc[i, j]):
                ax.add_patch(
                    mpatches.Rectangle(
                        (j, i), 1, 1,
                        fill=True,
                        facecolor="none",
                        hatch="///",
                        edgecolor="grey",
                        linewidth=0.0,
                        zorder=4,
                    )
                )

    p25_title = compute_percentile(matrix, 25)
    n_gaps = int(matrix["is_gap"].sum())
    n_empty = int(matrix["is_empty"].sum())
    ax.set_title(
        f"Capability x SDLC evidence matrix "
        f"(19 capabilities x 9 SDLC activities = 171 cells)\n"
        f"cell = distinct papers; red border = gap at P25={p25_title:.1f} "
        f"({n_gaps} cells); hatched = empty ({n_empty} cells)"
    )
    ax.set_xlabel("SDLC activity (F4)")
    ax.set_ylabel("Capability (harmonized, N=19)")
    plt.xticks(rotation=45, ha="right")
    plt.yticks(rotation=0)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Sensitivity narrative
# ---------------------------------------------------------------------------
def write_sensitivity_md(
    p25: float,
    p33: float,
    gap_25: int,
    gap_33: int,
    empty_count: int,
    out_path: Path,
) -> None:
    body = (
        "# Sensitivity analysis: P25 vs P33 gap thresholds\n\n"
        "**Artifact:** `artifacts/analysis/rq3_gap_matrix/sensitivity_25_33.md`\n"
        "**Script:** `code/analysis_rq3.py`\n"
        "**Source:** proposal §3.5 RQ3, sensitivity clause\n\n"
        "## Thresholds\n\n"
        f"- **P25** (primary) = {p25:.3f} (25th percentile of non-zero cells).\n"
        f"- **P33** (sensitivity) = {p33:.3f} (33rd percentile of non-zero cells).\n\n"
        "## Gap counts\n\n"
        f"- Cells flagged as gap at **P25**: **{gap_25}** of 171.\n"
        f"- Cells flagged as gap at **P33**: **{gap_33}** of 171.\n"
        f"- Cells flagged as empty (count == 0, reported separately): **{empty_count}** of 171.\n\n"
        "## Interpretation\n\n"
        "As expected, relaxing the threshold from P25 to P33 inflates the gap count: "
        f"{gap_33} cells vs {gap_25} at P25 (a delta of {gap_33 - gap_25}). "
        "The P25 threshold is the primary operational definition per proposal §3.5 — "
        "it isolates the genuinely scarce `(capability, SDLC)` intersections. "
        "P33 is the sensitivity probe: it exposes how many additional intersections sit on the "
        "margin of adequate evidence and would be reclassified as gaps under a less stringent rule.\n\n"
        "The empty-cell count is reported separately because `cell_value == 0` is categorically distinct from "
        "`cell_value ∈ (0, P25]` — empty cells reflect an outright literature vacuum, while gap cells indicate "
        "demonstrated-but-under-investigated combinations. Both feed ERP3 hypothesis generation but should not "
        "be pooled in aggregate counts.\n\n"
        "## How to regenerate\n\n"
        "```\n"
        "/home/bthia/smuprj/erp2-sms/venv/bin/python code/analysis_rq3.py\n"
        "```\n"
    )
    out_path.write_text(body, encoding="utf-8")


# ---------------------------------------------------------------------------
# Decision-register append
# ---------------------------------------------------------------------------
def classify_gap(capability_id: str, sdlc_activity: str) -> str:
    """Heuristic rationale label for a gap cell."""
    if capability_id in DESIGN_GAP_CAPS or sdlc_activity in {"Requirements", "Design"}:
        return "design_gap"
    if capability_id in ADOPTION_LAG_CAPS:
        return "adoption_lag"
    return "organizational_readiness_barrier"


def rationale_sentence(label: str, capability_id: str, sdlc_activity: str) -> str:
    templates = {
        "design_gap": (
            f"{label}: Evidence for {capability_id} at the {sdlc_activity} activity "
            "is below the P25 non-zero threshold, indicating an under-researched early-lifecycle "
            "intersection that warrants ERP3 investigation."
        ),
        "adoption_lag": (
            f"{label}: Evidence for the autonomy-leaning capability {capability_id} at "
            f"{sdlc_activity} is below the P25 non-zero threshold, consistent with known lag "
            "between research-frontier capabilities and practical SDLC adoption."
        ),
        "organizational_readiness_barrier": (
            f"{label}: Evidence for mature capability {capability_id} at {sdlc_activity} is "
            "below the P25 non-zero threshold, suggesting organizational or process friction "
            "rather than a technical shortfall."
        ),
    }
    return templates[label]


def append_register_rows(matrix: pd.DataFrame) -> int:
    """Append one row per is_gap=True cell; idempotent.

    Returns number of rows appended.
    """
    # Idempotence: skip if any row already exists for phase=5 hypothesis_for_erp3.
    if REGISTER.exists():
        with open(REGISTER, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("phase") == "5" and row.get("decision") == "hypothesis_for_erp3":
                    print(
                        "  ! decision_register.csv already contains phase=5 "
                        "hypothesis_for_erp3 rows — skipping append for idempotence."
                    )
                    return 0

    gaps = matrix[matrix["is_gap"]]
    if gaps.empty:
        return 0

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows_to_append = []
    for _, row in gaps.iterrows():
        cap = row["capability_id"]
        act = row["sdlc_activity"]
        label = classify_gap(cap, act)
        rationale = rationale_sentence(label, cap, act)
        rows_to_append.append([
            now,
            "5",
            "N/A",
            "hypothesis_for_erp3",
            "Proposal §3.5 RQ3 25th-percentile gap rule",
            rationale,
            "TBS",
        ])

    with open(REGISTER, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        for row in rows_to_append:
            writer.writerow(row)

    return len(rows_to_append)


# ---------------------------------------------------------------------------
# Fixture test
# ---------------------------------------------------------------------------
def fixture_test() -> None:
    """Assert (a) P25 uses non-zero only, (b) flag exclusivity."""
    fx = pd.DataFrame(
        {
            "capability_id": ["C1", "C1", "C2", "C2", "C3", "C3"],
            "sdlc_activity": ["A", "B", "A", "B", "A", "B"],
            "evidence_count": [0, 0, 2, 4, 6, 8],
        }
    )
    p25 = compute_percentile(fx, 25)
    expected = float(np.percentile([2, 4, 6, 8], 25))
    assert abs(p25 - expected) < 1e-9, (
        f"P25 fixture failed: got {p25}, expected {expected} (= {expected})"
    )
    assert abs(p25 - 3.5) < 1e-9, (
        f"P25 fixture sanity check failed: expected 3.5, got {p25}"
    )

    flagged = apply_flags(fx, p25)
    # is_gap AND is_empty must be False everywhere.
    assert not (flagged["is_gap"] & flagged["is_empty"]).any(), (
        "Flag exclusivity fixture failed"
    )
    # Sanity: 0-value cells are empty, not gap.
    zero_cells = flagged[flagged["evidence_count"] == 0]
    assert zero_cells["is_empty"].all() and not zero_cells["is_gap"].any(), (
        "Zero-value cells must be is_empty=True and is_gap=False"
    )
    print("  ✓ fixture test passed (P25=3.5 on [2,4,6,8]; flag exclusivity)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    np.random.seed(42)

    # --- Step 0: fixture test ---
    print("Running fixture test …")
    fixture_test()

    # --- Step 1: load inputs ---
    print("Loading inputs …")
    annotations = pd.read_csv(CAP_ANNOT)
    cap_list = pd.read_csv(CAP_LIST)
    extraction = pd.read_csv(EXTRACTION)

    capability_ids = sorted(cap_list["capability_id"].unique().tolist())
    # Use canonical SDLC order for output; sanity-check membership.
    cap_sdlc = set(cap_list["sdlc_activity"].unique())
    assert set(SDLC_ORDER) == cap_sdlc, (
        f"SDLC_ORDER mismatch with capability_list.csv: "
        f"missing={cap_sdlc - set(SDLC_ORDER)}, extra={set(SDLC_ORDER) - cap_sdlc}"
    )
    print(
        f"  capabilities: {len(capability_ids)}; "
        f"sdlc: {len(SDLC_ORDER)}; grid = {len(capability_ids) * len(SDLC_ORDER)} cells"
    )

    # --- Step 2: build master matrix ---
    print("Building master matrix …")
    matrix = build_matrix(annotations, extraction, capability_ids, SDLC_ORDER)
    assert len(matrix) == 171, f"Expected 171 rows, got {len(matrix)}"

    p25 = compute_percentile(matrix, 25)
    p33 = compute_percentile(matrix, 33)
    print(f"  P25 = {p25}; P33 = {p33}")

    matrix = apply_flags(matrix, p25)
    in_source = compute_in_source_survey(cap_list)
    matrix["in_source_survey"] = matrix["capability_id"].map(in_source).astype(int)

    gap_count = int(matrix["is_gap"].sum())
    empty_count = int(matrix["is_empty"].sum())
    print(f"  is_gap cells: {gap_count}; is_empty cells: {empty_count}")

    # Sort for reproducibility (alphabetical capability, canonical SDLC).
    order_map = {a: i for i, a in enumerate(SDLC_ORDER)}
    matrix["_sdlc_order"] = matrix["sdlc_activity"].map(order_map)
    matrix = matrix.sort_values(["capability_id", "_sdlc_order"]).drop(
        columns="_sdlc_order"
    )
    cols = [
        "capability_id",
        "sdlc_activity",
        "evidence_count",
        "is_gap",
        "is_empty",
        "in_source_survey",
    ]
    matrix = matrix[cols]

    # --- Step 3: write gap_matrix.csv + meta ---
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    matrix.to_csv(OUT_MATRIX, index=False)
    write_with_meta(
        OUT_MATRIX,
        script="code/analysis_rq3.py",
        inputs=[
            "artifacts/extraction/capability_annotations.csv",
            "artifacts/protocol/capability_list.csv",
            "artifacts/extraction/extraction_matrix.csv",
        ],
    )
    print(f"  wrote {OUT_MATRIX.relative_to(ROOT)}")

    # --- Step 4: heatmap ---
    print("Rendering heatmap …")
    render_heatmap(matrix, capability_ids, SDLC_ORDER, OUT_HEATMAP)
    write_with_meta(
        OUT_HEATMAP,
        script="code/analysis_rq3.py",
        inputs=[str(OUT_MATRIX.relative_to(ROOT))],
    )
    print(f"  wrote {OUT_HEATMAP.relative_to(ROOT)}")

    # --- Step 5: sensitivity analysis ---
    print("Writing sensitivity_25_33.md …")
    sens_matrix = apply_flags(
        matrix[["capability_id", "sdlc_activity", "evidence_count"]].copy(), p33
    )
    gap_33 = int(sens_matrix["is_gap"].sum())
    write_sensitivity_md(p25, p33, gap_count, gap_33, empty_count, OUT_SENS)
    print(f"  wrote {OUT_SENS.relative_to(ROOT)} (P25 gaps={gap_count}; P33 gaps={gap_33})")

    # --- Step 6: paradigm splits ---
    print("Computing paradigm splits …")
    OUT_PARADIGM_DIR.mkdir(parents=True, exist_ok=True)
    paradigm_map = {
        "Pro-code": OUT_PROCODE,
        "Low-code": OUT_LOWCODE,
        "No-code": OUT_NOCODE,
    }
    for paradigm, out_path in paradigm_map.items():
        sub_papers = extraction[extraction["f5_tool_paradigm"] == paradigm][
            ["paper_id", "f4_sdlc_activity"]
        ]
        sub_annot = annotations[annotations["paper_id"].isin(sub_papers["paper_id"])]
        sub_matrix = build_matrix(
            sub_annot, sub_papers, capability_ids, SDLC_ORDER
        )
        sub_p25 = compute_percentile(sub_matrix, 25)
        sub_matrix = apply_flags(sub_matrix, sub_p25)
        sub_matrix["in_source_survey"] = sub_matrix["capability_id"].map(
            in_source
        ).astype(int)
        sub_matrix["_sdlc_order"] = sub_matrix["sdlc_activity"].map(order_map)
        sub_matrix = sub_matrix.sort_values(
            ["capability_id", "_sdlc_order"]
        ).drop(columns="_sdlc_order")
        sub_matrix = sub_matrix[cols]
        sub_matrix.to_csv(out_path, index=False)
        write_with_meta(
            out_path,
            script="code/analysis_rq3.py",
            inputs=[
                "artifacts/extraction/capability_annotations.csv",
                "artifacts/extraction/extraction_matrix.csv",
                f"filter: f5_tool_paradigm == {paradigm!r}",
            ],
        )
        sub_gap = int(sub_matrix["is_gap"].sum())
        sub_empty = int(sub_matrix["is_empty"].sum())
        print(
            f"  wrote {out_path.relative_to(ROOT)} "
            f"(papers={sub_papers['paper_id'].nunique()}, P25={sub_p25}, "
            f"gaps={sub_gap}, empty={sub_empty})"
        )

    # --- Step 7: append decision-register rows ---
    print("Appending decision-register hypothesis rows …")
    appended = append_register_rows(matrix)
    print(f"  appended {appended} rows to {REGISTER.relative_to(ROOT)}")

    print("\n✓ analysis_rq3: all steps complete.")


if __name__ == "__main__":
    main()
