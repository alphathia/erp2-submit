# Sensitivity analysis: P25 vs P33 gap thresholds

**Artifact:** `artifacts/analysis/rq3_gap_matrix/sensitivity_25_33.md`
**Script:** `code/analysis_rq3.py`
**Source:** proposal §3.5 RQ3, sensitivity clause

## Thresholds

- **P25** (primary) = 2.000 (25th percentile of non-zero cells).
- **P33** (sensitivity) = 3.140 (33rd percentile of non-zero cells).

## Gap counts

- Cells flagged as gap at **P25**: **42** of 171.
- Cells flagged as gap at **P33**: **53** of 171.
- Cells flagged as empty (count == 0, reported separately): **12** of 171.

## Interpretation

As expected, relaxing the threshold from P25 to P33 inflates the gap count: 53 cells vs 42 at P25 (a delta of 11). The P25 threshold is the primary operational definition per proposal §3.5 — it isolates the genuinely scarce `(capability, SDLC)` intersections. P33 is the sensitivity probe: it exposes how many additional intersections sit on the margin of adequate evidence and would be reclassified as gaps under a less stringent rule.

The empty-cell count is reported separately because `cell_value == 0` is categorically distinct from `cell_value ∈ (0, P25]` — empty cells reflect an outright literature vacuum, while gap cells indicate demonstrated-but-under-investigated combinations. Both feed ERP3 hypothesis generation but should not be pooled in aggregate counts.

## How to regenerate

```
/home/bthia/smuprj/erp2-sms/venv/bin/python code/analysis_rq3.py
```
