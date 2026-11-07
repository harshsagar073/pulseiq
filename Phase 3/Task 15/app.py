
from pathlib import Path
import calendar
import duckdb
import pandas as pd
import streamlit as st

# ============================================================
# PULSEIQ | PHASE 3 | TASK 15
# Executive Company Health Scorecard
# Actual KPI values come only from governed metric views.
# Targets come from raw.kpi_targets.
# ============================================================

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "Phase 1" / "Task 4" / "pulseiq_task4.duckdb"

st.set_page_config(
    page_title="PulseIQ | Executive Health Scorecard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    .stApp {
        background: #0b1220;
        color: #e8eef9;
    }
    [data-testid="stHeader"] {
        background: transparent;
    }
    [data-testid="stSidebar"] {
        background: #111a2e;
    }
    .main-title {
        font-size: 34px;
        font-weight: 800;
        color: #f4f7ff;
        letter-spacing: -1px;
        margin-bottom: 2px;
    }
    .sub-title {
        color: #91a1ba;
        font-size: 14px;
        margin-bottom: 20px;
    }
    .kpi-card {
        background: linear-gradient(145deg, #17243a, #111c30);
        border: 1px solid #293b56;
        border-radius: 15px;
        padding: 19px;
        min-height: 175px;
        margin-bottom: 12px;
    }
    .kpi-name {
        color: #aab9d0;
        font-size: 13px;
        font-weight: 650;
        text-transform: uppercase;
        letter-spacing: .6px;
    }
    .kpi-value {
        color: #ffffff;
        font-size: 27px;
        font-weight: 800;
        margin-top: 12px;
        margin-bottom: 5px;
    }
    .kpi-target {
        color: #9fb0c8;
        font-size: 12px;
    }
    .kpi-trend {
        color: #d0dcf0;
        font-size: 12px;
        margin-top: 10px;
    }
    .status {
        display: inline-block;
        border-radius: 20px;
        padding: 5px 10px;
        font-size: 10px;
        font-weight: 800;
        letter-spacing: .6px;
        margin-top: 10px;
    }
    .green { background: #123c32; color: #65e6b8; }
    .red { background: #48232b; color: #ff9ba7; }
    .amber { background: #49391b; color: #ffd27a; }
    .grey { background: #28364a; color: #c1cee0; }
    .section-title {
        font-size: 21px;
        color: #f1f5fc;
        font-weight: 750;
        margin-top: 25px;
    }
    .detail-card {
        background: #111c30;
        border: 1px solid #293b56;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 10px;
    }
    .detail-label {
        color: #9fb0c8;
        font-size: 12px;
    }
    .detail-value {
        color: #f4f7ff;
        font-size: 18px;
        font-weight: 750;
    }
    a { color: #80b9ff !important; }
    @media print {
        body, .stApp { background: white !important; color: black !important; }
        [data-testid="stSidebar"],
        [data-testid="stHeader"],
        [data-testid="stToolbar"],
        .stButton { display: none !important; }
        .kpi-card, .detail-card {
            background: white !important;
            border: 1px solid #aaa !important;
            break-inside: avoid;
        }
        .kpi-name, .kpi-target, .kpi-trend,
        .section-title, .main-title, .sub-title,
        .kpi-value, .detail-value, .detail-label {
            color: black !important;
        }
    }
</style>
""", unsafe_allow_html=True)


# ---------------- DATABASE CONNECTION ----------------

@st.cache_resource
def get_connection():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Task 4 database not found: {DB_PATH}")
    return duckdb.connect(str(DB_PATH), read_only=True)


try:
    con = get_connection()
except Exception as exc:
    st.error(f"Could not connect to the governed metric database: {exc}")
    st.stop()


def query_df(sql, params=None):
    return con.execute(sql, params or []).fetchdf()


# ---------------- FORMATTERS ----------------

def money(value):
    if value is None or pd.isna(value):
        return "N/A"
    value = float(value)
    absolute = abs(value)

    if absolute >= 10_000_000:
        return f"₹{value / 10_000_000:,.2f} Cr"
    if absolute >= 100_000:
        return f"₹{value / 100_000:,.2f} L"
    return f"₹{value:,.0f}"


def number(value):
    if value is None or pd.isna(value):
        return "N/A"
    return f"{value:,.0f}"


def percent(value):
    if value is None or pd.isna(value):
        return "N/A"
    return f"{value:.2f}%"


def safe_value(df, column="metric_value"):
    if df.empty:
        return None
    value = df.iloc[0][column]
    return None if pd.isna(value) else float(value)


# ---------------- MONTH AND TARGETS ----------------

targets_months = query_df("""
    SELECT DISTINCT month
    FROM raw.kpi_targets
    ORDER BY month
""")

if targets_months.empty:
    st.error("No months found in raw.kpi_targets.")
    st.stop()

month_options = [
    pd.Timestamp(x).strftime("%Y-%m")
    for x in targets_months["month"]
]

default_month = month_options[-1]

selected_month = st.selectbox(
    "Reporting month",
    month_options,
    index=len(month_options) - 1,
)

month_date = pd.Timestamp(selected_month + "-01")
month_start = month_date.date()
previous_month = (month_date - pd.DateOffset(months=1)).strftime("%Y-%m")
month_end = calendar.monthrange(month_date.year, month_date.month)[1]
period_end = f"{selected_month}-{month_end:02d}"


def get_targets(month):
    return query_df("""
        SELECT
            AVG(attendance_rate_target) AS attendance_target,
            AVG(attrition_monthly_target_pct) AS attrition_target,
            AVG(task_completion_target_pct) AS task_target,
            COUNT(DISTINCT department_id) AS departments
        FROM raw.kpi_targets
        WHERE month = CAST(? AS DATE)
    """, [month + "-01"])


target_row = get_targets(selected_month).iloc[0]

attendance_target = (
    float(target_row["attendance_target"]) * 100
    if pd.notna(target_row["attendance_target"]) else None
)
attrition_target = (
    float(target_row["attrition_target"])
    if pd.notna(target_row["attrition_target"]) else None
)
task_target = (
    float(target_row["task_target"])
    if pd.notna(target_row["task_target"]) else None
)


# ---------------- GOVERNED METRIC VIEW QUERIES ----------------

def headcount_value(month):
    df = query_df("""
        SELECT SUM(metric_value) AS metric_value
        FROM governed.m01_headcount
        WHERE month_start_date = CAST(? AS DATE)
          AND suppressed = FALSE
    """, [month + "-01"])
    return safe_value(df)


def attrition_value(month):
    # Weighted by opening headcount (group_size).
    df = query_df("""
        SELECT
            SUM(metric_value * group_size)
                / NULLIF(SUM(group_size), 0) AS metric_value
        FROM governed.m04_monthly_attrition
        WHERE month_start_date = CAST(? AS DATE)
          AND suppressed = FALSE
          AND metric_value IS NOT NULL
    """, [month + "-01"])
    return safe_value(df)


def revenue_value(month):
    df = query_df("""
        SELECT SUM(metric_value) AS metric_value
        FROM governed.m16_revenue
        WHERE posting_period = ?
          AND suppressed = FALSE
    """, [month])
    return safe_value(df)


def profit_value(month):
    df = query_df("""
        SELECT metric_value
        FROM governed.m17_net_profit
        WHERE posting_period = ?
          AND suppressed = FALSE
        LIMIT 1
    """, [month])
    return safe_value(df)


def margin_value(month):
    df = query_df("""
        SELECT metric_value
        FROM governed.m18_operating_margin
        WHERE posting_period = ?
          AND suppressed = FALSE
        LIMIT 1
    """, [month])
    return safe_value(df)


def payroll_value(month):
    df = query_df("""
        SELECT SUM(metric_value) AS metric_value
        FROM governed.m09_payroll_cost
        WHERE period_end_date = CAST(? AS DATE)
          AND suppressed = FALSE
    """, [period_end_for(month)])
    return safe_value(df)


def period_end_for(month):
    date = pd.Timestamp(month + "-01")
    last_day = calendar.monthrange(date.year, date.month)[1]
    return f"{month}-{last_day:02d}"


def attendance_value(month):
    # Employee-weighted average of visible department rates.
    # The governed view exposes employee count, not scheduled-day totals.
    df = query_df("""
        SELECT
            SUM(metric_value * group_size)
                / NULLIF(SUM(group_size), 0) AS metric_value
        FROM governed.m13_attendance_rate
        WHERE period_end_date = CAST(? AS DATE)
          AND suppressed = FALSE
          AND metric_value IS NOT NULL
    """, [period_end_for(month)])
    value = safe_value(df)
    return value * 100 if value is not None else None


def task_completion_for_latest_sprint():
    latest = query_df("""
        SELECT sprint_id
        FROM governed.m22_task_completion_rate
        WHERE suppressed = FALSE
          AND metric_value IS NOT NULL
        ORDER BY TRY_CAST(REGEXP_EXTRACT(sprint_id, '[0-9]+') AS INTEGER) DESC
        LIMIT 1
    """)

    if latest.empty:
        return None, None

    sprint = latest.iloc[0]["sprint_id"]

    df = query_df("""
        SELECT
            SUM(metric_value * group_size)
                / NULLIF(SUM(group_size), 0) AS metric_value
        FROM governed.m22_task_completion_rate
        WHERE sprint_id = ?
          AND suppressed = FALSE
          AND metric_value IS NOT NULL
    """, [sprint])

    return safe_value(df), sprint


# ---------------- METRIC VALUES AND TRENDS ----------------

current_task, latest_sprint = task_completion_for_latest_sprint()

current = {
    "headcount": headcount_value(selected_month),
    "attrition": attrition_value(selected_month),
    "revenue": revenue_value(selected_month),
    "profit": profit_value(selected_month),
    "margin": margin_value(selected_month),
    "payroll": payroll_value(selected_month),
    "attendance": attendance_value(selected_month),
    "task": current_task,
}

previous = {
    "headcount": headcount_value(previous_month),
    "attrition": attrition_value(previous_month),
    "revenue": revenue_value(previous_month),
    "profit": profit_value(previous_month),
    "margin": margin_value(previous_month),
    "payroll": payroll_value(previous_month),
    "attendance": attendance_value(previous_month),
}

# For task completion, compare the latest sprint with the preceding sprint.
previous_task = None
if latest_sprint:
    sprint_num = int(latest_sprint.split("-")[-1])
    previous_sprint = f"SP-{sprint_num - 1:02d}"
    prev_task_df = query_df("""
        SELECT
            SUM(metric_value * group_size)
                / NULLIF(SUM(group_size), 0) AS metric_value
        FROM governed.m22_task_completion_rate
        WHERE sprint_id = ?
          AND suppressed = FALSE
          AND metric_value IS NOT NULL
    """, [previous_sprint])
    previous_task = safe_value(prev_task_df)

previous["task"] = previous_task


# ---------------- STATUS AND TREND ----------------

def status_for(key, value, target):
    if value is None or target is None:
        return "NOT CONFIGURED", "grey"

    if key == "attrition":
        return ("ON TARGET", "green") if value <= target else ("NEEDS ATTENTION", "red")

    if value >= target:
        return "ON TARGET", "green"

    if value >= target * 0.95:
        return "NEAR TARGET", "amber"

    return "NEEDS ATTENTION", "red"


def trend_for(key, value, old_value):
    if value is None or old_value is None:
        return "Trend unavailable"

    delta = value - old_value

    if abs(delta) < 0.000001:
        return "→ No material change"

    # Percentage rates use percentage-point change.
    if key in ("attrition", "attendance", "task", "margin"):
        label = f"{abs(delta):.2f} pp"
    elif key == "headcount":
        label = f"{abs(delta):,.0f} employees"
    else:
        label = money(abs(delta))

    if key == "attrition":
        direction = "↓" if delta < 0 else "↑"
    elif key == "payroll":
        direction = "↑" if delta > 0 else "↓"
    else:
        direction = "↑" if delta > 0 else "↓"

    return f"{direction} {label} vs previous period"


# ---------------- SCORECARD ----------------

st.markdown(
    '<div class="main-title">PULSEIQ | Company Health</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="sub-title">Executive scorecard · '
    f'{month_date.strftime("%B %Y")} · Phase 3 Task 15</div>',
    unsafe_allow_html=True,
)

st.caption(
    "Eight headline KPIs | Governed metric layer | "
    "Targets from the approved KPI target table"
)

st.divider()

kpis = [
    {
        "key": "headcount",
        "name": "Headcount",
        "value": current["headcount"],
        "target": None,
        "old": previous["headcount"],
        "formatter": number,
        "source": "governed.m01_headcount",
        "reason": "Shows the size of the active workforce.",
        "grain": "Department × month; sum of unsuppressed department groups.",
    },
    {
        "key": "attrition",
        "name": "Monthly Attrition",
        "value": current["attrition"],
        "target": attrition_target,
        "old": previous["attrition"],
        "formatter": percent,
        "source": "governed.m04_monthly_attrition",
        "reason": "Measures employee exits relative to opening headcount.",
        "grain": "Department × month; weighted by opening headcount.",
    },
    {
        "key": "revenue",
        "name": "Revenue",
        "value": current["revenue"],
        "target": None,
        "old": previous["revenue"],
        "formatter": money,
        "source": "governed.m16_revenue",
        "reason": "Measures the company's monthly income generation.",
        "grain": "Account × month; sum of visible account metrics.",
    },
    {
        "key": "profit",
        "name": "Net Profit",
        "value": current["profit"],
        "target": None,
        "old": previous["profit"],
        "formatter": money,
        "source": "governed.m17_net_profit",
        "reason": "Shows the company's bottom-line financial result.",
        "grain": "Company × month.",
    },
    {
        "key": "margin",
        "name": "Operating Margin",
        "value": current["margin"],
        "target": None,
        "old": previous["margin"],
        "formatter": percent,
        "source": "governed.m18_operating_margin",
        "reason": "Shows how efficiently revenue converts into profit.",
        "grain": "Company × month.",
    },
    {
        "key": "payroll",
        "name": "Payroll Cost",
        "value": current["payroll"],
        "target": None,
        "old": previous["payroll"],
        "formatter": money,
        "source": "governed.m09_payroll_cost",
        "reason": "Tracks the employer cost of the workforce.",
        "grain": "Department × payroll month; suppressed groups excluded.",
    },
    {
        "key": "attendance",
        "name": "Attendance Rate",
        "value": current["attendance"],
        "target": attendance_target,
        "old": previous["attendance"],
        "formatter": percent,
        "source": "governed.m13_attendance_rate",
        "reason": "Indicates workforce availability and attendance health.",
        "grain": "Employee-weighted average of visible department rates.",
    },
    {
        "key": "task",
        "name": "Task Completion",
        "value": current["task"],
        "target": task_target,
        "old": previous["task"],
        "formatter": percent,
        "source": "governed.m22_task_completion_rate",
        "reason": "Tracks completion of eligible operational tasks.",
        "grain": f"Team × sprint; latest available sprint: {latest_sprint or 'N/A'}.",
    },
]

for start in range(0, len(kpis), 4):
    cols = st.columns(4)
    for col, item in zip(cols, kpis[start:start + 4]):
        value = item["value"]
        target = item["target"]
        status, status_class = status_for(item["key"], value, target)

        value_text = item["formatter"](value)
        target_text = (
            item["formatter"](target)
            if target is not None
            else "Not configured"
        )
        trend_text = trend_for(item["key"], value, item["old"])

        with col:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-name">{item['name']}</div>
                <div class="kpi-value">{value_text}</div>
                <div class="kpi-target">Target: {target_text}</div>
                <div class="kpi-trend">{trend_text}</div>
                <span class="status {status_class}">{status}</span>
                <div style="margin-top:12px;font-size:12px;">
                    <a href="#detail-{item['key']}">View KPI details ↓</a>
                </div>
            </div>
            """, unsafe_allow_html=True)


# ---------------- SCORECARD NOTES ----------------

st.markdown('<div class="section-title">Executive reading guide</div>',
            unsafe_allow_html=True)

st.info(
    "Green = target achieved. Amber = within 5% below a higher-is-better "
    "target. Red = target missed. Grey = no configured target or no "
    "comparable value. Attrition is better when lower."
)

st.caption(
    "Suppressed department values are excluded, not treated as zero. "
    "Attendance is an employee-weighted average because the governed view "
    "does not expose scheduled-day totals. Task completion uses the latest "
    "available sprint and is not a monthly KPI."
)


# ---------------- DETAIL SECTIONS / INTERNAL LINKS ----------------

st.markdown('<div class="section-title">KPI details and lineage</div>',
            unsafe_allow_html=True)

for item in kpis:
    st.markdown(f'<div id="detail-{item["key"]}"></div>',
                unsafe_allow_html=True)

    with st.expander(f'{item["name"]} — details', expanded=False):
        st.markdown(f"**Why this KPI matters:** {item['reason']}")
        st.markdown(f"**Governed source:** `{item['source']}`")
        st.markdown(f"**Grain and aggregation:** {item['grain']}")
        st.markdown(f"**Selected period:** {selected_month}")

        st.write("Current value:", item["formatter"](item["value"]))
        st.write(
            "Target:",
            item["formatter"](item["target"])
            if item["target"] is not None else "Not configured",
        )
        st.write(
            "Previous period:",
            item["formatter"](item["old"])
            if item["old"] is not None else "Not available",
        )

        if item["key"] == "task":
            st.caption(
                "Task completion is sourced from the latest sprint, "
                "not the selected reporting month."
            )


# ---------------- KPI SELECTION DOCUMENT ----------------

st.markdown('<div class="section-title">Why these eight KPIs?</div>',
            unsafe_allow_html=True)

reasons = pd.DataFrame([
    ["Headcount", "Workforce capacity and company scale."],
    ["Monthly Attrition", "Employee retention and workforce stability."],
    ["Revenue", "Monthly business income and growth."],
    ["Net Profit", "Bottom-line financial performance."],
    ["Operating Margin", "Profitability efficiency."],
    ["Payroll Cost", "Major workforce-related cost control."],
    ["Attendance Rate", "Workforce availability."],
    ["Task Completion", "Operational execution and delivery."],
], columns=["Headline KPI", "Executive reason"])

st.dataframe(reasons, use_container_width=True, hide_index=True)

st.markdown("**If the scorecard had to be reduced to five KPIs:**")
st.markdown("""
- **Keep:** Revenue, Net Profit, Operating Margin, Monthly Attrition,
  and Attendance Rate.
- **Remove Headcount:** useful context, but not a direct performance outcome.
- **Remove Payroll Cost:** important operationally, but its financial impact
  is partly reflected in net profit and operating margin.
- **Remove Task Completion:** valuable for operations, but less central to
  a company-wide financial and workforce health snapshot.
""")

st.divider()
st.caption(
    "PulseIQ | Phase 3 · Task 15 | Read-only connection to Task 4 "
    "governed metric layer | Use your browser's Print / Save as PDF "
    "to export the scorecard."
)
