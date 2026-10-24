
-- PulseIQ Task 4: Hand Checks
-- Read-only checks against the governed metric views.
-- M28 may return no rows because actuals end in September 2026
-- while forecasts start in October 2026.

-- CHECK 1: M01 Headcount
-- Compare the governed view with the source monthly headcount.
SELECT
    h.month_start_date,
    h.department_id,
    h.headcount_end AS source_value,
    m.metric_value AS governed_value,
    h.headcount_end = m.metric_value AS matches
FROM raw.fact_headcount_monthly h
JOIN governed.m01_headcount m
  ON h.month_start_date = m.month_start_date
 AND h.department_id = m.department_id
WHERE h.month_start_date = DATE '2026-09-01'
ORDER BY h.department_id;

-- CHECK 2: M02 Hires
SELECT
    h.month_start_date,
    h.department_id,
    h.hires AS source_value,
    m.metric_value AS governed_value,
    h.hires = m.metric_value AS matches
FROM raw.fact_headcount_monthly h
JOIN governed.m02_hires m
  ON h.month_start_date = m.month_start_date
 AND h.department_id = m.department_id
WHERE h.month_start_date = DATE '2026-09-01'
ORDER BY h.department_id;

-- CHECK 3: M03 Exits
SELECT
    h.month_start_date,
    h.department_id,
    h.exits AS source_value,
    m.metric_value AS governed_value,
    h.exits = m.metric_value AS matches
FROM raw.fact_headcount_monthly h
JOIN governed.m03_exits m
  ON h.month_start_date = m.month_start_date
 AND h.department_id = m.department_id
WHERE h.month_start_date = DATE '2026-09-01'
ORDER BY h.department_id;

-- CHECK 4: M04 Monthly Attrition
-- Official formula: exits / headcount_start * 100.
SELECT
    h.month_start_date,
    h.department_id,
    ROUND(100.0 * h.exits / NULLIF(h.headcount_start, 0), 2)
        AS independently_calculated_pct,
    m.metric_value AS governed_pct,
    ABS(
        ROUND(100.0 * h.exits / NULLIF(h.headcount_start, 0), 2)
        - m.metric_value
    ) < 0.02 AS matches
FROM raw.fact_headcount_monthly h
JOIN governed.m04_monthly_attrition m
  ON h.month_start_date = m.month_start_date
 AND h.department_id = m.department_id
WHERE h.month_start_date = DATE '2026-09-01'
ORDER BY h.department_id;

-- CHECK 5: M28 Forecast Error Availability
-- Future forecast months should not have MAPE until actuals exist.
SELECT
    f.metric,
    MIN(CAST(f.forecast_month AS DATE)) AS first_forecast_month,
    MAX(CAST(f.forecast_month AS DATE)) AS last_forecast_month,
    MAX(CAST(h.month_start_date AS DATE)) AS last_actual_month,
    COUNT(h.month_start_date) AS matched_actual_rows
FROM raw.fact_forecast f
LEFT JOIN raw.fact_headcount_monthly h
  ON f.department_id = h.department_id
 AND CAST(f.forecast_month AS DATE) = CAST(h.month_start_date AS DATE)
WHERE f.metric = 'headcount_end'
GROUP BY f.metric;

-- CHECK 6: Confirm M28 has no results yet
SELECT COUNT(*) AS m28_result_rows
FROM governed.m28_forecast_error_mape;
