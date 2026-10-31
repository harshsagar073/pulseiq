# PulseIQ Task 3 — Data Quality Gatekeeper Handover

## Final run
- Date: 2026-10-23
- Latest result CSV: dq_results_20261023_174158.csv
- Configured checks: 14
- PASS: 2
- FAIL: 11
- UNAVAILABLE: 1
- Results history table: warehouse.dq_results
- Task 3 database: pulseiq_dq.duckdb

## Verified planted issues
- Attendance after exit: 4 records detected.
- Duplicate payroll keys: 2 planted rows matched existing payroll keys.
- Orphan employee IDs: 2 records detected.
- Payroll-ledger mismatch: June 2026 ledger salary expense exceeds payroll
  employer cost by 18,450; the journal entry itself balances.
- Overpaid invoice: paid amount exceeds total by 100.
- Task dates: 20 quarantined planted issues detected in an isolated test.
- Invalid leave dates: 2 records detected.
- Stale predictions: 5 records detected.
- Expense arithmetic: total exceeds ex-GST plus GST by 500.
- Employee history: overlapping intervals detected for EMP-0001.

## Review items
- DQ-C06: 11 employee-month differences between unpaid attendance days
  and payroll LOP days. Review business rules before treating every
  difference as a confirmed defect.
- DQ-C13: UNAVAILABLE because etl_run_log is absent. No successful-load
  timestamp was fabricated.
- DQ-C14: 120 small groups flagged. The local metric dictionary does
  not specify the minimum group-size thresholds. Confirm policy and
  suppression behavior with the business owner.
- The separate unlock_PQ-03 file was not found in the Desktop search.

## Scope and safety
- Task 1 validation rules were not changed.
- Quarantined task rows were tested separately, not inserted into the
  Task 2 warehouse.
- Task 2 warehouse data was not changed by the read-only audits.
- The Task 3 runner writes results to its own Task 3 database.

## Severity recommendation
- Critical checks should block publication/load only when the rule
  represents a confirmed integrity failure.
- Warning checks should alert for reviewable business-rule differences.
- Privacy suppression should prevent undersized aggregates from being
  shown to users; confirm policy before finalizing thresholds/severity.

## Submission note
The gatekeeper is implemented and producing auditable results.
Remaining limitations are explicitly recorded rather than hidden.

## Isolated data-quality predicate tests — 2026-10-23

- Result: PASS — 14 tests passed, 0 failures.
- Evidence: `isolated_test_results_20261023.txt`.
- DQ-C01 through DQ-C12 and DQ-C14: deliberately invalid sample data was detected by the isolated SQL predicate tests.
- DQ-C13: configuration test passed. Live pipeline freshness remains UNAVAILABLE because a genuine `etl_run_log` is not present.
- Test fixtures use in-memory DuckDB tables and do not intentionally modify Task 1 or Task 2 data.
- The tests validate the predicates against representative examples; they do not prove every possible edge case.
