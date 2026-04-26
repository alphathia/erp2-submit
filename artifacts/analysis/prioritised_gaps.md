# Prioritised Gaps — RQ3

**Source:** `artifacts/analysis/rq3_gap_matrix/gap_matrix.csv` (P25 = 2.0 on non-zero cells).
**Script:** `code/prioritize_gaps.py`
**Generated:** 2026-04-20T04:07:32.351134+00:00
**Gap count:** 42 (at P25). **Empty cells** (tracked separately, not gaps): 12.
**Priority formula:** `priority = P25_shortfall × capability_prevalence` where `P25_shortfall = (P25 − evidence_count) / P25` and `capability_prevalence = in_source_survey ∈ {1,2,3}`.

## Ranked gap list

| Rank | Capability | Label | SDLC Activity | Evidence | P25-shortfall | Prevalence | Priority | ERP3 bucket |
|---:|---|---|---|---:|---:|---:|---:|---|
| 1 | CAP_CODECOMP | Code Completion | Design | 1 | 0.50 | 3 | 1.50 | design_gap |
| 2 | CAP_CODECOMP | Code Completion | Requirements | 1 | 0.50 | 3 | 1.50 | design_gap |
| 3 | CAP_CODETRANS | Code Translation | CI/CD | 1 | 0.50 | 3 | 1.50 | organizational_readiness_barrier |
| 4 | CAP_CODETRANS | Code Translation | Project Management | 1 | 0.50 | 3 | 1.50 | organizational_readiness_barrier |
| 5 | CAP_CODETRANS | Code Translation | Requirements | 1 | 0.50 | 3 | 1.50 | design_gap |
| 6 | CAP_SELFREFLECT | Self-Reflection and Iterative Refinement | Code Review | 1 | 0.50 | 3 | 1.50 | adoption_lag |
| 7 | CAP_SELFREFLECT | Self-Reflection and Iterative Refinement | Documentation | 1 | 0.50 | 3 | 1.50 | adoption_lag |
| 8 | CAP_SELFREFLECT | Self-Reflection and Iterative Refinement | Project Management | 1 | 0.50 | 3 | 1.50 | adoption_lag |
| 9 | CAP_MULTIAGENT | Multi-Agent Collaboration | CI/CD | 1 | 0.50 | 2 | 1.00 | adoption_lag |
| 10 | CAP_MULTIAGENT | Multi-Agent Collaboration | Code Review | 1 | 0.50 | 2 | 1.00 | adoption_lag |
| 11 | CAP_MULTIAGENT | Multi-Agent Collaboration | Design | 1 | 0.50 | 2 | 1.00 | design_gap |
| 12 | CAP_VULNDET | Vulnerability Detection | CI/CD | 1 | 0.50 | 2 | 1.00 | organizational_readiness_barrier |
| 13 | CAP_VULNDET | Vulnerability Detection | Project Management | 1 | 0.50 | 2 | 1.00 | organizational_readiness_barrier |
| 14 | CAP_CODESEARCH | Code Search and Retrieval | Code Review | 1 | 0.50 | 1 | 0.50 | organizational_readiness_barrier |
| 15 | CAP_CODESEARCH | Code Search and Retrieval | Debugging | 1 | 0.50 | 1 | 0.50 | organizational_readiness_barrier |
| 16 | CAP_CODESEARCH | Code Search and Retrieval | Documentation | 1 | 0.50 | 1 | 0.50 | organizational_readiness_barrier |
| 17 | CAP_CODESEARCH | Code Search and Retrieval | Testing | 1 | 0.50 | 1 | 0.50 | organizational_readiness_barrier |
| 18 | CAP_CODESUM | Code Summarisation | Requirements | 1 | 0.50 | 1 | 0.50 | design_gap |
| 19 | CAP_COMMITMSG | Commit Message Generation | CI/CD | 1 | 0.50 | 1 | 0.50 | organizational_readiness_barrier |
| 20 | CAP_COMMITMSG | Commit Message Generation | Code Review | 1 | 0.50 | 1 | 0.50 | organizational_readiness_barrier |
| 21 | CAP_COMMITMSG | Commit Message Generation | Debugging | 1 | 0.50 | 1 | 0.50 | organizational_readiness_barrier |
| 22 | CAP_COMMITMSG | Commit Message Generation | Project Management | 1 | 0.50 | 1 | 0.50 | organizational_readiness_barrier |
| 23 | CAP_COMMITMSG | Commit Message Generation | Testing | 1 | 0.50 | 1 | 0.50 | organizational_readiness_barrier |
| 24 | CAP_CICD | CI/CD and Deployment Automation | Code Review | 2 | 0.00 | 2 | 0.00 | organizational_readiness_barrier |
| 25 | CAP_CICD | CI/CD and Deployment Automation | Design | 2 | 0.00 | 2 | 0.00 | design_gap |
| 26 | CAP_CICD | CI/CD and Deployment Automation | Documentation | 2 | 0.00 | 2 | 0.00 | organizational_readiness_barrier |
| 27 | CAP_CICD | CI/CD and Deployment Automation | Project Management | 2 | 0.00 | 2 | 0.00 | organizational_readiness_barrier |
| 28 | CAP_CODEREVIEW | Automated Code Review | Project Management | 2 | 0.00 | 3 | 0.00 | organizational_readiness_barrier |
| 29 | CAP_CODESUM | Code Summarisation | Code Review | 2 | 0.00 | 1 | 0.00 | organizational_readiness_barrier |
| 30 | CAP_CODESUM | Code Summarisation | Design | 2 | 0.00 | 1 | 0.00 | design_gap |
| 31 | CAP_CODETRANS | Code Translation | Design | 2 | 0.00 | 3 | 0.00 | design_gap |
| 32 | CAP_CODETRANS | Code Translation | Testing | 2 | 0.00 | 3 | 0.00 | organizational_readiness_barrier |
| 33 | CAP_COMMITMSG | Commit Message Generation | Coding | 2 | 0.00 | 1 | 0.00 | organizational_readiness_barrier |
| 34 | CAP_COMMITMSG | Commit Message Generation | Documentation | 2 | 0.00 | 1 | 0.00 | organizational_readiness_barrier |
| 35 | CAP_MULTIAGENT | Multi-Agent Collaboration | Documentation | 2 | 0.00 | 2 | 0.00 | adoption_lag |
| 36 | CAP_PROGREPAIR | Program Repair / Bug Fixing | Design | 2 | 0.00 | 3 | 0.00 | design_gap |
| 37 | CAP_PROGREPAIR | Program Repair / Bug Fixing | Requirements | 2 | 0.00 | 3 | 0.00 | design_gap |
| 38 | CAP_REQENG | Requirements Engineering | CI/CD | 2 | 0.00 | 2 | 0.00 | design_gap |
| 39 | CAP_REQENG | Requirements Engineering | Code Review | 2 | 0.00 | 2 | 0.00 | design_gap |
| 40 | CAP_SELFREFLECT | Self-Reflection and Iterative Refinement | Design | 2 | 0.00 | 3 | 0.00 | design_gap |
| 41 | CAP_SYSDESIGN | System Design and Architecture | Project Management | 2 | 0.00 | 1 | 0.00 | design_gap |
| 42 | CAP_VULNDET | Vulnerability Detection | Documentation | 2 | 0.00 | 2 | 0.00 | organizational_readiness_barrier |

## Rationale register

### Rank 1 — CAP_CODECOMP × Design (priority 1.50)

- **Capability label:** Code Completion
- **Evidence count:** 1 (P25 = 2.0)
- **Bucket:** design_gap
- **Rationale (from `decision_register.csv`):** design_gap: Evidence for CAP_CODECOMP at the Design activity is below the P25 non-zero threshold, indicating an under-researched early-lifecycle intersection that warrants ERP3 investigation.

### Rank 2 — CAP_CODECOMP × Requirements (priority 1.50)

- **Capability label:** Code Completion
- **Evidence count:** 1 (P25 = 2.0)
- **Bucket:** design_gap
- **Rationale (from `decision_register.csv`):** design_gap: Evidence for CAP_CODECOMP at the Requirements activity is below the P25 non-zero threshold, indicating an under-researched early-lifecycle intersection that warrants ERP3 investigation.

### Rank 3 — CAP_CODETRANS × CI/CD (priority 1.50)

- **Capability label:** Code Translation
- **Evidence count:** 1 (P25 = 2.0)
- **Bucket:** organizational_readiness_barrier
- **Rationale (from `decision_register.csv`):** organizational_readiness_barrier: Evidence for mature capability CAP_CODETRANS at CI/CD is below the P25 non-zero threshold, suggesting organizational or process friction rather than a technical shortfall.

### Rank 4 — CAP_CODETRANS × Project Management (priority 1.50)

- **Capability label:** Code Translation
- **Evidence count:** 1 (P25 = 2.0)
- **Bucket:** organizational_readiness_barrier
- **Rationale (from `decision_register.csv`):** organizational_readiness_barrier: Evidence for mature capability CAP_CODETRANS at Project Management is below the P25 non-zero threshold, suggesting organizational or process friction rather than a technical shortfall.

### Rank 5 — CAP_CODETRANS × Requirements (priority 1.50)

- **Capability label:** Code Translation
- **Evidence count:** 1 (P25 = 2.0)
- **Bucket:** design_gap
- **Rationale (from `decision_register.csv`):** design_gap: Evidence for CAP_CODETRANS at the Requirements activity is below the P25 non-zero threshold, indicating an under-researched early-lifecycle intersection that warrants ERP3 investigation.

### Rank 6 — CAP_SELFREFLECT × Code Review (priority 1.50)

- **Capability label:** Self-Reflection and Iterative Refinement
- **Evidence count:** 1 (P25 = 2.0)
- **Bucket:** adoption_lag
- **Rationale (from `decision_register.csv`):** adoption_lag: Evidence for the autonomy-leaning capability CAP_SELFREFLECT at Code Review is below the P25 non-zero threshold, consistent with known lag between research-frontier capabilities and practical SDLC adoption.

### Rank 7 — CAP_SELFREFLECT × Documentation (priority 1.50)

- **Capability label:** Self-Reflection and Iterative Refinement
- **Evidence count:** 1 (P25 = 2.0)
- **Bucket:** adoption_lag
- **Rationale (from `decision_register.csv`):** adoption_lag: Evidence for the autonomy-leaning capability CAP_SELFREFLECT at Documentation is below the P25 non-zero threshold, consistent with known lag between research-frontier capabilities and practical SDLC adoption.

### Rank 8 — CAP_SELFREFLECT × Project Management (priority 1.50)

- **Capability label:** Self-Reflection and Iterative Refinement
- **Evidence count:** 1 (P25 = 2.0)
- **Bucket:** adoption_lag
- **Rationale (from `decision_register.csv`):** adoption_lag: Evidence for the autonomy-leaning capability CAP_SELFREFLECT at Project Management is below the P25 non-zero threshold, consistent with known lag between research-frontier capabilities and practical SDLC adoption.

### Rank 9 — CAP_MULTIAGENT × CI/CD (priority 1.00)

- **Capability label:** Multi-Agent Collaboration
- **Evidence count:** 1 (P25 = 2.0)
- **Bucket:** adoption_lag
- **Rationale (from `decision_register.csv`):** adoption_lag: Evidence for the autonomy-leaning capability CAP_MULTIAGENT at CI/CD is below the P25 non-zero threshold, consistent with known lag between research-frontier capabilities and practical SDLC adoption.

### Rank 10 — CAP_MULTIAGENT × Code Review (priority 1.00)

- **Capability label:** Multi-Agent Collaboration
- **Evidence count:** 1 (P25 = 2.0)
- **Bucket:** adoption_lag
- **Rationale (from `decision_register.csv`):** adoption_lag: Evidence for the autonomy-leaning capability CAP_MULTIAGENT at Code Review is below the P25 non-zero threshold, consistent with known lag between research-frontier capabilities and practical SDLC adoption.

### Rank 11 — CAP_MULTIAGENT × Design (priority 1.00)

- **Capability label:** Multi-Agent Collaboration
- **Evidence count:** 1 (P25 = 2.0)
- **Bucket:** design_gap
- **Rationale (from `decision_register.csv`):** design_gap: Evidence for CAP_MULTIAGENT at the Design activity is below the P25 non-zero threshold, indicating an under-researched early-lifecycle intersection that warrants ERP3 investigation.

### Rank 12 — CAP_VULNDET × CI/CD (priority 1.00)

- **Capability label:** Vulnerability Detection
- **Evidence count:** 1 (P25 = 2.0)
- **Bucket:** organizational_readiness_barrier
- **Rationale (from `decision_register.csv`):** organizational_readiness_barrier: Evidence for mature capability CAP_VULNDET at CI/CD is below the P25 non-zero threshold, suggesting organizational or process friction rather than a technical shortfall.

### Rank 13 — CAP_VULNDET × Project Management (priority 1.00)

- **Capability label:** Vulnerability Detection
- **Evidence count:** 1 (P25 = 2.0)
- **Bucket:** organizational_readiness_barrier
- **Rationale (from `decision_register.csv`):** organizational_readiness_barrier: Evidence for mature capability CAP_VULNDET at Project Management is below the P25 non-zero threshold, suggesting organizational or process friction rather than a technical shortfall.

### Rank 14 — CAP_CODESEARCH × Code Review (priority 0.50)

- **Capability label:** Code Search and Retrieval
- **Evidence count:** 1 (P25 = 2.0)
- **Bucket:** organizational_readiness_barrier
- **Rationale (from `decision_register.csv`):** organizational_readiness_barrier: Evidence for mature capability CAP_CODESEARCH at Code Review is below the P25 non-zero threshold, suggesting organizational or process friction rather than a technical shortfall.

### Rank 15 — CAP_CODESEARCH × Debugging (priority 0.50)

- **Capability label:** Code Search and Retrieval
- **Evidence count:** 1 (P25 = 2.0)
- **Bucket:** organizational_readiness_barrier
- **Rationale (from `decision_register.csv`):** organizational_readiness_barrier: Evidence for mature capability CAP_CODESEARCH at Debugging is below the P25 non-zero threshold, suggesting organizational or process friction rather than a technical shortfall.

### Rank 16 — CAP_CODESEARCH × Documentation (priority 0.50)

- **Capability label:** Code Search and Retrieval
- **Evidence count:** 1 (P25 = 2.0)
- **Bucket:** organizational_readiness_barrier
- **Rationale (from `decision_register.csv`):** organizational_readiness_barrier: Evidence for mature capability CAP_CODESEARCH at Documentation is below the P25 non-zero threshold, suggesting organizational or process friction rather than a technical shortfall.

### Rank 17 — CAP_CODESEARCH × Testing (priority 0.50)

- **Capability label:** Code Search and Retrieval
- **Evidence count:** 1 (P25 = 2.0)
- **Bucket:** organizational_readiness_barrier
- **Rationale (from `decision_register.csv`):** organizational_readiness_barrier: Evidence for mature capability CAP_CODESEARCH at Testing is below the P25 non-zero threshold, suggesting organizational or process friction rather than a technical shortfall.

### Rank 18 — CAP_CODESUM × Requirements (priority 0.50)

- **Capability label:** Code Summarisation
- **Evidence count:** 1 (P25 = 2.0)
- **Bucket:** design_gap
- **Rationale (from `decision_register.csv`):** design_gap: Evidence for CAP_CODESUM at the Requirements activity is below the P25 non-zero threshold, indicating an under-researched early-lifecycle intersection that warrants ERP3 investigation.

### Rank 19 — CAP_COMMITMSG × CI/CD (priority 0.50)

- **Capability label:** Commit Message Generation
- **Evidence count:** 1 (P25 = 2.0)
- **Bucket:** organizational_readiness_barrier
- **Rationale (from `decision_register.csv`):** organizational_readiness_barrier: Evidence for mature capability CAP_COMMITMSG at CI/CD is below the P25 non-zero threshold, suggesting organizational or process friction rather than a technical shortfall.

### Rank 20 — CAP_COMMITMSG × Code Review (priority 0.50)

- **Capability label:** Commit Message Generation
- **Evidence count:** 1 (P25 = 2.0)
- **Bucket:** organizational_readiness_barrier
- **Rationale (from `decision_register.csv`):** organizational_readiness_barrier: Evidence for mature capability CAP_COMMITMSG at Code Review is below the P25 non-zero threshold, suggesting organizational or process friction rather than a technical shortfall.

### Rank 21 — CAP_COMMITMSG × Debugging (priority 0.50)

- **Capability label:** Commit Message Generation
- **Evidence count:** 1 (P25 = 2.0)
- **Bucket:** organizational_readiness_barrier
- **Rationale (from `decision_register.csv`):** organizational_readiness_barrier: Evidence for mature capability CAP_COMMITMSG at Debugging is below the P25 non-zero threshold, suggesting organizational or process friction rather than a technical shortfall.

### Rank 22 — CAP_COMMITMSG × Project Management (priority 0.50)

- **Capability label:** Commit Message Generation
- **Evidence count:** 1 (P25 = 2.0)
- **Bucket:** organizational_readiness_barrier
- **Rationale (from `decision_register.csv`):** organizational_readiness_barrier: Evidence for mature capability CAP_COMMITMSG at Project Management is below the P25 non-zero threshold, suggesting organizational or process friction rather than a technical shortfall.

### Rank 23 — CAP_COMMITMSG × Testing (priority 0.50)

- **Capability label:** Commit Message Generation
- **Evidence count:** 1 (P25 = 2.0)
- **Bucket:** organizational_readiness_barrier
- **Rationale (from `decision_register.csv`):** organizational_readiness_barrier: Evidence for mature capability CAP_COMMITMSG at Testing is below the P25 non-zero threshold, suggesting organizational or process friction rather than a technical shortfall.

### Rank 24 — CAP_CICD × Code Review (priority 0.00)

- **Capability label:** CI/CD and Deployment Automation
- **Evidence count:** 2 (P25 = 2.0)
- **Bucket:** organizational_readiness_barrier
- **Rationale (from `decision_register.csv`):** organizational_readiness_barrier: Evidence for mature capability CAP_CICD at Code Review is below the P25 non-zero threshold, suggesting organizational or process friction rather than a technical shortfall.

### Rank 25 — CAP_CICD × Design (priority 0.00)

- **Capability label:** CI/CD and Deployment Automation
- **Evidence count:** 2 (P25 = 2.0)
- **Bucket:** design_gap
- **Rationale (from `decision_register.csv`):** design_gap: Evidence for CAP_CICD at the Design activity is below the P25 non-zero threshold, indicating an under-researched early-lifecycle intersection that warrants ERP3 investigation.

### Rank 26 — CAP_CICD × Documentation (priority 0.00)

- **Capability label:** CI/CD and Deployment Automation
- **Evidence count:** 2 (P25 = 2.0)
- **Bucket:** organizational_readiness_barrier
- **Rationale (from `decision_register.csv`):** organizational_readiness_barrier: Evidence for mature capability CAP_CICD at Documentation is below the P25 non-zero threshold, suggesting organizational or process friction rather than a technical shortfall.

### Rank 27 — CAP_CICD × Project Management (priority 0.00)

- **Capability label:** CI/CD and Deployment Automation
- **Evidence count:** 2 (P25 = 2.0)
- **Bucket:** organizational_readiness_barrier
- **Rationale (from `decision_register.csv`):** organizational_readiness_barrier: Evidence for mature capability CAP_CICD at Project Management is below the P25 non-zero threshold, suggesting organizational or process friction rather than a technical shortfall.

### Rank 28 — CAP_CODEREVIEW × Project Management (priority 0.00)

- **Capability label:** Automated Code Review
- **Evidence count:** 2 (P25 = 2.0)
- **Bucket:** organizational_readiness_barrier
- **Rationale (from `decision_register.csv`):** organizational_readiness_barrier: Evidence for mature capability CAP_CODEREVIEW at Project Management is below the P25 non-zero threshold, suggesting organizational or process friction rather than a technical shortfall.

### Rank 29 — CAP_CODESUM × Code Review (priority 0.00)

- **Capability label:** Code Summarisation
- **Evidence count:** 2 (P25 = 2.0)
- **Bucket:** organizational_readiness_barrier
- **Rationale (from `decision_register.csv`):** organizational_readiness_barrier: Evidence for mature capability CAP_CODESUM at Code Review is below the P25 non-zero threshold, suggesting organizational or process friction rather than a technical shortfall.

### Rank 30 — CAP_CODESUM × Design (priority 0.00)

- **Capability label:** Code Summarisation
- **Evidence count:** 2 (P25 = 2.0)
- **Bucket:** design_gap
- **Rationale (from `decision_register.csv`):** design_gap: Evidence for CAP_CODESUM at the Design activity is below the P25 non-zero threshold, indicating an under-researched early-lifecycle intersection that warrants ERP3 investigation.

### Rank 31 — CAP_CODETRANS × Design (priority 0.00)

- **Capability label:** Code Translation
- **Evidence count:** 2 (P25 = 2.0)
- **Bucket:** design_gap
- **Rationale (from `decision_register.csv`):** design_gap: Evidence for CAP_CODETRANS at the Design activity is below the P25 non-zero threshold, indicating an under-researched early-lifecycle intersection that warrants ERP3 investigation.

### Rank 32 — CAP_CODETRANS × Testing (priority 0.00)

- **Capability label:** Code Translation
- **Evidence count:** 2 (P25 = 2.0)
- **Bucket:** organizational_readiness_barrier
- **Rationale (from `decision_register.csv`):** organizational_readiness_barrier: Evidence for mature capability CAP_CODETRANS at Testing is below the P25 non-zero threshold, suggesting organizational or process friction rather than a technical shortfall.

### Rank 33 — CAP_COMMITMSG × Coding (priority 0.00)

- **Capability label:** Commit Message Generation
- **Evidence count:** 2 (P25 = 2.0)
- **Bucket:** organizational_readiness_barrier
- **Rationale (from `decision_register.csv`):** organizational_readiness_barrier: Evidence for mature capability CAP_COMMITMSG at Coding is below the P25 non-zero threshold, suggesting organizational or process friction rather than a technical shortfall.

### Rank 34 — CAP_COMMITMSG × Documentation (priority 0.00)

- **Capability label:** Commit Message Generation
- **Evidence count:** 2 (P25 = 2.0)
- **Bucket:** organizational_readiness_barrier
- **Rationale (from `decision_register.csv`):** organizational_readiness_barrier: Evidence for mature capability CAP_COMMITMSG at Documentation is below the P25 non-zero threshold, suggesting organizational or process friction rather than a technical shortfall.

### Rank 35 — CAP_MULTIAGENT × Documentation (priority 0.00)

- **Capability label:** Multi-Agent Collaboration
- **Evidence count:** 2 (P25 = 2.0)
- **Bucket:** adoption_lag
- **Rationale (from `decision_register.csv`):** adoption_lag: Evidence for the autonomy-leaning capability CAP_MULTIAGENT at Documentation is below the P25 non-zero threshold, consistent with known lag between research-frontier capabilities and practical SDLC adoption.

### Rank 36 — CAP_PROGREPAIR × Design (priority 0.00)

- **Capability label:** Program Repair / Bug Fixing
- **Evidence count:** 2 (P25 = 2.0)
- **Bucket:** design_gap
- **Rationale (from `decision_register.csv`):** design_gap: Evidence for CAP_PROGREPAIR at the Design activity is below the P25 non-zero threshold, indicating an under-researched early-lifecycle intersection that warrants ERP3 investigation.

### Rank 37 — CAP_PROGREPAIR × Requirements (priority 0.00)

- **Capability label:** Program Repair / Bug Fixing
- **Evidence count:** 2 (P25 = 2.0)
- **Bucket:** design_gap
- **Rationale (from `decision_register.csv`):** design_gap: Evidence for CAP_PROGREPAIR at the Requirements activity is below the P25 non-zero threshold, indicating an under-researched early-lifecycle intersection that warrants ERP3 investigation.

### Rank 38 — CAP_REQENG × CI/CD (priority 0.00)

- **Capability label:** Requirements Engineering
- **Evidence count:** 2 (P25 = 2.0)
- **Bucket:** design_gap
- **Rationale (from `decision_register.csv`):** design_gap: Evidence for CAP_REQENG at the CI/CD activity is below the P25 non-zero threshold, indicating an under-researched early-lifecycle intersection that warrants ERP3 investigation.

### Rank 39 — CAP_REQENG × Code Review (priority 0.00)

- **Capability label:** Requirements Engineering
- **Evidence count:** 2 (P25 = 2.0)
- **Bucket:** design_gap
- **Rationale (from `decision_register.csv`):** design_gap: Evidence for CAP_REQENG at the Code Review activity is below the P25 non-zero threshold, indicating an under-researched early-lifecycle intersection that warrants ERP3 investigation.

### Rank 40 — CAP_SELFREFLECT × Design (priority 0.00)

- **Capability label:** Self-Reflection and Iterative Refinement
- **Evidence count:** 2 (P25 = 2.0)
- **Bucket:** design_gap
- **Rationale (from `decision_register.csv`):** design_gap: Evidence for CAP_SELFREFLECT at the Design activity is below the P25 non-zero threshold, indicating an under-researched early-lifecycle intersection that warrants ERP3 investigation.

### Rank 41 — CAP_SYSDESIGN × Project Management (priority 0.00)

- **Capability label:** System Design and Architecture
- **Evidence count:** 2 (P25 = 2.0)
- **Bucket:** design_gap
- **Rationale (from `decision_register.csv`):** design_gap: Evidence for CAP_SYSDESIGN at the Project Management activity is below the P25 non-zero threshold, indicating an under-researched early-lifecycle intersection that warrants ERP3 investigation.

### Rank 42 — CAP_VULNDET × Documentation (priority 0.00)

- **Capability label:** Vulnerability Detection
- **Evidence count:** 2 (P25 = 2.0)
- **Bucket:** organizational_readiness_barrier
- **Rationale (from `decision_register.csv`):** organizational_readiness_barrier: Evidence for mature capability CAP_VULNDET at Documentation is below the P25 non-zero threshold, suggesting organizational or process friction rather than a technical shortfall.

## Bucket tally

| Bucket | Count | % of total |
|---|---:|---:|
| adoption_lag | 6 | 14.3% |
| design_gap | 14 | 33.3% |
| organizational_readiness_barrier | 22 | 52.4% |
| **Total** | **42** | **100.0%** |

## Invariants verified

- Gap rows in ranked table: **42** (expected 42).
- Every gap has a matching Phase-5 `hypothesis_for_erp3` decision-register entry.
- No interpretation-label columns from the matrix leaked in (matrix columns remain `{capability_id, sdlc_activity, evidence_count, is_gap, is_empty, in_source_survey}`).
- Sort order: `priority desc`, tie-break `capability_id asc, sdlc_activity asc`.

