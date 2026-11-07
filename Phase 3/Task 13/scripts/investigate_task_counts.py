import pandas as pd
from pathlib import Path

base = Path(__file__).resolve().parents[1]
src = base / "data" / "source"

tasks = pd.read_csv(src / "fact_task.csv")
teams = pd.read_csv(src / "dim_team.csv")
employees = pd.read_csv(src / "dim_employee.csv")
ref = pd.read_csv(
    base / "data/reference/unlock_PQ-13_reference_summary_dept_month.csv"
)

tasks = tasks.merge(
    teams[["team_id", "department_id"]],
    on="team_id",
    how="left",
    validate="many_to_one"
)

tasks["created_date"] = pd.to_datetime(tasks["created_date"], errors="coerce")
tasks["completed_date"] = pd.to_datetime(tasks["completed_date"], errors="coerce")

d = tasks[
    tasks["department_id"].eq("D01")
    & tasks["created_date"].between("2025-04-01", "2025-04-30")
].copy()

known_employees = set(employees["employee_id"].dropna())
d["assignee_missing_in_employee_dim"] = ~d["assignee_employee_id"].isin(known_employees)

print("===== TASK FILE CHECK =====")
print("Task rows:", len(tasks))
print("Unique task IDs:", tasks["task_id"].nunique())
print("Missing task IDs:", tasks["task_id"].isna().sum())
print("Missing team IDs:", tasks["team_id"].isna().sum())
print("Missing assignees:", tasks["assignee_employee_id"].isna().sum())
print("Assignees not in employee dimension:", tasks["assignee_employee_id"].notna().sum() - tasks.loc[tasks["assignee_employee_id"].notna(), "assignee_employee_id"].isin(known_employees).sum())

print("\n===== D01 APRIL FILTER CHECK =====")
print("Created in April:", len(d))
print("Unique sprints:", d["sprint_id"].nunique())
print("Sprint counts:")
print(d["sprint_id"].value_counts(dropna=False).to_string())

print("\n===== D01 APRIL ASSIGNEE CHECK =====")
print("Missing assignee:", d["assignee_employee_id"].isna().sum())
print("Assignee absent from dimension:", d["assignee_missing_in_employee_dim"].sum())

print("\n===== D01 APRIL DATE CHECK =====")
print("Missing completed date:", d["completed_date"].isna().sum())
print("Done without completed date:", (
    d["status"].astype(str).str.lower().eq("done")
    & d["completed_date"].isna()
).sum())
print("Completed date before created date:", (
    d["completed_date"].notna()
    & (d["completed_date"] < d["created_date"])
).sum())

print("\n===== REFERENCE VS SOURCE =====")
print(ref[
    ref["department_id"].eq("D01")
    & ref["month"].eq("2025-04-01")
][["tasks", "tasks_done", "story_points_done", "task_completion_rate_pct"]].to_string(index=False))

print("\n===== STORY POINTS BY STATUS =====")
print(d.groupby("status", dropna=False)["story_points"].agg(["count", "sum"]).to_string())

print("\n===== CHECK COMPLETE =====")
