
-- PulseIQ Task 4: Governed Metric Catalog
-- One row per official metric definition.

CREATE SCHEMA IF NOT EXISTS governed;

CREATE OR REPLACE TABLE governed.metric_catalog (
    metric_id VARCHAR PRIMARY KEY,
    metric_name VARCHAR NOT NULL,
    formula VARCHAR NOT NULL,
    source_tables VARCHAR NOT NULL,
    grain VARCHAR NOT NULL,
    owner VARCHAR NOT NULL,
    unit VARCHAR NOT NULL,
    min_group_size INTEGER,
    business_rule VARCHAR
);

INSERT INTO governed.metric_catalog VALUES
('M01','Headcount','Distinct active employees on last day of month','fact_headcount_monthly; dim_employee','Department x month','HR','employees',5,'Use month-end active employees.'),
('M02','Hires','Count employees hired during the month','fact_headcount_monthly','Department x month','HR','employees',5,'Transfers are not hires.'),
('M03','Exits','Count employees exiting during the month','fact_headcount_monthly','Department x month','HR','employees',5,'Include resignations, terminations and contract endings.'),
('M04','Monthly attrition rate','Exits / headcount_start * 100','fact_headcount_monthly','Department x month','HR','percent',10,'Use beginning headcount as denominator.'),
('M05','Rolling 12-month attrition','SUM(exits over 12 months) / AVG(headcount_end over 12 months) * 100','fact_headcount_monthly','Department x month','HR','percent',10,'Require 12 months of data.'),
('M06','Voluntary attrition','SUM(voluntary_exits over 12 months) / AVG(headcount_end over 12 months) * 100','fact_headcount_monthly','Department x month','HR','percent',10,'Use a rolling 12-month window.'),
('M07','Gross pay','SUM(gross_pay)','fact_payroll','Employee x month','Payroll','INR',5,'Aggregate gross pay.'),
('M08','Net pay','SUM(net_pay)','fact_payroll','Employee x month','Payroll','INR',5,'Aggregate net pay.'),
('M09','Payroll cost','SUM(employer_cost)','fact_payroll','Employee x month','Finance','INR',5,'Reconcile with ledger accounts 5001-5005.'),
('M10','Cost per head','SUM(employer_cost) / COUNT(DISTINCT employee_id)','fact_payroll','Department x month','Finance','INR',5,'Distinct employee denominator.'),
('M11','Overtime share','SUM(overtime_pay) / SUM(employer_cost) * 100','fact_payroll','Department x month','Payroll','percent',5,'Include overtime-eligible roles only.'),
('M12','Variable pay share','SUM(variable_pay) / SUM(gross_pay) * 100','fact_payroll','Department x month','Payroll','percent',5,'Variable pay as a share of gross pay.'),
('M13','Attendance rate','(SUM(present_days) + 0.5 * SUM(half_days_unpaid)) / SUM(scheduled_days)','fact_attendance_monthly','Department x month','HR','ratio',5,'Paid leave is not counted as present.'),
('M14','Late arrival rate','SUM(late_arrivals) / SUM(present_days)','fact_attendance_monthly','Department x month','HR','ratio',5,'WFH uses web check-in.'),
('M15','Leave without pay days','SUM(lop_days)','fact_payroll','Employee x month','Payroll','days',5,'Aggregate LOP days.'),
('M16','Revenue','-SUM(signed_amount) for accounts 4001-4004','fact_ledger','Account x month','Finance','INR',NULL,'Exclude GST booked to account 2200.'),
('M17','Net profit','-SUM(signed_amount) for income and expense accounts 4xxx and 5xxx','fact_ledger','Month','Finance','INR',NULL,'Include interest income account 4900; exclude parent summary accounts.'),
('M18','Operating margin','Net profit / revenue * 100','fact_ledger','Month','Finance','percent',NULL,'Revenue denominator follows the official revenue definition.'),
('M19','Payroll as percent of revenue','Ledger payroll cost / revenue * 100','fact_payroll; fact_ledger','Month','Finance','percent',NULL,'Use ledger payroll accounts to avoid payroll reconciliation mismatch.'),
('M20','Days sales outstanding','Closing receivables / revenue including GST over last 90 days * 90','fact_invoice; fact_ledger','Month','Finance','days',NULL,'Include carried-in invoices.'),
('M21','Overdue receivables','SUM(balance_due) for overdue eligible invoices','fact_invoice','Client x report date','Finance','INR',NULL,'Due date before report date; exclude DRAFT and CANCELLED.'),
('M22','Task completion rate','COUNT(Done) / COUNT(status not Cancelled) * 100','fact_task','Team x sprint','Operations','percent',5,'Sample feed; minimum five eligible tasks.'),
('M23','On-time delivery','COUNT(Done and completed on time = Y) / COUNT(Done) * 100','fact_task','Team x sprint','Operations','percent',5,'Minimum five completed tasks.'),
('M24','Velocity','SUM(story_points) where status = Done','fact_task','Team x sprint','Operations','points',NULL,'Do not compare velocity between teams.'),
('M25','Average cycle time','AVG(completed_date - started_date)','fact_task','Team x sprint','Operations','days',5,'Negative cycle times are errors.'),
('M26','Anomaly flag rate','COUNT(flagged = Y) / COUNT(*) * 100','fact_anomaly','Source x month','AI/ML','percent',NULL,'Flags are leads for investigation, not proof of an anomaly.'),
('M27','High-risk share','COUNT(risk_band = High) / COUNT(*) * 100','fact_attrition_risk','Department','AI/ML','percent',10,'Aggregate by department; never rank named people.'),
('M28','Forecast error (MAPE)','AVG(ABS(actual - forecast) / actual) * 100','fact_forecast; fact_headcount_monthly','Department x month','AI/ML','percent',NULL,'Requires actuals for forecast months; exclude zero actuals.');
