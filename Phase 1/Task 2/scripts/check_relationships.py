from pathlib import Path
import csv
import duckdb

BASE = Path(__file__).resolve().parent.parent
DB_PATH = BASE / "pulseiq_warehouse.duckdb"
OUT = BASE / "evidence"
OUT.mkdir(exist_ok=True)

# child table, child column, parent table, parent column
RELATIONSHIPS = [
    ("fact_payroll", "employee_key", "dim_employee", "employee_key"),
    ("fact_payroll", "date_key", "dim_date", "date_key"),
    ("fact_payroll", "department_id", "dim_department", "department_id"),
    ("fact_payroll", "role_id", "dim_role", "role_id"),

    ("fact_attendance_monthly", "employee_key", "dim_employee", "employee_key"),
    ("fact_attendance_monthly", "date_key", "dim_date", "date_key"),
    ("fact_attendance_monthly", "department_id", "dim_department", "department_id"),

    ("fact_leave", "employee_key", "dim_employee", "employee_key"),
    ("fact_leave", "leave_type_code", "dim_leave_type", "leave_type_code"),
    ("fact_leave", "start_date_key", "dim_date", "date_key"),
    ("fact_leave", "end_date_key", "dim_date", "date_key"),

    ("fact_headcount_monthly", "date_key", "dim_date", "date_key"),
    ("fact_headcount_monthly", "department_id", "dim_department", "department_id"),

    ("fact_ledger", "date_key", "dim_date", "date_key"),
    ("fact_ledger", "account_code", "dim_account", "account_code"),
    ("fact_ledger", "cost_center_department_id", "dim_department", "department_id"),

    ("fact_invoice", "client_id", "dim_client", "client_id"),
    ("fact_invoice", "invoice_date_key", "dim_date", "date_key"),
    ("fact_invoice", "service_line_account", "dim_account", "account_code"),

    ("fact_invoice_payment", "invoice_id", "fact_invoice", "invoice_id"),
    ("fact_invoice_payment", "payment_date_key", "dim_date", "date_key"),

    ("fact_expense", "vendor_id", "dim_vendor", "vendor_id"),
    ("fact_expense", "category_account", "dim_account", "account_code"),
    ("fact_expense", "department_id", "dim_department", "department_id"),
    ("fact_expense", "expense_date_key", "dim_date", "date_key"),

    ("fact_task", "team_id", "dim_team", "team_id"),
    ("fact_task", "sprint_id", "dim_sprint", "sprint_id"),

    ("fact_attrition_risk", "employee_key", "dim_employee", "employee_key"),
    ("fact_attrition_risk", "department_id", "dim_department", "department_id"),
    ("fact_attrition_risk", "as_of_date_key", "dim_date", "date_key"),

    ("fact_forecast", "department_id", "dim_department", "department_id"),
    ("fact_forecast", "forecast_month_key", "dim_date", "date_key"),

    ("budget_payroll_dept_month", "department_id", "dim_department", "department_id"),
    ("kpi_targets", "department_id", "dim_department", "department_id"),
]

def q(value):
    return '"' + value.replace('"', '""') + '"'

con = duckdb.connect(str(DB_PATH))
results = []
orphan_details = []

try:
    for child, child_col, parent, parent_col in RELATIONSHIPS:
        c = f"c.{q(child_col)}"
        p = f"p.{q(parent_col)}"

        checked, nulls, orphans = con.execute(f"""
            SELECT
                COUNT(*) FILTER (WHERE {c} IS NOT NULL),
                COUNT(*) FILTER (WHERE {c} IS NULL),
                COUNT(*) FILTER (
                    WHERE {c} IS NOT NULL AND p.{q(parent_col)} IS NULL
                )
            FROM warehouse.{q(child)} c
            LEFT JOIN warehouse.{q(parent)} p
              ON {c} = {p}
        """).fetchone()

        details = con.execute(f"""
            SELECT c.*
            FROM warehouse.{q(child)} c
            WHERE {c} IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1
                  FROM warehouse.{q(parent)} p
                  WHERE c.{q(child_col)} = p.{q(parent_col)}
              )
        """).fetchdf()

        for _, row in details.iterrows():
            orphan_details.append({
                "child_table": child,
                "child_column": child_col,
                "parent_table": parent,
                "parent_column": parent_col,
                "orphan_key": str(row[child_col]),
                "child_row": row.to_json(date_format="iso"),
            })

        results.append({
            "child_table": child,
            "child_column": child_col,
            "parent_table": parent,
            "parent_column": parent_col,
            "non_null_keys_checked": checked,
            "null_keys": nulls,
            "orphan_rows": orphans,
            "status": "PASS" if orphans == 0 else "REVIEW",
        })

    report = OUT / "orphan_check_summary.csv"
    with report.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    detail_report = OUT / "orphan_rows.csv"
    fields = [
        "child_table", "child_column", "parent_table",
        "parent_column", "orphan_key", "child_row"
    ]
    with detail_report.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(orphan_details)

    con.execute("""
        CREATE OR REPLACE TABLE warehouse.relationship_check_summary AS
        SELECT * FROM read_csv_auto(?)
    """, [str(report)])

    print("\nRELATIONSHIP CHECK RESULTS")
    print("-" * 94)
    print(f"{'CHILD.COLUMN':36} {'PARENT.COLUMN':36} {'ORPHANS':>8} {'STATUS':>9}")
    print("-" * 94)

    for r in results:
        child_name = f"{r['child_table']}.{r['child_column']}"
        parent_name = f"{r['parent_table']}.{r['parent_column']}"
        print(
            f"{child_name:36} {parent_name:36} "
            f"{r['orphan_rows']:>8} {r['status']:>9}"
        )

    print("-" * 94)
    total_orphans = sum(r["orphan_rows"] for r in results)
    print(f"Relationships checked: {len(results)}")
    print(f"Total orphan relationship rows: {total_orphans}")
    print(f"Summary saved: {report}")
    print(f"Orphan details saved: {detail_report}")
    print("Note: NULL keys are reported separately from orphan keys.")

finally:
    con.close()
