# Raw Passages — doi:10.1609/aaai.v40i47.41475


## P001

- **Section:** Introduction

- **Relevance:** capability_claim

- **Text:**

> We propose NOVAID (Natural-language Observability Visualization Assistant for ITOps Dashboards), an interactive chatbot powered by large language models (LLMs), to streamline the dashboard widget creation process. Our tool addresses the limitations of existing solutions by introducing a domain-specific, schema-aware approach to generate IT monitoring dashboard widgets from natural language queries.


## P002

- **Section:** NOVAID Frontend

- **Relevance:** interaction_mode

- **Text:**

> The chat interface is the primary entry point for users, embedded directly within the Instana dashboard. Users express their requests in natural language—such as filters, aggregation strategies, or visualization preferences—and receive our tool’s interpretations within the chat window. The interface supports multi-turn conversations, prompting for missing parameters and offering clarification options when user input is ambiguous or is missing key elements.


## P003

- **Section:** Results

- **Relevance:** challenge

- **Text:**

> The primary challenge lies in extracting complex Tag Filter Expressions and, in particular, Grouping parameters. While Tag Filter Expression accuracy reached a respectable 80.07%, the Grouping accuracy varied, peaking at 64.58%. This is consistent with the nature of the task; grouping is often underspecified or implicit in a query, requiring more advanced reasoning to infer the user’s intent.


## P004

- **Section:** User Study

- **Relevance:** benefit

- **Text:**

> Participants performed two tasks: manually creating widgets and using NOVAID for automatic creation, followed by a survey. ... NOVAID achieved a System Usability Scale (SUS) score of 74.2, exceeding the benchmark of 68 (Sauro and Lewis 2016) and indicating good usability.
