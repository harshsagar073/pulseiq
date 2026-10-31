-- PulseIQ Task 6: Attendance and Leave Metric Views
-- Source data: validated CSV files from Task 1.

CREATE OR REPLACE VIEW monthly_attendance AS
SELECT
    strftime(CAST(period_end_date AS DATE), '%Y-%m') AS month,
    SUM(scheduled_days) AS scheduled_days,
    SUM(present_days) AS present_days,
    ROUND(
        100.0 * SUM(present_days) / NULLIF(SUM(scheduled_days), 0),
        2
    ) AS attendance_rate_pct,
    SUM(late_arrivals) AS late_arrivals,
    ROUND(SUM(overtime_hours), 2) AS overtime_hours
FROM read_csv_auto(
    '../../Phase 1/Task 1/validated/fact_attendance_monthly.csv',
    header = true
)
GROUP BY 1;

CREATE OR REPLACE VIEW department_attendance AS
SELECT
    department_id,
    SUM(scheduled_days) AS scheduled_days,
    SUM(present_days) AS present_days,
    ROUND(
        100.0 * SUM(present_days) / NULLIF(SUM(scheduled_days), 0),
        2
    ) AS attendance_rate_pct,
    SUM(late_arrivals) AS late_arrivals,
    ROUND(SUM(overtime_hours), 2) AS overtime_hours
FROM read_csv_auto(
    '../../Phase 1/Task 1/validated/fact_attendance_monthly.csv',
    header = true
)
GROUP BY department_id;

CREATE OR REPLACE VIEW approved_leave_by_type AS
SELECT
    leave_type_code,
    COUNT(*) AS approved_requests,
    ROUND(SUM(days), 2) AS approved_leave_days
FROM read_csv_auto(
    '../../Phase 1/Task 1/validated/fact_leave.csv',
    header = true
)
WHERE LOWER(status) = 'approved'
GROUP BY leave_type_code;

-- Note: Leave is grouped by request, not allocated across every date.
-- Monthly attendance is aggregated; holiday context does not prove causation.
