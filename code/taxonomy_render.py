"""Task 4.2 Step 5 — render interaction_taxonomy.md from the Step-4 partition.

Design: design/4_2_taxonomy_render.md

Reads:
    artifacts/synthesis/taxonomy_classifications.csv   (mode + residuals_subcategory)
    artifacts/synthesis/consolidated_codes.csv         (for member previews)
    artifacts/synthesis/interaction_taxonomy.md        (v0.2; salvage definitions)

Writes:
    artifacts/synthesis/interaction_taxonomy.md        (overwrites; backup is rater's job)

CLI:
    python code/taxonomy_render.py                # overwrite with fresh render
    python code/taxonomy_render.py --dry-run      # print to stdout only
    python code/taxonomy_render.py --verify       # structural + partition check
"""

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------
import argparse
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, str(ROOT))
from code.taxonomy_classify import MODES  # noqa: E402

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SYNTH_DIR        = ROOT / "artifacts" / "synthesis"
CLASSIFY_CSV     = SYNTH_DIR / "taxonomy_classifications.csv"
CONSOLIDATED_CSV = SYNTH_DIR / "consolidated_codes.csv"
TAXONOMY_MD      = SYNTH_DIR / "interaction_taxonomy.md"

VALID_MODE_KEYS  = {"1", "2", "3", "4", "5"}
VALID_RESID_SUBS = ["outcome", "affordance", "constraint", "meta"]
SUB_TITLES       = {
    "outcome":    "Outcome",
    "affordance": "Affordance / Surface",
    "constraint": "Constraint",
    "meta":       "Meta-observation",
}

# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------
def utcnow_iso_date() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def escape_pipe(s: str) -> str:
    return (s or "").replace("|", r"\|")


def mode_name(key: str) -> str:
    for m in MODES:
        if m["key"] == key:
            return m["name"]
    return "(unknown)"


def mode_gloss(key: str) -> str:
    for m in MODES:
        if m["key"] == key:
            return m["gloss"]
    return ""


# ---------------------------------------------------------------------------
# Load + validate partition
# ---------------------------------------------------------------------------
def load_partition() -> pd.DataFrame:
    if not CLASSIFY_CSV.exists():
        raise FileNotFoundError(
            f"{CLASSIFY_CSV} not found - run Step 4 (taxonomy_classify_llmassist.py).")
    if not CONSOLIDATED_CSV.exists():
        raise FileNotFoundError(
            f"{CONSOLIDATED_CSV} not found - run Task 4.1.")

    cls  = pd.read_csv(CLASSIFY_CSV, dtype=str).fillna("")
    cons = pd.read_csv(CONSOLIDATED_CSV, dtype=str).fillna("")
    cons["cluster_size"] = cons["cluster_size"].astype(int)

    # Sanity: partition is 1:1 with consolidated
    missing = set(cons["canonical_label"]) - set(cls["canonical_label"])
    extras  = set(cls["canonical_label"]) - set(cons["canonical_label"])
    if missing or extras:
        raise ValueError(
            f"partition mismatch: {len(missing)} missing, {len(extras)} extra")

    # Residuals must have subcategory
    if "residuals_subcategory" not in cls.columns:
        raise ValueError(
            "taxonomy_classifications.csv missing 'residuals_subcategory' "
            "column - run "
            "`python code/taxonomy_classify_llmassist.py "
            "--subcategorise-residuals` first.")

    df = cls.merge(
        cons[["canonical_label", "cluster_size", "pass1_codes"]],
        on="canonical_label", how="left", suffixes=("", "_cons"))
    # cluster_size was already string in cls; take from cons
    df["cluster_size"] = df["cluster_size_cons"].astype(int)
    df = df.drop(columns=["cluster_size_cons"])
    return df


# ---------------------------------------------------------------------------
# Preserve blocks from the existing v0.2 markdown
# ---------------------------------------------------------------------------
MODE_HEADER_RE    = re.compile(r"^##\s+Mode\s+(\d+)\s+—\s+(.+?)\s*$", re.M)
SECTION_BREAK_RE  = re.compile(r"^(##\s|---\s*$)", re.M)


def _slice_mode_sections(text: str) -> dict:
    """Return {mode_key: section_text} for each '## Mode N ...' block."""
    out: dict = {}
    starts: list = []
    for m in MODE_HEADER_RE.finditer(text):
        starts.append((m.start(), m.group(1)))
    starts.append((len(text), None))
    for i in range(len(starts) - 1):
        begin, key = starts[i]
        end, _ = starts[i + 1]
        out[key] = text[begin:end]
    return out


def _extract_block(section: str, label: str) -> str:
    """Extract '**Label:** body' up to the next bold field or hrule/header.

    Returns an empty string if not found.
    """
    pattern = re.compile(
        rf"^\*\*{re.escape(label)}:\*\*\s*(.+?)(?=(?:\n\*\*[A-Z][^*\n]+:\*\*)"
        rf"|(?:\n##\s)|(?:\n---\s*$)|(?:\Z))",
        re.S | re.M,
    )
    m = pattern.search(section)
    return (m.group(1).strip() if m else "")


def _extract_section_body(text: str, heading_regex: str) -> str:
    """Return the body text for a top-level section matched by heading_regex,
    up to the next '## ' heading or end of file."""
    m = re.search(heading_regex, text, re.M)
    if not m:
        return ""
    start = m.end()
    nxt = re.search(r"\n##\s", text[start:])
    body = text[start: start + nxt.start()] if nxt else text[start:]
    return body.strip()


def salvage_preserved_blocks(prior_md: str) -> dict:
    """Extract what we want to carry forward from the v0.2 taxonomy markdown."""
    blocks = {
        "axis":         "",
        "residuals_intro": "",
        "next_steps":   "",
        "mode_ops":     {},     # {"1": "...", "2": "..."}
        "mode_crit":    {},
        "mode_notes":   {},     # misc rater notes per mode (free-form text)
    }
    if not prior_md:
        return blocks

    blocks["axis"] = _extract_section_body(
        prior_md, r"^##\s+Axis\b[^\n]*\n")
    blocks["residuals_intro"] = _extract_section_body(
        prior_md, r"^##\s+Residuals\s*/\s*Cross-Cutting\b[^\n]*\n")
    # Only keep the opening paragraph of the residuals section intro
    # (before any tables), since the member table will be regenerated.
    if blocks["residuals_intro"]:
        parts = re.split(r"\n\s*\*\*|\n\|", blocks["residuals_intro"], 1)
        blocks["residuals_intro"] = parts[0].strip()

    blocks["next_steps"] = _extract_section_body(
        prior_md, r"^##\s+Next steps\b[^\n]*\n")

    for mkey, section in _slice_mode_sections(prior_md).items():
        ops = _extract_block(section, "Operational definition")
        crit = _extract_block(section, "Distinguishing criteria")
        if ops:
            blocks["mode_ops"][mkey] = ops
        if crit:
            blocks["mode_crit"][mkey] = crit
        # Capture any inline "Rater note for Step 6: ..." lines
        notes = re.findall(
            r"^\*\*Rater note[^*]*:\*\*.*?(?=\n\n|\Z)",
            section, re.S | re.M)
        if notes:
            blocks["mode_notes"][mkey] = "\n\n".join(n.strip() for n in notes)
    return blocks


# ---------------------------------------------------------------------------
# Emit
# ---------------------------------------------------------------------------
def _fmt_row(i: int, row: pd.Series) -> str:
    """One markdown table row for a canonical-label entry."""
    lbl     = escape_pipe(row["canonical_label"])
    size    = int(row["cluster_size"])
    source  = escape_pipe(row.get("source", "") or "-")
    notes   = escape_pipe(row.get("notes", "") or "")
    notes   = notes if notes else "—"
    return f"| {i} | {lbl} | {size} | {source} | {notes} |"


def _fmt_mode_table(df_mode: pd.DataFrame) -> str:
    if df_mode.empty:
        return "_(no canonical labels in this mode)_"
    lines = [
        "| # | Canonical label | Size | Source | Notes |",
        "|---:|---|---:|---|---|",
    ]
    ordered = df_mode.sort_values(
        ["cluster_size", "canonical_label"], ascending=[False, True]
    ).reset_index(drop=True)
    for i, row in ordered.iterrows():
        lines.append(_fmt_row(i + 1, row))
    return "\n".join(lines)


def _render_mode_section(key: str, df_mode: pd.DataFrame,
                         preserved: dict) -> str:
    name = mode_name(key)
    n = len(df_mode)
    total_members = int(df_mode["cluster_size"].sum()) if n else 0
    ops = preserved["mode_ops"].get(
        key, f"[TO-WRITE BY RATER AT STEP 5] {mode_gloss(key)}")
    crit = preserved["mode_crit"].get(
        key,
        "[TO-WRITE BY RATER AT STEP 5]\n"
        "- IS: …\n"
        "- IS NOT: …")
    notes = preserved["mode_notes"].get(key, "")

    out = []
    out.append(f"## Mode {key} — {name}\n")
    out.append(f"**Operational definition:** {ops}\n")
    out.append(f"**Distinguishing criteria:**\n{crit}\n")
    out.append(
        f"**Canonical labels grouped under this mode "
        f"({n} labels, {total_members} member pass-1 codes):**\n")
    out.append(_fmt_mode_table(df_mode) + "\n")
    if notes:
        out.append(notes + "\n")
    out.append(
        "**Exemplars (paraphrased — Step 6 will fill):**\n\n"
        "1. _placeholder — trace TBD_\n"
        "2. _placeholder — trace TBD_\n")
    return "\n".join(out)


def _render_residuals_section(df_r: pd.DataFrame,
                              preserved_intro: str) -> str:
    intro = preserved_intro or (
        "These canonical labels describe **outcomes, affordances, "
        "constraints, or meta-observations that cut across interaction "
        "modes** — they are evidence *about* interactions, not modes of "
        "interaction themselves. Per `design/4_2_taxonomy_classify.md §4`, "
        "each is retained here with a sub-category (outcome / affordance / "
        "constraint / meta) derived from an LLM-assisted post-pass. The "
        "sub-axis is analytic, not epistemic: all four sub-categories "
        "sit outside the 5-mode partition.")
    out = [f"## Residuals / Cross-Cutting Evidence\n", intro + "\n"]
    total = len(df_r)
    out.append(f"**Total: {total} canonical labels** across 4 sub-categories "
               f"(LLM-sub-classified, rater-adjudicated at Step 4 level).\n")

    for sub in VALID_RESID_SUBS:
        sub_df = df_r[df_r["residuals_subcategory"] == sub]
        if sub_df.empty:
            continue
        title = SUB_TITLES.get(sub, sub.title())
        out.append(f"### {title} ({len(sub_df)} labels)\n")
        out.append(_fmt_mode_table(sub_df) + "\n")

    # Unresolved bucket
    unresolved = df_r[~df_r["residuals_subcategory"].isin(VALID_RESID_SUBS)]
    if not unresolved.empty:
        out.append(f"### ⚠ Unresolved ({len(unresolved)} labels)\n")
        out.append(
            "These Residuals did not receive a sub-category. Re-run "
            "`python code/taxonomy_classify_llmassist.py "
            "--subcategorise-residuals --refresh-resid-llm` or assign by "
            "hand.\n")
        out.append(_fmt_mode_table(unresolved) + "\n")

    return "\n".join(out)


def _render_transition_appendix(df: pd.DataFrame) -> str:
    """Consolidated Step-3 → Step-4 transition notes.

    Per Q4, pull carry-forward audit material into one appendix:
      - Counts per source (step3 / step4 / step4_llmassist)
      - LLM-override rows (notes containing 'overrode LLM')
      - Any flagged ambiguities (notes containing 'Mode 4 or 5', etc.)
    """
    src_counts = Counter(df["source"].fillna("").tolist())
    total = len(df)
    overrides = df[df["notes"].fillna("").str.contains("overrode LLM")]

    out = ["## Step-3 → Step-4 transition notes (audit appendix)\n"]
    out.append(
        "This appendix consolidates provenance material that was inline "
        "in the v0.2 strawman. Mode sections above stay clean; the audit "
        "trail is captured here so reviewers can reconstruct decisions "
        "without chasing comments across mode tables.\n")
    out.append("**Provenance tally:**\n")
    out.append("| Source | Rows | Meaning |")
    out.append("|---|---:|---|")
    rows = [
        ("step3", "Step-3 top-40 strawman placement (rater)"),
        ("step4_llmassist", "Step-4 LLM-assisted placement (rater-confirmed)"),
        ("step4", "Step-4 manual placement (pre-LLM-assist base script)"),
        ("", "Unsourced (should be 0)"),
    ]
    for k, meaning in rows:
        n = src_counts.get(k, 0)
        pct = 100.0 * n / total if total else 0.0
        out.append(f"| `{k or '(blank)'}` | {n} ({pct:0.1f}%) | {meaning} |")
    out.append("")

    out.append(
        f"**LLM-override audit:** {len(overrides)} canonical label(s) where "
        f"the rater chose a mode different from the LLM's suggestion at "
        f"Step 4. These rows carry a `overrode LLM X -> Y` annotation in "
        f"`taxonomy_classifications.csv:notes`. Dependability-relevant; "
        f"see `decision_register.csv` for any substantive entries.\n")
    if not overrides.empty:
        out.append("| Canonical label | Mode | Size | Note |")
        out.append("|---|---|---:|---|")
        for _, r in overrides.sort_values(
                ["cluster_size", "canonical_label"],
                ascending=[False, True]).iterrows():
            out.append(
                f"| {escape_pipe(r['canonical_label'])} | {r['mode']} | "
                f"{int(r['cluster_size'])} | {escape_pipe(r['notes'])} |")
        out.append("")

    out.append(
        "**Step-3 v0.2 hand-written annotations:** merged/renamed/cross-"
        "referenced clusters and the Mode-4↔Mode-5 ambiguity flags are "
        "logged in `decision_register.csv` under rows "
        "`task4_2_canonical_merge`, `task4_2_canonical_rename`, and the "
        "forthcoming `taxonomy_finalised` row (Step 9).")
    return "\n".join(out)


def render_markdown(df: pd.DataFrame, preserved: dict,
                    rater: str) -> str:
    """Assemble the final markdown string."""
    # Header
    total = len(df)
    by_mode = df["mode"].value_counts().to_dict()
    resid_df = df[df["mode"] == "r"].copy()
    out = []
    out.append("# Interaction-Mode Taxonomy — RQ2 Deliverable\n")
    out.append(
        f"> **Status:** 🟡 v1.0 — Step-5 draft (auto-rendered from Step-4 "
        f"partition). Operational definitions flagged `[TO-WRITE BY RATER]` "
        f"need the rater pass; `[DRAFT]` definitions were preserved from "
        f"v0.2 and are ready for tightening.\n"
        f"> **Source:** `artifacts/synthesis/taxonomy_classifications.csv` "
        f"({total} canonical labels, Step-4 partition 19 Apr 2026).\n"
        f"> **Rater:** {rater}\n"
        f"> **Generated:** {utcnow_iso_date()} via `code/taxonomy_render.py`.\n"
        f"> **Corpus:** 290 papers with ≥1 raw passage (of 640 extracted; "
        f"350 Mode-B abstract-only papers excluded from coding denominator).\n"
        f"> **Saturation:** see `saturation_report.md`. Mode-layer "
        f"saturation to be recomputed at Step 8.\n")
    out.append("---\n")

    # Axis
    axis_body = preserved["axis"] or (
        "[TO-WRITE BY RATER AT STEP 5] Modes are ordered along a single "
        "ordinal axis: **the degree to which the human delegates the "
        "software-engineering task to the AI agent.**")
    out.append("## Axis — Delegation Depth\n")
    out.append(axis_body + "\n")
    out.append("---\n")

    # Mode summary table for quick navigation
    out.append("## Partition summary\n")
    out.append("| Mode | Name | Labels | % of 707 |")
    out.append("|---|---|---:|---:|")
    for key in ["1", "2", "3", "4", "5"]:
        n = by_mode.get(key, 0)
        pct = 100.0 * n / total if total else 0.0
        out.append(f"| {key} | {mode_name(key)} | {n} | {pct:0.1f}% |")
    r_n = by_mode.get("r", 0)
    r_pct = 100.0 * r_n / total if total else 0.0
    out.append(f"| r | Residuals / Cross-cutting | {r_n} | {r_pct:0.1f}% |")
    out.append(f"| **Total** | | **{total}** | **100.0%** |\n")
    out.append("---\n")

    # Mode sections
    for key in ["1", "2", "3", "4", "5"]:
        df_mode = df[df["mode"] == key]
        out.append(_render_mode_section(key, df_mode, preserved))
        out.append("---\n")

    # Residuals
    out.append(_render_residuals_section(
        resid_df, preserved["residuals_intro"]))
    out.append("---\n")

    # Transition audit appendix
    out.append(_render_transition_appendix(df))
    out.append("---\n")

    # Cross-refs
    out.append("## Cross-references\n")
    out.append(
        "- Live tracker: `task4_2_todo.md`\n"
        "- Phase tracker: `task4_tracker.md §3.2`\n"
        "- Task design: `design/4_2_interaction_taxonomy.md` (§4 schema = "
        "DoD contract)\n"
        "- Step-4 classifier design: `design/4_2_taxonomy_classify.md`, "
        "`design/4_2_taxonomy_classify_llmassist.md`\n"
        "- Step-4.5 sub-categorisation: "
        "`design/4_2_residuals_subcategorise.md`\n"
        "- Step-5 render: `design/4_2_taxonomy_render.md`\n"
        "- Input: `artifacts/synthesis/taxonomy_classifications.csv` "
        f"({total} rows), `artifacts/synthesis/consolidated_codes.csv` "
        "(707 canonical labels)\n"
        "- Proposal anchor: `docs/ERP2_Research_Proposal.docx` Appendix C "
        "Table 4 (8 illustrative modes)\n"
        "- Methodology: Cruzes & Dybå (2011) Step 4; Cruzes et al. (2015) §3\n")
    out.append("---\n")

    # Next steps
    next_body = preserved["next_steps"] or (
        "- [ ] **Step 5 (rater):** tighten operational definitions + "
        "IS/IS-NOT criteria in each Mode section (45–60 min).\n"
        "- [ ] **Step 6 (rater + Claude retrieval):** replace "
        "`_placeholder — trace TBD_` with paraphrased exemplars + "
        "`doi:...:P\\d{3}` traces, ≥2 per mode.\n"
        "- [ ] **Step 7 (Claude):** run `code/paraphrase_linter.py`; "
        "iterate until exit 0.\n"
        "- [ ] **Step 8 (Claude):** re-run saturation at mode layer.\n"
        "- [ ] **Step 9 (Claude + rater):** `check_phase4_task4_2` in "
        "`code/dod_checks.py`; tag `phase4-rc1`.\n")
    out.append("## Next steps (owner: rater)\n")
    out.append(next_body + "\n")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Verify
# ---------------------------------------------------------------------------
def run_verify() -> int:
    """Partition + residuals-subcategory integrity check.

    Structural-markdown checks are light: ensure the rendered file has
    the required ## Mode N -- sections and a Residuals section. A full
    DoD structural check belongs to code/dod_checks.py (Step 9).
    """
    errors = 0
    if not CLASSIFY_CSV.exists():
        print(f"[x] {CLASSIFY_CSV} not found.", file=sys.stderr)
        return 1
    cls  = pd.read_csv(CLASSIFY_CSV, dtype=str).fillna("")
    cons = pd.read_csv(CONSOLIDATED_CSV, dtype=str).fillna("")

    missing = set(cons["canonical_label"]) - set(cls["canonical_label"])
    extras  = set(cls["canonical_label"]) - set(cons["canonical_label"])
    if missing:
        print(f"[x] {len(missing)} canonical label(s) missing from partition")
        errors += 1
    if extras:
        print(f"[x] {len(extras)} label(s) in partition but not in consolidated")
        errors += 1

    valid_modes = {"1", "2", "3", "4", "5", "r"}
    bad = cls[~cls["mode"].isin(valid_modes)]
    if not bad.empty:
        print(f"[x] {len(bad)} row(s) with invalid mode")
        errors += 1

    if "residuals_subcategory" not in cls.columns:
        print("[x] missing 'residuals_subcategory' column — run "
              "`--subcategorise-residuals` first.")
        errors += 1
    else:
        r_rows = cls[cls["mode"] == "r"]
        bad_sub = r_rows[~r_rows["residuals_subcategory"].isin(VALID_RESID_SUBS)]
        if not bad_sub.empty:
            print(f"[x] {len(bad_sub)} Residual(s) without a valid sub-category")
            errors += 1
        non_r = cls[(cls["mode"] != "r") &
                    (cls["residuals_subcategory"] != "")]
        if not non_r.empty:
            print(f"[x] {len(non_r)} non-Residual row(s) with a "
                  f"sub-category set")
            errors += 1

    if TAXONOMY_MD.exists():
        md = TAXONOMY_MD.read_text(encoding="utf-8")
        required = [
            ("# Interaction-Mode Taxonomy",       "title"),
            ("## Axis",                           "axis section"),
            ("## Mode 1 —",                       "Mode 1 section"),
            ("## Mode 2 —",                       "Mode 2 section"),
            ("## Mode 3 —",                       "Mode 3 section"),
            ("## Mode 4 —",                       "Mode 4 section"),
            ("## Mode 5 —",                       "Mode 5 section"),
            ("## Residuals",                      "Residuals section"),
        ]
        for needle, what in required:
            if needle not in md:
                print(f"[x] taxonomy.md missing: {what}")
                errors += 1

    if errors == 0:
        print(f"[OK] partition verify passed: "
              f"{len(cls)} labels, modes "
              f"{sorted(cls['mode'].unique().tolist())}, "
              f"residual sub-categories OK.")
        print(cls["mode"].value_counts().to_string())
        return 0
    return 1


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Task 4.2 Step 5 — render interaction_taxonomy.md "
                    "from the Step-4 partition.")
    p.add_argument("--dry-run", action="store_true",
                   help="Print the rendered markdown to stdout; do not "
                        "overwrite interaction_taxonomy.md.")
    p.add_argument("--verify", action="store_true",
                   help="Partition + structural-markdown check on current "
                        "artefacts; do not render.")
    p.add_argument("--rater", type=str, default="TBS",
                   help="Rater initials for the header (default TBS).")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if args.verify:
        return run_verify()

    df = load_partition()
    prior_md = TAXONOMY_MD.read_text(encoding="utf-8") if TAXONOMY_MD.exists() else ""
    preserved = salvage_preserved_blocks(prior_md)
    md = render_markdown(df, preserved, args.rater)

    if args.dry_run:
        print(md)
        return 0

    SYNTH_DIR.mkdir(parents=True, exist_ok=True)
    tmp = TAXONOMY_MD.with_suffix(".md.tmp")
    tmp.write_text(md, encoding="utf-8")
    tmp.replace(TAXONOMY_MD)

    print(f"[OK] rendered {TAXONOMY_MD.relative_to(ROOT)} "
          f"({len(md):,} chars; {md.count(chr(10)) + 1} lines).")
    print("  run  python code/taxonomy_render.py --verify  to sanity-check.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
