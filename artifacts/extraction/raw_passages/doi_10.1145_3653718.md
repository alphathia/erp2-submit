# Raw Passages — doi:10.1145/3653718


## P001

- **Section:** 1 INTRODUCTION

- **Relevance:** interaction_mode

- **Text:**

> Llm4sa works by inspecting both the bug reports and their corresponding code snippets through querying LLMs, which explain the code snippets, reason about the reported warnings, and make a decision on whether a warning is a false positive based on expertise.


## P002

- **Section:** 2.3 A Desired LLMs-powered Static Analysis Pipeline

- **Relevance:** capability_claim

- **Text:**

> Llm4sa provides a more practical and intuitive method for examining bug warnings, effectively substituting human involvement in the process.


## P003

- **Section:** 3.3 Code Snippet Extraction Based on Program Dependency Analysis

- **Relevance:** capability_claim

- **Text:**

> Llm4sa derives only bug-related code snippets that are enriched with the necessary calling contexts. To achieve this, Llm4sa extracts code snippets related to bugs from the analyzed program by combining bug reports and the traversal of the program dependency graph.


## P004

- **Section:** 5.6 Overhead Analysis (RQ5)

- **Relevance:** benefit

- **Text:**

> On average, Llm4sa is capable of automatically inspecting bug warnings in less than 30 seconds per warning, as shown in Table 8, which is substantially faster than a human engineer.
