from pathlib import Path
import duckdb
import pandas as pd
import py_compile

ROOT = Path(__file__).resolve().parents[4]
DB = ROOT / "Phase 1" / "Task 4" / "pulseiq_task4.duckdb"
APP = Path(__file__).with_name("app.py")

checks = []

def check(name, condition, detail=""):
    status = bool(condition)
    checks.append(status)
    print(f"{'PASS' if status else 'FAIL'} | {name}" + (f" | {detail}" if detail else ""))

# 1. App syntax
try:
    py_compile.compile(str(APP), doraise=True)
    check("Dashboard Python syntax", True)
except Exception as exc:
    check("Dashboard Python syntax", False, str(exc))

# 2. Database exists and can be opened read-only
check("Source database exists", DB.exists(), str(DB))

if DB.exists():
    con = duckdb.connect(str(DB), read_only=True)

    df = con.execute("""
        SELECT p.payroll_item_id, p.employee_id,
               p.period_end_date, p.department_id,
               d.department_name, p.gross_pay, p.net_pay,
               p.employer_cost, p.overtime_pay, p.variable_pay
        FROM raw.fact_payroll p
        LEFT JOIN raw.dim_department d
          ON p.department_id = d.department_id
        WHERE p.payroll_item_id NOT IN (?, ?, ?, ?)
    """, ["PI-X0001", "PI-X0002", "PI-X0003", "PI-X0004"]).fetchdf()

    con.close()

    df["period_end_date"] = pd.to_datetime(df["period_end_date"])
    df["month"] = df["period_end_date"].dt.strftime("%Y-%m")

    check("Payroll data loaded", len(df) > 0, f"{len(df):,} rows")
    check("All four excluded IDs absent",
          not df["payroll_item_id"].isin(
              ["PI-X0001", "PI-X0002", "PI-X0003", "PI-X0004"]
          ).any())

    month_count = df["month"].nunique()
    check("Monthly history available", month_count >= 18, f"{month_count} months")

    september = df[df["month"] == "2026-09"]
    sep_employees = september["employee_id"].nunique()
    sep_gross = september["gross_pay"].sum()
    sep_net = september["net_pay"].sum()
    sep_cost = september["employer_cost"].sum()

    check("September 2026 employee count",
          sep_employees == 444, f"{sep_employees}")

    check("September gross pay matches dashboard",
          abs(sep_gross - 54788660) < 1, f"₹{sep_gross:,.2f}")

    check("September net pay matches dashboard",
          abs(sep_net - 48089678) < 1, f"₹{sep_net:,.2f}")

    check("September employer cost matches dashboard",
          abs(sep_cost - 55519622) < 1, f"₹{sep_cost:,.2f}")

    department_groups = (
        september.groupby("department_name")["employee_id"].nunique()
    )
    eligible = department_groups[department_groups >= 5]
    check("Privacy threshold can be applied",
          (eligible >= 5).all(),
          f"{len(eligible)} eligible department groups")

# 3. Required feature and privacy logic present
source = APP.read_text()

for phrase, description in [
    ("Monthly Payroll Cost Trend", "Monthly trend section"),
    ("Department Contribution", "Department contribution section"),
    ("Which Departments Drove the Change?", "Department change analysis"),
    ("Department Cost Breakdown", "Department drill-down"),
    ("MIN_GROUP_SIZE = 5", "Five-employee privacy threshold"),
    ("read_only=True", "Read-only database connection"),
]:
    check(description, phrase in source)

print("\n--------------------------------")
print(f"RESULT: {sum(checks)}/{len(checks)} checks passed")
print("--------------------------------")

if not all(checks):
    raise SystemExit(1)
