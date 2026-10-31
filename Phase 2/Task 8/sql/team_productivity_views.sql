
-- ============================================================
-- PULSEIQ PHASE 2 - TASK 8
-- TEAM PRODUCTIVITY METRIC LAYER
-- Source: Phase 1 / Task 4 warehouse
-- All views are TEMPORARY. Source database remains unchanged.
-- ============================================================

-- 1. Team and sprint productivity
CREATE OR REPLACE TEMP VIEW v_team_sprint_productivity AS

WITH task_metrics AS (

    SELECT
        team_id,
        sprint_id,

        COUNT(*) AS total_tasks,

        COUNT(*) FILTER (
            WHERE status = 'Done'
        ) AS completed_tasks,

        COALESCE(
            SUM(story_points) FILTER (
                WHERE status = 'Done'
            ), 0
        ) AS completed_story_points,

        COUNT(*) FILTER (
            WHERE status = 'Done'
              AND cycle_time_days >= 0
        ) AS valid_cycle_time_tasks,

        SUM(cycle_time_days) FILTER (
            WHERE status = 'Done'
              AND cycle_time_days >= 0
        ) AS cycle_time_sum_days,

        AVG(cycle_time_days) FILTER (
            WHERE status = 'Done'
              AND cycle_time_days >= 0
        ) AS avg_cycle_time_days,

        COUNT(*) FILTER (
            WHERE status = 'Done'
              AND cycle_time_days < 0
        ) AS invalid_cycle_time_tasks,

        COUNT(*) FILTER (
            WHERE status = 'Done'
              AND completed_on_time = 'Y'
        ) AS on_time_tasks,

        COUNT(*) FILTER (
            WHERE status = 'Done'
              AND completed_on_time = 'N'
        ) AS late_tasks,

        COUNT(*) FILTER (
            WHERE status = 'Done'
              AND completed_on_time IN ('Y', 'N')
        ) AS on_time_eligible_tasks,

        COUNT(*) FILTER (
            WHERE status = 'Blocked'
        ) AS blocked_tasks,

        COUNT(*) FILTER (
            WHERE status = 'Cancelled'
        ) AS cancelled_tasks,

        COUNT(*) FILTER (
            WHERE reopened_count > 0
        ) AS reopened_tasks,

        COALESCE(SUM(reopened_count), 0) AS reopen_events,

        COUNT(*) FILTER (
            WHERE status = 'Done'
              AND reopened_count > 0
        ) AS reopened_completed_tasks

    FROM raw.fact_task
    GROUP BY team_id, sprint_id
)

SELECT
    t.team_id,
    t.team_name,
    t.active_members,

    s.sprint_id,
    s.sprint_name,
    s.start_date,
    s.end_date,
    s.working_days,
    s.financial_year,

    COALESCE(m.total_tasks, 0) AS total_tasks,
    COALESCE(m.completed_tasks, 0) AS completed_tasks,

    COALESCE(m.completed_story_points, 0)
        AS completed_story_points,

    ROUND(
        COALESCE(m.completed_story_points, 0)::DOUBLE
        / NULLIF(t.active_members, 0),
        2
    ) AS velocity_per_member,

    m.avg_cycle_time_days,
    m.cycle_time_sum_days,
    COALESCE(m.valid_cycle_time_tasks, 0)
        AS valid_cycle_time_tasks,

    COALESCE(m.invalid_cycle_time_tasks, 0)
        AS invalid_cycle_time_tasks,

    COALESCE(m.on_time_tasks, 0) AS on_time_tasks,
    COALESCE(m.late_tasks, 0) AS late_tasks,

    COALESCE(m.on_time_eligible_tasks, 0)
        AS on_time_eligible_tasks,

    ROUND(
        100.0 * COALESCE(m.on_time_tasks, 0)
        / NULLIF(m.on_time_eligible_tasks, 0),
        2
    ) AS on_time_rate_pct,

    COALESCE(m.blocked_tasks, 0) AS blocked_tasks,
    COALESCE(m.cancelled_tasks, 0) AS cancelled_tasks,

    COALESCE(m.reopened_tasks, 0) AS reopened_tasks,
    COALESCE(m.reopen_events, 0) AS reopen_events,

    COALESCE(m.reopened_completed_tasks, 0)
        AS reopened_completed_tasks,

    ROUND(
        100.0 * COALESCE(m.blocked_tasks, 0)
        / NULLIF(
            COALESCE(m.total_tasks, 0)
            - COALESCE(m.cancelled_tasks, 0),
            0
        ),
        2
    ) AS blocked_rate_pct

FROM raw.dim_team t

CROSS JOIN raw.dim_sprint s

LEFT JOIN task_metrics m
    ON t.team_id = m.team_id
   AND s.sprint_id = m.sprint_id;


-- 2. Overall team productivity across all sprints

CREATE OR REPLACE TEMP VIEW v_team_overall_productivity AS

SELECT
    team_id,
    team_name,
    active_members,

    SUM(total_tasks) AS total_tasks,
    SUM(completed_tasks) AS completed_tasks,

    SUM(completed_story_points)
        AS total_completed_story_points,

    ROUND(
        AVG(velocity_per_member),
        2
    ) AS avg_sprint_velocity_per_member,

    ROUND(
        SUM(cycle_time_sum_days)
        / NULLIF(SUM(valid_cycle_time_tasks), 0),
        2
    ) AS avg_cycle_time_days,

    SUM(valid_cycle_time_tasks)
        AS valid_cycle_time_tasks,

    SUM(invalid_cycle_time_tasks)
        AS invalid_cycle_time_tasks,

    SUM(on_time_tasks) AS on_time_tasks,
    SUM(late_tasks) AS late_tasks,

    SUM(on_time_eligible_tasks)
        AS on_time_eligible_tasks,

    ROUND(
        100.0 * SUM(on_time_tasks)
        / NULLIF(SUM(on_time_eligible_tasks), 0),
        2
    ) AS on_time_rate_pct,

    SUM(blocked_tasks) AS blocked_tasks,
    SUM(cancelled_tasks) AS cancelled_tasks,

    SUM(reopened_tasks) AS reopened_tasks,
    SUM(reopen_events) AS reopen_events,

    SUM(reopened_completed_tasks)
        AS reopened_completed_tasks,

    ROUND(
        100.0 * SUM(blocked_tasks)
        / NULLIF(
            SUM(total_tasks) - SUM(cancelled_tasks),
            0
        ),
        2
    ) AS blocked_rate_pct

FROM v_team_sprint_productivity

GROUP BY
    team_id,
    team_name,
    active_members;


-- 3. Sprint-level comparison across all teams

CREATE OR REPLACE TEMP VIEW v_sprint_productivity AS

SELECT
    sprint_id,
    sprint_name,
    start_date,
    end_date,
    working_days,
    financial_year,

    SUM(total_tasks) AS total_tasks,
    SUM(completed_tasks) AS completed_tasks,

    SUM(completed_story_points)
        AS completed_story_points,

    ROUND(
        SUM(cycle_time_sum_days)
        / NULLIF(SUM(valid_cycle_time_tasks), 0),
        2
    ) AS avg_team_cycle_time_days,

    SUM(blocked_tasks) AS blocked_tasks,
    SUM(reopened_tasks) AS reopened_tasks,
    SUM(reopen_events) AS reopen_events,

    ROUND(
        100.0 * SUM(on_time_tasks)
        / NULLIF(SUM(on_time_eligible_tasks), 0),
        2
    ) AS on_time_rate_pct

FROM v_team_sprint_productivity

GROUP BY
    sprint_id,
    sprint_name,
    start_date,
    end_date,
    working_days,
    financial_year;
