# PulseIQ Task 3 — Data Quality Notes

## Purpose
The gatekeeper runs 14 checks against the Task 2 warehouse copy and
records status, bad-row count, severity, runtime, timestamp, and details
in `warehouse.dq_results`.

## Check catalogue
- DQ-C01: Reconcile monthly payroll employer cost to ledger salary expense.
- DQ-C02: Find ledger entries whose debits and credits do not balance.
- DQ-C03: Find repeated employee/run payroll keys.
- DQ-C04: Find payroll employee IDs missing from the employee dimension.
- DQ-C05: Find attendance periods after an employee's exit date.
- DQ-C06: Find unpaid attendance days that do not match payroll LOP days.
- DQ-C07: Find invoices overpaid or with a negative balance due.
- DQ-C08: Check expense total against amount excluding GST plus GST.
- DQ-C09: Find impossible task dates or completed tasks with no completion date.
- DQ-C10: Find leave requests whose end date precedes their start date.
- DQ-C11: Find attrition predictions older than seven days relative to
  the latest prediction date in the data.
- DQ-C12: Find overlapping employee dimension history intervals.
- DQ-C13: Check the latest successful ETL timestamp; unavailable if the
  expected `etl_run_log` table is absent.
- DQ-C14: Flag small groups in selected headcount, attrition, payroll,
  and attendance aggregates.

## Interpretation and limitations
A failing check is a finding for investigation, not automatically proof
that every returned row is a confirmed business defect. In particular,
DQ-C06 requires confirmation of attendance-to-LOP reconciliation rules.
DQ-C14 uses provisional thresholds (<5 for headcount/payroll/attendance
and <10 for attrition-risk groups); the local metric dictionary does not
define these thresholds. Confirm the policy with the data owner.

DQ-C11 checks prediction date freshness; it does not independently prove
that a prediction was scored within 24 hours of a load.

The isolated tests use deliberately invalid sample rows in in-memory
DuckDB tables. They do not change Task 1, Task 2, or the Task 3 results
database. The DQ-C13 test verifies the special-check configuration; a
genuine pipeline-freshness test requires a real ETL run log.
