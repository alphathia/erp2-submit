# Raw Passages — doi:10.1145/3644815.3644950


## P001

- **Section:** 1 INTRODUCTION

- **Relevance:** challenge

- **Text:**

> First, LLM regression tests should be defined at a different granularity. In traditional software engineering, a single breaking regression test would indicate a bug in the software implementation... LLM regression tests should be defined over data slices rather than on single predictions or the entire dataset.


## P002

- **Section:** 1 INTRODUCTION

- **Relevance:** challenge

- **Text:**

> Second, LLM regression tests need to monitor both model and prompt updates. It is well-known that prompt engineering can greatly influence LLMs’ performance [19]. As we will show, we observed that different prompt designs regress or improve differently on the same API update


## P003

- **Section:** 1 INTRODUCTION

- **Relevance:** challenge

- **Text:**

> Third, LLM regression tests need to deal with non-determinism of LLM APIs. LLMs are known to produce non-deterministic outputs: Non-determinism is often introduced intentionally for generating high-quality outputs with a non-zero temperature
