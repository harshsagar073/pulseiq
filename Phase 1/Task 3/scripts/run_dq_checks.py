from pathlib import Path
import shutil
import time
from datetime import datetime

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DB = ROOT.parent / "Task 2" / "pulseiq_warehouse.duckdb"
DB_PATH = ROOT / "pulseiq_dq.duckdb"
EVIDENCE = ROOT / "evidence"

EVIDENCE.mkdir(exist_ok=True)

# ------------------------------------------------------------
# ISOLATED DATABASE
# ------------------------------------------------------------

if not DB_PATH.exists():
    if not SOURCE_DB.exists():
        raise FileNotFoundError(f"Source warehouse not found: {SOURCE_DB}")

    shutil.copy2(SOURCE_DB, DB_PATH)
    print(f"Created isolated warehouse copy: {DB_PATH}")


# ------------------------------------------------------------
# 14 DATA QUALITY CHECKS
# ------------------------------------------------------------

CHECKS = [

    {
        "id": "DQ-C01",
        "name": "Payroll equals ledger",
        "severity": "Critical",
        "table": "fact_payroll / fact_ledger",
        "sql": """
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
            ) > 0.01
        """
    },

    {
        "id": "DQ-C02",
        "name": "Ledger balanced",
        "severity": "Critical",
        "table": "fact_ledger",
        "sql": """
            SELECT
                entry_id,
                SUM(debit) AS total_debit,
                SUM(credit) AS total_credit
            FROM warehouse.fact_ledger
            GROUP BY entry_id
            HAVING ABS(SUM(debit) - SUM(credit)) > 0.005
        """
    },

    {
        "id": "DQ-C03",
        "name": "Unique payroll rows",
        "severity": "Critical",
        "table": "fact_payroll",
        "sql": """
            SELECT
                employee_id,
                run_id,
                COUNT(*) AS row_count
            FROM warehouse.fact_payroll
            GROUP BY employee_id, run_id
            HAVING COUNT(*) > 1
        """
    },

    {
        "id": "DQ-C04",
        "name": "No orphan employees",
        "severity": "Critical",
        "table": "fact_payroll",
        "sql": """
            SELECT DISTINCT
                f.employee_id
            FROM warehouse.fact_payroll f
            LEFT JOIN warehouse.dim_employee d
                ON f.employee_id = d.employee_id
            WHERE d.employee_id IS NULL
        """
    },

    {
        "id": "DQ-C05",
        "name": "No attendance after exit",
        "severity": "Warning",
        "table": "fact_attendance_monthly",
        "sql": """
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
              AND a.period_end_date > last_day(d.exit_date)
        """
    },

    {
        "id": "DQ-C06",
        "name": "Unpaid leave deducted",
        "severity": "Warning",
        "table": "fact_attendance_monthly / fact_payroll",
        "sql": """
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
              )
        """
    },

    {
        "id": "DQ-C07",
        "name": "Invoice arithmetic",
        "severity": "Warning",
        "table": "fact_invoice",
        "sql": """
            SELECT
                invoice_id,
                total_amount,
                amount_paid,
                balance_due
            FROM warehouse.fact_invoice
            WHERE amount_paid > total_amount + 0.01
               OR balance_due < -0.01
        """
    },

    {
        "id": "DQ-C08",
        "name": "Expense arithmetic",
        "severity": "Warning",
        "table": "fact_expense",
        "sql": """
            SELECT
                expense_id,
                amount_excl_gst,
                gst_amount,
                total_amount
            FROM warehouse.fact_expense
            WHERE ABS(
                total_amount
                - (amount_excl_gst + gst_amount)
            ) > 0.01
        """
    },

    {
        "id": "DQ-C09",
        "name": "Task dates sensible",
        "severity": "Warning",
        "table": "fact_task",
        "sql": """
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
            )
        """
    },

    {
        "id": "DQ-C10",
        "name": "Leave dates sensible",
        "severity": "Warning",
        "table": "fact_leave",
        "sql": """
            SELECT
                leave_request_id,
                start_date,
                end_date
            FROM warehouse.fact_leave
            WHERE start_date IS NOT NULL
              AND end_date IS NOT NULL
              AND end_date < start_date
        """
    },

    {
        "id": "DQ-C11",
        "name": "AI feeds are fresh",
        "severity": "Warning",
        "table": "fact_attrition_risk",
        "sql": """
            SELECT
                prediction_id,
                as_of_date
            FROM warehouse.fact_attrition_risk
            WHERE as_of_date < (
                SELECT MAX(as_of_date)
                FROM warehouse.fact_attrition_risk
            ) - INTERVAL 7 DAYS
        """
    },

    {
        "id": "DQ-C12",
        "name": "Dimension history does not overlap",
        "severity": "Critical",
        "table": "dim_employee",
        "sql": """
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
                ) >= a.valid_from
        """
    },

    {
        "id": "DQ-C13",
        "name": "Pipeline freshness",
        "severity": "Critical",
        "table": "etl_run_log",
        "sql": None
    },

    {
        "id": "DQ-C14",
        "name": "Minimum group size",
        "severity": "Critical",
        "table": "manager-facing aggregates",
        "sql": """
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
            HAVING COUNT(DISTINCT employee_id) < 5
        """
    }
]


# ------------------------------------------------------------
# RESULTS TABLE
# ------------------------------------------------------------

def ensure_results_table(con):

    con.execute("""
        CREATE TABLE IF NOT EXISTS warehouse.dq_results (
            result_id BIGINT PRIMARY KEY,
            check_id VARCHAR NOT NULL,
            check_name VARCHAR NOT NULL,
            severity VARCHAR NOT NULL,
            table_name VARCHAR NOT NULL,
            bad_rows BIGINT,
            status VARCHAR NOT NULL,
            runtime_ms DOUBLE,
            checked_at TIMESTAMP,
            details VARCHAR
        )
    """)


# ------------------------------------------------------------
# RUN ALL CHECKS
# ------------------------------------------------------------

def run_checks():

    con = duckdb.connect(str(DB_PATH))

    ensure_results_table(con)

    next_id = con.execute("""
        SELECT COALESCE(MAX(result_id), 0) + 1
        FROM warehouse.dq_results
    """).fetchone()[0]

    run_rows = []

    print()
    print("PulseIQ Task 3 — Data Quality Gatekeeper")
    print("=" * 115)
    print(
        f"{'CHECK':<10} "
        f"{'SEVERITY':<10} "
        f"{'STATUS':<13} "
        f"{'BAD ROWS':>10} "
        f"{'TIME(ms)':>10}  "
        f"CHECK NAME"
    )
    print("-" * 115)

    for check in CHECKS:

        start = time.perf_counter()

        status = "PASS"
        bad_rows = None
        details = ""

        try:

            # ------------------------------------------------
            # C13 — Pipeline freshness
            # ------------------------------------------------

            if check["id"] == "DQ-C13":

                has_log = con.execute("""
                    SELECT COUNT(*)
                    FROM information_schema.tables
                    WHERE table_schema = 'warehouse'
                      AND table_name = 'etl_run_log'
                """).fetchone()[0] > 0

                if not has_log:

                    status = "UNAVAILABLE"

                    details = (
                        "etl_run_log is not present in the "
                        "Task 2 warehouse. Pipeline freshness "
                        "cannot be proven without a genuine "
                        "successful-load timestamp."
                    )

                else:

                    latest = con.execute("""
                        SELECT MAX(finished_at)
                        FROM warehouse.etl_run_log
                        WHERE lower(status) = 'success'
                    """).fetchone()[0]

                    if latest is None:

                        status = "FAIL"
                        bad_rows = 1
                        details = (
                            "No successful ETL load timestamp found."
                        )

                    else:

                        age_hours = (
                            datetime.now()
                            - latest.replace(tzinfo=None)
                        ).total_seconds() / 3600

                        bad_rows = (
                            0
                            if age_hours <= 24
                            else 1
                        )

                        status = (
                            "PASS"
                            if bad_rows == 0
                            else "FAIL"
                        )

                        details = (
                            f"Latest successful load age: "
                            f"{age_hours:.2f} hours."
                        )

            # ------------------------------------------------
            # C01-C12 and C14
            # ------------------------------------------------

            else:

                result = con.execute(
                    check["sql"]
                ).fetchall()

                bad_rows = len(result)

                status = (
                    "PASS"
                    if bad_rows == 0
                    else "FAIL"
                )

        except Exception as exc:

            status = "ERROR"

            details = str(exc).replace(
                "\n", " "
            )[:1000]

        runtime_ms = round(
            (time.perf_counter() - start) * 1000,
            3
        )

        con.execute("""
            INSERT INTO warehouse.dq_results
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            next_id,
            check["id"],
            check["name"],
            check["severity"],
            check["table"],
            bad_rows,
            status,
            runtime_ms,
            datetime.now(),
            details
        ])

        print(
            f"{check['id']:<10} "
            f"{check['severity']:<10} "
            f"{status:<13} "
            f"{str(bad_rows if bad_rows is not None else 'N/A'):>10} "
            f"{runtime_ms:>10.3f}  "
            f"{check['name']}"
        )

        if details:
            print(
                f"           {details}"
            )

        run_rows.append({
            "check_id": check["id"],
            "check_name": check["name"],
            "severity": check["severity"],
            "table_name": check["table"],
            "bad_rows": bad_rows,
            "status": status,
            "runtime_ms": runtime_ms,
            "details": details
        })

        next_id += 1

    con.commit()

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    print()
    print("-" * 115)
    print("LATEST CHECK SUMMARY")
    print("-" * 115)

    latest_summary = con.execute("""
        WITH latest AS (
            SELECT *,
                   ROW_NUMBER() OVER (
                       PARTITION BY check_id
                       ORDER BY checked_at DESC
                   ) AS rn
            FROM warehouse.dq_results
        )
        SELECT
            status,
            COUNT(*) AS checks
        FROM latest
        WHERE rn = 1
        GROUP BY status
        ORDER BY status
    """).fetchdf()

    print(
        latest_summary.to_string(
            index=False
        )
    )

    # --------------------------------------------------------
    # EVIDENCE CSV
    # --------------------------------------------------------

    stamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    evidence_file = (
        EVIDENCE
        / f"dq_results_{stamp}.csv"
    )

    pd.DataFrame(run_rows).to_csv(
        evidence_file,
        index=False
    )

    print()
    print(
        f"Results table: warehouse.dq_results"
    )

    print(
        f"Evidence file: {evidence_file}"
    )

    print(
        f"Database used: {DB_PATH}"
    )

    con.close()


if __name__ == "__main__":
    run_checks()
