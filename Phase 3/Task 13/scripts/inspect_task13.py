import pandas as pd
from pathlib import Path

base = Path("data/source")

files = [
    "fact_headcount_monthly.csv",
    "fact_payroll.csv",
    "fact_attendance_monthly.csv",
    "fact_leave.csv",
    "fact_task.csv",
    "dim_department.csv",
    "dim_date.csv",
    "dim_employee.csv",
    "dim_team.csv",
]

print("\n========== TASK 13 SOURCE INSPECTION ==========")

for filename in files:
    path = base / filename
    df = pd.read_csv(path, low_memory=False)

    print(f"\nFILE: {filename}")
    print(f"Rows: {len(df):,}")
    print("Columns:", list(df.columns))

    if "department_id" in df.columns:
        print("Departments:", df["department_id"].nunique())

    for col in ["month_start_date", "period_end_date", "start_date",
                "created_date", "completed_date", "date"]:
        if col in df.columns:
            dates = pd.to_datetime(df[col], errors="coerce")
            print(f"{col} range: {dates.min()} to {dates.max()}")

    if filename == "fact_headcount_monthly.csv":
        keys = ["department_id", "month_start_date"]
        print("Duplicate department-month keys:", df.duplicated(keys).sum())

    if filename == "dim_employee.csv":
        print("Employee IDs:", df["employee_id"].nunique())
        print("Current employee versions:")
        print(df["is_current"].value_counts(dropna=False).to_dict())

    if filename == "dim_team.csv":
        print("Team-to-department mapping:")
        print(df[["team_id", "department_id"]].to_string(index=False))

print("\n========== INSPECTION COMPLETE ==========")
