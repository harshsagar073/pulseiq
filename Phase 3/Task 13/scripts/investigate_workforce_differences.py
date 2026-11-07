import pandas as pd
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
SRC = BASE / "data/source"
REF = BASE / "data/reference"
WORKBOOK = Path(
    "/Users/admin/Desktop/PulseIQ/Phase 1/Task 1/03_Data/PulseIQ_Dataset.xlsx"
)

ref = pd.read_csv(
    REF / "unlock_PQ-13_reference_summary_dept_month.csv"
)
ref["month"] = pd.to_datetime(ref["month"]).dt.strftime("%Y-%m")

def read_csv(name, date_col):
    df = pd.read_csv(SRC / name)
    df["month"] = pd.to_datetime(df[date_col]).dt.strftime("%Y-%m")
    return df

def read_excel(sheet, date_col):
    df = pd.read_excel(WORKBOOK, sheet_name=sheet)
    df["month"] = pd.to_datetime(df[date_col]).dt.strftime("%Y-%m")
    return df

# Load local CSV and original workbook copies.
pay_csv = read_csv("fact_payroll.csv", "period_end_date")
pay_xls = read_excel("fact_payroll", "period_end_date")

att_csv = read_csv("fact_attendance_monthly.csv", "period_end_date")
att_xls = read_excel("fact_attendance_monthly", "period_end_date")

def compare_ids(label, csv_df, xls_df, id_col):
    a = set(csv_df[id_col].astype(str))
    b = set(xls_df[id_col].astype(str))
    print(f"\n===== {label} SOURCE ID CHECK =====")
    print("CSV rows:", len(csv_df), "| Workbook rows:", len(xls_df))
    print("IDs missing from CSV:", len(b - a))
    print("IDs extra in CSV:", len(a - b))
    if b - a:
        print("First missing IDs:", sorted(b - a)[:20])
    if a - b:
        print("First extra IDs:", sorted(a - b)[:20])

compare_ids("PAYROLL", pay_csv, pay_xls, "payroll_item_id")
compare_ids("ATTENDANCE", att_csv, att_xls, "attendance_fact_id")

# Aggregate original workbook payroll for comparison.
pay_original = (
    pay_xls.groupby(["department_id", "month"], as_index=False)
    .agg(
        xls_employer_cost=("employer_cost", "sum"),
        xls_gross_pay=("gross_pay", "sum"),
        xls_overtime_pay=("overtime_pay", "sum"),
        xls_employees_paid=("employee_id", "nunique")
    )
)

pay_local = (
    pay_csv.groupby(["department_id", "month"], as_index=False)
    .agg(
        csv_employer_cost=("employer_cost", "sum"),
        csv_gross_pay=("gross_pay", "sum"),
        csv_overtime_pay=("overtime_pay", "sum"),
        csv_employees_paid=("employee_id", "nunique")
    )
)

pay_check = ref.merge(
    pay_local, on=["department_id", "month"], how="left"
).merge(
    pay_original, on=["department_id", "month"], how="left"
)

pay_bad = pay_check[
    ((pay_check["employer_cost"] - pay_check["csv_employer_cost"]).abs() > 0.02)
    | ((pay_check["gross_pay"] - pay_check["csv_gross_pay"]).abs() > 0.02)
    | (pay_check["employees_paid"] != pay_check["csv_employees_paid"])
]

print("\n===== PAYROLL DIFFERENCES: REFERENCE / CSV / WORKBOOK =====")
if pay_bad.empty:
    print("No payroll differences.")
else:
    print(pay_bad[
        [
            "department_id", "month",
            "employer_cost", "csv_employer_cost", "xls_employer_cost",
            "gross_pay", "csv_gross_pay", "xls_gross_pay",
            "employees_paid", "csv_employees_paid", "xls_employees_paid"
        ]
    ].to_string(index=False))

# Aggregate attendance using different possible rate definitions.
att_csv["rate_from_days"] = (
    att_csv["present_days"] / att_csv["scheduled_days"]
)
att_xls["rate_from_days"] = (
    att_xls["present_days"] / att_xls["scheduled_days"]
)

att_agg = (
    att_csv.groupby(["department_id", "month"], as_index=False)
    .agg(
        csv_late_arrivals=("late_arrivals", "sum"),
        mean_employee_rate=("attendance_rate", "mean"),
        mean_ratio_from_days=("rate_from_days", "mean"),
        weighted_days_rate=("present_days", "sum"),
        scheduled_days_total=("scheduled_days", "sum"),
        attendance_rows=("employee_id", "nunique")
    )
)
att_agg["weighted_days_rate"] = (
    att_agg["weighted_days_rate"] / att_agg["scheduled_days_total"]
)

att_original = (
    att_xls.groupby(["department_id", "month"], as_index=False)
    .agg(
        xls_late_arrivals=("late_arrivals", "sum"),
        xls_mean_employee_rate=("attendance_rate", "mean"),
        xls_weighted_present=("present_days", "sum"),
        xls_scheduled=("scheduled_days", "sum")
    )
)
att_original["xls_weighted_days_rate"] = (
    att_original["xls_weighted_present"] / att_original["xls_scheduled"]
)

att_check = ref.merge(
    att_agg, on=["department_id", "month"], how="left"
).merge(
    att_original, on=["department_id", "month"], how="left"
)

late_bad = att_check[
    att_check["late_arrivals"] != att_check["csv_late_arrivals"]
]

print("\n===== LATE ARRIVAL DIFFERENCES =====")
if late_bad.empty:
    print("No late-arrival differences.")
else:
    print(late_bad[
        [
            "department_id", "month",
            "late_arrivals", "csv_late_arrivals", "xls_late_arrivals"
        ]
    ].to_string(index=False))

rate_methods = [
    ("mean_employee_rate", "Mean of attendance_rate"),
    ("mean_ratio_from_days", "Mean of present_days / scheduled_days"),
    ("weighted_days_rate", "Total present_days / total scheduled_days"),
    ("xls_mean_employee_rate", "Workbook mean attendance_rate"),
    ("xls_weighted_days_rate", "Workbook weighted day rate"),
]

print("\n===== ATTENDANCE RATE FORMULA COMPARISON =====")
for col, label in rate_methods:
    valid = att_check["attendance_rate"].notna() & att_check[col].notna()
    diff = (
        att_check.loc[valid, "attendance_rate"]
        - att_check.loc[valid, col]
    ).abs()
    print(
        f"{label}: within 0.00011 = "
        f"{int((diff <= 0.00011).sum())}/{int(valid.sum())}; "
        f"mean absolute difference = {diff.mean():.8f}"
    )

# Show first 15 rate differences for inspection.
bad_rate = att_check[
    (
        att_check["attendance_rate"]
        - att_check["mean_employee_rate"]
    ).abs() > 0.00011
]

print("\n===== FIRST 15 ATTENDANCE RATE EXAMPLES =====")
print(bad_rate[
    [
        "department_id", "month", "attendance_rate",
        "mean_employee_rate", "mean_ratio_from_days",
        "weighted_days_rate", "xls_mean_employee_rate",
        "xls_weighted_days_rate"
    ]
].head(15).to_string(index=False))

print("\nInvestigation complete. No source files were modified.")
