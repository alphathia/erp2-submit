# Transferability Statement

> **Deliverable class:** Phase 6 Task 6.4 — qualitative-research transferability (Lincoln & Guba 1985; Cruzes & Dybå 2011 §VI) operationalized as an explicit enumeration of boundary conditions under which the study's findings generalize / do not generalize.
> **Generated:** 2026-04-20 UTC
> **Rater:** TBS
> **Plain-English question this document answers:** *"Under what boundary conditions do the findings apply, and where don't they?"*

---

## Framing

Transferability is the trust-worthiness criterion parallel to positivist external validity (Lincoln & Guba 1985 §11.2). In qualitative synthesis, generalization claims are not made by the researcher; instead, the researcher provides sufficient thick description of the study's scope for readers to judge transferability to their own contexts. Cruzes & Dybå (2011) §VI frames this as naming the boundary conditions explicitly.

This document enumerates **eight boundary conditions** under which the study's findings (4 contributions across RQ1 / RQ2 / RQ3 / research agenda) apply. Each condition names (i) what the boundary is, (ii) how it was introduced by design or by execution, (iii) which findings it limits and which it does not.

---

## Boundary 1 — Time window

**What:** The corpus covers empirical AI-SE literature published **2022–2026 inclusive**.

**How introduced:** The search-strategy protocol (proposal §3.2; `search_strings.md`) anchors the window at 2022 (GitHub Copilot public release as the mass-adoption inflection point) through 2026 (submission year). Explicitly excluded: pre-2022 AI-assisted programming literature (e.g., early Intellicode, TabNine-era studies) and any 2026 work published after the Phase 2 search-cutoff date.

**Limits which findings:**
- **Does limit:** RQ1 landscape — the evidence concentration is for 2022–2026 only. Trends across the 5-year window should not be extrapolated to pre-2022.
- **Does limit:** RQ2 mode prevalence — the dominance of Mode 5 (Delegated Task Execution) and Mode 4 (Review & Validation) reflects the recent agentic turn; pre-2022 corpora would likely show Mode 1 (Inline Completion) dominance (see Boundary 6).
- **Does not limit:** The mode taxonomy structure itself — the 5-mode partition along the delegation-depth axis is an analytic construct, not a time-series claim. Its transferability depends on Boundary 6 + Boundary 7, not on the time window.
- **Does not limit:** RQ3 gap rule — the 25th-percentile rule is corpus-relative; it re-anchors automatically on any future corpus.

**ERP3 implication:** Practitioner interviews should explicitly probe whether interaction patterns pre-2022 differ from those captured here.

---

## Boundary 2 — Venue set

**What:** Database searches executed on **Scopus + IEEE CSDL + ACM Digital Library**; snowballing from three seed surveys. **Grey literature excluded** (blog posts, industry reports, pre-prints not yet indexed).

**How introduced:** Proposal §3.2 search strategy. IEEE Xplore was replaced by CSDL mid-Phase-2 (decision register `ieee_csdl_replaces_xplore`); duplicate Xplore entries removed post-substitution (`ieee_search_removed`). Grey-literature exclusion is a deliberate scope decision consistent with Petersen et al. (2015) §4.3 SMS methodology guidance.

**Limits which findings:**
- **Does limit:** RQ1 landscape — any empirical AI-SE practice reported only in grey literature is invisible to this corpus. This likely under-represents:
  - Industry-internal usage reports (e.g., vendor blog posts about tool adoption).
  - Emerging-tool evaluations that have not yet reached academic venues.
- **Does not limit:** RQ2 mode taxonomy — the inductive mode set is derived from the 290 passage-bearing papers; a different venue mix would shift the mode *prevalence* but not necessarily the mode *structure*.

**ERP3 implication:** ERP3 practitioner interviews can re-admit grey-literature signals by asking practitioners directly about tools and practices the academic literature has not yet caught up with.

---

## Boundary 3 — Language coverage

**What:** Search strings and extraction are **English-only**.

**How introduced:** Operational choice (single-rater study; the rater reads English). Non-English primary studies are out of scope even if indexed.

**Limits which findings:**
- **Does limit:** RQ1 landscape — region-specific AI-SE practices published only in Chinese, Japanese, German, Spanish, or other language venues are invisible. This likely under-represents non-Anglosphere practitioner contexts.
- **Does not limit:** RQ2 / RQ3 methodology — the taxonomy and gap rule generalize to non-English corpora in principle; re-running the pipeline on a translated corpus would yield a comparable output under the same boundaries.

**ERP3 implication:** Any ERP3 interview cohort outside the Anglosphere should be interpreted against an incomplete RQ1 baseline.

---

## Boundary 4 — Corpus composition: paradigm skew (Pro-code dominance)

**What:** Of 639 papers with a non-null F5 tool paradigm + modality, **537 (84%) are Pro-code**, 30 (5%) Low-code, 72 (11%) No-code.

**How introduced:** This is a property of the published literature, not the search strategy — the AI-SE research community has concentrated on Pro-code contexts.

**Limits which findings:**
- **Does limit:** RQ2 Mode 3 (Visual / Declarative Composition) — Mode 3 has only 9 canonical labels and sits predominantly in Low-code / No-code contexts; inferences about Mode 3 carry a thinner evidence base than Modes 2 / 4 / 5.
- **Does limit:** RQ3 paradigm-split gap matrix — the Low-code and No-code sub-matrices have only 30 and 72 papers respectively, producing thin per-paradigm P25 values (both = 1.0). Treat per-paradigm gap counts as directional, not dispositive.
- **Does not limit:** The paradigm-split artefacts themselves — `artifacts/analysis/rq3_gap_matrix/gap_matrix_by_paradigm/{procode,lowcode,nocode}.csv` are each complete given their contributing papers.

**ERP3 implication:** ERP3 should deliberately over-sample Low-code / No-code practitioner cohorts to counter corpus under-representation.

---

## Boundary 5 — F3 population coverage

**What:** Only **392 of 640 papers (61%) have a canonical F3 population value** (Professional SWE / Student / Citizen Developer / OSS Contributor / Mixed). 246 papers have F3 = NaN. 9 additional papers study non-developer end-user populations (writers, older adults, accessibility QA testers) and were coded closest-available under the existing vocabulary.

**How introduced:** F3 is extracted from the paper's participant description during Phase 3 Task 3.2. Papers that do not describe a study population (primarily benchmark-evaluation papers; surveys without human participants; secondary reviews) have F3 = NaN by construction. The 9 non-developer papers are logged under decision register row `f3_scope_boundary_accepted`.

**Limits which findings:**
- **Does limit:** RQ1 Figure 1 (`year_sdlc_bubble.png`) — shows 392 papers, not 640. The other 248 papers are still in the broader corpus but invisible to this population-faceted figure.
- **Does limit:** RQ2 Part B `mode_x_population_context` cross-tab — denominator drops further to 192 (requires both F3 population AND F3 context non-null). Mode × population claims carry this narrower denominator.
- **Does not limit:** RQ1 Figures 2–4, RQ3 gap matrix — these use corpus denominators of 640 / 640 / 384 respectively.

**ERP3 implication:** ERP3 practitioner cohorts should include non-developer populations explicitly, since the SMS corpus under-represents them.

---

## Boundary 6 — Mode 1 thin evidence

**What:** The RQ2 taxonomy's Mode 1 (Inline Completion) is supported by **only 4 of 707 canonical labels (0.6%)**, far below the 15-label re-open trigger specified in `task4_2_todo.md §1`.

**How introduced:** Observed in Phase 4 Task 4.2 Step 4 classification. The rater did not re-open the frame because the thinness is a property of the 2022–2026 published literature — papers about code completion tend to be short usage reports rather than full empirical studies (many were EC-excluded at Phase 2).

**Limits which findings:**
- **Does limit:** Any prevalence claim for Mode 1 — the empirical base is too thin to support "X% of developers use inline completion" claims. Report Mode 1 findings with explicit corpus-size caveats.
- **Does not limit:** Mode 1's operational definition or its position on the delegation-depth axis — these are analytic commitments grounded in proposal §3.5, not evidence-count commitments.

**Interpretive note (from `adoption_progression.md §Non-linearity note`):** Practitioners likely use Mode 1 *far more* than the corpus emphasizes. The corpus is biased toward papers that study *newer* interaction patterns (agentic, conversational) because those are the publication-worthy novelties. Mode 1 is a solved, deployed, under-studied baseline.

**ERP3 implication:** ERP3 should probe Mode 1 use directly even though the SMS evidence base is thin; practitioner self-report will likely refute the corpus signal.

---

## Boundary 7 — Mode-A vs Mode-B coding coverage

**What:** The RQ2 mode taxonomy is derived from **290 papers with extractable full-text passages (Mode A)**, not from the 350 abstract-only papers (Mode B).

**How introduced:** Phase 3 Task 3.3 only generated open codes from papers with retrievable full text. Mode-B papers contributed F1–F5 facets (and therefore appear in RQ1 landscape + RQ3 gap matrix) but no coding passages (so no mode assignment).

**Limits which findings:**
- **Does limit:** RQ2 mode taxonomy derivation denominator — 290 papers, not 640.
- **Does limit:** Saturation argument — mode-layer saturation (Saturated) is computed over 290 papers. Adding the 350 Mode-B papers would in principle surface new modes but in practice would not (Mode B papers are abstract-only and cannot support inductive coding).
- **Does not limit:** RQ1 or RQ3 — both use the full 640-paper corpus.

**ERP3 implication:** ERP3 practitioner interviews are a remedy for the Mode-B gap — they produce first-person usage data where the SMS had only the abstract.

---

## Boundary 8 — ERP3 hand-off scope

**What:** The research agenda (Task 5.3 `research_agenda.md`) pre-specifies **6 Wieringa-typed study calls** covering all 42 gap cells + 12-cell empty-cell appendix. ERP3 is the downstream follow-on study.

**How introduced:** Proposal §5 Practical Implications + §1.3 Objective 4. ERP3 is named in the proposal as the qualitative practitioner-interview study that operationalizes the research agenda.

**Limits which findings:**
- **Does not limit** RQ1 / RQ2 / RQ3 — those are Phase 5 deliverables. The research agenda is an ERP3 *input*, not an ERP3 dependency.
- **Does scope:** ERP3 study design — ERP3 may legitimately:
  - Re-prioritize the 6 calls (e.g., interview evidence may surface priorities the SMS gap rule did not flag).
  - Depart from the calls entirely if practitioner evidence diverges from the gap matrix.
  - Add follow-up questions outside the current call set.

**Transferability asymmetry:** The research agenda *predicts* ERP3 priorities; ERP3 will validate, refute, or extend those predictions. The SMS is not authoritative about ERP3 scope — it is a structured first-pass hypothesis set.

---

## Summary table

| # | Boundary | Limits RQ1? | Limits RQ2? | Limits RQ3? | Limits research agenda? |
|---:|---|:-:|:-:|:-:|:-:|
| 1 | Time window (2022–2026) | ✅ prevalence | ✅ prevalence | ✓ corpus-relative rule adapts | — |
| 2 | Venue set (Scopus + CSDL + ACM + seed snowball; no grey) | ✅ coverage | partial (prevalence only) | ✓ | — |
| 3 | Language (English-only) | ✅ regional gaps | partial (prevalence only) | partial | — |
| 4 | Paradigm skew (Pro-code 84%) | ✅ | ✅ Mode 3 thin | ✅ Low/No-code thin | ✅ ERP3 over-sampling needed |
| 5 | F3 population coverage (392/640) | ✅ population-facet figures | ✅ mode × population | — | partial |
| 6 | Mode 1 thin evidence (4/707 labels) | — | ✅ Mode 1 prevalence | — | partial |
| 7 | Mode-A vs Mode-B (290 / 350 split) | — | ✅ taxonomy denominator | — | ✅ ERP3 is the Mode-B remedy |
| 8 | ERP3 hand-off scope | — | — | — | ✅ scopes downstream study |

**Legend:** ✅ = primary limit; ✓ = partial / indirect; — = not limited.

---

## Scope statement (for manuscript §6)

The study's findings apply to **empirical, peer-reviewed, English-language AI-SE research published 2022–2026 in Scopus / IEEE CSDL / ACM Digital Library venues**, with supplementary backward snowballing from three reference surveys. Within that scope:

- **RQ1 landscape** characterizes the evidence distribution with full corpus coverage (640 papers), subject to F3 NaN in Figure 1 (392 papers).
- **RQ2 taxonomy** characterizes the interaction-mode partition using the 290 Mode-A passage-bearing papers; mode structure transfers; mode prevalence is corpus-specific.
- **RQ3 gap matrix** characterizes supply-vs-demand asymmetries using 384 annotated papers; gap rule is corpus-relative and re-anchors on any future corpus.
- **Research agenda** pre-specifies ERP3 priorities; ERP3 may validate / refute / extend them.

Findings do **not** automatically transfer to pre-2022 AI-SE, non-English venues, industry grey literature, or Low-code / No-code practitioner communities without additional primary research.

---

## References

- Lincoln, Y. S., & Guba, E. G. (1985). *Naturalistic Inquiry*. Sage Publications.
- Cruzes, D. S., & Dybå, T. (2011). *Recommended Steps for Thematic Synthesis in Software Engineering*. ESEM.
- Petersen, K., Vakkalanka, S., & Kuzniarz, L. (2015). *Guidelines for conducting systematic mapping studies in software engineering: An update*. IST 64.
