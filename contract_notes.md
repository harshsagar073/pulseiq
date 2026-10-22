# PulseIQ ETL — Data Contract Notes

## Dataset and source

The PulseIQ workbook contains fictional training data. The CSV extracts are stored in `03_Data/csv/` and loaded into the `raw` schema in `pulseiq.duckdb`.

## Validation policy

- Preserve raw source tables; do not delete or overwrite source rows during validation.
- Route failed rows from the four formally contracted feeds to `quarantine/`, including a `_quarantine_reason` and `_source_table`.
- Write accepted rows to `validated/`.
- Write per-table input, passed, and quarantined counts to `etl_summary.csv`.
- Retain unexpected extra columns and print a warning rather than silently dropping them.
- Re-running the pipeline replaces its generated CSV outputs, making the outputs reproducible.

## Contract 1 — fact_task

**Purpose:** Task-board and sprint tracking.

| Column | Type | Nullability / rule |
|---|---|---|
| task_id | String | Required; unique format `TASK-nnnnn` |
| team_id | String | Required; must exist in `dim_team` |
| sprint_id | String | Required; must exist in `dim_sprint` |
| assignee_employee_id | String | Required; must exist in `dim_employee` |
| task_type | String | Required; Feature, Bug, Chore, or Spike |
| priority | String | Required; P1, P2, P3, or P4 |
| story_points | Integer | Required; 1, 2, 3, 5, 8, or 13 |
| created_date | Date | Required; must not be after started_date |
| started_date | Date | Nullable only when status is To Do |
| due_date | Date | Required; must equal the sprint end date |
| completed_date | Date | Nullable; required for Done and not before started_date |
| status | String | Required; Done, In Progress, Blocked, To Do, or Cancelled |
| reopened_count | Integer | Required; must be a non-negative integer |

The input also contains derived fields such as `cycle_time_days`, `is_overdue_at_cutoff`, and `completed_on_time`. These are retained as extra columns.

## Contract 2 — fact_forecast

**Purpose:** Department-level metric forecasts.

| Column | Type | Nullability / rule |
|---|---|---|
| forecast_id | String | Required; unique format `FC-nnnn` |
| metric | String | Required; `headcount_end` or `attrition_rate_monthly_pct` |
| department_id | String | Required; existing department ID or `ALL` |
| forecast_month | Date | Required; first day of the month |
| forecast_value | Decimal | Required; greater than or equal to zero |
| lower_80 | Decimal | Required; no greater than forecast_value |
| upper_80 | Decimal | Required; no less than forecast_value |
| method | String | Required |
| trained_through | String | Required; format YYYY-MM |

Extra fields such as `forecast_month_key` and `model_version` are retained.

## Contract 3 — fact_attrition_risk

**Purpose:** Employee attrition-risk predictions.

| Column | Type | Nullability / rule |
|---|---|---|
| prediction_id | String | Required; unique format `AR-nnnn` |
| employee_id | String | Required; must exist in `dim_employee` and refer to an active employee |
| department_id | String | Required; must exist in `dim_department` |
| as_of_date | Date | Required; the same date for the whole batch |
| risk_score_12m | Decimal | Required; between 0 and 1 |
| risk_band | String | Required; Low, Medium, or High |
| top_reason_1 | String | Optional; plain English |
| top_reason_2 | String | Optional; plain English |
| top_reason_3 | String | Optional; plain English |
| model_version | String | Required |

Extra fields such as `as_of_date_key`, `employee_key`, and `model_note` are retained.

## Additional formal feed — fact_anomaly

- `result_id`: required unique `AN-nnnn` identifier.
- `source_dataset`: required; `attendance_monthly_features` or `payroll_monthly_features`.
- `record_id`: required; must exist in the source dataset.
- `employee_id`: required; must exist in `dim_employee`.
- `period`: required date, first or last day of the month.
- `anomaly_score`: required numeric value from 0 to 1.
- `flagged`: required Y or N.
- `reason_code`, `reason_text`, `model_version`, `scored_at`: required.
- `money_at_risk`: optional; numeric when populated.

## Scope and limitations

The provided `data_contracts` sheet formally defines four feeds: `fact_task`, `fact_forecast`, `fact_attrition_risk`, and `fact_anomaly`. The current ETL applies row-level checks to these four feeds. The other 21 tables are counted and exported unchanged; they do not yet have equivalent row-level contract validation in this implementation.

Foreign-key and business checks are limited to the rules implemented in `etl.py`. Additional rules—such as checking every identifier for uniqueness, confirming active employment status, verifying anomaly `record_id` against source datasets, and checking the same `as_of_date` across the entire attrition batch—should be added before describing this as complete validation of every contract rule.
