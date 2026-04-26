# Five-Facet Codebook

Source: `docs/ERP2_Research_Proposal.docx` §3.4, Table 2. Methodology: Petersen et al. (2008, 2015) for facet-based classification; Wieringa et al. (2006) for F1; Cruzes & Dybå (2011, 2015) for extraction/synthesis separation.

**Note:** Interaction Mode (RQ2) and Capability Category (RQ3) are **not** extraction facets. They are synthesis-layer outputs derived downstream per Cruzes & Dybå. See `research_plan_sms.md` Tasks 4.1–4.2 and 1.4/5.2 respectively.

Exemplars below are drawn from the proposal's cited papers as a pre-study illustration. Borderline rules were refined post-pilot (Task 1.6).

---

## Screening Notes (added post-pilot)

**EC4 discrimination — "survey" / "review" / "study" in title:**
A paper containing these words in its title requires reading the abstract to classify:
- **(a) Literature survey / SLR** — describes a search strategy, database selection, and paper-level inclusion/exclusion criteria → **exclude under EC4**. Route to snowball seed list.
- **(b) Questionnaire survey** — describes participant recruitment, a survey instrument, and human responses → **primary empirical study**. Code under F2 as Survey. Do not exclude.
- **(c) Hybrid** — combines SLR with primary data collection (e.g., "we reviewed 10 papers and interviewed 5 practitioners"). If the empirical component satisfies IC2 (human-interaction evidence), do **NOT** exclude under EC4. Classify based on the primary contribution and log in `decision_register.csv`.

---

## F1 — Contribution Type

**Definition:** Classifies the paper's primary research contribution using Wieringa et al.'s (2006) six mutually exclusive classes, as defined in their §3.

**Controlled values (verbatim from Wieringa et al., 2006):**

| Value | Operational definition |
|-------|----------------------|
| Evaluation Research | Investigation of a problem in practice or an implementation of a technique in practice. Novelty of the knowledge claim and soundness of the research method are the evaluation criteria, not novelty of the technique. |
| Validation Research | Investigation of the properties of a solution proposal not yet implemented in practice. Uses methodologically sound research setup (experiments, simulation, prototyping, mathematical analysis, etc.). |
| Solution Proposal | Proposes a novel technique and argues for its relevance without full-blown validation. A proof-of-concept may be offered via a small example or sound argument. |
| Philosophical | Sketches a new way of looking at things — a new conceptual framework. Evaluated on originality, soundness, and insightfulness. |
| Opinion | Expresses the author's opinion about what is wrong or good, how things should be done, etc. No new research results, designs, or frameworks. |
| Personal Experience | Describes the author's personal experience using a particular technique. Not a scientific experiment. Evidence may be anecdotal. |

**Positive exemplars:**
1. Yu (2025) reports a field study of developer coding productivity with GenAI tools → **Evaluation Research** (investigates technique-in-practice).
2. Geng et al. (2026) explore student-AI interactions in vibe coding via qualitative study → **Evaluation Research** (empirical investigation of practice).

**Negative exemplars:**
1. Wang et al. (2025) SWE-Dev proposes an agent training approach with SWE-bench evaluation → **Solution Proposal** (proposes technique + lab validation, no usage in practice; excluded by EC1).
2. Treude & Gerosa (2025) propose a taxonomy of human-AI collaboration → **Philosophical** (new conceptual framework, not empirical usage evidence; would need to check if any empirical component exists).

**Borderline rule:** A paper may span multiple classes (Wieringa §3 acknowledges this). Code the **primary** contribution. If a paper proposes a tool (Solution Proposal) but also includes a user study (Evaluation Research), assign based on where the paper's emphasis lies. If the empirical component is substantial and reports usage evidence (IC2), classify as Evaluation Research and include. Log the decision in `decision_register.csv` citing Wieringa's definitions.

**Operational threshold for "primary contribution" (post-Task 2.5 refinement):**
- **F1 = Evaluation Research** if ALL of the following hold: (a) dedicated empirical section (labelled "Study", "Evaluation", "Empirical", "User Study", or equivalent), AND (b) N ≥ 5 human participants are reported, AND (c) paper reports usage findings beyond tool correctness (e.g., user perceptions, workflows, errors, productivity).
- **F1 = Solution Proposal** if tool description dominates and user study is limited to a brief example or demo with <5 participants (or no participant count).
- **F1 = Validation Research** if benchmark evaluation (HumanEval, SWE-bench, MBPP, etc.) is the primary contribution, even when a small optional user survey is included.
- For excluded papers, F1 is still recorded where identifiable (EC1 exclusions → Solution Proposal by definition; EC2 exclusions → Validation Research by definition).

---

## F2 — Research Methodology

**Definition:** Identifies the empirical research method used to collect and analyse the human-interaction evidence reported in the paper.

**Controlled values:**

| Value | Operational definition |
|-------|----------------------|
| Survey | Structured or semi-structured questionnaire administered to a sample population. |
| Interview | Qualitative data collection through one-on-one or group interviews. |
| Case Study | In-depth investigation of a phenomenon within its real-world context, typically one or a small number of sites. |
| Experiment | Controlled study with treatment and control groups, either in lab or field setting. |
| Field Study | Observational study of practice without controlled intervention. |
| Mining Study | Analysis of software repositories, logs, telemetry, or other digital trace data. |
| Mixed | Paper explicitly combines two or more of the above methods. |

**Positive exemplars:**
1. Kumar et al. (2025) analyse telemetry from developer-agent collaborations at scale → **Mining Study**.
2. Geng et al. (2026) conduct think-aloud sessions with students using AI tools → **Interview** (qualitative data from participant sessions).

**Negative exemplars:**
1. A paper that runs a benchmark suite on an agent with no human participants → not a research methodology for this SMS (no human-interaction evidence; excluded by EC2).
2. A paper that surveys related work and proposes a framework → not empirical; the "survey" here is a literature review, not a Survey research method.

**Borderline rule:** If a paper uses multiple methods (e.g., survey + interviews), code as **Mixed** and note the component methods in the extraction form's notes column. If only one method produces the human-interaction evidence while the other is supplementary (e.g., benchmark + small user survey), code the method that generates the IC2-qualifying evidence. **Note:** The value "Survey" refers to a questionnaire or instrument administered to human participants. A paper titled "survey" that reviews existing literature (search strategy, paper selection criteria) is a literature review — exclude under EC4, not coded under F2. See Screening Notes above.

---

## F3 — Population & Context

**Definition:** Identifies who the study participants are and in what setting the study was conducted.

**Controlled values (composite — one from each axis):**

Population axis:
| Value | Operational definition |
|-------|----------------------|
| Professional SWE | Employed software engineers, developers, or DevOps practitioners. |
| Student | Undergraduate or graduate students in computing or related fields. |
| Citizen Developer | Non-professional developers using low-code/no-code platforms (business analysts, domain experts, etc.). |
| OSS Contributor | Open-source contributors identified through repository activity. |
| Mixed | Study explicitly includes participants from more than one population category. |
| N/A | Paper has no human participants (dataset-only, benchmark-based, or mining of artifacts without human subjects). Do NOT infer a population from the data source (e.g., mining GitHub ≠ `OSS Contributor`). |

Context axis:
| Value | Operational definition |
|-------|----------------------|
| Industry | Corporate or organisational setting. |
| Education | University course, bootcamp, or structured learning environment. |
| OSS | Open-source project or community. |
| Lab | Controlled laboratory or experimental setting. |
| N/A | No human study setting (paired with `f3_population = N/A`). |

**Positive exemplars:**
1. Geng et al. (2026) study students in a university course using AI tools → **Student × Education**.
2. Kumar et al. (2025) analyse developer-agent interactions from industry telemetry → **Professional SWE × Industry**.

**Negative exemplars:**
1. A paper studying GPT-4's code generation performance on HumanEval with no human participants → no population to code (excluded by EC2).
2. Kesavareddi (2026) describes Power Platform CRM transformations — if the participants are business users configuring workflows rather than professional SWEs, code as **Citizen Developer × Industry**, not Professional SWE.

**Borderline rule:** Code as **Mixed** when participants span multiple population categories. If one category comprises ≥80% of the sample, code that dominant category and note the minority group in extraction notes. Map "end-user developer" to **Professional SWE** (if employed in an SE role) or **Citizen Developer** (if non-technical/business user). For GitHub-recruited samples where roles are self-reported, use the reported distribution to determine the dominant category. If the context is ambiguous (e.g., a company hackathon with students), code the primary setting and log the rationale in `decision_register.csv`.

---

## F4 — SDLC Activity

**Definition:** Identifies which software development lifecycle activity the AI tool is used for in the reported study.

**Controlled values:**

| Value | Operational definition |
|-------|----------------------|
| Requirements | Elicitation, specification, or management of requirements. |
| Design | System or software architecture and design decisions. |
| Coding | Writing, generating, or completing source code. |
| Testing | Test case generation, test execution, or test-related activities. |
| Code Review | Reviewing, commenting on, or approving code changes. |
| Debugging | Identifying, localising, or fixing defects. |
| CI/CD | Continuous integration, continuous deployment, build pipelines. |
| Documentation | Generating or maintaining technical documentation. |
| Project Management | Planning, estimation, task tracking, or workflow coordination. |

Multi-select: a single paper may report usage across multiple SDLC activities.

**Positive exemplars:**
1. Yu (2025) studies coding productivity with GenAI → **Coding**.
2. A paper studying how developers use Copilot to write and debug code → **Coding + Debugging** (multi-select).

**Negative exemplars:**
1. A paper about using ChatGPT for general Q&A unrelated to a software project → does not map to any SDLC activity (excluded by EC3 if outside SE domain).
2. A paper about AI-generated marketing content using a low-code platform → not an SDLC activity unless the platform is building software artifacts.

**Borderline rule:** If the tool is used for an activity that spans two values (e.g., "AI-assisted code review that also catches bugs"), code both **Code Review** and **Debugging** and note the overlap. If the SDLC activity is not clearly stated, infer from the described task and log the inference in `decision_register.csv`. **Additional rules (post-pilot):** (a) Ideation and high-level planning map to **Design** unless the paper explicitly discusses requirements specification or elicitation as a distinct activity. (b) Developer activities that are not SDLC phases (e.g., learning APIs, recalling syntax, brainstorming) should be coded under the SDLC activity they support — if a developer uses AI to learn in order to write code, code **Coding**. Do not add learning/recalling as a new F4 value.

---

## F5 — Agent/Tool Profile

**Definition:** Classifies the AI tool or agent studied in the paper along two independent sub-facets: interaction modality and development paradigm.

**Controlled values (composite — multi-select on sub-facet A, single-select on sub-facet B):**

Sub-facet A — Interaction modality (multi-select):
| Value | Operational definition |
|-------|----------------------|
| Autocomplete | Inline code suggestions triggered by cursor position or partial input (e.g., GitHub Copilot tab-completion). |
| Conversational | Natural-language dialogue interface for code generation, explanation, or planning (e.g., ChatGPT, Claude chat). |
| IDE-Integrated | Tool embedded within an IDE providing contextual assistance beyond autocomplete (e.g., Cursor, Windsurf). |
| Autonomous | Agent that independently executes multi-step tasks with minimal human intervention (e.g., Devin, SWE-Agent). |

Sub-facet B — Development paradigm (single-select):
| Value | Operational definition |
|-------|----------------------|
| Pro-code | Traditional programming with source code (Python, Java, etc.). |
| Low-code | Visual development with some code customisation (e.g., Power Platform, OutSystems). |
| No-code | Fully visual or declarative development with no source code (e.g., AppSheet, n8n). |

**Positive exemplars:**
1. A study of GitHub Copilot in VS Code for Python development → **Autocomplete + IDE-Integrated × Pro-code**.
2. Kesavareddi (2026) studying Power Platform CRM with Copilot → **Conversational × Low-code**.

**Negative exemplars:**
1. A study of ChatGPT used in a web browser to answer general coding questions (not embedded in IDE) → **Conversational × Pro-code** only, not IDE-Integrated — the tool must be embedded in the IDE to qualify.
2. Cursor spans Autocomplete + Conversational + IDE-Integrated (all three sub-facet A values legitimately apply) — this is correct multi-select behaviour, not an error.

**Borderline rule:** If a tool legitimately spans multiple sub-facet A values (e.g., Cursor offers autocomplete, chat, and IDE integration), tag all that apply. For sub-facet B, if a platform supports both low-code and pro-code modes (e.g., Power Platform with custom connectors), code based on how participants **actually used** the tool in the study, not the tool's full capability. Log ambiguous cases in `decision_register.csv`. **Additional rule (post-pilot):** When a paper studies multiple tools but discusses them generically (e.g., "GenAI tools" or "AI programming assistants"), code the union of all studied tools' modalities. Record all tool names in `f5_tool_name` and add a note that attribution is aggregate. If the paper reports distinct usage patterns per tool (e.g., separate sections or cohorts for Copilot vs ChatGPT), code each tool as a separate study instance row in the extraction matrix.
