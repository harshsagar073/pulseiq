from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px

BASE = Path(__file__).resolve().parent
DATA = BASE / "evidence/department_month_comparison.csv"
DEPT_FILE = BASE / "data/source/dim_department.csv"

st.set_page_config(
    page_title="PulseIQ | Department Impact",
    page_icon="📊",
    layout="wide"
)

st.title("PulseIQ | Cross-Department Impact")
st.caption(
    "Department-month comparison of workforce cost, overtime, "
    "attendance, leave, attrition and productivity."
)

if not DATA.exists():
    st.error("Comparison dataset not found. Run the Task 13 build script first.")
    st.stop()

df = pd.read_csv(DATA)
df["month"] = pd.to_datetime(df["month"], errors="coerce")

if DEPT_FILE.exists():
    departments = pd.read_csv(DEPT_FILE)
    dept_name_col = next(
        (c for c in ["department_name", "dept_name", "name"] if c in departments.columns),
        None
    )
    if dept_name_col and "department_id" in departments.columns:
        df = df.merge(
            departments[["department_id", dept_name_col]].drop_duplicates(),
            on="department_id",
            how="left"
        )
        df["department_label"] = (
            df[dept_name_col].fillna(df["department_id"]).astype(str)
            + " (" + df["department_id"].astype(str) + ")"
        )
    else:
        df["department_label"] = df["department_id"].astype(str)
else:
    df["department_label"] = df["department_id"].astype(str)

numeric_cols = [
    "employer_cost", "gross_pay", "overtime_pay", "employees_paid",
    "late_arrivals", "attendance_rate_calculated", "headcount_end",
    "hires", "exits", "attrition_rate_monthly_pct",
    "approved_leave_days", "average_headcount",
    "leave_days_per_average_head", "cost_per_head_calculated",
    "overtime_share_pct_calculated", "overtime_cost_per_paid_employee",
    "tasks", "tasks_done", "story_points_done",
    "task_completion_rate_pct"
]
for col in numeric_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

min_month = df["month"].min()
max_month = df["month"].max()

st.sidebar.header("Filters")
selected_months = st.sidebar.date_input(
    "Month range",
    value=(min_month.date(), max_month.date()),
    min_value=min_month.date(),
    max_value=max_month.date()
)

if isinstance(selected_months, tuple) and len(selected_months) == 2:
    start_date, end_date = selected_months
    view = df[
        (df["month"].dt.date >= start_date)
        & (df["month"].dt.date <= end_date)
    ].copy()
else:
    view = df.copy()

dept_options = sorted(view["department_label"].dropna().unique().tolist())
selected_depts = st.sidebar.multiselect(
    "Departments",
    options=dept_options,
    default=dept_options
)
view = view[view["department_label"].isin(selected_depts)].copy()

if view.empty:
    st.warning("No rows match the selected filters.")
    st.stop()

st.caption(
    f"Showing {len(view):,} department-month records | "
    f"{view['department_id'].nunique()} departments"
)

# KPI summary
cost = view["employer_cost"].sum()
overtime = view["overtime_pay"].sum()
headcount = view["headcount_end"].mean()
attrition = view["attrition_rate_monthly_pct"].mean()
attendance = view["attendance_rate_calculated"].mean()

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Employer cost", f"₹{cost:,.0f}")
c2.metric("Overtime pay", f"₹{overtime:,.0f}")
c3.metric("Avg. month-end headcount", f"{headcount:,.1f}")
c4.metric("Avg. monthly attrition", f"{attrition:.2f}%")
c5.metric("Avg. attendance", f"{attendance * 100:.2f}%")

st.divider()

# Department comparison
st.subheader("Department comparison")
dept_summary = view.groupby("department_label", as_index=False).agg(
    employer_cost=("employer_cost", "sum"),
    overtime_pay=("overtime_pay", "sum"),
    average_attrition=("attrition_rate_monthly_pct", "mean"),
    average_attendance=("attendance_rate_calculated", "mean"),
    average_headcount=("headcount_end", "mean"),
    approved_leave_days=("approved_leave_days", "sum"),
    leave_days_per_average_head=("leave_days_per_average_head", "mean")
)

left, right = st.columns(2)
with left:
    fig = px.bar(
        dept_summary.sort_values("employer_cost", ascending=False),
        x="department_label", y="employer_cost",
        title="Employer cost by department",
        labels={"department_label": "Department", "employer_cost": "Employer cost (₹)"}
    )
    fig.update_layout(xaxis_tickangle=-35)
    st.plotly_chart(fig, use_container_width=True)

with right:
    fig = px.bar(
        dept_summary.sort_values("overtime_pay", ascending=False),
        x="department_label", y="overtime_pay",
        title="Overtime pay by department",
        labels={"department_label": "Department", "overtime_pay": "Overtime pay (₹)"}
    )
    fig.update_layout(xaxis_tickangle=-35)
    st.plotly_chart(fig, use_container_width=True)

left, right = st.columns(2)
with left:
    fig = px.bar(
        dept_summary.sort_values("average_attrition", ascending=False),
        x="department_label", y="average_attrition",
        title="Average monthly attrition by department",
        labels={"department_label": "Department", "average_attrition": "Attrition (%)"}
    )
    fig.update_layout(xaxis_tickangle=-35)
    st.plotly_chart(fig, use_container_width=True)

with right:
    fig = px.bar(
        dept_summary.sort_values("leave_days_per_average_head", ascending=False),
        x="department_label", y="leave_days_per_average_head",
        title="Approved leave days per average head",
        labels={
            "department_label": "Department",
            "leave_days_per_average_head": "Leave days per head"
        }
    )
    fig.update_layout(xaxis_tickangle=-35)
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# Monthly trend
st.subheader("Monthly workforce and cost trends")
monthly = view.groupby("month", as_index=False).agg(
    employer_cost=("employer_cost", "sum"),
    overtime_pay=("overtime_pay", "sum"),
    headcount_end=("headcount_end", "sum"),
    attrition_rate=("attrition_rate_monthly_pct", "mean"),
    attendance_rate=("attendance_rate_calculated", "mean")
)

trend_metric = st.selectbox(
    "Choose trend",
    ["employer_cost", "overtime_pay", "headcount_end",
     "attrition_rate", "attendance_rate"]
)
fig = px.line(
    monthly, x="month", y=trend_metric, markers=True,
    title=f"Monthly trend: {trend_metric.replace('_', ' ').title()}"
)
st.plotly_chart(fig, use_container_width=True)

# Productivity
st.subheader("Productivity comparison")
prod = dept_summary.merge(
    view.groupby("department_label", as_index=False).agg(
        tasks=("tasks", "sum"),
        tasks_done=("tasks_done", "sum"),
        story_points_done=("story_points_done", "sum")
    ),
    on="department_label",
    how="left"
)
prod["completion_rate_pct"] = (
    prod["tasks_done"] / prod["tasks"].replace(0, pd.NA) * 100
)
st.dataframe(
    prod[[
        "department_label", "tasks", "tasks_done",
        "story_points_done", "completion_rate_pct"
    ]].round(2),
    use_container_width=True,
    hide_index=True
)
st.caption(
    "Productivity is N/A for departments without a team mapping; "
    "N/A is not treated as zero."
)

# Detailed data
st.subheader("Department-month detail")
display_cols = [
    "department_id", "month", "employer_cost", "gross_pay",
    "overtime_pay", "employees_paid", "overtime_share_pct_calculated",
    "late_arrivals", "attendance_rate_calculated", "headcount_end",
    "hires", "exits", "attrition_rate_monthly_pct",
    "approved_leave_days", "leave_days_per_average_head",
    "tasks", "tasks_done", "story_points_done",
    "task_completion_rate_pct"
]
display_cols = [c for c in display_cols if c in view.columns]
st.dataframe(
    view[display_cols].sort_values(["month", "department_id"]).round(3),
    use_container_width=True,
    hide_index=True
)

csv = view[display_cols].to_csv(index=False).encode("utf-8")
st.download_button(
    "Download filtered department-month data",
    data=csv,
    file_name="task13_department_month_comparison.csv",
    mime="text/csv"
)

with st.expander("Methodology and reconciliation notes"):
    notes = BASE / "evidence/task13_methodology_and_findings.txt"
    if notes.exists():
        st.text(notes.read_text(encoding="utf-8"))
    st.write(
        "Department-level associations are descriptive. "
        "They do not establish that overtime, leave or cost caused attrition "
        "or productivity changes."
    )

st.caption("PulseIQ | Phase 3 — Task 13")
