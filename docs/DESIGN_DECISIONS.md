# Problem, assumptions, decisions, testing and limitations

## Problem as I understood it
Build a reproducible synthetic-data workflow that compares pay against role, level, location and documented factors, surfaces
**unexplained** disparities, routes defects to an exception path, creates auditable adjustment proposals, and can be graded against
a separate ground truth. Correctness and traceability matter more than a UI (no UI was required).

## Assumptions
- All data is synthetic. One FX rate per currency per year (not daily). Dataset "today" is fixed at 2026-10-22, snapshot date 2026-10-01.
- "Documented factors" = annual review rating, tenure and approved pay premiums. No protected attributes are modelled.
- Role/level/location are stored on each effective-dated `SalaryRecord` (instead of overwriting `Employee`) so history is never lost.
- Comparable group rule R1 = same role family + level + location; minimum size 5.

## Key decisions and trade-offs
| Decision | Why | Trade-off |
|---|---|---|
| Generate pay from documented factors, then add labelled outliers | Variation is explainable, so the residual is meaningful; labels come from rules, not random flags | Model is easy to recover, so detection is easier than in real life |
| Robust regression + MAD z-score (not ML) | Transparent and auditable for HR decisions | Less powerful; 3 false positives at 5,000 rows (noise tail / no-pay-cut policy) |
| Inject anomalies on derived tables (snapshot, groups, proposals) | Honours "do not silently corrupt unrelated rows"; raw salary history stays valid | Anomalies are analysis/process defects, not data-entry errors in master data |
| Methodology-defect rows go to an exception queue and are excluded from the model | Bad comparisons must not create pay changes | Slightly fewer rows in the model |
| `ground_truth/` kept separate; validator checks no label columns in inputs | Required by spec; avoids leakage | Detection metrics need the file at evaluation time only |
| Validation separates *expected* findings (labelled) from *unexpected* errors | A PASS proves clean data AND that each check catches its planted defect | More complex than a plain pass/fail |
| FKs are `DEFERRABLE INITIALLY DEFERRED` in SQL | Cyclic references (proposal <-> salary record, manager self-reference) load in one transaction | Needs `BEGIN/COMMIT` around the seed |

## Deviations / extensions to the brief
- 15 tables instead of the 10 core entities: added `FXRate`, `CompaRatioSnapshot`, `ComparableGroup`, `ComparableGroupMember` (N:M bridge), `ApprovalEvent`.
- Band IDs carry the year (`...-2024/2025/2026`) so expired versions exist for the "expired band" case; salary IDs use `-NN` sequence numbers for multiple changes per year.
- BOOLEAN columns are exported as 0/1.

## How I know it works (testing approach)
- 18 automated tests: ID formats, same-seed identity, known-input compa-ratio / range-position / FTE / FX math, effective-dated bands,
  every injected anomaly detected by a rule, anomalies rare and disjoint, valid manual group not flagged, validator **fails** on deliberately
  broken rows (FK, enum, arithmetic, dates, duplicate PK, derived value, missing approval), ground truth not leaked, SQL loads in SQLite with FK enforcement.
- `validation_summary.json`: 253 checks, ~968k rows, 0 unexpected errors. `evaluation_metrics.json`: precision/recall per issue type.
- `reproducibility_check.sh`: two runs, identical SHA-256 for every output file.
- Manual spot checks: tracing individual planted anomalies in the dashboard.

## Known limitations and next steps
- Simple model; real pay-equity work would add legally relevant attributes and statistical tests.
- Single snapshot date; no monthly time series of gaps.
- Approval timing uses fixed SLA offsets rather than simulated workloads.
- The dashboard is an optional extra; the core deliverable needs only Python.
