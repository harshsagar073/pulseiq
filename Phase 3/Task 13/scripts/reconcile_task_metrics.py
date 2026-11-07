import pandas as pd
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
SOURCE = BASE / "data" / "source"
REFERENCE = BASE / "data" / "reference"
EVIDENCE = BASE / "evidence"

EVIDENCE.mkdir(parents=True, exist_ok=True)

tasks = pd.read_csv(SOURCE / "fact_task.csv")
teams = pd.read_csv(SOURCE / "dim_team.csv")
sprints = pd.read_csv(SOURCE / "dim_sprint.csv")
reference = pd.read_csv(
    REFERENCE / "unlock_PQ-13_reference_summary_dept_month.csv"
)

# Attribute each task to its team's department and sprint start month.
df = tasks.merge(
    teams[["team_id", "department_id"]],
    on="team_id",
    how="left",
    validate="many_to_one"
)

df = df.merge(
    sprints[["sprint_id", "start_date"]],
    on="sprint_id",
    how="left",
    validate="many_to_one"
)

df["month"] = pd.to_datetime(df["start_date"]).dt.strftime("%Y-%m-01")
df["is_done"] = df["status"].eq("Done")
df["is_planned"] = ~df["status"].eq("Cancelled")

# Aggregate tasks before joining to the reference.
df["planned_count"] = df["is_planned"].astype(int)
df["done_count"] = df["is_done"].astype(int)
df["done_points"] = df["story_points"].where(df["is_done"], 0)

actual = (
    df.groupby(["department_id", "month"], as_index=False)
      .agg(
          actual_tasks=("planned_count", "sum"),
          actual_tasks_done=("done_count", "sum"),
          actual_story_points_done=("done_points", "sum")
      )
)

actual["actual_task_completion_rate_pct"] = (
    actual["actual_tasks_done"] / actual["actual_tasks"] * 100
)

comparison = reference[
    [
        "department_id", "month", "tasks", "tasks_done",
        "story_points_done", "task_completion_rate_pct"
    ]
].merge(
    actual,
    on=["department_id", "month"],
    how="left",
    validate="one_to_one"
)

# Departments without teams have no productivity values.
comparison["has_reference_productivity"] = comparison["tasks"].notna()

for actual_col in [
    "actual_tasks", "actual_tasks_done", "actual_story_points_done"
]:
    comparison[actual_col] = comparison[actual_col].fillna(0)

comparison["tasks_match"] = (
    comparison["tasks"].isna()
    | (comparison["tasks"] == comparison["actual_tasks"])
)
comparison["tasks_done_match"] = (
    comparison["tasks_done"].isna()
    | (comparison["tasks_done"] == comparison["actual_tasks_done"])
)
comparison["story_points_match"] = (
    comparison["story_points_done"].isna()
    | (comparison["story_points_done"] == comparison["actual_story_points_done"])
)
comparison["completion_rate_match"] = (
    comparison["task_completion_rate_pct"].isna()
    | (
        comparison["task_completion_rate_pct"]
        == comparison["actual_task_completion_rate_pct"].round(1)
    )
)

comparison["all_metrics_match"] = comparison[
    ["tasks_match", "tasks_done_match", "story_points_match", "completion_rate_match"]
].all(axis=1)

output = EVIDENCE / "task_metrics_reconciliation.csv"
comparison.to_csv(output, index=False)

valid = comparison[comparison["has_reference_productivity"]]
missing = comparison[~comparison["has_reference_productivity"]]
mismatches = valid[~valid["all_metrics_match"]]

print("\n===== TASK 13 PRODUCTIVITY RECONCILIATION =====")
print(f"Source task rows: {len(tasks):,}")
print(f"Unique task IDs: {tasks['task_id'].nunique():,}")
print(f"Department-month reference rows: {len(comparison):,}")
print(f"Rows with productivity reference: {len(valid):,}")
print(f"Rows without productivity reference: {len(missing):,}")
print(f"Productivity rows fully matched: {len(valid) - len(mismatches):,}")
print(f"Productivity rows with mismatches: {len(mismatches):,}")
print(f"Evidence saved: {output}")

if len(mismatches):
    print("\n===== FIRST 20 MISMATCHES =====")
    print(
        mismatches[
            [
                "department_id", "month",
                "tasks", "actual_tasks",
                "tasks_done", "actual_tasks_done",
                "story_points_done", "actual_story_points_done",
                "task_completion_rate_pct",
                "actual_task_completion_rate_pct"
            ]
        ].head(20).to_string(index=False)
    )
else:
    print("\nSUCCESS: All department-month productivity metrics match the reference.")
