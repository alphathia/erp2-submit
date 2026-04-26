# Interaction-Mode Taxonomy — RQ2 Deliverable

> **Status:** ✅ v1.1 — **finalized** at Phase 4 closeout 2026-04-20. Operational definitions + distinguishing criteria + ≥2 paraphrased exemplars per mode; paraphrase-linter clean; mode-layer saturation verdict **Saturated**.
> **Source:** `artifacts/synthesis/taxonomy_classifications.csv` (707 canonical labels, Step-4 partition 19 Apr 2026).
> **Rater:** TBS
> **Generated:** 2026-04-19 via `code/taxonomy_render.py`; header finalized 2026-04-20.
> **Corpus:** 290 papers with ≥1 raw passage (of 640 extracted; 350 Mode-B abstract-only papers excluded from coding denominator).
> **Saturation:** canonical-layer `saturation_report.md` (intermediate; not reportable). **Mode-layer `saturation_report_mode.md` — Saturated (0 new modes in final 29 papers) — is the reportable §6.3 dependability claim.**
> **Closeout record:** `artifacts/synthesis/task4_academic_closeout_report.md`.

---

## Axis — Delegation Depth

Modes are ordered along a single ordinal axis: **the degree to which the human delegates the software-engineering task to the AI agent.** The axis runs from the human producing the work with AI providing continuations (Mode 1), through turn-taking collaboration (Modes 2–3), evaluative review (Mode 4), to the AI executing multi-step work with the human reviewing at checkpoints or at end (Mode 5).

The axis is pre-committed from proposal §3.5 and Appendix C; the mode partition *on* the axis is inductive from the data. Starting frame derived at Step 2 of `task4_2_todo.md` collapses the proposal's 8 provisional modes to 5 based on top-40 cluster evidence:

- **Kept:** Inline Completion, Conversational Prompting, Visual/Declarative Composition, Review & Validation.
- **Folded:** Paired Collaboration → Conversational Prompting. Scaffolded Guidance dissolves across Conversational + Delegated. HITL Delegation + Autonomous Orchestration → Delegated Task Execution (distinction may re-emerge at Step 4).

See `task4_2_todo.md §1` for the full collapsing rationale and re-open triggers.

---

---

## Partition summary

| Mode | Name | Labels | % of 707 |
|---|---|---:|---:|
| 1 | Inline Completion | 4 | 0.6% |
| 2 | Conversational Prompting | 69 | 9.8% |
| 3 | Visual / Declarative Composition | 9 | 1.3% |
| 4 | Review & Validation | 82 | 11.6% |
| 5 | Delegated Task Execution | 75 | 10.6% |
| r | Residuals / Cross-cutting | 468 | 66.2% |
| **Total** | | **707** | **100.0%** |

---

## Mode 1 — Inline Completion

**Operational definition:** The human authors code in-flow; the AI produces short suggested continuations (tokens to a few lines) that the human accepts, modifies, or rejects immediately. The unit of interaction is the single accept/reject decision; no turn-based dialogue is required.

**Distinguishing criteria:**
- IS: continuation is inline within the editor, accepted/rejected without a separate conversational turn; the AI never takes multi-step initiative.
- IS NOT: iterative prompt refinement (that is Mode 2) or any case where the AI executes a task without an immediate token-level accept/reject moment (that is Mode 5).

**Canonical labels grouped under this mode (4 labels, 5 member pass-1 codes):**

| # | Canonical label | Size | Source | Notes |
|---:|---|---:|---|---|
| 1 | Activating Predictive Text Suggestions | 2 | step3 | — |
| 2 | Inline Code Completion | 1 | step4_llmassist | — |
| 3 | Just-In-Time Recommendation | 1 | step4_llmassist | — |
| 4 | Short Artifact Interactions | 1 | step4_llmassist | — |

**Exemplars (paraphrased):**

1. A controlled study of twenty-four programmers compared three task conditions: an inline Copilot surface that proposed per-line continuations, a chat-style GPT-3 workflow, and a baseline with no AI. The inline accept-or-reject surface typifies Mode 1 — the human writes and the AI suggests short continuations at the cursor.
   — trace: `doi:10.1145/3661145:P001`

2. Developers routinely invoked Copilot's autocomplete, letting the assistant finish the current line as typing progressed. Acceptance or rejection happens without opening a chat turn; the unit of interaction is a single inline proposal.
   — trace: `doi:10.24251/hicss.2025.883:P001`

---

## Mode 2 — Conversational Prompting

**Operational definition:** The human describes intent or asks a question in natural language; the AI produces a multi-line response; the human reads, evaluates, and iterates — typically over multiple turns — until the output is usable. The unit of interaction is the turn; the delegation scope is bounded by a single prompt-response cycle, but multiple cycles compose into a session.

**Distinguishing criteria:**
- IS: turn-based exchange via chat or comparable conversational surface; human re-prompts to refine; scope of any single AI action is bounded by the most recent prompt.
- IS NOT: inline accept/reject without a separate turn (Mode 1); visual/declarative surface rather than free text (Mode 3); multi-step task execution without intermediate human steering (Mode 5).

**Canonical labels grouped under this mode (69 labels, 116 member pass-1 codes):**

| # | Canonical label | Size | Source | Notes |
|---:|---|---:|---|---|
| 1 | Iterative Prompting Refinement | 16 | step3 | — |
| 2 | Automated Contextual Prompt Augmentation | 4 | step3 | — |
| 3 | Iterative Troubleshooting Methodologies | 4 | step3 | — |
| 4 | Collaborative AI Programming Workflow | 3 | step3 | — |
| 5 | Conversational Interaction Modality | 3 | step3 | — |
| 6 | Task Complexity Drives Iteration | 3 | step4_llmassist | — |
| 7 | AI Assisted Code Comprehension | 2 | step4_llmassist | — |
| 8 | Automated Prompt Output Synthesis | 2 | step4_llmassist | — |
| 9 | Context-Aware Code Processing | 2 | step4_llmassist | — |
| 10 | Creative Concept Exploration | 2 | step4_llmassist | — |
| 11 | Dynamic Test Specification Probing | 2 | step4_llmassist | — |
| 12 | Facilitating Preliminary Schematic Ideation | 2 | step4_llmassist | — |
| 13 | Interactive Contextual Debugging | 2 | step4_llmassist | — |
| 14 | Iterative AI Code Troubleshooting | 2 | step4_llmassist | — |
| 15 | Iterative Dialogue Steering | 2 | step4_llmassist | — |
| 16 | Iterative Execution Feedback Loop | 2 | step4_llmassist | — |
| 17 | Iterative Prompting Techniques | 2 | step4_llmassist | — |
| 18 | Knowledge Formalization Dynamics | 2 | step4_llmassist | overrode LLM r -> 2 |
| 19 | Linguistic Intent Articulation | 2 | step4_llmassist | — |
| 20 | Natural Language Data Entry | 2 | step4_llmassist | — |
| 21 | Recursive Inquiry Optimization | 2 | step4_llmassist | — |
| 22 | Standardized Prompting Frameworks | 2 | step4_llmassist | — |
| 23 | Structural Framework Formulation | 2 | step4_llmassist | — |
| 24 | Structural Framework Ideation | 2 | step4_llmassist | — |
| 25 | Structured Sequential Prompting | 2 | step4_llmassist | — |
| 26 | Sustained Dialogue Proficiency | 2 | step4_llmassist | — |
| 27 | Accessible Conversational Ui | 1 | step4_llmassist | — |
| 28 | Agent Affirmation | 1 | step4_llmassist | — |
| 29 | Agent Apology | 1 | step4_llmassist | — |
| 30 | Analyzing Tool-Triggered Conversations | 1 | step4_llmassist | — |
| 31 | Bot-Supported Brainstorming | 1 | step4_llmassist | — |
| 32 | Chat-Based Query | 1 | step4_llmassist | — |
| 33 | Chatbots As Learning Supplement | 1 | step4_llmassist | — |
| 34 | Collegial Interaction | 1 | step4_llmassist | — |
| 35 | Concept Simplification | 1 | step4_llmassist | — |
| 36 | Configuration Context Prompting | 1 | step4_llmassist | — |
| 37 | Constraints For Refinement | 1 | step4_llmassist | — |
| 38 | Conversational Behavior Taxonomy | 1 | step4_llmassist | — |
| 39 | Conversational Disambiguation | 1 | step4_llmassist | — |
| 40 | Conversational Problem Solving | 1 | step4_llmassist | — |
| 41 | Direct Solution Prompting | 1 | step4_llmassist | — |
| 42 | Dynamic Content Reformulation | 1 | step4_llmassist | — |
| 43 | Educational Content Generation | 1 | step4_llmassist | overrode LLM 5 -> 2 |
| 44 | Error Fixing Queries | 1 | step4_llmassist | — |
| 45 | Error Logging And Search | 1 | step4_llmassist | overrode LLM r -> 2 |
| 46 | Ethical And Security Challenges | 1 | step4_llmassist | overrode LLM r -> 2 |
| 47 | Exacerbates Incorrect Beliefs | 1 | step4_llmassist | overrode LLM r -> 2 |
| 48 | Feedback-Driven Optimization | 1 | step4_llmassist | — |
| 49 | Interactive Experimentation | 1 | step4_llmassist | — |
| 50 | Knowledge Probing Via Inference | 1 | step4_llmassist | — |
| 51 | Multi-Agent Chat Assistant | 1 | step4_llmassist | — |
| 52 | Multi-Turn Dialog Fixing | 1 | step4_llmassist | — |
| 53 | Nl For Complex Constraints | 1 | step4_llmassist | — |
| 54 | One-Shot Prompt Superiority | 1 | step4_llmassist | — |
| 55 | Profile Update Via Cot | 1 | step4_llmassist | — |
| 56 | Prompt Engineering For Security | 1 | step4_llmassist | — |
| 57 | Prompt Reuse Strategy | 1 | step4_llmassist | — |
| 58 | Prompt-Engineered Seed Generation | 1 | step4_llmassist | — |
| 59 | Prompting Via Test Examples | 1 | step4_llmassist | — |
| 60 | Providing Feedforward Cues | 1 | step4_llmassist | — |
| 61 | Repetitive Generic Questions | 1 | step4_llmassist | — |
| 62 | Separating Task From Format | 1 | step4_llmassist | — |
| 63 | Simulating Diverse Personas | 1 | step4_llmassist | — |
| 64 | Stack Trace Debugging | 1 | step4_llmassist | — |
| 65 | Structured Metacognitive Reasoning | 1 | step4_llmassist | — |
| 66 | Targeted Explanation Generation | 1 | step4_llmassist | — |
| 67 | Taxonomy-Guided Prompting | 1 | step4_llmassist | — |
| 68 | Textbook Question Answering | 1 | step4_llmassist | — |
| 69 | Zero-Shot Prompting | 1 | step4_llmassist | — |

**Exemplars (paraphrased):**

1. Participants described their dominant strategy as authoring natural-language prompts — often embedded as in-file comments — to articulate the desired code behaviour. Each prompt-response cycle forms one conversational turn, with refinement continuing across turns until the output matched intent.
   — trace: `doi:10.1145/3597503.3608128:P003`

2. A typical debugging turn has the developer paste a code fragment into ChatGPT, append the observed exception, and ask for a diagnosis plus fix. The dialogue continues across several turns if the first response is incomplete or misidentifies the cause.
   — trace: `doi:10.1145/3643991.3645074:P005`

---

## Mode 3 — Visual / Declarative Composition

**Operational definition:** The human composes software by arranging visual, structural, or declarative elements (drag-and-drop blocks, flow-chart nodes, configuration forms, natural-language-to-workflow pipelines); the AI generates the underlying implementation (logic, data models, or workflow steps) from the declarative specification. The unit of interaction is the declarative specification, not a free-text prompt.

**Distinguishing criteria:**
- IS: visual/declarative surface where the human's input is structural rather than natural-language; low-code / no-code / visual-AI-platform evidence.
- IS NOT: free-text prompt-and-response (Mode 2); code-editor inline completion (Mode 1).

**Canonical labels grouped under this mode (9 labels, 12 member pass-1 codes):**

| # | Canonical label | Size | Source | Notes |
|---:|---|---:|---|---|
| 1 | Prompt-Centric Visual Interaction | 4 | step3 | — |
| 2 | Configuration Adjustment | 1 | step4_llmassist | — |
| 3 | Diagramming For Comprehension | 1 | step4_llmassist | overrode LLM 4 -> 3 |
| 4 | Scratchpad Reasoning Tracking | 1 | step4_llmassist | overrode LLM r -> 3 |
| 5 | Step-Wise Script Execution | 1 | step4_llmassist | overrode LLM 5 -> 3 |
| 6 | Visual Chain Authoring | 1 | step4_llmassist | — |
| 7 | Visual Parsing Complexity | 1 | step4_llmassist | overrode LLM r -> 3 |
| 8 | Visual Test Generation | 1 | step4_llmassist | — |
| 9 | Visual Workflow Development | 1 | step4_llmassist | — |

**Rater note for Step 6:** member code "Visual and chat interaction" (sits under Mode 2's canonical label "Conversational Interaction Modality") is also relevant here — inspect at passage level in Step 6 and decide whether to use its passage(s) as a cross-reference exemplar for Mode 3.

**Exemplars (paraphrased):**

1. PromptAid surfaces prompt composition through a visual analytics interface — the user manipulates structural elements (exploration panels, perturbation widgets, test harnesses) rather than authoring free-text chat turns. The prompt is constructed declaratively; the system generates underlying execution from the visual specification.
   — trace: `doi:10.1109/tvcg.2025.3535332:P001`

2. Structural diagrams — visualised code trees and logic flows — let practitioners compose understanding declaratively rather than through free-text prose. The diagram is the surface of interaction; the AI produces the underlying explanation from the visual specification.
   — trace: `doi:10.7763/ijcte.2025.v17.1378:P003`

---

## Mode 4 — Review & Validation

**Operational definition:** The AI or the human performs an evaluative reading of code or AI output — detecting hallucinations, assessing quality, localising defects, providing or soliciting feedback. The unit of interaction is the evaluative judgement; the delegation axis reads this mode as "AI-as-subject-of-review" or "AI-as-review-provider" depending on direction.

**Distinguishing criteria:**
- IS: explicit evaluation of code or AI output for correctness / quality / trustworthiness; includes both directions (human reviews AI, AI reviews human).
- IS NOT: generation of new code (Modes 1/2/5); refinement of a prompt where evaluation is internal to a turn (Mode 2).

**Canonical labels grouped under this mode (82 labels, 136 member pass-1 codes):**

| # | Canonical label | Size | Source | Notes |
|---:|---|---:|---|---|
| 1 | Hallucination and Miscalibration Detection | 10 | step3 | — |
| 2 | Comparative Code Quality Assessment | 4 | step3 | — |
| 3 | Review Speed Quality Tradeoffs | 4 | step3 | — |
| 4 | Syntactic Accuracy Assurance | 4 | step3 | — |
| 5 | Automated Multidimensional Feedback Generation | 3 | step3 | — |
| 6 | Automation Trust and Security | 3 | step3 | — |
| 7 | Curbing AI over-reliance | 3 | step3 | — |
| 8 | Managing Model Output Veracity | 3 | step4_llmassist | — |
| 9 | Aligning User Trust Levels | 2 | step4_llmassist | — |
| 10 | Architectural Openness Expectations | 2 | step4_llmassist | overrode LLM r -> 4 |
| 11 | Assessing LLM Efficacy | 2 | step4_llmassist | — |
| 12 | Automated Data Integrity Assurance | 2 | step4_llmassist | — |
| 13 | Automated Pre-Submission Evaluation | 2 | step4_llmassist | — |
| 14 | Automated Static Program Evaluation | 2 | step4_llmassist | — |
| 15 | Comparative Evaluation Strategies | 2 | step4_llmassist | — |
| 16 | Cursory Academic Peer Evaluation | 2 | step4_llmassist | — |
| 17 | Defect Identification Effectiveness | 2 | step4_llmassist | — |
| 18 | Deficient Output Dependability Scrutiny | 2 | step4_llmassist | — |
| 19 | Enhanced Runtime Fault Discovery | 2 | step4_llmassist | — |
| 20 | Eroding Security Vigilance | 2 | step4_llmassist | — |
| 21 | Evaluating Realistic Change Integrity | 2 | step4_llmassist | — |
| 22 | Failure Detection and Classification | 2 | step4_llmassist | — |
| 23 | Human Assessment Criteria | 2 | step4_llmassist | — |
| 24 | Machine Generated Software Critique | 2 | step4_llmassist | — |
| 25 | Personalized Relevance Assessment | 2 | step4_llmassist | — |
| 26 | Precise Fault Localization | 2 | step4_llmassist | — |
| 27 | Requirement-Test Validation | 2 | step4_llmassist | — |
| 28 | Review Centric Workflow | 2 | step4_llmassist | — |
| 29 | Self-verification Reliability | 2 | step4_llmassist | — |
| 30 | Specialist Manual Review | 2 | step4_llmassist | — |
| 31 | Superficial Verification of Errors | 2 | step4_llmassist | — |
| 32 | Uncovering Unanticipated Boundary Scenarios | 2 | step4_llmassist | — |
| 33 | Uncritical Trust and Miscomprehension | 2 | step4_llmassist | — |
| 34 | Validation Driven Software Optimization | 2 | step4_llmassist | — |
| 35 | Verifying AI Conceptual Insights | 2 | step4_llmassist | — |
| 36 | Visual Sequential Code Tracing | 2 | step4_llmassist | — |
| 37 | Alert Fatigue And Trust | 1 | step4_llmassist | — |
| 38 | Api Vulnerability Detection | 1 | step4_llmassist | — |
| 39 | Automated Reflection Prompting | 1 | step4_llmassist | — |
| 40 | Autonomous Inspection | 1 | step4_llmassist | — |
| 41 | Black-Box Llm Distrust | 1 | step4_llmassist | — |
| 42 | Blind Acceptance Of Vulnerabilities | 1 | step4_llmassist | — |
| 43 | Cherry-Picking Solutions | 1 | step4_llmassist | — |
| 44 | Ci/Cd Code Review | 1 | step4_llmassist | — |
| 45 | Completeness And Standards Alignment | 1 | step4_llmassist | — |
| 46 | Comprehensive Security Explanations | 1 | step4_llmassist | — |
| 47 | Developer Reception To Ai Code | 1 | step4_llmassist | — |
| 48 | Discovers Novel Issues | 1 | step4_llmassist | — |
| 49 | Evaluating Model Responses | 1 | step4_llmassist | — |
| 50 | Expert Qualitative Assessment | 1 | step4_llmassist | — |
| 51 | False Security Confidence | 1 | step4_llmassist | — |
| 52 | Fear Of Over-Reliance | 1 | step4_llmassist | — |
| 53 | Human Judgment Override | 1 | step4_llmassist | — |
| 54 | Hybrid Assessment Approach | 1 | step4_llmassist | — |
| 55 | Hybrid Llm-Heuristic Localization | 1 | step4_llmassist | — |
| 56 | Inappropriate Ai Trust | 1 | step4_llmassist | — |
| 57 | Invalid Bug Filtering | 1 | step4_llmassist | — |
| 58 | Issue-Specific Review Challenges | 1 | step4_llmassist | — |
| 59 | Llm Personal Validation | 1 | step4_llmassist | — |
| 60 | Llm Reasoning On Warnings | 1 | step4_llmassist | — |
| 61 | Mandatory Human Verification | 1 | step4_llmassist | — |
| 62 | Modification Before Merging | 1 | step4_llmassist | — |
| 63 | Need For Developer Review | 1 | step4_llmassist | — |
| 64 | Need For Manual Verification | 1 | step4_llmassist | — |
| 65 | Noisy Human Feedback | 1 | step4_llmassist | — |
| 66 | Over-Trust And Absent Verification | 1 | step4_llmassist | — |
| 67 | Overreliance And Copy-Pasting | 1 | step4_llmassist | — |
| 68 | Overreliance On Ai Tools | 1 | step4_llmassist | — |
| 69 | Patch Review Task | 1 | step4_llmassist | — |
| 70 | Plan Validation And Confirmation | 1 | step4_llmassist | — |
| 71 | Poor Confidence Calibration | 1 | step4_llmassist | — |
| 72 | Post-Interaction Evaluation | 1 | step4_llmassist | — |
| 73 | Preliminary Automated Review | 1 | step4_llmassist | — |
| 74 | Review And Edit | 1 | step4_llmassist | — |
| 75 | Runtime Validation Requirement | 1 | step4_llmassist | — |
| 76 | Scalable Automated Evaluation | 1 | step4_llmassist | — |
| 77 | Static Non-Interactive Feedback | 1 | step4_llmassist | — |
| 78 | Unchecked Generated Code | 1 | step4_llmassist | — |
| 79 | User Behavior With False Predictions | 1 | step4_llmassist | — |
| 80 | User Ranking Of Ai Outputs | 1 | step4_llmassist | — |
| 81 | Verification Difficulty For Novices | 1 | step4_llmassist | — |
| 82 | Verifying Correctness | 1 | step4_llmassist | — |

**Exemplars (paraphrased):**

1. Evaluators sorted LLM-generated unit tests into three defect families — unresolved symbols, parameter mismatches, and abstract-class instantiations — each traceable to hallucination. The work product is evaluative: reading the AI's output, naming its failure modes, and attributing cause.
   — trace: `doi:10.1145/3691620.3695529:P004`

2. Reviewers applied an explicit four-axis rubric to AI-produced code: artefact quality, solution correctness, turnaround speed, and side-by-side comparison with human baselines. The interaction unit is the evaluative judgement, not the generation step.
   — trace: `doi:10.1109/c358072.2023.10436306:P002`

---

## Mode 5 — Delegated Task Execution

**Operational definition:** The human scopes a software-engineering task (generate tests, fix a bug, refactor a module, build a workflow); the AI executes the task end-to-end or across multiple sub-steps; the human reviews at checkpoints or at completion. The unit of interaction is the *task*, not the prompt or the suggestion. This mode folds in the proposal's HITL Delegation and Autonomous Orchestration; they may split again if Step 4 surfaces clean evidence of the distinction.

**Distinguishing criteria:**
- IS: AI takes multi-step initiative — generates a test suite, walks a debugging session, orchestrates an agentic workflow; human steers at boundaries, not per-token.
- IS NOT: single-turn prompt-response (Mode 2); token-level suggestion (Mode 1).

**Canonical labels grouped under this mode (75 labels, 148 member pass-1 codes):**

| # | Canonical label | Size | Source | Notes |
|---:|---|---:|---|---|
| 1 | Automated Test Suite Synthesis | 14 | step3 | — |
| 2 | Automated Defect Lifecycle Management | 7 | step3 | — |
| 3 | LLM Driven Test Synthesis | 5 | step3 | — |
| 4 | Proficient Code Synthesis | 5 | step3 | — |
| 5 | Automated Test Script Engineering | 4 | step3 | — |
| 6 | Contextual Code Synthesis Efficacy | 4 | step3 | — |
| 7 | Optimizing Defect Correction Processes | 4 | step3 | — |
| 8 | Automated Artifact Engineering | 3 | step3 | — |
| 9 | Automated Software Synthesis Tasks | 3 | step3 | — |
| 10 | Automated Test Oracle Synthesis | 3 | step3 | — |
| 11 | Automating Defect Reproduction Workflows | 3 | step3 | — |
| 12 | Automating Repetitive Workflows | 3 | step3 | — |
| 13 | Diverse Software Polishing Methods | 3 | step3 | — |
| 14 | Enhanced Defect Pinpointing | 3 | step3 | — |
| 15 | AI Mediated Code Refactoring | 2 | step4_llmassist | — |
| 16 | Accelerated Independent Execution | 2 | step4_llmassist | — |
| 17 | Anthropomorphic Navigation Failures | 2 | step4_llmassist | — |
| 18 | Automated Analytical Programming | 2 | step4_llmassist | — |
| 19 | Automated Design Logic | 2 | step4_llmassist | — |
| 20 | Automated Log Interpretation | 2 | step4_llmassist | — |
| 21 | Automated Software Asset Synthesis | 2 | step4_llmassist | — |
| 22 | Automated Technical Asset Synthesis | 2 | step4_llmassist | — |
| 23 | Automated UML Design Synthesis | 2 | step4_llmassist | — |
| 24 | Autonomous Compilation Error Resolution | 2 | step4_llmassist | — |
| 25 | Collective Multi-Agent Orchestration | 2 | step4_llmassist | — |
| 26 | Coordinated Agent Frameworks | 2 | step4_llmassist | — |
| 27 | End-to-End Software Synthesis | 2 | step4_llmassist | — |
| 28 | Inequitable Role Distribution | 2 | step4_llmassist | — |
| 29 | LLM Driven Code Repair | 2 | step4_llmassist | — |
| 30 | Multilingual Syntax Transformation | 2 | step4_llmassist | — |
| 31 | Recursive Accuracy Refinement | 2 | step4_llmassist | — |
| 32 | Software Defect Remediation | 2 | step4_llmassist | — |
| 33 | Strategic Workflow Partitioning | 2 | step4_llmassist | — |
| 34 | Streamlining Test Suite Execution | 2 | step4_llmassist | — |
| 35 | Structured Test Design Assistance | 2 | step4_llmassist | — |
| 36 | Synthetic Data Creation | 2 | step4_llmassist | — |
| 37 | Urgent Full Task Offloading | 2 | step4_llmassist | — |
| 38 | Agent Configuration And Deployment | 1 | step4_llmassist | — |
| 39 | Ai Defect Repair | 1 | step4_llmassist | — |
| 40 | Ai For Vulnerability Remediation | 1 | step4_llmassist | — |
| 41 | Automated Alert Summarisation | 1 | step4_llmassist | — |
| 42 | Automated Clump Refactoring | 1 | step4_llmassist | — |
| 43 | Automated Data Structuring | 1 | step4_llmassist | — |
| 44 | Automated Inclusivity Testing | 1 | step4_llmassist | — |
| 45 | Automated Infrastructure Deployment | 1 | step4_llmassist | — |
| 46 | Automated Pr Creation | 1 | step4_llmassist | — |
| 47 | Automated Process Analysis | 1 | step4_llmassist | — |
| 48 | Automated Variable Extraction | 1 | step4_llmassist | — |
| 49 | Autonomous Exploration | 1 | step4_llmassist | — |
| 50 | Autonomous Llm Tool Execution | 1 | step4_llmassist | — |
| 51 | Autonomous Script Repair | 1 | step4_llmassist | — |
| 52 | Autonomous Task Execution | 1 | step4_llmassist | — |
| 53 | Commit Message Generation | 1 | step4_llmassist | — |
| 54 | Complete Diff Recommendation | 1 | step4_llmassist | — |
| 55 | Context-Injected Orchestration | 1 | step4_llmassist | — |
| 56 | Custom Tailored Llm Agent | 1 | step4_llmassist | — |
| 57 | Dashboard Widget Generation | 1 | step4_llmassist | — |
| 58 | Database Schema Generation | 1 | step4_llmassist | — |
| 59 | Debugging Plan Generation | 1 | step4_llmassist | — |
| 60 | Delegating Tedious Tasks | 1 | step4_llmassist | — |
| 61 | Handling Flakiness | 1 | step4_llmassist | — |
| 62 | Impact Analysis Workflow | 1 | step4_llmassist | — |
| 63 | Multi-Agent Rule Refinement | 1 | step4_llmassist | — |
| 64 | Opaque Automated Resolution | 1 | step4_llmassist | — |
| 65 | Pr Summarization Generation | 1 | step4_llmassist | — |
| 66 | Quantum Circuit Generation | 1 | step4_llmassist | — |
| 67 | Requirement Reverse Engineering | 1 | step4_llmassist | — |
| 68 | Requirements Text Analysis | 1 | step4_llmassist | — |
| 69 | Self-Healing Test Scripts | 1 | step4_llmassist | — |
| 70 | Slice-Level Testing | 1 | step4_llmassist | — |
| 71 | Task Decomposition To Spec | 1 | step4_llmassist | — |
| 72 | Task Outsourcing | 1 | step4_llmassist | — |
| 73 | Team Formation Simulation | 1 | step4_llmassist | — |
| 74 | User Specifies Test Output | 1 | step4_llmassist | — |
| 75 | Zero-Touch Code Generation | 1 | step4_llmassist | — |

**Exemplars (paraphrased):**

1. Botender delegates chatbot testing end-to-end: the system synthesises provocative interaction scenarios, drives them through the bot under test, and surfaces outcomes for human review at task completion rather than per-prompt. The human scopes the task; the tool executes it.
   — trace: `doi:10.1145/3772318.3790500:P001`

2. A multi-agent framework accepts plain-English bug reports from end users, then autonomously enriches each report, attempts reproduction, and solicits clarification only when the evidence is insufficient. The human scopes the problem once; the agents execute the triage workflow across multiple sub-steps.
   — trace: `doi:10.1145/3806655:P001`

---

## Residuals / Cross-Cutting Evidence

These canonical labels describe **outcomes, affordances, or constraints that cut across modes** — not interaction modes themselves. Per Step-2 decision in `task4_2_todo.md §3`, each will be re-placed at Step 4 under the mode its underlying passages describe, *or* retained here if the passages span multiple modes.

**Total: 468 canonical labels** across 4 sub-categories (LLM-sub-classified, rater-adjudicated at Step 4 level).

### Outcome (192 labels)

| # | Canonical label | Size | Source | Notes |
|---:|---|---:|---|---|
| 1 | Varied Productivity Outcomes | 5 | step3 | — |
| 2 | Accelerated Engineering Velocity | 4 | step3 | — |
| 3 | Differential Cognitive Performance Outcomes | 4 | step3 | — |
| 4 | Enhanced Operational Productivity | 4 | step3 | — |
| 5 | Impact On Accuracy Outcomes | 4 | step3 | — |
| 6 | Positive User Sentiment | 4 | step3 | — |
| 7 | Defect Resolution Efficacy | 3 | step3 | — |
| 8 | Evaluating LLM Advisory Efficacy | 3 | step4_llmassist | — |
| 9 | Explanatory Troubleshooting Efficacy | 3 | step4_llmassist | — |
| 10 | Minimizing Context Switching Costs | 3 | step4_llmassist | — |
| 11 | Security Flaw Recognition Efficacy | 3 | step4_llmassist | — |
| 12 | Accelerated Operational Speed | 2 | step4_llmassist | — |
| 13 | Accelerated Task Execution | 2 | step4_llmassist | — |
| 14 | Chatgpt Superiority | 2 | step4_llmassist | — |
| 15 | Complexity Driven Accuracy Loss | 2 | step4_llmassist | — |
| 16 | Comprehensive Requirement Specification | 2 | step4_llmassist | — |
| 17 | Demonstrated Competency Advancement | 2 | step4_llmassist | — |
| 18 | Detection Performance Levels | 2 | step4_llmassist | — |
| 19 | Diminished AI Code Reliability | 2 | step4_llmassist | — |
| 20 | Effective Targeted Structural Restructuring | 2 | step4_llmassist | — |
| 21 | Enhanced Performance Outcomes | 2 | step4_llmassist | — |
| 22 | Enhanced Programming Velocity | 2 | step4_llmassist | — |
| 23 | Equivalent Code Comprehensibility Perception | 2 | step4_llmassist | — |
| 24 | Eroded Human Accountability | 2 | step4_llmassist | — |
| 25 | Escalated Review Effort | 2 | step4_llmassist | — |
| 26 | Expanded Verification Scope | 2 | step4_llmassist | — |
| 27 | Expediting Routine Syntax Construction | 2 | step4_llmassist | — |
| 28 | Facilitators Of Conceptual Clarity | 2 | step4_llmassist | — |
| 29 | Favorable User Reception | 2 | step4_llmassist | — |
| 30 | Feedback Reliability and Precision | 2 | step4_llmassist | — |
| 31 | Framework Specific Proficiency | 2 | step4_llmassist | — |
| 32 | Hazards Of Excessive Dependency | 2 | step4_llmassist | overrode LLM 4 -> r |
| 33 | Heightened Output Velocity | 2 | step4_llmassist | — |
| 34 | Inaccurate And Incomplete Propositions | 2 | step4_llmassist | — |
| 35 | Instructional Placement Advantages | 2 | step4_llmassist | — |
| 36 | Manual Effort Intensity | 2 | step4_llmassist | — |
| 37 | Operational Labor Demands | 2 | step4_llmassist | — |
| 38 | Perceived Interaction Quality | 2 | step4_llmassist | — |
| 39 | Perceived Reliability and Utility | 2 | step4_llmassist | — |
| 40 | Positive Developer Reception | 2 | step4_llmassist | — |
| 41 | Protracted Troubleshooting Cycles | 2 | step4_llmassist | — |
| 42 | Refined Programmatic Logic and Clarity | 2 | step4_llmassist | — |
| 43 | Scaffolding Facilitated Performance | 2 | step4_llmassist | — |
| 44 | Substantial Manual Code Revision | 2 | step4_llmassist | — |
| 45 | Transparency Fostering User Confidence | 2 | step4_llmassist | — |
| 46 | Wordy And Robotic Output | 2 | step4_llmassist | — |
| 47 | Accelerated Requirements Engineering | 1 | step4_llmassist | — |
| 48 | Accurate Answer Summarisation | 1 | step4_llmassist | — |
| 49 | Ai Generated Bias | 1 | step4_llmassist | — |
| 50 | Ai-Induced Dependency Errors | 1 | step4_llmassist | — |
| 51 | Alternative Solution Exposure | 1 | step4_llmassist | — |
| 52 | Api Generation Inaccuracies | 1 | step4_llmassist | — |
| 53 | Augmented Understanding | 1 | step4_llmassist | — |
| 54 | Behavioral Changes | 1 | step4_llmassist | — |
| 55 | Better Belief Calibration | 1 | step4_llmassist | — |
| 56 | Coding Performance Distinction | 1 | step4_llmassist | — |
| 57 | Comparable Student Performance | 1 | step4_llmassist | — |
| 58 | Compilation Errors | 1 | step4_llmassist | — |
| 59 | Consistent Polite Tone | 1 | step4_llmassist | — |
| 60 | Consistent Test Selection | 1 | step4_llmassist | — |
| 61 | Context-Dependent Security Benefits | 1 | step4_llmassist | — |
| 62 | Conversation Sentiment Dynamics | 1 | step4_llmassist | — |
| 63 | Copilot Code Complexity | 1 | step4_llmassist | — |
| 64 | Decreased Forum Activity | 1 | step4_llmassist | — |
| 65 | Demand Mitigation | 1 | step4_llmassist | — |
| 66 | Documentation Synchronization Failure | 1 | step4_llmassist | — |
| 67 | Easier Maintainability | 1 | step4_llmassist | — |
| 68 | Edge Case Failure | 1 | step4_llmassist | — |
| 69 | Effective Initial Parallelization | 1 | step4_llmassist | — |
| 70 | Efficiency And Accessibility | 1 | step4_llmassist | — |
| 71 | Efficiency And Syntax Recall | 1 | step4_llmassist | — |
| 72 | Emotional Skill Development | 1 | step4_llmassist | — |
| 73 | Enhanced Report Usability | 1 | step4_llmassist | — |
| 74 | Enhances Computational Thinking | 1 | step4_llmassist | — |
| 75 | Equity Improvement | 1 | step4_llmassist | — |
| 76 | Exact Match Generation | 1 | step4_llmassist | — |
| 77 | Explanation Transformation Success | 1 | step4_llmassist | — |
| 78 | Faster Prototyping | 1 | step4_llmassist | — |
| 79 | Few-Shot Performance Benefit | 1 | step4_llmassist | — |
| 80 | Goal-Oriented Progress | 1 | step4_llmassist | — |
| 81 | High Bug Frequency | 1 | step4_llmassist | — |
| 82 | High Comment Resolution | 1 | step4_llmassist | — |
| 83 | High Expert Rating | 1 | step4_llmassist | — |
| 84 | High Fix Resolution Rate | 1 | step4_llmassist | — |
| 85 | High Frequency Of Insecure Code | 1 | step4_llmassist | — |
| 86 | High Interaction Volume | 1 | step4_llmassist | — |
| 87 | High Modification Rate | 1 | step4_llmassist | — |
| 88 | High Recommendation Accuracy | 1 | step4_llmassist | — |
| 89 | High Resolution By Category | 1 | step4_llmassist | — |
| 90 | High Resolution Rate Via Hybrid System | 1 | step4_llmassist | — |
| 91 | High Usability And Low Workload | 1 | step4_llmassist | — |
| 92 | High Usability Score | 1 | step4_llmassist | — |
| 93 | High User Preference | 1 | step4_llmassist | — |
| 94 | High Zero-Revision Merge Rate | 1 | step4_llmassist | — |
| 95 | High-Quality Insights | 1 | step4_llmassist | — |
| 96 | High-Quality Language Generation | 1 | step4_llmassist | — |
| 97 | Human-Comparable Performance | 1 | step4_llmassist | — |
| 98 | Hypothesis Generation | 1 | step4_llmassist | — |
| 99 | Immediate Test Usability | 1 | step4_llmassist | — |
| 100 | Impact Of Cot | 1 | step4_llmassist | — |
| 101 | Improved Fuzzing Coverage | 1 | step4_llmassist | — |
| 102 | Improved Health Literacy | 1 | step4_llmassist | — |
| 103 | Improved Semantic Clarity | 1 | step4_llmassist | — |
| 104 | Improved Task Focus | 1 | step4_llmassist | — |
| 105 | Increased Localization Success Rate | 1 | step4_llmassist | — |
| 106 | Increased Merge Probability | 1 | step4_llmassist | — |
| 107 | Increased Perceived Fairness | 1 | step4_llmassist | — |
| 108 | Increased Suggestion Adoption | 1 | step4_llmassist | — |
| 109 | Increased Task Autonomy | 1 | step4_llmassist | — |
| 110 | Increased Team Confidence | 1 | step4_llmassist | — |
| 111 | Increased User Frustration | 1 | step4_llmassist | — |
| 112 | Insecure Suggestion Exposure | 1 | step4_llmassist | — |
| 113 | Interdependent Task Coherence | 1 | step4_llmassist | — |
| 114 | Interruption Costs | 1 | step4_llmassist | — |
| 115 | Irrelevant Suggestions | 1 | step4_llmassist | — |
| 116 | Japanese Language Superiority | 1 | step4_llmassist | — |
| 117 | Junior Developer Learning | 1 | step4_llmassist | — |
| 118 | Knowledge Transfer Success | 1 | step4_llmassist | — |
| 119 | Lack Of Preliminary Searching | 1 | step4_llmassist | — |
| 120 | Learning Programming Concepts | 1 | step4_llmassist | — |
| 121 | Loss Of Social Validation | 1 | step4_llmassist | — |
| 122 | Low Acceptance Of Atg Tests | 1 | step4_llmassist | — |
| 123 | Low Direct Code Adoption | 1 | step4_llmassist | — |
| 124 | Low Explicit Feedback Rate | 1 | step4_llmassist | — |
| 125 | Low Perceived Persuasiveness | 1 | step4_llmassist | — |
| 126 | Low Repair Cost | 1 | step4_llmassist | — |
| 127 | Lower Code Survival | 1 | step4_llmassist | — |
| 128 | Manual Interference Causes Errors | 1 | step4_llmassist | — |
| 129 | Memory Allocation Vulnerabilities | 1 | step4_llmassist | — |
| 130 | Metric Improvements | 1 | step4_llmassist | — |
| 131 | Mixed Conceptual Learning Outcomes | 1 | step4_llmassist | — |
| 132 | Mixed-Model Synergy | 1 | step4_llmassist | — |
| 133 | Moderate Answer Accuracy | 1 | step4_llmassist | — |
| 134 | Motivation Impact On Performance | 1 | step4_llmassist | — |
| 135 | Naturalness Improves Code Understanding | 1 | step4_llmassist | — |
| 136 | Negative Performance Impact | 1 | step4_llmassist | — |
| 137 | Negative Wellbeing Impacts | 1 | step4_llmassist | — |
| 138 | Neutral Vulnerability Impact | 1 | step4_llmassist | — |
| 139 | No Confidence Shift | 1 | step4_llmassist | — |
| 140 | No Time Savings | 1 | step4_llmassist | — |
| 141 | Omission Of Requirements | 1 | step4_llmassist | — |
| 142 | Output Inconsistency | 1 | step4_llmassist | — |
| 143 | Pattern Detection Performance | 1 | step4_llmassist | — |
| 144 | Perceived Chatbot Advantages | 1 | step4_llmassist | — |
| 145 | Perceived Educational Value | 1 | step4_llmassist | — |
| 146 | Perceived Humanness | 1 | step4_llmassist | — |
| 147 | Perceived Usefulness | 1 | step4_llmassist | — |
| 148 | Popup Ui Helpfulness | 1 | step4_llmassist | — |
| 149 | Problem Resolution | 1 | step4_llmassist | — |
| 150 | Prompting Improves Repair | 1 | step4_llmassist | — |
| 151 | Quantitative Security Increase | 1 | step4_llmassist | — |
| 152 | Rationale Variance | 1 | step4_llmassist | — |
| 153 | Reduced Cognitive Effort | 1 | step4_llmassist | — |
| 154 | Reduced Generation Efficiency | 1 | step4_llmassist | — |
| 155 | Reduced Idea Generation | 1 | step4_llmassist | — |
| 156 | Reduced Intellectual Engagement | 1 | step4_llmassist | — |
| 157 | Reduced Interaction Overhead | 1 | step4_llmassist | — |
| 158 | Reduced Investigation Time | 1 | step4_llmassist | — |
| 159 | Reduced Ownership Feeling | 1 | step4_llmassist | — |
| 160 | Reduced Peer Collaboration | 1 | step4_llmassist | — |
| 161 | Reduced Pr Communication | 1 | step4_llmassist | — |
| 162 | Reduced Public Help-Seeking | 1 | step4_llmassist | — |
| 163 | Reduced Search Effort | 1 | step4_llmassist | — |
| 164 | Reduced Typing Effort | 1 | step4_llmassist | — |
| 165 | Reluctance To Recommend | 1 | step4_llmassist | — |
| 166 | Repeated Execution Without Edits | 1 | step4_llmassist | — |
| 167 | Response Agreement Rate | 1 | step4_llmassist | — |
| 168 | Revealing Value Disagreements | 1 | step4_llmassist | — |
| 169 | Risk Of Shallow Learning | 1 | step4_llmassist | — |
| 170 | Security Improvement In Complex Tasks | 1 | step4_llmassist | — |
| 171 | Self-Contradictory Behavior | 1 | step4_llmassist | — |
| 172 | Sentiment Differences | 1 | step4_llmassist | — |
| 173 | Significant Fix Effort | 1 | step4_llmassist | — |
| 174 | Simplified Employee Onboarding | 1 | step4_llmassist | — |
| 175 | Single-Use Generated Code | 1 | step4_llmassist | — |
| 176 | Speed Efficiency | 1 | step4_llmassist | — |
| 177 | Speed Of Ai Response | 1 | step4_llmassist | — |
| 178 | Student Preference For Llm Graders | 1 | step4_llmassist | — |
| 179 | Successful Code Migration | 1 | step4_llmassist | — |
| 180 | Superior Test Naming | 1 | step4_llmassist | — |
| 181 | Syntax And Parameter Hallucinations | 1 | step4_llmassist | — |
| 182 | Time Reduction Benefit | 1 | step4_llmassist | — |
| 183 | Time-Saving Via Summaries | 1 | step4_llmassist | — |
| 184 | Unintended Code Modification | 1 | step4_llmassist | — |
| 185 | Unintended Quality Improvements | 1 | step4_llmassist | — |
| 186 | Unnoticed Harmful Behavior | 1 | step4_llmassist | — |
| 187 | User Fulfillment And Productivity | 1 | step4_llmassist | — |
| 188 | Valuable Study Aid | 1 | step4_llmassist | — |
| 189 | Variable Scoping Errors | 1 | step4_llmassist | — |
| 190 | Workflow Convenience | 1 | step4_llmassist | — |
| 191 | Workload Reduction | 1 | step4_llmassist | — |
| 192 | Zero-Shot Type Typing Failure | 1 | step4_llmassist | — |

### Affordance / Surface (56 labels)

| # | Canonical label | Size | Source | Notes |
|---:|---|---:|---|---|
| 1 | Integrated Development Tooling Workflows | 5 | step3 | — |
| 2 | Workflow Integration Depth | 4 | step3 | — |
| 3 | Comprehensive Development Lifecycle Integration | 2 | step4_llmassist | — |
| 4 | Directed Cognitive Prioritization | 2 | step4_llmassist | — |
| 5 | Facilitating Initial Task Steps | 2 | step4_llmassist | — |
| 6 | Manual Clipboard Operations | 2 | step4_llmassist | — |
| 7 | Manual Output Refinement | 2 | step4_llmassist | — |
| 8 | Syntax Proficiency Support | 2 | step4_llmassist | — |
| 9 | Adaptive Timing Controller | 1 | step4_llmassist | — |
| 10 | Api Inference Capability | 1 | step4_llmassist | — |
| 11 | Api Migration | 1 | step4_llmassist | — |
| 12 | Broad Se Task Coverage | 1 | step4_llmassist | — |
| 13 | Code Detail Reminder | 1 | step4_llmassist | — |
| 14 | Common Template Components | 1 | step4_llmassist | — |
| 15 | Comprehension Enforcement | 1 | step4_llmassist | — |
| 16 | Content Deletion Action | 1 | step4_llmassist | — |
| 17 | Context Extraction Via Pdg | 1 | step4_llmassist | — |
| 18 | Context Optimization | 1 | step4_llmassist | — |
| 19 | Contextual Alternative Generation | 1 | step4_llmassist | — |
| 20 | Contextual File Inclusion | 1 | step4_llmassist | — |
| 21 | Data Processing Functions | 1 | step4_llmassist | — |
| 22 | Decision Support | 1 | step4_llmassist | — |
| 23 | File Upload For Context | 1 | step4_llmassist | — |
| 24 | Full Codebase Processing | 1 | step4_llmassist | — |
| 25 | Full-Stack Development | 1 | step4_llmassist | — |
| 26 | Human-In-The-Loop Fallback | 1 | step4_llmassist | — |
| 27 | Ide Metadata Context Injection | 1 | step4_llmassist | — |
| 28 | Ide-Based Telemetry And Requests | 1 | step4_llmassist | — |
| 29 | Intermediate Output Visibility | 1 | step4_llmassist | — |
| 30 | Llm Ga As Integration | 1 | step4_llmassist | — |
| 31 | Llm Visual Comprehension | 1 | step4_llmassist | — |
| 32 | Llm-Based Text Input | 1 | step4_llmassist | — |
| 33 | Manual Terminology Refinement | 1 | step4_llmassist | — |
| 34 | Motion Recording Support | 1 | step4_llmassist | — |
| 35 | Native Channel Integration | 1 | step4_llmassist | — |
| 36 | Office Hour Augmentation | 1 | step4_llmassist | — |
| 37 | Output Modification | 1 | step4_llmassist | — |
| 38 | Parallel Chain Structures | 1 | step4_llmassist | — |
| 39 | Personality-Adapted Ai Responses | 1 | step4_llmassist | — |
| 40 | Pr Interface Integration | 1 | step4_llmassist | — |
| 41 | Project Documentation | 1 | step4_llmassist | — |
| 42 | Prompt Versioning | 1 | step4_llmassist | — |
| 43 | Quiz-Based Learning | 1 | step4_llmassist | — |
| 44 | Real-Time Troubleshooting Help | 1 | step4_llmassist | — |
| 45 | Rule-Grounded Explainability | 1 | step4_llmassist | — |
| 46 | Semantic Context Awareness | 1 | step4_llmassist | — |
| 47 | State Restoration Capability | 1 | step4_llmassist | — |
| 48 | Syntax Correction Capability | 1 | step4_llmassist | — |
| 49 | System Architecture | 1 | step4_llmassist | — |
| 50 | Testing Frameworks Integration | 1 | step4_llmassist | — |
| 51 | Ui Shortcuts For Common Tasks | 1 | step4_llmassist | — |
| 52 | User Profiling Mechanism | 1 | step4_llmassist | — |
| 53 | Version Rollback Feature | 1 | step4_llmassist | — |
| 54 | Visual Failure Organization | 1 | step4_llmassist | — |
| 55 | Web Ui Usage | 1 | step4_llmassist | — |
| 56 | Zero Temperature Setting | 1 | step4_llmassist | — |

### Constraint (119 labels)

| # | Canonical label | Size | Source | Notes |
|---:|---|---:|---|---|
| 1 | Regulating Cognitive Processing Demands | 7 | step3 | — |
| 2 | Restricted Contextual Scope | 5 | step3 | — |
| 3 | Erosion of Contextual Continuity | 3 | step4_llmassist | — |
| 4 | Linguistic Proficiency Disparities | 3 | step4_llmassist | — |
| 5 | Minimalist Interaction Prioritization | 3 | step4_llmassist | — |
| 6 | Navigating Initial Skill Acquisition | 3 | step4_llmassist | — |
| 7 | Restricted Contextual Capacity | 3 | step4_llmassist | — |
| 8 | Substantial Processing Lag | 3 | step4_llmassist | — |
| 9 | Contextual Processing Limitations | 2 | step4_llmassist | — |
| 10 | Counteracting Proficiency Deficits | 2 | step4_llmassist | — |
| 11 | Flawed Contextual Grounding | 2 | step4_llmassist | — |
| 12 | Goal Recognition Complexity | 2 | step4_llmassist | — |
| 13 | Limited Prompt Engineering Efficacy | 2 | step4_llmassist | — |
| 14 | Mandatory Human Supervision | 2 | step4_llmassist | — |
| 15 | Prioritizing Quality Over Volume | 2 | step4_llmassist | — |
| 16 | Unpredictable Generative Outputs | 2 | step4_llmassist | — |
| 17 | Verification Cognitive Burden | 2 | step4_llmassist | — |
| 18 | Agent Interaction Complexity | 1 | step4_llmassist | — |
| 19 | Ai Misunderstands Prompts | 1 | step4_llmassist | — |
| 20 | Api Deprecation Challenges | 1 | step4_llmassist | — |
| 21 | Api/Infrastructure Fragility | 1 | step4_llmassist | — |
| 22 | Ast Structural Loss | 1 | step4_llmassist | — |
| 23 | Audio-Visual Sync Issues | 1 | step4_llmassist | — |
| 24 | Barriers To Developer Resolution | 1 | step4_llmassist | — |
| 25 | Baseline Performance Challenge | 1 | step4_llmassist | — |
| 26 | Boilerplate Offloading Blindspot | 1 | step4_llmassist | — |
| 27 | Cascading Errors | 1 | step4_llmassist | — |
| 28 | Classification Limitations | 1 | step4_llmassist | — |
| 29 | Code Intention Required | 1 | step4_llmassist | — |
| 30 | Code Transparency Challenge | 1 | step4_llmassist | — |
| 31 | Cognitive Pace Mismatch | 1 | step4_llmassist | — |
| 32 | Complex Condition Failure | 1 | step4_llmassist | — |
| 33 | Complex Reasoning Failure | 1 | step4_llmassist | — |
| 34 | Complexity Limitation | 1 | step4_llmassist | — |
| 35 | Component Coupling Complexity | 1 | step4_llmassist | — |
| 36 | Context Distraction | 1 | step4_llmassist | — |
| 37 | Context Ignorance | 1 | step4_llmassist | — |
| 38 | Context Provision Challenge | 1 | step4_llmassist | — |
| 39 | Context Requirements For Tests | 1 | step4_llmassist | — |
| 40 | Context Resolution Failure | 1 | step4_llmassist | — |
| 41 | Contextual Logic Errors | 1 | step4_llmassist | — |
| 42 | Defect Prediction Limitation | 1 | step4_llmassist | — |
| 43 | Demographic Bias Vulnerability | 1 | step4_llmassist | — |
| 44 | Domain Context Deficit | 1 | step4_llmassist | — |
| 45 | Domain Convention Misalignment | 1 | step4_llmassist | — |
| 46 | Domain Fine-Tuning Necessity | 1 | step4_llmassist | — |
| 47 | Domain-Specific Context Challenge | 1 | step4_llmassist | — |
| 48 | Evidence-Constrained Responses | 1 | step4_llmassist | — |
| 49 | Extraction Failure | 1 | step4_llmassist | — |
| 50 | Forces Algorithmic Planning | 1 | step4_llmassist | — |
| 51 | Format Limitation | 1 | step4_llmassist | — |
| 52 | Frameworks/Libraries Challenges | 1 | step4_llmassist | — |
| 53 | Generation Latency | 1 | step4_llmassist | — |
| 54 | Geographic Bias | 1 | step4_llmassist | — |
| 55 | Granularity Trade-Offs | 1 | step4_llmassist | — |
| 56 | Hallucinated Identifiers | 1 | step4_llmassist | — |
| 57 | High Resource Footprint | 1 | step4_llmassist | — |
| 58 | Inaccessible Visual Suggestions | 1 | step4_llmassist | — |
| 59 | Inconsistency Breaks Mental Models | 1 | step4_llmassist | — |
| 60 | Insufficient Progress Details | 1 | step4_llmassist | — |
| 61 | Intent Verification Difficulty | 1 | step4_llmassist | — |
| 62 | Interaction Path Dependency | 1 | step4_llmassist | — |
| 63 | Iterative Prompt Testing Overhead | 1 | step4_llmassist | — |
| 64 | Keyboard Navigation Issues | 1 | step4_llmassist | — |
| 65 | Knowledge Cutoff Limitations | 1 | step4_llmassist | — |
| 66 | Knowledge Source Mixing Issues | 1 | step4_llmassist | — |
| 67 | Large File Poor Quality | 1 | step4_llmassist | — |
| 68 | Limited Reliable Modeling | 1 | step4_llmassist | — |
| 69 | Llm Generation Errors | 1 | step4_llmassist | — |
| 70 | Local Exploitation Bias | 1 | step4_llmassist | — |
| 71 | Low-Resource Language Barrier | 1 | step4_llmassist | — |
| 72 | Missing Domain Knowledge | 1 | step4_llmassist | — |
| 73 | Missing Status Feedback | 1 | step4_llmassist | — |
| 74 | Missing Version Constraints | 1 | step4_llmassist | — |
| 75 | Model Degradation Over Time | 1 | step4_llmassist | — |
| 76 | Model Insensitivity To Prompt Patterns | 1 | step4_llmassist | — |
| 77 | Multi-Method Generation Challenge | 1 | step4_llmassist | — |
| 78 | Noise Propagation In Training | 1 | step4_llmassist | — |
| 79 | Novice Developer Liability | 1 | step4_llmassist | — |
| 80 | Opaque Context Window | 1 | step4_llmassist | — |
| 81 | Opaque Input-Output Mapping | 1 | step4_llmassist | — |
| 82 | Organizational Policy Constraint | 1 | step4_llmassist | — |
| 83 | Output Unreliability And Non-Determinism | 1 | step4_llmassist | — |
| 84 | Over-Documentation Challenge | 1 | step4_llmassist | — |
| 85 | Poor Relationship Identification | 1 | step4_llmassist | — |
| 86 | Positive Prediction Bias | 1 | step4_llmassist | — |
| 87 | Preventing Learning Bypass | 1 | step4_llmassist | — |
| 88 | Problem Interpretation Errors | 1 | step4_llmassist | — |
| 89 | Prompt Dependency | 1 | step4_llmassist | — |
| 90 | Prompt Formulation Difficulty | 1 | step4_llmassist | — |
| 91 | Prompt Fragility And Sensitivity | 1 | step4_llmassist | — |
| 92 | Prompting Skill Requirements | 1 | step4_llmassist | — |
| 93 | Relationship Extraction Difficulty | 1 | step4_llmassist | — |
| 94 | Repair Generation Failure | 1 | step4_llmassist | — |
| 95 | Resource Consumption Risks | 1 | step4_llmassist | — |
| 96 | Scope Localization | 1 | step4_llmassist | — |
| 97 | Security Boundary Setting | 1 | step4_llmassist | — |
| 98 | Semantic Evaluation Challenge | 1 | step4_llmassist | — |
| 99 | Semantic Reasoning Limits | 1 | step4_llmassist | — |
| 100 | Sequential Screen Reader Processing | 1 | step4_llmassist | — |
| 101 | Session Persistence Issues | 1 | step4_llmassist | — |
| 102 | Shallow Evidence Exploration | 1 | step4_llmassist | — |
| 103 | Specificity Tuning Issues | 1 | step4_llmassist | — |
| 104 | Struggle With Complex Usages | 1 | step4_llmassist | — |
| 105 | Struggles With Complex Architecture | 1 | step4_llmassist | — |
| 106 | Subject Writing Difficulty | 1 | step4_llmassist | — |
| 107 | Suboptimal Ui Aesthetics | 1 | step4_llmassist | — |
| 108 | Support Redundancy | 1 | step4_llmassist | — |
| 109 | Survey Length Constraint | 1 | step4_llmassist | — |
| 110 | Tactic Detection Limits | 1 | step4_llmassist | — |
| 111 | Task Abandonment Threshold | 1 | step4_llmassist | — |
| 112 | Test Data Scarcity | 1 | step4_llmassist | — |
| 113 | Test Generation Unreliability | 1 | step4_llmassist | — |
| 114 | Text Input Friction | 1 | step4_llmassist | — |
| 115 | Tool Integration Challenge | 1 | step4_llmassist | — |
| 116 | Traceability Limitations | 1 | step4_llmassist | — |
| 117 | Unpredictable Complex Outputs | 1 | step4_llmassist | — |
| 118 | Usability Challenges | 1 | step4_llmassist | — |
| 119 | Zero Temperature Non-Determinism | 1 | step4_llmassist | — |

### Meta-observation (101 labels)

| # | Canonical label | Size | Source | Notes |
|---:|---|---:|---|---|
| 1 | Adoption Drivers And Inhibitors | 3 | step3 | — |
| 2 | Survey Research Procedures | 3 | step4_llmassist | — |
| 3 | Adoption Success Performance Correlation | 2 | step4_llmassist | — |
| 4 | Autonomous LLM Programming Dependency | 2 | step4_llmassist | — |
| 5 | Code Adoption Discrepancy | 2 | step4_llmassist | — |
| 6 | Competence Driving Technology Adoption | 2 | step4_llmassist | — |
| 7 | Hybrid Empirical Assessment | 2 | step4_llmassist | — |
| 8 | Learner Perception Evaluations | 2 | step4_llmassist | — |
| 9 | Accessible To Novices | 1 | step4_llmassist | — |
| 10 | Active Engagement Builds Trust | 1 | step4_llmassist | — |
| 11 | Activity Transition Modelling | 1 | step4_llmassist | — |
| 12 | Agent Response Types | 1 | step4_llmassist | — |
| 13 | Ai For Requirements Engineering | 1 | step4_llmassist | — |
| 14 | Ai Replacing Human Crowds | 1 | step4_llmassist | — |
| 15 | Ai-Assisted Architecting | 1 | step4_llmassist | — |
| 16 | Ai-Human Alignment | 1 | step4_llmassist | — |
| 17 | Anthropomorphic Partnership Framing | 1 | step4_llmassist | — |
| 18 | Assessment Validity Threat | 1 | step4_llmassist | — |
| 19 | Bias Mitigation Importance | 1 | step4_llmassist | — |
| 20 | Code Comprehension Use Case | 1 | step4_llmassist | — |
| 21 | Common Usage Problems | 1 | step4_llmassist | — |
| 22 | Community Sensemaking | 1 | step4_llmassist | — |
| 23 | Comparative Usage Study | 1 | step4_llmassist | — |
| 24 | Complementary To Traditional Methods | 1 | step4_llmassist | — |
| 25 | Conceptual Examples Over Production | 1 | step4_llmassist | — |
| 26 | Controlled Experimental Study | 1 | step4_llmassist | — |
| 27 | Controlled Field Experiment | 1 | step4_llmassist | — |
| 28 | Creative Problem-Solving | 1 | step4_llmassist | — |
| 29 | Criticality Of Reliability | 1 | step4_llmassist | — |
| 30 | Cross-Framework Evaluation Setup | 1 | step4_llmassist | — |
| 31 | Desire For Human Interaction | 1 | step4_llmassist | — |
| 32 | Developer Questionnaire | 1 | step4_llmassist | — |
| 33 | Diverse Testing Concepts | 1 | step4_llmassist | — |
| 34 | Engineering Trust Requirements | 1 | step4_llmassist | — |
| 35 | Experience Reporting | 1 | step4_llmassist | — |
| 36 | Explanation Expectation | 1 | step4_llmassist | — |
| 37 | Familiarity Skips Scaffolding | 1 | step4_llmassist | — |
| 38 | Feature Popularity | 1 | step4_llmassist | — |
| 39 | Focus On Non-Functional Code | 1 | step4_llmassist | — |
| 40 | General Text Generation And Review | 1 | step4_llmassist | — |
| 41 | Hackathon Observation Study | 1 | step4_llmassist | — |
| 42 | High Evaluation Agreement | 1 | step4_llmassist | — |
| 43 | High User Adoption | 1 | step4_llmassist | — |
| 44 | High Utility Overrules Cost | 1 | step4_llmassist | — |
| 45 | Homework Solving Usage | 1 | step4_llmassist | — |
| 46 | Human Vs Ai Help-Seeking | 1 | step4_llmassist | — |
| 47 | Human-Ai Benchmark Evaluation | 1 | step4_llmassist | — |
| 48 | Ideation Primary Use Case | 1 | step4_llmassist | — |
| 49 | Implicit User Intent | 1 | step4_llmassist | — |
| 50 | Industrial Deployment Evaluation | 1 | step4_llmassist | — |
| 51 | Industry Llm Adoption Survey | 1 | step4_llmassist | — |
| 52 | Ip And Ethical Risks | 1 | step4_llmassist | — |
| 53 | Json Formatting Dominance | 1 | step4_llmassist | — |
| 54 | Learning Process Telemetry | 1 | step4_llmassist | — |
| 55 | Limited Perceived Value | 1 | step4_llmassist | — |
| 56 | Llm Api Misuse Types | 1 | step4_llmassist | — |
| 57 | Llm Comment Distribution | 1 | step4_llmassist | — |
| 58 | Llm Output Self-Plagiarism | 1 | step4_llmassist | — |
| 59 | Longitudinal Field Deployment | 1 | step4_llmassist | — |
| 60 | Low Analysis Usage | 1 | step4_llmassist | — |
| 61 | Mixed Population Survey | 1 | step4_llmassist | — |
| 62 | Mixed User Base | 1 | step4_llmassist | — |
| 63 | Multi-Role Expert Study | 1 | step4_llmassist | — |
| 64 | Need For Customization | 1 | step4_llmassist | — |
| 65 | Need For Examples And Tutorials | 1 | step4_llmassist | — |
| 66 | Need For Explainability | 1 | step4_llmassist | — |
| 67 | Non-It Staff Participation | 1 | step4_llmassist | — |
| 68 | Occasional Ai Usage | 1 | step4_llmassist | — |
| 69 | Participant Sample Size | 1 | step4_llmassist | — |
| 70 | Persona-Based Usability Evaluation | 1 | step4_llmassist | — |
| 71 | Popular Languages | 1 | step4_llmassist | — |
| 72 | Practitioner Pushback | 1 | step4_llmassist | — |
| 73 | Preference For Built-In Helpers | 1 | step4_llmassist | — |
| 74 | Preference For Diversity | 1 | step4_llmassist | — |
| 75 | Preference For General Tools | 1 | step4_llmassist | — |
| 76 | Preference For Hybrid Generation | 1 | step4_llmassist | — |
| 77 | Prior Knowledge Application | 1 | step4_llmassist | — |
| 78 | Privacy And Permission Concerns | 1 | step4_llmassist | — |
| 79 | Project-Based Evaluation | 1 | step4_llmassist | — |
| 80 | Prompting Time Distribution | 1 | step4_llmassist | — |
| 81 | Qualitative User Evaluation | 1 | step4_llmassist | — |
| 82 | Reduced Ai Use In Pp | 1 | step4_llmassist | — |
| 83 | Rejection From Process Complexity | 1 | step4_llmassist | — |
| 84 | Replacing Traditional Search | 1 | step4_llmassist | — |
| 85 | Self-Hosting For Security | 1 | step4_llmassist | — |
| 86 | Shift To Private Problem-Solving | 1 | step4_llmassist | — |
| 87 | Simulated Onboarding Tasks | 1 | step4_llmassist | — |
| 88 | Statistical Insignificance | 1 | step4_llmassist | — |
| 89 | Strategy Variation By Interface | 1 | step4_llmassist | — |
| 90 | Student Annotation Task | 1 | step4_llmassist | — |
| 91 | Student Skepticism Towards Ai | 1 | step4_llmassist | — |
| 92 | Tam Motivational Factors | 1 | step4_llmassist | — |
| 93 | Task Complexity Increases Non-Determinism | 1 | step4_llmassist | — |
| 94 | Testing Lifecycle Distribution | 1 | step4_llmassist | — |
| 95 | Time Spent On Bodies | 1 | step4_llmassist | — |
| 96 | Trade-Off Expediency Vs Security | 1 | step4_llmassist | — |
| 97 | Training Data Memorisation | 1 | step4_llmassist | — |
| 98 | Transition To Task Specification | 1 | step4_llmassist | — |
| 99 | User Study Demographics | 1 | step4_llmassist | — |
| 100 | Various Se Tasks | 1 | step4_llmassist | — |
| 101 | Workplace Tool Usage | 1 | step4_llmassist | — |

---

## Step-3 → Step-4 transition notes (audit appendix)

This appendix consolidates provenance material that was inline in the v0.2 strawman. Mode sections above stay clean; the audit trail is captured here so reviewers can reconstruct decisions without chasing comments across mode tables.

**Provenance tally:**

| Source | Rows | Meaning |
|---|---:|---|
| `step3` | 40 (5.7%) | Step-3 top-40 strawman placement (rater) |
| `step4_llmassist` | 667 (94.3%) | Step-4 LLM-assisted placement (rater-confirmed) |
| `step4` | 0 (0.0%) | Step-4 manual placement (pre-LLM-assist base script) |
| `(blank)` | 0 (0.0%) | Unsourced (should be 0) |

**LLM-override audit:** 11 canonical label(s) where the rater chose a mode different from the LLM's suggestion at Step 4. These rows carry a `overrode LLM X -> Y` annotation in `taxonomy_classifications.csv:notes`. Dependability-relevant; see `decision_register.csv` for any substantive entries.

| Canonical label | Mode | Size | Note |
|---|---|---:|---|
| Architectural Openness Expectations | 4 | 2 | overrode LLM r -> 4 |
| Hazards Of Excessive Dependency | r | 2 | overrode LLM 4 -> r |
| Knowledge Formalization Dynamics | 2 | 2 | overrode LLM r -> 2 |
| Diagramming For Comprehension | 3 | 1 | overrode LLM 4 -> 3 |
| Educational Content Generation | 2 | 1 | overrode LLM 5 -> 2 |
| Error Logging And Search | 2 | 1 | overrode LLM r -> 2 |
| Ethical And Security Challenges | 2 | 1 | overrode LLM r -> 2 |
| Exacerbates Incorrect Beliefs | 2 | 1 | overrode LLM r -> 2 |
| Scratchpad Reasoning Tracking | 3 | 1 | overrode LLM r -> 3 |
| Step-Wise Script Execution | 3 | 1 | overrode LLM 5 -> 3 |
| Visual Parsing Complexity | 3 | 1 | overrode LLM r -> 3 |

**Step-3 v0.2 hand-written annotations:** merged/renamed/cross-referenced clusters and the Mode-4↔Mode-5 ambiguity flags are logged in `decision_register.csv` under rows `task4_2_canonical_merge`, `task4_2_canonical_rename`, and the forthcoming `taxonomy_finalised` row (Step 9).
---

## Cross-references

- Live tracker: `task4_2_todo.md`
- Phase tracker: `task4_tracker.md §3.2`
- Task design: `design/4_2_interaction_taxonomy.md` (§4 schema = DoD contract)
- Step-4 classifier design: `design/4_2_taxonomy_classify.md`, `design/4_2_taxonomy_classify_llmassist.md`
- Step-4.5 sub-categorisation: `design/4_2_residuals_subcategorise.md`
- Step-5 render: `design/4_2_taxonomy_render.md`
- Input: `artifacts/synthesis/taxonomy_classifications.csv` (707 rows), `artifacts/synthesis/consolidated_codes.csv` (707 canonical labels)
- Proposal anchor: `docs/ERP2_Research_Proposal.docx` Appendix C Table 4 (8 illustrative modes)
- Methodology: Cruzes & Dybå (2011) Step 4; Cruzes et al. (2015) §3

---

## Next steps (owner: rater)

See `task4_2_todo.md §4 Action tracker — Immediate`.
