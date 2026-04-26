# Phase 1 Report — Protocol Finalization & Capability Harmonization

**Study:** How Do People Use AI Agents for Software Engineering? (ERP2-SMS)
**Phase:** 1 (D.1 per research plan)
**Period:** 2026-04-12 to 2026-04-13
**Status:** Complete — pending supervisor sign-off

---

## 1. Objective

Phase 1 finalizes the research protocol before corpus-level search and screening begin in Phase 2. It produces the complete set of instruments needed to execute the SMS: search strings, inclusion/exclusion criteria, a five-facet codebook, a harmonized capability list, screening and extraction instruments, and a pilot validation of all instruments against real papers.

Methodology anchors: Petersen et al. (2008, 2015) for SMS design; Wieringa et al. (2006) for F1 Contribution Type; Cruzes & Dybå (2011, 2015) for extraction/synthesis separation; Ali & Petersen (2014) for study-selection discipline.

---

## 2. Tasks Completed

### Task 1.1 — Search Strings + Scopus Query Envelope

- **Artifacts:**
  - `artifacts/protocol/search_strings.md` — verbatim S1–S6 from proposal Appendix A.1
  - `artifacts/protocol/scopus_query_template.txt` — full Scopus query with TITLE-ABS-KEY wrapping all six strings + Layer-1 metadata filters
- **Code:** `code/dod_checks.py::check_phase1_task1_1` — replaces NotImplementedError stub; asserts S1–S6 labels, balanced parentheses (38 pairs), six string fragments, six filter keywords
- **DoD result:** PASS — all four assertions verified
- **Commits:** `51f78b1`, `c926ff2`

### Task 1.2 — Finalise IC/EC

- **Artifact:** `artifacts/protocol/inclusion_exclusion.md` — rewritten Appendix A.2 with IC1–IC5 and EC1–EC6, each tagged with enforcement layer (Q/S/P)
- **Key design decisions:**
  - IC3 (peer-reviewed) split from original IC1's source-type clause
  - IC5 (≥4 pages) added as new post-retrieval criterion
  - EC6 (full text not retrievable within 2 weeks) added for Phase 3
  - EC1 cites Wieringa "Solution Proposal"; EC2 cites Wieringa "Validation Research"
- **DoD result:** PASS — 11 tagged criteria, Wieringa cited at EC1 and EC2
- **Commit:** `69e3907`

### Task 1.3 — Five-Facet Codebook

- **Artifact:** `artifacts/protocol/codebook.md` — one section per facet with definition, controlled values, 2 positive + 2 negative exemplars, borderline decision rule
- **Facets:**
  - F1 Contribution Type — Wieringa's six classes verbatim (Evaluation Research, Validation Research, Solution Proposal, Philosophical, Opinion, Personal Experience)
  - F2 Research Methodology — Survey, Interview, Case Study, Experiment, Field Study, Mining Study, Mixed
  - F3 Population & Context — composite {Professional SWE, Student, Citizen Developer, OSS Contributor, Mixed} x {Industry, Education, OSS, Lab}
  - F4 SDLC Activity — 9 values, multi-select (Requirements, Design, Coding, Testing, Code Review, Debugging, CI/CD, Documentation, Project Management)
  - F5 Agent/Tool Profile — composite {Autocomplete, Conversational, IDE-Integrated, Autonomous} x {Pro-code, Low-code, No-code}
- **Design note:** Interaction Mode (RQ2) and Capability Category (RQ3) are explicitly excluded from extraction facets per Cruzes & Dybå extraction/synthesis separation
- **DoD result:** PASS — all 5 facet headers, all 6 Wieringa classes, 20 exemplars (4 per facet)
- **Commit:** `779f25b`

### Task 1.4 — Harmonise Capability List

- **Artifacts:**
  - `artifacts/protocol/capability_list.csv` — 43 rows, 19 unique capability IDs
  - `artifacts/protocol/capability_list.csv.meta.json` — provenance sidecar
- **Source surveys read:**
  1. Otoum & Elkhalili (2026) — 23 pages, 15 capability claims extracted
  2. Wang — Agents in SE (2025) — 36 pages, 13 capability claims extracted
  3. Wang — AI Agentic Programming (2025) — 36 pages, 15 capability claims extracted
- **19 harmonized capabilities:** CAP_CODEGEN, CAP_CODECOMP, CAP_PROGREPAIR, CAP_TESTING, CAP_DEBUGGING, CAP_CODEREVIEW, CAP_REFACTORING, CAP_DOCGEN, CAP_CODESEARCH, CAP_CODESUM, CAP_CODETRANS, CAP_VULNDET, CAP_REQENG, CAP_SYSDESIGN, CAP_CICD, CAP_COMMITMSG, CAP_PLANNING, CAP_MULTIAGENT, CAP_SELFREFLECT
- **Finding:** All 19 capabilities are pro-code-centric. LCNC-specific capabilities (app generation, workflow automation, data connector configuration) are not represented because the three source surveys focus on coding agents.
- **Decision registered:** `retain_procode_capabilities_defer_lcnc` — defer LCNC assessment to pilot (Task 1.6). Paradigm gaps captured via F5 secondary cross-tabulation per proposal §3.5.
- **DoD result:** PASS — source_paper non-null, no conflicting labels, ≥1 row per seed
- **Commits:** `54aa179`, `0966082`

### Task 1.5 — Build Screening & Extraction Instruments

- **Artifacts:**
  - `artifacts/protocol/screening_instrument.md` — Phase 2 decision tree with 11 nodes across 3 layers (Layer 1 query-enforced: IC1, IC3, IC4, EC4; Layer 2 manual screening: IC2, EC1, EC2, EC3; Layer 3 post-retrieval: IC5/EC5, EC6) + borderline protocol
  - `artifacts/protocol/extraction_schema.md` — column schema for `extraction_matrix.csv` in 3 regions: Region 1 Metadata (M1 bibliographic 7 cols, M2 sample 3 cols), Region 2 Facets (F1–F5 per codebook, 8 cols), Region 3 Synthesis-Register Inputs (5 cols)
- **Design note:** Extraction schema enforces Cruzes & Dybå separation — synthesis outputs (Interaction Mode, Capability Category) are not stored in the extraction matrix; Region 3 holds file pointers to downstream synthesis artifacts
- **DoD result:** PASS — all section headers, all 11 criteria, all 3 regions, all key columns present
- **Commit:** `5aafc3e`

### Task 1.6 — Pilot on 2–3 Papers

- **Artifact:** `artifacts/protocol/pilot_report.md` — complete pilot report with screening walkthroughs, extraction tables, ambiguity log, and codebook refinements
- **Supporting artifact:** `artifacts/extraction/retrieval_status.csv` — paper_id → filename mapping for 8 candidate papers (Option B: human-readable filenames)
- **Papers piloted:**

| Paper | Decision | Category | Key evidence |
|-------|----------|----------|-------------|
| P1: Banh et al. (2025) — Copiloting the future | INCLUDE | Include | Interview study, 18 SE professionals, Grounded Theory; Evaluation Research |
| P2: Ajimati et al. (2025) — Adoption of LCNC development | EXCLUDE (EC4) | Exclude | SLR of 40 primary studies; seed paper #5 |
| P3: Liang et al. (2024) — Large-Scale Survey on Usability of AI Programming Assistants | INCLUDE (borderline at EC4 → resolved) | Borderline | Survey questionnaire, 410 developers; "Survey" in title triggered EC4 uncertainty, resolved by reading abstract |

- **Ambiguities discovered:** 7 across 3 papers (2 from P1, 2 from P2, 3 from P3)
- **Codebook refinements:** 5 approved and applied:

| # | Facet | Refinement |
|---|-------|-----------|
| 1 | F2 | Survey disambiguation — "Survey" in F2 means questionnaire, not literature review |
| 2 | F3 | Mixed population ≥80% threshold rule + "end-user developer" mapping |
| 3 | F4 | Ideation/planning → Design; learning/recalling → code underlying SDLC activity |
| 4 | F5 | Multi-tool generic attribution — code union of modalities when paper says "GenAI" generically |
| 5 | Screening | EC4 screening notes added to codebook top: discriminators for literature survey vs questionnaire vs hybrid |

- **LCNC capability assessment:** Deferred. P2 (LCNC SLR) was excluded under EC4 before extraction could test capability mapping. Decision register entry remains active.
- **DoD result:** PASS — ≥1 include + ≥1 exclude + ≥1 borderline; ≥1 codebook refinement committed
- **Commits:** `9cd28d4`, `c986c76`, `2a3a790`, `aaf6494`

---

## 3. Artifact Index

All Phase 1 artifacts reside under `artifacts/protocol/`:

| Artifact | Path | Task | Description |
|----------|------|------|-------------|
| Search strings | `artifacts/protocol/search_strings.md` | 1.1 | S1–S6 verbatim from proposal Appendix A.1 |
| Scopus query template | `artifacts/protocol/scopus_query_template.txt` | 1.1 | Full query with Layer-1 metadata filters |
| Inclusion/exclusion criteria | `artifacts/protocol/inclusion_exclusion.md` | 1.2 | IC1–IC5, EC1–EC6 with Q/S/P enforcement tags |
| Five-facet codebook | `artifacts/protocol/codebook.md` | 1.3, 1.6 | F1–F5 definitions, values, exemplars, borderline rules (refined post-pilot) |
| Capability list | `artifacts/protocol/capability_list.csv` | 1.4 | 43 rows, 19 capability IDs from 3 seed surveys |
| Capability list metadata | `artifacts/protocol/capability_list.csv.meta.json` | 1.4 | Provenance sidecar |
| Screening instrument | `artifacts/protocol/screening_instrument.md` | 1.5 | Decision tree with 11 nodes across 3 layers |
| Extraction schema | `artifacts/protocol/extraction_schema.md` | 1.5 | Column schema (23 cols, 3 regions) for extraction_matrix.csv |
| Pilot report | `artifacts/protocol/pilot_report.md` | 1.6 | Full pilot on 3 papers with ambiguities and refinements |
| Retrieval status | `artifacts/extraction/retrieval_status.csv` | 1.6 | paper_id → filename mapping for pilot papers |

**Code artifacts:**

| Artifact | Path | Task | Description |
|----------|------|------|-------------|
| DoD checker (phase1_task1_1) | `code/dod_checks.py` | 1.1 | Verifies search strings and query template |

**Decision register entries:**

| Timestamp | Decision | Task |
|-----------|----------|------|
| 2026-04-12T12:28:42Z | `retain_procode_capabilities_defer_lcnc` | 1.4 |
| 2026-04-13T08:18:49Z | `codebook_refined_post_pilot` | 1.6 |

---

## 4. Key Findings and Observations

### 4.1 Capability list is pro-code-centric

All 19 harmonised capabilities derive from three surveys focused on agentic SE and coding agents. LCNC-specific capabilities (NL-to-app generation, workflow automation, data connector configuration) are absent. This is not a design flaw — it reflects the current supply-side literature. The F5 sub-facet B (Pro-code / Low-code / No-code) and the proposal's secondary cross-tabulation by Agent/Tool Profile will capture paradigm-specific gaps at the analysis stage.

### 4.2 Pilot confirmed instrument usability with refinements needed

The pilot on 3 papers revealed 7 ambiguities, leading to 5 codebook refinements. The most significant:
- **"Survey" ambiguity (EC4/F2):** The word "survey" in a paper title can mean either a literature review (exclude) or a questionnaire study (include). This was the primary source of the borderline case and led to the new Screening Notes section in the codebook.
- **Multi-tool generic attribution (F5):** Papers studying multiple AI tools often discuss "GenAI" generically. The new rule codes the union of modalities and flags aggregate attribution.
- **Design/Requirements boundary (F4):** "Ideation and planning" now maps to Design unless requirements specification is explicitly discussed.

### 4.3 Extraction schema enforces Cruzes & Dybå separation

The three-region extraction schema (Metadata / Facets / Synthesis-Register Inputs) explicitly prevents mixing extraction-layer codings with synthesis-layer outputs. Interaction Mode and Capability Category are not columns in the extraction matrix — they are derived downstream in Phase 4 and Phase 5 respectively.

### 4.4 Pilot papers provide early landscape signals

From the two included pilot papers:
- Both study **pro-code** tools (ChatGPT, GitHub Copilot, Tabnine) — no LCNC coverage
- Both focus on **Coding** as the dominant SDLC activity
- Population is **Professional SWE** (P1) and **Mixed** GitHub-recruited (P3)
- Research methods are **Interview** (P1) and **Survey** (P3) — no experiments or mining studies yet

These early signals are consistent with the proposal's observation that "GitHub Copilot and ChatGPT dominate" and "code generation/completion accounts for most studies."

---

## 5. Open Items for Phase 2

1. **Phase 1 Exit:** Supervisor sign-off needed → record in `decision_register.csv` (phase=1, decision='phase1_approved')
2. **LCNC capability assessment:** Deferred — will be triggered when the first primary LCNC usage paper enters the corpus during Phase 2 screening
3. **Scopus access path:** Must be confirmed (API key or web UI export) before Task 2.1 executes — check `memory.md` and `.env`
4. **Pilot papers in corpus:** P1 (Banh) and P3 (Liang) passed screening — if they appear in the Phase 2 search results, their screening decisions are already logged and extraction can proceed directly

---

## 6. Methodology References

| Anchor | Role in Phase 1 |
|--------|----------------|
| Petersen et al. (2008) | SMS design: keywording, classification facets |
| Petersen et al. (2015) | Protocol refinement (§6), facet-based classification, reporting |
| Wieringa et al. (2006) | F1 Contribution Type: six classes verbatim from §3 |
| Cruzes & Dybå (2011) | Extraction/synthesis separation enforced in extraction schema |
| Cruzes et al. (2015) | Thematic synthesis steps (downstream in Phase 4) |
| Ali & Petersen (2014) | Study-selection process discipline; screening instrument design; protocol piloting |
