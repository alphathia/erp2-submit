# Raw Passages — doi:10.1109/ase63991.2025.00223


## P001

- **Section:** I. INTRODUCTION

- **Relevance:** capability_claim

- **Text:**

> PALM begins with path analysis of the focal method to identify its execution paths, each representing a sequence of conditions and return values. We gather contextual information, including the focal method’s body, other declarations, definitions, and function call details, to guide the LLM. For each path, we construct a prompt using this information and ask the LLM to generate test cases.


## P002

- **Section:** IV. METHODOLOGY

- **Relevance:** capability_claim

- **Text:**

> PALM adopts the second method for fixing compilation errors, as regenerating tests may inadvertently alter error-free parts. First, we extract error information and relevant code snippets from the compilation messages. For each error, we construct a prompt instructing the model to generate a change log based on this information.


## P003

- **Section:** V. EXPERIMENT DESIGN, RESULTS AND DISCUSSION

- **Relevance:** challenge

- **Text:**

> Developer interactions during the PR process indicated that while some expressed caution towards LLM-generated code, most were receptive, provided the tests were meaningful and demonstrably increased coverage. The 5 rejected tests were primarily due to developers seeking additional value beyond mere coverage improvement or perceiving the tests as redundant.
