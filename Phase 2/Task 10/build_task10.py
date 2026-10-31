from pathlib import Path
import duckdb

BASE = Path(__file__).resolve().parent
SOURCE_DB = Path(
    "/Users/admin/Desktop/PulseIQ/Phase 1/Task 4/pulseiq_task4.duckdb"
)
OUTPUT_DB = BASE / "pulseiq_task10.duckdb"

EXCLUDED_PAYROLL_IDS = (
    "PI-X0001",
    "PI-X0002",
    "PI-X0003",
    "PI-X0004",
)

if not SOURCE_DB.exists():
    raise FileNotFoundError(f"Source database not found: {SOURCE_DB}")

if OUTPUT_DB.exists():
    OUTPUT_DB.unlink()

con = duckdb.connect(str(OUTPUT_DB))

try:
    con.execute(
        f"ATTACH '{SOURCE_DB.as_posix()}' AS src (READ_ONLY)"
    )

    con.execute("""
        CREATE TABLE budget_actual AS
        WITH payroll AS (
            SELECT
                date_trunc('month', period_end_date)::DATE AS month,
                department_id,
                SUM(employer_cost) AS actual_payroll_cost
            FROM src.raw.fact_payroll
            WHERE payroll_item_id NOT IN (
                'PI-X0001', 'PI-X0002', 'PI-X0003', 'PI-X0004'
            )
            GROUP BY 1, 2
        )
        SELECT
            b.month,
            b.department_id,
            d.department_name,
            b.budget_payroll_cost,
            p.actual_payroll_cost,
            p.actual_payroll_cost - b.budget_payroll_cost
                AS variance_amount,
            CASE
                WHEN b.budget_payroll_cost = 0 THEN NULL
                ELSE ROUND(
                    100.0 * (
                        p.actual_payroll_cost - b.budget_payroll_cost
                    ) / b.budget_payroll_cost,
                    2
                )
            END AS variance_pct,
            CASE
                WHEN p.actual_payroll_cost IS NULL THEN 'AMBER'
                WHEN p.actual_payroll_cost > b.budget_payroll_cost
                    THEN 'RED'
                ELSE 'GREEN'
            END AS budget_status
        FROM src.raw.budget_payroll_dept_month b
        LEFT JOIN payroll p
          ON b.month = p.month
         AND b.department_id = p.department_id
        LEFT JOIN src.raw.dim_department d
          ON b.department_id = d.department_id
    """)

    con.execute("""
        CREATE TABLE kpi_performance AS
        WITH attendance AS (
            SELECT
                date_trunc('month', period_end_date)::DATE AS month,
                department_id,
                metric_value AS attendance_actual
            FROM src.governed.m13_attendance_rate
        ),
        overtime AS (
            SELECT
                date_trunc('month', period_end_date)::DATE AS month,
                department_id,
                metric_value AS overtime_actual_pct
            FROM src.governed.m11_overtime_share
        ),
        attrition AS (
            SELECT
                month_start_date AS month,
                department_id,
                metric_value AS attrition_actual_pct
            FROM src.governed.m04_monthly_attrition
        ),
        tasks AS (
            SELECT
                date_trunc('month', t.due_date)::DATE AS month,
                tm.department_id,
                COUNT(*) FILTER (
                    WHERE upper(CAST(t.status AS VARCHAR)) != 'CANCELLED'
                ) AS eligible_tasks,
                COUNT(*) FILTER (
                    WHERE upper(CAST(t.status AS VARCHAR)) = 'DONE'
                ) AS completed_tasks,
                ROUND(
                    100.0 * COUNT(*) FILTER (
                        WHERE upper(CAST(t.status AS VARCHAR)) = 'DONE'
                    ) / NULLIF(
                        COUNT(*) FILTER (
                            WHERE upper(CAST(t.status AS VARCHAR)) != 'CANCELLED'
                        ), 0
                    ),
                    2
                ) AS task_completion_actual_pct
            FROM src.raw.fact_task t
            JOIN src.raw.dim_team tm ON t.team_id = tm.team_id
            WHERE t.due_date >= DATE '2025-04-01'
              AND t.due_date < DATE '2026-10-01'
            GROUP BY 1, 2
        )
        SELECT
            target.month,
            target.department_id,
            d.department_name,

            attendance.attendance_actual,
            target.attendance_rate_target,

            overtime.overtime_actual_pct,
            target.overtime_share_target_pct,

            attrition.attrition_actual_pct,
            target.attrition_monthly_target_pct,

            tasks.task_completion_actual_pct,
            target.task_completion_target_pct,
            tasks.eligible_tasks,
            tasks.completed_tasks,

            CASE
                WHEN attendance.attendance_actual IS NULL
                  OR target.attendance_rate_target IS NULL THEN 'AMBER'
                WHEN attendance.attendance_actual >=
                     target.attendance_rate_target THEN 'GREEN'
                ELSE 'RED'
            END AS attendance_status,

            CASE
                WHEN overtime.overtime_actual_pct IS NULL
                  OR target.overtime_share_target_pct IS NULL THEN 'AMBER'
                WHEN overtime.overtime_actual_pct <=
                     target.overtime_share_target_pct THEN 'GREEN'
                ELSE 'RED'
            END AS overtime_status,

            CASE
                WHEN attrition.attrition_actual_pct IS NULL
                  OR target.attrition_monthly_target_pct IS NULL THEN 'AMBER'
                WHEN attrition.attrition_actual_pct <=
                     target.attrition_monthly_target_pct THEN 'GREEN'
                ELSE 'RED'
            END AS attrition_status,

            CASE
                WHEN tasks.task_completion_actual_pct IS NULL
                  OR target.task_completion_target_pct IS NULL THEN 'AMBER'
                WHEN tasks.task_completion_actual_pct >=
                     target.task_completion_target_pct THEN 'GREEN'
                ELSE 'RED'
            END AS task_completion_status

        FROM src.raw.kpi_targets target
        LEFT JOIN src.raw.dim_department d
          ON target.department_id = d.department_id
        LEFT JOIN attendance
          ON target.month = attendance.month
         AND target.department_id = attendance.department_id
        LEFT JOIN overtime
          ON target.month = overtime.month
         AND target.department_id = overtime.department_id
        LEFT JOIN attrition
          ON target.month = attrition.month
         AND target.department_id = attrition.department_id
        LEFT JOIN tasks
          ON target.month = tasks.month
         AND target.department_id = tasks.department_id
    """)

    print("\n===== TASK 10 BUILD SUCCESSFUL =====")
    print("Output database:", OUTPUT_DB)

    for table in ["budget_actual", "kpi_performance"]:
        count = con.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()[0]
        print(f"{table}: {count} rows")

    print("\n===== BUDGET DATA SAMPLE =====")
    print(con.execute("""
        SELECT *
        FROM budget_actual
        ORDER BY month, department_id
        LIMIT 10
    """).fetchdf().to_string(index=False))

    print("\n===== KPI DATA SAMPLE =====")
    print(con.execute("""
        SELECT *
        FROM kpi_performance
        ORDER BY month, department_id
        LIMIT 10
    """).fetchdf().to_string(index=False))

    print("\n===== MONTH COVERAGE =====")
    print(con.execute("""
        SELECT
            MIN(month) AS first_month,
            MAX(month) AS last_month,
            COUNT(DISTINCT month) AS months
        FROM budget_actual
    """).fetchdf().to_string(index=False))

finally:
    con.close()
