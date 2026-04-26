# Threshold Sensitivity Extension (P20 / P25 / P33 / P40)

> **Deliverable class:** Phase 6 Task 6.5 — robustness check for the proposal §3.5 RQ3 25th-percentile gap rule; extends the Phase-5 `sensitivity_25_33.md` from two thresholds to four.
> **Generated:** 2026-04-20 UTC
> **Rater:** TBS
> **Plain-English question this document answers:** *"Is the 25th-percentile gap rule stable — would a nearby threshold (20 / 33 / 40%) produce substantively different gaps?"*

---

## Framing

The proposal §3.5 RQ3 commits to a single rule (25th percentile of non-zero cells) with a 33rd-percentile sensitivity check. This document extends the sensitivity band to **P20 / P25 / P33 / P40** — a wider bracket than the proposal's P25 / P33 baseline — so a reader can assess whether the gap set is an artefact of the specific percentile choice or a stable property of the evidence matrix. Petersen et al. (2015) §5.8 flags this class of sensitivity as standard SMS validity reporting.

The source matrix is `artifacts/analysis/rq3_gap_matrix/gap_matrix.csv` (171 cells, 19 capabilities × 9 SDLC activities). Gap definition retained verbatim per the proposal: `is_gap = (evidence_count > 0) AND (evidence_count <= P_threshold)` computed on **non-zero cells only**. Empty cells (`evidence_count == 0`) remain reported separately as a distinct interpretive category and are unaffected by threshold sensitivity.

Computation reuses `code/analysis_rq3.py::compute_percentile` — no new script; a 20-line inline Python snippet generates the tables below. This preserves dependability (one implementation, one test surface) per `dependability_audit.md §4`.

---

## 1. Threshold × gap-count table

| Percentile | Threshold value | Gap count | Empty cell count | Normal cell count | Δ gaps vs P25 |
|---:|---:|---:|---:|---:|---:|
| **P20** | 2.000 | 42 | 12 | 117 | 0 |
| **P25 (primary)** | 2.000 | 42 | 12 | 117 | — |
| **P33 (sensitivity)** | 3.140 | 53 | 12 | 106 | +11 |
| **P40** | 5.000 | 72 | 12 | 87 | +30 |

**Observations:**
- P20 and P25 yield **identical** thresholds (both = 2.0) on this corpus because the distribution of non-zero cells is right-skewed; the 20th and 25th percentiles both land on the same integer count. This is a corpus-specific property, not a methodological error.
- Empty-cell count is invariant at 12 across all thresholds — `is_empty` depends on `evidence_count == 0`, not on the percentile.
- No cell exits the gap set as the threshold rises. The P25 gap set is a **monotonic subset** of P33, which is a subset of P40. Confirmed by flip analysis in §2 below.

---

## 2. Flip analysis — which cells enter as the threshold rises

The table below shows the directional change from P25 (primary) to neighboring thresholds. "Added" = cell enters the gap set at the higher threshold; "Dropped" = cell exits.

### 2.1 P25 → P20 — no change (both thresholds = 2.0)

- Added: 0
- Dropped: 0

### 2.2 P25 → P33 — 11 added, 0 dropped

| Capability × SDLC | Evidence count | Bucket if promoted to gap |
|---|---:|---|
| CAP_CODEREVIEW × Requirements | 3 | design_gap (consistent with other Requirements gaps) |
| CAP_CODESUM × Debugging | 3 | organizational_readiness_barrier |
| CAP_CODETRANS × Code Review | 3 | organizational_readiness_barrier |
| CAP_CODETRANS × Debugging | 3 | organizational_readiness_barrier |
| CAP_CODETRANS × Documentation | 3 | organizational_readiness_barrier |
| CAP_MULTIAGENT × Project Management | 3 | adoption_lag |
| CAP_PLANNING × CI/CD | 3 | adoption_lag |
| CAP_PLANNING × Code Review | 3 | adoption_lag |
| CAP_REFACTORING × Project Management | 3 | organizational_readiness_barrier |
| CAP_REFACTORING × Requirements | 3 | design_gap |
| CAP_SYSDESIGN × CI/CD | 3 | design_gap |

### 2.3 P25 → P40 — 30 added, 0 dropped

At P40 (threshold = 5), the gap set grows by 30 cells relative to P25. The full list is in the script output at Phase 6 execution time; condensed view:

- **SDLC activities receiving newly-flagged cells (count):** CI/CD (5), Code Review (3), Project Management (7), Requirements (4), Design (2), Documentation (2), Debugging (4), Testing (3).
- **Capabilities most affected:** CAP_MULTIAGENT (+4 at P40 vs P25), CAP_CODETRANS (+3), CAP_SYSDESIGN (+3), CAP_VULNDET (+2), CAP_REFACTORING (+2), CAP_PROGREPAIR (+2), CAP_SELFREFLECT (+2), CAP_PLANNING (+2). Others gain 1 each.
- **No cell drops** from the P25 gap set at P40.

---

## 3. Robustness narrative

### 3.1 Monotonicity claim

The P25 gap set is **monotonically preserved** across the [P20, P40] band — every cell flagged at P25 remains flagged at higher thresholds. This property:

- Rules out the concern that the specific P25 choice produces idiosyncratic gaps that would disappear at a nearby threshold.
- Is a mathematical consequence of the gap rule (`count ≤ P_threshold`) and the monotonicity of percentiles on a non-decreasing threshold sequence — given for this dataset because the percentile function is well-behaved on the integer-valued `evidence_count` column.
- Does **not** itself establish that the P25 gap set is the "right" set of priority cells; it establishes that the set is *stable* against the threshold choice, which is the transferability claim readers need.

### 3.2 Expansion interpretation

At P33, the gap set grows by 11 cells — a **26% expansion** over P25. At P40, it grows by 30 cells (71% expansion). Two interpretations sit behind these expansions:

1. **The primary P25 rule is conservative.** The proposal explicitly chose P25 (not P33 or P40) to keep the gap set focused on the most-asymmetric cells. A reader who prefers a broader priority list can consult the P33 or P40 expansions.
2. **The P33 additions include two new agentic-capability gaps** (CAP_MULTIAGENT × Project Management; CAP_PLANNING × CI/CD, Code Review) that the P25 rule missed. These are arguably important additions to the `adoption_lag` bucket. The Phase 7 manuscript §6 should note this as a conservative-bias consequence of the P25 primary rule.

### 3.3 Empty-cell stability

The 12 empty cells (count = 0) remain empty at every threshold. Empty cells are, by proposal §3.5 RQ3 commitment, a distinct interpretive category — not gaps. Threshold sensitivity does not re-classify them. Their list is in `research_agenda.md §4` empty-cell appendix.

### 3.4 Sensitivity verdict

**The 25th-percentile gap rule is robust across the [P20, P40] band on this corpus.** No cell that is a gap at P25 ceases to be a gap at any nearby threshold; the only sensitivity effect is additive expansion at higher thresholds, which a reader can inspect via §2.2–§2.3 above. The proposal's primary-P25 / sensitivity-P33 commitment produces a conservative 42-gap core; P40 broadens to 72 gaps but is not the primary claim.

For manuscript §6 "Threats to Validity": the gap rule's threshold is a **scope choice**, not a **finding-sensitive knob**. A reader preferring P33 or P40 can consult the broader sets; the P25 set is the manuscript's primary ERP3 hand-off.

---

## 4. Reproducing this table

```python
import sys; sys.path.insert(0, '.')
import pandas as pd
from code.analysis_rq3 import compute_percentile

df = pd.read_csv('artifacts/analysis/rq3_gap_matrix/gap_matrix.csv')
for p in (20, 25, 33, 40):
    thr = compute_percentile(df, p)
    gaps = df[(df['evidence_count'] > 0) & (df['evidence_count'] <= thr)]
    empties = df[df['evidence_count'] == 0]
    print(f'P{p}: thr={thr:.3f}, gaps={len(gaps)}, empties={len(empties)}')
```

Expected output: exact match to §1 table above.

---

## References

- Proposal `docs/ERP2_Research_Proposal.docx` §3.5 RQ3 — single-rule gap definition + 33rd-percentile sensitivity clause.
- Petersen, K., Vakkalanka, S., & Kuzniarz, L. (2015). *Guidelines for conducting systematic mapping studies in software engineering: An update*. IST 64 — §5.8 threats-to-validity guidance.
- `artifacts/analysis/rq3_gap_matrix/sensitivity_25_33.md` — Phase-5 P25 vs P33 extension (this document subsumes it with P20 and P40 added).
