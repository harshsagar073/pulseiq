
-- Database: pulseiq_task4.duckdb
-- Source schema: raw
-- Output schema: governed

CREATE SCHEMA IF NOT EXISTS governed;

-- M01: Headcount
-- Grain: department x month
CREATE OR REPLACE VIEW governed.m01_headcount AS
SELECT
    month_start_date,
    department_id,
    CASE
        WHEN headcount_end < 5 THEN NULL
        ELSE headcount_end
    END AS metric_value,
    'employees' AS unit,
    headcount_end AS group_size,
    headcount_end < 5 AS suppressed
FROM raw.fact_headcount_monthly;

-- M02: Hires
-- Grain: department x month
CREATE OR REPLACE VIEW governed.m02_hires AS
SELECT
    month_start_date,
    department_id,
    CASE
        WHEN hires < 5 THEN NULL
        ELSE hires
    END AS metric_value,
    'employees' AS unit,
    hires AS group_size,
    hires < 5 AS suppressed
FROM raw.fact_headcount_monthly;

-- M03: Exits
-- Grain: department x month
CREATE OR REPLACE VIEW governed.m03_exits AS
SELECT
    month_start_date,
    department_id,
    CASE
        WHEN exits < 5 THEN NULL
        ELSE exits
    END AS metric_value,
    'employees' AS unit,
    exits AS group_size,
    exits < 5 AS suppressed
FROM raw.fact_headcount_monthly;




-- M04: Monthly attrition rate
-- Grain: department x month
-- Official definition: exits / headcount_start * 100
-- Privacy: minimum group size 10, using opening headcount

CREATE OR REPLACE VIEW governed.m04_monthly_attrition AS
SELECT
    month_start_date,
    department_id,
    CASE
        WHEN headcount_start < 10 THEN NULL
        ELSE ROUND(
            100.0 * exits / NULLIF(headcount_start, 0),
            2
        )
    END AS metric_value,
    'percent' AS unit,
    headcount_start AS group_size,
    headcount_start < 10 AS suppressed
FROM raw.fact_headcount_monthly;




-- M05: Rolling 12-month attrition rate
-- Grain: department x month
-- Official definition: SUM(exits, 12 months) / AVG(headcount_end, 12 months) * 100
-- Privacy: minimum group size 10, based on average headcount

CREATE OR REPLACE VIEW governed.m05_rolling_12m_attrition AS
WITH rolling AS (
    SELECT
        month_start_date,
        department_id,
        SUM(exits) OVER (
            PARTITION BY department_id
            ORDER BY month_start_date
            ROWS BETWEEN 11 PRECEDING AND CURRENT ROW
        ) AS exits_12m,
        AVG(headcount_end) OVER (
            PARTITION BY department_id
            ORDER BY month_start_date
            ROWS BETWEEN 11 PRECEDING AND CURRENT ROW
        ) AS avg_headcount_12m,
        COUNT(*) OVER (
            PARTITION BY department_id
            ORDER BY month_start_date
            ROWS BETWEEN 11 PRECEDING AND CURRENT ROW
        ) AS months_available
    FROM raw.fact_headcount_monthly
)
SELECT
    month_start_date,
    department_id,
    CASE
        WHEN months_available < 12 THEN NULL
        WHEN avg_headcount_12m < 10 THEN NULL
        ELSE ROUND(
            100.0 * exits_12m / NULLIF(avg_headcount_12m, 0),
            2
        )
    END AS metric_value,
    'percent' AS unit,
    ROUND(avg_headcount_12m, 2) AS group_size,
    CASE
        WHEN months_available >= 12 AND avg_headcount_12m < 10 THEN TRUE
        ELSE FALSE
    END AS suppressed
FROM rolling;



-- M06: Voluntary attrition rate
-- Grain: department x month
-- Official definition: SUM(voluntary_exits, 12 months) / AVG(headcount_end, 12 months) * 100
-- Privacy: minimum group size 10, based on average headcount

CREATE OR REPLACE VIEW governed.m06_voluntary_attrition AS
WITH rolling AS (
    SELECT
        month_start_date,
        department_id,
        SUM(voluntary_exits) OVER (
            PARTITION BY department_id
            ORDER BY month_start_date
            ROWS BETWEEN 11 PRECEDING AND CURRENT ROW
        ) AS voluntary_exits_12m,
        AVG(headcount_end) OVER (
            PARTITION BY department_id
            ORDER BY month_start_date
            ROWS BETWEEN 11 PRECEDING AND CURRENT ROW
        ) AS avg_headcount_12m,
        COUNT(*) OVER (
            PARTITION BY department_id
            ORDER BY month_start_date
            ROWS BETWEEN 11 PRECEDING AND CURRENT ROW
        ) AS months_available
    FROM raw.fact_headcount_monthly
)
SELECT
    month_start_date,
    department_id,
    CASE
        WHEN months_available < 12 THEN NULL
        WHEN avg_headcount_12m < 10 THEN NULL
        ELSE ROUND(
            100.0 * voluntary_exits_12m / NULLIF(avg_headcount_12m, 0),
            2
        )
    END AS metric_value,
    'percent' AS unit,
    ROUND(avg_headcount_12m, 2) AS group_size,
    CASE
        WHEN months_available >= 12 AND avg_headcount_12m < 10 THEN TRUE
        ELSE FALSE
    END AS suppressed
FROM rolling;



-- M07: Gross pay
-- Grain: employee x month
-- Official definition: SUM(gross_pay)
-- Source: raw.fact_payroll
-- Privacy: minimum group size 5

CREATE OR REPLACE VIEW governed.m07_gross_pay AS
SELECT
    period_end_date,
    department_id,
    SUM(gross_pay) AS metric_value,
    'INR' AS unit,
    COUNT(DISTINCT employee_id) AS group_size,
    COUNT(DISTINCT employee_id) < 5 AS suppressed
FROM raw.fact_payroll
GROUP BY
    period_end_date,
    department_id;



-- M08: Net pay
-- Official definition: SUM(net_pay)
-- Source: raw.fact_payroll
-- Privacy: minimum group size 5

CREATE OR REPLACE VIEW governed.m08_net_pay AS
SELECT
    period_end_date,
    department_id,
    SUM(net_pay) AS metric_value,
    'INR' AS unit,
    COUNT(DISTINCT employee_id) AS group_size,
    COUNT(DISTINCT employee_id) < 5 AS suppressed
FROM raw.fact_payroll
GROUP BY
    period_end_date,
    department_id;



-- M09: Payroll cost (employer cost)
-- Official definition: SUM(employer_cost)
-- Source: raw.fact_payroll
-- Privacy: minimum group size 5
-- Reconciliation: should align with ledger accounts 5001-5005

CREATE OR REPLACE VIEW governed.m09_payroll_cost AS
SELECT
    period_end_date,
    department_id,
    SUM(employer_cost) AS metric_value,
    'INR' AS unit,
    COUNT(DISTINCT employee_id) AS group_size,
    COUNT(DISTINCT employee_id) < 5 AS suppressed
FROM raw.fact_payroll
GROUP BY
    period_end_date,
    department_id;



-- M10: Cost per head
-- Official definition: SUM(employer_cost) / COUNT(DISTINCT employee_id)
-- Source: raw.fact_payroll
-- Grain: department x month
-- Privacy: minimum group size 5

CREATE OR REPLACE VIEW governed.m10_cost_per_head AS
SELECT
    period_end_date,
    department_id,
    ROUND(
        SUM(employer_cost) / NULLIF(COUNT(DISTINCT employee_id), 0),
        2
    ) AS metric_value,
    'INR' AS unit,
    COUNT(DISTINCT employee_id) AS group_size,
    COUNT(DISTINCT employee_id) < 5 AS suppressed
FROM raw.fact_payroll
GROUP BY
    period_end_date,
    department_id;



-- M11: Overtime share
-- Official definition: SUM(overtime_pay) / SUM(employer_cost) * 100
-- Source: raw.fact_payroll
-- Grain: department x month
-- Privacy: minimum group size 5

CREATE OR REPLACE VIEW governed.m11_overtime_share AS
SELECT
    period_end_date,
    department_id,
    CASE
        WHEN COUNT(DISTINCT employee_id) < 5 THEN NULL
        ELSE ROUND(
            100.0 * SUM(overtime_pay) / NULLIF(SUM(employer_cost), 0),
            2
        )
    END AS metric_value,
    'percent' AS unit,
    COUNT(DISTINCT employee_id) AS group_size,
    COUNT(DISTINCT employee_id) < 5 AS suppressed
FROM raw.fact_payroll
GROUP BY
    period_end_date,
    department_id;



-- M12: Variable pay share
-- Formula: SUM(variable_pay) / SUM(gross_pay) * 100
CREATE OR REPLACE VIEW governed.m12_variable_pay_share AS
SELECT
    period_end_date,
    department_id,
    CASE WHEN COUNT(DISTINCT employee_id) < 5 THEN NULL
         ELSE ROUND(100.0 * SUM(variable_pay) / NULLIF(SUM(gross_pay), 0), 2)
    END AS metric_value,
    'percent' AS unit,
    COUNT(DISTINCT employee_id) AS group_size,
    COUNT(DISTINCT employee_id) < 5 AS suppressed
FROM raw.fact_payroll
GROUP BY period_end_date, department_id;


-- M13: Attendance rate
-- Formula: (present_days + 0.5 * half_days_unpaid) / scheduled_days
CREATE OR REPLACE VIEW governed.m13_attendance_rate AS
SELECT
    period_end_date,
    department_id,
    CASE WHEN COUNT(DISTINCT employee_id) < 5 THEN NULL
         ELSE ROUND(
             (SUM(present_days) + 0.5 * SUM(half_days_unpaid))
             / NULLIF(SUM(scheduled_days), 0), 4
         )
    END AS metric_value,
    'ratio' AS unit,
    COUNT(DISTINCT employee_id) AS group_size,
    COUNT(DISTINCT employee_id) < 5 AS suppressed
FROM raw.fact_attendance_monthly
GROUP BY period_end_date, department_id;


-- M14: Late arrival rate
-- Formula: SUM(late_arrivals) / SUM(present_days)
CREATE OR REPLACE VIEW governed.m14_late_arrival_rate AS
SELECT
    period_end_date,
    department_id,
    CASE WHEN COUNT(DISTINCT employee_id) < 5 THEN NULL
         ELSE ROUND(
             SUM(late_arrivals) * 1.0 / NULLIF(SUM(present_days), 0), 4
         )
    END AS metric_value,
    'ratio' AS unit,
    COUNT(DISTINCT employee_id) AS group_size,
    COUNT(DISTINCT employee_id) < 5 AS suppressed
FROM raw.fact_attendance_monthly
GROUP BY period_end_date, department_id;


-- M15: Leave without pay days
-- Privacy-safe output: department x payroll period
CREATE OR REPLACE VIEW governed.m15_lop_days AS
SELECT
    period_end_date,
    department_id,
    CASE WHEN COUNT(DISTINCT employee_id) < 5 THEN NULL
         ELSE ROUND(SUM(lop_days), 2)
    END AS metric_value,
    'days' AS unit,
    COUNT(DISTINCT employee_id) AS group_size,
    COUNT(DISTINCT employee_id) < 5 AS suppressed
FROM raw.fact_payroll
GROUP BY period_end_date, department_id;



-- M16: Revenue
-- Official formula: -SUM(signed_amount) for accounts 4001-4004
CREATE OR REPLACE VIEW governed.m16_revenue AS
SELECT
    posting_period,
    account_code,
    -SUM(signed_amount_debit_positive) AS metric_value,
    'INR' AS unit,
    COUNT(DISTINCT line_id) AS group_size,
    FALSE AS suppressed
FROM raw.fact_ledger
WHERE TRY_CAST(account_code AS INTEGER) BETWEEN 4001 AND 4004
GROUP BY posting_period, account_code;


-- M17: Net profit
-- Includes interest income account 4900 and expense accounts 5001-5999
CREATE OR REPLACE VIEW governed.m17_net_profit AS
SELECT
    posting_period,
    -SUM(signed_amount_debit_positive) AS metric_value,
    'INR' AS unit,
    COUNT(DISTINCT line_id) AS group_size,
    FALSE AS suppressed
FROM raw.fact_ledger
WHERE
    TRY_CAST(account_code AS INTEGER) BETWEEN 4001 AND 4999
    OR TRY_CAST(account_code AS INTEGER) BETWEEN 5001 AND 5999
GROUP BY posting_period;


-- M18: Operating margin
CREATE OR REPLACE VIEW governed.m18_operating_margin AS
WITH monthly AS (
    SELECT
        posting_period,
        -SUM(CASE
            WHEN TRY_CAST(account_code AS INTEGER) BETWEEN 4001 AND 4004
            THEN signed_amount_debit_positive ELSE 0
        END) AS revenue,
        -SUM(CASE
            WHEN TRY_CAST(account_code AS INTEGER) BETWEEN 4001 AND 4999
              OR TRY_CAST(account_code AS INTEGER) BETWEEN 5001 AND 5999
            THEN signed_amount_debit_positive ELSE 0
        END) AS net_profit,
        COUNT(DISTINCT line_id) AS group_size
    FROM raw.fact_ledger
    GROUP BY posting_period
)
SELECT
    posting_period,
    CASE WHEN revenue = 0 THEN NULL
         ELSE ROUND(100.0 * net_profit / revenue, 2)
    END AS metric_value,
    'percent' AS unit,
    group_size,
    FALSE AS suppressed
FROM monthly;


-- M19: Payroll as percentage of revenue
-- Payroll expense comes from ledger accounts 5001-5005
CREATE OR REPLACE VIEW governed.m19_payroll_pct_revenue AS
WITH monthly AS (
    SELECT
        posting_period,
        -SUM(CASE
            WHEN TRY_CAST(account_code AS INTEGER) BETWEEN 4001 AND 4004
            THEN signed_amount_debit_positive ELSE 0
        END) AS revenue,
        SUM(CASE
            WHEN TRY_CAST(account_code AS INTEGER) BETWEEN 5001 AND 5005
            THEN signed_amount_debit_positive ELSE 0
        END) AS payroll_cost,
        COUNT(DISTINCT line_id) AS group_size
    FROM raw.fact_ledger
    GROUP BY posting_period
)
SELECT
    posting_period,
    CASE WHEN revenue = 0 THEN NULL
         ELSE ROUND(100.0 * payroll_cost / revenue, 2)
    END AS metric_value,
    'percent' AS unit,
    group_size,
    FALSE AS suppressed
FROM monthly;


-- M20: Days sales outstanding (DSO)
CREATE OR REPLACE VIEW governed.m20_dso AS
WITH months AS (
    SELECT DISTINCT month_end_date AS report_date
    FROM raw.dim_date
),
monthly AS (
    SELECT
        m.report_date,
        SUM(CASE
            WHEN CAST(i.invoice_date AS DATE) <= m.report_date
             AND UPPER(CAST(i.status AS VARCHAR)) NOT IN ('DRAFT', 'CANCELLED')
            THEN i.balance_due ELSE 0
        END) AS closing_receivables,
        SUM(CASE
            WHEN CAST(i.invoice_date AS DATE) > m.report_date - INTERVAL 90 DAY
             AND CAST(i.invoice_date AS DATE) <= m.report_date
             AND UPPER(CAST(i.status AS VARCHAR)) NOT IN ('DRAFT', 'CANCELLED')
            THEN i.total_amount ELSE 0
        END) AS revenue_including_gst,
        COUNT(DISTINCT i.invoice_id) AS group_size
    FROM months m
    LEFT JOIN raw.fact_invoice i
      ON CAST(i.invoice_date AS DATE) <= m.report_date
    GROUP BY m.report_date
)
SELECT
    report_date,
    CASE WHEN revenue_including_gst = 0 THEN NULL
         ELSE ROUND(90.0 * closing_receivables / revenue_including_gst, 2)
    END AS metric_value,
    'days' AS unit,
    group_size,
    FALSE AS suppressed
FROM monthly;


-- M21: Overdue receivables
CREATE OR REPLACE VIEW governed.m21_overdue_receivables AS
SELECT
    d.month_end_date AS report_date,
    i.client_id,
    SUM(i.balance_due) AS metric_value,
    'INR' AS unit,
    COUNT(DISTINCT i.invoice_id) AS group_size,
    FALSE AS suppressed
FROM (
    SELECT DISTINCT month_end_date
    FROM raw.dim_date
) d
JOIN raw.fact_invoice i
  ON CAST(i.due_date AS DATE) < d.month_end_date
 AND UPPER(CAST(i.status AS VARCHAR)) NOT IN ('DRAFT', 'CANCELLED')
GROUP BY d.month_end_date, i.client_id;




-- M22: Task completion rate
-- Formula: Done tasks / tasks not Cancelled * 100
CREATE OR REPLACE VIEW governed.m22_task_completion_rate AS
SELECT
    team_id,
    sprint_id,
    CASE
        WHEN COUNT(*) FILTER (
            WHERE UPPER(CAST(status AS VARCHAR)) <> 'CANCELLED'
        ) < 5 THEN NULL
        ELSE ROUND(
            100.0 * COUNT(*) FILTER (
                WHERE UPPER(CAST(status AS VARCHAR)) = 'DONE'
            )
            / NULLIF(COUNT(*) FILTER (
                WHERE UPPER(CAST(status AS VARCHAR)) <> 'CANCELLED'
            ), 0),
            2
        )
    END AS metric_value,
    'percent' AS unit,
    COUNT(*) FILTER (
        WHERE UPPER(CAST(status AS VARCHAR)) <> 'CANCELLED'
    ) AS group_size,
    COUNT(*) FILTER (
        WHERE UPPER(CAST(status AS VARCHAR)) <> 'CANCELLED'
    ) < 5 AS suppressed
FROM raw.fact_task
GROUP BY team_id, sprint_id;




-- M23: On-time delivery rate
-- Formula: Done tasks completed on time / all Done tasks * 100
CREATE OR REPLACE VIEW governed.m23_on_time_delivery_rate AS
SELECT
    team_id,
    sprint_id,
    CASE
        WHEN COUNT(*) FILTER (
            WHERE UPPER(CAST(status AS VARCHAR)) = 'DONE'
        ) < 5 THEN NULL
        ELSE ROUND(
            100.0 * COUNT(*) FILTER (
                WHERE UPPER(CAST(status AS VARCHAR)) = 'DONE'
                  AND UPPER(CAST(completed_on_time AS VARCHAR))
                      IN ('Y', 'TRUE', '1')
            )
            / NULLIF(COUNT(*) FILTER (
                WHERE UPPER(CAST(status AS VARCHAR)) = 'DONE'
            ), 0),
            2
        )
    END AS metric_value,
    'percent' AS unit,
    COUNT(*) FILTER (
        WHERE UPPER(CAST(status AS VARCHAR)) = 'DONE'
    ) AS group_size,
    COUNT(*) FILTER (
        WHERE UPPER(CAST(status AS VARCHAR)) = 'DONE'
    ) < 5 AS suppressed
FROM raw.fact_task
GROUP BY team_id, sprint_id;


-- M24: Velocity
-- Formula: SUM(story_points) for tasks Done
CREATE OR REPLACE VIEW governed.m24_velocity AS
SELECT
    team_id,
    sprint_id,
    SUM(CASE
        WHEN UPPER(CAST(status AS VARCHAR)) = 'DONE'
        THEN COALESCE(story_points, 0)
        ELSE 0
    END) AS metric_value,
    'points' AS unit,
    COUNT(*) FILTER (
        WHERE UPPER(CAST(status AS VARCHAR)) = 'DONE'
    ) AS group_size,
    FALSE AS suppressed
FROM raw.fact_task
GROUP BY team_id, sprint_id;


-- M25: Average cycle time
-- Negative cycle times are excluded and should be investigated as data errors.
CREATE OR REPLACE VIEW governed.m25_average_cycle_time AS
WITH valid_tasks AS (
    SELECT
        team_id,
        sprint_id,
        date_diff(
            'day',
            CAST(started_date AS DATE),
            CAST(completed_date AS DATE)
        ) AS cycle_days
    FROM raw.fact_task
    WHERE UPPER(CAST(status AS VARCHAR)) = 'DONE'
      AND started_date IS NOT NULL
      AND completed_date IS NOT NULL
)
SELECT
    team_id,
    sprint_id,
    CASE WHEN COUNT(*) FILTER (WHERE cycle_days >= 0) < 5 THEN NULL
         ELSE ROUND(AVG(cycle_days) FILTER (WHERE cycle_days >= 0), 2)
    END AS metric_value,
    'days' AS unit,
    COUNT(*) FILTER (WHERE cycle_days >= 0) AS group_size,
    COUNT(*) FILTER (WHERE cycle_days >= 0) < 5 AS suppressed
FROM valid_tasks
GROUP BY team_id, sprint_id;




-- M26: Anomaly flag rate
-- Formula: Flagged records / all records * 100
-- Flags are leads for investigation, not proof of an anomaly.
CREATE OR REPLACE VIEW governed.m26_anomaly_flag_rate AS
SELECT
    source_dataset,
    period,
    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE UPPER(CAST(flagged AS VARCHAR)) IN ('Y', 'TRUE', '1')
        ) / NULLIF(COUNT(*), 0),
        2
    ) AS metric_value,
    'percent' AS unit,
    COUNT(*) AS group_size,
    FALSE AS suppressed
FROM raw.fact_anomaly
GROUP BY source_dataset, period;


-- M27: High-risk share
-- Privacy: minimum group size 10
CREATE OR REPLACE VIEW governed.m27_high_risk_share AS
SELECT
    department_id,
    CASE WHEN COUNT(*) < 10 THEN NULL
         ELSE ROUND(
             1.0 * COUNT(*) FILTER (
                 WHERE UPPER(CAST(risk_band AS VARCHAR)) = 'HIGH'
             ) / NULLIF(COUNT(*), 0),
             4
         )
    END AS metric_value,
    'ratio' AS unit,
    COUNT(*) AS group_size,
    COUNT(*) < 10 AS suppressed
FROM raw.fact_attrition_risk
GROUP BY department_id;


-- M28: Forecast error (MAPE)
-- Join forecast headcount to actual monthly closing headcount.
CREATE OR REPLACE VIEW governed.m28_forecast_error_mape AS
WITH matched AS (
    SELECT
        CAST(f.forecast_month AS DATE) AS forecast_month,
        f.department_id,
        f.forecast_value,
        h.headcount_end AS actual_value
    FROM raw.fact_forecast f
    JOIN raw.fact_headcount_monthly h
      ON f.department_id = h.department_id
     AND CAST(f.forecast_month AS DATE) = CAST(h.month_start_date AS DATE)
    WHERE LOWER(CAST(f.metric AS VARCHAR)) LIKE '%headcount%'
      AND h.headcount_end > 0
)
SELECT
    forecast_month,
    department_id,
    ROUND(
        AVG(ABS(actual_value - forecast_value) / NULLIF(actual_value, 0)) * 100,
        2
    ) AS metric_value,
    'percent' AS unit,
    COUNT(*) AS group_size,
    FALSE AS suppressed
FROM matched
GROUP BY forecast_month, department_id;
