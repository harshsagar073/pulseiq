from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px
import duckdb

st.set_page_config(
    page_title="PulseIQ | Attendance & Leave",
    page_icon="📊",
    layout="wide"
)

DATA_DIR = Path(__file__).resolve().parents[2] / "Phase 1" / "Task 1" / "validated"

st.title("PulseIQ | Attendance & Leave Dashboard")
st.caption("Monthly workforce attendance, punctuality, overtime and approved leave trends.")

@st.cache_data
def load_data():
    attendance = pd.read_csv(DATA_DIR / "fact_attendance_monthly.csv")
    leave = pd.read_csv(DATA_DIR / "fact_leave.csv")
    calendar = pd.read_csv(DATA_DIR / "dim_date.csv")

    attendance["period_end_date"] = pd.to_datetime(
        attendance["period_end_date"], errors="coerce"
    )
    leave["start_date"] = pd.to_datetime(leave["start_date"], errors="coerce")
    calendar["date"] = pd.to_datetime(calendar["date"], errors="coerce")

    for col in ["scheduled_days", "present_days", "late_arrivals", "overtime_hours"]:
        attendance[col] = pd.to_numeric(attendance[col], errors="coerce").fillna(0)

    leave["days"] = pd.to_numeric(leave["days"], errors="coerce").fillna(0)
    return attendance, leave, calendar

try:
    attendance, leave, calendar = load_data()
except Exception as e:
    st.error(f"Data load nahi ho paaya: {e}")
    st.stop()

if "department_id" not in attendance.columns:
    st.error("Attendance file mein department_id column nahi mila.")
    st.stop()

departments = sorted(attendance["department_id"].dropna().astype(str).unique())
selected = st.sidebar.multiselect(
    "Department filter",
    departments,
    default=departments
)

df = attendance[attendance["department_id"].astype(str).isin(selected)].copy()

if df.empty:
    st.warning("Selected departments ke liye data nahi hai.")
    st.stop()

df["month"] = df["period_end_date"].dt.to_period("M").astype(str)
monthly = df.groupby("month", as_index=False).agg(
    scheduled_days=("scheduled_days", "sum"),
    present_days=("present_days", "sum"),
    late_arrivals=("late_arrivals", "sum"),
    overtime_hours=("overtime_hours", "sum"),
    employees=("employee_id", "nunique")
)
monthly["attendance_rate"] = (
    monthly["present_days"] / monthly["scheduled_days"].replace(0, pd.NA) * 100
).fillna(0)
monthly["month_date"] = pd.to_datetime(monthly["month"] + "-01")

total_scheduled = df["scheduled_days"].sum()
total_present = df["present_days"].sum()
overall_rate = total_present / total_scheduled * 100 if total_scheduled else 0
total_late = int(df["late_arrivals"].sum())
total_overtime = df["overtime_hours"].sum()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Attendance rate", f"{overall_rate:.1f}%")
c2.metric("Present days", f"{total_present:,.0f}")
c3.metric("Late arrivals", f"{total_late:,}")
c4.metric("Overtime hours", f"{total_overtime:,.1f}")

st.divider()

st.subheader("1. Monthly attendance rate")
st.caption("Takeaway: Compare monthly attendance against the overall trend. Rate = total present days ÷ total scheduled days.")
fig = px.line(
    monthly, x="month_date", y="attendance_rate", markers=True,
    labels={"month_date": "Month", "attendance_rate": "Attendance rate (%)"},
    title="Monthly attendance rate"
)
fig.update_yaxes(ticksuffix="%")
st.plotly_chart(fig, use_container_width=True)

left, right = st.columns(2)

with left:
    st.subheader("2. Attendance by department")
    st.caption("Takeaway: Identify departments with comparatively higher or lower attendance.")
    dept = df.groupby("department_id", as_index=False).agg(
        scheduled_days=("scheduled_days", "sum"),
        present_days=("present_days", "sum")
    )
    dept["attendance_rate"] = (
        dept["present_days"] / dept["scheduled_days"].replace(0, pd.NA) * 100
    ).fillna(0)
    fig = px.bar(
        dept.sort_values("attendance_rate"),
        x="attendance_rate", y="department_id", orientation="h",
        labels={"attendance_rate": "Attendance rate (%)", "department_id": "Department"},
        title="Attendance rate by department"
    )
    fig.update_xaxes(ticksuffix="%")
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("3. Monthly late arrivals")
    st.caption("Takeaway: Peaks indicate months to investigate; the chart alone does not establish the cause.")
    fig = px.bar(
        monthly, x="month_date", y="late_arrivals",
        labels={"month_date": "Month", "late_arrivals": "Late arrivals"},
        title="Late arrivals by month"
    )
    st.plotly_chart(fig, use_container_width=True)

left, right = st.columns(2)

with left:
    st.subheader("4. Monthly overtime hours")
    st.caption("Takeaway: Review unusually high overtime months with operational context.")
    fig = px.line(
        monthly, x="month_date", y="overtime_hours", markers=True,
        labels={"month_date": "Month", "overtime_hours": "Overtime hours"},
        title="Overtime hours by month"
    )
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("5. Approved leave by type")
    st.caption("Takeaway: Only approved requests are counted; leave is grouped by request start month.")
    approved = leave[leave["status"].astype(str).str.lower().eq("approved")].copy()
    if not approved.empty:
        leave_type = approved.groupby("leave_type_code", as_index=False)["days"].sum()
        fig = px.bar(
            leave_type.sort_values("days"),
            x="days", y="leave_type_code", orientation="h",
            labels={"days": "Approved leave days", "leave_type_code": "Leave type"},
            title="Approved leave days by type"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Approved leave records nahi mile.")

st.subheader("5A. Monthly approved leave trends")
st.caption(
    "Approved leave requests and leave days are grouped by request start month."
)

approved_monthly = leave[
    leave["status"].astype(str).str.strip().str.lower().eq("approved")
].copy()

if not approved_monthly.empty:
    approved_monthly["leave_month"] = (
        approved_monthly["start_date"].dt.to_period("M").astype(str)
    )

    leave_monthly = approved_monthly.groupby(
        "leave_month", as_index=False
    ).agg(
        approved_requests=("leave_request_id", "nunique"),
        approved_leave_days=("days", "sum")
    )

    leave_monthly["month_date"] = pd.to_datetime(
        leave_monthly["leave_month"] + "-01",
        errors="coerce"
    )

    left, right = st.columns(2)

    with left:
        fig = px.bar(
            leave_monthly,
            x="month_date",
            y="approved_requests",
            title="Approved leave requests by month",
            labels={
                "month_date": "Month",
                "approved_requests": "Approved requests"
            }
        )
        st.plotly_chart(fig, use_container_width=True)

    with right:
        fig = px.line(
            leave_monthly,
            x="month_date",
            y="approved_leave_days",
            markers=True,
            title="Approved leave days by month",
            labels={
                "month_date": "Month",
                "approved_leave_days": "Approved leave days"
            }
        )
        st.plotly_chart(fig, use_container_width=True)

    st.dataframe(
        leave_monthly[
            ["leave_month", "approved_requests", "approved_leave_days"]
        ].rename(columns={
            "leave_month": "Month",
            "approved_requests": "Approved requests",
            "approved_leave_days": "Approved leave days"
        }),
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("Approved leave records nahi mile.")


st.subheader("6. Holiday and long-weekend context")

st.caption("Calendar context only: monthly attendance data cannot prove that holidays caused a change in attendance.")
if {"date", "is_holiday", "is_weekend"}.issubset(calendar.columns):
    cal = calendar.copy()
    cal["month"] = cal["date"].dt.to_period("M").astype(str)
    holiday_months = cal.groupby("month", as_index=False).agg(
        holiday_days=("is_holiday", lambda s: s.astype(str).str.upper().isin(["Y", "YES", "TRUE", "1"]).sum()),
        weekend_days=("is_weekend", lambda s: s.astype(str).str.upper().isin(["Y", "YES", "TRUE", "1"]).sum())
    )
    context = monthly.merge(holiday_months, on="month", how="left").fillna(0)
    fig = px.bar(
        context, x="month_date", y=["holiday_days", "weekend_days"],
        barmode="group", labels={"month_date": "Month", "value": "Calendar days", "variable": "Day type"},
        title="Holidays and weekends by month"
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Calendar file mein holiday/weekend flags nahi mile.")

st.subheader("7. Three unusual months to investigate")
st.caption("Months are flagged by the largest absolute difference from the median monthly attendance rate. These are investigation leads, not proven causes.")
if len(monthly):
    median_rate = monthly["attendance_rate"].median()
    unusual = monthly.copy()
    unusual["difference_from_median_pp"] = unusual["attendance_rate"] - median_rate
    unusual["absolute_difference_pp"] = unusual["difference_from_median_pp"].abs()
    unusual = unusual.nlargest(min(3, len(unusual)), "absolute_difference_pp")
    unusual = unusual[[
        "month", "attendance_rate", "difference_from_median_pp",
        "late_arrivals", "overtime_hours"
    ]].sort_values("month")
    st.dataframe(
        unusual.rename(columns={
            "month": "Month",
            "attendance_rate": "Attendance rate (%)",
            "difference_from_median_pp": "Difference vs median (pp)",
            "late_arrivals": "Late arrivals",
            "overtime_hours": "Overtime hours"
        }),
        use_container_width=True,
        hide_index=True
    )

st.subheader("Three numeric insights")
if len(monthly):
    highest = monthly.loc[monthly["attendance_rate"].idxmax()]
    lowest = monthly.loc[monthly["attendance_rate"].idxmin()]
    late_peak = monthly.loc[monthly["late_arrivals"].idxmax()]
    st.write(
        f"1. Highest monthly attendance was **{highest['attendance_rate']:.1f}%** "
        f"in **{highest['month']}**."
    )
    st.write(
        f"2. Lowest monthly attendance was **{lowest['attendance_rate']:.1f}%** "
        f"in **{lowest['month']}**."
    )
    st.write(
        f"3. Highest late-arrival count was **{int(late_peak['late_arrivals']):,}** "
        f"in **{late_peak['month']}**."
    )

st.subheader("Monthly detail")
st.dataframe(
    monthly[[
        "month", "employees", "scheduled_days", "present_days",
        "attendance_rate", "late_arrivals", "overtime_hours"
    ]].rename(columns={
        "month": "Month",
        "employees": "Employees",
        "scheduled_days": "Scheduled days",
        "present_days": "Present days",
        "attendance_rate": "Attendance rate (%)",
        "late_arrivals": "Late arrivals",
        "overtime_hours": "Overtime hours"
    }),
    use_container_width=True,
    hide_index=True
)

st.download_button(
    "Download monthly summary CSV",
    monthly.to_csv(index=False).encode("utf-8"),
    file_name="task6_monthly_attendance_summary.csv",
    mime="text/csv"
)

st.caption(
    "Definitions: Attendance rate = summed present days / summed scheduled days. "
    "Approved leave days are grouped by request start month, not spread across every leave date. "
    "Holiday context is calendar-only and does not establish causation."
)
