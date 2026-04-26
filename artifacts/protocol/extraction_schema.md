# Extraction Schema for `artifacts/extraction/extraction_matrix.csv`

Source: `artifacts/protocol/codebook.md`, `artifacts/protocol/inclusion_exclusion.md`. Methodology: Cruzes & Dybå (2011, 2015) extraction/synthesis separation; Petersen (2008, 2015) facet-based classification.

The extraction matrix is organised into three explicit regions. Every row represents one empirical study instance (a single paper may contribute multiple rows if it reports distinct studies, cohorts, or contexts).

---

## Region 1 — Metadata

### M1: Bibliographic

| Column | Type | Description |
|--------|------|-------------|
| `paper_id` | string | **Primary key.** Normalised DOI (lowercase, no `https://doi.org/` prefix). |
| `title` | string | Full paper title. |
| `authors` | string | Semicolon-separated author list. |
| `year` | int | Publication year. |
| `venue` | string | Journal name or conference proceedings title. |
| `venue_type` | enum | `journal` or `conference`. |
| `doi` | string | Full DOI URL for reference. |

### M2: Sample and Duration

| Column | Type | Description |
|--------|------|-------------|
| `sample_size` | int or null | Number of **human participants** studied. Null if not reported or if the study has no human participants (dataset-only / benchmark-based). Do NOT populate with artifact counts (bug reports, code samples, repositories mined, benchmark instances, generated outputs, etc.). |
| `sample_description` | string or null | Brief description of who/what was sampled. For human-participant studies: e.g., "42 professional developers at Company X". For dataset/benchmark studies: describe the artefact sample (e.g., "100 Android apps", "587 patch reviews", "36,000 generated code snippets"). Null only if the paper reports no sample information at all. |
| `study_duration` | string or null | Duration of the empirical study as reported (e.g., "6 weeks", "one semester"). Null if cross-sectional or not reported. |

---

## Region 2 — Facets (F1–F5)

Coded per `artifacts/protocol/codebook.md`. Each value must match the controlled vocabulary defined there.

| Column | Type | Controlled values | Source in paper |
|--------|------|-------------------|-----------------|
| `f1_contribution_type` | enum | Evaluation Research, Validation Research, Solution Proposal, Philosophical, Opinion, Personal Experience | Title + Abstract |
| `f2_research_methodology` | enum | Survey, Interview, Case Study, Experiment, Field Study, Mining Study, Mixed | Abstract / Method section |
| `f3_population` | enum | Professional SWE, Student, Citizen Developer, OSS Contributor, Mixed, N/A | Full text |
| `f3_context` | enum | Industry, Education, OSS, Lab, N/A | Full text |
| `f4_sdlc_activity` | multi-enum | Requirements, Design, Coding, Testing, Code Review, Debugging, CI/CD, Documentation, Project Management | Full text |
| `f5_tool_modality` | multi-enum | Autocomplete, Conversational, IDE-Integrated, Autonomous | Full text |
| `f5_tool_paradigm` | enum | Pro-code, Low-code, No-code | Full text |
| `f5_tool_name` | string | Free text — specific tool(s) studied (e.g., "GitHub Copilot", "Power Platform"). | Full text |

**Notes:**
- `f3_population` and `f3_context` are the two axes of the F3 composite facet. Both take the value `N/A` when the paper has no human participants (benchmark evaluation, mining of artifacts with no human subjects). Do NOT infer a population from the data source (a paper mining GitHub repos with no human study is `N/A` / `N/A`, not `OSS Contributor` / `OSS`).
- `f5_tool_modality` and `f5_tool_paradigm` are the two sub-facets of F5 (Agent/Tool Profile). `f5_tool_modality` is multi-select; `f5_tool_paradigm` is single-select.
- `f4_sdlc_activity` is multi-select (pipe-delimited, e.g., `Coding|Testing`).
- `f5_tool_modality` is multi-select (pipe-delimited, e.g., `Autocomplete|IDE-Integrated`).

---

## Region 3 — Synthesis-Register Inputs

These columns point to downstream synthesis artifacts. They are **not** coded values — they are file locations and flags that feed Phase 4 (thematic synthesis) and Phase 5 (gap analysis). Per Cruzes & Dybå, synthesis outputs (Interaction Mode, Capability Category) are derived from these inputs, not stored in the extraction matrix.

| Column | Type | Description |
|--------|------|-------------|
| `raw_passages_file` | string | Path to the verbatim passage file for this paper: `artifacts/extraction/raw_passages/{paper_id}.md`. Created during Task 3.2. |
| `capability_annotations_file` | string | Path to capability annotation rows for this paper in `artifacts/extraction/capability_annotations.csv`. Links `paper_id` to `capability_id` values from `artifacts/protocol/capability_list.csv`. |
| `open_codes_tagged` | boolean | `true` once first-pass open codes (Task 3.3) have been assigned for this paper. |
| `extraction_complete` | boolean | `true` once all Region 1 + Region 2 columns and both synthesis-register pointers are populated and reviewed. |
| `notes` | string or null | Free-text notes on extraction difficulties, borderline decisions, or items requiring follow-up. |
