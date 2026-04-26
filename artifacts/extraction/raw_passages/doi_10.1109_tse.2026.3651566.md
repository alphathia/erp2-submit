# Raw Passages — doi:10.1109/tse.2026.3651566


## P001

- **Section:** 1 INTRODUCTION

- **Relevance:** challenge

- **Text:**

> LLMs are often prompted with an incomplete code snippet and asked to suggest an appropriate API call. In this context, LLMs face distinct challenges: They may erroneously hallucinate functions from other libraries, suggest irrelevant or incorrect APIs, or specify invalid parameters, even when familiar with the target library.


## P002

- **Section:** 1 INTRODUCTION

- **Relevance:** usage_pattern

- **Text:**

> Through extensive manual annotation of 3,209 method-level and 3,492 parameter-level cases, we identify four recurring misuse patterns in LLM-generated API code: (1) Intent misuse... (2) Hallucination misuse... (3) Missing item misuse... and (4) Redundancy misuse...


## P003

- **Section:** 1 INTRODUCTION

- **Relevance:** interaction_mode

- **Text:**

> We evaluate three representative decoder-only LLMs used in IDE settings: StarCoder-7B... Qwen2.5-Coder-7B... and Copilot... Both models are widely used in IDE environments such as VSCode.


## P004

- **Section:** 1 INTRODUCTION

- **Relevance:** capability_claim

- **Text:**

> To address these issues, we propose Detect-reason-Fix (Dr.Fix), a taxonomy-guided LLM-based APR method. Compared with baseline prompting and prior repair methods, Dr.Fix achieves substantial improvements...
