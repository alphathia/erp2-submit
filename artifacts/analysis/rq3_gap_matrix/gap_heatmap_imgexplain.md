# Explanation — `gap_heatmap.png`

> **Figure purpose.** The RQ3 capability-usage gap matrix: a 19 × 9 grid showing how empirical evidence is distributed across the intersection of **supply-side capabilities** (rows; from the three reference surveys) and **SDLC activities** (columns; from the proposal F4 codebook). Cell value = distinct-paper count; red border = **gap** at the P25 threshold; diagonal hatching = **empty cell** (no evidence).

## 1. Source data

| Input | Rows | Role |
|---|---:|---|
| `artifacts/protocol/capability_list.csv` | 43 rows → 19 unique `capability_id`; 9 distinct `sdlc_activity` values | Defines the matrix vocabulary (the row × column axes). |
| `artifacts/extraction/capability_annotations.csv` | 776 rows; 384 unique `paper_id` | Primary evidence source: one row per `(paper_id, capability_id)` pair with a short `evidence` quotation. |
| `artifacts/extraction/extraction_matrix.csv` | 640 rows | Provides `f4_sdlc_activity` (pipe-separated) per paper — joined on `paper_id`. |

## 2. Counting unit

Each cell is a **distinct-`paper_id` count** over the triple `(capability_id, f4_sdlc_activity, paper has that capability annotation)`:

```
cell_count(c, s) = |{ paper_id : (paper_id, c) ∈ annotations
                                 ∧ s ∈ extraction_matrix.f4_sdlc_activity(paper_id).split('|') }|
```

Values range from 0 (empty cells) to 156 (the max in this matrix; typically `CAP_CODEGEN × Coding`).

## 3. Multi-valued SDLC handling

Like `sdlc_year_heatmap.png` (see `../rq1_landscape/sdlc_year_heatmap_imgexplain.md §3`), we **explode** the pipe-separated `f4_sdlc_activity` so an annotation on a paper tagged `"Coding|Debugging"` contributes to **both** the corresponding capability's Coding cell and Debugging cell.

Consequence: the sum of all 171 cell values (**2,023**) exceeds both the annotation-row count (776) and the distinct-paper count (383 — 1 paper has NaN F4 and is effectively excluded). The matrix shows **paper × capability × SDLC bindings**, not distinct-paper counts.

| Quantity | Value |
|---|---:|
| Total annotations in `capability_annotations.csv` | 776 |
| Unique papers annotated | 384 |
| Annotations whose paper has NaN F4 (excluded from matrix) | 2 |
| Unique papers contributing to the matrix (after F4 join) | 383 |
| Sum of `evidence_count` across 171 cells | 2,023 |
| Maximum cell value | 156 |

## 4. Why the corpus denominator is not 640

- **Only 384 of 640 papers have capability annotations.** Phase 3 Task 3.2 applied the harmonized capability vocabulary to each paper during extraction; 256 papers had no capability match and are absent from `capability_annotations.csv`. Those 256 papers are still counted elsewhere (e.g., Fig 2 F2 distribution) but are epistemically invisible to the RQ3 gap analysis by construction — a paper with no capability annotation has nothing to contribute to a capability-usage cross-tab.
- **2 annotations have NaN F4** (the paper's SDLC column is missing). These are dropped from the matrix; no cell receives their contribution. See the Phase 3 closeout for the F3 / F4 coverage notes.
- **No Mode-B abstract-only papers contribute** — Phase 3 Task 3.3 only generated capability annotations from the 290 papers with extractable full-text passages. This is documented in `task3_academic_closeout_report.md §2.2`.

The gap matrix is therefore a **demand-side-sample view over supply-side-harmonized vocabulary**, not a corpus census. Low cell counts signal where the 383-paper demand-side evidence base is thin relative to supply-side claims — which is exactly what RQ3 seeks.

## 5. Gap rule (proposal §3.5 RQ3 verbatim)

A cell is a **gap** iff **all three** conditions hold:

1. `evidence_count > 0` — non-empty (gaps are about under-representation, not absence).
2. `evidence_count ≤ P25` — where `P25` is the **25th percentile of non-zero cells only** (currently **P25 = 2.0**).
3. The capability is documented in ≥1 reference survey — auto-satisfied because every `capability_id` in `capability_list.csv` has at least one `source_paper`.

A cell with `evidence_count == 0` is an **empty cell**, NOT a gap. Empty cells are reported separately (proposal §3.5 RQ3: "absence of evidence is treated as a distinct interpretive category"). Gap and empty are mutually exclusive.

| Cell partition (current matrix) | Count | % of 171 |
|---|---:|---:|
| Gap cells (`is_gap=True`) | 42 | 24.6% |
| Empty cells (`is_empty=True`) | 12 | 7.0% |
| Normal cells (`evidence_count > P25`) | 117 | 68.4% |
| **Total** | **171** | **100%** |

### Sensitivity at P33

The robustness check at the 33rd percentile flags 53 gap cells (see `sensitivity_25_33.md`). P25 remains the primary threshold because the proposal §3.5 RQ3 commits to it explicitly; P33 is the sensitivity analysis.

## 6. Visual encoding

- **Cell color** — `YlGnBu` sequential colormap; darker = higher `evidence_count`. Annotated integer shown in each cell.
- **Red border** — cell is `is_gap=True` (0 < count ≤ P25). A visible border, not a color substitution — you still see the cell's count.
- **Diagonal grey hatching** — cell is `is_empty=True` (count == 0). The hatching sits on top of the zero-colored cell so readers do not mistake an empty cell for the lowest-evidence (non-zero) cell.
- **Colorbar label** — `"distinct paper count"`. This clarifies the counting unit is papers, not annotation rows.

## 7. Interpretation guidance

- **Rows are capabilities, not sub-activities of a single concept.** Capabilities span distinct research sub-areas (code generation, test synthesis, requirements analysis, etc.) harmonized from three reference surveys into 19 unified labels. Two capabilities can both be high-density for Coding without "double-counting" — they describe different tool capabilities.
- **Columns are SDLC activities.** The same 9-value vocabulary used in `sdlc_year_heatmap.png`; multi-SDLC paper handling is identical.
- **A gap is NOT a claim that research is deficient.** It is a **quantitative signal** about the joint distribution: this (capability × SDLC) intersection has less than the P25 of non-zero evidence, while the reference surveys claim the capability exists. The interpretation — adoption lag / design gap / organizational readiness barrier — is logged in `decision_register.csv` as Phase-5 ERP3 hypotheses, **never** as matrix columns (this separation is enforced by `check_phase5_task5_2` in `code/dod_checks.py`).
- **Empty cells are a distinct interpretive category.** They motivate "why is this untouched?" research questions, not "why is this understudied?" questions. The Task 5.3 research agenda surfaces both buckets separately (see `prioritised_gaps.md` for the 42 gap prioritization and the empty-cell appendix of `research_agenda.md`).
- **Paradigm splits exist as separate CSVs.** `gap_matrix_by_paradigm/{procode,lowcode,nocode}.csv` re-run the same algorithm on subsets of the corpus filtered by `f5_tool_paradigm`. Their P25 values differ (Pro=2.0, Low=1.0, No=1.0) because P25 is recomputed per paradigm — this prevents the dominant Pro-code sub-corpus from washing out the Low-code and No-code signal.

## 8. Terminological clarifications

- **Capability (F6 in some older notes; harmonized list in `capability_list.csv`)** — supply-side claim from a reference survey that a particular AI-SE tool class does thing X. 19 harmonized capability IDs (`CAP_CODEGEN`, `CAP_CODECOMP`, etc.) unify the three reference surveys' vocabularies.
- **Evidence** — a **passage-backed annotation** in `capability_annotations.csv`. Not a statistical measurement — the word is used in the Cruzes & Dybå (2011) sense of "extracted evidence for a theme".
- **Gap** — quantitative flag per the §5 rule. Not a judgement.
- **Empty cell** — zero-evidence cell; reported as a distinct category per proposal §3.5 RQ3.
- **P25** — recomputed in `prioritize_gaps.py` and asserted stable at 2.0 (design/5_3_prioritize_gaps.md §3). If the matrix is ever regenerated and P25 drifts, both the heatmap title and `prioritised_gaps.md` will flag the change.
- Do not confuse **capability** (F6 supply-side) with **interaction modality** (F5 tool profile) or **interaction mode** (RQ2 taxonomy). See `f5_tool_profile_stacked_imgexplain.md §1` for the mode vs modality disambiguation — capability is a third, orthogonal construct.

## 9. Methodological references

- Proposal §3.5 RQ3 — full operational rule (single-rule, 25th-percentile, non-zero cells only, empty cells as distinct category, 33rd-percentile sensitivity).
- Petersen et al. (2015) §6.4 — cross-tabulation reporting conventions for capability × activity matrices.
- Cruzes & Dybå (2011) Step 5 interpretation — the gap matrix is a Step-5 interpretive artifact, complemented by the Task 5.3 research agenda.

## 10. Provenance

- **Script:** `code/analysis_rq3.py::render_heatmap`
- **Meta sidecar:** `gap_heatmap.png.meta.json`.
- **Design spec:** `design/5_2_analysis_rq3.md`.
- **Companion artefacts:** `gap_matrix.csv` (the tabular form); `sensitivity_25_33.md` (P25 vs P33 gap-count comparison); `gap_matrix_by_paradigm/{procode,lowcode,nocode}.csv` (F5 paradigm-split re-runs).
