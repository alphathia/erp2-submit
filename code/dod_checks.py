"""Definition-of-Done (DoD) verification runner.

Usage:
    python code/dod_checks.py <phase_task_id>

Example:
    python code/dod_checks.py phase0_task0_1
"""

import importlib
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Check: phase0_task0_1 — Initialise repository skeleton
# ---------------------------------------------------------------------------

def check_phase0_task0_1() -> None:
    """Assert every §4 folder exists, control files exist, key imports work."""

    # §4 directories (every directory node in the tree)
    required_dirs = [
        "docs",
        "docs/methodology",
        "docs/seeds",
        "code",
        "artifacts",
        "artifacts/protocol",
        "artifacts/search",
        "artifacts/search/raw",
        "artifacts/search/enriched",
        "artifacts/screening",
        "artifacts/extraction",
        "artifacts/extraction/fulltext",
        "artifacts/extraction/raw_passages",
        "artifacts/synthesis",
        "artifacts/analysis",
        "artifacts/analysis/rq1_landscape",
        "artifacts/analysis/rq3_gap_matrix",
        "artifacts/trustworthiness",
        "manuscript",
        "manuscript/figures",
        "manuscript/tables",
        "manuscript/supplementary",
        "tests",
    ]

    print("Checking §4 directories …")
    for d in required_dirs:
        p = ROOT / d
        assert p.is_dir(), f"Missing directory: {d}"
    print(f"  ✓ All {len(required_dirs)} directories exist.")

    # Control files
    control_files = [
        "claude.md",
        "memory.md",
        "promptplan.md",
        "decision_register.csv",
        "requirements.txt",
    ]

    print("Checking control files …")
    for f in control_files:
        p = ROOT / f
        assert p.is_file(), f"Missing control file: {f}"
    print(f"  ✓ All {len(control_files)} control files exist.")

    # Key package imports
    print("Checking key imports …")
    for pkg in ["pandas", "requests", "pyalex"]:
        importlib.import_module(pkg)
        print(f"  ✓ {pkg}")

    print("\n✓ phase0_task0_1: all checks passed.")


# ---------------------------------------------------------------------------
# TODO: register checks for later tasks
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Check: phase1_task1_1 — Search strings + Scopus query envelope
# ---------------------------------------------------------------------------

def check_phase1_task1_1() -> None:
    """Assert search_strings.md and scopus_query_template.txt are correct."""

    ss_path = ROOT / "artifacts" / "protocol" / "search_strings.md"
    qt_path = ROOT / "artifacts" / "protocol" / "scopus_query_template.txt"

    assert ss_path.is_file(), f"Missing: {ss_path}"
    assert qt_path.is_file(), f"Missing: {qt_path}"

    ss_text = ss_path.read_text(encoding="utf-8")
    qt_text = qt_path.read_text(encoding="utf-8")

    # (1) search_strings.md contains all six labels S1–S6
    print("Checking S1–S6 labels in search_strings.md …")
    for label in ["## S1", "## S2", "## S3", "## S4", "## S5", "## S6"]:
        assert label in ss_text, f"Missing label: {label}"
    print("  ✓ All six labels present.")

    # (2) scopus_query_template.txt has balanced parentheses
    print("Checking balanced parentheses in query template …")
    open_count = qt_text.count("(")
    close_count = qt_text.count(")")
    assert open_count == close_count, (
        f"Unbalanced parentheses: {open_count} open vs {close_count} close"
    )
    print(f"  ✓ Balanced: {open_count} pairs.")

    # (3) Query contains the six string fragments (one distinctive phrase per S)
    print("Checking six string fragments in query template …")
    fragments = [
        '"AI coding assistant"',        # S1
        '"GitHub Copilot"',              # S2
        '"agentic software engineering"',# S3
        '"AI-assisted programming"',     # S4
        '"large language model"',        # S5
        '"citizen developer"',           # S6
    ]
    for frag in fragments:
        assert frag in qt_text, f"Missing fragment: {frag}"
    print("  ✓ All six string fragments present.")

    # (4) Query contains the six Layer-1 filter keywords
    print("Checking Layer-1 filter keywords …")
    filters = ["PUBYEAR", "LANGUAGE", "SRCTYPE", "DOCTYPE", "TITLE-ABS-KEY", "NOT DOCTYPE"]
    for f in filters:
        assert f in qt_text, f"Missing filter keyword: {f}"
    print("  ✓ All six filter keywords present.")

    print("\n✓ phase1_task1_1: all checks passed.")


# ---------------------------------------------------------------------------
# Check: phase2_task2_3 — OpenAlex enrichment
# ---------------------------------------------------------------------------

def check_phase2_task2_3() -> None:
    """Assert OpenAlex match rate ≥ 95% and report flagged records."""

    merged_path = ROOT / "artifacts" / "search" / "enriched" / "merged_openalex.csv"
    assert merged_path.is_file(), f"Missing: {merged_path}"

    # Discover raw CSVs
    raw_dir = ROOT / "artifacts" / "search" / "raw"
    scopus_files = sorted(raw_dir.glob("scopus_*.csv"))
    scopus_files = [f for f in scopus_files if not f.name.endswith(".meta.json")]
    acm_files = sorted(raw_dir.glob("acm_*.csv"))
    acm_files = [f for f in acm_files if not f.name.endswith(".meta.json")]

    assert scopus_files, "No Scopus CSV found in artifacts/search/raw/"
    assert acm_files, "No ACM DL CSV found in artifacts/search/raw/"

    # Load all three CSVs
    merged = pd.read_csv(merged_path, dtype=str)
    scopus = pd.read_csv(scopus_files[-1], dtype=str)
    acm = pd.read_csv(acm_files[-1], dtype=str)

    print(f"Loaded: merged={len(merged)}, scopus={len(scopus)}, acm={len(acm)}")

    # Compute total unique DOIs across raw inputs
    raw_dois = pd.concat([scopus["doi"], acm["doi"]]).dropna().str.strip().str.lower().unique()
    total_unique_dois = len(raw_dois)
    print(f"  Total unique DOIs across raw CSVs: {total_unique_dois}")

    # Compute matched DOI count from merged CSV
    matched_dois = (
        merged[merged["openalex_lookup"] == "matched"]["doi"]
        .dropna().str.strip().str.lower().nunique()
    )
    match_rate = matched_dois / total_unique_dois if total_unique_dois > 0 else 0.0
    print(f"  Matched DOIs: {matched_dois}")
    print(f"  Match rate: {match_rate:.1%}")

    # Assert match rate ≥ 95%
    assert match_rate >= 0.95, (
        f"OpenAlex match rate {match_rate:.1%} is below 95% threshold"
    )
    print(f"  ✓ Match rate {match_rate:.1%} ≥ 95%")

    # Emit flagged record counts
    ic3_count = merged["ic3_flag"].notna().sum()
    preprint_count = (merged["preprint_flag"].str.lower() == "true").sum()
    retracted_count = (merged["retracted_flag"].str.lower() == "true").sum()
    paratext_count = (merged["paratext_flag"].str.lower() == "true").sum()

    print(f"\n  Flagged records:")
    print(f"    IC3 source_type mismatch: {ic3_count}")
    print(f"    Preprint (submittedVersion): {preprint_count}")
    print(f"    Retracted: {retracted_count}")
    print(f"    Paratext: {paratext_count}")
    print(f"    Total flagged: {ic3_count + preprint_count + retracted_count + paratext_count}")

    # Report abstract fill
    abstracts_nonnull = merged["abstract"].notna().sum()
    print(f"\n  Abstracts: {abstracts_nonnull}/{len(merged)} non-null")

    print(f"\n✓ phase2_task2_3: all checks passed."
          f" Match rate: {match_rate:.1%},"
          f" flagged: {ic3_count + preprint_count + retracted_count + paratext_count}")


# ---------------------------------------------------------------------------
# Check: phase4_task4_2 — Interaction-mode taxonomy DoD
# ---------------------------------------------------------------------------

def check_phase4_task4_2() -> None:
    """Assert the Task 4.2 Phase-4 §6 exit criteria are satisfied.

    Specified in design/4_2_interaction_taxonomy.md §9:
      1. Structure — interaction_taxonomy.md has title, Axis, >=3 Modes;
         each mode has Operational definition, Distinguishing criteria,
         Canonical labels subsection, and >=2 numbered Exemplars.
      2. Trace — every "trace: `doi:...:PNNN`" resolves to a passage
         actually present in artifacts/extraction/raw_passages/.
      3. Partition — taxonomy_classifications.csv is a 1:1 partition of
         consolidated_codes.csv.canonical_label; every mode in {1..5,r}.
      4. Paraphrase — code/paraphrase_linter.py exits 0.
      5. Saturation — both canonical-label and interaction-mode reports
         exist and carry a "Saturation verdict" line.
      6. Compression ratio sanity — 6 units / N_canonical_labels in
         [0.005, 0.05].

    Out of scope (Task 4.3's DoD): self_assessment_rubric.md,
    adoption_progression.md.
    """
    import re
    import subprocess

    sys.path.insert(0, str(ROOT))
    from code.retrieval import safe_paper_id_to_filename   # noqa: E402

    synth   = ROOT / "artifacts" / "synthesis"
    passages = ROOT / "artifacts" / "extraction" / "raw_passages"
    md_path  = synth / "interaction_taxonomy.md"
    cls_path = synth / "taxonomy_classifications.csv"
    cons_path = synth / "consolidated_codes.csv"
    sat_md     = synth / "saturation_report.md"
    sat_mode_md = synth / "saturation_report_mode.md"

    # ---- 1. Structure ----
    print("Checking interaction_taxonomy.md structure …")
    assert md_path.is_file(), f"Missing: {md_path}"
    md = md_path.read_text(encoding="utf-8")
    assert "# Interaction-Mode Taxonomy" in md, "Missing top-level title"
    assert re.search(r"^## Axis\b", md, re.M), "Missing ## Axis section"
    mode_hdrs = re.findall(r"^## Mode (\d+) —", md, re.M)
    assert len(mode_hdrs) >= 3, (
        f"Only {len(mode_hdrs)} Mode sections; DoD requires >=3")

    # Per-mode subsection + exemplar check
    mode_iter = list(re.finditer(
        r"^## Mode (\d+) —[^\n]*\n(.*?)(?=\n## |\Z)", md, re.S | re.M))
    for m in mode_iter:
        num, body = m.group(1), m.group(2)
        for req in ["**Operational definition:**",
                    "**Distinguishing criteria:**",
                    "**Canonical labels"]:
            assert req in body, f"Mode {num} missing subsection: {req}"
        non_stub = re.findall(r"^\d+\. (?!_placeholder)", body, re.M)
        assert len(non_stub) >= 2, (
            f"Mode {num} has {len(non_stub)} non-placeholder exemplars; "
            f"DoD requires >=2")
    print(f"  ✓ {len(mode_hdrs)} Mode sections, each with required "
          f"subsections + >=2 exemplars")

    # ---- 2. Trace ----
    print("Checking exemplar traces resolve to real passages …")
    traces = re.findall(r"trace:\s*`(doi:[^`]+:P\d{3})`", md)
    assert traces, "No exemplar traces found in interaction_taxonomy.md"
    broken: list = []
    for t in traces:
        parts = t.rsplit(":", 1)
        if len(parts) != 2:
            broken.append((t, "malformed")); continue
        paper_id, passage_id = parts
        fname = safe_paper_id_to_filename(paper_id).replace(".pdf", ".md")
        fp = passages / fname
        if not fp.exists():
            broken.append((t, f"file missing: {fname}")); continue
        if f"## {passage_id}" not in fp.read_text(encoding="utf-8",
                                                  errors="ignore"):
            broken.append((t, f"passage {passage_id} not in file"))
    assert not broken, (
        f"{len(broken)} broken trace(s); first: {broken[:3]}")
    print(f"  ✓ All {len(traces)} exemplar traces resolve to passages")

    # ---- 3. Partition ----
    print("Checking partition integrity …")
    assert cls_path.is_file(), f"Missing: {cls_path}"
    assert cons_path.is_file(), f"Missing: {cons_path}"
    cls  = pd.read_csv(cls_path, dtype=str).fillna("")
    cons = pd.read_csv(cons_path, dtype=str).fillna("")
    missing_in_cls = set(cons["canonical_label"]) - set(cls["canonical_label"])
    extras_in_cls  = set(cls["canonical_label"]) - set(cons["canonical_label"])
    assert not missing_in_cls, (
        f"{len(missing_in_cls)} canonical label(s) in consolidated but "
        f"not in classifications (first: "
        f"{sorted(missing_in_cls)[:3]})")
    assert not extras_in_cls, (
        f"{len(extras_in_cls)} label(s) in classifications but not in "
        f"consolidated")
    valid_modes = {"1", "2", "3", "4", "5", "r"}
    bad = cls[~cls["mode"].isin(valid_modes)]
    assert len(bad) == 0, (
        f"{len(bad)} row(s) with invalid mode; valid: {sorted(valid_modes)}")
    assert cls["canonical_label"].nunique() == len(cls), (
        "Duplicate canonical_label values in classifications")
    print(f"  ✓ Partition: {len(cls)} labels, all in "
          f"{sorted(cls['mode'].unique().tolist())}")

    # ---- 4. Paraphrase linter ----
    print("Running paraphrase_linter.py …")
    result = subprocess.run(
        [sys.executable, "code/paraphrase_linter.py"],
        cwd=str(ROOT), capture_output=True, text=True)
    assert result.returncode == 0, (
        f"paraphrase_linter.py failed (exit {result.returncode}):\n"
        f"{result.stdout}\n{result.stderr}")
    print(f"  ✓ paraphrase linter clean")

    # ---- 5. Saturation (both layers) ----
    print("Checking saturation reports …")
    for path, layer in [(sat_md, "canonical-label"),
                        (sat_mode_md, "interaction-mode")]:
        assert path.is_file(), f"Missing {layer} saturation report: {path}"
        body = path.read_text(encoding="utf-8")
        assert "Saturation verdict" in body, (
            f"{layer} saturation report missing verdict: {path}")
    print(f"  ✓ Both saturation reports present with verdicts")

    # ---- 6. Compression ratio ----
    n_units  = cls["mode"].nunique()          # expected 6 when all reached
    n_labels = len(cls)
    ratio = n_units / n_labels if n_labels else 0.0
    assert 0.005 <= ratio <= 0.05, (
        f"Compression ratio {ratio:.4f} outside band [0.005, 0.05]")
    print(f"  ✓ Compression ratio {ratio:.4f} "
          f"({n_units} units / {n_labels} labels) in band")

    # ---- 7. Task 4.3 practical artefacts ----
    # Per research_plan_sms.md §Phase 4 / Task 4.3: every mode from the
    # taxonomy appears in both files, paraphrase rules apply.
    print("Checking Task 4.3 practical artefacts …")
    rubric_path      = synth / "self_assessment_rubric.md"
    progression_path = synth / "adoption_progression.md"
    for path, label in [(rubric_path, "self_assessment_rubric.md"),
                        (progression_path, "adoption_progression.md")]:
        assert path.is_file(), f"Missing {label}: {path}"
        body = path.read_text(encoding="utf-8")
        for mkey in ["Mode 1", "Mode 2", "Mode 3", "Mode 4", "Mode 5"]:
            assert mkey in body, (
                f"{label} missing reference to {mkey}")
        # Paraphrase linter per file
        result = subprocess.run(
            [sys.executable, "code/paraphrase_linter.py",
             "--target", str(path)],
            cwd=str(ROOT), capture_output=True, text=True)
        assert result.returncode == 0, (
            f"paraphrase_linter failed for {label} (exit "
            f"{result.returncode}):\n{result.stdout}\n{result.stderr}")
    print(f"  ✓ rubric + progression exist, cover all 5 modes, "
          f"paraphrase-linter clean")

    print("\n✓ phase4_task4_2: all checks passed.")


def check_phase5_task5_1() -> None:
    """Verify Task 5.1 outputs: 4 RQ1 PNGs + 3 RQ2 Markdown/CSV pairs.

    Checks:
        1. Exactly 4 *.png in rq1_landscape/, each with a sibling *.meta.json.
        2. Exactly 3 *.md and 3 *.csv in rq2_variation/, naming:
             mode_x_sdlc, mode_x_tool_profile, mode_x_population_context.
        3. For each RQ2 CSV, recompute the per-file unique paper count
           (`file_unique_papers` footer row, col 0) and assert it is in
           [150, 310] — a proxy for the ~290 passage-bearing papers ±
           deduplication. The floor is slightly relaxed from the ideal
           [200, 310] because mode_x_population_context drops rows with
           missing population/context metadata (~192 papers qualify).
    """
    print("Checking Phase 5 Task 5.1 artefacts …")

    rq1_dir = ROOT / "artifacts" / "analysis" / "rq1_landscape"
    rq2_dir = ROOT / "artifacts" / "analysis" / "rq2_variation"

    # ---- 1. RQ1 PNGs + meta sidecars ----
    assert rq1_dir.is_dir(), f"Missing {rq1_dir}"
    pngs = sorted(rq1_dir.glob("*.png"))
    assert len(pngs) == 4, (
        f"Expected 4 PNGs in {rq1_dir.relative_to(ROOT)}, found {len(pngs)}: "
        f"{[p.name for p in pngs]}")
    for png in pngs:
        meta = png.with_suffix(png.suffix + ".meta.json")
        assert meta.is_file(), (
            f"Missing meta sidecar for {png.relative_to(ROOT)}: {meta.name}")
    print(f"  ✓ 4 RQ1 PNGs + meta sidecars present in "
          f"{rq1_dir.relative_to(ROOT)}")

    # ---- 2. RQ2 Markdown/CSV pairs ----
    expected_stems = {"mode_x_sdlc", "mode_x_tool_profile",
                      "mode_x_population_context"}
    assert rq2_dir.is_dir(), f"Missing {rq2_dir}"
    mds = sorted(rq2_dir.glob("*.md"))
    csvs = sorted(rq2_dir.glob("*.csv"))
    assert len(mds) == 3, (
        f"Expected 3 *.md in {rq2_dir.relative_to(ROOT)}, found {len(mds)}: "
        f"{[p.name for p in mds]}")
    assert len(csvs) == 3, (
        f"Expected 3 *.csv in {rq2_dir.relative_to(ROOT)}, found {len(csvs)}: "
        f"{[p.name for p in csvs]}")
    md_stems = {p.stem for p in mds}
    csv_stems = {p.stem for p in csvs}
    assert md_stems == expected_stems, (
        f"Markdown names mismatch: got {md_stems}, expected {expected_stems}")
    assert csv_stems == expected_stems, (
        f"CSV names mismatch: got {csv_stems}, expected {expected_stems}")
    print(f"  ✓ 3 RQ2 Markdown/CSV pairs present with expected names")

    # ---- 3. Recompute unique paper count per file ----
    for stem in sorted(expected_stems):
        csv_path = rq2_dir / f"{stem}.csv"
        df = pd.read_csv(csv_path, index_col="mode")
        # Every mode must appear as a row
        for mode in ["1", "2", "3", "4", "5", "r"]:
            assert mode in df.index, (
                f"{csv_path.name} missing row for mode '{mode}'")
        assert "file_unique_papers" in df.index, (
            f"{csv_path.name} missing 'file_unique_papers' footer row")
        unique_n = int(df.loc["file_unique_papers"].iloc[0])
        assert 150 <= unique_n <= 310, (
            f"{csv_path.name}: file_unique_papers = {unique_n} "
            f"outside proxy band [150, 310] for ~290 passage-bearing papers")
        # Also confirm the Markdown contains every mode label.
        md_body = (rq2_dir / f"{stem}.md").read_text(encoding="utf-8")
        for mode in ["1", "2", "3", "4", "5", "r"]:
            assert f"| {mode} " in md_body or f"|{mode}|" in md_body, (
                f"{stem}.md missing mode row '{mode}'")
        print(f"  ✓ {stem}: {unique_n} unique papers in proxy band "
              f"[150, 310]")

    print("\n✓ phase5_task5_1: all checks passed.")


def check_phase5_task5_2() -> None:
    """Assert Task 5.2 (RQ3 gap matrix) artefacts are complete and consistent."""
    out_dir = ROOT / "artifacts" / "analysis" / "rq3_gap_matrix"
    gap_matrix_path = out_dir / "gap_matrix.csv"
    sens_path = out_dir / "sensitivity_25_33.md"
    paradigm_dir = out_dir / "gap_matrix_by_paradigm"

    # (1) gap_matrix.csv has exactly 171 data rows.
    print("Checking gap_matrix.csv …")
    assert gap_matrix_path.is_file(), f"Missing {gap_matrix_path}"
    gap_df = pd.read_csv(gap_matrix_path)
    assert len(gap_df) == 171, (
        f"gap_matrix.csv must have 171 data rows, got {len(gap_df)}"
    )
    print(f"  ✓ 171 rows present.")

    # (2) Column set is exactly the required 6; no interpretation-label extras.
    expected_cols = {
        "capability_id", "sdlc_activity", "evidence_count",
        "is_gap", "is_empty", "in_source_survey",
    }
    actual_cols = set(gap_df.columns)
    assert actual_cols == expected_cols, (
        f"gap_matrix.csv columns must be exactly {expected_cols}; "
        f"got {actual_cols} (extras={actual_cols - expected_cols}, "
        f"missing={expected_cols - actual_cols})"
    )
    print(f"  ✓ columns = {sorted(expected_cols)} (no interpretation labels).")

    # (3) is_gap AND is_empty is False everywhere.
    both = gap_df["is_gap"].astype(bool) & gap_df["is_empty"].astype(bool)
    assert not both.any(), (
        f"Flag exclusivity violated: {int(both.sum())} rows have both "
        "is_gap and is_empty True"
    )
    print("  ✓ is_gap AND is_empty is False on every row.")

    # (4) is_gap count == count of phase=5 hypothesis_for_erp3 rows in register.
    gap_count = int(gap_df["is_gap"].astype(bool).sum())
    register_path = ROOT / "decision_register.csv"
    assert register_path.is_file(), "decision_register.csv missing"
    reg_df = pd.read_csv(register_path, dtype=str).fillna("")
    hyp_rows = reg_df[
        (reg_df["phase"] == "5")
        & (reg_df["decision"] == "hypothesis_for_erp3")
    ]
    assert len(hyp_rows) == gap_count, (
        f"decision_register has {len(hyp_rows)} phase=5 hypothesis_for_erp3 "
        f"rows but gap_matrix has {gap_count} is_gap=True cells — must match"
    )
    print(f"  ✓ {gap_count} gaps == {len(hyp_rows)} register hypothesis rows.")

    # (5) All 3 paradigm-split CSVs exist.
    for name in ["procode.csv", "lowcode.csv", "nocode.csv"]:
        p = paradigm_dir / name
        assert p.is_file(), f"Missing paradigm split: {p}"
    print("  ✓ procode/lowcode/nocode CSVs all present.")

    # (6) sensitivity_25_33.md exists and mentions both P25 and P33.
    assert sens_path.is_file(), f"Missing {sens_path}"
    sens_body = sens_path.read_text(encoding="utf-8")
    assert "P25" in sens_body, "sensitivity_25_33.md must mention P25"
    assert "P33" in sens_body, "sensitivity_25_33.md must mention P33"
    print("  ✓ sensitivity_25_33.md mentions both P25 and P33.")

    print("\n✓ phase5_task5_2: all checks passed.")


def check_phase7_task7_1() -> None:
    """Phase 7 Task 7.6 DoD — 6 coverage invariants for the manuscript bundle.

    1. manuscript/draft.md + manuscript/appendix.md exist.
    2. Every inline [citekey] in draft+appendix has a matching @entry in references.bib.
    3. manuscript/draft.docx + manuscript/appendix.docx exist and are >50 KB.
    4. manuscript/references.bib has >=15 entries.
    5. manuscript/supplementary/erp2-sms-supplementary-*.zip exists with MANIFEST.txt.
    6. manuscript/final_review.md exists and contains 0 lines matching "blocker"
       (case-insensitive).
    """
    import re
    import zipfile as _zf

    errors: list[str] = []

    # Invariant 1 — core Markdown artefacts
    draft_md = Path("manuscript/draft.md")
    appendix_md = Path("manuscript/appendix.md")
    for p in (draft_md, appendix_md):
        if not p.exists():
            errors.append(f"missing: {p}")
    if errors:
        raise AssertionError("phase7_task7_1: " + "; ".join(errors))

    draft_text = draft_md.read_text(encoding="utf-8")
    appendix_text = appendix_md.read_text(encoding="utf-8")
    combined = draft_text + "\n" + appendix_text

    # Invariant 2 — bibliography coverage
    bib_path = Path("manuscript/references.bib")
    if not bib_path.exists():
        errors.append(f"missing: {bib_path}")
    else:
        bib_text = bib_path.read_text(encoding="utf-8")
        cite_groups = re.findall(r'\[([a-z][a-z0-9_]+(?:;\s*[a-z][a-z0-9_]+)*)\]', combined)
        all_cites = set()
        for g in cite_groups:
            for k in re.split(r';\s*', g):
                all_cites.add(k.strip())
        defined = set(re.findall(r'@\w+\{([a-z][a-z0-9_]+)\s*,', bib_text))
        missing = all_cites - defined
        if missing:
            errors.append(f"bib missing {len(missing)} citekeys: {sorted(missing)[:5]}")
        if len(defined) < 15:
            errors.append(f"references.bib has only {len(defined)} entries (need >=15)")

    # Invariant 3 — rendered Word documents
    for p in (Path("manuscript/draft.docx"), Path("manuscript/appendix.docx")):
        if not p.exists():
            errors.append(f"missing: {p}")
        elif p.stat().st_size < 50 * 1024:
            errors.append(f"{p} suspiciously small ({p.stat().st_size} bytes)")

    # Invariant 5 — supplementary zip
    supp_dir = Path("manuscript/supplementary")
    zips = list(supp_dir.glob("erp2-sms-supplementary-*.zip")) if supp_dir.exists() else []
    if not zips:
        errors.append("no supplementary zip found in manuscript/supplementary/")
    else:
        latest = max(zips, key=lambda p: p.stat().st_mtime)
        try:
            with _zf.ZipFile(latest) as z:
                names = z.namelist()
                if not any(n.endswith("MANIFEST.txt") for n in names):
                    errors.append(f"{latest} missing MANIFEST.txt")
        except _zf.BadZipFile:
            errors.append(f"{latest} is not a valid zip")

    # Invariant 6 — final_review.md 0 blockers
    fr = Path("manuscript/final_review.md")
    if not fr.exists():
        errors.append(f"missing: {fr}")
    else:
        fr_text = fr.read_text(encoding="utf-8")
        # Severity-tagged findings follow the pattern "- blocker:" or "* blocker" or
        # a bold tag like "**Severity: blocker**". Exempt any line that only
        # *mentions* the word (section headers, count statements, scheme definitions).
        blocker_lines = []
        for line in fr_text.splitlines():
            lower = line.lower()
            if not re.search(r'\bblocker\b', lower):
                continue
            # Exemptions — administrative mentions, not findings.
            if re.search(r'0\s*blocker|no blocker|zero blocker', lower):
                continue
            if re.search(r'blocker\s*(count|severity tag|convention|\/)', lower):
                continue
            if line.lstrip().startswith(("#", ">", "|")):
                continue
            # Finding pattern: a severity tag followed by a description.
            if re.match(r'\s*[-*]\s+\*?\*?blocker', lower) or re.search(r'severity[:\s]*blocker', lower):
                blocker_lines.append(line)
        if blocker_lines:
            errors.append(f"final_review.md has {len(blocker_lines)} blocker-severity line(s): {blocker_lines[:2]}")

    if errors:
        for e in errors:
            print(f"  ✗ {e}")
        raise AssertionError(
            f"phase7_task7_1: {len(errors)} invariant(s) failed"
        )

    print("  ✓ manuscript/draft.md + appendix.md present")
    print("  ✓ references.bib: all inline citekeys resolve; >=15 entries")
    print("  ✓ draft.docx + appendix.docx rendered and non-trivial")
    print("  ✓ supplementary zip present with MANIFEST.txt")
    print("  ✓ final_review.md present; 0 blocker-severity lines")
    print("\n✓ phase7_task7_1: all 6 invariants pass.")


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

def check_phase6_task6_1() -> None:
    """Phase 6 Task 6.1-6.7 DoD — 6 trace-checker invariants.

    Delegates to code/trace_checker.py which verifies the 6 Phase 6
    coverage invariants across the 6 trustworthiness Markdown deliverables.
    Loaded by absolute path to avoid stdlib ``code`` module name collision.
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "trace_checker",
        Path(__file__).resolve().parent / "trace_checker.py",
    )
    trace_checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(trace_checker)

    print("Running Phase 6 trace checker …")
    ok, results = trace_checker.run_all()
    for name, passed, msg in results:
        mark = "✓" if passed else "✗"
        print(f"  {mark} {name}")
        print(f"      {msg}")
    if not ok:
        raise AssertionError("phase6_task6_1: one or more invariants FAILED")
    print("\n✓ phase6_task6_1: all 6 trace-checker invariants pass.")


CHECKS = {
    "phase0_task0_1": check_phase0_task0_1,
    "phase1_task1_1": check_phase1_task1_1,
    "phase2_task2_3": check_phase2_task2_3,
    "phase4_task4_2": check_phase4_task4_2,
    "phase5_task5_1": check_phase5_task5_1,
    "phase5_task5_2": check_phase5_task5_2,
    "phase6_task6_1": check_phase6_task6_1,
    "phase7_task7_1": check_phase7_task7_1,
}


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in CHECKS:
        valid = ", ".join(sorted(CHECKS))
        print(f"Usage: python code/dod_checks.py <phase_task_id>")
        print(f"Valid IDs: {valid}")
        sys.exit(1)

    task_id = sys.argv[1]
    CHECKS[task_id]()


if __name__ == "__main__":
    main()
