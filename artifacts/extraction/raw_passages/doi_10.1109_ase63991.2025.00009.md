# Raw Passages — doi:10.1109/ase63991.2025.00009


## P001

- **Section:** III. EXPERIENCE OF DESIGNING ALERTGUARDIAN > B. Alert Summary

- **Relevance:** capability_claim

- **Text:**

> Alert Summary module employs RAG to incorporate internal knowledge (e.g., system documents, alert rule explanations, incident tickets) of Company-X into an LLM, thereby generating concise yet actionable alert summaries (e.g., fault explanations, localization, and resolutions).


## P002

- **Section:** III. EXPERIENCE OF DESIGNING ALERTGUARDIAN > C. Alert Rule Refinement

- **Relevance:** capability_claim

- **Text:**

> AlertGuardian introduces a multi-agent workflow to refine alert rules, executed every large time window (30 minutes by default) to balance efficiency and effectiveness. Agents collaborate in a pipeline without a central orchestrator, ensuring streamlined communication.


## P003

- **Section:** IV. EXPERIMENTAL EVALUATION > C. RQ2: Performance in Alert Summary

- **Relevance:** usage_pattern

- **Text:**

> Qualitative assessment involved two SREs scoring summaries for Actionability and Relevance (1–5 scale).


## P004

- **Section:** V. DISCUSSION > A. Success Stories

- **Relevance:** benefit

- **Text:**

> By analyzing noisy alerts flagged by the alert denoise module, AlertGuardian generated over 300 rule optimization proposals, with near 100 adopted by SREs. Through continuous refinement, the system eliminates over 50,000 false positives per day.
