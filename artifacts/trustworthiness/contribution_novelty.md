# Contribution & Novelty Statement

> **Deliverable class:** Phase 6 Task 6.6 — manuscript-level framing per Petersen et al. (2015) §4; maps each of the 4 research objectives from proposal §1.3 to a named contribution + novelty claim against each of the 3 reference surveys.
> **Generated:** 2026-04-20 UTC
> **Rater:** TBS
> **Plain-English question this document answers:** *"What does this study add that the existing literature does not?"*

---

## 1. Summary table

| # | Research objective (proposal §1.3) | Contribution | Artefact | Novelty anchor vs. the 3 reference surveys |
|---:|---|---|---|---|
| 1 | SMS of empirical usage evidence (RQ1) | **C1.** Demand-side landscape map of 2022–2026 empirical AI-SE literature across F1–F5 + mode × F3/F4/F5 variation | `rq1_landscape/` 4 PNGs + `rq2_variation/` 3 MD+CSV | None of the 3 reference surveys is demand-side; all 3 classify what AI systems *can do*, not how users *use* them |
| 2 | Human–AI Interaction Mode Taxonomy (RQ2) | **C2.** 5-mode taxonomy along a delegation-depth axis, inductively derived from 707 canonical labels across 290 papers | `interaction_taxonomy.md` v1.1 + `taxonomy_classifications.csv` + `self_assessment_rubric.md` + `adoption_progression.md` | Wang [15] classifies system behaviors (reactivity / single-turn / tool-augmented); Wang [16] classifies agent internals (perception-memory-action). Neither proposes a human-agent interaction mode taxonomy along a delegation axis |
| 3 | Capability-Evidence Gap Analysis (RQ3) | **C3.** 19 × 9 supply-demand cross-tab with single-rule P25 gap definition; 42 gaps + 12 empty cells identified | `gap_matrix.csv` (171 cells) + `gap_heatmap.png` + `sensitivity_25_33.md` + 3 paradigm splits | None of the 3 surveys cross-tabulates its own capability taxonomy against empirical usage; this is the first supply-vs-demand cross-tab in the AI-SE literature to our knowledge |
| 4 | Evidence-based research agenda (ERP3 hand-off) | **C4.** 6 Wieringa-typed ERP3 study calls covering all 42 gaps + 12-cell empty-cell appendix | `prioritised_gaps.md` + `research_agenda.md` | Otoum & Elkhalili [9] identifies adoption trends but does not derive prioritized research calls; Wang [15, 16] do not frame an empirical research agenda |

**Bottom line:** The study's novelty is its **demand-side lens** on a supply-side-saturated literature, operationalized through an interaction-mode taxonomy along a delegation-depth axis and a supply-vs-demand gap cross-tab. These are the first such artefacts in the AI-SE mapping-study literature to our knowledge; the 3 reference surveys occupy the supply-side of the same problem space.

---

## 2. Per-objective contributions

### 2.1 Contribution C1 — RQ1 demand-side landscape map

**What was produced.**

- 4 RQ1 landscape figures at `artifacts/analysis/rq1_landscape/`: (i) year × SDLC activity bubble faceted by developer population; (ii) F2 research methodology distribution bar; (iii) SDLC × year heatmap; (iv) F5 tool profile (paradigm × modality) stacked bar. Each with a meta-sidecar provenance JSON + an `_imgexplain.md` document articulating counting-unit semantics and multi-valued-cell handling (academic-rigor layer added for Phase 5 closeout).
- 3 RQ2 variation cross-tabs at `artifacts/analysis/rq2_variation/`: mode × F4 SDLC, mode × F5 Tool Profile, mode × F3 Population & Context. Each as a Markdown + CSV pair with raw counts + row-normalized percentages.

**How it is auditable.** Every figure cites its source CSV (`extraction_matrix.csv`, 640 rows) + `.meta.json` provenance + `_imgexplain.md` narrative. Counting units are explicitly typed: distinct papers (bar / bubble / heatmap cell) vs. paper-activity bindings (multi-SDLC explosion noted in `sdlc_year_heatmap_imgexplain.md §3`). Verified by `check_phase5_task5_1` DoD dispatcher.

**Novelty claim.** This is the first 2022–2026 AI-SE SMS **focused on empirical usage evidence** (demand-side) across a five-facet classification scheme covering contribution type (F1), methodology (F2), population & context (F3), SDLC activity (F4), and agent/tool profile (F5). The three reference surveys ([9], [15], [16]) are each supply-side — they inventory what AI systems or agents *do*, not how humans *use* them — so none can be cited as a predecessor for a demand-side landscape.

### 2.2 Contribution C2 — RQ2 interaction-mode taxonomy

**What was produced.**

- A 5-mode interaction taxonomy: Mode 1 Inline Completion / Mode 2 Conversational Prompting / Mode 3 Visual–Declarative Composition / Mode 4 Review & Validation / Mode 5 Delegated Task Execution, ordered along a delegation-depth axis. Artefact: `artifacts/synthesis/interaction_taxonomy.md` v1.1.
- Every canonical label from Phase 4 Task 4.1 (707 canonical labels from 1,003 unique pass-1 codes) is classified into exactly one mode + Residuals sub-bucket. Artefact: `artifacts/synthesis/taxonomy_classifications.csv`.
- Mode-layer saturation verdict **Saturated** (0 new modes in final 29 of 290 papers). Artefact: `artifacts/synthesis/saturation_report_mode.md`.
- Practitioner artefacts — `self_assessment_rubric.md` (per-mode observable indicators) + `adoption_progression.md` (transitions between modes with capability / organizational / risk-posture prerequisites).

**How it is auditable.** Each of 5 modes has ≥2 paraphrased exemplars with passage-ID traces (see `confirmability_annex.md §1`). Mode partition is verified by `check_phase4_task4_2` (partition integrity, all exemplar traces resolve, paraphrase-linter clean 6,295 n-grams).

**Novelty claim.**

- **vs. Wang et al. (2025) AI Agentic Programming [15]:** [15] proposes a hierarchical *system-behavior* taxonomy (reactive vs. proactive, single-turn vs. multi-turn, tool-augmented vs. standalone, static vs. adaptive). That taxonomy classifies the agent as a system artefact. Our Mode taxonomy classifies the *human-agent interaction*, which [15] explicitly identifies as an open direction it does not address.
- **vs. Wang et al. (2025) Agents in SE [16]:** [16] uses a *perception-memory-action* framework for agent internals across 115 studies. That framework describes how agents are structured, not how humans engage with them. Our Mode taxonomy operates on the interaction surface, not the agent internals.
- **vs. Otoum & Elkhalili (2026) [9]:** [9] is methods-oriented (SLR of 61 studies covering methods, lifecycle integration, autonomy, architectures, evaluation). It covers adoption as one research question but does not derive an interaction-mode taxonomy.

The delegation-depth axis (Assistive → Collaborative → Delegative → Autonomous) is a commitment pre-registered in proposal §3.5 and grounded inductively in the 707 canonical labels; no reference survey proposes an equivalent axis.

### 2.3 Contribution C3 — RQ3 capability-evidence gap matrix

**What was produced.**

- A 19 × 9 = 171-cell evidence matrix cross-tabulating **harmonized supply-side capabilities** (19 unified capability IDs derived from the 3 reference surveys; see `artifacts/protocol/capability_list.csv`) against **empirical usage** (demand-side, from 384 papers contributing 776 annotations joined to F4 SDLC activities).
- Gap rule applied per proposal §3.5 RQ3 single-rule operational definition: `is_gap = (evidence_count > 0 AND evidence_count ≤ P25(non-zero cells))`; P25 = 2.0; 42 gap cells flagged.
- Empty cells (`is_empty = True`) reported separately as a distinct interpretive category: 12 empty cells across 171 total. Empty cells are **not** gaps.
- 33rd-percentile sensitivity: 53 gaps. 20th and 40th percentile sensitivity extension at `threshold_sensitivity.md`: P25 gap set is monotonically preserved across [P20, P40]; no cell exits.
- Paradigm-split sub-matrices at `gap_matrix_by_paradigm/{procode,lowcode,nocode}.csv` — per-paradigm P25 avoids washing out Low-code / No-code signal.
- Gap heatmap at `gap_heatmap.png` with distinct visual encoding (red border for gaps, diagonal hatching for empty cells).

**How it is auditable.** Each of 42 gap cells is paired with exactly one `phase=5, decision='hypothesis_for_erp3'` row in `decision_register.csv` (verified by `check_phase5_task5_2` invariant 3). The matrix carries no interpretation-label columns — bucket labels (`adoption_lag`, `design_gap`, `organizational_readiness_barrier`) live only in the register (invariant 4). Bidirectional trace: `gap_matrix.csv ↔ decision_register.csv`.

**Novelty claim.**

- **vs. [15]:** [15] tabulates tool categories; does not cross-tabulate categories against empirical usage.
- **vs. [16]:** [16] enumerates agent capabilities; does not assess where empirical deployment lags the capability claims.
- **vs. [9]:** [9] addresses adoption broadly but does not derive a capability × activity gap matrix. Our cross-tab is the first to quantify the supply-vs-demand asymmetry at this granularity.

The single-rule P25-on-non-zero-cells gap definition is (to our knowledge) novel in the AI-SE mapping-study literature — prior gap analyses in SE mapping studies (e.g., Petersen 2015 examples) use absolute-threshold rules or qualitative gap identification.

### 2.4 Contribution C4 — Evidence-based ERP3 research agenda

**What was produced.**

- `artifacts/analysis/prioritised_gaps.md` — 42 gaps ranked by priority score (`P25_shortfall × capability_prevalence`). Deterministic sort with alphabetical tie-breaking for byte-identical re-runs. Top-priority cluster: CAP_CODECOMP at early-lifecycle activities (ranks 1–2), CAP_CODETRANS at non-coding activities (ranks 3–5), CAP_SELFREFLECT outside Coding (ranks 6–8).
- `artifacts/analysis/research_agenda.md` — 6 research calls covering all 42 gaps:
  - Call 1: AI code completion at early-lifecycle activities (Evaluation Research).
  - Call 2: AI code translation beyond the coding boundary (Validation + Evaluation).
  - Call 3: Agentic self-reflection outside Coding (Validation Research).
  - Call 4: Multi-agent orchestration at under-studied SDLC intersections (Validation Research).
  - Call 5: AI vulnerability detection beyond Coding (Evaluation Research).
  - Call 6: Knowledge-management capabilities at non-native SDLC activities (Evaluation Research; integrative study across 10 priority-0.50 gaps).
  - Borderline-gaps attribution table for the remaining 19 priority-0.00 gaps.
- 12-cell empty-cell appendix with per-cell interpretive notes (inapplicable-by-architecture vs. exploratory-research-absence).
- RQ2-linkage table mapping each research call to the interaction modes it exercises.

**How it is auditable.** Every gap in `gap_matrix.csv` appears in `prioritised_gaps.md` with a priority score + rationale excerpt (verified by Task 5.3 DoD). Every gap maps to ≥1 Wieringa-typed call in `research_agenda.md` (verified at Phase 5 closeout with the post-DoD-audit extensions). Both files paraphrase-linter clean (2,241 + 2,957 n-grams).

**Novelty claim.**

- **vs. [15]:** [15] identifies open research directions generally; does not frame them in Wieringa's Evaluation / Validation class vocabulary.
- **vs. [16]:** [16] frames challenges for agents in SE; does not prioritize them against empirical evidence gaps.
- **vs. [9]:** [9] discusses adoption frictions; does not propose a structured research-call set keyed to gap-matrix cells.

Our agenda is the first in the AI-SE mapping-study literature to **pre-register ERP3 priorities** against a formal gap matrix with Wieringa-typed study-call classifications — a reproducibility claim the practitioner-interview phase can validate, refute, or extend.

---

## 3. Novelty-comparison matrix (4 objectives × 3 reference surveys)

| | [15] Wang — AI Agentic Programming | [16] Wang — Agents in SE | [9] Otoum & Elkhalili |
|---|---|---|---|
| **C1 — RQ1 landscape** | [15] classifies system-level behaviors across 4 dimensions; no demand-side landscape. Our figures span year / F1 / F2 / F3 / F4 / F5 — [15] covers none of these facets as an SMS. | [16] reviews 115 agent studies through the perception-memory-action lens; no SMS-style facet distribution. Our RQ1 figures complement by characterizing the human-side empirical literature. | [9] has a partial landscape for methods + adoption (60-paper SLR); ours is a 640-paper SMS with F1–F5 coverage, so the scale and facet-breadth are substantially broader. |
| **C2 — RQ2 taxonomy** | [15] proposes behavior dimensions, not interaction modes; our delegation-depth axis is a different construct operating at the interaction layer. | [16] perception-memory-action is internal to the agent; our modes live at the human-agent boundary. No taxonomic overlap. | [9] does not propose an interaction taxonomy. |
| **C3 — RQ3 gap matrix** | [15] does not cross-tabulate its behaviors against usage. | [16] does not cross-tabulate agent capabilities against usage. | [9] identifies adoption trends but does not build a capability × SDLC cross-tab with a formal gap rule. |
| **C4 — Research agenda** | [15] names open questions at the system level; no Wieringa-typed prioritization. | [16] names agent-research challenges; no pre-registered ERP3 priority set. | [9] offers adoption-barrier observations; no structured research-call set. |

The matrix shows zero overlap at any (objective × reference survey) cell. The three reference surveys define the supply side; this study defines the demand side.

---

## 4. Practical implications (manuscript §5 anchor)

From proposal §5 Practical Implications + this study's artefacts:

1. **Organizations** can use `self_assessment_rubric.md` (Phase 4 Task 4.3) to self-locate along the 5-mode spectrum and `adoption_progression.md` for transition prerequisites. These artefacts are directly derived from the RQ2 taxonomy.
2. **Tool builders** can consult `gap_matrix.csv` + `gap_heatmap.png` to identify capability-usage asymmetries — cells where their build investments outrun empirical evidence of adoption.
3. **Researchers** can use `research_agenda.md` as a pre-registered priority set for empirical AI-SE studies; ERP3 begins from Call 1 (most-asymmetric priority 1.50 gaps).
4. **Educators** can use the mode taxonomy + `adoption_progression.md` as a curriculum structuring device, progressing students through Mode 1 → Mode 2 → Mode 4 evaluative practice → Mode 5 delegated-task experiences.

These four audiences map onto Petersen et al. (2015) §4 "significance of contribution" categories (academic, industry, education, tooling).

---

## 5. What this study does NOT claim

Explicit disclosure of what the novelty claims do not cover:

- **Not a practitioner study.** All claims derive from published literature; first-person practitioner evidence is ERP3 scope. Mode prevalence claims carry corpus bias (see `transferability.md §Boundary 1, 7`).
- **Not a causal study.** The gap matrix identifies correlational asymmetries between supply-side capabilities and demand-side evidence; it does not establish causal mechanisms (why gaps exist). Causal interpretations are ERP3 hypotheses (the 42 register rows), not SMS findings.
- **Not an inter-rater study.** This is a single-rater SMS; inter-rater reliability is an ERP3 validation step, documented in `transferability.md` and proposal §6.
- **Not a grey-literature-inclusive synthesis.** Industry-internal reports are explicitly out of scope (proposal §6 External Validity mitigation).

---

## References

- Proposal `docs/ERP2_Research_Proposal.docx` §1.3 (research objectives), §2 (background + 3 reference surveys), §5 (practical implications).
- Wang et al. (2025). *AI Agentic Programming: A Survey of Feedback, Planning, and Memory-Aware Code Generation*. Reference [15] in proposal.
- Wang et al. (2025). *Agents in Software Engineering: Survey, Landscape, and Vision*. Reference [16] in proposal.
- Otoum, N., & Elkhalili, N. (2026). *Methods and Techniques of Agentic Software Engineering: A Systematic Literature Review*. IEEE Access 14. Reference [9] in proposal.
- Petersen, K., Vakkalanka, S., & Kuzniarz, L. (2015). *Guidelines for conducting systematic mapping studies in software engineering: An update*. IST 64. — §4 contribution framing.
- Wieringa, R., Maiden, N., Mead, N., & Rolland, C. (2006). *Requirements engineering paper classification and evaluation criteria: a proposal and a discussion*. REJ 11(1). — Evaluation / Validation / Solution Proposal / Philosophical / Opinion / Personal Experience class definitions.
