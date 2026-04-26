# Dependability Audit

> **Deliverable class:** Phase 6 Task 6.3 — qualitative-research dependability (Lincoln & Guba 1985; Cruzes & Dybå 2011 §VI) operationalized as a complete audit trail of every non-trivial judgement made across Phases 1–5.
> **Generated:** 2026-04-20 UTC
> **Rater:** TBS
> **Plain-English question this document answers:** *"Could another researcher follow the same decisions and reach a similar synthesis?"*

---

## Framing

Dependability is the trust-worthiness criterion parallel to positivist reliability (Lincoln & Guba 1985 §11.4). In SE thematic synthesis (Cruzes & Dybå 2011 §VI), dependability requires a **complete audit trail**: every non-trivial judgement — what rule was applied, what the alternative choice would have been, who made the call, when — is logged so an independent reviewer can retrace the reasoning and assess whether their own judgement would have produced a similar output.

This study's audit trail is `decision_register.csv` — a single append-only CSV maintained from Phase 1 through Phase 5. At Phase 6 close, the register contains **397 rows** distributed as follows:

| Phase | Rows | % of total |
|---:|---:|---:|
| 1 (Protocol) | 2 | 0.5% |
| 2 (Screening) | 24 | 6.0% |
| 3 (Extraction + Coding) | 325 | 81.9% |
| 4 (Synthesis) | 4 | 1.0% |
| 5 (Analysis) | 42 | 10.6% |
| **Total** | **397** | **100%** |

Column schema (fixed since Phase 0 initialisation): `timestamp,phase,paper_id,decision,rule_applied,rationale,rater_initials`.

---

## 1. Decision classes — 24 distinct slugs

The 397 rows distribute across 24 distinct `decision` slugs. The table below groups them by category and cites the controlling rule. The dominant slug (`f1_revised`, 323 rows) reflects routine extraction-time reclassification under a single rule and is narrated in §2.3 below.

| Decision slug | Count | Phase | Category | Rule applied (short) |
|---|---:|---:|---|---|
| `f1_revised` | 323 | 3 | Extraction classification | Wieringa F1 reclassified after full-text read |
| `hypothesis_for_erp3` | 42 | 5 | Gap-matrix interpretation | §3.5 RQ3 25th-percentile gap rule + adoption_lag / design_gap / organizational_readiness_barrier bucket |
| `screening_complete` | 4 | 2 | Screening milestone | Per-stage completion flag |
| `llm_review_executed` | 3 | 2 | LLM-assisted screening | Gemini-assisted title/abstract review |
| `llm_reviews_approved` | 3 | 2 | Rater-approved LLM output | Rater approval after spot-check |
| `dedup_executed` | 2 | 2 | Pipeline step | DOI-based de-duplication |
| `page_filter_executed` | 2 | 2 | Pipeline step | <4-page filter (short-paper exclusion) |
| `scis_enrichment_executed` | 2 | 2 | Pipeline step | SCIS venue-rank enrichment |
| `codebook_refined_post_pilot` | 1 | 1 | Protocol refinement | Pilot study → codebook §F1–F5 refinements |
| `retain_procode_capabilities_defer_lcnc` | 1 | 1 | Scope decision | Low-/no-code capabilities deferred to ERP3 as scope boundary |
| `scopus_search_executed` | 1 | 2 | Pipeline step | Scopus query run logged |
| `ieee_csdl_replaces_xplore` | 1 | 2 | Source revision | IEEE Xplore unavailable; CSDL substituted |
| `query_translated_ieee_csdl` | 1 | 2 | Source revision | Query translation to CSDL syntax |
| `query_translated_acm_dl` | 1 | 2 | Source revision | Query translation to ACM DL syntax |
| `ieee_search_removed` | 1 | 2 | Source revision | Duplicate IEEE entries removed after CSDL substitution |
| `openalex_enrichment_executed` | 1 | 2 | Pipeline step | OpenAlex enrichment for missing bibliographic metadata |
| `snowball_complete` | 1 | 2 | Milestone | Backward snowball round completion |
| `prisma_complete` | 1 | 2 | Milestone | PRISMA diagram reconciliation |
| `f3_scope_boundary_accepted` | 1 | 3 | Scope decision | 9 papers with non-developer populations (F3) coded closest-available |
| `a6_rule9_wording_patch_no_rerun` | 1 | 3 | Pipeline correction | `sample_description` rule 9 wording patched; no re-extraction (cost / benefit justified) |
| `c59_split_merge_recovery` | 1 | 4 | Data-loss recovery | Cluster 59 split/merge state repaired; `[m]erge-into` guard added |
| `task4_2_canonical_merge` | 1 | 4 | Taxonomy judgement | Cluster 149 merged into cluster 368 during Step-3 review |
| `task4_2_canonical_rename` | 1 | 4 | Taxonomy judgement | "Toolchain Embedding Depth" → "Workflow Integration Depth" |
| `taxonomy_finalised` | 1 | 4 | Milestone | 5-mode partition frozen; ERP3 hand-off ready |

---

## 2. Phase-by-phase narrative

### 2.1 Phase 1 — Protocol (2 rows)

- **`codebook_refined_post_pilot`** — The Phase 1 pilot (Task 1.3) exercised F1–F5 coding on a 10-paper seed set. Three codebook refinements landed: F1 added `Philosophical` and `Opinion` per Wieringa's full vocabulary; F4 split `Coding` from `Debugging`; F5 footnote `a` clarified the composite-tag multi-select rule. No re-pilot was necessary because the refinements tightened (never broadened) the vocabulary.
- **`retain_procode_capabilities_defer_lcnc`** — Task 1.4 considered harmonizing the three reference surveys' capabilities into a single master vocabulary regardless of paradigm. The alternative — to split capabilities by Pro-code / Low-code / No-code at the capability layer — was rejected. Rationale: the reference surveys all describe Pro-code capabilities; Low-code / No-code-specific capabilities would have to be induced from Phase 3 evidence and could not be pre-specified. Consequence: the paradigm dimension lives in F5, not in `capability_list.csv`; `gap_matrix_by_paradigm/` (Task 5.2) re-runs the gap rule per paradigm instead.

### 2.2 Phase 2 — Screening (24 rows)

Phase 2 decisions split into three classes:

1. **Source revisions (5 rows)** — `ieee_csdl_replaces_xplore`, `query_translated_ieee_csdl`, `query_translated_acm_dl`, `ieee_search_removed`, `scopus_search_executed`. IEEE Xplore was unavailable during Phase 2 execution; CSDL was substituted after Task 2.1 re-translation of the Scopus query. After the CSDL run, 41 duplicates with the prior Xplore attempt were removed. ACM DL required its own query translation. Each move is logged individually so the Phase 7 manuscript §3.2 search-strategy narrative reconciles to a single source of truth.
2. **Pipeline steps (9 rows)** — `dedup_executed`, `page_filter_executed`, `scis_enrichment_executed`, `openalex_enrichment_executed`, plus the LLM-assisted review steps (`llm_review_executed` × 3, `llm_reviews_approved` × 3). The pairing of `llm_review_executed` with `llm_reviews_approved` is deliberate — LLM output is never auto-adopted; the rater approves each batch after spot-check.
3. **Milestones (6 rows)** — `screening_complete` × 4 (one per screening stage: Stage-1 title/abstract, Stage-2 full-text, final PRISMA reconciliation, and the Phase-2 closeout marker), `snowball_complete`, `prisma_complete`. Each milestone is a stable checkpoint from which Phase 3 can resume.

No Phase 2 decision affected downstream phases beyond the screening exclusion set. No retractions.

### 2.3 Phase 3 — Extraction + Coding (325 rows)

**Dominant slug: `f1_revised` (323 rows).** Phase 3 extraction (Task 3.2) applied Wieringa F1 classes at full-text read-through. Because Stage-1 screening (Phase 2) applied F1 at abstract-level only, many papers needed F1 reclassification once the full text was available. Every reclassification is logged as a `f1_revised` row with the paper's DOI, the old F1 class → new F1 class pair, and the reviewing LLM model. This is not 323 separate research decisions; it is a single rule (`re-code F1 from full text if abstract-level F1 disagrees`) applied uniformly.

Rule source: Wieringa et al. (2006) full-text classification preference over abstract-inferred classification. Rater policy: accept LLM's full-text F1 unless spot-check disputes it.

Spot-check (from Task 3.3):
- 64-paper stratified sample was cross-model-verified post-extraction.
- 24 A5 `sample_size` disagreements found — rule 5 wording was patched at source (`a6_rule9_wording_patch_no_rerun`).
- 9 F3 `f3_population` disagreements found — all on papers with non-developer end-user populations (writers, older adults, accessibility QA testers). Logged as `f3_scope_boundary_accepted` (see §2.3.1 below).
- 0 F1 disagreements found post-patch — the dominant `f1_revised` slug was acting as intended.

**`f3_scope_boundary_accepted` (1 row).** 9 papers had participants outside the F3 `VALID_F3_POP` vocabulary (Professional SWE / Student / Citizen Developer / OSS Contributor / Mixed / N/A). Options considered: (a) extend vocabulary to include `End-user`; (b) accept boundary + document; (c) exclude via EC3. Option (b) chosen. Rationale: the 9 papers still study valid human-AI-for-SE interactions and belong in the corpus per IC1–IC3; extending F3 mid-study would destabilise Phase 2 F1/F3 calibration. Full paper list in the register row rationale.

**`a6_rule9_wording_patch_no_rerun` (1 row).** 14 A6 `sample_description` failures traced to over-aggressive rule-9 wording in `code/extraction.py`. Rule 9 patched; no re-extraction. Rationale: A5 `sample_size` is the RQ1-critical field (A5 is correct); no Phase 4/5 consumer keys on `sample_description`; re-extraction cost (~$15 + half-day) not justified. Rule 9 wording preserved in the register row for full reproducibility.

### 2.4 Phase 4 — Synthesis (4 rows)

- **`c59_split_merge_recovery`** — Cluster 59 in Task 4.1 had a split/merge action sequence that caused two pass-1 codes to be silently orphaned. Recovery logged in full: state flipped `split → approved`; members de-duplicated (4 → 2); `member_passage_map` reconciled; recovery label stamped `AT-recovery`. Root-cause patched in `code/coding_consolidate.py` (new guard on `[m]erge-into` rejects `split`/`merged` targets). Backups preserved: `.consolidate_state.json.bak-before-c59-recovery` + `consolidated_codes.csv.bak-before-c59-recovery` (both now under `artifacts/synthesis/archive/`).
- **`task4_2_canonical_merge`** — Cluster 149 "Iterative Prompt Refinement" merged into cluster 368 "Iterative Prompting Refinement" during Step-3 strawman review. 7 + 9 → 16 members. Zero semantic daylight between the two labels — both were retention-biased duplicates from Task 4.1's 0.35 clustering threshold. Bidirectional trace preserved.
- **`task4_2_canonical_rename`** — "Toolchain Embedding Depth" → "Workflow Integration Depth". Reason: original Title-Case LLM proposal phrased the concept awkwardly; the member-code vocabulary ("workflow integration") is more readable and appears in the Residuals sub-categorization.
- **`taxonomy_finalised`** — 5-mode partition (Inline Completion / Conversational Prompting / Visual-Declarative Composition / Review & Validation / Delegated Task Execution) + Residuals (outcome 192 / constraint 119 / meta 101 / affordance 56) frozen. Mode-layer saturation verdict Saturated. Paraphrase linter 0 / 6,295. DoD dispatcher green. No further mode re-opens without manuscript-§6 amendment.

### 2.5 Phase 5 — Analysis (42 rows)

All 42 Phase-5 rows are `hypothesis_for_erp3` applications of the §3.5 RQ3 25th-percentile gap rule. Each row binds one (capability_id × SDLC activity) gap cell to one rationale bucket:

- `organizational_readiness_barrier` (22 gaps) — mature capabilities with low empirical evidence at non-native SDLC activities (e.g., CAP_COMMITMSG at CI/CD, CAP_CICD at Code Review). Bucket hypothesis: deployment exists but adoption is gated by organizational or process factors rather than technical capability.
- `design_gap` (14 gaps) — capabilities with low evidence at early-lifecycle activities (Design, Requirements). Bucket hypothesis: tool designers have not yet surfaced the capability at those activities; future ERP3 work could explore.
- `adoption_lag` (6 gaps) — emerging agentic capabilities (CAP_MULTIAGENT, CAP_SELFREFLECT) where supply-side research has outrun empirical deployment. Bucket hypothesis: research-to-practice lag.

These buckets are **ERP3 hypotheses, not SMS classifications**. The bucket vocabulary lives only in `decision_register.csv`, never as a column in `gap_matrix.csv` — the separation is enforced by `check_phase5_task5_2` invariant 4.

Every bucket choice is auditable: the register rationale states the bucket + the capability × SDLC pair + one sentence of reasoning. The rater (TBS) made each bucket call according to the heuristic:
- Requirements / Design → `design_gap` (early-lifecycle asymmetry).
- Agentic capabilities (MULTIAGENT, SELFREFLECT) → `adoption_lag` (research-to-practice lag).
- Otherwise → `organizational_readiness_barrier` (default for mature capabilities with non-native SDLC gaps).

---

## 3. Codebook stability across phases

A reproducible synthesis requires a stable coding vocabulary. This study's vocabulary is documented in three artefacts — `codebook.md` (F1–F5), `extraction_schema.md` (matrix columns), `capability_list.csv` (19 harmonized capability IDs). The table below records any changes to each across Phases 1–5.

| Artefact | Phase 1 | Phase 2 | Phase 3 | Phase 4 | Phase 5 | Stable? |
|---|---|---|---|---|---|---|
| `codebook.md` F1–F5 vocabulary | Pilot-refined (`codebook_refined_post_pilot`) | Unchanged | Unchanged | Unchanged | Unchanged | ✅ stable after Phase 1 |
| `codebook.md` F3 vocabulary values | 6 values | 6 values | 9 papers coded closest-available (F3 scope boundary) | N/A | N/A | ✅ vocabulary unchanged; scope boundary documented |
| `extraction_schema.md` (rule 9 wording) | Initial | Initial | **Patched mid-Phase-3** (`a6_rule9_wording_patch_no_rerun`) | Unchanged | Unchanged | ✅ one documented patch; no re-extraction required |
| `capability_list.csv` (19 harmonized IDs) | Built in Task 1.4 | Unchanged | Unchanged | Unchanged | Unchanged | ✅ stable since Phase 1 |
| Interaction-mode vocabulary | Provisional 8 (proposal Appendix C) | N/A | N/A | **Collapsed to 5** (Step-2 rationale in `task4_2_todo.md`) | Unchanged | ✅ one documented refinement pre-Step-4; frozen at `taxonomy_finalised` |

**Summary:** the coding vocabulary was refined once in Phase 1 (pilot-driven), patched once in Phase 3 (rule-9 wording, no re-extraction needed), and collapsed once in Phase 4 Step 2 (provisional 8 → empirical 5 with data-driven rationale). These refinements are all documented in the register with the rule applied. No silent vocabulary drift.

---

## 4. Reproducibility claims

- **Deterministic scripts** — `code/coding_consolidate.py`, `code/taxonomy_classify_llmassist.py`, `code/taxonomy_render.py`, `code/saturation_report.py`, `code/paraphrase_linter.py`, `code/analysis_rq1.py`, `code/analysis_rq2_variation.py`, `code/analysis_rq3.py`, `code/prioritize_gaps.py`. All use `seed=42` via `utils.write_with_meta` + deterministic sort orders (e.g., `prioritize_gaps.py` tie-breaks alphabetically for byte-identical re-runs).
- **Idempotence guards** — `analysis_rq3.py` skips duplicate register appends; `coding_consolidate.py [m]erge-into` rejects `split`/`merged` targets post-c59 incident.
- **DoD dispatchers** — 5 phases × 1 dispatcher each (plus `phase6_task6_1` landing in this commit). Every run verifies structural invariants; any drift surfaces immediately.
- **Version-pinned inputs** — `sentence-transformers/all-MiniLM-L6-v2` (384-dim, cached); `gemini-3-flash-preview` for Phase 4 label proposal (documented in `task4_tracker.md §5.1`); `gemini-3.1-pro-preview` for Task 4.2 LLM pre-pass.
- **Git-tagged phase milestones** — `phase1-complete`, `phase3-rc1`, `phase3-complete`, `phase4-complete`, `phase5-complete` (this commit will add `phase6-complete`). Each tag is annotated with the phase's closeout summary.

---

## 5. What would break reproducibility (honest disclosure)

Three known risks documented here rather than hidden:

1. **LLM model drift** — if `gemini-3-flash-preview` behavior changes or the model is deprecated, Phase 4 Task 4.1 label proposal may produce different labels on re-run. Mitigation: raw LLM output is cached at `.taxonomy_classify_llmsuggest.json` (archived); labels can be regenerated from cache or re-run with a different model via `--llm-model` flag.
2. **Sentence-transformer model drift** — `all-MiniLM-L6-v2` embeddings are deterministic per model version; a future model update would shift cosine distances and could change cluster boundaries. Mitigation: embedding cache committed at `.embeddings_cache.npz` (archived).
3. **Register regex fragility** — Phase 5 `prioritize_gaps.py` parses Phase-5 `hypothesis_for_erp3` rationales via regex to join to gap rows. If a future append rewrites the rationale format, the parse would fail. Mitigation: hard assert at regex match site; script fails fast with the offending row printed (not a silent data loss).

None of these is currently affecting the synthesis; all are named so a future re-runner knows where to start.

---

## References

- Lincoln, Y. S., & Guba, E. G. (1985). *Naturalistic Inquiry*. Sage Publications.
- Cruzes, D. S., & Dybå, T. (2011). *Recommended Steps for Thematic Synthesis in Software Engineering*. ESEM.
- Wieringa, R., Maiden, N., Mead, N., & Rolland, C. (2006). *Requirements engineering paper classification and evaluation criteria: a proposal and a discussion*. REJ 11(1).
