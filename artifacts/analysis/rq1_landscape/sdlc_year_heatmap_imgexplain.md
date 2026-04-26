# Explanation — `sdlc_year_heatmap.png`

> **Figure purpose.** Heatmap showing how empirical AI-SE evidence distributes across **SDLC activity (F4)** rows and **publication year** columns. Cell intensity (and annotated value) = distinct papers in that `(SDLC activity, year)` cell.

## 1. Source data

| Field | Source | Role |
|---|---|---|
| `paper_id` | `artifacts/extraction/extraction_matrix.csv` | Counting key. |
| `year` | `extraction_matrix.csv` | X-axis; NaN dropped. |
| `f4_sdlc_activity` | `extraction_matrix.csv` | Y-axis. **Multi-valued** pipe-separated column — see §3. |

## 2. Counting unit

Each cell is a **distinct-`paper_id` count** over the pair `(f4_sdlc_activity, year)`:

```
cell_count(s, y) = |{ paper_id : s ∈ f4_sdlc_activity.split('|') ∧ year = y }|
```

## 3. Multi-SDLC papers — how the figure handles them

Per proposal §3.4, a single paper can describe multiple SDLC activities (e.g., a study of an AI tool that supports both code generation and debugging would be coded `"Coding|Debugging"` in F4). We treat the pipe as a list delimiter:

1. **Explode** `f4_sdlc_activity` on `|` so each paper produces as many rows as it has SDLC tags.
2. After explosion, count **distinct papers** per `(SDLC, year)` cell (via `.nunique()`).

### Consequence: the heatmap over-counts papers at the grand-total level, but correctly counts evidence at the cell level

- A paper with two SDLC tags contributes to **two rows**, once each — this is epistemically correct because the paper is evidence for both activities.
- Therefore **the sum of all cell values exceeds the distinct-paper count**. Grand total: **1,083 paper × SDLC bindings**; distinct papers contributing: **635** (5 of 640 have no F4 tag at all).
- Row sums (per SDLC activity) also over-count the corpus: a paper tagged `"Coding|Testing"` appears in both the Coding row and the Testing row, not split between them.
- Column sums (per year) also reflect over-counting.

| Quantity | Value |
|---|---:|
| Papers with ≥1 SDLC activity tag | 635 |
| Papers with F4 = NaN (excluded) | 5 |
| Single-SDLC papers | 365 |
| Multi-SDLC papers | 270 |
| Mean SDLC tags per contributing paper | 1.71 |
| Max SDLC tags on one paper | 9 (all nine activities) |
| Grand total paper × SDLC bindings | 1,083 |

### Alternative would have been problematic

We considered two rejected alternatives:

- **Fractional assignment** (a paper with 2 SDLC tags contributes 0.5 to each cell). Rejected because cells become non-integer and harder to interpret; also misrepresents the epistemology ("the paper studied BOTH activities" is not "half a study per activity").
- **First-tag-only** (take only the first SDLC activity listed). Rejected because tag order in the extraction does not carry semantics — a paper whose F4 is `"Testing|Coding"` would be classed as Testing-only, discarding real coding evidence. Order artefacts should not drive SDLC coverage analysis.

**Explode-and-count distinct** is the Petersen (2008) convention for multi-valued facets and is the epistemically cleanest choice: each `(SDLC, year)` cell shows how much distinct-paper evidence exists for that pair, acknowledging multiple papers can be evidence for more than one row.

## 4. Why totals may not add to 640

Two reasons:

1. **5 papers have NaN F4** and are dropped — their evidence is invisible in this figure. They still appear in Figures 2 and 4 where F4 is not a plotting axis.
2. **Multi-SDLC papers inflate the grand total** from 635 distinct papers to 1,083 paper × SDLC bindings. The figure intentionally shows bindings, not distinct-paper counts, at the cell level.

Neither 1 nor 2 is a defect — both are documented in the script (`code/analysis_rq1.py::fig3_sdlc_year_heatmap`) and in the design spec.

## 5. Interpretation guidance

- **Row totals = SDLC-activity coverage.** Sum along a row to estimate how much evidence exists for that activity across all years (with over-counting from multi-SDLC papers noted). For a defect-free corpus count per SDLC, use `decision-register`-style deduped aggregates or consult `capability_annotations.csv`.
- **Column totals = per-year volume (over-counted).** Sum along a column overestimates yearly publication count due to multi-SDLC inflation.
- **Diagonal-like clusters signal emerging coverage.** If a new SDLC activity develops evidence only in recent years, the cell pattern will concentrate toward the right edge of that row.
- **Empty cells do not imply "no research exists."** The corpus is the included set only (proposal §3.3 screening outcome); a dark cell means "no *included paper* in our corpus covers that (SDLC, year) pair."

## 6. Terminological clarifications

- **SDLC activity (F4)** — the 9-value proposal-codebook vocabulary. Listed in §F4 of the codebook.
- **Paper × SDLC binding** — one `(paper_id, SDLC activity)` tuple after pipe explosion. Sum of bindings across cells = 1,083; sum of distinct papers = 635.
- The figure's colour bar is labelled **"Distinct papers in cell"** to disambiguate — each cell's annotated integer is the distinct-`paper_id` count for that cell alone, not a per-row or per-column share.

## 7. Methodological references

- Proposal §3.5 RQ1 — "heatmaps depicting SDLC coverage over time" is the proposal-specified figure.
- Petersen et al. (2008) Table 3 — the SDLC × year cross-tab is a standard SMS reporting artefact for the evidence-landscape dimension.
- Multi-valued facet handling follows Petersen et al. (2015) §6.2.

## 8. Provenance

- **Script:** `code/analysis_rq1.py::fig3_sdlc_year_heatmap`
- **Meta sidecar:** `sdlc_year_heatmap.png.meta.json`.
- **Design spec:** `design/5_1_analysis_rq1.md`.
