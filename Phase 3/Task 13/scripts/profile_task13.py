from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
SRC = BASE / "data" / "source"
REF = BASE / "data" / "reference" / "unlock_PQ-13_reference_summary_dept_month.csv"

def load(name):
    return pd.read_csv(SRC / name)

ref = pd.read_csv(REF)
teams = load("dim_team.csv")
tasks = load("fact_task.csv")
payroll = load("fact_payroll.csv")
attendance = load("fact_attendance_monthly.csv")
headcount = load("fact_headcount_monthly.csv")

print("\n===== TASK 13 SOURCE PROFILE =====")
for name, df in [
    ("dim_team", teams),
    ("fact_task", tasks),
    ("fact_payroll", payroll),
    ("fact_attendance_monthly", attendance),
    ("fact_headcount_monthly", headcount),
]:
    print(f"{name}: {len(df):,} rows")

print("\n===== TEAM TO DEPARTMENT MAPPING =====")
print(teams[["team_id", "team_name", "department_id"]].to_string(index=False))

tasks = tasks.merge(
    teams[["team_id", "department_id"]],
    on="team_id",
    how="left",
    validate="many_to_one"
)

for col in ["created_date", "completed_date", "due_date"]:
    tasks[col] = pd.to_datetime(tasks[col], errors="coerce")

tasks["status_clean"] = tasks["status"].astype(str).str.strip().str.lower()
tasks["is_done"] = tasks["status_clean"].eq("done")

sample_month = "2025-04"
sample_dept = "D01"

print("\n===== TASK COUNT DEFINITIONS: D01 / APRIL 2025 =====")
for date_col in ["created_date", "completed_date", "due_date"]:
    subset = tasks[
        tasks["department_id"].eq(sample_dept)
        & tasks[date_col].dt.strftime("%Y-%m").eq(sample_month)
    ]
    total = len(subset)
    done = int(subset["is_done"].sum())
    rate = round(done / total * 100, 2) if total else None
    print(
        f"{date_col}: tasks={total}, done_status={done}, "
        f"completion_rate={rate}%"
    )

print("\n===== REFERENCE D01 / APRIL 2025 =====")
print(
    ref[
        ref["department_id"].eq(sample_dept)
        & ref["month"].eq("2025-04-01")
    ][["tasks", "tasks_done", "task_completion_rate_pct"]].to_string(index=False)
)

print("\n===== PAYROLL D01 / APRIL 2025 =====")
payroll["period_end_date"] = pd.to_datetime(
    payroll["period_end_date"], errors="coerce"
)
p = payroll[
    payroll["department_id"].eq(sample_dept)
    & payroll["period_end_date"].dt.strftime("%Y-%m").eq(sample_month)
]
print("Rows:", len(p))
for col in ["employer_cost", "gross_pay", "overtime_pay", "overtime_hours_paid"]:
    if col in p.columns:
        print(f"{col}: {p[col].sum():,.2f}")
print("Unique employees:", p["employee_id"].nunique())

print("\n===== REFERENCE PAYROLL D01 / APRIL 2025 =====")
print(
    ref[
        ref["department_id"].eq(sample_dept)
        & ref["month"].eq("2025-04-01")
    ][["employer_cost", "gross_pay", "overtime_pay",
       "employees_paid", "overtime_hours"]].to_string(index=False)
)

print("\n===== ATTENDANCE D01 / APRIL 2025 =====")
attendance["period_end_date"] = pd.to_datetime(
    attendance["period_end_date"], errors="coerce"
)
a = attendance[
    attendance["department_id"].eq(sample_dept)
    & attendance["period_end_date"].dt.strftime("%Y-%m").eq(sample_month)
]
print("Rows:", len(a))
for col in ["scheduled_days", "present_days", "late_arrivals",
            "overtime_hours", "attendance_rate"]:
    if col in a.columns:
        print(f"{col}: sum={a[col].sum():,.2f}, mean={a[col].mean():.4f}")

print("\n===== REFERENCE ATTENDANCE D01 / APRIL 2025 =====")
print(
    ref[
        ref["department_id"].eq(sample_dept)
        & ref["month"].eq("2025-04-01")
    ][["attendance_rate", "late_arrivals", "overtime_hours"]].to_string(index=False)
)

print("\n===== HEADCOUNT D01 / APRIL 2025 =====")
headcount["month_start_date"] = pd.to_datetime(
    headcount["month_start_date"], errors="coerce"
)
h = headcount[
    headcount["department_id"].eq(sample_dept)
    & headcount["month_start_date"].dt.strftime("%Y-%m").eq(sample_month)
]
print(h.to_string(index=False))

print("\n===== PROFILE COMPLETE =====")
