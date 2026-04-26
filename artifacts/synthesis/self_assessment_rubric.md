# Self-Assessment Rubric — AI-Assisted Software Engineering Practitioner

> **Purpose.** Maps each interaction mode from `interaction_taxonomy.md` to observable practitioner indicators. Use this rubric to self-identify the mode that best describes your current dominant pattern of interaction with AI coding agents, and then consult `adoption_progression.md` for what moving deeper along the delegation-depth axis looks like.
> **Scope.** Modes 1–5 of the interaction-mode taxonomy (RQ2 deliverable, Phase 4). Residuals (outcomes / affordances / constraints / meta-observations) are cross-cutting and are summarised at the end rather than treated as a mode.
> **Companion documents.** `interaction_taxonomy.md` (operational definitions + distinguishing criteria); `adoption_progression.md` (transition prerequisites along delegation depth).
> **Rater:** TBS  **Generated:** 2026-04-19

---

## How to use this rubric

1. Read every mode's `Dominant signal` line — the one-sentence behavioural summary.
2. Walk the **Practitioner indicators** checklist for each mode and tick every indicator that honestly describes your current workflow with AI coding tools in the last 30 days. Do not count intentions or aspirations — only observed behaviour.
3. Read the **You are NOT in this mode if** line and drop the mode if any exclusion fires.
4. Identify the **highest-numbered mode** for which you tick at least three indicators AND no exclusion fires. That is your current dominant mode. If you tick three or more indicators in more than one mode, your practice is mixed — use `adoption_progression.md §Non-linearity note` to interpret the overlap.

The rubric is deliberately conservative: the absence of ticks in a higher-numbered mode does not imply deficiency, and the presence of ticks in a higher-numbered mode does not imply skipping the lower ones. The delegation-depth axis is ordinal, not cumulative — see `interaction_taxonomy.md §Axis`.

---

## Mode 1 — Inline Completion

**Dominant signal.** You let the assistant finish the line you are currently typing; the AI never drives a multi-step action without you authoring the next keystroke.

**Practitioner indicators (self-check):**
- [ ] I use an editor extension that displays AI-proposed continuations inline at the cursor (greyed-out text, tab-to-accept, or equivalent).
- [ ] The unit of AI interaction in my workflow is the **single suggestion**: I accept, modify, or reject each one as it appears.
- [ ] Proposals appear continuously as I type and disappear if I keep typing past them; I do not have to compose a prompt to invoke them.
- [ ] Most AI-assisted time I spend is *in the editor*, not in a separate chat window.
- [ ] I do not normally read a long natural-language response before taking action — the AI's output is code, not prose. [Rater Review — this indicator should screen out Mode 2; confirm it is specific enough]
- [ ] I rarely ask the AI to explain itself or to take a multi-step action. When I do, I switch to a different tool / surface. [Rater Review]

**Tooling typically observed.** IDE autocomplete-style surfaces (GitHub Copilot in-editor, JetBrains AI Assistant inline suggestions, Codeium, similar). [Rater Review — tooling list is non-exhaustive; confirm no Singapore-context local tools are missed.]

**You are NOT in this mode if:** your dominant AI interaction is a chat-style back-and-forth (that is Mode 2), OR if the AI typically completes multi-step tasks that span files and checkpoints (that is Mode 5).

---

## Mode 2 — Conversational Prompting

**Dominant signal.** You describe what you want in natural language, the AI responds, and you iterate across several turns until the output is usable.

**Practitioner indicators (self-check):**
- [ ] I routinely hold a dialogue with the AI — a chat window, in-IDE side panel, or equivalent conversational surface — rather than relying solely on inline completion.
- [ ] The unit of AI interaction in my workflow is the **prompt-response turn**: one question, one multi-line response, then I decide whether to re-prompt.
- [ ] I refine my prompts across turns (adding constraints, correcting misunderstandings, supplying missing context) rather than accepting the first response as final.
- [ ] I sometimes paste code fragments, error messages, or stack traces into the chat and ask for explanation or fixes.
- [ ] A single usable outcome routinely takes **two or more turns** with the AI.
- [ ] I rely on the conversation's own running context more than on external project-wide context (the AI usually does not have autonomous access to my entire repository). [Rater Review — "autonomous access" boundary depends on the specific tool used; confirm]

**Tooling typically observed.** ChatGPT, Claude, Gemini chat interfaces; IDE-integrated chat panels (GitHub Copilot Chat, Cursor chat, JetBrains AI chat); command-line LLM chat clients. [Rater Review]

**You are NOT in this mode if:** your dominant interaction is inline accept / reject without a separate turn (that is Mode 1), OR if you compose software primarily by arranging visual or declarative elements (that is Mode 3), OR if the AI routinely executes a scoped task end-to-end before you look at the result (that is Mode 5).

---

## Mode 3 — Visual / Declarative Composition

**Dominant signal.** You compose software by arranging structural elements — visual blocks, workflow nodes, configuration forms, or a declarative specification — and the AI fills in the underlying implementation.

**Practitioner indicators (self-check):**
- [ ] My primary authoring surface for at least some AI-assisted work is **visual or declarative**, not a code editor or a chat window: drag-and-drop blocks, flow-chart nodes, form fields, or schema-driven specs.
- [ ] The AI's role is to translate the visual/declarative specification into running implementation (logic, data models, workflow steps, or code behind the visuals).
- [ ] I produce and edit **artefacts in the visual surface** (a workflow, a form, a spec) rather than producing and editing free-text prompts.
- [ ] When I want to change behaviour, I edit the structural element, not a prompt. [Rater Review — this indicator is the key discriminator from Mode 2]
- [ ] I recognise my tooling in categories like low-code, no-code, visual AI platforms, workflow builders, or natural-language-to-workflow pipelines. [Rater Review — phrasing avoids proprietary tool names that may not apply to this rater's context]

**Tooling typically observed.** Low-code / no-code platforms with AI augmentation (Zapier AI, Make, Power Automate with Copilot); AI-augmented BPMN tools; visual-analytics prompt composers (PromptAid-class tools); configuration-driven agentic workflow builders. [Rater Review]

**You are NOT in this mode if:** your primary surface is free-text prompts in a chat (that is Mode 2), OR if you author code directly in an editor and accept AI continuations inline (that is Mode 1).

---

## Mode 4 — Review & Validation

**Dominant signal.** Your primary AI-assisted work product is an **evaluative judgement** — of code, of AI output, or of the interaction itself — rather than newly generated code.

**Practitioner indicators (self-check):**
- [ ] I regularly use AI to review, critique, or assess code or AI-generated artefacts — looking for defects, hallucinations, quality issues, security concerns, or miscalibration.
- [ ] The unit of AI interaction in my workflow is the **evaluative decision**: pass / fail / needs-rework, or a scored rubric judgement.
- [ ] I either (a) ask AI to evaluate *my* code or (b) evaluate the AI's code as the primary work product. Both are Mode 4.
- [ ] I can articulate *what quality means* for the artefact under review — correctness, maintainability, security, alignment with a spec — before the review starts. [Rater Review]
- [ ] I routinely reject AI output when it fails quality criteria, rather than accepting it by default.
- [ ] Trust calibration — deciding how much to trust a given AI output — is an explicit part of my workflow. [Rater Review — this indicator surfaces the Task 3 spot-check lineage; confirm it is observable for a typical practitioner]

**Tooling typically observed.** AI code-review assistants (CodeRabbit, GitHub Copilot Code Review, diff-reviewing LLMs), AI-augmented linters, AI-based test oracle tooling, hallucination detectors for code-generation outputs. [Rater Review]

**You are NOT in this mode if:** your dominant work product is newly generated code (that is Modes 1, 2, or 5). Mode 4 *coexists* with 1/2/5 rather than replacing them; see `adoption_progression.md §Non-linearity note`.

---

## Mode 5 — Delegated Task Execution

**Dominant signal.** You scope a task — generate a test suite, fix a bug, refactor a module, build a workflow — and the AI executes it end-to-end or across multiple sub-steps, with you reviewing at checkpoints or at completion rather than turn-by-turn.

**Practitioner indicators (self-check):**
- [ ] I routinely hand the AI a **task**, not a prompt — something with a beginning, middle, and end across multiple files or multiple steps.
- [ ] The unit of AI interaction in my workflow is the **task**: one scope specification, one (or few) checkpoint reviews, one completion gate.
- [ ] I review the AI's output **after** several steps have been taken, not **between** each step.
- [ ] The AI in my workflow can read, edit, and run code across my project without me orchestrating each action by hand.
- [ ] I define success criteria up front (tests pass, behaviour matches spec, refactor preserves interfaces) and let the AI iterate against them.
- [ ] I have experience with agentic tooling that runs for minutes-to-hours on a single scoped task. [Rater Review — "minutes-to-hours" threshold is from the exemplar passages; confirm it matches the practitioner reality the rater has observed in the corpus]

**Tooling typically observed.** Agentic SE tools (Devin, Claude Code agents, Cursor agent mode, Aider, GitHub Copilot agent mode), SWE-bench-class evaluation frameworks, automated test-suite-synthesis agents (Botender-class), autonomous bug-triage frameworks. [Rater Review]

**You are NOT in this mode if:** your dominant interaction is single-turn prompt-response (Mode 2) or token-level suggestion (Mode 1). Periodic delegation of *a* task is not enough to count — the pattern must be recurring.

---

## Cross-cutting considerations (Residuals)

The interaction-mode taxonomy carries a large Residuals / Cross-Cutting section (468 of 707 canonical labels; 66.2% of the partition — see `interaction_taxonomy.md §Residuals`). These labels describe:

- **Outcomes** — productivity gains, accuracy shifts, satisfaction, velocity (192 labels).
- **Affordances / surfaces** — IDE integration, toolchain depth, workflow embedding (56 labels).
- **Constraints** — context-window limits, cognitive load, processing lag, skill gaps (119 labels).
- **Meta-observations** — adoption drivers and inhibitors, research framings (101 labels).

These are not modes but they shape experience **inside every mode**. When applying this rubric, notice whether your practice is being shaped by a constraint (e.g. a limited context window pushing you from Mode 5 back to Mode 2) or by an affordance (e.g. a deep IDE integration enabling Mode 1 in your current tool). Residuals influence *which* mode you sit in today; they do not redefine the modes.

[Rater Review — whether to elevate any specific Residual sub-category to a self-assessment dimension (e.g. a separate "cognitive-load fit" sub-score) is a Task 4.3 open question; current draft treats Residuals as background rather than foreground.]

---

## Self-assessment procedure (at a glance)

1. **Tick all indicators that apply**, across all five modes.
2. For each mode, count the ticks; mark whether any exclusion clause fires.
3. Your **current dominant mode** = the highest-numbered mode with ≥3 ticks AND no exclusion firing.
4. If the dominant mode is unclear (ties or mixed signal), consult `adoption_progression.md` to interpret the overlap — Modes 3 and 4 often coexist with 2 or 5 rather than replacing them.
5. Record your result and the date; re-apply the rubric every 3 months to track drift along the delegation-depth axis.

---

## Notes for reviewers

- **Grounding.** Every indicator is derived from the `**Distinguishing criteria:**` IS / IS-NOT lines of the corresponding mode in `interaction_taxonomy.md`, rephrased to be observable at practitioner level.
- **Paraphrase discipline.** No indicator quotes a raw passage verbatim; the paraphrase linter is expected to exit 0 against this file.
- **Open [Rater Review] items.** Tooling lists, "typical" framings, and the cognitive-load-as-Residual dimension all carry explicit review markers.
- **Methodology anchor.** This file realises Task 4.3 Goal 1 from `research_plan_sms.md §Phase 4 / Task 4.3` and Cruzes & Dybå (2011) Step 5 (interpretation: "making a new whole out of the parts").

**Cross-references:**

- `artifacts/synthesis/interaction_taxonomy.md` — mode operational definitions + distinguishing criteria + exemplars.
- `artifacts/synthesis/adoption_progression.md` — transition prerequisites along delegation depth.
- `research_plan_sms.md §Phase 4 Task 4.3` — scope, methodology, DoD.
- `docs/ERP2_Research_Proposal.docx` §3.5 — three-track analysis framework (RQ1 frequency, RQ2 taxonomy, RQ3 gap matrix).
