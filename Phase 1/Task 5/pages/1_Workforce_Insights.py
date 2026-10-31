from pathlib import Path
import duckdb
import plotly.express as px
import streamlit as st

DB = Path(__file__).resolve().parents[1] / "pulseiq_task5.duckdb"

st.set_page_config(page_title="Workforce Insights | PulseIQ", layout="wide")
st.title("Workforce Insights")
st.caption("Explore department, location-tier, and work-mode distributions.")

if not DB.exists():
    st.error("Dashboard database not found. Run the Task 5 setup script.")
    st.stop()

with duckdb.connect(str(DB), read_only=True) as con:
    departments = con.execute(
        "SELECT * FROM governed.v_dashboard_department_mix ORDER BY employee_count DESC"
    ).fetchdf()
    locations = con.execute(
        "SELECT * FROM governed.v_dashboard_location_tier ORDER BY employee_count DESC"
    ).fetchdf()
    modes = con.execute(
        "SELECT * FROM governed.v_dashboard_work_mode ORDER BY employee_count DESC"
    ).fetchdf()

left, right = st.columns(2)

with left:
    st.subheader("Employees by department")
    if not departments.empty:
        fig = px.bar(departments, x="department_name", y="employee_count")
        st.plotly_chart(fig, use_container_width=True)
        top = departments.iloc[0]
        st.caption(
            f"**Insight:** {top['department_name']} has the largest current "
            f"count ({int(top['employee_count']):,} employees)."
        )
    else:
        st.info("No department data available.")

with right:
    st.subheader("Employees by location tier")
    if not locations.empty:
        fig = px.bar(locations, x="location_tier", y="employee_count")
        st.plotly_chart(fig, use_container_width=True)
        top = locations.iloc[0]
        st.caption(
            f"**Insight:** Tier {top['location_tier']} has "
            f"{int(top['employee_count']):,} employees."
        )
    else:
        st.info("No location data available.")

st.subheader("Employees by work mode")
if not modes.empty:
    fig = px.bar(modes, x="work_mode", y="employee_count")
    st.plotly_chart(fig, use_container_width=True)
    top = modes.iloc[0]
    st.caption(
        f"**Insight:** {top['work_mode']} is the most common recorded work mode, "
        f"with {int(top['employee_count']):,} employees."
    )
else:
    st.info("No work-mode data available.")
