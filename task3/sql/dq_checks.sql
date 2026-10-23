-- PulseIQ Task 3 SQL reference
-- Generated from scripts/run_dq_checks.py CHECKS.
-- DQ-C13 is handled in Python because it must distinguish a missing
-- etl_run_log table from a stale or missing successful timestamp.
-- Run each SELECT against a warehouse with the expected schema.

-- DQ-C01 | Critical | Payroll equals ledger
-- Source: fact_payroll / fact_ledger
WITH payroll AS (
                SELECT
                    date_trunc('month', period_end_date)::DATE AS month,
                    SUM(employer_cost) AS payroll_cost
                FROM warehouse.fact_payroll
                GROUP BY 1
            ),
            ledger AS (
                SELECT
                    date_trunc('month', entry_date)::DATE AS month,
                    SUM(debit - credit) AS ledger_cost
                FROM warehouse.fact_ledger
                WHERE account_code BETWEEN 5001 AND 5005
                GROUP BY 1
            )
            SELECT
                COALESCE(p.month, l.month) AS month,
                p.payroll_cost,
                l.ledger_cost,
                COALESCE(p.payroll_cost, 0)
                - COALESCE(l.ledger_cost, 0) AS difference
            FROM payroll p
            FULL OUTER JOIN ledger l
                ON p.month = l.month
            WHERE ABS(
                COALESCE(p.payroll_cost, 0)
                - COALESCE(l.ledger_cost, 0)
            ) > 0.01;

-- DQ-C02 | Critical | Ledger balanced
-- Source: fact_ledger
SELECT
                entry_id,
                SUM(debit) AS total_debit,
                SUM(credit) AS total_credit
            FROM warehouse.fact_ledger
            GROUP BY entry_id
            HAVING ABS(SUM(debit) - SUM(credit)) > 0.005;

-- DQ-C03 | Critical | Unique payroll rows
-- Source: fact_payroll
SELECT
                employee_id,
                run_id,
                COUNT(*) AS row_count
            FROM warehouse.fact_payroll
            GROUP BY employee_id, run_id
            HAVING COUNT(*) > 1;

-- DQ-C04 | Critical | No orphan employees
-- Source: fact_payroll
SELECT DISTINCT
                f.employee_id
            FROM warehouse.fact_payroll f
            LEFT JOIN warehouse.dim_employee d
                ON f.employee_id = d.employee_id
            WHERE d.employee_id IS NULL;

-- DQ-C05 | Warning | No attendance after exit
-- Source: fact_attendance_monthly
SELECT
                a.attendance_fact_id,
                a.employee_id,
                a.period_end_date,
                d.exit_date
            FROM warehouse.fact_attendance_monthly a
            JOIN warehouse.dim_employee d
                ON a.employee_id = d.employee_id
                AND d.is_current = 'Y'
            WHERE d.exit_date IS NOT NULL
              AND a.period_end_date > last_day(d.exit_date);

-- DQ-C06 | Warning | Unpaid leave deducted
-- Source: fact_attendance_monthly / fact_payroll
WITH attendance AS (
                SELECT
                    employee_id,
                    period_end_date,
                    SUM(unpaid_absence_days) AS unpaid_days
                FROM warehouse.fact_attendance_monthly
                GROUP BY employee_id, period_end_date
            ),
            payroll AS (
                SELECT
                    employee_id,
                    period_end_date,
                    SUM(lop_days) AS lop_days
                FROM warehouse.fact_payroll
                GROUP BY employee_id, period_end_date
            )
            SELECT
                a.employee_id,
                a.period_end_date,
                a.unpaid_days,
                p.lop_days
            FROM attendance a
            LEFT JOIN payroll p
                ON a.employee_id = p.employee_id
                AND a.period_end_date = p.period_end_date
            WHERE a.unpaid_days > 0
              AND (
                    p.employee_id IS NULL
                    OR ABS(
                        a.unpaid_days
                        - COALESCE(p.lop_days, 0)
                    ) > 0.5
              );

-- DQ-C07 | Warning | Invoice arithmetic
-- Source: fact_invoice
SELECT
                invoice_id,
                total_amount,
                amount_paid,
                balance_due
            FROM warehouse.fact_invoice
            WHERE amount_paid > total_amount + 0.01
               OR balance_due < -0.01;

-- DQ-C08 | Warning | Expense arithmetic
-- Source: fact_expense
SELECT
                expense_id,
                amount_excl_gst,
                gst_amount,
                total_amount
            FROM warehouse.fact_expense
            WHERE ABS(
                total_amount
                - (amount_excl_gst + gst_amount)
            ) > 0.01;

-- DQ-C09 | Warning | Task dates sensible
-- Source: fact_task
SELECT
                task_id,
                status,
                started_date,
                completed_date
            FROM warehouse.fact_task
            WHERE (
                started_date IS NOT NULL
                AND completed_date IS NOT NULL
                AND completed_date < started_date
            )
            OR (
                lower(trim(status)) IN ('done', 'completed')
                AND completed_date IS NULL
            );

-- DQ-C10 | Warning | Leave dates sensible
-- Source: fact_leave
SELECT
                leave_request_id,
                start_date,
                end_date
            FROM warehouse.fact_leave
            WHERE start_date IS NOT NULL
              AND end_date IS NOT NULL
              AND end_date < start_date;

-- DQ-C11 | Warning | AI feeds are fresh
-- Source: fact_attrition_risk
SELECT
                prediction_id,
                as_of_date
            FROM warehouse.fact_attrition_risk
            WHERE as_of_date < (
                SELECT MAX(as_of_date)
                FROM warehouse.fact_attrition_risk
            ) - INTERVAL 7 DAYS;

-- DQ-C12 | Critical | Dimension history does not overlap
-- Source: dim_employee
SELECT
                a.employee_id,
                a.employee_key AS earlier_key,
                b.employee_key AS later_key,
                a.valid_from AS earlier_from,
                a.valid_to AS earlier_to,
                b.valid_from AS later_from,
                b.valid_to AS later_to
            FROM warehouse.dim_employee a
            JOIN warehouse.dim_employee b
                ON a.employee_id = b.employee_id
                AND a.employee_key < b.employee_key
            WHERE
                COALESCE(
                    a.valid_to,
                    DATE '9999-12-31'
                ) >= b.valid_from
            AND
                COALESCE(
                    b.valid_to,
                    DATE '9999-12-31'
                ) >= a.valid_from;

-- DQ-C13 | Critical | Pipeline freshness
-- Source: etl_run_log
-- Special check: see DQ-C13 logic in scripts/run_dq_checks.py

-- DQ-C14 | Critical | Minimum group size
-- Source: manager-facing aggregates
SELECT
                'headcount' AS metric,
                CAST(month_start_date AS VARCHAR) AS period,
                department_id,
                headcount_end AS group_size
            FROM warehouse.fact_headcount_monthly
            WHERE headcount_end > 0
              AND headcount_end < 5

            UNION ALL

            SELECT
                'attrition_risk' AS metric,
                CAST(as_of_date AS VARCHAR) AS period,
                department_id,
                COUNT(DISTINCT employee_id) AS group_size
            FROM warehouse.fact_attrition_risk
            GROUP BY as_of_date, department_id
            HAVING COUNT(DISTINCT employee_id) < 10

            UNION ALL

            SELECT
                'payroll' AS metric,
                CAST(period_end_date AS VARCHAR) AS period,
                department_id,
                COUNT(DISTINCT employee_id) AS group_size
            FROM warehouse.fact_payroll
            GROUP BY period_end_date, department_id
            HAVING COUNT(DISTINCT employee_id) < 5

            UNION ALL

            SELECT
                'attendance' AS metric,
                CAST(period_end_date AS VARCHAR) AS period,
                department_id,
                COUNT(DISTINCT employee_id) AS group_size
            FROM warehouse.fact_attendance_monthly
            GROUP BY period_end_date, department_id
            HAVING COUNT(DISTINCT employee_id) < 5;

