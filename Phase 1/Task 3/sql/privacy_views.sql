-- Manager-facing privacy suppression views.
-- Minimum group sizes: 5 for operational aggregates, 10 for risk aggregates.

CREATE OR REPLACE VIEW warehouse.manager_headcount_monthly AS
SELECT month_start_date, department_id, headcount_start, hires, exits,
       voluntary_exits, transfers_in, transfers_out, headcount_end,
       attrition_rate_monthly_pct
FROM warehouse.fact_headcount_monthly
WHERE headcount_end >= 5;

CREATE OR REPLACE VIEW warehouse.manager_payroll_monthly AS
SELECT period_end_date, department_id,
       COUNT(DISTINCT employee_id) AS employee_count,
       SUM(gross_pay) AS total_gross_pay,
       SUM(total_deductions) AS total_deductions,
       SUM(net_pay) AS total_net_pay,
       SUM(employer_cost) AS total_employer_cost,
       SUM(overtime_hours_paid) AS total_overtime_hours
FROM warehouse.fact_payroll
GROUP BY period_end_date, department_id
HAVING COUNT(DISTINCT employee_id) >= 5;

CREATE OR REPLACE VIEW warehouse.manager_attendance_monthly AS
SELECT period_end_date, department_id,
       COUNT(DISTINCT employee_id) AS employee_count,
       SUM(scheduled_days) AS scheduled_days,
       SUM(present_days) AS present_days,
       SUM(paid_leave_days) AS paid_leave_days,
       SUM(unpaid_absence_days) AS unpaid_absence_days,
       SUM(late_arrivals) AS late_arrivals,
       SUM(overtime_hours) AS overtime_hours,
       AVG(attendance_rate) AS average_attendance_rate
FROM warehouse.fact_attendance_monthly
GROUP BY period_end_date, department_id
HAVING COUNT(DISTINCT employee_id) >= 5;

CREATE OR REPLACE VIEW warehouse.manager_attrition_risk_summary AS
SELECT as_of_date, department_id,
       COUNT(DISTINCT employee_id) AS employee_count,
       AVG(risk_score_12m) AS average_risk_score,
       COUNT(DISTINCT CASE WHEN LOWER(risk_band) = 'high'
                           THEN employee_id END) AS high_risk_employee_count
FROM warehouse.fact_attrition_risk
GROUP BY as_of_date, department_id
HAVING COUNT(DISTINCT employee_id) >= 10;
