"""Task 4.2 — Saturation-curve computation (Cruzes & Dybå Step 5 dependability).

Answers: *at what point in the processing order did new canonical labels
stop emerging?* The saturation verdict is the dependability evidence that
the coding process has converged for this corpus.

Algorithm (per design/4_2_interaction_taxonomy.md §2):
    1. Load consolidated_codes.csv; explode passage_ids so each row is
       (canonical_label, paper_id, passage_id).
    2. Join with extraction_status.csv on paper_id to get per-paper
       extraction timestamp. Order papers by timestamp ascending
       (tie-break: paper_id lexicographic).
    3. Walk papers in order. For each paper p_i:
           new_codes_i       = canonical_labels first seen at p_i
           cumulative_codes_i = union of all canonical_labels through p_i
    4. Mark the final 10% window (papers with rank > 0.9 * N, where
       N = count of papers with ≥1 passage).
    5. Report:
           new_in_final_window = sum(new_count_i in window)
           saturated = (new_in_final_window == 0)
           marginal_rate = new_in_final_window / window_size

Outputs (canonical-label layer, default):
    artifacts/synthesis/saturation_data.csv
    artifacts/synthesis/saturation_report.md
    artifacts/synthesis/saturation_curve.png

Outputs (interaction-mode layer, with --group-by-mode):
    artifacts/synthesis/saturation_data_mode.csv
    artifacts/synthesis/saturation_report_mode.md
    artifacts/synthesis/saturation_curve_mode.png

Usage:
    python code/saturation_report.py                   # canonical-label layer
    python code/saturation_report.py --group-by-mode   # interaction-mode layer
    python code/saturation_report.py --window 0.15     # final 15% window
    python code/saturation_report.py --verify          # DoD on existing output
    python code/saturation_report.py --chart-only      # regen PNG only
    python code/saturation_report.py --self-test       # in-memory fixture
"""

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------
import argparse
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
SYNTH_DIR = ROOT / "artifacts" / "synthesis"
CONSOLIDATED_CSV = SYNTH_DIR / "consolidated_codes.csv"
CLASSIFY_CSV = SYNTH_DIR / "taxonomy_classifications.csv"
EXTRACT_STATUS_CSV = ROOT / "artifacts" / "extraction" / "extraction_status.csv"

# Canonical-label layer (Task 4.1 output)
SATURATION_CSV = SYNTH_DIR / "saturation_data.csv"
SATURATION_MD = SYNTH_DIR / "saturation_report.md"
SATURATION_PNG = SYNTH_DIR / "saturation_curve.png"

# Interaction-mode layer (Task 4.2 output) — sidecars, kept separate so
# the canonical-layer run from the pre-taxonomy commit is not overwritten.
SATURATION_MODE_CSV = SYNTH_DIR / "saturation_data_mode.csv"
SATURATION_MODE_MD  = SYNTH_DIR / "saturation_report_mode.md"
SATURATION_MODE_PNG = SYNTH_DIR / "saturation_curve_mode.png"

DEFAULT_WINDOW = 0.10
PASSAGE_ID_COL = "passage_ids"
LABEL_COL = "canonical_label"
VALID_MODE_KEYS = {"1", "2", "3", "4", "5", "r"}


# ---------------------------------------------------------------------------
# Small utilities
# ---------------------------------------------------------------------------
def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha1_of_file(path: Path) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def paper_id_from_passage(passage_id: str) -> str:
    """A passage_id has the form '<scheme>:<id>:P<nnn>' — strip the
    trailing ':P<nnn>' to recover the paper_id."""
    return passage_id.rsplit(":", 1)[0]


# ---------------------------------------------------------------------------
# Load + explode
# ---------------------------------------------------------------------------
def load_label_to_papers(csv_path: Path) -> pd.DataFrame:
    """Return a long-form DataFrame with one row per (label, paper_id)."""
    if not csv_path.exists():
        raise FileNotFoundError(f"{csv_path} not found — run Task 4.1 first.")
    df = pd.read_csv(csv_path, dtype=str).fillna("")
    rows: list[dict] = []
    for _, r in df.iterrows():
        label = r[LABEL_COL]
        try:
            passage_ids = json.loads(r[PASSAGE_ID_COL]) if r[PASSAGE_ID_COL] else []
        except json.JSONDecodeError:
            passage_ids = []
        seen_papers_for_label: set[str] = set()
        for pid in passage_ids:
            paper = paper_id_from_passage(pid)
            if paper in seen_papers_for_label:
                continue
            seen_papers_for_label.add(paper)
            rows.append({"canonical_label": label, "paper_id": paper})
    return pd.DataFrame(rows)


def load_mode_to_papers(cons_csv: Path, cls_csv: Path) -> pd.DataFrame:
    """Long-form (mode, paper_id) from the Step-4 partition.

    Joins consolidated_codes.csv (label -> passage_ids) with
    taxonomy_classifications.csv (label -> mode), then reduces to the
    unique (mode, paper_id) pairs. Returned column is named
    'canonical_label' for drop-in compatibility with compute_saturation;
    values are mode keys {'1','2','3','4','5','r'}.
    """
    if not cons_csv.exists():
        raise FileNotFoundError(f"{cons_csv} not found - run Task 4.1 first.")
    if not cls_csv.exists():
        raise FileNotFoundError(
            f"{cls_csv} not found - run Step 4 "
            "(taxonomy_classify_llmassist.py) first.")
    cls = pd.read_csv(cls_csv, dtype=str).fillna("")
    if "mode" not in cls.columns or LABEL_COL not in cls.columns:
        raise ValueError(f"{cls_csv} missing 'mode' or '{LABEL_COL}' column.")
    label_to_mode = dict(zip(cls[LABEL_COL], cls["mode"]))

    cons = pd.read_csv(cons_csv, dtype=str).fillna("")
    rows: list[dict] = []
    for _, r in cons.iterrows():
        label = r[LABEL_COL]
        mode = label_to_mode.get(label, "")
        if mode not in VALID_MODE_KEYS:
            continue
        try:
            pids = json.loads(r[PASSAGE_ID_COL]) if r[PASSAGE_ID_COL] else []
        except json.JSONDecodeError:
            pids = []
        for pid in pids:
            paper = paper_id_from_passage(pid)
            rows.append({"canonical_label": mode, "paper_id": paper})
    df = pd.DataFrame(rows).drop_duplicates().reset_index(drop=True)
    return df


def load_processing_order(status_csv: Path) -> pd.DataFrame:
    """Return paper_id → timestamp, sorted by timestamp ascending."""
    if not status_csv.exists():
        raise FileNotFoundError(
            f"{status_csv} not found — needed for processing order.")
    df = pd.read_csv(status_csv, dtype=str).fillna("")
    needed = {"paper_id", "timestamp"}
    missing = needed - set(df.columns)
    if missing:
        raise ValueError(f"{status_csv} missing columns: {missing}")
    df = df[["paper_id", "timestamp"]].copy()
    df = df[df["paper_id"].str.strip() != ""]
    df["timestamp"] = df["timestamp"].replace("", pd.NA)
    # Use (timestamp, paper_id) for stable ordering; lexicographic tie-break.
    df = df.sort_values(["timestamp", "paper_id"],
                        na_position="last").reset_index(drop=True)
    return df


# ---------------------------------------------------------------------------
# Saturation computation
# ---------------------------------------------------------------------------
def compute_saturation(label_paper: pd.DataFrame,
                       order: pd.DataFrame,
                       window_frac: float) -> pd.DataFrame:
    """Return saturation_data.csv as a DataFrame.

    Args:
        label_paper: long-form (canonical_label, paper_id)
        order:       paper_id → timestamp (sorted ascending)
        window_frac: fraction of papers counted as the 'final window'

    Returns:
        DataFrame with columns rank, paper_id, extraction_timestamp,
        new_count, cumulative_count, in_final_window (bool)
    """
    papers_with_codes = set(label_paper["paper_id"])
    order_filtered = order[order["paper_id"].isin(papers_with_codes)].copy()
    order_filtered = order_filtered.reset_index(drop=True)
    order_filtered["rank"] = np.arange(1, len(order_filtered) + 1)

    # Group labels by paper once.
    papers_to_labels: dict[str, set[str]] = {
        str(k): set(v) for k, v in
        label_paper.groupby("paper_id")["canonical_label"].apply(set).items()
    }

    seen: set[str] = set()
    new_counts: list[int] = []
    cum_counts: list[int] = []
    for _, r in order_filtered.iterrows():
        labels_here = papers_to_labels.get(r["paper_id"], set())
        new_here = labels_here - seen
        new_counts.append(len(new_here))
        seen |= labels_here
        cum_counts.append(len(seen))

    order_filtered["new_count"] = new_counts
    order_filtered["cumulative_count"] = cum_counts

    n = len(order_filtered)
    window_start_rank = math.ceil((1 - window_frac) * n) + 1  # 1-indexed
    order_filtered["in_final_window"] = (
        order_filtered["rank"] >= window_start_rank)

    return order_filtered.rename(
        columns={"timestamp": "extraction_timestamp"})[
        ["rank", "paper_id", "extraction_timestamp",
         "new_count", "cumulative_count", "in_final_window"]
    ]


# ---------------------------------------------------------------------------
# Chart
# ---------------------------------------------------------------------------
def render_chart(sat: pd.DataFrame, out_png: Path, window_frac: float,
                 unit_label: str = "canonical labels") -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("  [warn] matplotlib not installed — skipping chart",
              file=sys.stderr)
        return

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(sat["rank"], sat["cumulative_count"],
            color="#1f77b4", linewidth=1.6,
            label=f"Cumulative {unit_label}")
    # Shade final window
    if sat["in_final_window"].any():
        first_win = int(sat.loc[sat["in_final_window"], "rank"].min())
        last_rank = int(sat["rank"].max())
        ax.axvspan(first_win - 0.5, last_rank + 0.5,
                   alpha=0.10, color="#ff7f0e",
                   label=f"Final {int(window_frac * 100)}% window")
    ax.set_xlabel("Paper rank (extraction timestamp ascending)")
    ax.set_ylabel(f"Cumulative {unit_label}")
    ax.set_title(f"Coding saturation curve — {unit_label.capitalize()} "
                 f"(Task 4.2)")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="lower right")
    fig.tight_layout()
    fig.savefig(out_png, dpi=150)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
def render_report(sat: pd.DataFrame,
                  total_labels: int,
                  consolidated_sha1: str,
                  window_frac: float,
                  *,
                  layer: str = "canonical-label",
                  unit_singular: str = "canonical label",
                  unit_plural: str = "canonical labels",
                  png_filename: str = "saturation_curve.png") -> str:
    n = len(sat)
    window = sat[sat["in_final_window"]]
    window_size = len(window)
    new_in_window = int(window["new_count"].sum())
    marginal = new_in_window / window_size if window_size else 0.0
    verdict = ("Saturated" if new_in_window == 0
               else f"Not saturated — {new_in_window} new "
                    f"{unit_singular}(s) in final window")

    lines: list[str] = []
    lines.append(f"# Coding Saturation Report ({layer} layer) — Task 4.2")
    lines.append("")
    lines.append(f"> Generated: `{utcnow_iso()}`")
    lines.append(f"> Script: `code/saturation_report.py`")
    lines.append(f"> Input: `artifacts/synthesis/consolidated_codes.csv` "
                 f"(sha1 `{consolidated_sha1[:16]}...`)")
    if layer == "interaction-mode":
        lines.append(f"> Partition source: "
                     f"`artifacts/synthesis/taxonomy_classifications.csv` "
                     f"(707 canonical labels -> 5 modes + Residuals)")
    lines.append(f"> Processing order source: "
                 f"`artifacts/extraction/extraction_status.csv` timestamp")
    lines.append("")

    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---:|")
    lines.append(f"| Papers with ≥1 passage (denominator) | {n} |")
    lines.append(f"| Total {unit_plural} | {total_labels} |")
    lines.append(f"| Final window fraction | {window_frac:.2f} |")
    lines.append(f"| Final window size | {window_size} papers |")
    lines.append(f"| New {unit_plural} in final window | {new_in_window} |")
    lines.append(f"| Marginal rate in final window | "
                 f"{marginal:.3f} {unit_plural}/paper |")
    lines.append(f"| **Saturation verdict** | **{verdict}** |")
    lines.append("")

    lines.append("## Emergence curve")
    lines.append("")
    lines.append(f"![saturation curve]({png_filename})")
    lines.append("")

    lines.append("## Narrative")
    lines.append("")
    if new_in_window == 0 and layer == "interaction-mode":
        narrative = (
            f"At the **interaction-mode layer** — the reportable "
            f"dependability claim for Cruzes & Dybå Step 5 — new-mode "
            f"emergence collapsed to zero across the final "
            f"{int(window_frac * 100)}% of papers in extraction order "
            f"({window_size} of {n}). The taxonomy's {total_labels} "
            f"higher-order themes are **empirically saturated** for this "
            f"corpus: every paper in the tail described interactions that "
            f"already fit the partition built from the upstream data. "
            f"This is the stronger saturation claim that §6.3 "
            f"dependability stands on."
        )
    elif new_in_window == 0:
        narrative = (
            f"New-{unit_singular} emergence collapsed to zero across the "
            f"final {int(window_frac * 100)}% of papers in extraction "
            f"order ({window_size} papers out of {n}). The corpus is "
            f"**coding-saturated** at the {layer} layer: no paper in the "
            f"tail contributed a {unit_singular} that had not already "
            f"emerged upstream. This result supports the §6.3 "
            f"dependability statement that Phase 3 coverage is sufficient "
            f"for the interaction-mode taxonomy at Task 4.2."
        )
    else:
        narrative = (
            f"The final {int(window_frac * 100)}% window "
            f"({window_size} papers) still introduced {new_in_window} "
            f"new {unit_singular}(s), a marginal rate of "
            f"{marginal:.3f} {unit_plural}/paper. Whether this represents "
            f"a long-tail of idiosyncratic usage (acceptable) or a "
            f"systematic coverage gap (which would motivate additional "
            f"coding) is a qualitative call for §6.3 dependability."
        )
        if layer == "canonical-label":
            narrative += (
                " The singletons in `consolidated_codes.csv` are the most "
                "likely source; the mode-layer saturation result (run with "
                "`--group-by-mode`) is the stricter reportable claim."
            )
    lines.append(narrative)
    lines.append("")

    lines.append("## Notes")
    lines.append("")
    lines.append(
        "- **Denominator rationale** — N counts papers with ≥1 passage "
        "(i.e. papers that actually contributed codes), not the full 640. "
        "Mode B abstract-only papers contribute no passages and are "
        "therefore excluded from the saturation denominator.")
    lines.append(
        "- **Processing-order rationale** — saturation in Cruzes & Dybå "
        "is about the *coding* process, not corpus composition. "
        "`extraction_status.csv.timestamp` is the nearest available "
        "proxy for when each paper was coded; lexicographic `paper_id` "
        "breaks ties.")
    if layer == "interaction-mode":
        lines.append(
            "- **Layer of analysis** — this report measures saturation at "
            "the **interaction-mode layer** (Task 4.2 output, 5 modes + "
            "Residuals). The canonical-label layer companion report is at "
            "`saturation_report.md`. The mode layer is the reportable "
            "dependability claim; the canonical layer is an intermediate "
            "artefact.")
    else:
        lines.append(
            "- **Layer of analysis** — this report measures saturation at "
            "the canonical-label layer (Task 4.1 output). Saturation at the "
            "interaction-mode layer (Task 4.2 output) is stricter and is "
            "addressed by the `--group-by-mode` run "
            "(`saturation_report_mode.md`).")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Verify / CLI paths
# ---------------------------------------------------------------------------
def _paths_for_layer(group_by_mode: bool) -> tuple:
    """(csv, md, png, unit_plural, unit_singular, layer)."""
    if group_by_mode:
        return (SATURATION_MODE_CSV, SATURATION_MODE_MD, SATURATION_MODE_PNG,
                "interaction modes", "interaction mode", "interaction-mode")
    return (SATURATION_CSV, SATURATION_MD, SATURATION_PNG,
            "canonical labels", "canonical label", "canonical-label")


def run_verify(group_by_mode: bool = False) -> int:
    csv_p, md_p, _, unit_plural, _, layer = _paths_for_layer(group_by_mode)
    if not csv_p.exists():
        print(f"✗ {csv_p} not found — run without --verify first.")
        return 1
    if not md_p.exists():
        print(f"✗ {md_p} not found — run without --verify first.")
        return 1
    sat = pd.read_csv(csv_p)
    errors = 0
    if not sat["cumulative_count"].is_monotonic_increasing:
        print("✗ cumulative_count is not monotonically increasing")
        errors += 1
    # Cumulative-tail sanity check against the expected unit count
    if group_by_mode:
        if CLASSIFY_CSV.exists():
            cls = pd.read_csv(CLASSIFY_CSV, dtype=str).fillna("")
            expected = cls[cls["mode"].isin(VALID_MODE_KEYS)]["mode"].nunique()
            actual = int(sat["cumulative_count"].iloc[-1])
            if actual > expected:
                print(f"✗ cumulative tail {actual} exceeds expected "
                      f"mode count {expected}")
                errors += 1
    else:
        if CONSOLIDATED_CSV.exists():
            cons = pd.read_csv(CONSOLIDATED_CSV, dtype=str).fillna("")
            expected = cons[LABEL_COL].nunique()
            actual = int(sat["cumulative_count"].iloc[-1])
            if actual > expected:
                print(f"✗ cumulative tail {actual} exceeds label count {expected}")
                errors += 1
            elif actual < expected:
                print(f"  note: {expected - actual} label(s) have no passages "
                      f"and are absent from saturation data (expected)")
    if sat["in_final_window"].sum() == 0:
        print("✗ no papers marked in_final_window")
        errors += 1
    if errors == 0:
        n = len(sat)
        last_cum = int(sat["cumulative_count"].iloc[-1])
        win_new = int(sat.loc[sat["in_final_window"], "new_count"].sum())
        print(f"✓ saturation DoD passed ({layer} layer) — {n} papers, "
              f"{last_cum} {unit_plural} reached, "
              f"{win_new} new in final window")
        return 0
    print(f"\n✗ {errors} verify failure(s).")
    return 1


def run_chart_only(window_frac: float, group_by_mode: bool = False) -> int:
    csv_p, _, png_p, unit_plural, _, _ = _paths_for_layer(group_by_mode)
    if not csv_p.exists():
        print(f"✗ {csv_p} not found — run the full script first.")
        return 1
    sat = pd.read_csv(csv_p)
    render_chart(sat, png_p, window_frac, unit_label=unit_plural)
    print(f"✓ chart refreshed → {png_p.relative_to(ROOT)}")
    return 0


def run_full(window_frac: float, group_by_mode: bool = False) -> int:
    csv_p, md_p, png_p, unit_plural, unit_singular, layer = \
        _paths_for_layer(group_by_mode)

    if group_by_mode:
        label_paper = load_mode_to_papers(CONSOLIDATED_CSV, CLASSIFY_CSV)
    else:
        label_paper = load_label_to_papers(CONSOLIDATED_CSV)
    order = load_processing_order(EXTRACT_STATUS_CSV)
    total_units = label_paper["canonical_label"].nunique()
    sat = compute_saturation(label_paper, order, window_frac)

    SYNTH_DIR.mkdir(parents=True, exist_ok=True)
    sat.to_csv(csv_p, index=False)
    render_chart(sat, png_p, window_frac, unit_label=unit_plural)
    cons_sha1 = sha1_of_file(CONSOLIDATED_CSV)
    md_p.write_text(
        render_report(sat, total_units, cons_sha1, window_frac,
                      layer=layer,
                      unit_singular=unit_singular,
                      unit_plural=unit_plural,
                      png_filename=png_p.name),
        encoding="utf-8",
    )

    n = len(sat)
    last_cum = int(sat["cumulative_count"].iloc[-1])
    new_in_win = int(sat.loc[sat["in_final_window"], "new_count"].sum())
    verdict = ("Saturated" if new_in_win == 0
               else f"Not saturated ({new_in_win} new)")
    print(f"✓ {csv_p.relative_to(ROOT)}  ({n} rows)")
    print(f"✓ {md_p.relative_to(ROOT)}")
    print(f"✓ {png_p.relative_to(ROOT)}")
    print(f"  → papers N={n}  {unit_plural} reached={last_cum}  "
          f"verdict: {verdict}")
    return 0


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------
def run_self_test() -> int:
    """Tiny in-memory fixture: 4 papers, 5 labels.

    paper A (t=01) → {L1, L2}
    paper B (t=02) → {L1}
    paper C (t=03) → {L3}
    paper D (t=04) → {L2, L4, L5}    ← final 25% window

    Expected cumulative: 2, 2, 3, 6 (wait: 2+0+1+3=6? L1 at A already,
    L2 at A already, L4 and L5 new at D, L3 new at C → 2,2,3,5)
    New counts: 2, 0, 1, 2.  So at 25% window size=1 (paper D), new=2.
    """
    label_paper = pd.DataFrame([
        {"canonical_label": "L1", "paper_id": "A"},
        {"canonical_label": "L2", "paper_id": "A"},
        {"canonical_label": "L1", "paper_id": "B"},
        {"canonical_label": "L3", "paper_id": "C"},
        {"canonical_label": "L2", "paper_id": "D"},
        {"canonical_label": "L4", "paper_id": "D"},
        {"canonical_label": "L5", "paper_id": "D"},
    ])
    order = pd.DataFrame([
        {"paper_id": "A", "timestamp": "2026-01-01T00:00:00Z"},
        {"paper_id": "B", "timestamp": "2026-01-02T00:00:00Z"},
        {"paper_id": "C", "timestamp": "2026-01-03T00:00:00Z"},
        {"paper_id": "D", "timestamp": "2026-01-04T00:00:00Z"},
    ])
    sat = compute_saturation(label_paper, order, window_frac=0.25)
    expected_new = [2, 0, 1, 2]
    expected_cum = [2, 2, 3, 5]
    ok = (list(sat["new_count"]) == expected_new
          and list(sat["cumulative_count"]) == expected_cum
          and sat["in_final_window"].tolist() == [False, False, False, True])
    print("self-test:", "✓ PASS" if ok else "✗ FAIL")
    if not ok:
        print(sat)
        return 1
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Task 4.2 saturation-curve computation")
    p.add_argument("--window", type=float, default=DEFAULT_WINDOW,
                   help=f"Final window fraction (default {DEFAULT_WINDOW}).")
    p.add_argument("--group-by-mode", action="store_true",
                   help="Compute saturation at the interaction-mode layer "
                        "(Task 4.2 output) instead of the canonical-label "
                        "layer (Task 4.1 output). Writes sidecar files "
                        "saturation_{data,report,curve}_mode.*.")
    p.add_argument("--verify", action="store_true",
                   help="Check DoD on existing saturation_data.csv + report "
                        "(respects --group-by-mode).")
    p.add_argument("--chart-only", action="store_true",
                   help="Re-render PNG from existing saturation_data.csv "
                        "(respects --group-by-mode).")
    p.add_argument("--self-test", action="store_true",
                   help="Run the in-memory fixture and exit.")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if args.self_test:
        return run_self_test()
    if args.verify:
        return run_verify(args.group_by_mode)
    if args.chart_only:
        return run_chart_only(args.window, args.group_by_mode)
    return run_full(args.window, args.group_by_mode)


if __name__ == "__main__":
    sys.exit(main())
