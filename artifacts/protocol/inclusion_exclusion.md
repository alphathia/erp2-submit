# Inclusion and Exclusion Criteria (Rewritten Appendix A.2)

Source: `docs/ERP2_Research_Proposal.docx`, Appendix A.2, expanded per `research_plan_sms.md` consistency review.

Enforcement layers: **Q** = Scopus query (Layer 1), **S** = manual screening (Layer 2), **P** = post-retrieval script (Layer 3).

---

## Inclusion Criteria

**IC1** [Q] The paper is published between 1 January 2022 and the search cut-off in April 2026.

**IC2** [S] The paper reports at least one empirical study (survey, interview, case study, experiment, field study, mining study) of human interaction with SE agents, AI coding tools, or AI-enhanced low-code/no-code and workflow-automation platforms used for software or application development.

**IC3** [Q] The paper is a peer-reviewed journal article or conference paper (SRCTYPE journal or conference proceedings; DOCTYPE article or conference paper).

**IC4** [Q] The paper is written in English.

**IC5** [P] The paper is at least 4 pages in length.

---

## Exclusion Criteria

**EC1** [S] The paper only proposes or builds an agent system without reporting usage evidence. Such papers are classified as **Solution Proposal** per Wieringa et al. (2006) and are excluded because they contribute to the supply side, not the demand side that this SMS maps.

**EC2** [S] The paper is a benchmark study evaluating model or agent capabilities without human users. Such papers are classified as **Validation Research** per Wieringa et al. (2006) and are excluded because they lack the empirical human-interaction evidence required by IC2.

**EC3** [S] The paper is outside the software engineering domain. This is a Layer-2 manual screening check; SUBJAREA(COMP) is deliberately not applied at Layer 1 to avoid silently dropping citizen-developer and cross-disciplinary venues.

**EC4** [Q+S] The paper is a secondary study (existing survey or systematic literature review). DOCTYPE(re) is excluded at Layer 1; manual confirmation at Layer 2. Secondary studies are used as snowball seeds only (see §2 of `research_plan_sms.md`).

**EC5** [Q+P] The paper is a short paper (<4 pages), poster, or extended abstract. Partially filtered at Layer 1 by DOCTYPE exclusions (ed, no, le, sh, er, rt); confirmed by the page-count script at Layer 3.

**EC6** [P] The full text is not retrievable within two weeks of identification. Logged in `decision_register.csv` with the retrieval attempts and deadline.
