from pathlib import Path
import json

import pandas as pd
import streamlit as st

# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------
st.set_page_config(
    page_title="PulseIQ | Executive Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

APP_DIR = Path(__file__).resolve().parent
DATA_FILE = APP_DIR / "data" / "company_kpis.csv"
META_FILE = APP_DIR / "data" / "metadata.json"

# --------------------------------------------------
# LOAD PUBLIC DATA
# --------------------------------------------------
@st.cache_data
def load_data():
    df = pd.read_csv(DATA_FILE, parse_dates=["month"])
    metadata = json.loads(META_FILE.read_text(encoding="utf-8"))
    return df, metadata


if not DATA_FILE.exists() or not META_FILE.exists():
    st.error("Published KPI data is missing. Please run the data export script.")
    st.stop()

df, metadata = load_data()

if df.empty:
    st.error("No published KPI data is available.")
    st.stop()

df = df.sort_values("month").reset_index(drop=True)

# --------------------------------------------------
# FORMATTING HELPERS
# --------------------------------------------------
def money_cr(value):
    if pd.isna(value):
        return "N/A"
    return f"₹{value / 10_000_000:.2f} Cr"


def percent(value):
    if pd.isna(value):
        return "N/A"
    return f"{value:.2f}%"


def number(value):
    if pd.isna(value):
        return "N/A"
    return f"{value:,.0f}"


def metric_value(row, column):
    return row[column] if column in row.index else None


# --------------------------------------------------
# HEADER
# --------------------------------------------------
st.title("📊 PulseIQ")
st.subheader("Executive Company Health Dashboard & Self-service KPI Explorer")

cutoff = metadata.get("reporting_cutoff", "Not available")
st.caption(
    f"Reporting cut-off: **{cutoff}**  |  "
    "Source: governed and privacy-protected aggregate data"
)

st.info(
    "This public demonstration provides company-level KPIs and approved, "
    "privacy-protected department and team aggregates. It does not publish "
    "employee-level records or personal identifiers."
)

# --------------------------------------------------
# SIDEBAR NAVIGATION AND FILTER
# --------------------------------------------------
st.sidebar.title("PulseIQ Navigation")

page = st.sidebar.radio(
    "Select dashboard section",
    ["Executive Overview", "Monthly Trends", "Data & Methodology", "Self-service KPI Explorer"],
)

available_months = df["month"].dropna().sort_values().tolist()

selected_month = st.sidebar.selectbox(
    "Select reporting month",
    options=available_months,
    index=len(available_months) - 1,
    format_func=lambda x: x.strftime("%B %Y"),
)

selected = df.loc[df["month"] == selected_month]

if selected.empty:
    st.error("No data available for the selected month.")
    st.stop()

row = selected.iloc[0]

st.sidebar.divider()
if page == "Self-service KPI Explorer":
    st.sidebar.caption("PulseIQ | Phase 4 | Task 18")
    st.sidebar.caption("Privacy-protected demo explorer")
else:
    st.sidebar.caption("PulseIQ | Phase 4 | Task 17")
    st.sidebar.caption("Public release candidate")

# --------------------------------------------------
# EXECUTIVE OVERVIEW
# --------------------------------------------------
if page == "Executive Overview":

    st.header("Executive Overview")
    st.write(
        f"Company performance for **{selected_month.strftime('%B %Y')}**."
    )

    # Row 1: Workforce and attendance
    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Headcount",
        number(metric_value(row, "headcount")),
    )
    c2.metric(
        "Monthly Attrition",
        percent(metric_value(row, "monthly_attrition_pct")),
        help="Company-level employee-weighted rate from governed metrics.",
    )
    c3.metric(
        "Attendance Rate",
        percent(metric_value(row, "attendance_rate_pct")),
        help="Employee-weighted average of visible governed department rates.",
    )
    c4.metric(
        "Payroll Cost",
        money_cr(metric_value(row, "payroll_cost_inr")),
    )

    st.divider()

    # Row 2: Financial performance
    c5, c6, c7 = st.columns(3)

    c5.metric(
        "Revenue",
        money_cr(metric_value(row, "revenue_inr")),
    )
    c6.metric(
        "Net Profit",
        money_cr(metric_value(row, "net_profit_inr")),
    )
    c7.metric(
        "Operating Margin",
        percent(metric_value(row, "operating_margin_pct")),
    )

    st.divider()
    st.subheader("KPI Target Comparison")

    target_columns = st.columns(3)

    attendance = metric_value(row, "attendance_rate_pct")
    attendance_target = metric_value(row, "attendance_target_pct")

    attrition = metric_value(row, "monthly_attrition_pct")
    attrition_target = metric_value(row, "attrition_target_pct")

    if pd.notna(attendance) and pd.notna(attendance_target):
        target_columns[0].metric(
            "Attendance Target",
            percent(attendance_target),
            delta=f"{attendance - attendance_target:+.2f} pp",
        )
    else:
        target_columns[0].metric("Attendance Target", "N/A")

    if pd.notna(attrition) and pd.notna(attrition_target):
        target_columns[1].metric(
            "Attrition Target",
            percent(attrition_target),
            delta=f"{attrition - attrition_target:+.2f} pp",
            delta_color="inverse",
        )
    else:
        target_columns[1].metric("Attrition Target", "N/A")

    task_completion = metadata.get("task_completion_pct")
    task_target = metric_value(row, "task_completion_target_pct")
    sprint = metadata.get("task_completion_sprint", "Not available")

    if task_completion is not None:
        delta = (
            task_completion - task_target
            if pd.notna(task_target) else None
        )
        target_columns[2].metric(
            f"Task Completion ({sprint})",
            percent(task_completion),
            delta=f"{delta:+.2f} pp" if delta is not None else None,
        )
    else:
        target_columns[2].metric("Task Completion", "N/A")

    st.caption(
        "Task completion is sprint-based, not monthly. "
        "It is displayed separately using the latest available sprint."
    )

    st.divider()
    st.subheader("Latest Available Reporting Period")

    latest_row = df.dropna(subset=["headcount"]).iloc[-1]
    st.write(
        f"Latest headcount record: **{latest_row['month'].strftime('%B %Y')}**"
    )
    st.write(f"Headcount: **{number(latest_row['headcount'])}**")

# --------------------------------------------------
# MONTHLY TRENDS
# --------------------------------------------------
elif page == "Monthly Trends":

    st.header("Monthly KPI Trends")
    st.write("Explore the historical company-level reporting data.")

    trend_options = {
        "Headcount": "headcount",
        "Monthly Attrition (%)": "monthly_attrition_pct",
        "Attendance Rate (%)": "attendance_rate_pct",
        "Payroll Cost (INR)": "payroll_cost_inr",
        "Revenue (INR)": "revenue_inr",
        "Net Profit (INR)": "net_profit_inr",
        "Operating Margin (%)": "operating_margin_pct",
    }

    selected_trend = st.selectbox(
        "Choose a KPI",
        list(trend_options.keys()),
    )

    column = trend_options[selected_trend]
    trend = df[["month", column]].dropna().copy()
    trend = trend.set_index("month")

    if trend.empty:
        st.warning("No historical data is available for this KPI.")
    else:
        st.line_chart(trend, height=380)
        st.caption(
            f"Showing {len(trend)} available monthly records. "
            "Missing periods are not treated as zero."
        )

    st.divider()
    st.subheader("Published Monthly Data")

    display_df = df.copy()
    display_df["month"] = display_df["month"].dt.strftime("%Y-%m")

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
    )

# --------------------------------------------------
# DATA AND METHODOLOGY
# --------------------------------------------------
elif page == "Data & Methodology":

    st.header("Data & Methodology")

    st.subheader("Publication Information")

    st.write(f"**Reporting cut-off:** {cutoff}")
    st.write(f"**Monthly records:** {metadata.get('monthly_rows', 'N/A')}")
    st.write(f"**Data source:** {metadata.get('data_source', 'N/A')}")
    st.write(f"**Latest task-completion sprint:** {sprint if 'sprint' in locals() else metadata.get('task_completion_sprint', 'N/A')}")

    st.subheader("Metric Definitions")

    definitions = [
        ("Headcount", "Company-level headcount from governed monthly headcount metrics."),
        ("Monthly Attrition", "Employee-weighted average of visible governed department attrition rates."),
        ("Payroll Cost", "Sum of visible governed monthly payroll cost values."),
        ("Attendance Rate", "Employee-weighted average of visible governed attendance rates."),
        ("Revenue", "Sum of visible governed revenue values."),
        ("Net Profit", "Company-level governed net profit metric."),
        ("Operating Margin", "Company-level governed operating margin metric."),
        ("Task Completion", "Employee-weighted completion rate for the latest available sprint."),
    ]

    st.table(
        pd.DataFrame(definitions, columns=["KPI", "Methodology"])
    )

    st.subheader("Privacy and Suppression")

    st.write(
        "- Only company-level aggregate values are published.\n"
        "- Suppressed governed records are excluded from calculations.\n"
        "- Employee identifiers and employee-level records are not published.\n"
        "- Department, team and client identifiers are not published.\n"
        "- The original DuckDB warehouse is not included in this public app."
    )

    st.subheader("Data Freshness")

    st.warning(
        "This is a point-in-time published snapshot. A scheduled workflow "
        "can validate and publish updated data only after an approved, "
        "updated source database becomes available."
    )

    st.write(metadata.get("refresh_note", ""))

# --------------------------------------------------
# TASK 18: SELF-SERVICE KPI EXPLORER
# --------------------------------------------------
else:
    import importlib.util

    explorer_file = (
        Path(__file__).resolve().parents[1] / "Task 18" / "explorer_page.py"
    )
    spec = importlib.util.spec_from_file_location(
        "pulseiq_task18_explorer", explorer_file
    )
    explorer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(explorer)

# --------------------------------------------------
# FOOTER
# --------------------------------------------------
st.divider()
if page == "Self-service KPI Explorer":
    st.caption("PulseIQ | Data Analytics | Phase 4 Task 18 | Self-service KPI Explorer")
else:
    st.caption("PulseIQ | Data Analytics | Phase 4 Task 17 | Public company-level reporting")
