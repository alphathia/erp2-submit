# Credibility Statement

> **Deliverable class:** Phase 6 Task 6.1 — qualitative-research credibility (Cruzes & Dybå 2011 §VI) operationalized through Wieringa et al. (2006) six Evaluation Research criteria + Petersen et al. (2015) §5 SMS reporting checklist.
> **Generated:** 2026-04-20 UTC
> **Rater:** TBS
> **Plain-English question this document answers:** *"Is the research believable given the data and method applied?"*

---

## Framing

Lincoln & Guba (1985) introduce credibility as the qualitative-research analogue of internal validity: the degree to which a reader can verify that the study's claims are supported by the evidence collected and that the method was applied soundly. Cruzes & Dybå (2011) adapt this to SE thematic synthesis as Step 5 of their recommended process. This study operationalizes credibility through two nested self-assessments — Wieringa et al. (2006) six Evaluation Research criteria (§1–§6 below) and Petersen et al. (2015) §5 SMS reporting checklist (§7 below) — citing concrete Phase 3 / 4 / 5 artefacts for each claim.

---

## 1. Problem clarity *(Wieringa criterion 1)*

The research problem is stated in three coherent layers:

- **Motivation** (proposal §1.1) — Since the launch of GitHub Copilot, AI integration into software engineering has accelerated; three supply-side surveys have mapped what AI agents *can do*, but none has synthesized how practitioners *actually use* them. The study addresses this supply-vs-demand imbalance.
- **Research questions** (proposal §1.2) — Three precise questions: RQ1 (evidence landscape), RQ2 (interaction modes + variation), RQ3 (capability-usage gaps).
- **Research objectives** (proposal §1.3) — Four deliverables: SMS landscape, Human–AI Interaction Mode Taxonomy, Capability-Evidence Gap Matrix, ERP3 research agenda.

Each layer is traceable to a concrete Phase 3 / 4 / 5 artefact (see Task 6.6 `contribution_novelty.md` §2 for the objective-to-deliverable mapping).

**Rating:** **Present.** Problem statement is operationalized into measurable deliverables with entry/exit criteria per task (see `research_plan_sms.md` per-task DoD prompts).

## 2. Causal / logical property clarity *(Wieringa criterion 2)*

The study's logical properties are each tied to an operational rule documented ahead of execution:

- **RQ1 landscape** — descriptive frequency analysis using the F1–F5 codebook (`artifacts/protocol/codebook.md`); 4 figures per proposal §3.5 RQ1 specification. Output: `artifacts/analysis/rq1_landscape/` + 4 image-explanation MDs that articulate counting-unit semantics and multi-valued-cell handling.
- **RQ2 taxonomy** — inductive three-pass open coding per Cruzes & Dybå (2011) Steps 1–4; delegation-depth axis committed in proposal §3.5 pre-synthesis. Output: `artifacts/synthesis/interaction_taxonomy.md` v1.1 (5 modes + Residuals).
- **RQ3 gap rule** — single-rule, 25th-percentile on non-zero cells, empty cells reported separately; P33 sensitivity clause. Output: `artifacts/analysis/rq3_gap_matrix/gap_matrix.csv` (171 cells).

The rules are not inferred post-hoc; they are named in `research_plan_sms.md` at each task's entry/execution/DoD prompt and enforced via the `code/dod_checks.py` dispatcher (`check_phase2_task2_3`, `check_phase4_task4_2`, `check_phase5_task5_1`, `check_phase5_task5_2`, and Task 6.7's `check_phase6_task6_1`).

**Rating:** **Present.** All operational rules are declared ahead of execution and machine-checked.

## 3. Method soundness *(Wieringa criterion 3)*

Method soundness is demonstrated through alignment to published SE-synthesis methodology + Phase-level discipline:

- **SMS backbone** — Petersen et al. (2008) + Petersen et al. (2015). Phases 1–2 implement the protocol / screening / PRISMA stages per Petersen; Phase 7 will implement §7 reporting.
- **Thematic synthesis core** — Cruzes & Dybå (2011) five steps:
  - Step 1 (extract data) — Phase 3 Task 3.2 (`artifacts/extraction/extraction_matrix.csv`, 640 rows).
  - Step 2 (code data) — Phase 3 Task 3.3 (`artifacts/extraction/open_codes_pass1.csv`, 1,016 rows).
  - Step 3 (translate codes into themes) — Phase 4 Task 4.1 (`artifacts/synthesis/consolidated_codes.csv`, 707 canonical labels).
  - Step 4 (create higher-order themes) — Phase 4 Task 4.2 (`artifacts/synthesis/interaction_taxonomy.md` + `taxonomy_classifications.csv`).
  - Step 5 (assess trustworthiness) — Phase 6 (this document + the other 5 trustworthiness MDs).
- **Human epistemic control preserved** — LLM used only as an assistant for label proposal and pre-classification (Phase 4); rater approves / renames / splits / merges every decision (Cruzes 2011 warns explicitly against automation without human validation).
- **Bidirectional trace** — `mode → canonical_label → pass1_codes → passage_ids → paper_id` preserved at every layer; every RQ2 claim can be verified against `raw_passages/` (see Task 6.2 `confirmability_annex.md`).

**Rating:** **Present.** Method alignment is concrete at every step; no step delegated to un-audited automation.

## 4. Knowledge claim validity *(Wieringa criterion 4)*

Knowledge claims are bounded and auditable:

- **Mode-layer saturation Saturated** — 0 new modes in the final 29 of 290 papers (`artifacts/synthesis/saturation_report_mode.md`). This is the Phase 6 dependability anchor for RQ2 and is not recomputed here.
- **Paraphrase-linter clean** — 0 / 6,295 n-grams from `interaction_taxonomy.md` appear verbatim in `raw_passages/` (confirmability at the text level). The linter is reused on every Phase 4 / 5 / 6 Markdown deliverable.
- **Idempotence-guarded scripts** — `code/analysis_rq3.py` skips duplicate register appends on re-run. Deterministic sort in `code/prioritize_gaps.py` guarantees byte-identical output across re-runs.
- **DoD dispatchers machine-verify invariants** — `check_phase4_task4_2` (structure / exemplar traces / partition / linter / saturation / Task 4.3 coverage), `check_phase5_task5_1` (landscape + variation), `check_phase5_task5_2` (gap matrix + register correspondence). Task 6.7 adds `check_phase6_task6_1`.
- **All claims in this file cite a concrete artefact** — no bare assertions.

**Rating:** **Present.** Knowledge claims carry explicit bounds (saturation, linter, dispatcher) and are reproducible.

## 5. Significance of lessons learned *(Wieringa criterion 5)*

The study contributes four artefacts that address a named gap in the literature:

- **Contribution 1 — RQ1 demand-side landscape** — 4 figures + 3 RQ2 variation tables characterize where 2022–2026 empirical AI-SE evidence concentrates across year × F3 × F4 × F5. No prior SMS has mapped this demand-side distribution at this scale (see `contribution_novelty.md` §2.1 for the vs-prior-work comparison).
- **Contribution 2 — RQ2 5-mode interaction taxonomy along delegation depth** — empirically grounded in 707 canonical labels; supersedes the provisional 8-mode taxonomy in proposal Appendix C via data-driven collapsing.
- **Contribution 3 — RQ3 19 × 9 capability × SDLC gap matrix** — the first study to cross-tabulate the three reference surveys' capabilities against empirical usage; 42 gaps + 12 empty cells identified with explicit supply-side anchors.
- **Contribution 4 — ERP3 research agenda** — 6 Wieringa-typed study calls covering all 42 gaps + 12-cell empty-cell appendix. Directly enables the ERP3 practitioner-interview study.

Significance is both methodological (the 4 criteria × 3 reference surveys novelty matrix in `contribution_novelty.md`) and practical (`self_assessment_rubric.md` + `adoption_progression.md` give practitioners a usable artefact for self-locating along the delegation axis).

**Rating:** **Present.** Each contribution is named, artefact-backed, and positioned against prior work.

## 6. Related work *(Wieringa criterion 6)*

Related work is engaged at three levels:

- **Three reference surveys** — Wang et al. (2025) AI Agentic Programming [15]; Wang et al. (2025) Agents in SE [16]; Otoum & Elkhalili (2026) [9]. Each is summarized in proposal §2 Table 1 with its primary lens, core output, and the gap this study addresses. `capability_list.csv` harmonizes their capability vocabularies into 19 unified IDs; `contribution_novelty.md` §3 contains the 4 × 3 objective-vs-survey novelty matrix.
- **Methodology references** — Petersen 2008/2015 (SMS), Cruzes & Dybå 2011/2015 (thematic synthesis), Wieringa 2006 (F1 classifier + this credibility self-assessment), Lincoln & Guba 1985 (trustworthiness criteria origin), Braun & Clarke 2006 (15–20 theme guideline).
- **Seed papers** — `docs/seeds/` contains the three surveys + Kumar et al. (2025) *Why AI Agents Still Need You* (used for snowball seed generation in Phase 2 Task 2.2).

**Rating:** **Present.** Prior work is engaged at the survey, methodology, and seed-paper levels; each engagement is artefact-anchored.

---

## 7. Petersen et al. (2015) §5 SMS reporting checklist

Petersen et al. (2015) §5 provides a systematic-mapping-study reporting checklist (adapted from Petersen 2008 + Kitchenham & Charters 2007). Ratings against this study's artefacts:

| # | Checklist item | Rating | Evidence |
|---:|---|---|---|
| 1 | Research questions stated and motivated | **Present** | Proposal §1.1 + §1.2; reprised in every task prompt. |
| 2 | Search strategy documented + reproducible | **Present** | `artifacts/search/search_strings.md`, `scopus_query_template.txt`, `retrieval_status.csv`; Phase 2 Task 2.3 executed and logged. |
| 3 | Inclusion / exclusion criteria declared before screening | **Present** | `artifacts/protocol/inclusion_exclusion.md`; decision-register row `codebook_refined_post_pilot` captures the Phase 1 pilot adjustment. |
| 4 | Screening procedure documented (incl. reliability pilot) | **Partial** | `artifacts/screening/phase2_decisions.csv` logs EC outcomes; pilot documented in Phase 1 Task 1.3; formal inter-rater pilot deferred to ERP3 (single-rater study; documented in `transferability.md`). |
| 5 | Classification scheme (extraction form) declared ahead of extraction | **Present** | `artifacts/protocol/codebook.md` (F1–F5 with operational definitions); `artifacts/protocol/extraction_schema.md`. |
| 6 | PRISMA flow + numbers reconciled | **Present** | `artifacts/screening/prisma_flow.md`; `check_phase2_task2_3` dispatcher enforces reconciliation. |
| 7 | Saturation or stopping rule stated | **Present** | Mode-layer saturation Saturated at `saturation_report_mode.md`; canonical-layer Not-saturated acknowledged as intermediate. |
| 8 | Data extraction quality-assurance (e.g., cross-model spot check) | **Present** | Phase 3 Task 3.3 cross-model spot check at `artifacts/extraction/spotcheck_manifest.md`; 64-paper stratified sample; decision-register rows `f1_revised` (323 rows) record post-check F1 adjustments. |
| 9 | Threats to validity explicitly stated | **Present** | This document + Task 6.2–6.5; proposal §6 engaged point-by-point. |
| 10 | Limitations / boundary conditions named | **Present** | `transferability.md` (Task 6.4) — ≥7 boundary conditions enumerated. |
| 11 | Results visualized using mapping-study conventions | **Present** | `artifacts/analysis/rq1_landscape/` — 4 figures per Petersen 2008 Fig. 4 + Petersen 2015 §7 visualization catalogue. |
| 12 | Reproducibility package / supplementary | **Partial** | Full artefact set + code committed to git with per-phase tags (`phase1-complete` → `phase5-complete`); Phase 7 Task 7.2 will freeze a supplementary zip. |

**Overall checklist status:** 10 **Present** + 2 **Partial** (items 4 and 12) — both explicitly documented as deferred (reliability pilot → ERP3; supplementary zip → Phase 7) rather than absent.

---

## 8. Summary

| Criterion | Rating | Anchor |
|---|---|---|
| Wieringa 1 — Problem clarity | Present | Proposal §1.1–§1.3; `contribution_novelty.md` §2 |
| Wieringa 2 — Causal / logical property clarity | Present | `research_plan_sms.md` per-task prompts; `dod_checks.py` |
| Wieringa 3 — Method soundness | Present | Cruzes & Dybå Steps 1–5 alignment table |
| Wieringa 4 — Knowledge claim validity | Present | Mode saturation; paraphrase linter; idempotent scripts |
| Wieringa 5 — Significance of lessons | Present | 4 contributions named; practitioner artefacts (`self_assessment_rubric.md`, `adoption_progression.md`) |
| Wieringa 6 — Related work | Present | 3 reference surveys + methodology anchors + seed papers |
| Petersen 2015 §5 checklist | 10 Present + 2 Partial | §7 above |

Credibility verdict: **supported** across all 6 Wieringa criteria and the Petersen §5 checklist, with two partial items (reliability pilot deferred to ERP3; supplementary zip deferred to Phase 7) documented as scope choices rather than gaps.

---

## References

- Cruzes, D. S., & Dybå, T. (2011). *Recommended Steps for Thematic Synthesis in Software Engineering*. ESEM.
- Lincoln, Y. S., & Guba, E. G. (1985). *Naturalistic Inquiry*. Sage Publications.
- Petersen, K., Feldt, R., Mujtaba, S., & Mattsson, M. (2008). *Systematic Mapping Studies in Software Engineering*. EASE.
- Petersen, K., Vakkalanka, S., & Kuzniarz, L. (2015). *Guidelines for conducting systematic mapping studies in software engineering: An update*. IST 64.
- Wieringa, R., Maiden, N., Mead, N., & Rolland, C. (2006). *Requirements engineering paper classification and evaluation criteria: a proposal and a discussion*. Requirements Engineering 11(1).
