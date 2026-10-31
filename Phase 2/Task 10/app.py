from pathlib import Path
import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st

BASE = Path(__file__).resolve().parent
DB = BASE / "pulseiq_task10.duckdb"

st.set_page_config(
    page_title="PulseIQ | Budget vs Actual",
    page_icon="📊",
    layout="wide"
)

st.title("PulseIQ — Budget vs Actual & KPI Targets")
st.caption("Phase 2 · Task 10 | April 2025 – September 2026")

if not DB.exists():
    st.error("Database missing. Run python build_task10.py first.")
    st.stop()


@st.cache_data
def load_data():
    con = duckdb.connect(str(DB), read_only=True)
    budget = con.execute(
        "SELECT * FROM budget_actual ORDER BY month, department_id"
    ).fetchdf()
    kpi = con.execute(
        "SELECT * FROM kpi_performance ORDER BY month, department_id"
    ).fetchdf()
    con.close()

    budget["month"] = pd.to_datetime(budget["month"])
    kpi["month"] = pd.to_datetime(kpi["month"])
    return budget, kpi


budget, kpi = load_data()

months = sorted(budget["month"].dropna().unique())
month_labels = {"All months": None}
month_labels.update({
    pd.Timestamp(m).strftime("%b %Y"): pd.Timestamp(m)
    for m in months
})

with st.sidebar:
    st.header("Filters")
    selected_label = st.selectbox(
        "Reporting period", list(month_labels.keys())
    )
    selected_month = month_labels[selected_label]

    departments = sorted(budget["department_name"].dropna().unique())
    selected_departments = st.multiselect(
        "Departments", departments, default=departments
    )

b = budget[budget["department_name"].isin(selected_departments)].copy()
k = kpi[kpi["department_name"].isin(selected_departments)].copy()

if selected_month is not None:
    b = b[b["month"] == selected_month]
    k = k[k["month"] == selected_month]


def money(value):
    if pd.isna(value):
        return "—"
    return f"₹{value:,.0f}"


actual = b["actual_payroll_cost"].sum(min_count=1)
planned = b["budget_payroll_cost"].sum(min_count=1)
variance = actual - planned if pd.notna(actual) and pd.notna(planned) else None
variance_pct = (
    variance / planned * 100
    if variance is not None and planned
    else None
)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Actual employer cost", money(actual))
c2.metric("Budget", money(planned))
c3.metric(
    "Net variance",
    money(variance),
    None if variance_pct is None else f"{variance_pct:+.2f}%"
)
c4.metric(
    "Over-budget department-months",
    int((b["variance_amount"] > 0).sum())
)

st.info(
    "Variance = actual employer cost − budget. "
    "Positive means overspend; negative means underspend. "
    "Payroll excludes PI-X0001, PI-X0002, PI-X0003 and PI-X0004, "
    "consistent with Task 9."
)

st.subheader("Budget versus actual by department")

if not b.empty:
    chart = b.groupby("department_name", as_index=False)[
        ["budget_payroll_cost", "actual_payroll_cost"]
    ].sum()

    chart = chart.melt(
        id_vars="department_name",
        var_name="series",
        value_name="amount"
    )

    chart["series"] = chart["series"].map({
        "budget_payroll_cost": "Budget",
        "actual_payroll_cost": "Actual employer cost"
    })

    fig = px.bar(
        chart,
        x="department_name",
        y="amount",
        color="series",
        barmode="group"
    )
    fig.update_layout(
        xaxis_title="Department",
        yaxis_title="Amount (₹)",
        legend_title=""
    )
    st.plotly_chart(fig, use_container_width=True)

    display = b.copy()
    display["month"] = display["month"].dt.strftime("%b %Y")
    st.dataframe(
        display[[
            "month", "department_id", "department_name",
            "budget_payroll_cost", "actual_payroll_cost",
            "variance_amount", "variance_pct", "budget_status"
        ]],
        use_container_width=True,
        hide_index=True
    )

st.subheader("Department overspend ranking")

rank = budget.groupby(
    ["department_id", "department_name"], as_index=False
).agg(
    gross_overspend=(
        "variance_amount",
        lambda x: x.clip(lower=0).sum()
    ),
    net_variance=("variance_amount", "sum"),
    over_budget_months=(
        "variance_amount",
        lambda x: int((x > 0).sum())
    )
).sort_values("gross_overspend", ascending=False)

rank = rank[rank["department_name"].isin(selected_departments)]
rank.insert(0, "rank", range(1, len(rank) + 1))

st.caption(
    "Gross overspend adds only positive monthly variances. "
    "Net variance offsets underspend months against overspend months."
)
st.dataframe(rank, use_container_width=True, hide_index=True)

st.subheader("KPI target scorecard")

metric_options = {
    "Attendance": (
        "attendance_actual", "attendance_rate_target",
        "attendance_status", True
    ),
    "Overtime share": (
        "overtime_actual_pct", "overtime_share_target_pct",
        "overtime_status", False
    ),
    "Monthly attrition": (
        "attrition_actual_pct", "attrition_monthly_target_pct",
        "attrition_status", False
    ),
    "Task completion": (
        "task_completion_actual_pct", "task_completion_target_pct",
        "task_completion_status", False
    )
}

metric = st.selectbox("Select KPI", list(metric_options.keys()))
actual_col, target_col, status_col, is_ratio = metric_options[metric]

view = k[[
    "month", "department_id", "department_name",
    actual_col, target_col, status_col
]].copy()

view["month"] = view["month"].dt.strftime("%b %Y")

if is_ratio:
    view[actual_col] = view[actual_col] * 100
    view[target_col] = view[target_col] * 100

view = view.rename(columns={
    actual_col: "Actual (%)",
    target_col: "Target (%)",
    status_col: "Traffic light"
})

st.dataframe(view, use_container_width=True, hide_index=True)

counts = k[status_col].value_counts().reindex(
    ["GREEN", "RED", "AMBER"], fill_value=0
)

g, r, a = st.columns(3)
g.metric("Green — target met", int(counts["GREEN"]))
r.metric("Red — target missed", int(counts["RED"]))
a.metric("Amber — unavailable", int(counts["AMBER"]))

st.subheader("Top two departments to review")

for row in rank.head(2).itertuples(index=False):
    st.markdown(
        f"**{row.department_name} ({row.department_id})**"
    )
    st.write(
        f"Gross overspend: {money(row.gross_overspend)} | "
        f"Net variance: {money(row.net_variance)} | "
        f"Over-budget months: {row.over_budget_months}"
    )
    st.write(
        "Recommended action: reconcile paid headcount and employer-cost "
        "components against the approved budget. Check hiring-freeze timing, "
        "approved exceptions, vacancies, backfills and one-off payments "
        "before proposing cost reductions."
    )

st.warning(
    "Budget freshness caveat: the budget may not have been refreshed after "
    "the hiring freeze. Treat overspend rankings as review priorities, not "
    "proof of avoidable spending. Validate the approved headcount plan and "
    "authorized exceptions before taking action."
)

st.subheader("Manual verification")

verification_file = BASE / "verification" / "manual_verification.csv"

if verification_file.exists():
    st.success("Three manual verification examples are available.")
    st.dataframe(
        pd.read_csv(verification_file),
        use_container_width=True,
        hide_index=True
    )
else:
    st.warning("Run python verify_task10.py to generate manual checks.")

st.caption(
    "Traffic lights: green = target met; red = target missed; "
    "amber = actual or target unavailable/suppressed. "
    "Attendance and task completion are higher-is-better; "
    "overtime and attrition are lower-is-better."
)
