from pathlib import Path
import json
import pandas as pd
import streamlit as st

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"

@st.cache_data
def load_explorer_data():
    company = pd.read_csv(DATA / "company_month.csv", parse_dates=["month"])
    department = pd.read_csv(DATA / "department_month.csv", parse_dates=["month"])
    teams = pd.read_csv(DATA / "team_sprint.csv")
    users = pd.read_csv(DATA / "demo_users.csv")
    dictionary = json.loads((DATA / "metric_dictionary.json").read_text())
    return company, department, teams, users, dictionary

company, department, teams, users, dictionary = load_explorer_data()

st.header("🔎 Self-service KPI Explorer")
st.write(
    "Explore approved company, department and team metrics. "
    "Small groups are suppressed to protect employee privacy."
)
st.warning(
    "DEMO ROLE SIMULATION ONLY — selecting a role does not authenticate "
    "a person. This public demonstration is not production role-based access control."
)

role_labels = {
    "ADMIN": "Administrator",
    "HR": "HR",
    "MANAGER": "Manager",
    "EXECUTIVE": "Executive",
}
role = st.selectbox(
    "Demonstration user role",
    list(role_labels),
    format_func=lambda value: role_labels[value],
)
demo_user = users.loc[users["role"] == role].iloc[0]

st.caption(
    f"Demo account: {demo_user['user_id']} | Role: {role}"
)

workforce = {
    "Headcount": ("headcount_end", "employees"),
    "Hires": ("hires", "employees"),
    "Exits": ("exits", "employees"),
    "Monthly attrition rate": ("attrition_pct", "%"),
    "Payroll cost": ("employer_cost", "INR"),
    "Cost per head": ("cost_per_head", "INR"),
    "Overtime share": ("overtime_share_pct", "%"),
    "Attendance rate": ("attendance_pct", "%"),
    "Late arrival rate": ("late_arrival_pct", "%"),
}
productivity = {
    "Task completion rate": ("completion_pct", "%"),
    "On-time delivery": ("on_time_pct", "%"),
    "Velocity": ("story_points_done", "points"),
    "Average cycle time": ("average_cycle_time", "days"),
}

if role == "ADMIN":
    allowed = list(workforce) + list(productivity)
    dimensions = ["Company", "Department", "Team"]
elif role == "HR":
    allowed = [
        "Headcount", "Hires", "Exits", "Monthly attrition rate",
        "Attendance rate", "Late arrival rate",
    ] + list(productivity)
    dimensions = ["Company", "Department", "Team"]
elif role == "MANAGER":
    allowed = list(productivity)
    dimensions = ["Team"]
else:
    allowed = [
        "Headcount", "Hires", "Exits", "Monthly attrition rate",
        "Payroll cost", "Cost per head", "Overtime share",
        "Attendance rate", "Late arrival rate",
    ]
    dimensions = ["Company", "Department"]

metric = st.selectbox("Choose a metric", allowed)
if metric in workforce:
    dimension_options = ["Company", "Department"]
else:
    dimension_options = ["Team"]
dimension = st.selectbox("Choose a dimension", dimension_options)

st.caption(
    "Privacy rule: employee-derived department groups require at least "
    "10 people. Team productivity groups require at least 10 distinct assignees."
)

if dimension in ("Company", "Department"):
    month_values = sorted(company["month"].dropna().unique())
    selected_month = st.selectbox(
        "Reporting month",
        month_values,
        index=len(month_values) - 1,
        format_func=lambda value: pd.Timestamp(value).strftime("%B %Y"),
    )

    if metric not in workforce:
        st.info("This metric is available only at team/sprint level.")
    elif dimension == "Company":
        record = company.loc[company["month"] == selected_month]
        if record.empty:
            st.warning("No company aggregate is available for this month.")
        else:
            value_column, unit = workforce[metric]
            value = record.iloc[0][value_column]
            if pd.isna(value):
                st.info("This metric is unavailable for the selected period.")
            elif unit == "INR":
                st.metric(metric, f"₹{value:,.2f}")
            elif unit == "%":
                st.metric(metric, f"{value:.2f}%")
            else:
                st.metric(metric, f"{value:,.0f}")
            st.caption("Company aggregate. Department-level suppressed groups are not displayed here.")

    else:
        value_column, unit = workforce[metric]
        view = department.loc[department["month"] == selected_month].copy()
        names = {
            "D00": "Executive Office",
            "D01": "Engineering",
            "D02": "Product",
            "D03": "Data",
            "D04": "Sales",
            "D05": "Marketing",
            "D06": "Customer Support",
            "D07": "Human Resources",
            "D08": "Finance",
            "D09": "IT",
            "D10": "Operations",
        }
        view["Department"] = view["department_id"].map(names).fillna("Department")
        view = view[["Department", value_column]].rename(
            columns={value_column: metric}
        )
        if view.empty:
            st.warning("No department data is available for this month.")
        else:
            st.dataframe(view, use_container_width=True, hide_index=True)
            st.caption(
                "Only departments that pass the privacy rule are shown. "
                "Two or more groups may be hidden to prevent subtraction attacks. "
                "No company total is shown alongside this breakdown."
            )
            if unit == "INR":
                st.caption("Currency values are in INR.")

else:
    value_column, unit = productivity[metric]
    view = teams.copy()

    if role == "MANAGER":
        assigned_team = str(demo_user["team_id"])
        view = view.loc[view["team_id"] == assigned_team]
        st.caption(f"Manager scope: assigned team {assigned_team} only.")

    if view.empty:
        st.warning("No team data is available within this role's scope.")
    else:
        sprint_values = sorted(view["sprint_id"].dropna().astype(str).unique())
        selected_sprint = st.selectbox("Choose sprint", sprint_values)
        view = view.loc[view["sprint_id"].astype(str) == selected_sprint]

        team_options = view[["team_id", "team_name"]].drop_duplicates()
        selected_team = st.selectbox(
            "Choose one team",
            team_options["team_id"].tolist(),
            format_func=lambda team_id: (
                team_options.loc[
                    team_options["team_id"] == team_id, "team_name"
                ].iloc[0]
            ),
        )
        selected = view.loc[view["team_id"] == selected_team]

        if selected.empty:
            st.warning("No data for this team and sprint.")
        else:
            record = selected.iloc[0]
            count = int(record["distinct_assignees"])
            if count < 10:
                st.info(
                    "This team is hidden because it does not meet the "
                    "minimum group-size requirement of 10."
                )
            else:
                value = record[value_column]
                if pd.isna(value):
                    st.info("This metric is unavailable for the selected team/sprint.")
                elif unit == "%":
                    st.metric(metric, f"{value:.2f}%")
                elif unit == "points":
                    st.metric(metric, f"{value:,.1f}")
                else:
                    st.metric(metric, f"{value:.2f} days")
                st.caption(
                    f"Team group size: {count} distinct task assignees. "
                    "Velocity is shown for one selected team only and must not "
                    "be used to rank or compare teams."
                )

st.divider()
with st.expander("Role permissions and privacy decisions"):
    st.markdown("""
    | Role | Permitted view |
    |---|---|
    | ADMIN | Company, department and team metrics |
    | HR | Workforce metrics and team productivity |
    | MANAGER | Assigned team productivity only |
    | EXECUTIVE | Company and department aggregates |

    **Privacy decisions**
    - Employee-derived groups below 10 are suppressed.
    - Department breakdowns use complementary suppression.
    - Team payroll and team attrition are not offered because the source data
      does not reliably support those metrics at team level.
    - Managers do not see attrition for a team of three. The group is too small,
      and team-level attrition is not supported by the available source data.
    - Velocity is displayed for one selected team only, not as a team ranking.
    - The role selector is a demonstration, not authentication.
    """)
