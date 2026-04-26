# Explanation — `f2_method_bar.png`

> **Figure purpose.** Descriptive distribution of research methodologies across the 640-paper corpus. Each bar height = distinct-paper count for that F2 value.

## 1. Source data

| Field | Source | Role |
|---|---|---|
| `paper_id` | `artifacts/extraction/extraction_matrix.csv` | Counting key. |
| `f2_research_methodology` | `extraction_matrix.csv` | X-axis; one F2 value per paper per the extraction schema. |

## 2. Counting unit

Each bar height is a **distinct-`paper_id` count** over `f2_research_methodology`:

```
bar_count(m) = |{ paper_id : f2_research_methodology = m }|
```

Because `f2_research_methodology` is **single-valued** per paper (the codebook specifies exactly one F2 per study), bar heights sum exactly to the non-NaN paper count.

## 3. Why totals add to 640 exactly

Current extraction has **0 NaN** values in `f2_research_methodology` (all 640 papers coded). Therefore:

```
sum(bar_heights) = 640 = N (corpus total)
```

This is the only RQ1 landscape figure where the bar/bubble totals reconcile exactly with the corpus denominator. The other three figures involve multi-valued columns (`f4_sdlc_activity`, `f5_tool_modality`) or filtered sub-populations (F3 NaN).

## 4. F2 vocabulary

Per the codebook (`artifacts/protocol/codebook.md`), F2 canonical values:

- Survey
- Interview
- Case Study
- Experiment
- Field Study
- Mining
- Mixed

Bars are sorted descending by count for readability; no fixed methodological ordering is imposed.

## 5. Interpretation guidance

- **F2 is mutually exclusive** by construction. A study combining survey + interview is coded `Mixed`, not two rows.
- **Mining** here refers to software-repository mining / corpus analysis, not data mining broadly — per codebook §F2.4.
- **No axis manipulation.** Raw counts shown above each bar; no log scale; no percentage transform. A value of 100 means 100 papers used that methodology.

## 6. Terminological clarifications

- **"Methodology" (F2) is the empirical-study design of the primary paper** — how the authors collected evidence. This is distinct from:
  - **Contribution type (F1)** — Wieringa-class of the paper itself (Evaluation / Validation / Solution Proposal / Philosophical / Opinion / Personal Experience).
  - **Research strategy** — we do not use this term to avoid conflation with "methodology".
- F2 values are **English-method names**, not codes; the codebook tabulates them with 1–2 sentence operational definitions.

## 7. Methodological references

- Proposal §3.5 RQ1 — "bar charts summarizing the distribution of research methodologies" is the proposal-specified figure.
- Petersen et al. (2015) §7.3 — method-distribution bars are a primary SMS reporting artefact.

## 8. Provenance

- **Script:** `code/analysis_rq1.py::fig2_f2_method_bar`
- **Meta sidecar:** `f2_method_bar.png.meta.json`.
- **Design spec:** `design/5_1_analysis_rq1.md`.
