from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "Phase 1" / "Task 4" / "pulseiq_task4.duckdb"
MIN_GROUP = 5
MIN_RISK_GROUP = 10

st.set_page_config(
    page_title="PulseIQ | Attrition Analytics",
    page_icon="📉",
    layout="wide",
)

st.title("PulseIQ | Attrition Analytics")
st.caption(
    "Actual exits and governed attrition metrics are separated from "
    "predicted risk. All database access is read-only."
)

if not DB.exists():
    st.error(f"Existing governed database not found: {DB}")
    st.stop()


@st.cache_data(ttl=60)
def load_data(db_path, db_modified):
    with duckdb.connect(db_path, read_only=True) as con:
        departments = con.execute("""
            SELECT department_id, department_name
            FROM raw.dim_department
            QUALIFY ROW_NUMBER() OVER (
                PARTITION BY department_id ORDER BY department_name
            ) = 1
            ORDER BY department_name
        """).fetchdf()

        actual = con.execute("""
            SELECT
                e.month_start_date,
                e.department_id,
                d.department_name,
                e.metric_value AS governed_exits,
                e.group_size AS exit_group_size,
                e.suppressed AS exits_suppressed,
                a.metric_value AS monthly_attrition_pct,
                a.suppressed AS attrition_suppressed,
                r.metric_value AS rolling_12m_attrition_pct,
                r.suppressed AS rolling_suppressed,
                v.metric_value AS rolling_12m_voluntary_attrition_pct,
                v.suppressed AS voluntary_rate_suppressed,
                f.exits AS raw_exits,
                f.voluntary_exits,
                f.headcount_start
            FROM governed.m03_exits e
            LEFT JOIN governed.m04_monthly_attrition a
              ON a.month_start_date = e.month_start_date
             AND a.department_id = e.department_id
            LEFT JOIN governed.m05_rolling_12m_attrition r
              ON r.month_start_date = e.month_start_date
             AND r.department_id = e.department_id
            LEFT JOIN governed.m06_voluntary_attrition v
              ON v.month_start_date = e.month_start_date
             AND v.department_id = e.department_id
            LEFT JOIN raw.fact_headcount_monthly f
              ON f.month_start_date = e.month_start_date
             AND f.department_id = e.department_id
            LEFT JOIN raw.dim_department d
              ON d.department_id = e.department_id
            ORDER BY e.month_start_date, d.department_name
        """).fetchdf()

        tenure = con.execute("""
            WITH latest_employee AS (
                SELECT *,
                    ROW_NUMBER() OVER (
                        PARTITION BY employee_id
                        ORDER BY valid_from DESC NULLS LAST,
                                 employee_key DESC
                    ) AS rn
                FROM raw.dim_employee
            )
            SELECT
                department_id,
                hire_date,
                exit_date,
                employment_status
            FROM latest_employee
            WHERE rn = 1
              AND hire_date IS NOT NULL
              AND exit_date IS NOT NULL
              AND exit_date >= hire_date
        """).fetchdf()

        risk = con.execute("""
            SELECT
                r.department_id,
                d.department_name,
                r.metric_value AS high_risk_share,
                r.group_size,
                r.suppressed
            FROM governed.m27_high_risk_share r
            LEFT JOIN raw.dim_department d
              ON d.department_id = r.department_id
            ORDER BY d.department_name
        """).fetchdf()

        snapshot = con.execute("""
            SELECT MAX(as_of_date) FROM raw.fact_attrition_risk
        """).fetchone()[0]

    actual["month_start_date"] = pd.to_datetime(actual["month_start_date"])
    for col in [
        "governed_exits", "monthly_attrition_pct",
        "rolling_12m_attrition_pct",
        "rolling_12m_voluntary_attrition_pct",
        "raw_exits", "voluntary_exits", "headcount_start",
    ]:
        actual[col] = pd.to_numeric(actual[col], errors="coerce")

    tenure["hire_date"] = pd.to_datetime(tenure["hire_date"], errors="coerce")
    tenure["exit_date"] = pd.to_datetime(tenure["exit_date"], errors="coerce")
    tenure["tenure_years"] = (
        (tenure["exit_date"] - tenure["hire_date"]).dt.days / 365.25
    )
    tenure["tenure_band"] = pd.cut(
        tenure["tenure_years"],
        bins=[-0.001, 1, 3, 5, 10, float("inf")],
        labels=["Under 1 year", "1–3 years", "3–5 years",
                "5–10 years", "10+ years"],
        right=False,
    )
    return departments, actual, tenure, risk, snapshot


try:
    departments, actual, tenure, risk, snapshot = load_data(
        str(DB), DB.stat().st_mtime
    )
except Exception as exc:
    st.error("Could not read the existing governed data.")
    st.code(str(exc))
    st.stop()

if actual.empty:
    st.warning("No monthly attrition metric records were found.")
    st.stop()

st.sidebar.header("Filters")
dept_names = sorted(actual["department_name"].dropna().unique().tolist())
selected_depts = st.sidebar.multiselect(
    "Department",
    options=dept_names,
    default=dept_names,
)

min_date = actual["month_start_date"].min().date()
max_date = actual["month_start_date"].max().date()
date_range = st.sidebar.date_input(
    "Actual exits date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)

if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date = end_date = date_range

period = actual[
    actual["month_start_date"].dt.date.between(start_date, end_date)
    & actual["department_name"].isin(selected_depts)
].copy()

if period.empty:
    st.warning("No data matches these filters.")
    st.stop()

# Use only governed M03 values for displayed actual exit counts.
visible = period[
    (~period["exits_suppressed"].fillna(True))
    & period["governed_exits"].notna()
].copy()

st.subheader("1. Actual exits and attrition")
st.caption(
    "Actual results come from governed.m03_exits and "
    "governed.m04_monthly_attrition. The governed database currently "
    "releases only a limited number of department-month metrics. "
    "Departments with suppressed values are intentionally not displayed; "
    "missing departments must not be interpreted as zero exits."
)

total_visible_exits = int(visible["governed_exits"].sum()) if not visible.empty else 0
visible_months = visible["month_start_date"].nunique()
valid_rates = period[
    (~period["attrition_suppressed"].fillna(True))
    & period["monthly_attrition_pct"].notna()
]
mean_rate = (
    valid_rates["monthly_attrition_pct"].mean()
    if not valid_rates.empty else None
)

k1, k2, k3 = st.columns(3)
k1.metric("Visible governed exits", f"{total_visible_exits:,}")
k2.metric("Months with visible exit metrics", f"{visible_months:,}")
k3.metric(
    "Mean visible monthly attrition",
    f"{mean_rate:.2f}%" if mean_rate is not None else "Suppressed / unavailable",
    help="Unweighted mean of visible governed department-month percentages.",
)

left, right = st.columns(2)

with left:
    st.markdown("**Monthly exits**")
    if not visible.empty:
        monthly = (
            visible.groupby("month_start_date", as_index=False)["governed_exits"]
            .sum()
            .sort_values("month_start_date")
        )
        monthly = monthly[monthly["governed_exits"] >= MIN_GROUP]
        if not monthly.empty:
            fig = px.bar(
                monthly, x="month_start_date", y="governed_exits",
                labels={
                    "month_start_date": "Month",
                    "governed_exits": "Visible governed exits",
                },
            )
            st.plotly_chart(fig, use_container_width=True)
            st.caption(
                "Monthly totals sum only department-month values released by M03; "
                "suppressed values are excluded."
            )
        else:
            st.info("No monthly total meets the display threshold.")
    else:
        st.info("No non-suppressed exit metrics are available for this selection.")

with right:
    st.markdown("**Governed monthly attrition rate by department**")
    rate_chart = valid_rates.sort_values("month_start_date")
    if not rate_chart.empty:
        fig = px.line(
            rate_chart,
            x="month_start_date",
            y="monthly_attrition_pct",
            color="department_name",
            markers=True,
            labels={
                "month_start_date": "Month",
                "monthly_attrition_pct": "Attrition (%)",
                "department_name": "Department",
            },
        )
        fig.update_yaxes(ticksuffix="%")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No visible governed monthly attrition rates for this selection.")




st.markdown("**Department attrition-rate summary over the selected period**")
st.caption(
    "Shows averages of released governed monthly attrition rates. "
    "This is a rate comparison, not a ranking of actual exit counts."
)

if not valid_rates.empty:
    dept_rate_summary = (
        valid_rates.groupby("department_name", as_index=False)
        .agg(
            mean_monthly_attrition_pct=("monthly_attrition_pct", "mean"),
            released_months=("month_start_date", "nunique"),
        )
        .sort_values("mean_monthly_attrition_pct", ascending=False)
    )

    dept_rate_summary["mean_monthly_attrition_pct"] = (
        dept_rate_summary["mean_monthly_attrition_pct"].round(2)
    )

    st.dataframe(
        dept_rate_summary.rename(
            columns={
                "department_name": "Department",
                "mean_monthly_attrition_pct": "Mean monthly attrition (%)",
                "released_months": "Months with released rates",
            }
        ),
        hide_index=True,
        use_container_width=True,
    )
else:
    st.info(
        "No released governed monthly attrition rates are available "
        "for the selected filters."
    )

st.subheader("2. Voluntary versus other exits")
st.caption(
    "The split uses the source monthly fact table only when the relevant "
    "department-month has a released M03 exit metric. Each displayed category "
    "must independently contain at least five exits."
)

if not visible.empty:
    voluntary = int(visible["voluntary_exits"].fillna(0).sum())
    all_exits = int(visible["raw_exits"].fillna(0).sum())
    other = max(0, all_exits - voluntary)

    split_cols = st.columns(2)
    split_cols[0].metric(
        "Voluntary exits",
        f"{voluntary:,}" if voluntary >= MIN_GROUP else "Suppressed (<5)",
    )
    split_cols[1].metric(
        "Other exits",
        f"{other:,}" if other >= MIN_GROUP else "Suppressed (<5)",
    )
    st.caption(
        "These totals cover only department-months whose M03 exit metric is "
        "released. Category counts under five are hidden."
    )
else:
    st.info("No eligible exit groups are available for this split.")

st.divider()
st.subheader("3. Tenure at exit")
st.caption(
    "Tenure is calculated from hire date to exit date using one latest "
    "employee record per employee. No names or employee IDs are displayed."
)

tenure_filtered = tenure[
    tenure["department_id"].isin(
        period["department_id"].dropna().unique()
    )
    & tenure["exit_date"].dt.date.between(start_date, end_date)
].copy()

if len(tenure_filtered) >= MIN_GROUP:
    median_tenure = tenure_filtered["tenure_years"].median()
    st.metric("Median tenure at exit", f"{median_tenure:.1f} years")

    bands = (
        tenure_filtered.groupby("tenure_band", observed=False)
        .size()
        .rename("exit_count")
        .reset_index()
    )
    bands["tenure_band"] = bands["tenure_band"].astype(str)
    bands["display_count"] = bands["exit_count"].where(
        bands["exit_count"] >= MIN_GROUP
    )
    bands = bands[bands["display_count"].notna()]
    if not bands.empty:
        fig = px.bar(
            bands,
            x="tenure_band",
            y="display_count",
            labels={"tenure_band": "Tenure at exit", "display_count": "Exits"},
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Individual tenure buckets are suppressed because each is below five.")
else:
    st.info("Tenure results are hidden because fewer than five exit records match.")

st.divider()
st.subheader("4. Predicted, not certain")
st.warning(
    "Predictions are estimates for supportive HR conversations, not facts or "
    "decisions about individuals. They do not prove that someone will leave."
)
if snapshot is not None:
    st.caption(f"Risk feed snapshot date: {pd.Timestamp(snapshot).date()}")

risk_filtered = risk[
    risk["department_name"].isin(selected_depts)
    & (~risk["suppressed"].fillna(True))
    & (pd.to_numeric(risk["group_size"], errors="coerce") >= MIN_RISK_GROUP)
    & risk["high_risk_share"].notna()
].copy()

if not risk_filtered.empty:
    risk_filtered["high_risk_share_pct"] = risk_filtered["high_risk_share"] * 100
    fig = px.bar(
        risk_filtered.sort_values("high_risk_share_pct"),
        x="high_risk_share_pct",
        y="department_name",
        orientation="h",
        labels={
            "high_risk_share_pct": "High-risk share (%)",
            "department_name": "Department",
        },
    )
    fig.update_xaxes(ticksuffix="%")
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "Risk shares use governed.m27_high_risk_share. Only non-suppressed "
        "groups of at least ten are shown. No individual prediction is displayed."
    )
else:
    st.info("No risk groups meet the governed minimum group-size requirement.")

st.divider()
st.subheader("5. Three biggest findings")

findings = []

# Finding 1: actual attrition, using only visible governed M04 values.
if not valid_rates.empty:
    dept_rates = (
        valid_rates.groupby("department_name")["monthly_attrition_pct"]
        .agg(["mean", "count"])
        .sort_values("mean", ascending=False)
    )
    if not dept_rates.empty:
        dept_name = dept_rates.index[0]
        row = dept_rates.iloc[0]
        findings.append(
            f"**Observed attrition:** {dept_name} had the highest mean "
            f"visible monthly attrition rate at {row['mean']:.2f}% across "
            f"{int(row['count'])} visible months."
        )

# Finding 2: highest predicted risk, only among governed visible groups.
if not risk_filtered.empty:
    risk_ranked = risk_filtered.sort_values(
        "high_risk_share", ascending=False
    )
    top_risk = risk_ranked.iloc[0]
    findings.append(
        f"**Predicted risk, not actual exits:** "
        f"{top_risk['department_name']} had the highest governed high-risk "
        f"share at {top_risk['high_risk_share'] * 100:.2f}% "
        f"for a group of {int(top_risk['group_size'])}."
    )

    # A second department comparison is useful only if another distinct
    # department is available in the governed, non-suppressed risk feed.
    if len(risk_ranked) > 1:
        second_risk = risk_ranked.iloc[1]
        findings.append(
            f"**Predicted risk comparison:** {second_risk['department_name']} "
            f"had a governed high-risk share of "
            f"{second_risk['high_risk_share'] * 100:.2f}% "
            f"for a group of {int(second_risk['group_size'])}."
        )

# Actual exit count: use only released M03 rows, never raw suppressed counts.
if not visible.empty:
    month_totals = (
        visible.groupby("month_start_date")["governed_exits"]
        .sum()
        .sort_values(ascending=False)
    )
    if not month_totals.empty and month_totals.iloc[0] >= MIN_GROUP:
        month = month_totals.index[0]
        findings.append(
            f"**Released exit-count context:** {month:%b %Y} had "
            f"{int(month_totals.iloc[0])} visible exits across released "
            "M03 department-month groups. This is not the dataset-wide "
            "exit total; suppressed counts are excluded."
        )

if not findings:
    st.info(
        "There is not enough non-suppressed data to produce findings "
        "for the current filters. Broaden the date range or department selection."
    )
else:
    for i, finding in enumerate(findings[:3], start=1):
        st.markdown(f"{i}. {finding}")
    if len(findings) < 3:
        st.caption(
            "Fewer than three findings could be supported by the visible "
            "metrics; no missing findings have been invented."
        )

st.divider()
st.subheader("Metric and privacy notes")
st.markdown(
    """
- **Actual exits:** governed metric view `governed.m03_exits`.
- **Monthly attrition:** governed metric view `governed.m04_monthly_attrition`.
- **Rolling 12-month attrition:** sourced from `governed.m05_rolling_12m_attrition`.
- **Voluntary attrition rate:** sourced from `governed.m06_voluntary_attrition`.
- **Predicted risk:** governed view `governed.m27_high_risk_share`.
- **Privacy:** suppressed metric values are not reconstructed from raw counts.
  Exit charts require released metrics; tenure buckets need at least five records;
  risk groups need at least ten.
- **Prediction limits:** this baseline demo model is an early-warning support
  signal, not a certainty, diagnosis, or basis for an automated employment decision.
"""
)
