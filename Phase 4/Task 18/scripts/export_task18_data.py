from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "Phase 3" / "Task 13" / "data" / "source"
OUT = Path(__file__).resolve().parents[1] / "data"
OUT.mkdir(parents=True, exist_ok=True)

def read(name):
    path = SOURCE / name
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path)

def num(df, cols):
    for col in cols:
        if col in df:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df

# Official catalog thresholds. Sensitive employee groups use at least 10.
catalog = {
    "M01": ("Headcount", 5, "employees"),
    "M02": ("Hires", 5, "employees"),
    "M03": ("Exits", 5, "employees"),
    "M04": ("Monthly attrition rate", 10, "percent"),
    "M07": ("Gross pay", 5, "INR"),
    "M08": ("Net pay", 5, "INR"),
    "M09": ("Payroll cost", 5, "INR"),
    "M10": ("Cost per head", 5, "INR"),
    "M11": ("Overtime share", 5, "percent"),
    "M12": ("Variable pay share", 5, "percent"),
    "M13": ("Attendance rate", 5, "percent"),
    "M14": ("Late arrival rate", 5, "percent"),
    "M22": ("Task completion rate", 5, "percent"),
    "M23": ("On-time delivery", 5, "percent"),
    "M24": ("Velocity", 0, "points"),
    "M25": ("Average cycle time", 5, "days"),
}
catalog = {
    k: {"name": v[0], "minimum": max(10, v[1]), "unit": v[2]}
    for k, v in catalog.items()
}

# Department-month workforce data.
hc = read("fact_headcount_monthly.csv")
hc["month"] = pd.to_datetime(hc["month_start_date"], errors="coerce")
hc = num(hc, ["headcount_start", "headcount_end", "hires", "exits",
              "voluntary_exits"])
work = hc.groupby(["department_id", "month"], as_index=False).agg(
    headcount_start=("headcount_start", "sum"),
    headcount_end=("headcount_end", "sum"),
    hires=("hires", "sum"),
    exits=("exits", "sum"),
    voluntary_exits=("voluntary_exits", "sum"),
)
work["attrition_pct"] = (
    work["exits"] / work["headcount_start"].replace(0, pd.NA) * 100
)

# Payroll aggregates; employee identifiers are used only for counting,
# never included in the exported file.
pay = read("fact_payroll.csv")
pay["month"] = pd.to_datetime(pay["period_end_date"], errors="coerce").dt.to_period("M").dt.to_timestamp()
pay = num(pay, ["gross_pay", "net_pay", "employer_cost",
                "overtime_pay", "variable_pay"])
payroll = pay.groupby(["department_id", "month"], as_index=False).agg(
    payroll_employees=("employee_id", "nunique"),
    gross_pay=("gross_pay", "sum"),
    net_pay=("net_pay", "sum"),
    employer_cost=("employer_cost", lambda x: x.sum(min_count=1)),
    overtime_pay=("overtime_pay", lambda x: x.sum(min_count=1)),
    variable_pay=("variable_pay", "sum"),
)
payroll["cost_per_head"] = (
    payroll["employer_cost"] /
    payroll["payroll_employees"].replace(0, pd.NA)
)
payroll["overtime_share_pct"] = (
    payroll["overtime_pay"] /
    payroll["employer_cost"].replace(0, pd.NA) * 100
)
payroll["variable_pay_share_pct"] = (
    payroll["variable_pay"] /
    payroll["gross_pay"].replace(0, pd.NA) * 100
)

# Attendance aggregates.
att = read("fact_attendance_monthly.csv")
att["month"] = pd.to_datetime(att["period_end_date"], errors="coerce").dt.to_period("M").dt.to_timestamp()
att = num(att, ["scheduled_days", "present_days", "half_days_unpaid",
                "late_arrivals"])
att["adjusted_present"] = att["present_days"] + 0.5 * att["half_days_unpaid"]
attendance = att.groupby(["department_id", "month"], as_index=False).agg(
    attendance_employees=("employee_id", "nunique"),
    adjusted_present=("adjusted_present", lambda x: x.sum(min_count=1)),
    scheduled_days=("scheduled_days", lambda x: x.sum(min_count=1)),
    late_arrivals=("late_arrivals", lambda x: x.sum(min_count=1)),
    present_days=("present_days", lambda x: x.sum(min_count=1)),
)
attendance["attendance_pct"] = (
    attendance["adjusted_present"] /
    attendance["scheduled_days"].replace(0, pd.NA) * 100
)
attendance["late_arrival_pct"] = (
    attendance["late_arrivals"] /
    attendance["present_days"].replace(0, pd.NA) * 100
)

dept = work.merge(payroll, on=["department_id", "month"], how="left")
dept = dept.merge(attendance, on=["department_id", "month"], how="left")

# Conservative group size: require at least 10 for every employee-derived
# department metric. Also suppress a second department to prevent subtraction
# from the already-public company totals in Task 17.
dept["privacy_count"] = dept[
    ["headcount_start", "headcount_end"]
].min(axis=1)

# Company totals are calculated before department suppression.
company = dept.groupby("month", as_index=False).agg(
    headcount_start=("headcount_start", "sum"),
    headcount_end=("headcount_end", "sum"),
    hires=("hires", "sum"),
    exits=("exits", "sum"),
    employer_cost=("employer_cost", lambda x: x.sum(min_count=1)),
    payroll_employees=("payroll_employees", lambda x: x.sum(min_count=1)),
    overtime_pay=("overtime_pay", lambda x: x.sum(min_count=1)),
    adjusted_present=("adjusted_present", lambda x: x.sum(min_count=1)),
    scheduled_days=("scheduled_days", lambda x: x.sum(min_count=1)),
    late_arrivals=("late_arrivals", lambda x: x.sum(min_count=1)),
    present_days=("present_days", lambda x: x.sum(min_count=1)),
)
company["attrition_pct"] = company["exits"] / company["headcount_start"].replace(0, pd.NA) * 100
company["cost_per_head"] = company["employer_cost"] / company["payroll_employees"].replace(0, pd.NA)
company["overtime_share_pct"] = company["overtime_pay"] / company["employer_cost"].replace(0, pd.NA) * 100
company["attendance_pct"] = company["adjusted_present"] / company["scheduled_days"].replace(0, pd.NA) * 100
company["late_arrival_pct"] = company["late_arrivals"] / company["present_days"].replace(0, pd.NA) * 100

# Mask department metrics when their own employee/event group is below 10.
# Company totals above are calculated before these department-only masks.
dept.loc[dept["hires"] < 10, ["hires"]] = pd.NA
dept.loc[dept["exits"] < 10, ["exits", "voluntary_exits"]] = pd.NA

payroll_fields = [
    "payroll_employees", "gross_pay", "net_pay", "employer_cost",
    "overtime_pay", "variable_pay", "cost_per_head",
    "overtime_share_pct", "variable_pay_share_pct",
]
small_payroll = dept["payroll_employees"].notna() & dept["payroll_employees"].lt(10)
dept.loc[small_payroll, payroll_fields] = pd.NA

attendance_fields = [
    "attendance_employees", "adjusted_present", "scheduled_days",
    "late_arrivals", "present_days", "attendance_pct", "late_arrival_pct",
]
small_attendance = dept["attendance_employees"].notna() & dept["attendance_employees"].lt(10)
dept.loc[small_attendance, attendance_fields] = pd.NA

company.to_csv(OUT / "company_month.csv", index=False)

# Complementary suppression: hide the smallest otherwise-visible department
# in each month as well as any group below 10.
dept["primary_suppressed"] = dept["privacy_count"] < 10
dept["secondary_suppressed"] = False
for month, group in dept.groupby("month"):
    visible = group.loc[~group["primary_suppressed"]]
    if len(group.loc[group["primary_suppressed"]]) == 1 and len(visible):
        secondary_id = visible.sort_values("privacy_count").iloc[0]["department_id"]
        dept.loc[
            (dept["month"] == month) &
            (dept["department_id"] == secondary_id),
            "secondary_suppressed"
        ] = True

dept["suppressed"] = dept["primary_suppressed"] | dept["secondary_suppressed"]
dept = dept.loc[~dept["suppressed"]].copy()

# Remove identifiers not needed for aggregate exploration.
dept["month"] = dept["month"].dt.strftime("%Y-%m-%d")
dept = dept.drop(columns=["primary_suppressed", "secondary_suppressed",
                          "suppressed", "privacy_count"], errors="ignore")
dept.to_csv(OUT / "department_month.csv", index=False)

# Team/sprint productivity. Only aggregates leave this script.
tasks = read("fact_task.csv")
tasks["story_points"] = pd.to_numeric(tasks["story_points"], errors="coerce").fillna(0)
tasks["status_clean"] = tasks["status"].astype(str).str.upper()
tasks["is_done"] = tasks["status_clean"].eq("DONE")
tasks["is_eligible"] = tasks["status_clean"].ne("CANCELLED")
tasks["on_time"] = (
    tasks["is_done"]
    & tasks["completed_on_time"].astype(str).str.upper().isin(["Y", "TRUE", "1"])
)
tasks["started_date_parsed"] = pd.to_datetime(tasks["started_date"], errors="coerce")
tasks["completed_date_parsed"] = pd.to_datetime(tasks["completed_date"], errors="coerce")
tasks["cycle_days"] = (
    tasks["completed_date_parsed"] - tasks["started_date_parsed"]
).dt.days
tasks["valid_cycle_days"] = (
    tasks["is_done"]
    & tasks["started_date_parsed"].notna()
    & tasks["completed_date_parsed"].notna()
    & tasks["cycle_days"].ge(0)
)

team = tasks.groupby(["team_id", "sprint_id"], as_index=False).agg(
    distinct_assignees=("assignee_employee_id", "nunique"),
    total_tasks=("task_id", "count"),
    eligible_tasks=("is_eligible", "sum"),
    done_tasks=("is_done", "sum"),
    on_time_tasks=("on_time", "sum"),
    valid_cycle_tasks=("valid_cycle_days", "sum"),
    story_points_done=("story_points", lambda s: s[tasks.loc[s.index, "is_done"]].sum()),
    average_cycle_time=("cycle_days", lambda s: s[tasks.loc[s.index, "valid_cycle_days"]].mean()),
)
team["completion_pct"] = (
    team["done_tasks"] / team["eligible_tasks"].replace(0, pd.NA) * 100
).where(team["eligible_tasks"] >= 10)
team["on_time_pct"] = (
    team["on_time_tasks"] / team["done_tasks"].replace(0, pd.NA) * 100
).where(team["done_tasks"] >= 10)
team["average_cycle_time"] = team["average_cycle_time"].where(
    team["valid_cycle_tasks"] >= 10
)

dim_team = read("dim_team.csv")[["team_id", "team_name", "department_id"]]
team = team.merge(dim_team, on="team_id", how="left")
team = team.loc[team["distinct_assignees"] >= 10].copy()
team.to_csv(OUT / "team_sprint.csv", index=False)

# Publish the metric dictionary used by the explorer.
(OUT / "metric_dictionary.json").write_text(
    json.dumps(catalog, indent=2), encoding="utf-8"
)

metadata = {
    "source": "Phase 3 Task 13 approved aggregate source CSVs",
    "generated_from": "department-month workforce/payroll/attendance and team-sprint task data",
    "minimum_group_size": 10,
    "complementary_suppression": True,
    "employee_level_data_exported": False,
    "employee_identifiers_exported": False,
    "department_month_rows_after_suppression": len(dept),
    "team_sprint_rows_after_suppression": len(team),
    "note": "Demo role selection is not authentication. Team payroll and team attrition are not available and are not inferred."
}
(OUT / "metadata.json").write_text(
    json.dumps(metadata, indent=2), encoding="utf-8"
)

print("TASK 18 SAFE DATA EXPORT")
print("Department-month rows:", len(dept))
print("Team-sprint rows:", len(team))
print("Suppression threshold: 10")
print("Complementary suppression: enabled")
print("Employee-level records exported: NO")
print("Employee identifiers exported: NO")
print("Output:", OUT)
