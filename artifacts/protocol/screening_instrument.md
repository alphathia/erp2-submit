# Screening Instrument — Phase 2 Decision Tree

Source: `artifacts/protocol/inclusion_exclusion.md`. Methodology: Ali & Petersen (2014) screening protocol; Wieringa et al. (2006) for provisional F1 assignment.

For each candidate paper, walk the tree top-to-bottom. Stop at the first **EXCLUDE** or reach **INCLUDE** at the end. Log every decision in `decision_register.csv` with the criterion applied.

## Alignment with Ali & Petersen (2014)

Ali & Petersen's framework recommends three components for reliable study selection:

1. **Objective criteria formulated as questions that can be answered objectively** — implemented as the Q/S/P-tagged IC/EC criteria in `inclusion_exclusion.md`.
2. **Decision rules using three possible labels** (relevant / irrelevant / uncertain) — implemented as three-way decisions in `code/screening_harness.py` (include / exclude / defer).
3. **Rules for resolving uncertainties** — implemented via second-pass review of deferred papers (Task 2.5) and logging in `decision_register.csv`.

Additional Ali & Petersen elements applied:
- **Think-aloud protocol** (reviewer expresses reasoning during screening) — implemented via the optional `rationale` field on every screening decision.
- **Pilot on a subset** — completed in Task 1.6 with 3 papers + 5 codebook refinements.
- **Inclusive strategy for disagreements** — our single-rater context replaces inter-rater disagreement with intra-rater consistency; we adopt the paper's inclusive default (defer rather than exclude when uncertain).
- **Adaptive reading depth** — abstract-level screening here, full-text verification at Task 3.1 for inclusion-confirmed papers and for any `manual_review` rows (Policy A, see Task 2.5).

**Single-rater context:** Ali & Petersen's inter-rater agreement recommendation is not directly applicable. Instead, we apply **intra-rater consistency checking**: after all ≈4093 decisions are made, re-screen a random 10% sample (≈409 papers) after a 1-week cooldown without access to prior decisions. Target ≥90% percent-agreement; <80% triggers codebook review.

---

## Layer 1 — Query-Enforced (pre-screened by Scopus query)

These criteria are enforced by the Scopus query template and the post-retrieval scripts. They do not require manual judgement but are listed for completeness and for manual verification of borderline cases flagged by the enrichment pipeline.

```
[IC1] Published Jan 2022 – Apr 2026?
  ├─ NO  → EXCLUDE (IC1: outside date range)
  └─ YES ↓

[IC3] Peer-reviewed journal article or conference paper?
  ├─ NO  → EXCLUDE (IC3: not peer-reviewed)
  └─ YES ↓

[IC4] Written in English?
  ├─ NO  → EXCLUDE (IC4: not English)
  └─ YES ↓

[EC4] Is this a secondary study (survey/SLR)?
  ├─ YES → EXCLUDE (EC4: secondary study — route to snowball seed list)
  └─ NO  ↓
```

## Layer 2 — Manual Title/Abstract Screening

Read the title and abstract. Apply each criterion in order.

```
[IC2] Reports at least one empirical study of human interaction
      with SE agents, AI coding tools, or AI-enhanced LCNC/workflow
      platforms for software or application development?
  ├─ NO  → EXCLUDE (IC2: no empirical human-interaction evidence)
  └─ YES ↓

[EC1] Does the paper ONLY propose/build an agent system without
      reporting usage evidence? (Solution Proposal per Wieringa)
  ├─ YES → EXCLUDE (EC1: Solution Proposal only)
  └─ NO  ↓

[EC2] Is this a benchmark study evaluating model/agent capabilities
      without human users? (Validation Research per Wieringa)
  ├─ YES → EXCLUDE (EC2: Validation Research without human users)
  └─ NO  ↓

[EC3] Is the paper outside the software engineering domain?
  ├─ YES → EXCLUDE (EC3: outside SE domain)
  └─ NO  ↓
```

**If reached here → PROVISIONALLY INCLUDE.** Assign a provisional F1 (Contribution Type) per Wieringa's six classes and record it.

## Layer 3 — Post-Retrieval Script Checks

These are applied after full-text retrieval and are enforced by `code/page_filter.py` and the retrieval tracker.

```
[IC5 / EC5] Is the paper at least 4 pages?
  ├─ NO  → EXCLUDE (EC5: short paper / poster / extended abstract)
  └─ YES ↓

[EC6] Is the full text retrievable within two weeks?
  ├─ NO  → EXCLUDE (EC6: full text not retrievable — log attempts
  │         and deadline in decision_register.csv)
  └─ YES ↓
```

**If reached here → INCLUDE.** Paper enters the extraction pipeline (Phase 3).

---

## Borderline Protocol

For any criterion where the rater is uncertain:
1. Mark the paper as **borderline** in `artifacts/screening/borderline_log.csv`.
2. Record the criterion, the uncertainty, and a preliminary lean (include/exclude).
3. Re-read the abstract (or full text if available) before making a final decision.
4. Log the final decision in `decision_register.csv` with the rationale.
