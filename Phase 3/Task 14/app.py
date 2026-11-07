from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ============================================================
# PULSEIQ - PHASE 3, TASK 14
# AI Signals Dashboard
# All source files are local copies inside this Task 14 folder.
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
SOURCE_DIR = BASE_DIR / "data" / "source"
REFERENCE_DIR = BASE_DIR / "data" / "reference"
EVIDENCE_DIR = BASE_DIR / "evidence"
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

st.set_page_config(
    page_title="PulseIQ | AI Signals",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .main {background-color: #0b1020;}
    [data-testid="stSidebar"] {background-color: #111a2e;}
    .block-container {padding-top: 1.5rem; padding-bottom: 2rem;}
    .hero {
        padding: 22px 26px;
        border: 1px solid #263653;
        border-radius: 16px;
        background: linear-gradient(120deg, #172642, #10182b);
        margin-bottom: 18px;
    }
    .hero h1 {margin: 0; color: #f2f6ff; font-size: 2.1rem;}
    .hero p {color: #b7c5dc; margin: 8px 0 0 0;}
    .ai-label {
        display: inline-block;
        color: #ffd98a;
        border: 1px solid #80652c;
        background: #352b17;
        border-radius: 6px;
        padding: 5px 9px;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.2px;
        margin: 2px 0 10px 0;
    }
    .note {
        background: #14233a;
        border-left: 3px solid #62a6ff;
        padding: 14px 16px;
        border-radius: 8px;
        color: #d6e2f3;
        line-height: 1.55;
        margin-top: 28px;
    }
    .small-muted {color: #aab8ce; font-size: 0.88rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


# ----------------------------
# Load source files
# ----------------------------

@st.cache_data
def load_data():
    anomaly = pd.read_csv(SOURCE_DIR / "fact_anomaly.csv")
    forecast = pd.read_csv(SOURCE_DIR / "fact_forecast.csv")
    risk = pd.read_csv(SOURCE_DIR / "fact_attrition_risk.csv")
    headcount = pd.read_csv(SOURCE_DIR / "fact_headcount_monthly.csv")
    departments = pd.read_csv(REFERENCE_DIR / "dim_department.csv")

    anomaly["money_at_risk"] = pd.to_numeric(
        anomaly["money_at_risk"], errors="coerce"
    )
    anomaly["anomaly_score"] = pd.to_numeric(
        anomaly["anomaly_score"], errors="coerce"
    )
    forecast["forecast_value"] = pd.to_numeric(
        forecast["forecast_value"], errors="coerce"
    )
    forecast["lower_80"] = pd.to_numeric(
        forecast["lower_80"], errors="coerce"
    )
    forecast["upper_80"] = pd.to_numeric(
        forecast["upper_80"], errors="coerce"
    )
    forecast["forecast_month"] = pd.to_datetime(
        forecast["forecast_month"], errors="coerce"
    )
    headcount["month_start_date"] = pd.to_datetime(
        headcount["month_start_date"], errors="coerce"
    )
    risk["risk_score_12m"] = pd.to_numeric(
        risk["risk_score_12m"], errors="coerce"
    )

    return anomaly, forecast, risk, headcount, departments


try:
    anomaly, forecast, risk, headcount, departments = load_data()
except Exception as exc:
    st.error(f"Could not load Task 14 source files: {exc}")
    st.stop()


# ----------------------------
# Helpers
# ----------------------------

def money_inr(value):
    if pd.isna(value):
        return "Not quantified"
    return f"₹{value:,.2f}"


def make_anomaly_summary(df):
    work = df.copy()
    work["reason_code"] = work["reason_code"].fillna("UNKNOWN")

    summary = (
        work.groupby("reason_code", dropna=False)
        .agg(
            anomaly_count=("result_id", "count"),
            quantified_count=("money_at_risk", "count"),
            money_at_risk=("money_at_risk", "sum"),
        )
        .reset_index()
    )

    summary["unquantified_count"] = (
        summary["anomaly_count"] - summary["quantified_count"]
    )
    summary = summary.sort_values(
        ["money_at_risk", "anomaly_count"],
        ascending=[False, False],
    )
    return summary


def get_actual_series(metric, department_id):
    data = headcount.copy()

    if metric == "headcount_end":
        if department_id == "ALL":
            actual = (
                data.groupby("month_start_date", as_index=False)
                ["headcount_end"].sum()
                .rename(columns={"headcount_end": "actual_value"})
            )
        else:
            actual = (
                data[data["department_id"] == department_id][
                    ["month_start_date", "headcount_end"]
                ]
                .rename(columns={"headcount_end": "actual_value"})
            )
        actual["month"] = actual["month_start_date"]
        return actual[["month", "actual_value"]].sort_values("month")

    # Company-wide attrition actual is weighted:
    # total exits / total starting headcount * 100.
    monthly = (
        data.groupby("month_start_date", as_index=False)
        .agg(
            total_exits=("exits", "sum"),
            total_headcount_start=("headcount_start", "sum"),
        )
    )
    monthly["actual_value"] = (
        monthly["total_exits"]
        / monthly["total_headcount_start"].replace(0, pd.NA)
        * 100
    )
    monthly["month"] = monthly["month_start_date"]
    return monthly[["month", "actual_value"]].sort_values("month")


def get_forecast_series(metric, department_id):
    selected = forecast[forecast["metric"] == metric].copy()

    if metric == "attrition_rate_monthly_pct":
        department_id = "ALL"

    selected = selected[selected["department_id"] == department_id].copy()
    selected = selected.sort_values("forecast_month")
    return selected


def calculate_forecast_errors(metric, department_id):
    actual = get_actual_series(metric, department_id)
    predicted = get_forecast_series(metric, department_id)

    merged = predicted.merge(
        actual,
        left_on="forecast_month",
        right_on="month",
        how="inner",
    )

    if merged.empty:
        return pd.DataFrame(
            columns=[
                "metric",
                "department_id",
                "month",
                "actual_value",
                "forecast_value",
                "error",
                "absolute_error",
                "absolute_percentage_error_pct",
            ]
        )

    merged["error"] = merged["forecast_value"] - merged["actual_value"]
    merged["absolute_error"] = merged["error"].abs()
    merged["absolute_percentage_error_pct"] = (
        merged["absolute_error"]
        / merged["actual_value"].replace(0, pd.NA)
        * 100
    )
    merged["metric"] = metric
    merged["department_id"] = department_id

    return merged[
        [
            "metric",
            "department_id",
            "forecast_month",
            "actual_value",
            "forecast_value",
            "error",
            "absolute_error",
            "absolute_percentage_error_pct",
        ]
    ].rename(columns={"forecast_month": "month"})


def export_evidence(anomaly_summary, error_table):
    anomaly_summary.to_csv(
        EVIDENCE_DIR / "anomaly_exposure_by_type.csv", index=False
    )

    error_table.to_csv(
        EVIDENCE_DIR / "forecast_error_table.csv", index=False
    )

    all_actual_months = set(
        headcount["month_start_date"].dt.strftime("%Y-%m-%d").dropna()
    )
    all_forecast_months = set(
        forecast["forecast_month"].dt.strftime("%Y-%m-%d").dropna()
    )
    overlap = sorted(all_actual_months.intersection(all_forecast_months))

    status = pd.DataFrame(
        [{
            "actuals_through": headcount["month_start_date"].max().date(),
            "forecast_from": forecast["forecast_month"].min().date(),
            "forecast_through": forecast["forecast_month"].max().date(),
            "overlapping_months": len(overlap),
            "forecast_error_status": (
                "Available" if overlap else
                "Not available - all forecast months are future periods"
            ),
            "explanation": (
                "Forecast error will be measurable after actual results "
                "are loaded for the forecast months."
            ),
        }]
    )
    status.to_csv(
        EVIDENCE_DIR / "forecast_accuracy_status.csv", index=False
    )

    risk_summary = (
        risk.groupby("risk_band")
        .size()
        .reset_index(name="employee_count")
    )
    risk_summary.to_csv(
        EVIDENCE_DIR / "attrition_risk_band_summary.csv", index=False
    )


# ----------------------------
# Header and sidebar
# ----------------------------

st.markdown(
    """
    <div class="hero">
        <h1>🧠 PulseIQ — AI Signals Dashboard</h1>
        <p>Workforce anomaly exposure, predictive signals and forecast monitoring</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.sidebar.title("Dashboard Controls")
st.sidebar.caption("Phase 3 · Task 14 · Advanced")

metric_choice = st.sidebar.selectbox(
    "Forecast metric",
    ["headcount_end", "attrition_rate_monthly_pct"],
    format_func=lambda x: (
        "Headcount" if x == "headcount_end"
        else "Monthly attrition rate (%)"
    ),
)

forecast_departments = sorted(
    forecast.loc[
        forecast["metric"] == "headcount_end", "department_id"
    ].dropna().unique().tolist()
)
department_options = ["ALL"] + [
    d for d in forecast_departments if d != "ALL"
]

department_names = dict(
    zip(departments["department_id"], departments["department_name"])
)

department_choice = st.sidebar.selectbox(
    "Department",
    department_options,
    format_func=lambda x: (
        "All departments" if x == "ALL"
        else f"{x} — {department_names.get(x, x)}"
    ),
)

if metric_choice == "attrition_rate_monthly_pct":
    department_choice = "ALL"
    st.sidebar.info(
        "The supplied attrition forecast is company-wide only."
    )

st.sidebar.divider()
st.sidebar.caption(
    "Source data: Task 14 local copies of validated Phase 1 AI outputs "
    "and historical workforce actuals."
)


# ----------------------------
# KPI calculations
# ----------------------------

anomaly_summary = make_anomaly_summary(anomaly)
known_money = anomaly["money_at_risk"].dropna()
total_exposure = known_money.sum()
quantified_records = int(known_money.count())
unquantified_records = int(anomaly["money_at_risk"].isna().sum())

high_risk_count = int((risk["risk_band"] == "High").sum())
latest_actual_date = headcount["month_start_date"].max()
first_forecast_date = forecast["forecast_month"].min()
last_forecast_date = forecast["forecast_month"].max()

error_table = calculate_forecast_errors(
    metric_choice, department_choice
)
export_evidence(anomaly_summary, error_table)

k1, k2, k3, k4 = st.columns(4)
k1.metric("Flagged anomaly records", f"{len(anomaly):,}")
k2.metric("Quantified money at risk", money_inr(total_exposure))
k3.metric("Anomalies without money value", f"{unquantified_records:,}")
k4.metric("High attrition-risk signals", f"{high_risk_count:,}")

st.caption(
    f"Historical actuals through {latest_actual_date:%B %Y} · "
    f"Forecast horizon {first_forecast_date:%b %Y} to "
    f"{last_forecast_date:%b %Y}"
)

st.divider()


# ============================================================
# SECTION 1 — ANOMALY EXPOSURE
# ============================================================

st.header("1. Anomaly Signals & Money at Risk")

left, right = st.columns([1.65, 1])

with left:
    st.markdown(
        '<div class="ai-label">AI-generated, for human review</div>',
        unsafe_allow_html=True,
    )

    chart_data = anomaly_summary[
        anomaly_summary["money_at_risk"] > 0
    ].sort_values("money_at_risk", ascending=True)

    if not chart_data.empty:
        fig = px.bar(
            chart_data,
            x="money_at_risk",
            y="reason_code",
            orientation="h",
            text="money_at_risk",
            labels={
                "money_at_risk": "Known money at risk (₹)",
                "reason_code": "Anomaly type",
            },
            title="Ranked anomaly types by quantified money at risk",
            color="money_at_risk",
            color_continuous_scale="Teal",
        )
        fig.update_traces(
            texttemplate="₹%{x:,.0f}",
            textposition="outside",
            cliponaxis=False,
        )
        fig.update_layout(
            height=470,
            template="plotly_dark",
            showlegend=False,
            coloraxis_showscale=False,
            margin=dict(l=10, r=75, t=55, b=35),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No quantified anomaly exposure is available.")

with right:
    st.markdown(
        """
        <div class="note">
        <b>What this chart means</b><br><br>
        The chart ranks anomaly categories by the sum of their available
        money-at-risk values. It helps reviewers prioritise categories
        with the largest quantified exposure.<br><br>
        <b>Important limitation:</b> a missing money-at-risk value is
        unknown, not zero. Categories without a monetary estimate are
        excluded from this money ranking and are reported separately.
        These are investigation signals, not confirmed losses or fraud.
        </div>
        """,
        unsafe_allow_html=True,
    )

st.subheader("Anomaly type detail")
display_anomaly = anomaly_summary.copy()
display_anomaly["money_at_risk"] = display_anomaly[
    "money_at_risk"
].map(money_inr)
display_anomaly = display_anomaly.rename(
    columns={
        "reason_code": "Anomaly type",
        "anomaly_count": "Total signals",
        "quantified_count": "With money estimate",
        "unquantified_count": "Without money estimate",
        "money_at_risk": "Known money at risk",
    }
)
st.dataframe(display_anomaly, use_container_width=True, hide_index=True)

st.caption(
    f"Known money-at-risk total: {money_inr(total_exposure)} across "
    f"{quantified_records:,} quantified records. "
    f"{unquantified_records:,} records have no monetary estimate."
)

st.divider()


# ============================================================
# SECTION 2 — FORECAST VS ACTUAL
# ============================================================

st.header("2. Forecast vs Actual")

st.markdown(
    '<div class="ai-label">AI-generated, for human review</div>',
    unsafe_allow_html=True,
)

actual_series = get_actual_series(metric_choice, department_choice)
forecast_series = get_forecast_series(metric_choice, department_choice)

forecast_left, forecast_right = st.columns([1.7, 1])

with forecast_left:
    if forecast_series.empty:
        st.warning(
            "No forecast records are available for this metric and scope."
        )
    else:
        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=actual_series["month"],
                y=actual_series["actual_value"],
                mode="lines",
                name="Historical actual",
                line=dict(width=2.5, color="#55b8ff"),
            )
        )

        # Upper boundary first, then lower boundary fills the 80% band.
        fig.add_trace(
            go.Scatter(
                x=forecast_series["forecast_month"],
                y=forecast_series["upper_80"],
                mode="lines",
                line=dict(width=0),
                name="80% range upper",
                showlegend=False,
                hoverinfo="skip",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=forecast_series["forecast_month"],
                y=forecast_series["lower_80"],
                mode="lines",
                line=dict(width=0),
                fill="tonexty",
                fillcolor="rgba(255, 190, 80, 0.20)",
                name="80% forecast range",
                hoverinfo="skip",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=forecast_series["forecast_month"],
                y=forecast_series["forecast_value"],
                mode="lines+markers",
                name="AI forecast",
                line=dict(width=3, color="#ffbd59", dash="dash"),
                marker=dict(size=8),
            )
        )

        metric_label = (
            "Headcount" if metric_choice == "headcount_end"
            else "Monthly attrition rate (%)"
        )
        fig.update_layout(
            title=f"{metric_label}: historical actual and forecast",
            xaxis_title="Month",
            yaxis_title=metric_label,
            template="plotly_dark",
            height=480,
            hovermode="x unified",
            legend=dict(orientation="h", y=-0.22),
            margin=dict(l=10, r=20, t=60, b=70),
        )
        st.plotly_chart(fig, use_container_width=True)

with forecast_right:
    if metric_choice == "headcount_end":
        scope_text = (
            "all departments combined"
            if department_choice == "ALL"
            else department_names.get(department_choice, department_choice)
        )
    else:
        scope_text = "the company overall"

    st.markdown(
        f"""
        <div class="note">
        <b>How to read this forecast</b><br><br>
        The blue line shows historical actuals for {scope_text}.
        The dashed forecast line shows the supplied model estimate for
        future months. The shaded area is the supplied lower-to-upper
        80% forecast range.<br><br>
        The forecast was trained through September 2026. An 80% range
        is an uncertainty interval from the supplied model, not a
        guarantee that the actual result will fall inside it.<br><br>
        Forecasts are planning signals. They should be reviewed alongside
        business context and updated when new actuals arrive.
        </div>
        """,
        unsafe_allow_html=True,
    )

st.subheader("Forecast values and 80% range")

if not forecast_series.empty:
    forecast_display = forecast_series[
        ["forecast_month", "forecast_value", "lower_80", "upper_80",
         "method", "model_version"]
    ].copy()
    forecast_display["forecast_month"] = (
        forecast_display["forecast_month"].dt.strftime("%b %Y")
    )
    forecast_display = forecast_display.rename(
        columns={
            "forecast_month": "Month",
            "forecast_value": "Forecast",
            "lower_80": "Lower 80% range",
            "upper_80": "Upper 80% range",
            "method": "Method",
            "model_version": "Model version",
        }
    )
    st.dataframe(
        forecast_display,
        use_container_width=True,
        hide_index=True,
    )

st.divider()


# ============================================================
# SECTION 3 — FORECAST ERROR MONITORING
# ============================================================

st.header("3. Forecast Error Monitoring")

if error_table.empty:
    st.info(
        "Forecast error is not available yet. All supplied forecast months "
        "are in the future (October 2026–March 2027), while historical "
        "actuals currently end in September 2026. There are zero overlapping "
        "months, so MAE/MAPE cannot be calculated honestly yet."
    )
    st.dataframe(
        error_table,
        use_container_width=True,
        hide_index=True,
    )
else:
    st.success(
        f"{len(error_table)} month(s) have both forecast and actual values."
    )
    st.dataframe(
        error_table,
        use_container_width=True,
        hide_index=True,
    )

st.caption(
    "The forecast error CSV is saved in the Task 14 evidence folder. "
    "It contains column headers but no fabricated rows until actuals "
    "become available for forecast months."
)

st.divider()


# ============================================================
# SECTION 4 — ATTRITION RISK SIGNALS
# ============================================================

st.header("4. Attrition Risk Signals")

risk_summary = (
    risk.groupby("risk_band")
    .size()
    .reindex(["Low", "Medium", "High"], fill_value=0)
    .reset_index(name="employee_count")
)

risk_left, risk_right = st.columns([1.5, 1])

with risk_left:
    st.markdown(
        '<div class="ai-label">AI-generated, for human review</div>',
        unsafe_allow_html=True,
    )

    fig_risk = px.bar(
        risk_summary,
        x="risk_band",
        y="employee_count",
        text="employee_count",
        labels={
            "risk_band": "Risk band",
            "employee_count": "Number of employees",
        },
        title="Aggregated 12-month attrition risk bands",
        color="risk_band",
        category_orders={"risk_band": ["Low", "Medium", "High"]},
    )
    fig_risk.update_layout(
        template="plotly_dark",
        height=380,
        showlegend=False,
        margin=dict(l=10, r=10, t=55, b=35),
    )
    st.plotly_chart(fig_risk, use_container_width=True)

with risk_right:
    st.markdown(
        """
        <div class="note">
        <b>What this signal means</b><br><br>
        This chart shows only aggregate counts in the supplied Low,
        Medium and High risk bands. It does not expose employee names
        or IDs.<br><br>
        The source model describes itself as a baseline demo model and
        says it is a support signal for HR, never a decision. Risk bands
        must not be used alone for employment decisions.
        </div>
        """,
        unsafe_allow_html=True,
    )

st.divider()


# ============================================================
# SECTION 5 — REVIEW PRIORITIES
# ============================================================

st.header("5. Human Review Priorities")

top_anomalies = anomaly_summary.head(3)
recommendations = []

for _, row in top_anomalies.iterrows():
    if row["money_at_risk"] > 0:
        recommendations.append(
            f"Review {row['reason_code']} first: "
            f"{int(row['anomaly_count'])} signals and "
            f"{money_inr(row['money_at_risk'])} in known exposure. "
            "Validate source records before taking action."
        )

if unquantified_records > 0:
    recommendations.append(
        f"Investigate the {unquantified_records} anomaly records without "
        "a money-at-risk estimate; do not interpret missing estimates as zero."
    )

recommendations.append(
    "Revisit forecast performance after October 2026 actuals are loaded; "
    "then calculate forecast error against the stored predictions."
)

recommendations.append(
    "Use attrition-risk bands only as aggregated HR review prompts, "
    "with human context and appropriate safeguards."
)

for i, recommendation in enumerate(recommendations, start=1):
    st.markdown(f"**{i}.** {recommendation}")

st.divider()

st.subheader("Data coverage and model limitations")
st.markdown(
    f"""
    - Anomaly source records: **{len(anomaly):,}**
    - Forecast records: **{len(forecast):,}**
    - Attrition-risk records: **{len(risk):,}**
    - Historical headcount records: **{len(headcount):,}**
    - Historical actuals end: **{latest_actual_date:%d %B %Y}**
    - Forecast horizon: **{first_forecast_date:%B %Y} to {last_forecast_date:%B %Y}**
    - Forecast/actual overlapping months: **{len(error_table)} for the selected metric and scope**
    - Forecast ranges and model outputs are supplied source values; this dashboard
      does not retrain the model or independently validate its predictive quality.
    """
)

st.caption(
    "PulseIQ · Phase 3 · Task 14 · AI Signals Dashboard · "
    "AI outputs require human review."
)
