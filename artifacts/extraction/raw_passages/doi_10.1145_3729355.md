# Raw Passages — doi:10.1145/3729355


## P001

- **Section:** 1 Introduction

- **Relevance:** capability_claim

- **Text:**

> ChatDBG lets programmers engage in a collaborative dialogue with the debugger, allowing them to pose complex questions about program state, perform root cause analysis for crashes or assertion failures, and explore open-ended queries like ‘why is x null?’.


## P002

- **Section:** 2 Overview

- **Relevance:** interaction_mode

- **Text:**

> A key feature of ChatDBG is that it grants autonomy to the LLM to “take the wheel” and act as an independent agent [10, 42] while answering the programmer’s queries. Specifically, the LLM issues “function calls” [33] to run commands in the underlying debugger to investigate program state, execute code, or obtain source code.


## P003

- **Section:** 3 Related Work

- **Relevance:** capability_claim

- **Text:**

> ChatDBG performs best-effort automated program repair by requesting that the LLM propose code fixes as part of its response, ultimately letting the programmer drive code changes using these suggestions.


## P004

- **Section:** 5.1 Python

- **Relevance:** benefit

- **Text:**

> While all features of ChatDBG contribute to its success, the technical innovations enabling it to take the wheel are critical. The most sophisticated configurations show that user-provided contextual information about behavior and engaging in multi-step dialogs are particularly good ways to improve its effectiveness.
