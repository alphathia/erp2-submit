# Raw Passages — doi:10.1186/s40537-024-01019-z


## P001

- **Section:** Abstract

- **Relevance:** capability_claim

- **Text:**

> We used nine different benchmark applications which represent typical parallel programming workloads and compared their OpenMP-based parallel solutions produced manually and using ChatGPT and Github Copilot in terms of obtained speedup, applied optimizations, and quality of the solution.


## P002

- **Section:** Experimental setup and design

- **Relevance:** interaction_mode

- **Text:**

> The experimentation further extends to include two variations facilitated by the ChatGPT tool with the series of interactive conversations, labeled omp_gpt and omp_gpt2, as well as a version produced by GitHub Copilot extension, referred to as the copilot version.


## P003

- **Section:** Discussion

- **Relevance:** challenge

- **Text:**

> Generally, ChatGPT requires less effort from the programmer than Github Copilot. However, sometimes it can be confused when the large code context is given, often leading to compilation errors, erroneous execution, or even significant changes of the original code


## P004

- **Section:** Elaboration

- **Relevance:** benefit

- **Text:**

> GitHub Copilot effectively parallelized the application from the beginning, identifying the iteration imbalance and incorporating the schedule(dynamic) directive in the initial prompt.


## P005

- **Section:** Discussion

- **Relevance:** challenge

- **Text:**

> Both ChatGPT and Github Copilot exhibited problems with scoping of variables, as they try both to move variable declarations to the inner blocks of code or incorrectly use OpenMP scoping clauses, such as shared, private, and firstprivate.
