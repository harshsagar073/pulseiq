import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px
from pathlib import Path

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------

st.set_page_config(
    page_title="PulseIQ | Team Productivity",
    page_icon="📊",
    layout="wide"
)

DB_PATH = (
    Path(__file__).resolve().parents[2]
    / "Phase 1"
    / "Task 4"
    / "pulseiq_task4.duckdb"
)

SQL_PATH = Path(__file__).parent / "sql" / "team_productivity_views.sql"

# --------------------------------------------------
# DATABASE
# --------------------------------------------------

@st.cache_resource
def get_connection():
    con = duckdb.connect(str(DB_PATH), read_only=True)
    con.execute(SQL_PATH.read_text())
    return con


con = get_connection()


@st.cache_data
def load_data():
    teams = con.execute("""
        SELECT *
        FROM v_team_overall_productivity
        ORDER BY team_id
    """).df()

    sprint = con.execute("""
        SELECT *
        FROM v_sprint_productivity
        ORDER BY start_date
    """).df()

    team_sprint = con.execute("""
        SELECT *
        FROM v_team_sprint_productivity
        ORDER BY start_date, team_id
    """).df()

    return teams, sprint, team_sprint


teams, sprints, team_sprint = load_data()

# --------------------------------------------------
# HEADER
# --------------------------------------------------

st.title("📊 PulseIQ | Team Productivity Dashboard")

st.markdown(
    "Measure team delivery, sprint velocity, cycle time, "
    "on-time performance and delivery quality."
)

st.caption(
    "Phase 2 | Task 8 | Source: Task 4 governed warehouse | "
    "16 Teams | 38 Sprints | 28,868 Tasks"
)

st.divider()

# --------------------------------------------------
# SIDEBAR FILTERS
# --------------------------------------------------

st.sidebar.title("Dashboard Filters")

sprint_options = ["All Sprints"] + sprints["sprint_name"].tolist()

selected_sprint = st.sidebar.selectbox(
    "Select Sprint",
    sprint_options
)

team_options = ["All Teams"] + teams["team_name"].tolist()

selected_team = st.sidebar.selectbox(
    "Select Team",
    team_options
)

if selected_sprint == "All Sprints":
    sprint_data = team_sprint.copy()
    sprint_summary = sprints.copy()
else:
    sprint_data = team_sprint[
        team_sprint["sprint_name"] == selected_sprint
    ].copy()

    sprint_summary = sprints[
        sprints["sprint_name"] == selected_sprint
    ].copy()

if selected_team != "All Teams":
    sprint_data = sprint_data[
        sprint_data["team_name"] == selected_team
    ]

    overall = teams[
        teams["team_name"] == selected_team
    ].copy()
else:
    overall = teams.copy()

# --------------------------------------------------
# KPI SECTION
# --------------------------------------------------

if selected_sprint == "All Sprints":
    total_completed = int(teams["completed_tasks"].sum())
    total_points = int(teams["total_completed_story_points"].sum())
    blocked = int(teams["blocked_tasks"].sum())
    reopened = int(teams["reopened_tasks"].sum())

    on_time = (
        teams["on_time_tasks"].sum()
        / max(teams["on_time_eligible_tasks"].sum(), 1)
    ) * 100

    cycle = con.execute("""
        SELECT ROUND(
            SUM(cycle_time_sum_days)
            / NULLIF(SUM(valid_cycle_time_tasks), 0), 2
        )
        FROM v_team_sprint_productivity
    """).fetchone()[0]

else:
    total_completed = int(sprint_summary["completed_tasks"].sum())
    total_points = int(sprint_summary["completed_story_points"].sum())
    blocked = int(sprint_summary["blocked_tasks"].sum())
    reopened = int(sprint_summary["reopened_tasks"].sum())
    on_time = float(sprint_summary["on_time_rate_pct"].iloc[0])

    cycle = float(
        sprint_summary["avg_team_cycle_time_days"].iloc[0]
    )

st.subheader("Delivery Overview")

k1, k2, k3, k4, k5, k6 = st.columns(6)

k1.metric("Completed Tasks", f"{total_completed:,}")
k2.metric("Story Points", f"{total_points:,}")
k3.metric("On-Time Rate", f"{on_time:.2f}%")
k4.metric("Avg Cycle Time", f"{cycle:.2f} days")
k5.metric("Blocked Tasks", f"{blocked:,}")
k6.metric("Reopened Tasks", f"{reopened:,}")

st.divider()

# --------------------------------------------------
# TEAM VELOCITY
# --------------------------------------------------

st.subheader("1. Team Velocity Comparison")

velocity_chart = px.bar(
    sprint_data,
    x="team_name",
    y="velocity_per_member",
    color="team_name",
    hover_data=[
        "active_members",
        "completed_tasks",
        "completed_story_points"
    ],
    labels={
        "team_name": "Team",
        "velocity_per_member": "Story Points per Active Member"
    },
    title="Normalized Sprint Velocity by Team"
)

velocity_chart.update_layout(
    showlegend=False,
    xaxis_tickangle=-35
)

st.plotly_chart(velocity_chart, use_container_width=True)

# --------------------------------------------------
# ON TIME RATE
# --------------------------------------------------

st.subheader("2. On-Time Delivery Performance")

ontime_chart = px.bar(
    sprint_data,
    x="team_name",
    y="on_time_rate_pct",
    color="on_time_rate_pct",
    color_continuous_scale="RdYlGn",
    hover_data=["on_time_tasks", "late_tasks"],
    labels={
        "team_name": "Team",
        "on_time_rate_pct": "On-Time Rate (%)"
    }
)

ontime_chart.update_layout(xaxis_tickangle=-35)

st.plotly_chart(ontime_chart, use_container_width=True)

# --------------------------------------------------
# BLOCKED AND REOPENED WORK
# --------------------------------------------------

st.subheader("3. Blocked and Reopened Work")

quality_col1, quality_col2 = st.columns(2)

with quality_col1:
    blocked_chart = px.bar(
        sprint_data,
        x="team_name",
        y="blocked_tasks",
        title="Blocked Tasks by Team",
        color="blocked_tasks",
        color_continuous_scale="Reds"
    )

    blocked_chart.update_layout(xaxis_tickangle=-35)
    st.plotly_chart(blocked_chart, use_container_width=True)

with quality_col2:
    reopened_chart = px.bar(
        sprint_data,
        x="team_name",
        y="reopened_tasks",
        title="Reopened Tasks by Team",
        color="reopened_tasks",
        color_continuous_scale="Oranges"
    )

    reopened_chart.update_layout(xaxis_tickangle=-35)
    st.plotly_chart(reopened_chart, use_container_width=True)

# --------------------------------------------------
# SPRINT TRENDS
# --------------------------------------------------

st.subheader("4. Sprint Performance Trends")

trend_col1, trend_col2 = st.columns(2)

with trend_col1:
    fig = px.line(
        sprints,
        x="sprint_name",
        y="completed_story_points",
        markers=True,
        title="Completed Story Points per Sprint"
    )

    st.plotly_chart(fig, use_container_width=True)

with trend_col2:
    fig = px.line(
        sprints,
        x="sprint_name",
        y="on_time_rate_pct",
        markers=True,
        title="Sprint On-Time Delivery Trend"
    )

    st.plotly_chart(fig, use_container_width=True)

# --------------------------------------------------
# TEAM DETAIL
# --------------------------------------------------

st.subheader("5. Team Performance Details")

st.dataframe(
    overall[
        [
            "team_id",
            "team_name",
            "active_members",
            "total_tasks",
            "completed_tasks",
            "total_completed_story_points",
            "avg_sprint_velocity_per_member",
            "avg_cycle_time_days",
            "on_time_rate_pct",
            "blocked_tasks",
            "reopened_tasks",
            "reopen_events"
        ]
    ].round(2),
    use_container_width=True,
    hide_index=True
)

# --------------------------------------------------
# SPRINT SELECTOR DETAIL
# --------------------------------------------------

st.subheader("6. Selected Sprint Details")

st.dataframe(
    sprint_data[
        [
            "team_name",
            "sprint_name",
            "completed_tasks",
            "completed_story_points",
            "velocity_per_member",
            "avg_cycle_time_days",
            "on_time_rate_pct",
            "blocked_tasks",
            "reopened_tasks",
            "cancelled_tasks"
        ]
    ].round(2),
    use_container_width=True,
    hide_index=True
)

# --------------------------------------------------
# AUTOMATIC FINDINGS
# --------------------------------------------------

st.subheader("7. Team Health Findings")

highest_velocity = teams.loc[
    teams["avg_sprint_velocity_per_member"].idxmax()
]

best_ontime = teams.loc[
    teams["on_time_rate_pct"].idxmax()
]

highest_blocked = teams.loc[
    teams["blocked_tasks"].idxmax()
]

highest_reopened = teams.loc[
    teams["reopened_tasks"].idxmax()
]

st.markdown(
    f"""
    **Finding 1 – Velocity:** {highest_velocity['team_name']}
    has the highest average normalized sprint velocity of
    **{highest_velocity['avg_sprint_velocity_per_member']:.2f}
    story points per member per sprint**.

    **Finding 2 – Delivery reliability:** {best_ontime['team_name']}
    leads on-time delivery at
    **{best_ontime['on_time_rate_pct']:.2f}%**.

    **Finding 3 – Work blockage:** {highest_blocked['team_name']}
    has the highest blocked workload with
    **{int(highest_blocked['blocked_tasks']):,} blocked tasks**.
    {highest_reopened['team_name']} has the most reopened tasks:
    **{int(highest_reopened['reopened_tasks']):,}**.
    """
)

# --------------------------------------------------
# BUSINESS RULES
# --------------------------------------------------

with st.expander("Metric Definitions and Business Rules", expanded=True):

    st.markdown("""
    | Metric | Business Rule |
    |---|---|
    | Velocity | Sum of story points for tasks with Done status |
    | Normalized Velocity | Completed story points divided by active team members |
    | Cycle Time | Average valid, non-negative cycle time for Done tasks |
    | On-Time Rate | Y classifications divided by all Y and N classifications among Done tasks |
    | Blocked Work | Tasks currently marked Blocked |
    | Reopened Work | Tasks with reopened_count greater than zero |
    | Reopen Events | Sum of reopened_count |
    | Cancelled Tasks | Excluded from delivery metrics and displayed separately |

    **Cancelled task treatment:** Cancelled tasks are excluded from
    velocity, cycle time and on-time delivery. They remain visible
    in task counts and cancellation reporting.

    **Cycle-time quality:** Negative cycle times are invalid and
    excluded. Missing cycle times are excluded from the average.
    Zero cycle times are retained if present.

    **On-time quality:** Tasks without Y/N classification are
    excluded from the on-time denominator.

    **Fair team comparison:** Team size is considered using
    normalized velocity. Team work type and sprint length should
    also be considered before making management decisions.
    """)

    st.info(
        "Source database is connected in read-only mode. "
        "Cancelled tasks are not counted as completed delivery."
    )

st.caption(
    "PulseIQ | Phase 2 - Task 8 | Team Productivity Analytics"
)
