"""Task 5.1 Step A — RQ1 landscape figures.

Produces four descriptive PNGs characterizing the 640-paper corpus:

    1. year_sdlc_bubble.png       — year × SDLC bubble, faceted by f3_population.
    2. f2_method_bar.png          — research-methodology distribution bar.
    3. sdlc_year_heatmap.png      — SDLC activity × year heatmap.
    4. f5_tool_profile_stacked.png — tool paradigm × modality stacked bar.

See design/5_1_analysis_rq1.md for specifications.

Usage:
    python code/analysis_rq1.py
"""

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from code.utils import write_with_meta  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
INPUT_CSV = ROOT / "artifacts" / "extraction" / "extraction_matrix.csv"
OUT_DIR = ROOT / "artifacts" / "analysis" / "rq1_landscape"
INPUT_MANIFEST = ["artifacts/extraction/extraction_matrix.csv"]

SDLC_ORDER = [
    "Coding", "Testing", "Debugging", "Code Review", "Requirements",
    "Design", "Documentation", "Project Management", "CI/CD",
]
POPULATION_ORDER = [
    "Student", "Professional SWE", "Mixed", "Citizen Developer",
    "OSS Contributor",
]
PARADIGM_ORDER = ["Pro-code", "Low-code", "No-code"]
MODALITY_ORDER = [
    "Autocomplete", "Conversational", "IDE-Integrated", "Autonomous",
]

DPI = 300
SEED = 42


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
def load_extraction() -> pd.DataFrame:
    df = pd.read_csv(INPUT_CSV)
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    return df


def explode_pipe(df: pd.DataFrame, col: str) -> pd.DataFrame:
    """Return a copy of df with *col* split on '|' and exploded to rows."""
    out = df.copy()
    out[col] = out[col].fillna("").astype(str).str.split("|")
    out = out.explode(col)
    out[col] = out[col].str.strip()
    out = out[out[col] != ""]
    return out


# ---------------------------------------------------------------------------
# Fig 1 — year × SDLC bubble, faceted by population
# ---------------------------------------------------------------------------
def fig1_year_sdlc_bubble(df: pd.DataFrame) -> Path:
    out_path = OUT_DIR / "year_sdlc_bubble.png"

    sdlc = explode_pipe(df, "f4_sdlc_activity")
    sdlc = sdlc.dropna(subset=["f3_population", "year"])
    sdlc = sdlc[sdlc["f3_population"].isin(POPULATION_ORDER)]

    years = sorted(sdlc["year"].dropna().unique().tolist())
    populations = [p for p in POPULATION_ORDER if p in sdlc["f3_population"].unique()]

    n_pop = len(populations)
    n_cols = 3
    n_rows = int(np.ceil(n_pop / n_cols))
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(14, 8), sharex=True, sharey=True)
    axes = np.atleast_2d(axes)

    for i, pop in enumerate(populations):
        r, c = divmod(i, n_cols)
        ax = axes[r, c]
        sub = sdlc[sdlc["f3_population"] == pop]
        counts = (
            sub.groupby(["year", "f4_sdlc_activity"])["paper_id"]
            .nunique()
            .reset_index(name="n")
        )
        if counts.empty:
            ax.set_title(f"{pop} (n=0)")
            ax.set_xticks(years)
            ax.set_yticks(range(len(SDLC_ORDER)))
            ax.set_yticklabels(SDLC_ORDER)
            continue

        x = counts["year"].astype(int).to_numpy()
        y = counts["f4_sdlc_activity"].map(
            {name: idx for idx, name in enumerate(SDLC_ORDER)}
        ).to_numpy()
        s = counts["n"].to_numpy()
        sizes = 20 + s * 30
        ax.scatter(x, y, s=sizes, alpha=0.6, edgecolors="black", linewidths=0.5)
        ax.set_title(f"{pop} (n={sub['paper_id'].nunique()})")
        ax.set_xticks(years)
        ax.set_yticks(range(len(SDLC_ORDER)))
        ax.set_yticklabels(SDLC_ORDER)
        ax.grid(True, alpha=0.3, linestyle=":")

    # Hide unused axes
    for j in range(n_pop, n_rows * n_cols):
        r, c = divmod(j, n_cols)
        axes[r, c].axis("off")

    n_plot = sdlc["paper_id"].nunique()
    fig.suptitle(
        "Empirical AI-SE studies by year, SDLC activity, and developer population\n"
        f"(n={n_plot} papers with canonical F3 population, numeric year, and "
        "≥1 tagged SDLC activity;\nbubble area = distinct paper count per "
        "year x SDLC cell)",
        y=1.02,
    )
    fig.supxlabel("Publication year")
    fig.supylabel("SDLC activity (F4)")
    fig.tight_layout()
    fig.savefig(out_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)

    write_with_meta(out_path, "code/analysis_rq1.py", INPUT_MANIFEST, seed=SEED)
    return out_path


# ---------------------------------------------------------------------------
# Fig 2 — F2 research methodology bar
# ---------------------------------------------------------------------------
def fig2_f2_method_bar(df: pd.DataFrame) -> Path:
    out_path = OUT_DIR / "f2_method_bar.png"
    counts = (
        df["f2_research_methodology"].dropna()
        .value_counts()
        .sort_values(ascending=False)
    )

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(counts.index, counts.values, color="steelblue",
                  edgecolor="black")
    for bar, v in zip(bars, counts.values):
        ax.text(bar.get_x() + bar.get_width() / 2, v + 2,
                str(int(v)), ha="center", va="bottom", fontsize=10)

    ax.set_xlabel("F2 research methodology")
    ax.set_ylabel("Paper count")
    ax.set_title(
        f"Distribution of research methodologies across the corpus "
        f"(N={len(df)} papers; one F2 value per paper)"
    )
    ax.grid(True, alpha=0.3, axis="y")
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    fig.tight_layout()
    fig.savefig(out_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)

    write_with_meta(out_path, "code/analysis_rq1.py", INPUT_MANIFEST, seed=SEED)
    return out_path


# ---------------------------------------------------------------------------
# Fig 3 — SDLC × year heatmap
# ---------------------------------------------------------------------------
def fig3_sdlc_year_heatmap(df: pd.DataFrame) -> Path:
    out_path = OUT_DIR / "sdlc_year_heatmap.png"

    sdlc = explode_pipe(df, "f4_sdlc_activity")
    sdlc = sdlc.dropna(subset=["year"])
    years = sorted(sdlc["year"].dropna().astype(int).unique().tolist())

    mat = (
        sdlc.groupby(["f4_sdlc_activity", "year"])["paper_id"]
        .nunique()
        .unstack(fill_value=0)
        .reindex(index=SDLC_ORDER, columns=years, fill_value=0)
    )

    n_plot = sdlc["paper_id"].nunique()
    n_bindings = len(sdlc)
    fig, ax = plt.subplots(figsize=(9, 6))
    sns.heatmap(mat, annot=True, fmt="d", cmap="YlOrRd", ax=ax,
                cbar_kws={"label": "Distinct papers in cell"})
    ax.set_xlabel("Publication year")
    ax.set_ylabel("SDLC activity (F4)")
    ax.set_title(
        f"SDLC activity coverage across publication years "
        f"(n={n_plot} papers; {n_bindings} paper x SDLC bindings)"
    )
    fig.tight_layout()
    fig.savefig(out_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)

    write_with_meta(out_path, "code/analysis_rq1.py", INPUT_MANIFEST, seed=SEED)
    return out_path


# ---------------------------------------------------------------------------
# Fig 4 — F5 tool-profile stacked bar
# ---------------------------------------------------------------------------
def fig4_f5_tool_profile_stacked(df: pd.DataFrame) -> Path:
    out_path = OUT_DIR / "f5_tool_profile_stacked.png"

    f5 = explode_pipe(df, "f5_tool_modality")
    f5 = f5.dropna(subset=["f5_tool_paradigm"])
    f5 = f5[f5["f5_tool_modality"].isin(MODALITY_ORDER)]
    f5 = f5[f5["f5_tool_paradigm"].isin(PARADIGM_ORDER)]

    mat = (
        f5.groupby(["f5_tool_paradigm", "f5_tool_modality"])["paper_id"]
        .nunique()
        .unstack(fill_value=0)
        .reindex(index=PARADIGM_ORDER, columns=MODALITY_ORDER, fill_value=0)
    )

    fig, ax = plt.subplots(figsize=(9, 6))
    bottoms = np.zeros(len(PARADIGM_ORDER))
    colors = ["#4c72b0", "#55a868", "#c44e52", "#8172b2"]
    for modality, color in zip(MODALITY_ORDER, colors):
        vals = mat[modality].to_numpy()
        ax.bar(PARADIGM_ORDER, vals, bottom=bottoms, label=modality,
               color=color, edgecolor="black")
        bottoms += vals

    n_plot = f5["paper_id"].nunique()
    n_bindings = len(f5)
    ax.set_xlabel("F5 tool paradigm (Pro-code / Low-code / No-code)")
    ax.set_ylabel("Paper x modality bindings (stacked)")
    ax.set_title(
        "Tool profile: F5 paradigm x F5 interaction modality\n"
        f"(n={n_plot} papers; {n_bindings} paper x modality bindings; "
        "modality is multi-select per proposal 3.4)"
    )
    ax.legend(title="F5 interaction modality", loc="center left",
              bbox_to_anchor=(1.02, 0.5))
    ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(out_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)

    write_with_meta(out_path, "code/analysis_rq1.py", INPUT_MANIFEST, seed=SEED)
    return out_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = load_extraction()
    assert df.shape[0] == 640, (
        f"Expected 640 rows in extraction_matrix.csv, found {df.shape[0]}")

    print(f"Loaded {df.shape[0]} papers from {INPUT_CSV.relative_to(ROOT)}")
    p1 = fig1_year_sdlc_bubble(df); print(f"  -> {p1.relative_to(ROOT)}")
    p2 = fig2_f2_method_bar(df);    print(f"  -> {p2.relative_to(ROOT)}")
    p3 = fig3_sdlc_year_heatmap(df); print(f"  -> {p3.relative_to(ROOT)}")
    p4 = fig4_f5_tool_profile_stacked(df); print(f"  -> {p4.relative_to(ROOT)}")
    print("OK analysis_rq1: 4 PNGs + meta sidecars written.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
