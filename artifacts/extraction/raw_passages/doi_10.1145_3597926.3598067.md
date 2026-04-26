# Raw Passages — doi:10.1145/3597926.3598067


## P001

- **Section:** ABSTRACT

- **Relevance:** capability_claim

- **Text:**

> To address these limitations, we propose TitanFuzz – the first approach to directly leveraging Large Language Models (LLMs) to generate input programs for fuzzing DL libraries.


## P002

- **Section:** 1 INTRODUCTION

- **Relevance:** usage_pattern

- **Text:**

> In TitanFuzz, we first use a generative LLM with a step-by-step input prompt [46] to produce the initial seed programs for fuzzing. To enrich the pool of test programs, we further adopt an evolutionary strategy to produce new test programs by using LLMs to automatically mutate the seed programs.


## P003

- **Section:** ABSTRACT

- **Relevance:** benefit

- **Text:**

> Our experimental results demonstrate that TitanFuzz can achieve 30.38%/50.84% higher code coverage than state-of-the-art fuzzers on TensorFlow/PyTorch. Furthermore, TitanFuzz is able to detect 65 bugs, with 41 already confirmed as previously unknown bugs.
