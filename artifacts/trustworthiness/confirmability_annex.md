# Confirmability Annex

> **Deliverable class:** Phase 6 Task 6.2 — qualitative-research confirmability (Lincoln & Guba 1985; Cruzes & Dybå 2011 §VI) operationalized as per-claim bidirectional trace between study outputs and source data.
> **Generated:** 2026-04-20 UTC
> **Rater:** TBS
> **Plain-English question this document answers:** *"Can every interpretive claim be traced back to source data, rather than reflecting researcher bias?"*

---

## Framing

Confirmability is the trust-worthiness criterion parallel to positivist objectivity (Lincoln & Guba 1985 §11.3). In SE thematic synthesis (Cruzes & Dybå 2011 §VI + checklist item 9), confirmability requires "clear, evident connections between the text and the codes" — every interpretive claim must point at the primary-study evidence that supports it. This annex provides that trace across the three RQ outputs:

- **§1 RQ2 interaction-mode taxonomy** — ≥2 passage IDs per mode linking each mode's paraphrased exemplars back to specific `raw_passages/{paper_id}.md` files.
- **§2 RQ3 capability-usage gaps** — each of 42 flagged gap cells points at its paired `decision_register.csv` Phase-5 `hypothesis_for_erp3` row.
- **§3 RQ1 landscape figures** — each of 4 figures + `.meta.json` provenance sidecar + `_imgexplain.md` documentation.
- **§4 Saturation claim** — cites the Cruzes-compatible emergence-curve artefact.

---

## 1. RQ2 mode traces

Each mode in `artifacts/synthesis/interaction_taxonomy.md` v1.1 carries paraphrased exemplars with passage-ID citations of the form `doi:<paper>:P\d{3}`. Those passage IDs resolve directly to the paper's `raw_passages/{paper_id}.md` file. The primary traces below were extracted by scanning the mode sections of `interaction_taxonomy.md` and are verified by `code/dod_checks.py::check_phase4_task4_2` (all 10 exemplar traces resolve to real passages).

### Mode 1 — Inline Completion (4 canonical labels; 2 paraphrased exemplars)

- `doi:10.1145/3661145:P001` — `artifacts/extraction/raw_passages/10.1145_3661145.md` §P001
- `doi:10.24251/hicss.2025.883:P001` — `artifacts/extraction/raw_passages/10.24251_hicss.2025.883.md` §P001

Mode 1 trace is the thinnest of the five modes (4 canonical labels; see `transferability.md` §Mode 1 boundary for the associated transferability caveat). Both passage IDs were resolved via `check_phase4_task4_2` at Phase 4 closeout.

### Mode 2 — Conversational Prompting (69 canonical labels; 2 exemplars)

- `doi:10.1145/3597503.3608128:P003` — `artifacts/extraction/raw_passages/10.1145_3597503.3608128.md` §P003
- `doi:10.1145/3643991.3645074:P005` — `artifacts/extraction/raw_passages/10.1145_3643991.3645074.md` §P005

### Mode 3 — Visual / Declarative Composition (9 canonical labels; 2 exemplars)

- `doi:10.1109/tvcg.2025.3535332:P001` — `artifacts/extraction/raw_passages/10.1109_tvcg.2025.3535332.md` §P001
- `doi:10.7763/ijcte.2025.v17.1378:P003` — `artifacts/extraction/raw_passages/10.7763_ijcte.2025.v17.1378.md` §P003

### Mode 4 — Review & Validation (82 canonical labels; 2 exemplars)

- `doi:10.1145/3691620.3695529:P004` — `artifacts/extraction/raw_passages/10.1145_3691620.3695529.md` §P004
- `doi:10.1109/c358072.2023.10436306:P002` — `artifacts/extraction/raw_passages/10.1109_c358072.2023.10436306.md` §P002

### Mode 5 — Delegated Task Execution (75 canonical labels; 2 exemplars)

- `doi:10.1145/3772318.3790500:P001` — `artifacts/extraction/raw_passages/10.1145_3772318.3790500.md` §P001
- `doi:10.1145/3806655:P001` — `artifacts/extraction/raw_passages/10.1145_3806655.md` §P001

### Residuals (468 canonical labels; 4 sub-categories)

Residuals are not a mode; they are **evidence about interaction** rather than interaction itself (proposal §3.5 RQ2 commitment). Their trace chain is `canonical_label → pass1_codes → passage_ids` in `artifacts/synthesis/consolidated_codes.csv`, with the sub-category (`outcome` / `constraint` / `meta` / `affordance`) in `taxonomy_classifications.csv.residuals_subcategory`. Sub-category counts (proposal §4.2 transferability relevance): outcome 192 / constraint 119 / meta 101 / affordance 56.

**Verification:** The mode trace set above is auto-extracted by `code/trace_checker.py` (Task 6.7) and asserted by `check_phase6_task6_1` invariant 1 (≥2 passage IDs per mode 1–5).

---

## 2. RQ3 gap traces

Each of 42 `is_gap=True` cells in `gap_matrix.csv` is paired with exactly one `decision_register.csv` row carrying `phase=5, decision='hypothesis_for_erp3'` and a rationale of the form `<bucket>: Evidence for <CAP_ID> at <SDLC_activity> …`. The pairing is enforced bidirectionally by `check_phase5_task5_2` (landed in `df5d0ec`). This annex provides the grouped trace organized by SDLC activity + bucket.

### 2.1 CI/CD (5 gap cells)

| Capability | Evidence | Bucket | Register row (timestamp) |
|---|---:|---|---|
| CAP_CODETRANS | 1 | organizational_readiness_barrier | 2026-04-20T03:16:54Z |
| CAP_COMMITMSG | 1 | organizational_readiness_barrier | 2026-04-20T03:16:54Z |
| CAP_MULTIAGENT | 1 | adoption_lag | 2026-04-20T03:16:54Z |
| CAP_REQENG | 2 | design_gap | 2026-04-20T03:16:54Z |
| CAP_VULNDET | 1 | organizational_readiness_barrier | 2026-04-20T03:16:54Z |

### 2.2 Code Review (7 gap cells)

| Capability | Evidence | Bucket |
|---|---:|---|
| CAP_CICD | 2 | organizational_readiness_barrier |
| CAP_CODESEARCH | 1 | organizational_readiness_barrier |
| CAP_CODESUM | 2 | organizational_readiness_barrier |
| CAP_COMMITMSG | 1 | organizational_readiness_barrier |
| CAP_MULTIAGENT | 1 | adoption_lag |
| CAP_REQENG | 2 | design_gap |
| CAP_SELFREFLECT | 1 | adoption_lag |

### 2.3 Coding (1 gap cell)

| Capability | Evidence | Bucket |
|---|---:|---|
| CAP_COMMITMSG | 2 | organizational_readiness_barrier |

### 2.4 Debugging (2 gap cells)

| Capability | Evidence | Bucket |
|---|---:|---|
| CAP_CODESEARCH | 1 | organizational_readiness_barrier |
| CAP_COMMITMSG | 1 | organizational_readiness_barrier |

### 2.5 Design (7 gap cells)

| Capability | Evidence | Bucket |
|---|---:|---|
| CAP_CICD | 2 | design_gap |
| CAP_CODECOMP | 1 | design_gap |
| CAP_CODESUM | 2 | design_gap |
| CAP_CODETRANS | 2 | design_gap |
| CAP_MULTIAGENT | 1 | design_gap |
| CAP_PROGREPAIR | 2 | design_gap |
| CAP_SELFREFLECT | 2 | design_gap |

### 2.6 Documentation (6 gap cells)

| Capability | Evidence | Bucket |
|---|---:|---|
| CAP_CICD | 2 | organizational_readiness_barrier |
| CAP_CODESEARCH | 1 | organizational_readiness_barrier |
| CAP_COMMITMSG | 2 | organizational_readiness_barrier |
| CAP_MULTIAGENT | 2 | adoption_lag |
| CAP_SELFREFLECT | 1 | adoption_lag |
| CAP_VULNDET | 2 | organizational_readiness_barrier |

### 2.7 Project Management (7 gap cells)

| Capability | Evidence | Bucket |
|---|---:|---|
| CAP_CICD | 2 | organizational_readiness_barrier |
| CAP_CODEREVIEW | 2 | organizational_readiness_barrier |
| CAP_CODETRANS | 1 | organizational_readiness_barrier |
| CAP_COMMITMSG | 1 | organizational_readiness_barrier |
| CAP_SELFREFLECT | 1 | adoption_lag |
| CAP_SYSDESIGN | 2 | design_gap |
| CAP_VULNDET | 1 | organizational_readiness_barrier |

### 2.8 Requirements (4 gap cells)

| Capability | Evidence | Bucket |
|---|---:|---|
| CAP_CODECOMP | 1 | design_gap |
| CAP_CODESUM | 1 | design_gap |
| CAP_CODETRANS | 1 | design_gap |
| CAP_PROGREPAIR | 2 | design_gap |

### 2.9 Testing (3 gap cells)

| Capability | Evidence | Bucket |
|---|---:|---|
| CAP_CODESEARCH | 1 | organizational_readiness_barrier |
| CAP_CODETRANS | 2 | organizational_readiness_barrier |
| CAP_COMMITMSG | 1 | organizational_readiness_barrier |

**Summary:** 42 / 42 gap cells traced to Phase-5 register rows. Register rationales are preserved verbatim in the rows cited above (all stamped `2026-04-20T03:16:54Z`, rater `TBS`). Bucket tally across all 42: `organizational_readiness_barrier` 22, `design_gap` 14, `adoption_lag` 6 (matches `prioritised_gaps.md` bucket tally).

**Verification:** `check_phase6_task6_1` invariant 2 asserts every `is_gap=True` `(capability_id, sdlc_activity)` pair appears in either this annex or `dependability_audit.md`. Task 6.7 script parses this section + `gap_matrix.csv` to enforce the invariant.

---

## 3. RQ1 landscape figure traces

| Figure | Source CSV | Meta sidecar | Image-explanation doc |
|---|---|---|---|
| `rq1_landscape/year_sdlc_bubble.png` | `extraction_matrix.csv` (640 rows) | `year_sdlc_bubble.png.meta.json` | `year_sdlc_bubble_imgexplain.md` (explains 640 → 392 filtered n due to 246 F3-NaN papers + canonical F3 filter) |
| `rq1_landscape/f2_method_bar.png` | `extraction_matrix.csv` | `f2_method_bar.png.meta.json` | `f2_method_bar_imgexplain.md` (only figure with exact N=640 reconciliation) |
| `rq1_landscape/sdlc_year_heatmap.png` | `extraction_matrix.csv` | `sdlc_year_heatmap.png.meta.json` | `sdlc_year_heatmap_imgexplain.md` (explains multi-SDLC handling: 635 papers → 1,083 bindings) |
| `rq1_landscape/f5_tool_profile_stacked.png` | `extraction_matrix.csv` | `f5_tool_profile_stacked.png.meta.json` | `f5_tool_profile_stacked_imgexplain.md` (§1 modality-vs-mode disambiguation — load-bearing) |

Each meta sidecar carries `generated_by, script, inputs, git_sha, timestamp, seed` per `code/utils.py::write_with_meta`. The RQ2 variation tables under `rq2_variation/` carry the same provenance via their CSV headers and are documented in the cross-tab files themselves.

**The gap heatmap** (`artifacts/analysis/rq3_gap_matrix/gap_heatmap.png` + `gap_heatmap_imgexplain.md`) sits in RQ3 rather than RQ1 but is confirmability-traced the same way — `gap_matrix.csv` → `.meta.json` → imgexplain doc.

---

## 4. Saturation trace

The reportable RQ2 dependability anchor is **mode-layer saturation = Saturated**, computed from the Cruzes-compatible emergence-curve algorithm.

| Artefact | Content | Generating script |
|---|---|---|
| `artifacts/synthesis/saturation_report_mode.md` | Verdict narrative; 0 new modes in final 29 of 290 papers | `code/saturation_report.py` |
| `artifacts/synthesis/saturation_data_mode.csv` | Per-paper emergence data (290 rows) | `code/saturation_report.py` |
| `artifacts/synthesis/saturation_curve_mode.png` | Visual emergence curve | `code/saturation_report.py` |

The canonical-layer saturation (`saturation_report.md`) reports 63 new canonical labels in the final 29 papers and is **intermediate, not reportable** per the Phase 4 Task 4.2 Step-8 methodology. This distinction is encoded in the proposal §3.5 RQ2 stopping-condition clause and enforced at `check_phase4_task4_2`.

---

## 5. What remains outside confirmability

Two classes of claims in the study do **not** carry a single-passage trace and are documented here as scope boundaries rather than confirmability gaps:

1. **Aggregated frequency counts** (RQ1 landscape figures) — a bubble area or bar height is derived by counting distinct papers, not by citing one representative passage. Their trace is at the *CSV + imgexplain.md* level (§3 above), not the passage level. This is consistent with Petersen et al. (2008) bubble-plot convention.
2. **Methodological / cross-cutting narrative claims** — e.g., "the mode taxonomy collapses the provisional 8 into 5 based on data-driven evidence." These trace to decision-register rows (`task4_2_canonical_merge`, `task4_2_canonical_rename`, `taxonomy_finalised`) rather than primary-paper passages. Their confirmability is therefore audit-trail-based (see `dependability_audit.md`) rather than passage-based.

---

## References

- Lincoln, Y. S., & Guba, E. G. (1985). *Naturalistic Inquiry*. Sage Publications.
- Cruzes, D. S., & Dybå, T. (2011). *Recommended Steps for Thematic Synthesis in Software Engineering*. ESEM.
- Petersen, K., Feldt, R., Mujtaba, S., & Mattsson, M. (2008). *Systematic Mapping Studies in Software Engineering*. EASE.
