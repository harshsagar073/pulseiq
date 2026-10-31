from pathlib import Path
import duckdb

DB = Path("/Users/admin/Desktop/PulseIQ/Phase 1/Task 4/pulseiq_task4.duckdb")
OUT = Path("verification")
OUT.mkdir(exist_ok=True)

teams = {
    "T01": ("Platform Core", 35),
    "T12": ("Support Tooling", 58),
}

sql = """
WITH selected_teams(team_id, team_name, active_members) AS (
    VALUES
        ('T01', 'Platform Core', 35),
        ('T12', 'Support Tooling', 58)
),
team_sprint AS (
    SELECT
        t.team_id,
        t.team_name,
        t.active_members,
        s.sprint_id,
        COUNT(f.task_id) AS total_tasks,
        COUNT(*) FILTER (WHERE f.status = 'Done') AS completed_tasks,
        SUM(CASE WHEN f.status = 'Done'
                 THEN COALESCE(f.story_points, 0) ELSE 0 END) AS story_points,
        SUM(CASE WHEN f.status = 'Done'
                  AND f.cycle_time_days >= 0
                 THEN f.cycle_time_days ELSE 0 END) AS cycle_time_sum,
        COUNT(*) FILTER (
            WHERE f.status = 'Done' AND f.cycle_time_days >= 0
        ) AS valid_cycle_tasks,
        COUNT(*) FILTER (
            WHERE f.status = 'Done' AND f.completed_on_time = 'Y'
        ) AS on_time_tasks,
        COUNT(*) FILTER (
            WHERE f.status = 'Done' AND f.completed_on_time = 'N'
        ) AS late_tasks,
        COUNT(*) FILTER (WHERE f.status = 'Blocked') AS blocked_tasks,
        COUNT(*) FILTER (
            WHERE COALESCE(f.reopened_count, 0) > 0
        ) AS reopened_tasks,
        SUM(COALESCE(f.reopened_count, 0)) AS reopen_events,
        COUNT(*) FILTER (WHERE f.status = 'Cancelled') AS cancelled_tasks
    FROM selected_teams t
    CROSS JOIN raw.dim_sprint s
    LEFT JOIN raw.fact_task f
        ON f.team_id = t.team_id
       AND f.sprint_id = s.sprint_id
    GROUP BY t.team_id, t.team_name, t.active_members, s.sprint_id
)
SELECT
    team_id,
    team_name,
    active_members,
    SUM(total_tasks) AS total_tasks,
    SUM(completed_tasks) AS completed_tasks,
    SUM(story_points) AS completed_story_points,
    ROUND(SUM(story_points) / (active_members * COUNT(*)), 2)
        AS avg_normalized_sprint_velocity,
    ROUND(SUM(cycle_time_sum) / NULLIF(SUM(valid_cycle_tasks), 0), 2)
        AS avg_cycle_time_days,
    SUM(valid_cycle_tasks) AS valid_cycle_time_tasks,
    SUM(on_time_tasks) AS on_time_tasks,
    SUM(late_tasks) AS late_tasks,
    ROUND(
        100.0 * SUM(on_time_tasks)
        / NULLIF(SUM(on_time_tasks) + SUM(late_tasks), 0), 2
    ) AS on_time_rate_pct,
    SUM(blocked_tasks) AS blocked_tasks,
    SUM(reopened_tasks) AS reopened_tasks,
    SUM(reopen_events) AS reopen_events,
    SUM(cancelled_tasks) AS cancelled_tasks
FROM team_sprint
GROUP BY team_id, team_name, active_members
ORDER BY team_id
"""

con = duckdb.connect(str(DB), read_only=True)

try:
    result = con.execute(sql).df()
finally:
    con.close()

(OUT / "manual_verification.sql").write_text(sql.strip() + "\n")
result.to_csv(OUT / "manual_verification_results.csv", index=False)

report = [
    "PULSEIQ PHASE 2 - TASK 8",
    "MANUAL TEAM METRIC VERIFICATION",
    "=" * 55,
    "Source: Phase 1 / Task 4 governed DuckDB warehouse",
    "Method: Independent aggregation from raw.fact_task",
    "Sprint coverage: All sprints in raw.dim_sprint",
    "Source database opened in read-only mode.",
    "",
]

for _, r in result.iterrows():
    report += [
        f"TEAM: {r['team_name']} ({r['team_id']})",
        "-" * 45,
        f"Active members: {int(r['active_members'])}",
        f"Total tasks: {int(r['total_tasks'])}",
        f"Completed tasks: {int(r['completed_tasks'])}",
        f"Completed story points: {int(r['completed_story_points'])}",
        f"Average normalized sprint velocity: {r['avg_normalized_sprint_velocity']}",
        f"Valid cycle-time tasks: {int(r['valid_cycle_time_tasks'])}",
        f"Average cycle time (days): {r['avg_cycle_time_days']}",
        f"On-time tasks: {int(r['on_time_tasks'])}",
        f"Late tasks: {int(r['late_tasks'])}",
        f"On-time rate (%): {r['on_time_rate_pct']}",
        f"Blocked tasks: {int(r['blocked_tasks'])}",
        f"Reopened tasks: {int(r['reopened_tasks'])}",
        f"Reopen events: {int(r['reopen_events'])}",
        f"Cancelled tasks: {int(r['cancelled_tasks'])}",
        "",
    ]

report += [
    "VERIFICATION RULES",
    "-" * 45,
    "Completed delivery: status = Done.",
    "Velocity: sum of story points for Done tasks.",
    "Normalized velocity: completed story points divided by active members and 38 sprints.",
    "Cycle time: Done tasks with non-negative cycle_time_days; missing values excluded.",
    "On-time rate: Y / (Y + N) among Done tasks.",
    "Blocked: current status = Blocked.",
    "Reopened tasks: reopened_count > 0.",
    "Reopen events: sum of reopened_count.",
    "Cancelled tasks are reported separately and excluded from delivery metrics.",
    "",
    "This report is an independent raw-table calculation for two teams.",
]

(OUT / "manual_verification_report.txt").write_text("\n".join(report))

print("\n".join(report))
print("\nSUCCESS: SQL, CSV results and text verification report saved.")
