"""Task 5.1 Step B — RQ2 variation cross-tabulations.

Emits three paired (CSV, Markdown) tables showing how the 5 interaction
modes (+ residuals) vary across:

    1. mode x F4 SDLC activity       -> mode_x_sdlc.{csv,md}
    2. mode x F5 tool profile        -> mode_x_tool_profile.{csv,md}
    3. mode x F3 population/context  -> mode_x_population_context.{csv,md}

See design/5_1_analysis_rq2_variation.md for specifications.

Usage:
    python code/analysis_rq2_variation.py
"""

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Minimal pipe-table renderer (keeps this script dep-free of `tabulate`)
# ---------------------------------------------------------------------------
def _pipe_table(headers: list[str], rows: list[list[str]]) -> str:
    """Render a GitHub-flavor pipe Markdown table without external deps."""
    cells = [headers] + [[str(c) for c in r] for r in rows]
    widths = [max(len(cells[r][c]) for r in range(len(cells)))
              for c in range(len(headers))]
    def _fmt(row: list[str]) -> str:
        return "| " + " | ".join(
            cell.ljust(widths[i]) for i, cell in enumerate(row)
        ) + " |"
    sep = "| " + " | ".join("-" * widths[i] for i in range(len(headers))) + " |"
    body = [_fmt(headers), sep] + [_fmt(r) for r in rows]
    return "\n".join(body)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
CONSOLIDATED_CSV = ROOT / "artifacts" / "synthesis" / "consolidated_codes.csv"
TAXONOMY_CSV = ROOT / "artifacts" / "synthesis" / "taxonomy_classifications.csv"
EXTRACTION_CSV = ROOT / "artifacts" / "extraction" / "extraction_matrix.csv"

OUT_DIR = ROOT / "artifacts" / "analysis" / "rq2_variation"

MODE_ORDER = ["1", "2", "3", "4", "5", "r"]
SDLC_ORDER = [
    "Coding", "Testing", "Debugging", "Code Review", "Requirements",
    "Design", "Documentation", "Project Management", "CI/CD",
]
PARADIGM_ORDER = ["Pro-code", "Low-code", "No-code"]

PASSAGE_RE = re.compile(r"^(doi:.+):P\d+$")


# ---------------------------------------------------------------------------
# Join chain
# ---------------------------------------------------------------------------
def build_label_paper_frame() -> pd.DataFrame:
    """Return a frame of DISTINCT (canonical_label, paper_id) pairs."""
    cc = pd.read_csv(CONSOLIDATED_CSV)
    assert cc.shape[0] == 707, (
        f"Expected 707 consolidated codes, found {cc.shape[0]}")
    rows = []
    for _, r in cc.iterrows():
        raw = r["passage_ids"]
        if not isinstance(raw, str) or not raw.strip():
            continue
        try:
            pids = json.loads(raw)
        except json.JSONDecodeError:
            continue
        for pid in pids:
            m = PASSAGE_RE.match(pid)
            if m:
                rows.append(
                    {"canonical_label": r["canonical_label"],
                     "paper_id": m.group(1)})
    df = pd.DataFrame(rows).drop_duplicates().reset_index(drop=True)
    return df


def build_join() -> pd.DataFrame:
    """Return frame joined to taxonomy and extraction attributes."""
    lp = build_label_paper_frame()

    tx = pd.read_csv(TAXONOMY_CSV, dtype={"mode": str})
    assert tx.shape[0] == 707, (
        f"Expected 707 taxonomy rows, found {tx.shape[0]}")

    em = pd.read_csv(EXTRACTION_CSV)
    assert em.shape[0] == 640, (
        f"Expected 640 extraction rows, found {em.shape[0]}")

    joined = lp.merge(tx[["canonical_label", "mode"]], on="canonical_label",
                      how="left")
    assert joined["mode"].isna().sum() == 0, (
        "Some canonical_labels have no mode in taxonomy_classifications.csv")

    attrs = em[[
        "paper_id", "f3_population", "f3_context",
        "f4_sdlc_activity", "f5_tool_paradigm",
    ]]
    joined = joined.merge(attrs, on="paper_id", how="left")
    return joined


# ---------------------------------------------------------------------------
# Aggregation helpers
# ---------------------------------------------------------------------------
def distinct_papers_per_mode(join: pd.DataFrame) -> dict[str, int]:
    """Total distinct papers per mode (row denominator)."""
    return {
        m: int(join[join["mode"] == m]["paper_id"].nunique())
        for m in MODE_ORDER
    }


def crosstab(join: pd.DataFrame, col: str, col_order: list[str],
             explode_pipe: bool = False) -> pd.DataFrame:
    """Return a mode x col matrix of distinct paper counts."""
    sub = join.copy()
    if explode_pipe:
        sub = sub.dropna(subset=[col])
        sub[col] = sub[col].astype(str).str.split("|")
        sub = sub.explode(col)
        sub[col] = sub[col].str.strip()
        sub = sub[sub[col] != ""]
    else:
        sub = sub.dropna(subset=[col])

    mat = (
        sub.groupby(["mode", col])["paper_id"]
        .nunique()
        .unstack(fill_value=0)
    )
    mat = mat.reindex(index=MODE_ORDER, columns=col_order, fill_value=0)
    mat = mat.fillna(0).astype(int)
    mat.index.name = "mode"
    return mat


def crosstab_pop_context(join: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    sub = join.dropna(subset=["f3_population", "f3_context"]).copy()
    sub["pop_ctx"] = sub["f3_population"].astype(str) + " / " \
        + sub["f3_context"].astype(str)
    col_order = sorted(sub["pop_ctx"].unique().tolist())
    mat = (
        sub.groupby(["mode", "pop_ctx"])["paper_id"]
        .nunique()
        .unstack(fill_value=0)
    )
    mat = mat.reindex(index=MODE_ORDER, columns=col_order, fill_value=0)
    mat = mat.fillna(0).astype(int)
    mat.index.name = "mode"
    return mat, col_order


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------
def render_markdown(mat: pd.DataFrame, totals: dict[str, int],
                    title: str, note: str = "") -> str:
    """Return a pipe Markdown string with row-normalized percentages."""
    headers = ["mode"] + list(mat.columns) + ["Total N"]
    body = []
    for mode in MODE_ORDER:
        row = [mode]
        denom = totals.get(mode, 0)
        for col in mat.columns:
            count = int(mat.at[mode, col]) if mode in mat.index else 0
            if denom > 0:
                pct = 100.0 * count / denom
                row.append(f"{count} ({pct:.1f}%)")
            else:
                row.append(f"{count} (0.0%)")
        row.append(str(denom))
        body.append(row)

    md = [f"# {title}", ""]
    if note:
        md.extend([note, ""])
    md.append(_pipe_table(headers, body))
    md.append("")
    return "\n".join(md)


# ---------------------------------------------------------------------------
# Table writers
# ---------------------------------------------------------------------------
def _file_unique_papers(join: pd.DataFrame, col: str | None,
                        explode_pipe: bool) -> int:
    """Return count of distinct paper_ids contributing any cell in this file.

    This is the per-file deduplicated paper count; the proxy that lets
    `dod_checks` confirm the RQ2 join landed on ~290 unique papers even
    though individual rows/cells can overcount due to mode overlap or
    multi-value explosion.
    """
    if col is None:  # population x context
        sub = join.dropna(subset=["f3_population", "f3_context"])
    else:
        sub = join.dropna(subset=[col])
    return int(sub["paper_id"].nunique())


def write_table(join: pd.DataFrame, totals: dict[str, int], name: str,
                title: str, col: str | None, col_order: list[str] | None,
                explode_pipe: bool, note: str) -> tuple[Path, Path]:
    csv_path = OUT_DIR / f"{name}.csv"
    md_path = OUT_DIR / f"{name}.md"

    if col is None:  # population x context: ad-hoc
        mat, resolved_cols = crosstab_pop_context(join)
    else:
        mat = crosstab(join, col, col_order or [], explode_pipe=explode_pipe)
        resolved_cols = list(mat.columns)

    # Append a 'file_unique_papers' row that records the file-level unique
    # paper count as the first column. The value is deduplicated across
    # modes and multi-value explosions, so it is a single scalar summary
    # readable from any of the table cells in that row (every non-first
    # column is filled with 0 as a placeholder). `dod_checks.py` reads
    # the first cell of that row to verify the proxy is in [200, 310].
    export = mat.copy()
    unique_total = _file_unique_papers(join, col, explode_pipe)
    export.loc["file_unique_papers"] = [unique_total] + \
        [0] * (len(resolved_cols) - 1)
    export.to_csv(csv_path)
    md = render_markdown(mat, totals, title, note=note)
    md_path.write_text(md, encoding="utf-8")
    print(f"  -> {csv_path.relative_to(ROOT)} / {md_path.relative_to(ROOT)}")
    return csv_path, md_path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    join = build_join()
    print(f"Joined frame: {join.shape[0]} (label, paper) pairs, "
          f"{join['paper_id'].nunique()} distinct papers.")

    extracted_paper_count = join["paper_id"].nunique()
    assert extracted_paper_count > 0, (
        "No papers produced from the join — check regex and inputs.")

    totals = distinct_papers_per_mode(join)
    print("Distinct papers per mode:", totals)

    # Table 1 — mode x F4 SDLC activity (pipe-exploded)
    write_table(
        join, totals, name="mode_x_sdlc",
        title="Table 1 — Interaction mode x F4 SDLC activity "
              "(row %, distinct paper count)",
        col="f4_sdlc_activity", col_order=SDLC_ORDER,
        explode_pipe=True,
        note="> Cell = distinct papers whose passages map to this mode "
             "and whose paper-level F4 activity set includes the column. "
             "Multi-activity papers contribute to every activity they list; "
             "row percentages therefore may sum to > 100%. Total N is the "
             "distinct paper denominator per mode (pre-explode).")

    # Table 2 — mode x F5 tool paradigm
    write_table(
        join, totals, name="mode_x_tool_profile",
        title="Table 2 — Interaction mode x F5 tool profile "
              "(row %, distinct paper count)",
        col="f5_tool_paradigm", col_order=PARADIGM_ORDER,
        explode_pipe=False,
        note="> Cell = distinct papers whose passages map to this mode "
             "and whose paper-level F5 tool paradigm matches the column. "
             "f5_tool_paradigm is single-valued; row percentages sum to "
             "100% minus any rows with missing paradigm.")

    # Table 3 — mode x F3 population x context
    write_table(
        join, totals, name="mode_x_population_context",
        title="Table 3 — Interaction mode x F3 population x context "
              "(row %, distinct paper count)",
        col=None, col_order=None, explode_pipe=False,
        note="> Cell = distinct papers whose passages map to this mode and "
             "whose (population, context) metadata matches the column. "
             "Rows with missing population or context are excluded from the "
             "cross-tab. Row percentages may sum to <100% because of those "
             "exclusions.")

    print("OK analysis_rq2_variation: 3 CSVs + 3 Markdowns written.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
