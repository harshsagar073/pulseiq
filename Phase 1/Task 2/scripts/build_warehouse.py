from pathlib import Path
import duckdb

BASE = Path(__file__).resolve().parent.parent
SOURCE = BASE.parent / "Task 1" / "validated"
DB_PATH = BASE / "pulseiq_warehouse.duckdb"

PRIMARY_KEYS = {
    "dim_employee": ["employee_key"],
    "dim_department": ["department_id"],
    "dim_role": ["role_id"],
    "dim_date": ["date_key"],
    "dim_account": ["account_code"],
    "dim_client": ["client_id"],
    "dim_leave_type": ["leave_type_code"],
    "dim_location": ["work_location"],
    "dim_sprint": ["sprint_id"],
    "dim_team": ["team_id"],
    "dim_vendor": ["vendor_id"],
    "fact_payroll": ["payroll_item_id"],
    "fact_attendance_monthly": ["attendance_fact_id"],
    "fact_leave": ["leave_request_id"],
    "fact_headcount_monthly": ["date_key", "department_id"],
    "fact_ledger": ["line_id"],
    "fact_invoice": ["invoice_id"],
    "fact_invoice_payment": ["payment_id"],
    "fact_expense": ["expense_id"],
    "fact_task": ["task_id"],
    "fact_anomaly": ["result_id"],
    "fact_attrition_risk": ["prediction_id"],
    "fact_forecast": ["forecast_id"],
    "budget_payroll_dept_month": ["department_id", "month"],
    "kpi_targets": ["month", "department_id"],
}

def quote(name):
    return '"' + name.replace('"', '""') + '"'

if not SOURCE.is_dir():
    raise SystemExit(f"ERROR: Source folder not found: {SOURCE}")

files = sorted(SOURCE.glob("*.csv"))
expected = set(PRIMARY_KEYS)
found = {f.stem for f in files}

if found != expected:
    print("Missing CSV tables:", sorted(expected - found))
    print("Unexpected CSV tables:", sorted(found - expected))
    raise SystemExit("Fix the CSV list before building the warehouse.")

if DB_PATH.exists():
    DB_PATH.unlink()

con = duckdb.connect(str(DB_PATH))
con.execute("CREATE SCHEMA warehouse")
summary = []

try:
    for csv_file in files:
        table = csv_file.stem
        print(f"Loading {table}...")

        con.execute(
            "CREATE OR REPLACE TEMP TABLE incoming AS "
            "SELECT * FROM read_csv_auto(?, header=true, sample_size=-1)",
            [str(csv_file)]
        )

        columns = con.execute("DESCRIBE incoming").fetchall()
        names = [row[0] for row in columns]
        types = {row[0]: row[1] for row in columns}

        missing_keys = set(PRIMARY_KEYS[table]) - set(names)
        if missing_keys:
            raise RuntimeError(f"{table}: primary-key columns missing: {missing_keys}")

        key_sql = ", ".join(quote(k) for k in PRIMARY_KEYS[table])
        null_condition = " OR ".join(
            f"{quote(k)} IS NULL" for k in PRIMARY_KEYS[table]
        )
        null_count = con.execute(
            f"SELECT COUNT(*) FROM incoming WHERE {null_condition}"
        ).fetchone()[0]
        duplicate_count = con.execute(
            f"SELECT COUNT(*) FROM ("
            f"SELECT {key_sql} FROM incoming GROUP BY {key_sql} "
            f"HAVING COUNT(*) > 1)"
        ).fetchone()[0]

        if null_count or duplicate_count:
            raise RuntimeError(
                f"{table}: cannot apply primary key. "
                f"Rows with null key={null_count}; duplicate key groups={duplicate_count}"
            )

        definitions = [
            f"{quote(name)} {types[name]}" for name in names
        ]
        definitions.append(f"PRIMARY KEY ({key_sql})")

        con.execute(
            f"CREATE TABLE warehouse.{quote(table)} "
            f"({', '.join(definitions)})"
        )
        con.execute(
            f"INSERT INTO warehouse.{quote(table)} "
            f"SELECT * FROM incoming"
        )

        row_count = con.execute(
            f"SELECT COUNT(*) FROM warehouse.{quote(table)}"
        ).fetchone()[0]

        summary.append((table, row_count, ", ".join(PRIMARY_KEYS[table])))
        con.execute("DROP TABLE incoming")

    con.execute("""
        CREATE TABLE warehouse.load_summary (
            table_name VARCHAR PRIMARY KEY,
            row_count BIGINT,
            primary_key_columns VARCHAR
        )
    """)
    con.executemany(
        "INSERT INTO warehouse.load_summary VALUES (?, ?, ?)",
        summary
    )

    con.execute("CHECKPOINT")

    print("\nWAREHOUSE BUILD SUCCESSFUL")
    print("-" * 72)
    print(f"{'TABLE':32} {'ROWS':>10}  PRIMARY KEY")
    print("-" * 72)
    for table, rows, keys in summary:
        print(f"{table:32} {rows:>10,}  {keys}")

    print("-" * 72)
    print(f"TOTAL ROWS LOADED: {sum(row[1] for row in summary):,}")
    print(f"DATABASE: {DB_PATH}")
    print("All tables have primary keys.")

finally:
    con.close()
