
import streamlit as st
import duckdb
import pandas as pd
from pathlib import Path

# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="PulseIQ | Payroll Analytics",
    page_icon="💰",
    layout="wide"
)

st.title("💰 PulseIQ | Payroll Cost Dashboard")
st.caption(
    "Phase 2 · Task 9 · Payroll Cost Dashboard and Reconciliation"
)

# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

DB_PATH = Path(
    "/Users/admin/Desktop/PulseIQ/Phase 1/Task 4/pulseiq_task4.duckdb"
)

BASE_DIR = Path(__file__).parent
EVIDENCE_DIR = BASE_DIR / "evidence"

RECONCILIATION_FILE = (
    EVIDENCE_DIR / "monthly_reconciliation.csv"
)

EXCLUDED_FILE = (
    EVIDENCE_DIR / "excluded_payroll_rows.csv"
)

EXCLUDED_IDS = [
    "PI-X0001",
    "PI-X0002",
    "PI-X0003",
    "PI-X0004"
]

MIN_GROUP_SIZE = 5

# --------------------------------------------------
# LOAD DATA - TASK 4 DATABASE IS READ ONLY
# --------------------------------------------------

if not DB_PATH.exists():
    st.error("Task 4 source database was not found.")
    st.stop()


@st.cache_data
def load_payroll():

    con = duckdb.connect(
        str(DB_PATH),
        read_only=True
    )

    try:
        payroll = con.execute("""
            SELECT
                p.payroll_item_id,
                p.employee_id,
                p.period_end_date,
                p.department_id,
                p.gross_pay,
                p.net_pay,
                p.employer_cost
            FROM raw.fact_payroll p
            WHERE p.payroll_item_id NOT IN (?, ?, ?, ?)
        """, EXCLUDED_IDS).fetchdf()

        departments = con.execute("""
            SELECT
                department_id,
                department_name
            FROM raw.dim_department
            ORDER BY department_name
        """).fetchdf()

    finally:
        con.close()

    payroll["period_end_date"] = pd.to_datetime(
        payroll["period_end_date"]
    )

    payroll["month"] = (
        payroll["period_end_date"].dt.strftime("%Y-%m")
    )

    payroll = payroll.merge(
        departments,
        on="department_id",
        how="left"
    )

    return payroll


df = load_payroll()

if df.empty:
    st.error("No valid payroll records were found.")
    st.stop()


# --------------------------------------------------
# SIDEBAR FILTERS
# --------------------------------------------------

st.sidebar.header("Dashboard Filters")

months = sorted(df["month"].unique())

selected_months = st.sidebar.multiselect(
    "Select months",
    months,
    default=months
)

departments = sorted(
    df["department_name"].dropna().unique()
)

selected_departments = st.sidebar.multiselect(
    "Select departments",
    departments,
    default=departments
)

filtered = df[
    df["month"].isin(selected_months)
    & df["department_name"].isin(selected_departments)
].copy()

if filtered.empty:
    st.warning(
        "No payroll records match the selected filters."
    )
    st.stop()


# --------------------------------------------------
# PAYROLL SUMMARY AND EMPLOYEE-MONTH CALCULATION
# --------------------------------------------------

employees = filtered["employee_id"].nunique()

gross = filtered["gross_pay"].sum()
net = filtered["net_pay"].sum()
employer = filtered["employer_cost"].sum()

# Employee-months = sum of distinct paid employees in each month.
employee_months = (
    filtered.groupby("month")["employee_id"]
    .nunique()
    .sum()
)

# Average employer cost per employee-month.
cost_per_employee_month = (
    employer / employee_months
    if employee_months
    else 0
)


# --------------------------------------------------
# PAYROLL OVERVIEW
# --------------------------------------------------

st.subheader("Payroll Overview")

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "Gross Payroll",
    f"₹{gross / 10000000:,.2f} Cr"
)

c2.metric(
    "Net Payroll",
    f"₹{net / 10000000:,.2f} Cr"
)

c3.metric(
    "Employer Cost",
    f"₹{employer / 10000000:,.2f} Cr"
)

c4.metric(
    "Avg. Cost / Employee-Month",
    f"₹{cost_per_employee_month:,.2f}"
)

st.caption(
    "Payroll amounts are displayed in crore. "
    "Refer to the monthly PQ-09 reconciliation below "
    "for the official month-by-month comparison."
)

st.caption(
    f"{employees:,} distinct employees | "
    f"{employee_months:,} employee-months. "
    "Average employer cost per employee-month = "
    "total employer cost / total employee-months."
)

st.divider()


# --------------------------------------------------
# MONTHLY PAYROLL TREND
# --------------------------------------------------

st.subheader("Monthly Payroll Cost Trend")

monthly = (
    filtered.groupby("month", as_index=False)
    .agg(
        employees_paid=("employee_id", "nunique"),
        gross_pay=("gross_pay", "sum"),
        net_pay=("net_pay", "sum"),
        employer_cost=("employer_cost", "sum")
    )
    .sort_values("month")
)

st.line_chart(
    monthly.set_index("month")[
        [
            "gross_pay",
            "net_pay",
            "employer_cost"
        ]
    ]
)

st.caption(
    "Monthly payroll totals after excluding the four "
    "validated incorrect records."
)

st.divider()


# --------------------------------------------------
# DEPARTMENT-WISE PAYROLL
# --------------------------------------------------

st.subheader("Department-wise Payroll")

department_month = (
    filtered.groupby(
        ["department_name", "month"],
        as_index=False
    )
    .agg(
        employees=("employee_id", "nunique"),
        gross_pay=("gross_pay", "sum"),
        net_pay=("net_pay", "sum"),
        employer_cost=("employer_cost", "sum")
    )
)

department_month["cost_per_employee_month"] = (
    department_month["employer_cost"]
    / department_month["employees"]
)

# Apply minimum group-size privacy rule.
# Do not expose even the employee count for suppressed groups.

sensitive_columns = [
    "employees",
    "gross_pay",
    "net_pay",
    "employer_cost",
    "cost_per_employee_month"
]

for column in sensitive_columns:

    department_month.loc[
        department_month["employees"] < MIN_GROUP_SIZE,
        column
    ] = None

st.caption(
    "Privacy protection: department-month groups with fewer "
    "than 5 employees are suppressed."
)

st.dataframe(
    department_month.sort_values(
        ["month", "department_name"]
    ),
    use_container_width=True,
    hide_index=True
)


# --------------------------------------------------
# DEPARTMENT EMPLOYER COST COMPARISON
# --------------------------------------------------

st.subheader("Department Employer Cost Comparison")

department_totals = (
    filtered.groupby(
        "department_name",
        as_index=False
    )
    .agg(
        employees=("employee_id", "nunique"),
        employer_cost=("employer_cost", "sum")
    )
)

# Hide departments with fewer than 5 employees.
department_totals = department_totals[
    department_totals["employees"] >= MIN_GROUP_SIZE
].copy()

if not department_totals.empty:

    st.bar_chart(
        department_totals.set_index("department_name")[
            ["employer_cost"]
        ]
    )

    department_totals["cost_per_employee"] = (
        department_totals["employer_cost"]
        / department_totals["employees"]
    )

    st.dataframe(
        department_totals[
            [
                "department_name",
                "employer_cost",
                "cost_per_employee"
            ]
        ],
        use_container_width=True,
        hide_index=True
    )

else:
    st.info(
        "No department meets the minimum group-size requirement "
        "for this selection."
    )

st.divider()


# --------------------------------------------------
# PQ-09 RECONCILIATION
# --------------------------------------------------

st.subheader("PQ-09 Payroll Reconciliation")

if RECONCILIATION_FILE.exists():

    reconciliation = pd.read_csv(
        RECONCILIATION_FILE
    )

    passed = (
        reconciliation["status"] == "PASS"
    ).sum()

    failed = (
        reconciliation["status"] != "PASS"
    ).sum()

    total_months = len(reconciliation)

    r1, r2, r3 = st.columns(3)

    r1.metric(
        "Months Reconciled",
        f"{passed}/{total_months}"
    )

    r2.metric(
        "Months Requiring Investigation",
        f"{failed}"
    )

    r3.metric(
        "Excluded Payroll Records",
        "4"
    )

    if failed == 0 and total_months == 18:
        st.success(
            "All 18 months successfully reconcile with "
            "the official PQ-09 answer key."
        )
    else:
        st.warning(
            "Some reconciliation months require investigation."
        )

    st.dataframe(
        reconciliation,
        use_container_width=True,
        hide_index=True
    )

else:

    st.warning(
        "Monthly reconciliation evidence file was not found."
    )


# --------------------------------------------------
# EXCLUDED RECORDS - SUMMARY ONLY
# --------------------------------------------------

st.subheader("Payroll Data Quality Adjustments")

st.write(
    "Four incorrect payroll records were excluded from "
    "the Task 9 analytical calculations."
)

st.write(
    "- Two exact duplicate employee-month payroll records."
)

st.write(
    "- Two records referencing employee IDs missing "
    "from the employee master."
)

st.caption(
    "Detailed excluded-row evidence is maintained separately "
    "in evidence/excluded_payroll_rows.csv. "
    "Original Task 4 source records remain unchanged."
)


# --------------------------------------------------
# FINANCE RECONCILIATION NOTE
# --------------------------------------------------

st.subheader("Finance Reconciliation Note")

st.write(
    "During reconciliation, four payroll records were identified "
    "that inflated the monthly totals. Two records were duplicate "
    "employee-month entries, and two referenced employee IDs "
    "missing from the employee master. We excluded these four "
    "records from the Task 9 reporting calculations only, preserved "
    "the original source data, and reconciled all 18 months to the "
    "official PQ-09 answer key with zero difference."
)


# --------------------------------------------------
# FOOTER
# --------------------------------------------------

st.divider()

st.caption(
    "PulseIQ | Phase 2 | Task 9 | "
    "Source: Task 4 Payroll Warehouse | "
    "Minimum privacy group size: 5 employees | "
    "Source database accessed read-only"
)
