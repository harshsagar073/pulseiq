-- ============================================================
-- PULSEIQ PHASE 3 - TASK 14
-- AI Signals Dashboard
-- Reusable DuckDB views over Task 14's local source copies
-- ============================================================

CREATE OR REPLACE VIEW stg_anomaly AS
SELECT
    result_id,
    source_dataset,
    record_id,
    employee_id,
    period,
    TRY_CAST(anomaly_score AS DOUBLE) AS anomaly_score,
    flagged,
    reason_code,
    reason_text,
    TRY_CAST(money_at_risk AS DOUBLE) AS money_at_risk,
    model_version,
    scored_at,
    period_key
FROM read_csv_auto('data/source/fact_anomaly.csv', header = true);


CREATE OR REPLACE VIEW stg_forecast AS
SELECT
    forecast_id,
    metric,
    department_id,
    TRY_CAST(forecast_month AS DATE) AS forecast_month,
    TRY_CAST(forecast_value AS DOUBLE) AS forecast_value,
    TRY_CAST(lower_80 AS DOUBLE) AS lower_80,
    TRY_CAST(upper_80 AS DOUBLE) AS upper_80,
    method,
    trained_through,
    model_version,
    forecast_month_key
FROM read_csv_auto('data/source/fact_forecast.csv', header = true);


CREATE OR REPLACE VIEW stg_attrition_risk AS
SELECT
    prediction_id,
    employee_id,
    as_of_date_key,
    department_id,
    TRY_CAST(as_of_date AS DATE) AS as_of_date,
    TRY_CAST(risk_score_12m AS DOUBLE) AS risk_score_12m,
    risk_band,
    top_reason_1,
    top_reason_2,
    top_reason_3,
    model_version,
    model_note,
    employee_key
FROM read_csv_auto('data/source/fact_attrition_risk.csv', header = true);


CREATE OR REPLACE VIEW stg_headcount AS
SELECT
    date_key,
    TRY_CAST(month_start_date AS DATE) AS month_start_date,
    department_id,
    TRY_CAST(headcount_start AS DOUBLE) AS headcount_start,
    TRY_CAST(hires AS DOUBLE) AS hires,
    TRY_CAST(exits AS DOUBLE) AS exits,
    TRY_CAST(voluntary_exits AS DOUBLE) AS voluntary_exits,
    TRY_CAST(transfers_in AS DOUBLE) AS transfers_in,
    TRY_CAST(transfers_out AS DOUBLE) AS transfers_out,
    TRY_CAST(headcount_end AS DOUBLE) AS headcount_end,
    TRY_CAST(attrition_rate_monthly_pct AS DOUBLE)
        AS attrition_rate_monthly_pct
FROM read_csv_auto('data/source/fact_headcount_monthly.csv', header = true);


-- Department names for readable output.
CREATE OR REPLACE VIEW stg_department AS
SELECT *
FROM read_csv_auto('data/reference/dim_department.csv', header = true);


-- Anomaly type summary.
-- Missing money values remain unquantified; they are not converted to zero.
CREATE OR REPLACE VIEW mart_anomaly_exposure AS
SELECT
    reason_code,
    COUNT(*) AS anomaly_count,
    COUNT(money_at_risk) AS quantified_count,
    COUNT(*) - COUNT(money_at_risk) AS unquantified_count,
    SUM(money_at_risk) AS known_money_at_risk
FROM stg_anomaly
GROUP BY reason_code;


-- Historical actual headcount at company-wide level.
CREATE OR REPLACE VIEW mart_actual_headcount_all AS
SELECT
    month_start_date,
    SUM(headcount_end) AS actual_headcount
FROM stg_headcount
GROUP BY month_start_date;


-- Company-wide attrition calculated as a weighted rate:
-- total exits / total starting headcount * 100.
CREATE OR REPLACE VIEW mart_actual_attrition_all AS
SELECT
    month_start_date,
    SUM(exits) AS total_exits,
    SUM(headcount_start) AS total_headcount_start,
    CASE
        WHEN SUM(headcount_start) = 0 THEN NULL
        ELSE SUM(exits) / SUM(headcount_start) * 100
    END AS actual_attrition_rate_pct
FROM stg_headcount
GROUP BY month_start_date;


-- Forecast error is calculated only when the same month has actuals.
-- No future actual values are manufactured.
CREATE OR REPLACE VIEW mart_forecast_error AS

SELECT
    f.metric,
    f.department_id,
    f.forecast_month AS month,
    a.actual_headcount AS actual_value,
    f.forecast_value,
    f.forecast_value - a.actual_headcount AS error,
    ABS(f.forecast_value - a.actual_headcount) AS absolute_error,
    CASE
        WHEN a.actual_headcount = 0 THEN NULL
        ELSE ABS(f.forecast_value - a.actual_headcount)
             / ABS(a.actual_headcount) * 100
    END AS absolute_percentage_error_pct
FROM stg_forecast f
INNER JOIN mart_actual_headcount_all a
    ON f.forecast_month = a.month_start_date
WHERE f.metric = 'headcount_end'
  AND f.department_id = 'ALL'

UNION ALL

SELECT
    f.metric,
    f.department_id,
    f.forecast_month AS month,
    a.actual_attrition_rate_pct AS actual_value,
    f.forecast_value,
    f.forecast_value - a.actual_attrition_rate_pct AS error,
    ABS(f.forecast_value - a.actual_attrition_rate_pct) AS absolute_error,
    CASE
        WHEN a.actual_attrition_rate_pct = 0 THEN NULL
        ELSE ABS(f.forecast_value - a.actual_attrition_rate_pct)
             / ABS(a.actual_attrition_rate_pct) * 100
    END AS absolute_percentage_error_pct
FROM stg_forecast f
INNER JOIN mart_actual_attrition_all a
    ON f.forecast_month = a.month_start_date
WHERE f.metric = 'attrition_rate_monthly_pct'
  AND f.department_id = 'ALL';


-- Aggregated risk-band counts; no employee-level details exposed.
CREATE OR REPLACE VIEW mart_attrition_risk_bands AS
SELECT
    risk_band,
    COUNT(*) AS employee_count
FROM stg_attrition_risk
GROUP BY risk_band;
