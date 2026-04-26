# Explanation — `f5_tool_profile_stacked.png`

> **Figure purpose.** Stacked bar showing the distribution of **F5 tool profile** across the corpus. Bars group papers by **F5 tool paradigm** (Pro-code / Low-code / No-code); within each bar, stacks are subdivided by **F5 interaction modality** (Autocomplete / Conversational / IDE-Integrated / Autonomous).

## 1. "Modality" vs "Mode" — critical disambiguation

The word "mode" appears in two **completely different** places in this project. They must not be conflated.

| Term | Facet | Where it comes from | Values | Used in |
|---|---|---|---|---|
| **F5 tool interaction modality** | F5 (Agent/Tool Profile) — supply-side characterization of the *tool* | Proposal §3.4 codebook; extracted during Phase 3 Task 3.2 | Autocomplete, Conversational, IDE-Integrated, Autonomous | **This figure** (Task 5.1 Part A) |
| **Human–AI interaction mode** (RQ2 taxonomy) | Inductive output of Phase 4 Task 4.2; the RQ2 deliverable | Derived from Phase 3 open codes via the 9-step Task 4.2 methodology | Mode 1–5 + Residuals (Inline Completion, Conversational Prompting, Visual / Declarative Composition, Review & Validation, Delegated Task Execution) | `artifacts/synthesis/interaction_taxonomy.md`, `artifacts/analysis/rq2_variation/mode_x_*.md` |

**This figure uses F5 tool interaction modality (supply-side).** It is an **attribute of the tool the study used**, not an observation about human behavior. The RQ2 interaction modes (Phase 4 output) are the *empirical, demand-side* construct — they characterize how humans actually engaged with AI during the reported studies, synthesised inductively from open codes. The two taxonomies can look similar on the surface (both have "Conversational" and both relate to AI-SE) but they are **methodologically distinct**:

- **F5 modality** = a classification of the tool. A paper studying GitHub Copilot would have F5 modality `Autocomplete` regardless of how participants used it.
- **RQ2 interaction mode** = a classification of the interaction in the reported study. A paper about Copilot might be classified under Mode 2 "Conversational Prompting" if participants wrote prompts at the comment-to-code level, or Mode 1 "Inline Completion" if they used tab-completion only.

To avoid confusion, the figure's axis and legend labels explicitly use "F5 interaction modality" (never unqualified "mode"). The RQ2 interaction modes do not appear in this figure.

## 2. Source data

| Field | Source | Role |
|---|---|---|
| `paper_id` | `artifacts/extraction/extraction_matrix.csv` | Counting key. |
| `f5_tool_paradigm` | `extraction_matrix.csv` | X-axis (3 categorical values: Pro-code / Low-code / No-code). Single-valued per paper. |
| `f5_tool_modality` | `extraction_matrix.csv` | Stack segmentation (4 categorical values). **Multi-valued** pipe-separated — see §4. |

The F5 facet is a **composite tag** per proposal §3.4 footnote `a`:

> Agent/Tool Profile is a composite multi-select facet: each tool is tagged with one or more values from `{Autocomplete, Conversational, IDE-Integrated, Autonomous}` and one value from `{Pro-code, Low-code, No-code}`...

So paradigm is single-valued; modality is multi-select.

## 3. Counting unit

Each stack segment is a **distinct-`paper_id` count** over `(paradigm, modality)`:

```
segment_count(p, m) = |{ paper_id : f5_tool_paradigm = p ∧ m ∈ f5_tool_modality.split('|') }|
```

A paper with modality `"Autocomplete|Conversational"` and paradigm `"Pro-code"` contributes to **both** the Pro-code/Autocomplete segment AND the Pro-code/Conversational segment, reflecting that the paper's tool legitimately spans both modalities.

## 4. Multi-modality papers — how the figure handles them

Analogous to Fig 3 handling of multi-SDLC, we explode the pipe-separated modality list. Consequence: the sum of stack heights across all three bars **exceeds** the 640-paper corpus.

| Quantity | Value |
|---|---:|
| Papers with F5 paradigm populated AND ≥1 canonical F5 modality | 639 |
| Papers excluded (NaN F5 modality — see §5 for the single paper) | 1 |
| Single-modality papers | 471 |
| Multi-modality papers | 168 |
| Mean modalities per paper (among contributing) | 1.36 |
| Grand total paper × modality bindings (sum of all stack heights) | 867 |

Distinct-paper counts **per paradigm** (bar totals if we used distinct counting rather than modality stacks):

| Paradigm | Distinct papers |
|---|---:|
| Pro-code | 537 |
| Low-code | 30 |
| No-code | 72 |
| **Total distinct** | **639** (of 640 in corpus) |

## 5. Why the bars' total exceeds 640, and the 1-paper exclusion

Two effects shape the relationship between bar totals and the 640-paper corpus:

1. **Multi-modality inflation.** 168 papers tag more than one modality, so they contribute to multiple stack segments within the same bar. This pushes the total above the distinct-paper count of 639.
2. **1 paper excluded by mechanism, not by figure logic.** Identified precisely:

   | Field | Value |
   |---|---|
   | `paper_id` | `doi:10.1109/icodse68111.2025.11351919` |
   | `title` | A Mobile Application Front-End for Presenting Explainable AI Results in Diabetes Risk Estimation |
   | `venue` / `year` | ICoDSE / 2025 |
   | `f5_tool_paradigm` | `Pro-code` (populated) |
   | `f5_tool_name` | `GPT-4o; SHAP` (populated) |
   | `f5_tool_modality` | **`NaN`** (the cause of exclusion) |

   With no canonical modality value, there is no stack segment for the paper to occupy — the figure mechanically cannot place it. Across the entire corpus, `f5_tool_paradigm` has 0 NaN rows and `f5_tool_modality` has exactly 1 NaN row, so this single paper accounts for the full 640 → 639 gap.

   This same paper also has `f4_sdlc_activity = NaN` and is therefore one of the two Mixed-panel exclusions in `year_sdlc_bubble.png` (see that figure's `_imgexplain.md §4`). It is a known F4/F5-modality data gap — distinct from (and not part of) the 9-paper F3 scope-boundary set logged in `task3_academic_closeout_report.md`. A future re-coding pass (or supervisor decision-register entry) would either assign canonical F4/F5-modality values from a re-read or formally tag the paper as a second scope-boundary case.

The figure intentionally shows **paper × modality bindings** at the segment level (867 bindings) because that's the supply-side characterization most useful for RQ1 landscape interpretation — it answers "how much of the corpus touches each (paradigm, modality) combination?" rather than "how are papers partitioned?"

## 6. Interpretation guidance

- **Do not sum stack segments and claim "the corpus has X papers."** Use the distinct-paper counts in §4 for corpus-count claims; use stack segments for coverage claims.
- **Pro-code dominance is a known corpus property** — 537 of 639 contributing papers (84%). Low-code and No-code sub-populations are thin; inferences about those paradigms should be cautious and noted as transferability limitations in §6 of the manuscript.
- **Modality stacks are not mutually exclusive within a paradigm.** A paper can appear in multiple modality stacks of the same paradigm bar.
- **Autonomous** modality is the most recent (post-2024) and would correlate with the emergence of agentic SE tools — expect it to grow in future re-runs.

## 7. Terminological clarifications

Beyond the mode-vs-modality disambiguation in §1:

- **F5 tool paradigm** — The *development paradigm* the tool targets. Pro-code = traditional hand-coded software; Low-code = visual-declarative platforms with code-escape (e.g., Power Platform, OutSystems); No-code = fully declarative platforms without code-escape. Single-valued per the codebook.
- **F5 tool interaction modality** — The *primary mode of AI–user interaction* as the tool is designed. Multi-valued because a tool (e.g., Cursor) can legitimately be both IDE-Integrated and Conversational.
- **"Tool profile"** (the figure's title noun) is the proposal's composite term for the `(paradigm, modality)` pair. It is an F5 concept, not a Phase 4 concept.

## 8. Methodological references

- Proposal §3.4 — F5 codebook entry; composite-tag specification.
- Proposal §3.5 RQ1 — "stacked bar chart or faceted plot distinguishing pro-code, low-code, and no-code tool profiles" is the proposal-specified figure.
- Proposal Appendix C Table 4 — provisional 8-mode *interaction-mode* taxonomy (inductive RQ2; NOT related to F5 modality).

## 9. Provenance

- **Script:** `code/analysis_rq1.py::fig4_f5_tool_profile_stacked`
- **Meta sidecar:** `f5_tool_profile_stacked.png.meta.json`.
- **Design spec:** `design/5_1_analysis_rq1.md`.
