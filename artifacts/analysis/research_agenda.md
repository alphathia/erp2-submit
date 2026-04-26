# Research Agenda — ERP3 Hypotheses Derived from the Capability-Usage Gap Matrix

**Sources:** `artifacts/analysis/rq3_gap_matrix/gap_matrix.csv` (171 cells); `artifacts/analysis/prioritised_gaps.md` (42 gaps ranked at P25 = 2.0); decision register Phase-5 `hypothesis_for_erp3` rows (n=42); `artifacts/analysis/rq3_gap_matrix/sensitivity_25_33.md` (robustness check).
**Vocabulary:** Wieringa et al. (2006) contribution classes — **Evaluation Research** (investigates a problem or a solution in its use context) and **Validation Research** (tests a solution's novel properties in isolation — typically laboratory studies of as-yet-un-deployed solutions).
**Scope:** 5 priority research calls framing the top 13 gaps (priority ≥ 1.00) as ERP3 primary-study proposals; an empty-cell appendix enumerating all 12 zero-evidence intersections as research-absence callouts; a cross-cutting themes section; and an RQ2 linkage mapping each call to the interaction-mode taxonomy.
**Rater:** TBS  **Authored:** 2026-04-20.

---

## 1. Framing

Phase 5 Task 5.2 produced a 19 × 9 capability × SDLC evidence matrix populated from 776 capability annotations across 383 contributing papers. Applying the proposal §3.5 RQ3 single-rule gap definition (25th percentile on non-zero cells; current P25 = 2.0; 33rd-percentile sensitivity flags 53 cells vs. 42 at P25) identifies **42 under-evidenced (capability × SDLC) intersections** and **12 empty cells** where no empirical evidence was recovered. The priority score in `prioritised_gaps.md` multiplies the P25 shortfall by the capability's reference-survey prevalence (1–3); this agenda frames the highest-priority gaps as concrete ERP3 study calls using Wieringa's contribution-type vocabulary so that each future study has a pre-specified methodological class and entry condition.

The agenda is prescriptive about *what to study next* and descriptive about *what the current literature does not cover*. It deliberately does not rank capabilities against each other in isolation — capability × SDLC **intersections** are the unit of priority, following the proposal's commitment to a demand-side cross-tabulation perspective. A capability like CAP_CODEGEN has saturated evidence at Coding (156 papers) but is invisible at early-lifecycle activities; the gap matrix surfaces this asymmetry deliberately.

---

## 2. Priority research calls

All five calls target gaps at priority ≥ 1.00 (evidence_count = 1 with prevalence ≥ 2). Calls are grouped by capability cluster because within-capability gaps at different SDLC activities admit shared methodological design.

### Call 1 — AI code completion at early-lifecycle activities (Requirements, Design)

- **Target gaps (2 at priority 1.50):** `CAP_CODECOMP × Requirements` (rank 2); `CAP_CODECOMP × Design` (rank 1).
- **Wieringa class:** **Evaluation Research.** Code-completion tools (GitHub Copilot, Cursor, tab-completion variants) are widely deployed in practice. The gap is in how developers actually use them at pre-coding activities — whether as prompt-interlocutors, sketch-producers, or not at all.
- **Research question template:** "In what ways, and to what effect, do practitioners use AI code-completion tools during requirements elicitation and software design activities, and how do those usage patterns compare to the Coding-stage usage that dominates the literature?"
- **Bucket (from decision register):** `design_gap` — the low evidence count suggests a conceptual mismatch between how completion tools are designed (code-first) and what early-lifecycle activities require (intent-first).
- **Population fit (from Task 5.1 mode × F3 table):** Professional SWE + Mixed cohorts are best suited; Student cohorts would speak only to educational contexts.
- **Study design suggestion:** Mixed-methods field study, N ≥ 20 professional teams; data = usage telemetry from completion tools + contextual interviews at requirements-workshop and design-review points. Triangulate against the interaction-mode taxonomy (Mode 1 Inline Completion vs. Mode 2 Conversational Prompting) to characterize the actual mode of use.
- **Why now:** CAP_CODECOMP has prevalence 3 (all three reference surveys name it); evidence_count 1 at each of these SDLC activities is the deepest asymmetry in the matrix for a fully-deployed capability.

### Call 2 — AI code translation beyond the coding boundary (Requirements, CI/CD, Project Management)

- **Target gaps (3 at priority 1.50):** `CAP_CODETRANS × Requirements` (rank 5); `CAP_CODETRANS × CI/CD` (rank 3); `CAP_CODETRANS × Project Management` (rank 4).
- **Wieringa class:** **Validation Research** at Requirements (translation-from-requirements is an as-yet-unproposed research solution for formalizing natural-language specs); **Evaluation Research** at CI/CD and Project Management (LLM-based translators are deployed for legacy modernization; the gap is in how those deployments integrate with pipeline automation and migration project management).
- **Research question template (Requirements):** "Can LLM-based translation between natural-language specifications and formal specification notations serve as a bridge between requirements engineering and downstream code generation, and under what conditions does such translation preserve specification intent?"
- **Research question template (CI/CD and PM):** "How do legacy-modernization projects integrate AI code translation into their pipeline automation and project-management workflows, and what organizational readiness conditions mediate effective use?"
- **Bucket:** `design_gap` (Requirements) and `organizational_readiness_barrier` (CI/CD, PM). The three-way split indicates the capability is well-published for language-pair translation but has been exercised neither as a requirements bridge nor as a CI/CD-pipeline asset.
- **Population fit:** Professional SWE in enterprise legacy-modernization contexts for CI/CD and PM calls; Mixed cohorts with domain experts for the Requirements call.
- **Study design suggestion:** Case-study series (n = 3–5 modernization projects) for CI/CD + PM; laboratory experiment (Validation Research) with paired requirements ↔ formal-spec datasets for the Requirements call.

### Call 3 — Agentic self-reflection outside Coding (Code Review, Documentation, Project Management)

- **Target gaps (3 at priority 1.50):** `CAP_SELFREFLECT × Code Review` (rank 6); `CAP_SELFREFLECT × Documentation` (rank 7); `CAP_SELFREFLECT × Project Management` (rank 8).
- **Wieringa class:** **Validation Research.** Self-reflection / iterative-refinement is an emerging agentic capability; published deployments are rare outside Coding. Early-stage studies in isolation are appropriate.
- **Research question template:** "To what extent does agentic self-reflection produce measurably better output when applied to (i) code-review synthesis, (ii) documentation generation, or (iii) project-management task decomposition, compared to single-pass baselines?"
- **Bucket:** `adoption_lag` across all three. The capability is named in all three reference surveys but deployed almost exclusively at Coding — a textbook adoption-lag pattern where supply-side research outruns demand-side use.
- **Population fit:** Validation Research is artefact-level; population is typically researcher-selected benchmark tasks. A follow-up Evaluation study with Professional SWE teams is warranted once initial validation results are in.
- **Study design suggestion:** Controlled comparison against single-pass baselines; ablation over reflection depth (1 round, 3 rounds, until convergence); three task classes corresponding to the three SDLC activities. This maps naturally onto Mode 5 Delegated Task Execution in the RQ2 taxonomy.

### Call 4 — Multi-agent orchestration at under-studied SDLC intersections (CI/CD, Code Review, Design)

- **Target gaps (3 at priority 1.00):** `CAP_MULTIAGENT × CI/CD` (rank 9); `CAP_MULTIAGENT × Code Review` (rank 10); `CAP_MULTIAGENT × Design` (rank 11).
- **Wieringa class:** **Validation Research** — multi-agent SE is predominantly supply-side at present; deployment evidence is thin.
- **Research question template:** "How do multi-agent orchestration frameworks perform when deployed as (i) CI/CD pipeline coordinators, (ii) collaborative code-review committees, or (iii) design-stage ideation partners, and what coordination patterns prove robust?"
- **Bucket:** `adoption_lag` (CI/CD, Code Review) and `design_gap` (Design). The Design gap is particularly telling — multi-agent systems are most-claimed as design-exploration tools in the reference surveys but have the thinnest empirical base at that activity.
- **Population fit:** Professional SWE in tooling-adoption-ready organizations; researcher-led laboratory studies acceptable as first-phase Validation.
- **Study design suggestion:** Benchmark framework evaluation (Validation) extended to a case-study Evaluation in a single organization with instrumented pipelines. This call has highest methodological kinship with Call 3.

### Call 5 — AI vulnerability detection beyond Coding (CI/CD, Project Management)

- **Target gaps (2 at priority 1.00):** `CAP_VULNDET × CI/CD` (rank 12); `CAP_VULNDET × Project Management` (rank 13).
- **Wieringa class:** **Evaluation Research.** Vulnerability-detection tools (Snyk-class, LLM-augmented SAST) are deployed in production; the gap is in how pipeline integration and program-level security management use them.
- **Research question template:** "How is AI-augmented vulnerability detection integrated into CI/CD pipelines and enterprise security-program management, and what organizational factors predict effective triage of AI-produced security alerts?"
- **Bucket:** `organizational_readiness_barrier`. Low evidence despite strong supply-side claims typically signals organizational rather than technical friction — security teams, audit obligations, and merge-gate policies mediate deployment.
- **Population fit:** Professional SWE in security-regulated industries; Mixed cohorts where security engineers and developers both participate.
- **Study design suggestion:** Multi-case study (n = 4–6 organizations across industries) with triangulated data: pipeline configurations, alert-disposition telemetry, interviews with security + engineering leads.

### Call 6 — Knowledge-management capabilities at non-native SDLC activities (priority 0.50 gaps)

- **Target gaps (10 at priority 0.50):** `CAP_CODESEARCH × {Code Review, Debugging, Documentation, Testing}` (ranks 14–17); `CAP_CODESUM × Requirements` (rank 18); `CAP_COMMITMSG × {CI/CD, Code Review, Debugging, Project Management, Testing}` (ranks 19–23).
- **Wieringa class:** **Evaluation Research.** All three capabilities — code search, code summarization, and commit-message generation — are deployed in production IDEs and pipelines. The gap is in how practitioners use these tools at SDLC activities other than their native home (search and summarization at Coding; commit messages at Coding and Documentation). Low prevalence in the reference surveys (1 of 3 each) tempers the priority, but the 10 gaps together constitute a coherent cluster worth one integrative study.
- **Research question template:** "Outside the coding flow, when and how do practitioners invoke AI-driven code search, code summarization, and commit-message generation — and what marginal value or friction do these tools produce at code review, testing, debugging, documentation, and CI/CD pipeline decision points?"
- **Bucket:** All 10 gaps fall into `organizational_readiness_barrier` (9) or `design_gap` (1, `CAP_CODESUM × Requirements`). The pattern indicates deployed tools that are technically applicable but under-adopted outside the coding flow — a classic organizational-readiness signature.
- **Population fit:** Professional SWE teams with mature CI/CD practices; Mixed cohorts if the study extends to documentation-authoring roles (technical writers, developer-advocate functions).
- **Study design suggestion:** Observational field study with usage telemetry from an AI-augmented IDE or pipeline assistant (N ≥ 30 professional teams over 6–12 weeks); secondary analysis of artifact-level outputs (search queries, summaries produced, commit messages accepted/rejected) stratified by SDLC activity. A single integrative study is preferable to 10 small studies because the usage patterns likely share organizational antecedents.
- **Why combined rather than split:** The 10 gaps span three capabilities across five SDLC activities but all carry low prevalence and the same 0.50 priority. Individually each is a thin signal; collectively they describe a coherent "knowledge-management tools at non-native activities" adoption question that can be answered with one well-scoped study.

### Borderline gaps at priority 0.00 (19 gaps)

Cells with `evidence_count == 2.0`, exactly at the P25 threshold. Their P25-shortfall is zero by construction (see `design/5_3_prioritize_gaps.md §4`), so priority score is 0.00. These are weak flags — at the boundary between "under-evidenced" and "normal". They are documented here for DoD completeness and mapped to the most relevant existing call for contextual reference; **they do not warrant dedicated ERP3 study calls** and should not drive agenda planning on their own.

| Rank | Capability × SDLC | Bucket | Maps to |
|---:|---|---|---|
| 24 | CAP_CICD × Code Review | organizational_readiness_barrier | Call 5 (security/pipeline cluster — secondary relevance) |
| 25 | CAP_CICD × Design | design_gap | No dedicated call; weak signal |
| 26 | CAP_CICD × Documentation | organizational_readiness_barrier | No dedicated call; weak signal |
| 27 | CAP_CICD × Project Management | organizational_readiness_barrier | Call 5 (pipeline-to-PM integration) |
| 28 | CAP_CODEREVIEW × Project Management | organizational_readiness_barrier | No dedicated call; weak signal |
| 29 | CAP_CODESUM × Code Review | organizational_readiness_barrier | Call 6 (knowledge-management cluster) |
| 30 | CAP_CODESUM × Design | design_gap | Call 6 |
| 31 | CAP_CODETRANS × Design | design_gap | Call 2 (extends the translation cluster to Design) |
| 32 | CAP_CODETRANS × Testing | organizational_readiness_barrier | Call 2 |
| 33 | CAP_COMMITMSG × Coding | organizational_readiness_barrier | Call 6 |
| 34 | CAP_COMMITMSG × Documentation | organizational_readiness_barrier | Call 6 |
| 35 | CAP_MULTIAGENT × Documentation | adoption_lag | Call 4 (extends multi-agent cluster) |
| 36 | CAP_PROGREPAIR × Design | design_gap | No dedicated call; weak signal |
| 37 | CAP_PROGREPAIR × Requirements | design_gap | No dedicated call; weak signal |
| 38 | CAP_REQENG × CI/CD | design_gap | No dedicated call; weak signal |
| 39 | CAP_REQENG × Code Review | design_gap | No dedicated call; weak signal |
| 40 | CAP_SELFREFLECT × Design | design_gap | Call 3 (extends self-reflection cluster) |
| 41 | CAP_SYSDESIGN × Project Management | design_gap | No dedicated call; weak signal |
| 42 | CAP_VULNDET × Documentation | organizational_readiness_barrier | Call 5 |

Nine of the 19 borderline gaps attach to an existing call (Calls 2, 3, 4, 5, 6); ten carry no dedicated call and are surfaced as audit-trail entries only. The Phase 6 dependability narrative should note that these borderline cells are a known weakness of the single-percentile gap rule — cells exactly at P25 are flagged as gaps but carry no priority, an intentional consequence of the formula that trades discriminatory power for methodological simplicity per proposal §3.5 RQ3.

---

## 3. Cross-cutting themes

- **Early-lifecycle activities dominate the gap list.** Requirements, Design, and Project Management collectively account for 15 of 42 gaps. Capability research is code-stage-centric; empirical evidence for pre-code AI use remains thin. Future ERP3 work should privilege early-lifecycle studies.
- **CI/CD is both under-evidenced and absent.** CI/CD appears as the SDLC activity with the most empty cells (4 of 12), yet also carries several priority gaps (ranks 3, 9, 12). The CI/CD column is where the corpus is simultaneously thin and uneven — a good target for both research-agenda calls and deliberate ERP3 sampling.
- **Self-reflection and multi-agent capabilities concentrate in `adoption_lag`.** These two emerging agentic capabilities produce the most adoption-lag flags because the supply-side community has moved faster than deployment. This is a reproducibility-of-claims risk worth surfacing in the Phase 6 credibility narrative.
- **Mature capabilities produce mostly `organizational_readiness_barrier` gaps.** Commit-message generation, code search, and CI/CD automation show low evidence at non-native SDLC activities (22 of 42 gaps in this bucket). The pattern is consistent with tools that work technically but under-adopt because of team or process friction.
- **Priority-0.00 gaps (cells exactly at P25 = 2.0) are borderline.** 19 of 42 gaps sit exactly at the threshold; their priority score is 0 by design. These are weak flags — the ERP3 agenda should not lead with them.

---

## 4. Empty cells — research-absence callouts

Proposal §3.5 RQ3 commits to treating empty cells (evidence_count = 0) as a distinct interpretive category. These are not gaps; they are absences — the distinguishing research question is not "why is this understudied?" but "why is this untouched, and should it be?"

### Empty-cell inventory (n = 12)

| Capability | SDLC Activity | Reference surveys naming it | Interpretive note |
|---|---|---:|---|
| CAP_CODECOMP | CI/CD | 3 | Completion tools operate at development time; their absence at CI/CD is architecturally expected, not a defect. Likely not a research call. |
| CAP_CODESEARCH | CI/CD | 1 | Search-in-pipeline is plausible (artefact discovery during deploys) but unstudied. Candidate exploratory ERP3 study. |
| CAP_CODESUM | CI/CD | 1 | Summarization-in-pipeline (auto-generating release notes from commits) is plausible and unstudied. Candidate ERP3 study. |
| CAP_SELFREFLECT | CI/CD | 3 | Agentic self-reflection at pipeline-decision points is a natural extension of Call 3 once initial validation lands. |
| CAP_CODESEARCH | Design | 1 | Reference-example retrieval during design is plausible. Candidate exploratory study. |
| CAP_COMMITMSG | Design | 1 | Architecturally inapplicable — commit-message generation presupposes existing code. Not a research call. |
| CAP_CODECOMP | Project Management | 3 | Architecturally inapplicable. Not a research call. |
| CAP_CODESEARCH | Project Management | 1 | Task-knowledge retrieval during PM is plausible but out of the current corpus. Candidate study. |
| CAP_CODESUM | Project Management | 1 | Summary-for-stakeholder-reporting is plausible. Candidate study. |
| CAP_CICD | Requirements | 2 | Inapplicable — CI/CD automation cannot run against requirements documents. Not a research call. |
| CAP_CODESEARCH | Requirements | 1 | Retrieval for related-requirements discovery is plausible. Candidate exploratory study. |
| CAP_COMMITMSG | Requirements | 1 | Inapplicable. Not a research call. |

### Empty-cell interpretation summary

Of 12 empty cells, **7 are candidate exploratory ERP3 studies** (novel research-absence intersections where the capability × activity pair is semantically plausible). **5 are architecturally inapplicable** (the capability cannot operate at that SDLC activity by construction; their empty status reinforces the validity of the coding rather than signalling missed research). This split is itself a finding: one-third of the empty cells are not "missing research" but "missing research question", which the Phase 6 transferability discussion should surface as a feature of the corpus-relative gap rule rather than a defect of the extraction.

---

## 5. Relationship to the interaction-mode taxonomy (RQ2 link)

Each priority call maps to one or more interaction modes in `artifacts/synthesis/interaction_taxonomy.md`. The linkage is informative because the modes carry operational definitions and paraphrased exemplars — future ERP3 studies can pre-specify which mode they target and align their study design with the mode's distinguishing criteria.

| Call | Capability cluster | Primary mode(s) | Secondary mode(s) |
|---|---|---|---|
| 1 | CAP_CODECOMP | **Mode 1 Inline Completion** | Mode 2 Conversational Prompting (at early lifecycle where completion becomes dialogic) |
| 2 | CAP_CODETRANS | **Mode 2 Conversational Prompting** (human-directed translation) | Mode 5 Delegated Task Execution (agent-scale migration) |
| 3 | CAP_SELFREFLECT | **Mode 5 Delegated Task Execution** | Mode 4 Review & Validation (self-reflection as a review mechanism) |
| 4 | CAP_MULTIAGENT | **Mode 5 Delegated Task Execution** | Mode 2 Conversational Prompting (human-in-the-loop orchestration) |
| 5 | CAP_VULNDET | **Mode 4 Review & Validation** | Mode 5 Delegated Task Execution (for automated triage) |

Two cross-cutting observations:

- **Mode 5 Delegated Task Execution dominates the priority-call map** (appears as primary or secondary in 4 of 5 calls). This is consistent with the observation in `interaction_taxonomy.md` §Mode 5 that delegated execution is the newest and fastest-moving mode in the 2022–2026 corpus — supply-side research has outpaced demand-side evidence, and that gap is reflected in both the taxonomy's Mode-5 label distribution and the RQ3 gap matrix.
- **Mode 3 Visual / Declarative Composition does not appear in any priority call.** This follows from the Low-code and No-code sub-populations being structurally data-sparse in the corpus (see Fig 4 of Task 5.1 Part A — 30 and 72 distinct papers respectively, versus 537 Pro-code papers). ERP3 study design should consider whether to deliberately sample Low-code and No-code contexts to counter this under-representation.

---

## 6. Methodological references

- Proposal §3.5 RQ3 — single-rule gap definition; 25th-percentile threshold on non-zero cells; empty cells reported as a distinct interpretive category.
- Proposal §5.3 — practical implications; research-agenda derivation as a Phase-5 output.
- Wieringa et al. (2006) — Evaluation Research vs. Validation Research class definitions.
- Petersen et al. (2015) §7 — research-agenda structure for systematic mapping studies.
- Cruzes & Dybå (2011) Step 5 — interpretation phase; turning synthesis outputs into agendas.

---

## 7. Provenance

- **Generated:** 2026-04-20.
- **Inputs:** `artifacts/analysis/prioritised_gaps.md`; `artifacts/analysis/rq3_gap_matrix/gap_matrix.csv`; `decision_register.csv` Phase-5 `hypothesis_for_erp3` rows; `artifacts/synthesis/interaction_taxonomy.md` for the RQ2 linkage in §5.
- **Author:** TBS (single-rater study; hand-drafted from the deterministic prioritization output).
- **Companion artefacts:** `prioritised_gaps.md` (full 42-gap ranked table + rationale register); `sensitivity_25_33.md` (P25 vs P33 robustness check).
