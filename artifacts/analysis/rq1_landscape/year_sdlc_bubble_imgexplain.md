# Explanation — `year_sdlc_bubble.png`

> **Figure purpose.** Descriptive RQ1 landscape view of where empirical AI-SE studies sit along three dimensions simultaneously: **publication year**, **SDLC activity (F4)**, and **developer population (F3)**. One sub-panel per F3 population value; one bubble per `(year, SDLC activity)` cell inside each panel.

## 1. Source data

| Field | Source | Role |
|---|---|---|
| `paper_id` | `artifacts/extraction/extraction_matrix.csv` | Counting key (distinct-paper counts). |
| `year` | `extraction_matrix.csv` | X-axis; `pd.to_numeric(..., errors="coerce")` coerces non-numeric to NaN (NaN rows dropped). |
| `f4_sdlc_activity` | `extraction_matrix.csv` | Y-axis. Pipe-separated multi-value string (e.g. `"Coding\|Debugging"`); see §3 for handling. |
| `f3_population` | `extraction_matrix.csv` | Panel facet (one panel per canonical value). |

## 2. Counting unit

Each bubble is a **distinct-`paper_id` count** over the triple `(year, f4_sdlc_activity, f3_population)`. Formally, for panel `p`:

```
cell_count(p, y, s) = |{ paper_id : f3_population = p ∧ year = y ∧ s ∈ f4_sdlc_activity.split('|') }|
```

Bubble **area** (not radius) is proportional to `cell_count` (scaled as `20 + 30 * count` pixels² for legibility).

## 3. Multi-valued SDLC handling

`f4_sdlc_activity` is **multi-value** per proposal §3.4 — a single paper can describe multiple SDLC activities. We **explode** the pipe-separated values so a paper with `"Coding|Debugging"` contributes to the `Coding` row **and** the `Debugging` row within the same year panel.

Consequence: **intra-panel bubble areas do not sum to the panel's distinct-paper count.** Multi-SDLC papers are counted once per SDLC activity they describe (by design — a paper that studied both coding and debugging is evidence for both). The panel subtitle reports the **distinct-paper** count for the panel (via `.nunique()`), which is lower than the sum of bubble areas.

Corpus-level multi-SDLC distribution (among the 635 papers with ≥1 SDLC activity):

- Single-SDLC papers: 365
- Multi-SDLC papers: 270 (max 9 activities; mean 1.71 activities per non-empty paper)
- Papers with no SDLC tag: 5

Grand total paper × SDLC bindings across the corpus: **1,083** (vs. N = 640 papers).

## 4. Why totals may not add to 640

The figure shows **only 392 of 640 papers**. Three filters (applied in the order the plotting code applies them) explain the 248-paper exclusion:

1. **SDLC-activity filter (applied first by `explode_pipe`).** Rows with empty/NaN `f4_sdlc_activity` are dropped before counting, because a paper with no F4 tag cannot be placed in any `(year, SDLC)` cell. This removes 5 papers corpus-wide (2 of which have canonical F3 population — see `§4 Exclusion accounting` below).
2. **F3 population filter.** 246 papers have `f3_population` NaN (the facet-key is missing) and are excluded from every panel. This is the dominant exclusion.
3. **Year filter.** Rows with non-numeric or NaN `year` are dropped (negligible in the current extraction).

The 392 plotted papers are partitioned across five panels by canonical F3 population (disjoint partition, so per-panel counts sum to 392):

| Panel (F3 population) | Distinct papers |
|---|---:|
| Student | 133 |
| Professional SWE | 128 |
| Mixed | 109 |
| Citizen Developer | 19 |
| OSS Contributor | 3 |
| **Total plotted** | **392** |
| Excluded (canonical F3 but empty F4) | 2 |
| Excluded (F3 NaN) | 246 |
| Excluded (year NaN; already inside F3-NaN) | ≈0 net |
| **N corpus** | **640** |

### Exclusion accounting — the 2 canonical-F3 papers with empty F4

| `paper_id` | `year` | `f3_population` | `f4_sdlc_activity` |
|---|---:|---|---|
| `doi:10.1109/icodse68111.2025.11351919` | 2025 | Mixed | *(empty)* |
| `doi:10.1109/icei64305.2024.10912343` | 2024 | Mixed | *(empty)* |

Both have canonical F3 `Mixed` but no SDLC activity tagged; they are factually excluded from the plot because no bubble cell exists for them. Hence the **Mixed panel reports n=109**, not 111 (which would be the count of all Mixed papers in the corpus). This is the honest denominator per the CLAUDE.md figure-caption convention.

The 246 F3-NaN exclusions are documented in `task3_academic_closeout_report.md` as a Phase-3 scope boundary. They are not suppressed from Phase 5 — they still appear in Figures 2–4 where F3 population is not a plotting axis.

## 5. Interpretation guidance

- **Use the figure for joint distribution, not for absolute totals.** The bubbles answer "where does empirical evidence concentrate jointly across (year, SDLC, population)?" — not "how many papers are there per cell?" The sum of bubble areas is not a corpus count.
- **Read by-panel, not across panels.** Panel subtitles report distinct-paper counts; bubble positions show where that panel's evidence clusters.
- **Absent bubbles signal absence of evidence for that (year × SDLC × population) combination in the included corpus.** They do not imply the combination is impossible.
- **Citizen Developer and OSS Contributor panels are sparse** (19 and 3 distinct papers). Their bubble patterns should not drive inference; they surface corpus thin-ness.

## 6. Terminological clarifications

- **SDLC activity (F4)** is the proposal-codebook facet. Its 9 values are: Requirements, Design, Coding, Testing, Code Review, Debugging, CI/CD, Documentation, Project Management.
- **Developer population (F3)** is the *who* — characterizes the human users in the study. Five canonical values are: Student, Professional SWE, Citizen Developer, OSS Contributor, Mixed.
- **Bubble area** encodes count, **not radius** — a bubble twice as "big" represents twice as many papers. (If you were to compare by radius you would under-estimate the contrast.)

## 7. Methodological references

- Proposal §3.5 RQ1 — bubble plots recommended as systematic-mapping-study convention.
- Petersen et al. (2008) Fig. 4 — bubble-plot template; distinct-paper counting is the Petersen convention.
- Proposal §3.4 — F3/F4 codebook entries (multi-select F4 is per the codebook footnote).

## 8. Provenance

- **Script:** `code/analysis_rq1.py::fig1_year_sdlc_bubble`
- **Meta sidecar:** `year_sdlc_bubble.png.meta.json` (git SHA, input manifest, timestamp, seed).
- **Design spec:** `design/5_1_analysis_rq1.md`.
