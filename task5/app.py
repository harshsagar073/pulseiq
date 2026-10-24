from pathlib import Path
import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st

DB = Path(__file__).resolve().parent / "pulseiq_task5.duckdb"

st.set_page_config(
    page_title="PulseIQ | Workforce",
    page_icon="📊",
    layout="wide",
)

st.title("PulseIQ | Workforce & Headcount")
st.caption("A governed view of workforce size, department mix, and work locations.")

if not DB.exists():
    st.error(f"Dashboard database not found: {DB}")
    st.stop()

@st.cache_data(ttl=60)
def read_view(view_name):
    # App queries are restricted to governed dashboard views.
    allowed = {
        "v_dashboard_headcount",
        "v_dashboard_hires",
        "v_dashboard_exits",
        "v_dashboard_current_employee",
        "v_dashboard_department_mix",
        "v_dashboard_location_tier",
        "v_dashboard_work_mode",
    }
    if view_name not in allowed:
        raise ValueError("View is not approved for dashboard use.")
    with duckdb.connect(str(DB), read_only=True) as con:
        return con.execute(
            f"SELECT * FROM governed.{view_name}"
        ).fetchdf()

try:
    headcount = read_view("v_dashboard_headcount")
    hires = read_view("v_dashboard_hires")
    exits = read_view("v_dashboard_exits")
    employees = read_view("v_dashboard_current_employee")
    departments = read_view("v_dashboard_department_mix")
    locations = read_view("v_dashboard_location_tier")
    work_modes = read_view("v_dashboard_work_mode")
except Exception as exc:
    st.error("Dashboard views are not ready yet.")
    st.code(str(exc))
    st.info("Run: python task5/scripts/setup_database.py")
    st.stop()

if headcount.empty:
    st.warning("No headcount records were returned by the governed metric view.")
    st.stop()

headcount["month_start_date"] = pd.to_datetime(headcount["month_start_date"])
min_date = headcount["month_start_date"].min().date()
max_date = headcount["month_start_date"].max().date()

st.sidebar.header("Dashboard filters")
dept_options = sorted(headcount["department_name"].dropna().astype(str).unique())
selected_depts = st.sidebar.multiselect(
    "Department",
    options=dept_options,
    default=dept_options,
)
date_range = st.sidebar.date_input(
    "Date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)

if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date = end_date = date_range

filtered = headcount[
    (headcount["month_start_date"].dt.date >= start_date)
    & (headcount["month_start_date"].dt.date <= end_date)
]
if selected_depts:
    filtered = filtered[filtered["department_name"].astype(str).isin(selected_depts)]
else:
    filtered = filtered.iloc[0:0]

if filtered.empty:
    st.warning("No headcount data matches these filters. Select another department or date range.")
    st.stop()

monthly = (
    filtered.groupby("month_start_date", as_index=False)["headcount"]
    .sum()
    .sort_values("month_start_date")
)
latest_month = monthly["month_start_date"].max()
latest_headcount = float(monthly.loc[monthly["month_start_date"] == latest_month, "headcount"].sum())

period_hires = hires[
    (pd.to_datetime(hires["month_start_date"]).dt.date >= start_date)
    & (pd.to_datetime(hires["month_start_date"]).dt.date <= end_date)
]
period_exits = exits[
    (pd.to_datetime(exits["month_start_date"]).dt.date >= start_date)
    & (pd.to_datetime(exits["month_start_date"]).dt.date <= end_date)
]
if selected_depts:
    selected_ids = filtered["department_id"].astype(str).unique().tolist()
    period_hires = period_hires[period_hires["department_id"].astype(str).isin(selected_ids)]
    period_exits = period_exits[period_exits["department_id"].astype(str).isin(selected_ids)]

total_hires = float(period_hires["metric_value"].sum()) if not period_hires.empty else 0
total_exits = float(period_exits["metric_value"].sum()) if not period_exits.empty else 0
active_count = int(employees["employee_id"].nunique()) if not employees.empty else 0

k1, k2, k3, k4 = st.columns(4)
k1.metric("Latest headcount", f"{latest_headcount:,.0f}", help=f"Latest available month: {latest_month:%b %Y}")
k2.metric("Hires in period", f"{total_hires:,.0f}")
k3.metric("Exits in period", f"{total_exits:,.0f}")
k4.metric("Current employee records", f"{active_count:,.0f}")

st.divider()
left, right = st.columns([1.6, 1])

with left:
    st.subheader("Headcount trend")
    trend = px.line(
        monthly,
        x="month_start_date",
        y="headcount",
        markers=True,
        labels={"month_start_date": "Month", "headcount": "Headcount"},
    )
    trend.update_layout(showlegend=False, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(trend, use_container_width=True)
    if len(monthly) >= 2:
        first = float(monthly.iloc[0]["headcount"])
        last = float(monthly.iloc[-1]["headcount"])
        change = last - first
        direction = "increased" if change > 0 else "decreased" if change < 0 else "was unchanged"
        st.caption(
            f"**Insight:** Headcount {direction} by {abs(change):,.0f} "
            f"from {first:,.0f} to {last:,.0f} over the selected period."
        )
    else:
        st.caption("**Insight:** Only one monthly observation is available for this selection.")

with right:
    st.subheader("Department mix")
    mix = departments.copy()
    if selected_depts:
        mix = mix[mix["department_name"].astype(str).isin(selected_depts)]
    mix = mix.sort_values("employee_count", ascending=False)
    if not mix.empty:
        fig = px.bar(
            mix,
            x="employee_count",
            y="department_name",
            orientation="h",
            labels={"employee_count": "Employees", "department_name": "Department"},
        )
        fig.update_layout(
            yaxis={"categoryorder": "total ascending"},
            showlegend=False,
            margin=dict(l=10, r=10, t=10, b=10),
        )
        st.plotly_chart(fig, use_container_width=True)
        largest = mix.sort_values("employee_count", ascending=False).iloc[0]
        st.caption(
            f"**Insight:** {largest['department_name']} is the largest displayed "
            f"department with {int(largest['employee_count']):,} employees."
        )
    else:
        st.info("No department mix records are available.")

st.divider()
left, right = st.columns(2)

with left:
    st.subheader("Employees by location tier")
    if not locations.empty:
        loc = locations.sort_values("employee_count", ascending=False)
        fig = px.bar(
            loc,
            x="location_tier",
            y="employee_count",
            labels={"location_tier": "Location tier", "employee_count": "Employees"},
        )
        fig.update_layout(showlegend=False, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)
        largest = loc.iloc[0]
        st.caption(
            f"**Insight:** Location tier {largest['location_tier']} has "
            f"{int(largest['employee_count']):,} employees in the current employee view."
        )
    else:
        st.info("No location-tier data is available.")

with right:
    st.subheader("Employees by work mode")
    if not work_modes.empty:
        modes = work_modes.sort_values("employee_count", ascending=False)
        fig = px.bar(
            modes,
            x="work_mode",
            y="employee_count",
            labels={"work_mode": "Work mode", "employee_count": "Employees"},
        )
        fig.update_layout(showlegend=False, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)
        largest = modes.iloc[0]
        st.caption(
            f"**Insight:** {largest['work_mode']} is the most common work mode, "
            f"with {int(largest['employee_count']):,} employees."
        )
    else:
        st.info("No work-mode data is available.")

st.caption(
    "Data source: governed PulseIQ metric and dashboard views. "
    "Counts reflect the available data and selected filters."
)
