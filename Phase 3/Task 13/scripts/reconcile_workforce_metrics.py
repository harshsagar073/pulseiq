import pandas as pd
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
SRC = BASE / "data/source"
REF = BASE / "data/reference"
EVIDENCE = BASE / "evidence"
EVIDENCE.mkdir(exist_ok=True)

ref = pd.read_csv(
    REF / "unlock_PQ-13_reference_summary_dept_month.csv"
)
ref["month"] = pd.to_datetime(ref["month"]).dt.strftime("%Y-%m-01")

payroll = pd.read_csv(SRC / "fact_payroll.csv")
attendance = pd.read_csv(SRC / "fact_attendance_monthly.csv")
headcount = pd.read_csv(SRC / "fact_headcount_monthly.csv")

def month_start(series):
    return pd.to_datetime(series).dt.to_period("M").dt.to_timestamp().dt.strftime("%Y-%m-%d")

# ---------------- PAYROLL ----------------
payroll["month"] = month_start(payroll["period_end_date"])

pay = (
    payroll.groupby(["department_id", "month"], as_index=False)
    .agg(
        actual_employer_cost=("employer_cost", "sum"),
        actual_gross_pay=("gross_pay", "sum"),
        actual_overtime_pay=("overtime_pay", "sum"),
        actual_employees_paid=("employee_id", "nunique"),
        payroll_overtime_hours=("overtime_hours_paid", "sum")
    )
)

# ---------------- ATTENDANCE ----------------
attendance["month"] = month_start(attendance["period_end_date"])

att = (
    attendance.groupby(["department_id", "month"], as_index=False)
    .agg(
        actual_late_arrivals=("late_arrivals", "sum"),
        actual_attendance_rate=("attendance_rate", "mean"),
        attendance_overtime_hours=("overtime_hours", "sum"),
        attendance_employee_rows=("employee_id", "nunique")
    )
)

# ---------------- HEADCOUNT ----------------
headcount["month"] = month_start(headcount["month_start_date"])

hc = headcount[
    [
        "department_id", "month",
        "headcount_start", "hires", "exits",
        "headcount_end", "attrition_rate_monthly_pct"
    ]
].copy()

hc = hc.rename(columns={
    "headcount_start": "actual_headcount_start",
    "hires": "actual_hires",
    "exits": "actual_exits",
    "headcount_end": "actual_headcount_end",
    "attrition_rate_monthly_pct": "actual_attrition_rate"
})

# ---------------- COMBINE AGGREGATED SOURCES ----------------
result = ref.merge(
    pay, on=["department_id", "month"], how="left",
    validate="one_to_one"
)
result = result.merge(
    att, on=["department_id", "month"], how="left",
    validate="one_to_one"
)
result = result.merge(
    hc, on=["department_id", "month"], how="left",
    validate="one_to_one"
)

checks = [
    ("employer_cost", "actual_employer_cost", 0.02),
    ("gross_pay", "actual_gross_pay", 0.02),
    ("overtime_pay", "actual_overtime_pay", 0.02),
    ("employees_paid", "actual_employees_paid", 0),
    ("late_arrivals", "actual_late_arrivals", 0),
    ("attendance_rate", "actual_attendance_rate", 0.00011),
    ("headcount_end", "actual_headcount_end", 0),
    ("hires", "actual_hires", 0),
    ("exits", "actual_exits", 0),
    ("attrition_rate_monthly_pct", "actual_attrition_rate", 0.011),
]

summary = []

for reference_col, actual_col, tolerance in checks:
    valid = result[reference_col].notna() & result[actual_col].notna()
    difference = (
        result.loc[valid, reference_col]
        - result.loc[valid, actual_col]
    ).abs()

    passed = difference <= tolerance
    summary.append({
        "metric": reference_col,
        "compared_rows": int(valid.sum()),
        "matched_rows": int(passed.sum()),
        "mismatched_rows": int((~passed).sum()),
        "tolerance": tolerance
    })

summary_df = pd.DataFrame(summary)
summary_df.to_csv(
    EVIDENCE / "workforce_reconciliation_summary.csv",
    index=False
)

result.to_csv(
    EVIDENCE / "workforce_metrics_reconciliation.csv",
    index=False
)

print("\n===== WORKFORCE RECONCILIATION SUMMARY =====")
print(summary_df.to_string(index=False))

print("\n===== OVERTIME HOURS SOURCE COMPARISON =====")
print("Reference overtime_hours vs payroll overtime_hours_paid:")
valid = result["overtime_hours"].notna() & result["payroll_overtime_hours"].notna()
print(
    "Matched:",
    int((
        result.loc[valid, "overtime_hours"]
        == result.loc[valid, "payroll_overtime_hours"]
    ).sum()),
    "/",
    int(valid.sum())
)

print("Reference overtime_hours vs attendance overtime_hours:")
valid = result["overtime_hours"].notna() & result["attendance_overtime_hours"].notna()
print(
    "Matched:",
    int((
        result.loc[valid, "overtime_hours"]
        == result.loc[valid, "attendance_overtime_hours"]
    ).sum()),
    "/",
    int(valid.sum())
)

print("\n===== FIRST 15 WORKFORCE MISMATCHES =====")
mismatch_rows = []

for reference_col, actual_col, tolerance in checks:
    bad = result[
        result[reference_col].notna()
        & result[actual_col].notna()
        & (
            (result[reference_col] - result[actual_col]).abs()
            > tolerance
        )
    ].copy()

    if not bad.empty:
        bad["metric"] = reference_col
        bad["reference_value"] = bad[reference_col]
        bad["actual_value"] = bad[actual_col]
        mismatch_rows.append(
            bad[
                [
                    "department_id", "month", "metric",
                    "reference_value", "actual_value"
                ]
            ]
        )

if mismatch_rows:
    print(
        pd.concat(mismatch_rows, ignore_index=True)
        .head(15).to_string(index=False)
    )
else:
    print("All tested workforce metrics match.")

print("\n===== SOURCE GRAIN CHECK =====")
print("Payroll rows:", len(payroll))
print("Payroll department-month rows:", len(pay))
print("Attendance rows:", len(attendance))
print("Attendance department-month rows:", len(att))
print("Headcount rows:", len(headcount))
print("Headcount duplicate department-month keys:",
      int(headcount.duplicated(["department_id", "month"]).sum()))

print("\nEvidence files saved:")
print(EVIDENCE / "workforce_reconciliation_summary.csv")
print(EVIDENCE / "workforce_metrics_reconciliation.csv")
