import pandas as pd
import numpy as np
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
SRC = BASE / "data/source"
REF = BASE / "data/reference/unlock_PQ-13_reference_summary_dept_month.csv"
OUT = BASE / "evidence"
OUT.mkdir(exist_ok=True)

def read(name):
    return pd.read_csv(SRC / name)

def month_start(series):
    return pd.to_datetime(series, errors="coerce").dt.to_period("M").dt.to_timestamp()

def numeric(df, cols):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    return df

ref = pd.read_csv(REF)
ref["month"] = month_start(ref["month"])
keys = ["department_id", "month"]

# ---------- PAYROLL ----------
pay = read("fact_payroll.csv")
pay["month"] = month_start(pay["period_end_date"])
pay = numeric(pay, ["employer_cost", "gross_pay", "overtime_pay", "overtime_hours_paid"])

excluded_ids = ["PI-X0001", "PI-X0002", "PI-X0003", "PI-X0004"]
excluded = pay[pay["payroll_item_id"].astype(str).isin(excluded_ids)].copy()
excluded.to_csv(OUT / "excluded_payroll_rows_task13.csv", index=False)
pay = pay[~pay["payroll_item_id"].astype(str).isin(excluded_ids)].copy()

pay_m = pay.groupby(keys, as_index=False).agg(
    employer_cost=("employer_cost", "sum"),
    gross_pay=("gross_pay", "sum"),
    overtime_pay=("overtime_pay", "sum"),
    employees_paid=("employee_id", "nunique"),
    payroll_overtime_hours=("overtime_hours_paid", "sum")
)

# ---------- ATTENDANCE ----------
att = read("fact_attendance_monthly.csv")
att["month"] = month_start(att["period_end_date"])
att = numeric(att, [
    "present_days", "half_days_unpaid", "scheduled_days",
    "late_arrivals", "overtime_hours"
])
att["adjusted_present_days"] = (
    att["present_days"] + 0.5 * att["half_days_unpaid"]
)

att_m = att.groupby(keys, as_index=False).agg(
    attendance_adjusted_present=("adjusted_present_days", "sum"),
    attendance_scheduled_days=("scheduled_days", "sum"),
    late_arrivals=("late_arrivals", "sum"),
    attendance_overtime_hours=("overtime_hours", "sum"),
    attendance_employee_rows=("employee_id", "nunique")
)
att_m["attendance_rate_calculated"] = (
    att_m["attendance_adjusted_present"]
    / att_m["attendance_scheduled_days"].replace(0, np.nan)
)

# ---------- HEADCOUNT ----------
hc = read("fact_headcount_monthly.csv")
hc["month"] = month_start(hc["month_start_date"])
hc = numeric(hc, [
    "headcount_start", "headcount_end", "hires", "exits",
    "attrition_rate_monthly_pct"
])
hc_m = hc.groupby(keys, as_index=False).agg(
    headcount_start=("headcount_start", "sum"),
    headcount_end=("headcount_end", "sum"),
    hires=("hires", "sum"),
    exits=("exits", "sum"),
    attrition_rate_monthly_pct=("attrition_rate_monthly_pct", "mean")
)
hc_m["average_headcount"] = (
    hc_m["headcount_start"] + hc_m["headcount_end"]
) / 2

# ---------- APPROVED LEAVE, ALLOCATED BY WORKING DATE ----------
leave = read("fact_leave.csv")
dates = read("dim_date.csv")
employees = read("dim_employee.csv")

dates["date"] = pd.to_datetime(dates["date"], errors="coerce")
working_flag = dates["is_working_day"].astype(str).str.strip().str.lower()
working_dates = set(
    dates.loc[working_flag.isin(["1", "true", "y", "yes"]), "date"].dt.normalize()
)

leave["start_date"] = pd.to_datetime(leave["start_date"], errors="coerce")
leave["end_date"] = pd.to_datetime(leave["end_date"], errors="coerce")
leave["days"] = pd.to_numeric(leave["days"], errors="coerce").fillna(0)
leave["status"] = leave["status"].astype(str).str.strip().str.lower()

approved = leave[leave["status"].eq("approved")].copy()
invalid = approved[
    approved["start_date"].isna()
    | approved["end_date"].isna()
    | (approved["start_date"] > approved["end_date"])
].copy()
invalid.to_csv(OUT / "invalid_approved_leave_ranges.csv", index=False)
approved = approved.drop(index=invalid.index)

employees["valid_from"] = pd.to_datetime(employees["valid_from"], errors="coerce")
employees["valid_to"] = pd.to_datetime(employees["valid_to"], errors="coerce")
employees["department_id"] = employees["department_id"].astype(str)

leave_allocations = []
unallocated = []

for _, r in approved.iterrows():
    start = r["start_date"].normalize()
    end = r["end_date"].normalize()
    workdays = sorted(d for d in working_dates if start <= d <= end)

    if not workdays or r["days"] <= 0:
        unallocated.append({
            "leave_request_id": r.get("leave_request_id"),
            "employee_id": r.get("employee_id"),
            "start_date": start,
            "end_date": end,
            "days": r["days"],
            "reason": "No calendar working dates in request range or non-positive days"
        })
        continue

    # Spread the recorded request days evenly over its calendar working dates.
    daily_leave = r["days"] / len(workdays)

    for day in workdays:
        hist = employees[
            (employees["employee_id"].astype(str) == str(r["employee_id"]))
            & (employees["valid_from"] <= day)
            & (employees["valid_to"].isna() | (employees["valid_to"] >= day))
        ]

        if len(hist) == 1:
            dept = hist.iloc[0]["department_id"]
        else:
            # Fallback to the exact employee_key recorded on the leave fact.
            by_key = employees[
                employees["employee_key"].astype(str)
                == str(r.get("employee_key"))
            ]
            dept = by_key.iloc[0]["department_id"] if len(by_key) == 1 else None

        if not dept or dept == "nan":
            unallocated.append({
                "leave_request_id": r.get("leave_request_id"),
                "employee_id": r.get("employee_id"),
                "date": day,
                "days": daily_leave,
                "reason": f"Could not resolve department; SCD matches={len(hist)}"
            })
            continue

        leave_allocations.append({
            "department_id": dept,
            "month": day.to_period("M").to_timestamp(),
            "leave_days": daily_leave,
            "leave_request_id": r.get("leave_request_id")
        })

pd.DataFrame(unallocated).to_csv(
    OUT / "unallocated_leave_exceptions.csv", index=False
)

if leave_allocations:
    leave_daily = pd.DataFrame(leave_allocations)
    leave_m = leave_daily.groupby(keys, as_index=False).agg(
        approved_leave_days=("leave_days", "sum"),
        approved_leave_requests=("leave_request_id", "nunique")
    )
else:
    leave_m = pd.DataFrame(columns=keys + [
        "approved_leave_days", "approved_leave_requests"
    ])

# ---------- PRODUCTIVITY BY SPRINT START MONTH ----------
tasks = read("fact_task.csv")
teams = read("dim_team.csv")
sprints = read("dim_sprint.csv")

tasks = tasks.merge(
    teams[["team_id", "department_id"]], on="team_id", how="left"
)
tasks = tasks.merge(
    sprints[["sprint_id", "start_date"]], on="sprint_id", how="left"
)
tasks["month"] = month_start(tasks["start_date"])
tasks["status_clean"] = tasks["status"].astype(str).str.strip().str.lower()
tasks["story_points"] = pd.to_numeric(
    tasks["story_points"], errors="coerce"
).fillna(0)

valid_tasks = tasks[
    tasks["department_id"].notna()
    & tasks["month"].notna()
    & tasks["status_clean"].ne("cancelled")
].copy()
valid_tasks["is_done"] = valid_tasks["status_clean"].eq("done")
valid_tasks["done_points"] = np.where(
    valid_tasks["is_done"], valid_tasks["story_points"], 0
)

prod_m = valid_tasks.groupby(keys, as_index=False).agg(
    tasks=("status", "size"),
    tasks_done=("is_done", "sum"),
    story_points_done=("done_points", "sum")
)
prod_m["task_completion_rate_pct"] = (
    prod_m["tasks_done"] / prod_m["tasks"] * 100
)

# ---------- BUILD ONE ROW PER REFERENCE DEPARTMENT-MONTH ----------
result = ref[keys].copy()
for frame in [pay_m, att_m, hc_m, leave_m, prod_m]:
    result = result.merge(frame, on=keys, how="left", validate="one_to_one")

# Preserve missing productivity as N/A, particularly D00 and D10.
result["task_completion_rate_pct"] = np.where(
    result["tasks"].isna(), np.nan, result["task_completion_rate_pct"]
)

result["cost_per_head_calculated"] = (
    result["employer_cost"] / result["employees_paid"].replace(0, np.nan)
)
result["overtime_share_pct_calculated"] = (
    result["overtime_pay"] / result["employer_cost"].replace(0, np.nan) * 100
)
result["overtime_cost_per_paid_employee"] = (
    result["overtime_pay"] / result["employees_paid"].replace(0, np.nan)
)
result["leave_days_per_average_head"] = (
    result["approved_leave_days"] / result["average_headcount"].replace(0, np.nan)
)

# ---------- RECONCILIATION ----------
comparison = result.merge(
    ref, on=keys, how="left", suffixes=("_calculated", "_reference"),
    validate="one_to_one"
)

metrics = [
    ("employer_cost", 0.02),
    ("gross_pay", 0.02),
    ("overtime_pay", 0.02),
    ("employees_paid", 0),
    ("payroll_overtime_hours", 0.00001),
    ("late_arrivals", 0),
    ("attendance_rate_calculated", 0.00011),
    ("headcount_end", 0),
    ("hires", 0),
    ("exits", 0),
    ("attrition_rate_monthly_pct", 0.011),
    ("tasks", 0),
    ("tasks_done", 0),
    ("story_points_done", 0),
    ("task_completion_rate_pct", 0.11),
]

rows = []
for metric, tolerance in metrics:
    ref_metric = metric
    if metric == "payroll_overtime_hours":
        ref_metric = "overtime_hours"
    elif metric == "attendance_rate_calculated":
        ref_metric = "attendance_rate"

    left = comparison.get(metric + "_calculated")
    if left is None:
        left = comparison.get(metric)
    right = comparison.get(ref_metric + "_reference")
    if right is None:
        right = comparison.get(ref_metric)

    if left is None or right is None:
        continue

    valid = left.notna() & right.notna()
    matched = ((left - right).abs() <= tolerance) & valid
    rows.append({
        "metric": metric,
        "compared": int(valid.sum()),
        "matched": int(matched.sum()),
        "mismatched": int((valid & ~matched).sum()),
        "tolerance": tolerance
    })

recon = pd.DataFrame(rows)
recon.to_csv(OUT / "task13_reconciliation_summary.csv", index=False)

# Keep source reference fields for side-by-side review.
result.to_csv(OUT / "department_month_comparison.csv", index=False)

# Detailed variance table for key reference measures.
variance_rows = []
for metric in [
    "employer_cost", "gross_pay", "overtime_pay", "employees_paid",
    "late_arrivals", "attendance_rate", "headcount_end", "hires", "exits",
    "attrition_rate_monthly_pct", "tasks", "tasks_done",
    "story_points_done", "task_completion_rate_pct"
]:
    calc_col = {
        "attendance_rate": "attendance_rate_calculated"
    }.get(metric, metric)

    if calc_col not in result.columns or metric not in ref.columns:
        continue

    left = result[keys + [calc_col]].rename(
        columns={calc_col: "calculated"}
    )
    right = ref[keys + [metric]].rename(
        columns={metric: "reference"}
    )

    tmp = left.merge(right, on=keys, how="left", validate="one_to_one")
    tmp["metric"] = metric
    tmp["difference"] = tmp["calculated"] - tmp["reference"]

    variance_rows.append(
        tmp[keys + ["metric", "calculated", "reference", "difference"]]
    )

if variance_rows:
    pd.concat(variance_rows, ignore_index=True).to_csv(
        OUT / "task13_metric_variances.csv", index=False
    )

# Three transparent hand checks.
hand = []
def add_check(name, detail, passed):
    hand.append({"check": name, "detail": detail, "result": "PASS" if passed else "REVIEW"})

add_check(
    "Department-month grain",
    f"{len(result)} rows; {result[keys].drop_duplicates().shape[0]} unique keys",
    len(result) == 198 and not result.duplicated(keys).any()
)
add_check(
    "Payroll exclusion audit",
    f"{len(excluded)} excluded rows; IDs={','.join(excluded['payroll_item_id'].astype(str).tolist())}",
    set(excluded["payroll_item_id"].astype(str)) == set(excluded_ids)
)
add_check(
    "Productivity applicability",
    f"{int(result['tasks'].notna().sum())} populated department-months; "
    f"{int(result['tasks'].isna().sum())} N/A department-months",
    int(result["tasks"].notna().sum()) == 162
)
pd.DataFrame(hand).to_csv(OUT / "task13_hand_checks.csv", index=False)

notes = f"""TASK 13 BUILD NOTES

Grain: one row per department-month, based on the supplied reference key.
Rows: {len(result)}
Unique department-month keys: {result[keys].drop_duplicates().shape[0]}

Payroll:
- Excluded PI-X0001 through PI-X0004 from Task 13 payroll aggregations.
- Two are duplicate employee-month payroll rows; two refer to employee IDs absent from dim_employee.
- Original source CSV was not changed. Excluded rows are preserved in excluded_payroll_rows_task13.csv.

Attendance:
- Retained attendance fact rows using their recorded department and employee-month.
- Used (present_days + 0.5 * half_days_unpaid) / scheduled_days for the department-month attendance rate.
- Attendance rows are not dropped solely because the employee's SCD dimension validity ends before month-end.
- SCD exceptions should be reviewed as dimension-maintenance issues, not treated as proof that the fact rows are invalid.

Leave:
- Included Approved requests only.
- Excluded invalid approved date ranges from monthly allocation; see invalid_approved_leave_ranges.csv.
- Allocated each request's recorded days proportionally across calendar working dates in the request interval.
- Assigned department using employee SCD validity on each working date, with employee_key fallback.
- Any unresolved rows are listed in unallocated_leave_exceptions.csv.

Productivity:
- Joined task to team and sprint.
- Attributed each task to the sprint start month.
- Excluded Cancelled tasks from the denominator; Done tasks contribute to completed tasks and story points.
- D00 and D10 have no team mapping, so productivity remains N/A rather than zero.

Derived metrics:
- Cost per head = employer_cost / employees_paid.
- Overtime share = overtime_pay / employer_cost * 100.
- Overtime cost per paid employee = overtime_pay / employees_paid.
- Leave days per average head = approved_leave_days / ((headcount_start + headcount_end) / 2).

Interpretation:
- Department-level patterns and correlations are descriptive, not proof of causation.
- Payroll and attendance differences are retained in reconciliation evidence, not silently overwritten to force a match.
"""
(OUT / "task13_methodology_and_findings.txt").write_text(notes, encoding="utf-8")

print("\n===== TASK 13 FINAL BUILD =====")
print("Department-month rows:", len(result))
print("Unique keys:", result[keys].drop_duplicates().shape[0])
print("\nReconciliation:")
print(recon.to_string(index=False))
print("\nHand checks:")
print(pd.DataFrame(hand).to_string(index=False))
print("\nLeave:")
print("Approved requests:", len(approved))
print("Invalid approved ranges:", len(invalid))
print("Allocated leave-day rows:", len(leave_allocations))
print("Unallocated leave exceptions:", len(unallocated))
print("\nProductivity populated rows:", int(result["tasks"].notna().sum()))
print("Productivity N/A rows:", int(result["tasks"].isna().sum()))
print("\nCreated:")
for f in sorted(OUT.glob("task13_*")):
    print(" -", f)
print(" -", OUT / "department_month_comparison.csv")
print(" -", OUT / "excluded_payroll_rows_task13.csv")
