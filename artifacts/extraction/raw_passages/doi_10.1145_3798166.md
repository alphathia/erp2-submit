# Raw Passages — doi:10.1145/3798166


## P001

- **Section:** 1 Introduction

- **Relevance:** capability_claim

- **Text:**

> Agentic coding, defined as the use of autonomous AI agents to generate, modify, and submit code, has emerged as a transformative paradigm in software engineering. This approach is enabled by large language models (LLMs), and several agentic coding tools have recently been introduced, including Claude Code... agentic coding enables AI agents to autonomously plan, execute, test, and iterate on development tasks with minimal human intervention.


## P002

- **Section:** 1 Introduction

- **Relevance:** usage_pattern

- **Text:**

> Our findings indicate that both Agentic-PRs and Human-PRs fix bugs and add features, but Agentic-PRs focus on non-functional improvements (tests, refactoring, documentation) while Human-PRs handle project maintenance (CI, chores).


## P003

- **Section:** 4.2 RQ2: To what extent are Agentic-PRs rejected and why?

- **Relevance:** challenge

- **Text:**

> The most common reasons for Agentic-PRs rejections stem from project evolution and PR complexity, not just code quality. Table 3 shows that alternative solutions (12.0%), obsolescence (3.3%), and oversized PRs (3.3%) frequently result in Agentic-PRs rejections, reflecting project evolution and maintainability concerns.


## P004

- **Section:** 4.3 RQ3: What proportion of Agentic-PRs are accepted without revisions? If needed, to what extent?

- **Relevance:** benefit

- **Text:**

> The majority of both Agentic-PRs and Human-PRs are merged without revision. Among merged PRs, we observe that 54.9% of APRs (261 PRs) are merged as-is with a single commit, as compared to 58.5% (302 PRs) of HPRs.


## P005

- **Section:** 4.4 RQ4: What changes are required to revise Agentic-PRs?

- **Relevance:** challenge

- **Text:**

> Addressing documentation gaps constitutes the second largest focus (29.0%) of Agentic-PRs revisions. Documentation updates were present in 29.0% (62 out of 214) of revisions, as shown in Table 4. Although agents sometimes generated or updated code comments, they often failed to synchronize all relevant artifacts.
