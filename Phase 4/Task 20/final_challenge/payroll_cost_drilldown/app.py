from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st

# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------
ROOT = Path(__file__).resolve().parents[4]
DB_PATH = ROOT / "Phase 1" / "Task 4" / "pulseiq_task4.duckdb"

EXCLUDED_IDS = ["PI-X0001", "PI-X0002", "PI-X0003", "PI-X0004"]
MIN_GROUP_SIZE = 5

st.set_page_config(
    page_title="PulseIQ | Payroll Cost Drill-down",
    page_icon="📊",
    layout="wide"
)

st.title("PulseIQ — Payroll Cost Drill-down")
st.caption(
    "Management analysis | Department contribution, monthly movement "
    "and payroll cost composition"
)

# ---------------------------------------------------------
# DATA LOADING — READ ONLY
# ---------------------------------------------------------
@st.cache_data
def load_payroll(db_path, excluded_ids):
    con = duckdb.connect(db_path, read_only=True)

    query = """
        SELECT
            p.payroll_item_id,
            p.employee_id,
            p.period_end_date,
            p.department_id,
            d.department_name,
            p.gross_pay,
            p.net_pay,
            p.employer_cost,
            p.overtime_pay,
            p.variable_pay,
            p.overtime_hours_paid
        FROM raw.fact_payroll p
        LEFT JOIN raw.dim_department d
            ON p.department_id = d.department_id
        WHERE p.payroll_item_id NOT IN (?, ?, ?, ?)
    """

    df = con.execute(query, excluded_ids).fetchdf()
    con.close()

    df["period_end_date"] = pd.to_datetime(df["period_end_date"])
    df["month"] = df["period_end_date"].dt.strftime("%Y-%m")

    numeric_cols = [
        "gross_pay", "net_pay", "employer_cost",
        "overtime_pay", "variable_pay", "overtime_hours_paid"
    ]

    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["department_name"] = df["department_name"].fillna("Unmapped Department")
    return df


if not DB_PATH.exists():
    st.error(f"Database not found: {DB_PATH}")
    st.stop()

try:
    payroll = load_payroll(str(DB_PATH), EXCLUDED_IDS)
except Exception as exc:
    st.error(f"Could not load payroll data: {exc}")
    st.stop()

if payroll.empty:
    st.warning("No payroll records are available after applying exclusions.")
    st.stop()

# ---------------------------------------------------------
# SIDEBAR FILTERS
# ---------------------------------------------------------
st.sidebar.header("Analysis Filters")

months = sorted(payroll["month"].dropna().unique().tolist())

selected_month = st.sidebar.selectbox(
    "Select reporting month",
    months,
    index=len(months) - 1
)

departments = sorted(payroll["department_name"].unique().tolist())

selected_department = st.sidebar.selectbox(
    "Department for drill-down",
    ["All Departments"] + departments
)

st.sidebar.caption(
    "Source: Task 4 Payroll Warehouse. "
    "Four Task 9 excluded records remain excluded."
)

current = payroll[payroll["month"] == selected_month].copy()

month_position = months.index(selected_month)
previous_month = months[month_position - 1] if month_position > 0 else None

if previous_month:
    previous = payroll[payroll["month"] == previous_month].copy()
else:
    previous = payroll.iloc[0:0].copy()

# ---------------------------------------------------------
# COMPANY-LEVEL KPI SUMMARY
# ---------------------------------------------------------
st.subheader(f"Company Payroll Snapshot — {selected_month}")

total_employees = current["employee_id"].nunique()
gross_total = current["gross_pay"].sum()
net_total = current["net_pay"].sum()
employer_total = current["employer_cost"].sum()

avg_cost = employer_total / total_employees if total_employees else 0

if previous_month:
    previous_cost = previous["employer_cost"].sum()
    cost_change = employer_total - previous_cost
    pct_change = (
        cost_change / previous_cost * 100
        if previous_cost else None
    )
else:
    previous_cost = None
    cost_change = None
    pct_change = None

c1, c2, c3, c4 = st.columns(4)

c1.metric("Employees Paid", f"{total_employees:,}")
c2.metric("Gross Pay", f"₹{gross_total:,.0f}")
c3.metric("Net Pay", f"₹{net_total:,.0f}")
c4.metric("Employer Cost", f"₹{employer_total:,.0f}")

c5, c6 = st.columns(2)
c5.metric("Average Employer Cost / Employee", f"₹{avg_cost:,.0f}")

if pct_change is not None:
    c6.metric(
        f"Employer Cost Change vs {previous_month}",
        f"₹{cost_change:,.0f}",
        f"{pct_change:+.2f}%"
    )
else:
    c6.metric("Month-on-Month Change", "Not available")

st.divider()

# ---------------------------------------------------------
# MONTHLY PAYROLL TREND
# ---------------------------------------------------------
st.subheader("Monthly Payroll Cost Trend")

monthly = (
    payroll.groupby("month", as_index=False)
    .agg(
        employees=("employee_id", "nunique"),
        gross_pay=("gross_pay", "sum"),
        net_pay=("net_pay", "sum"),
        employer_cost=("employer_cost", "sum")
    )
    .sort_values("month")
)

st.line_chart(
    monthly.set_index("month")[["employer_cost", "gross_pay", "net_pay"]]
)

trend_view = monthly.copy()
trend_view["employer_cost_change"] = trend_view["employer_cost"].diff()
trend_view["employer_cost_change_pct"] = (
    trend_view["employer_cost"].pct_change() * 100
)

st.dataframe(
    trend_view,
    use_container_width=True,
    hide_index=True
)

st.divider()

# ---------------------------------------------------------
# DEPARTMENT CONTRIBUTION
# ---------------------------------------------------------
st.subheader(f"Department Contribution — {selected_month}")

department_month = (
    current.groupby("department_name", as_index=False)
    .agg(
        employees=("employee_id", "nunique"),
        gross_pay=("gross_pay", "sum"),
        net_pay=("net_pay", "sum"),
        employer_cost=("employer_cost", "sum"),
        overtime_pay=("overtime_pay", "sum"),
        variable_pay=("variable_pay", "sum")
    )
)

department_month["cost_per_employee"] = (
    department_month["employer_cost"] /
    department_month["employees"].replace(0, pd.NA)
)

# Suppress groups below the established Task 9 threshold.
eligible = department_month[
    department_month["employees"] >= MIN_GROUP_SIZE
].copy()

suppressed_count = len(department_month) - len(eligible)

if not eligible.empty:
    chart_data = eligible.sort_values("employer_cost", ascending=False)

    st.bar_chart(
        chart_data.set_index("department_name")[["employer_cost"]]
    )

    st.caption(
        f"Department groups below {MIN_GROUP_SIZE} employees are suppressed. "
        f"Suppressed groups in this month: {suppressed_count}."
    )

    st.dataframe(
        chart_data[
            [
                "department_name", "employees", "gross_pay", "net_pay",
                "employer_cost", "overtime_pay", "variable_pay",
                "cost_per_employee"
            ]
        ],
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("No department meets the minimum group-size privacy threshold.")

st.divider()

# ---------------------------------------------------------
# DEPARTMENT MONTH-ON-MONTH CHANGE
# ---------------------------------------------------------
st.subheader("Which Departments Drove the Change?")

if previous_month:
    previous_dept = (
        previous.groupby("department_name", as_index=False)
        .agg(
            previous_employees=("employee_id", "nunique"),
            previous_employer_cost=("employer_cost", "sum")
        )
    )

    current_dept = (
        current.groupby("department_name", as_index=False)
        .agg(
            current_employees=("employee_id", "nunique"),
            current_employer_cost=("employer_cost", "sum")
        )
    )

    comparison = current_dept.merge(
        previous_dept,
        on="department_name",
        how="outer"
    ).fillna(0)

    comparison["cost_change"] = (
        comparison["current_employer_cost"] -
        comparison["previous_employer_cost"]
    )

    comparison["cost_change_pct"] = comparison.apply(
        lambda row: (
            row["cost_change"] / row["previous_employer_cost"] * 100
            if row["previous_employer_cost"] else None
        ),
        axis=1
    )

    # Apply privacy rule to both months before displaying a comparison.
    comparison = comparison[
        (comparison["current_employees"] >= MIN_GROUP_SIZE) &
        (comparison["previous_employees"] >= MIN_GROUP_SIZE)
    ].copy()

    comparison = comparison.sort_values("cost_change", ascending=False)

    if not comparison.empty:
        st.caption(
            f"Comparison: {previous_month} versus {selected_month}. "
            "Only departments meeting the privacy threshold in both months are shown."
        )

        st.bar_chart(
            comparison.set_index("department_name")[["cost_change"]]
        )

        st.dataframe(
            comparison,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No department meets the privacy threshold in both months.")
else:
    st.info("A previous month is not available for comparison.")

st.divider()

# ---------------------------------------------------------
# SELECTED DEPARTMENT DRILL-DOWN
# ---------------------------------------------------------
st.subheader("Department Cost Breakdown")

if selected_department == "All Departments":
    detail = current.copy()
    st.caption("Showing all eligible department groups.")
else:
    detail = current[
        current["department_name"] == selected_department
    ].copy()

detail_employee_count = detail["employee_id"].nunique()

if detail_employee_count < MIN_GROUP_SIZE:
    st.warning(
        "This department has fewer than five employees in the selected month. "
        "Its detailed figures are suppressed under the privacy rule."
    )
else:
    d1, d2, d3, d4 = st.columns(4)

    d1.metric("Employees", f"{detail_employee_count:,}")
    d2.metric("Gross Pay", f"₹{detail['gross_pay'].sum():,.0f}")
    d3.metric("Net Pay", f"₹{detail['net_pay'].sum():,.0f}")
    d4.metric("Employer Cost", f"₹{detail['employer_cost'].sum():,.0f}")

    components = pd.DataFrame({
        "Pay Component": [
            "Gross Pay", "Overtime Pay", "Variable Pay",
            "Employer Cost", "Net Pay"
        ],
        "Amount": [
            detail["gross_pay"].sum(),
            detail["overtime_pay"].sum(),
            detail["variable_pay"].sum(),
            detail["employer_cost"].sum(),
            detail["net_pay"].sum()
        ]
    })

    st.bar_chart(components.set_index("Pay Component"))

    st.dataframe(
        components,
        use_container_width=True,
        hide_index=True
    )

st.divider()

# ---------------------------------------------------------
# DATA QUALITY AND INTERPRETATION
# ---------------------------------------------------------
st.subheader("Data Quality & Interpretation")

q1, q2, q3 = st.columns(3)
q1.metric("Included Payroll Records", f"{len(payroll):,}")
q2.metric("Excluded Payroll IDs", "4")
q3.metric("Privacy Threshold", f"{MIN_GROUP_SIZE} employees")

st.info(
    "Interpretation: employer cost movement identifies where payroll cost "
    "changed. It does not by itself prove the cause. Employee mix, headcount, "
    "overtime, variable pay and pay changes should be investigated before "
    "management concludes why costs increased."
)

st.caption(
    "PulseIQ | Phase 4 | Task 20 Final Challenge | "
    "Payroll source: Task 4 DuckDB | Read-only connection | "
    "Task 9 exclusions and minimum group-size rule preserved."
)
