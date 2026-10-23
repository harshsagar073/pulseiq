# Task 3 — Official Planted Issue Comparison

## Audit source
Workbook:
03_PulseIQ_Analytics_Star_Schema_Dataset.xlsx

Official catalog:
dq_known_issues

Record presence audit:
planted_issue_record_presence_audit.txt

## Findings

| Issue | Expected check | Record presence | Current assessment |
|---|---|---|---|
| DQ-01 Attendance after exit | DQ-C05 | 4/4 in warehouse | VERIFIED — all 4 planted records detected |
| DQ-02 Duplicate payroll | DQ-C03 | 2/2 in warehouse | VERIFIED — both rows share keys with existing payroll items |
| DQ-03 Orphan employee IDs | DQ-C04 | 2/2 in warehouse | VERIFIED — both planted employee IDs are orphaned |
| DQ-04 Payroll-ledger mismatch | DQ-C01 | 3/3 ledger IDs in warehouse | VERIFIED — June ledger exceeds payroll by 18,450; journal entry balances |
| DQ-05 Overpaid invoice | DQ-C07 | 1/1 in warehouse | VERIFIED — paid amount exceeds invoice by 100 and balance is -100 |
| DQ-06 Completion before start | DQ-C09 | Quarantined; absent from warehouse | Isolated test detected all 12 |
| DQ-07 Done without completion date | DQ-C09 | Quarantined; absent from warehouse | Isolated test detected all 8 |
| DQ-08 Invalid leave dates | DQ-C10 | 2/2 in warehouse | VERIFIED — both planted records have end dates before start dates |
| DQ-09 Stale predictions | DQ-C11 | 5/5 in warehouse | VERIFIED — all 5 planted predictions are older than the latest date by more than 7 days |
| DQ-10 Expense arithmetic | DQ-C08 | 1/1 in warehouse | VERIFIED — planted total exceeds ex-GST plus GST by 500 |
| DQ-11 Employee history overlap | DQ-C12 | 1/1 in warehouse | VERIFIED — employee EMP-0001 versions 100000 and 100001 overlap May 3–12, 2012 |

## Verified isolated test

DQ-C09 was tested against the 20 official quarantined task records:
- 12 completion-before-start issues detected
- 8 Done-without-completion-date issues detected
- Total detected: 20 of 20

Evidence:
- dq_c09_quarantine_test.csv
- dq_c09_findings.txt

## Important limitation

Record presence and a failing check do not, by themselves, prove that
the exact planted records triggered the intended rule. The isolated test suite was subsequently executed successfully:
14 tests passed, with 0 failures. It tests representative deliberately
invalid rows for DQ-C01 through DQ-C12 and DQ-C14. This supplements the
targeted record audits above; it does not prove every possible edge case.

Test evidence: isolated_test_results_20261023.txt.
DQ-C13 has a configuration test, but live freshness remains UNAVAILABLE
until a genuine ETL run log is available.

Task 1 validation rules and Task 2 warehouse data were not modified.

## Additional checks requiring review

- DQ-C13 Pipeline freshness: currently UNAVAILABLE because the expected
  etl_run_log table is absent. Do not invent a successful load timestamp.
- DQ-C14 Minimum group size: verify coverage of every relevant
  manager-facing aggregate and the metric dictionary's minimum size.

## Decision

Keep the quarantined source records intact. Do not load them into the
production/task warehouse merely to make a test fail. Use isolated test
tables or an in-memory database to test the remaining rules.
