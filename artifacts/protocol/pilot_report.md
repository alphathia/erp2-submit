# Pilot Report — Task 1.6

Methodology: Ali & Petersen (2014) protocol piloting; Petersen 2015 §6 protocol refinement.

**Objective:** Run 2–3 pre-study papers through the screening instrument and extraction schema end-to-end. Document ambiguities. Propose and apply codebook refinements.

**Paper selection criteria:** One clear include, one clear exclude, one borderline (per Task 1.6 spec).

**Pilot paper PDFs stored in:** `artifacts/extraction/fulltext/`

---

## Pilot Paper Selection

| # | Paper | DOI / ID | Expected category | Rationale for selection |
|---|-------|----------|-------------------|----------------------|
| P1 | | | Include | |
| P2 | | | Exclude | |
| P3 | | | Borderline | |

**Selection confirmed by user on:** _(date)_

---

## Paper P1 — Copiloting the future: How generative AI transforms Software Engineering

### Screening walkthrough

| Step | Criterion | Result | Notes |
|------|-----------|--------|-------|
| 1 | IC1 — Published 2022–2026? | YES | |
| 2 | IC3 — Peer-reviewed journal/conference? | YES | |
| 3 | IC4 — Written in English? | YES | |
| 4 | EC4 — Secondary study? | NO | |
| 5 | IC2 — Empirical human-interaction evidence? | YES | |
| 6 | EC1 — Solution Proposal only? | NO | |
| 7 | EC2 — Benchmark without human users? | NO | |
| 8 | EC3 — Outside SE domain? | NO | |
| 9 | IC5/EC5 — ≥4 pages? | YES | |
| 10 | EC6 — Full text retrievable? | YES | |

**Screening decision:** INCLUDE  (The paper passes every inclusion criterion and triggers no exclusion criterion)

**Provisional F1 (Wieringa class):** Evaluation Research

### Extraction (if included)

#### Region 1 — Metadata

| Column | Value |
|--------|-------|
| `paper_id` | 10.1016/j.infsof.2025.107751 |
| `title` | Copiloting the future: How generative AI transforms Software Engineering |
| `authors` | Banh, Leonardo; Holldack, Florian; Strobel, Gero |
| `year` | 2025 |
| `venue` | Information and Software Technology |
| `venue_type` | journal |
| `doi` | https://doi.org/10.1016/j.infsof.2025.107751 |
| `sample_size` | 18 |
| `sample_description` | 18 professionals in SE-related roles (developers, analysts, architects, managers) from finance, energy, consulting, research, and software development sectors; coding experience 1–15 years; job tenure 1–10 years |
| `study_duration` | August 2023 – January 2024 (approx. 6 months data collection) |

#### Region 2 — Facets

| Column | Value | Confidence | Notes |
|--------|-------|------------|-------|
| `f1_contribution_type` | Evaluation Research | High | Investigates GenAI techniques-in-practice via empirical interviews; novelty is in the knowledge claim (grounded framework), not in proposing a tool |
| `f2_research_methodology` | Interview | High | Semi-structured expert interviews with 18 participants; Grounded Theory (Gioia methodology) for analysis |
| `f3_population` | Professional SWE | High | Developers, analysts, architects, managers in SE-related roles; coding experience 1–15 years |
| `f3_context` | Industry | High | Participants from finance, energy, consulting, research, and software development organisations |
| `f4_sdlc_activity` | Coding\|Testing\|Debugging\|Documentation\|Design | Medium | Coding dominant (code generation, completion); testing (test case generation); debugging (error identification); documentation (code docs); design (ideation, planning). Requirements mentioned but not a primary focus of the reported usage evidence |
| `f5_tool_modality` | Conversational\|IDE-Integrated | Medium | ChatGPT used conversationally (natural language prompting); GitHub Copilot used as IDE-integrated autocomplete. Paper discusses both but does not always distinguish which tool participants used for which task |
| `f5_tool_paradigm` | Pro-code | High | Participants are professional SWEs writing Python, Java, etc.; no LCNC usage reported |
| `f5_tool_name` | ChatGPT; GitHub Copilot | High | ChatGPT (16 mentions) and GitHub Copilot (8 mentions); ChatGPT is the primary tool discussed |

#### Region 3 — Synthesis-Register Inputs

| Column | Value |
|--------|-------|
| `raw_passages_file` | `artifacts/extraction/raw_passages/10.1016_j.infsof.2025.107751.md` |
| `capability_annotations_file` | `artifacts/extraction/capability_annotations.csv` (rows where paper_id = 10.1016/j.infsof.2025.107751) |
| `open_codes_tagged` | false |
| `extraction_complete` | false |
| `notes` | Pilot paper P1 (include). Interviews conducted in German, translated to English — verbatim passages in raw_passages file will be from the English translation as published. F5 modality coding is medium confidence because paper often discusses "GenAI" generically without specifying ChatGPT vs Copilot per task. F4 could arguably include Requirements (mentioned in context of ideation) but evidence is thin compared to Coding/Testing/Debugging/Documentation/Design. |

### Ambiguities encountered

| # | Criterion / Column | Ambiguity description | Proposed resolution |
|---|-------------------|----------------------|-------------------|
| 1 | F4 — SDLC Activity | Paper discusses GenAI for "ideation and planning phases" and "requirements analysis" but these are mentioned briefly alongside dominant coding tasks. Unclear if Requirements should be coded as a separate SDLC activity or subsumed under Design. | Code Design (covers ideation/planning); omit Requirements unless the paper devotes substantive discussion to requirements elicitation specifically. Add borderline rule to codebook: "Ideation and high-level planning map to Design unless the paper explicitly discusses requirements specification or elicitation as a distinct activity." |
| 2 | F5 — Tool Modality | Paper studies both ChatGPT (conversational) and GitHub Copilot (IDE-integrated) but often refers to "GenAI" generically without attributing specific tasks to specific tools. Should we code the union of both tools' modalities, or only what is explicitly attributed? | Code the union of modalities for all tools studied (Conversational + IDE-Integrated). Note in extraction notes that attribution is aggregate. If a future paper clearly separates usage per tool, code each tool's row separately per the extraction schema (one study instance per tool if distinct cohorts). |

---

## Paper P2 — Adoption of low-code and no-code development: A systematic literature review and future research agenda

### Screening walkthrough

| Step | Criterion | Result | Notes |
|------|-----------|--------|-------|
| 1 | IC1 — Published 2022–2026? | YES | Published 2025 in Journal of Systems and Software; received May 2023, accepted Nov 2024 |
| 2 | IC3 — Peer-reviewed journal/conference? | YES | Journal of Systems and Software (Elsevier) |
| 3 | IC4 — Written in English? | YES | Full text in English |
| 4 | EC4 — Secondary study? | **YES → EXCLUDE** | "This review is primarily conducted using a multi-phase systematic literature review"; "We identified 40 primary studies"; SLR with search strategy, inclusion/exclusion criteria, and synthesis of existing literature |
| 5 | IC2 | — | Screening stopped at EC4 |
| 6 | EC1 | — | Screening stopped at EC4 |
| 7 | EC2 | — | Screening stopped at EC4 |
| 8 | EC3 | — | Screening stopped at EC4 |
| 9 | IC5/EC5 | — | Screening stopped at EC4 |
| 10 | EC6 | — | Screening stopped at EC4 |

**Screening decision:** EXCLUDE (EC4: secondary study — systematic literature review of 40 primary studies on LCNC adoption)

**Provisional F1 (Wieringa class):** Philosophical (proposes a new conceptual framework for LCNC/CD adoption derived from literature synthesis)

### Extraction (if included)

_Excluded paper — extraction not performed._

Note: This paper is one of the five snowball seeds (see `research_plan_sms.md` §2, seed #5: Ajimati et al. 2025). It is stored in `docs/seeds/` and used for backward snowballing in Task 2.6, but excluded from the primary corpus per EC4.

### Ambiguities encountered

| # | Criterion / Column | Ambiguity description | Proposed resolution |
|---|-------------------|----------------------|-------------------|
| 1 | EC4 — boundary between SLR and empirical study with literature component | This paper is clearly an SLR (40 primary studies reviewed, explicit search strategy and I/E criteria). No ambiguity here. However, future papers may combine a small literature review with primary empirical data (e.g., "we reviewed 10 papers and then interviewed 5 practitioners"). | If a paper combines an SLR component with primary empirical data collection (interviews, surveys, experiments), classify based on the primary contribution. If the empirical component satisfies IC2 (human-interaction evidence), do NOT exclude under EC4. Log as borderline in decision_register.csv. |
| 2 | F1 — Philosophical vs Evaluation Research for SLRs | SLRs synthesise existing work into a new framework. Under Wieringa, this is Philosophical (new conceptual framework). However, some SLRs include quantitative meta-analysis that resembles Evaluation Research. | For pure SLRs with no original empirical data: classify as Philosophical. This is moot for our SMS since EC4 excludes them anyway, but the provisional F1 assignment is useful for consistency when the paper appears in snowball seed lists. |

---

## Paper P3 — A Large-Scale Survey on the Usability of AI Programming Assistants: Successes and Challenges

**Borderline nature:** Title contains "Survey" which initially triggers EC4 uncertainty (literature survey vs questionnaire survey). Resolves to include upon reading the abstract — this is a primary empirical study using a survey questionnaire, not a literature review.

### Screening walkthrough

| Step | Criterion | Result | Notes |
|------|-----------|--------|-------|
| 1 | IC1 — Published 2022–2026? | YES | ICSE 2024 (April 14–20, 2024, Lisbon) |
| 2 | IC3 — Peer-reviewed journal/conference? | YES | ICSE 2024 — top-tier SE conference |
| 3 | IC4 — Written in English? | YES | Full text in English |
| 4 | EC4 — Secondary study? | **NO (BORDERLINE)** | Title says "Survey" but this is a questionnaire-based survey of 410 developers, NOT a literature review. No search strategy, no I/E criteria for papers, no synthesis of existing studies. Primary empirical data collection. |
| 5 | IC2 — Empirical human-interaction evidence? | YES | Survey of 410 developers on their practices and usability challenges with AI programming assistants (Copilot, ChatGPT, Tabnine) |
| 6 | EC1 — Solution Proposal only? | NO | Does not propose a tool; investigates usability of existing tools |
| 7 | EC2 — Benchmark without human users? | NO | 410 human participants; no benchmark evaluation |
| 8 | EC3 — Outside SE domain? | NO | Studies developers using AI tools for software development tasks |
| 9 | IC5/EC5 — ≥4 pages? | YES | 13 pages |
| 10 | EC6 — Full text retrievable? | YES | PDF on disk |

**Screening decision:** INCLUDE (passes all criteria; EC4 borderline resolved to NO upon reading abstract)

**Provisional F1 (Wieringa class):** Evaluation Research (empirical investigation of AI programming assistants in practice via large-scale survey)

### Extraction (if included)

#### Region 1 — Metadata

| Column | Value |
|--------|-------|
| `paper_id` | 10.1145/3597503.3608128 |
| `title` | A Large-Scale Survey on the Usability of AI Programming Assistants: Successes and Challenges |
| `authors` | Liang, Jenny T.; Yang, Chenyang; Myers, Brad A. |
| `year` | 2024 |
| `venue` | ICSE 2024 (46th International Conference on Software Engineering) |
| `venue_type` | conference |
| `doi` | https://doi.org/10.1145/3597503.3608128 |
| `sample_size` | 410 |
| `sample_description` | 410 developers recruited from GitHub repositories related to AI programming assistants; 57 countries; programming experience 1–41 years (median 6 years); includes professional SWEs (n=203), end-user developers (n=82), OSS contributors; mixed gender (man=280, woman=8, non-binary=7) |
| `study_duration` | January 2023 (survey deployment; cross-sectional) |

#### Region 2 — Facets

| Column | Value | Confidence | Notes |
|--------|-------|------------|-------|
| `f1_contribution_type` | Evaluation Research | High | Investigates usability of existing AI tools in practice; no new tool proposed |
| `f2_research_methodology` | Survey | High | Qualtrics questionnaire with closed-ended and open-ended questions; mixed qualitative (thematic coding, Saldana) and quantitative analysis |
| `f3_population` | Mixed | Medium | Primarily Professional SWE (n=203) but also includes end-user developers (n=82) and OSS contributors; recruited from GitHub so skews toward OSS-active developers |
| `f3_context` | Mixed | Medium | Participants work across Industry, OSS, and Education contexts; not restricted to one setting. Survey asks about "a specific project" but doesn't constrain context |
| `f4_sdlc_activity` | Coding\|Documentation\|Debugging | Medium | Coding dominant (autocomplete, code generation, repetitive code, simple logic); documentation (6 participants explicitly); debugging (error identification). "Learning/recalling" is a prominent use case but does not map to a standard SDLC activity |
| `f5_tool_modality` | Autocomplete\|IDE-Integrated\|Conversational | High | Copilot = Autocomplete + IDE-Integrated; ChatGPT = Conversational; Tabnine = Autocomplete + IDE-Integrated; multiple tools studied |
| `f5_tool_paradigm` | Pro-code | High | All participants are programmers recruited from GitHub; Python, JavaScript, TypeScript usage; no LCNC |
| `f5_tool_name` | GitHub Copilot; ChatGPT; Tabnine; CodeWhisperer | High | Copilot most popular (31 mentions); ChatGPT (10); Tabnine (8); CodeWhisperer (2) |

#### Region 3 — Synthesis-Register Inputs

| Column | Value |
|--------|-------|
| `raw_passages_file` | `artifacts/extraction/raw_passages/10.1145_3597503.3608128.md` |
| `capability_annotations_file` | `artifacts/extraction/capability_annotations.csv` (rows where paper_id = 10.1145/3597503.3608128) |
| `open_codes_tagged` | false |
| `extraction_complete` | false |
| `notes` | Pilot paper P3 (borderline → include). Borderline at EC4 due to "Survey" in title; resolved as primary questionnaire study. F3 population is Mixed because participants span professional SWEs, end-user developers, and OSS contributors — codebook may need a rule for how to handle GitHub-recruited samples that cross population categories. "Learning/recalling" is a frequently reported use case (19 participants) that doesn't map to any F4 SDLC activity — consider whether to add a note or treat as supplementary to Coding. |

### Ambiguities encountered

| # | Criterion / Column | Ambiguity description | Proposed resolution |
|---|-------------------|----------------------|-------------------|
| 1 | EC4 — "Survey" in title | Title contains "Survey" which could trigger EC4 (secondary study). Upon reading, this is a questionnaire-based survey (primary empirical method), not a literature survey. | Add codebook borderline rule: "A paper titled 'survey' or 'study' requires reading the abstract to distinguish between a literature survey (EC4 exclude) and a survey questionnaire (primary method, IC2 qualifying). Key discriminators: literature surveys describe search strategies and paper selection; questionnaire surveys describe participant recruitment and data collection instruments." |
| 2 | F3 — GitHub-recruited mixed population | Participants include professional SWEs (n=203), end-user developers (n=82), and others. The codebook's F3 population values (Professional SWE, Student, Citizen Developer, OSS Contributor, Mixed) may not cleanly cover "end-user developer." | Code as Mixed when participants span multiple population categories. "End-user developer" maps closest to Professional SWE or OSS Contributor depending on context. If a paper's sample is predominantly one category (>80%), code that category; otherwise code Mixed with a note listing constituent groups. |
| 3 | F4 — "Learning/recalling" as SDLC activity | 19 participants reported using AI tools to learn new APIs or recall syntax. This is a prominent use case that doesn't map to any F4 SDLC activity. | Do not add a new F4 value — "learning" is a developer activity, not an SDLC phase. Code the underlying task: if they learn in order to write code, it's Coding; if they learn to debug, it's Debugging. Note the learning aspect in extraction notes. |

---

## Summary of Ambiguities

| # | Source | Criterion / Column | Ambiguity | Resolution |  Codebook change needed? |
|---|--------|-------------------|-----------|------------|----------------------|
| 1 | P1 | F4 — SDLC Activity | "Ideation and planning" vs Requirements vs Design | Code Design; Requirements only if explicitly about specification/elicitation | YES |
| 2 | P1 | F5 — Tool Modality | Paper uses "GenAI" generically for multiple tools | Code union of all tools' modalities; note aggregate attribution | YES |
| 3 | P2 | EC4 — SLR + empirical hybrid | Future papers may combine SLR with primary data | If empirical component satisfies IC2, do not exclude under EC4 | YES |
| 4 | P2 | F1 — SLR classification | Philosophical vs Evaluation Research for SLRs | Pure SLRs → Philosophical; moot since EC4 excludes | NO |
| 5 | P3 | EC4 — "Survey" in title | Literature survey vs questionnaire survey | Discriminate by abstract: search strategy = EC4; participant recruitment = IC2 | YES |
| 6 | P3 | F3 — Mixed population | GitHub-recruited samples span categories; "end-user developer" not in codebook | Code Mixed if no category ≥80%; map "end-user developer" to closest match | YES |
| 7 | P3 | F4 — Learning/recalling | Prominent use case not mapping to SDLC activity | Code the underlying task (learning to code → Coding); do not add new F4 value | YES |

## Proposed Codebook Refinements

| # | Facet | Current wording | Proposed change | Rationale | User approved? |
|---|-------|----------------|-----------------|-----------|---------------|
| 1 | F2 — Research Methodology | Borderline rule only addresses mixed methods and supplementary benchmarks | **Add to borderline rule:** "The value 'Survey' refers to a questionnaire or instrument administered to human participants. A paper titled 'survey' that reviews existing literature (search strategy, paper selection criteria) is a literature review — exclude under EC4, not coded under F2." | P2 and P3 both involved "survey" ambiguity. The F2 value "Survey" needs explicit disambiguation from literature surveys to prevent miscoding. This aligns with Ali & Petersen's screening discipline. | YES |
| 2 | F3 — Population & Context | Borderline rule: "If a paper studies both professional developers and students in separate cohorts, code as Mixed" | **Expand borderline rule to:** "Code as Mixed when participants span multiple population categories. If one category comprises ≥80% of the sample, code that dominant category and note the minority group. Map 'end-user developer' to Professional SWE (if employed) or Citizen Developer (if non-technical). For GitHub-recruited samples where roles are self-reported, use the reported distribution." | P3 had 410 participants spanning Professional SWE (203), end-user developers (82), and others. Current rule doesn't address threshold for Mixed vs dominant category, or how to map "end-user developer." RQ1 explicitly covers SWE, students, and citizen developers — the codebook should guide clean mapping. | YES |
| 3 | F4 — SDLC Activity | Borderline rule: "If the tool is used for an activity that spans two values, code both and note the overlap" | **Add to borderline rule:** "(a) Ideation and high-level planning map to Design unless the paper explicitly discusses requirements specification or elicitation as a distinct activity. (b) Developer activities that are not SDLC phases (e.g., learning APIs, recalling syntax, brainstorming) should be coded under the SDLC activity they support — if a developer uses AI to learn in order to write code, code Coding. Do not add learning/recalling as a new F4 value." | P1 had Design/Requirements ambiguity; P3 had learning/recalling as a prominent use case. The proposal's RQ1 maps evidence across "SE activities" — these borderline rules ensure consistent SDLC coding without inflating the value set. | YES |
| 4 | F5 — Agent/Tool Profile | Borderline rule only addresses multi-select modality and paradigm coding based on actual usage | **Add to borderline rule:** "When a paper studies multiple tools but discusses them generically (e.g., 'GenAI tools' or 'AI programming assistants'), code the union of all studied tools' modalities. Record all tool names in `f5_tool_name` and add a note that attribution is aggregate. If the paper reports distinct usage patterns per tool (e.g., separate sections or cohorts for Copilot vs ChatGPT), code each tool as a separate study instance row in the extraction matrix." | P1 frequently referred to "GenAI" without distinguishing ChatGPT from Copilot. The proposal notes that tool coverage is fragmented — distinguishing per-tool evidence where possible is critical for RQ1's landscape mapping and RQ3's gap analysis by tool profile. | YES |
| 5 | Screening (EC4) | Not currently in codebook — EC4 rule is in inclusion_exclusion.md only | **Add a new "Screening Notes" section at the top of the codebook:** "EC4 discrimination: A paper containing 'survey', 'review', or 'study' in its title requires reading the abstract to classify. Key discriminators: (a) Literature survey/SLR — describes a search strategy, database selection, and paper-level inclusion/exclusion criteria → exclude under EC4. (b) Questionnaire survey — describes participant recruitment, a survey instrument, and human responses → primary empirical study, code under F2 as Survey. (c) Hybrid — combines SLR with primary data collection. If the empirical component satisfies IC2 (human-interaction evidence), do NOT exclude under EC4; classify based on the primary contribution and log in decision_register.csv." | P2 (clear SLR) and P3 (clear questionnaire) both triggered EC4 consideration. The proposal acknowledges that secondary studies are snowball seeds, not primary corpus — the codebook should guide this decision consistently. | YES |

---

## LCNC Capability Assessment

Per decision register entry `retain_procode_capabilities_defer_lcnc` (2026-04-12), at least one LCNC-relevant paper should be tested during the pilot. If the 19 capability IDs do not adequately cover the paper's capabilities, propose new LCNC-specific IDs here.

**LCNC paper tested:** P2 (Ajimati et al. 2025) — an SLR on LCNC adoption. Excluded under EC4 before extraction, so capability mapping could not be tested against a primary LCNC study. The decision register entry stands: defer full LCNC capability assessment until a primary LCNC usage study enters the corpus during Phase 2 screening.

**Capability mapping issues:**

| Capability observed | Closest existing ID | Fit? | Proposed new ID (if needed) |
|--------------------|--------------------|------|---------------------------|
| N/A — P2 excluded under EC4 | N/A | N/A | Deferred to Phase 2/3 |

**Conclusion:** Assessment deferred. No primary LCNC usage paper was available in the pilot set. The decision register entry `retain_procode_capabilities_defer_lcnc` remains active.

---

## DoD Checklist

- [x] ≥1 paper categorised as **include** (P1 Banh et al., P3 Liang et al.)
- [x] ≥1 paper categorised as **exclude** (P2 Ajimati et al. — EC4)
- [x] ≥1 paper categorised as **borderline** (P3 Liang et al. — EC4 borderline → include)
- [x] ≥1 codebook refinement committed (5 refinements applied)
- [x] All ambiguities documented with resolutions (7 ambiguities across 3 papers)
- [x] `codebook.md` updated post-pilot
- [ ] `decision_register.csv` updated with any judgement calls
- [ ] `memory.md` updated
