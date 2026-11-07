import pandas as pd
from pathlib import Path

base = Path(__file__).resolve().parents[1]
tasks = pd.read_csv(base / "data/source/fact_task.csv")
ref = pd.read_csv(base / "data/reference/unlock_PQ-13_reference_summary_dept_month.csv")
teams = pd.read_csv(base / "data/source/dim_team.csv")

tasks = tasks.merge(
    teams[["team_id", "department_id"]],
    on="team_id",
    how="left",
    validate="many_to_one"
)

tasks["created_date"] = pd.to_datetime(tasks["created_date"], errors="coerce")
tasks["completed_date"] = pd.to_datetime(tasks["completed_date"], errors="coerce")
tasks["due_date"] = pd.to_datetime(tasks["due_date"], errors="coerce")

d = tasks[
    tasks["department_id"].eq("D01")
    & tasks["created_date"].dt.strftime("%Y-%m").eq("2025-04")
].copy()

print("===== D01 APRIL CREATED TASKS =====")
print("Total rows:", len(d))
print("Unique task IDs:", d["task_id"].nunique())
print("\nStatus counts:")
print(d["status"].value_counts(dropna=False).to_string())

print("\n===== TASK FLAGS =====")
for col in ["completed_on_time", "is_overdue_at_cutoff"]:
    if col in d.columns:
        print(f"\n{col}:")
        print(d[col].value_counts(dropna=False).to_string())

print("\n===== TASK TYPE COUNTS =====")
print(d["task_type"].value_counts(dropna=False).to_string())

print("\n===== POSSIBLE FILTER COUNTS =====")
print("All created:", len(d))
print("Excluding Cancelled:", (~d["status"].astype(str).str.lower().eq("cancelled")).sum())
print("Done status:", d["status"].astype(str).str.lower().eq("done").sum())
print("Done excluding Cancelled:", (
    d["status"].astype(str).str.lower().eq("done")
    & ~d["status"].astype(str).str.lower().eq("cancelled")
).sum())

print("\n===== REFERENCE =====")
print(ref[
    ref["department_id"].eq("D01")
    & ref["month"].eq("2025-04-01")
][["tasks", "tasks_done", "story_points_done", "task_completion_rate_pct"]].to_string(index=False))

print("\n===== DUPLICATE TASK IDs =====")
print("Duplicate rows:", tasks["task_id"].duplicated().sum())

print("\n===== SAMPLE TASK RECORDS =====")
print(d.head(8).to_string(index=False))
