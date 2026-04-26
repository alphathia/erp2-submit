# ERP2 — Systematic Mapping Study of AI-Agent Usage in Software Engineering

**How Do People Use AI Agents for Software Engineering? A Systematic Mapping Study of Usage Patterns, Interaction Modes, and Capability-Usage Gaps in Research Literature.**

This repository is the reproducibility bundle for the ERP2 SMS report. The formatted final report is **[`erp2_report_submission.pdf`](erp2_report_submission.pdf)** at the root of this repo. Everything else in the repo is the evidence and code that backs the report's claims.

---

## 1. Headline outcomes

Corpus of **640 included papers** (Scopus + ACM DL, 2022 – early 2026; backward-snowballed from 5 seed surveys).

| RQ | Output | Where |
|---|---|---|
| RQ1 — Landscape | 4 figures + descriptive stats | `artifacts/analysis/rq1_landscape/` |
| RQ2 — Interaction-mode taxonomy | 5 modes + Residuals; saturation: **Saturated** | `artifacts/synthesis/interaction_taxonomy.md` |
| RQ3 — Capability-evidence gaps | 19 × 9 gap matrix (171 cells); 42 gaps at P25 | `artifacts/analysis/rq3_gap_matrix/` |
| RQ4 — Research agenda (ERP3 hand-off) | 6 Wieringa-typed study calls; 42 ranked gaps | `artifacts/analysis/research_agenda.md`, `prioritised_gaps.md` |
| Trustworthiness | Cruzes & Dybå 4-criteria + Wieringa self-assessment + threshold sensitivity + novelty | `artifacts/trustworthiness/` (6 MDs) |

---

## 2. Folder map

```
erp2/
├── README.md                       ← this file
├── erp2_report_submission.pdf      ← final report (main article + appendices A–H)
├── decision_register.csv           ← append-only audit trail (397 rows, all phases)
├── requirements.txt                ← Python 3.11+ deps (pinned)
├── .env.example                    ← API-key template (full-pipeline path only)
│
├── docs/
│   ├── methodology/                ← Petersen × 2, Cruzes & Dybå × 2, Wieringa, Lincoln & Guba
│   └── seeds/                      ← 5 snowballing seed papers
│
├── code/                           ← Python scripts (see §3 for the per-phase index)
├── tests/                          ← pytest unit tests
│
└── artifacts/                      ← all research outputs
    ├── protocol/                   (codebook, IC/EC, search strings, capability list)
    ├── search/                     (raw + enriched + post-filtered CSVs)
    ├── screening/                  (decisions, included_set, PRISMA flow)
    ├── extraction/                 (extraction_matrix, raw_passages/, capability_annotations, open_codes)
    ├── synthesis/                  (consolidated_codes, taxonomy_classifications, interaction_taxonomy, saturation reports)
    ├── analysis/                   (rq1_landscape/, rq2_variation/, rq3_gap_matrix/, prioritised_gaps, research_agenda)
    └── trustworthiness/            (credibility, confirmability, dependability, transferability, threshold_sensitivity, contribution_novelty)
```

---

## 3. Pipeline scripts (by execution order)

**Phase 2 — Search & screening.** `scopus_search.py` (Scopus API), `acm_bib2csv.py` (ACM BibTeX → CSV), `openalex_enrich.py` (OpenAlex metadata), `scis_enrich.py` + `enrich_scis_authors.py` (SCIS venue + author enrichment), `dedup.py` (cross-source dedup), `page_filter.py` (EC1 page-count exclusion), `snowball.py` (backward snowballing from seed surveys), `screening_harness.py` (interactive title/abstract screener), `llm_review.py` + `llm_review_approve.py` (LLM-assisted second pass), `screening_verify.py` (consistency check), `prisma_builder.py` (PRISMA flow render).

**Phase 3 — Full-text extraction.** `retrieval.py` (fetch PDFs), `extraction.py` (LLM-driven F1–F5 facet coding + capability annotation + first-pass open coding), `extractionspotcheck.py` (cross-model spot-check QA), `extraction_matrix_enrich.py` (join matrix with annotations + open codes for downstream use).

**Phase 4 — Code consolidation & taxonomy.** `coding_consolidate.py` (Cruzes Step 3: cluster pass-1 codes into canonical labels), `taxonomy_classify.py` + `taxonomy_classify_llmassist.py` (Step 4: canonical labels → 5 interaction modes), `taxonomy_render.py` (write `interaction_taxonomy.md`), `saturation_report.py` (saturation curve + verdict).

**Phase 5 — Analysis.** `analysis_rq1.py` (RQ1 landscape figures), `analysis_rq2_variation.py` (RQ2 mode-variation cross-tabs), `analysis_rq3.py` (RQ3 gap matrix + sensitivity), `prioritize_gaps.py` (rank gaps + feed the research agenda).

**Phase 6 — Trustworthiness.** `trace_checker.py` (DoD enforcer for credibility / confirmability / dependability / transferability coverage).

**Phase 8 — Bibliography (deferred to May 2026).** `build_zotero_import.py`, `reconcile_bib.py`, `zotero_author_audit.py` — Zotero integration scripts.

**Cross-cutting.** `utils.py` (shared helpers: `write_with_meta`, `paper_id` normalisation, `git_sha`); `paraphrase_linter.py` (15+ word verbatim check on synthesised Markdown); `dod_checks.py` (Definition-of-Done dispatcher across all phases).

---

## 4. Reproducing the analysis

The Phase 3 extraction matrix and Phase 4 taxonomy are **frozen** in `artifacts/`. Re-running the downstream analysis from these frozen inputs is deterministic, free, and takes minutes — no LLM API access required.

```bash
# Setup (Python 3.11+)
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Verify frozen inputs are intact
python code/dod_checks.py phase4_task4_2     # taxonomy + saturation
python code/dod_checks.py phase5_task5_1     # RQ1 figures + RQ2 cross-tabs
python code/dod_checks.py phase5_task5_2     # RQ3 gap matrix + sensitivity
python code/dod_checks.py phase6_task6_1     # trustworthiness deliverables

# Re-generate analysis outputs
python code/analysis_rq1.py                  # → artifacts/analysis/rq1_landscape/
python code/analysis_rq2_variation.py        # → artifacts/analysis/rq2_variation/
python code/analysis_rq3.py                  # → artifacts/analysis/rq3_gap_matrix/
python code/prioritize_gaps.py               # → artifacts/analysis/prioritised_gaps.md
```

Each script writes its output with a `.meta.json` sidecar (script, inputs, git SHA, timestamp). Outputs should be byte-identical to the committed copies modulo timestamp.

The paraphrase linter — `python code/paraphrase_linter.py --target <file>` — enforces that no 15+ word string in any synthesised Markdown appears verbatim in `artifacts/extraction/raw_passages/*.md`. Expected output on every committed Markdown: `0 violations`.

---

## 5. Methodological anchors

Source PDFs in `docs/methodology/`:

| Anchor | Used for |
|---|---|
| Petersen et al. (2008, 2015) | SMS design: keywording, classification facets, PRISMA, bubble plots, reporting structure. |
| Cruzes & Dybå (2011); Cruzes et al. (2015) | Inductive thematic synthesis Steps 1–5; trustworthiness package. |
| Wieringa et al. (2006) | Research-type boundaries; 6-criterion contribution self-assessment. |
| Lincoln & Guba (1985) | Origin of the four-criterion trustworthiness framework. |
| Ali & Petersen (2014) | Study-selection process discipline. |

Five additional seed papers (`docs/seeds/`) were used for backward snowballing only, never as primary corpus.

---

## 6. Full-pipeline reproduction (search → screening → extraction → synthesis)

Re-running the upstream pipeline requires Elsevier / OpenAlex / Unpaywall / Google Gemini API keys (see `.env.example`), costs ~US$15.50 in LLM calls, takes hours, and contains non-deterministic LLM steps and interactive rater judgement (Phase 4 cluster review and mode naming). For most reviewers, the analysis-only path in §3 is sufficient.
