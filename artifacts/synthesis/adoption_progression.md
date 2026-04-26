# Adoption Progression Framework — Delegation Depth

> **Purpose.** Sequences the five interaction modes of the RQ2 taxonomy along the **delegation-depth axis** and names the prerequisites — capability, organisational, and risk-posture — for moving from one mode to the next. This document is the practitioner-facing complement to `self_assessment_rubric.md`: the rubric tells you *where you are*; this framework tells you *what moving deeper looks like*.
> **Scope.** Modes 1–5 from `interaction_taxonomy.md`. Residuals (outcomes / affordances / constraints / meta-observations) are cross-cutting — they shape movement along the axis but are not steps on it.
> **Rater:** TBS  **Generated:** 2026-04-19

---

## The axis

The taxonomy orders modes by a single ordinal axis: **the degree to which the human delegates the software-engineering task to the AI agent.** The axis runs from the human producing the work with AI contributing continuations (Mode 1), through turn-taking collaboration (Modes 2 and 3) and evaluative review (Mode 4), to the AI executing multi-step work with the human reviewing at task-level checkpoints (Mode 5). See `interaction_taxonomy.md §Axis` for the axis's commitment in the research proposal (§3.5 and Appendix C).

The axis is **ordinal, not cumulative**. Being in Mode 5 does not mean you are also doing Modes 1–4 in parallel; being in Mode 2 does not mean you have mastered Mode 1 first. Practitioners move along the axis by reshaping their workflow, not by stacking new behaviours on top of old ones.

---

## Progression map

```
  (Assistive)                                               (Autonomous)
  Mode 1 ───────▶ Mode 2 ───────▶ Mode 5
                     │
                     ├──▶ Mode 3   (parallel branch — visual/declarative)
                     │
                     └──▶ Mode 4   (parallel coexistence — evaluation)
```

**Reading the map.** The backbone progression is **Mode 1 → Mode 2 → Mode 5**. Mode 3 and Mode 4 are **parallel branches** off Mode 2 rather than strict up-steps: Mode 3 sits at the same delegation depth as Mode 2 but uses a visual/declarative surface; Mode 4 is an **evaluative stance** that can and usually does coexist with whichever generation mode (1, 2, 3, or 5) a practitioner uses. 

---

## Mode 1 (Inline Completion) — entry prerequisites

Mode 1 is the lowest-friction entry point into AI-assisted SE. Prerequisites to reach it:

**Capability:**
- An editor or IDE that supports AI autocomplete extensions (VS Code, JetBrains IDEs, Cursor, Neovim + LSP-based plugin, etc.).
- Basic familiarity with the extension's accept / reject interaction pattern (tab-to-accept, escape-to-reject, or equivalent).

**Organisational:**
- The organization permits the use of an AI coding extension on work code (licence in place, acceptable-use policy covers the tool, data-egress terms acceptable to security).


**Risk posture:**
- Acceptance that AI suggestions can be wrong and that the developer retains responsibility for every line committed.
- Acceptance that the AI's training distribution shapes what it suggests; suggestions may reflect mainstream patterns at the expense of project-specific conventions.

---

## Mode 1 → Mode 2 (Conversational Prompting) transition

Moving from Mode 1 to Mode 2 reframes the unit of interaction from the single suggestion to the prompt-response turn. Prerequisites:

**Capability:**
- Comfort **articulating intent** in natural language at the granularity of a prompt turn — writing a paragraph that describes what the code should do, what constraints apply, and what is already in place.
- Comfort iterating across turns: reading the AI's multi-line response critically, identifying what the AI misunderstood, and re-prompting to correct.
- Basic prompt-engineering fluency (providing context, constraining output format, asking for explanation alongside code).

**Organisational:**
- No policy blocking chat-based LLM use for work code (some organisations permit inline Copilot-style tools while prohibiting chat paste of proprietary code — this is a common sub-step gate).
- If organisational policy requires prompt-logging or redaction, the tooling and habit must be in place.

**Risk posture:**
- Acceptance that longer AI responses are more likely to contain subtle errors than short continuations — the practitioner must be willing to read and evaluate, not skim and commit.
- Acceptance that multi-turn dialogues leak more context than inline completions; data-handling posture must match.

---

## Mode 2 → Mode 3 (Visual / Declarative Composition) transition

Mode 3 is a **parallel branch**, not a strict up-step from Mode 2. A practitioner who uses Mode 2 does not need to "graduate" through Mode 3; a practitioner who starts in Mode 3 does not need to have used Mode 2 first. Transitioning to Mode 3 (additively or as a partial workflow substitute) requires:

**Capability:**
- Access to and training in a visual or declarative tooling surface that supports AI augmentation — low-code / no-code platforms, AI-augmented workflow builders, natural-language-to-workflow pipelines, or similar.
- Comfort expressing intent **structurally** rather than in free-form prose: a form, a workflow graph, a schema, or a set of connected blocks rather than a paragraph of prompt.

**Organisational:**
- A use case that *benefits* from visual/declarative expression — typically workflow automation, citizen-developer-adjacent app building, or domain-specific platform work. Mode 3 is less relevant to traditional library/service engineering. 
- Licence and deployment footprint for the chosen platform.

**Risk posture:**
- Acceptance that the visual surface's execution semantics can drift from what the practitioner intends — and that the AI-generated underlying logic is harder to inspect than hand-written code.
- Acceptance of platform lock-in if the visual tool ties the implementation to a specific runtime.

---

## Mode 2 → Mode 4 (Review & Validation) transition

Mode 4 is **evaluative coexistence**, not a strict up-step. A practitioner who reaches Mode 2 often incorporates Mode 4 without leaving Mode 2. Transitioning *into an evaluative stance* (as opposed to a generative one) requires:

**Capability:**
- Ability to articulate quality criteria for the artefact under review: correctness against a spec, security properties, maintainability heuristics, alignment with project conventions.
- Familiarity with AI code-review tooling, AI-augmented linters, or prompt patterns that direct the AI to evaluate rather than generate.
- Calibrated judgement about when to trust the AI's evaluation and when to sanity-check it manually — i.e. trust calibration as a named skill. 

**Organisational:**
- Acceptance within the team that AI-produced review signals (e.g. hallucination flags, quality scores, security callouts) inform but do not replace human decisions at merge time.
- Clarity on audit-trail obligations: if AI reviewed code, is that visible in the review record?

**Risk posture:**
- Awareness that Mode 4 surfaces two distinct risks: the AI may miss real defects (false negatives — over-trust) and the AI may flag non-defects (false positives — alert fatigue).
- Acceptance that trusting AI-as-reviewer without verification can produce worse outcomes than not using Mode 4 at all. This is the **over-reliance risk** named in the taxonomy.

---

## Mode 3 → Mode 4 (Review & Validation) transition

Like Mode 2 → Mode 4, Mode 3 → Mode 4 is **evaluative coexistence**, not a strict up-step. A Mode 3 practitioner who also reviews the AI's output is operating in Mode 3 + Mode 4. One distinctive challenge separates this path from Mode 2 → Mode 4: **the review target is the rendered flow, not the underlying code.** A visual or declarative surface hides execution semantics behind a graph, form, or block layout, so the reviewer must trace the visual flow and reason about what the runtime will do with it rather than reading source directly. The corpus names this in **Visual Parsing Complexity** (Mode 3) and, from the review side, **Visual Sequential Code Tracing** (Mode 4).

**Prerequisites beyond those listed under Mode 2 → Mode 4:**
- Ability to trace execution through the visual surface, or tooling that expands the surface to the underlying logic for inspection.
- Calibration that visual-surface defects are often invisible until runtime — review coverage must extend to end-to-end execution, not static inspection of the diagram.


---

## Mode 2 → Mode 5 (Delegated Task Execution) transition

Mode 5 is the **deepest delegation step** on the backbone progression. The move from Mode 2 to Mode 5 shifts the unit of interaction from the prompt-response turn to the task, and shifts review from turn-by-turn to checkpoint-by-checkpoint. Prerequisites:

**Capability:**
- Ability to **scope a task** clearly enough that success can be checked at completion rather than during execution: "generate a test suite for module X with ≥80% branch coverage and no mocks of DB calls", not "help me with tests".
- Fluency with agentic tooling that runs for minutes or hours on a single task (agent frameworks, Cursor agent mode, Claude Code subagents, SWE-bench-style evaluation harnesses). 
- Ability to define and automate success criteria — tests, behavioural assertions, diff review — that the agent can iterate against.

**Organisational:**
- Trust that the agent can safely read, modify, and run code across the project — this typically requires sandboxing, scoped credentials, and a revertibility policy (e.g. agent works on a branch, never on main).
- CI/CD infrastructure that supports rapid checkpoint verification: tests run in minutes, not hours.
- Clarity on audit trails — which agent ran when, on what branch, with what credentials.

**Risk posture:**
- Acceptance that the agent will make decisions the practitioner would have made differently; the cost is paid back by the delegation throughput, if the task scope is right.
- Acceptance of the blast-radius difference: an agent acting across files can cause more damage than a single-turn prompt error. Revertibility and pre-commit checks become load-bearing.
- Awareness that over-broad task scope is the **number one mode-5 failure pattern** — tasks must be scoped tightly enough that a bad outcome is contained.

---

## Mode 4 ↔ Mode 5 relationship

Modes 4 and 5 interlock: most Mode 5 workflows **embed Mode 4** at the checkpoint review stage (the human or a second AI evaluates the agent's output before accept). A practitioner who is strong in Mode 4 has an easier path into Mode 5 because they already know how to articulate success criteria and calibrate trust.

---

## What can block progression (Residuals in action)

Residuals — the 468 labels (66.2% of the partition) sub-categorised as **outcomes**, **affordances**, **constraints**, and **meta-observations** — gate movement along the axis. The most frequently observed blockers in the corpus:

| Blocker category | Example evidence shape in the corpus | Typical axis effect |
|---|---|---|
| **Constraint — context window** | Restricted Contextual Scope / Restricted Contextual Capacity / Erosion of Contextual Continuity | Pushes practitioners *back* from Mode 5 to Mode 2 on large codebases, because the agent loses track across multiple sub-steps. |
| **Constraint — cognitive load** | Regulating Cognitive Processing Demands / Directed Cognitive Prioritization | Caps movement into Mode 5 when the practitioner cannot absorb the agent's checkpoint output fast enough to stay in control. |
| **Constraint — processing lag** | Substantial Processing Lag | Discourages Mode 2 over Mode 1 when every turn costs seconds-to-minutes. |
| **Affordance — workflow integration depth** | Workflow Integration Depth / Integrated Development Tooling Workflows | Enables Mode 1 or Mode 5 when the tool is deeply in-flow; its absence forces Mode 2 on a separate surface. |
| **Meta — adoption drivers and inhibitors** | Adoption Drivers And Inhibitors | Organisational readiness shapes which modes are *available*; practitioner capability shapes which are *used*. |
| **Outcome — accuracy / productivity signals** | Varied Productivity Outcomes / Impact On Accuracy Outcomes / Enhanced Operational Productivity | Reinforces or weakens a practitioner's commitment to a mode. Mode shifts often trail outcome signals by months. |

See `interaction_taxonomy.md §Residuals / Cross-Cutting Evidence` for the full inventory and sub-categorisation.

---

## Non-linearity note

The delegation-depth axis is **ordinal, not a prescriptive ladder.** Specifically:

- **Mode 3 is a parallel branch,** not a strict up-step from Mode 2. A citizen-developer or low-code practitioner may operate primarily in Mode 3 without having used Mode 2. Treat the 3-vs-2 choice as "visual/declarative versus conversational", not "more advanced versus less advanced".
- **Mode 4 coexists with everything.** Review and validation is an *evaluative stance* that can be layered on top of Modes 1, 2, 3, or 5. A practitioner fluent in Mode 2 who also reviews the AI's output is in Mode 2 + Mode 4, not transitioning out of Mode 2.
- **Mode 5 embeds Mode 4 at checkpoints.** The most sustainable Mode-5 practice is one where checkpoint reviews are formal Mode-4 judgements — explicit pass/fail gates against pre-stated success criteria — rather than informal "looks good" accepts.
- **Regression is normal.** A practitioner who reaches Mode 5 for some task scopes may legitimately drop back to Mode 2 when context windows, latency, or trust calibration make Mode 5 counter-productive. Mode regression under clear constraints is **competent practice**, not deficit.
- **The corpus evidence on Mode 1 is thin** (4 canonical labels of 707). This does not mean Mode 1 is uncommon in practice; it means the published empirical literature of 2022–2026 foregrounds Modes 2, 4, and 5. Practitioners may be in Mode 1 far more often than the corpus emphasises.

---

## How to use this framework

1. Run `self_assessment_rubric.md` first and identify your current dominant mode.
2. Read the transition block that moves **from your current mode toward the next step** on the axis you care about — backbone (1 → 2 → 5), visual branch (2 → 3), or evaluative layer (→ 4).
3. Treat the prerequisites as a **readiness checklist**, not a training plan. If three or more prerequisites are missing, the mode transition is likely to fail or regress; address the missing prerequisite before attempting the transition at scale.
4. Re-apply the rubric every 3 months to track movement. Log mode-level drift in the rater's own decision register or workflow journal — it is a leading indicator of team-level capability change.

---

## Notes for reviewers

- **Grounding.** Every prerequisite and blocker is derived from the taxonomy's mode definitions, the Residuals sub-categorisation, or rater decisions logged in `decision_register.csv`. No prerequisite is introduced from outside the corpus evidence.
- **Paraphrase discipline.** No paragraph quotes a raw passage verbatim; the paraphrase linter is expected to exit 0 against this file.
- **Methodology anchor.** This file realises Task 4.3 Goal 2 from `research_plan_sms.md §Phase 4 / Task 4.3`; Cruzes & Dybå (2011) Step 5 (interpretation / "new whole out of the parts"); Petersen et al. (2015) §3 (practical implications of mapping-study outputs).

**Cross-references:**

- `artifacts/synthesis/interaction_taxonomy.md` — mode operational definitions + distinguishing criteria + exemplars.
- `artifacts/synthesis/self_assessment_rubric.md` — per-mode observable indicators for self-identification.
- `artifacts/synthesis/taxonomy_classifications.csv` — partition data (707 labels; 5 modes + Residuals).
- `research_plan_sms.md §Phase 4 Task 4.3` — scope, methodology, DoD.
- `docs/ERP2_Research_Proposal.docx` §3.5 — three-track analysis framework and delegation-depth axis commitment.
