
# PulseIQ Task 2 — Data Quality Notes

## 1. Row-count reconciliation

- Source tables checked: 25
- Total validated source rows: 62,295
- Total warehouse rows: 62,385
- Additional calendar rows: 90
- Unexpected row-count mismatches: 0

The `dim_date` source contains 2,557 rows. The warehouse dimension contains 2,647 rows because 90 calendar rows were added to support forecast dates through 2027-03-31. The original source CSV was not modified.

Evidence: `evidence/row_count_reconciliation.csv`

## 2. Payroll employee-key exceptions

Two payroll rows have `employee_key = -1`, which does not match any employee in `dim_employee`.

| Payroll item | Employee ID | Period end | Department | Role |
|---|---|---|---|---|
| PI-X0003 | EMP-9001 | 2026-04-30 | D01 | R006 |
| PI-X0004 | EMP-9002 | 2025-12-31 | D09 | R053 |

Both rows are retained. No employee records were invented, and no employee keys were silently changed. These exceptions require source-data review.

Evidence:
- `evidence/orphan_check_summary.csv`
- `evidence/orphan_rows.csv`

## 3. Forecast scope

The 72 forecast rows comprise:
- 60 department-level forecasts.
- 12 company-wide forecasts.

Company-wide rows use `forecast_scope = 'COMPANY'` and a NULL `department_id`. Department-level rows use `forecast_scope = 'DEPARTMENT'`. The marker `ALL` is treated as company-wide scope rather than a department.

## 4. Relationship validation

The latest check evaluated 34 relationships. All passed except `fact_payroll.employee_key`, which has two unresolved orphan rows. These exceptions are documented, not treated as passing checks.

## 5. Employee history

Employee-related facts should join through `employee_key` to preserve the correct historical employee version. Joining only through `employee_id` can misattribute records when an employee changes departments.
