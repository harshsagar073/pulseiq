# PulseIQ — Task 10: Budget vs Actual and KPI Targets

## Objective
Compare monthly departmental payroll costs against approved budgets and evaluate departmental KPIs against their targets.

## Data sources
- Read-only source warehouse: Phase 1/Task 4/pulseiq_task4.duckdb
- Budget and KPI target tables
- Payroll, department, attendance, overtime, attrition and task data

Task 10 builds its own database: pulseiq_task10.duckdb. The source warehouse is not modified.

## Payroll calculation
Actual payroll cost is the sum of employer_cost, grouped by month and department.

Excluded payroll item IDs:
- PI-X0001
- PI-X0002
- PI-X0003
- PI-X0004

Variance = Actual employer cost - Budget

Variance % = (Variance / Budget) × 100

Positive variance means overspending. Negative variance means spending below budget.

## KPI traffic-light rules
- Green: target met.
- Red: target missed.
- Amber: actual or target is unavailable or suppressed.

KPI direction:
- Attendance: higher is better.
- Overtime share: lower is better.
- Monthly attrition: lower is better.
- Task completion: higher is better.

Missing KPI targets remain unavailable, not zero. No unsupported amber thresholds have been invented.

Task completion is calculated as DONE tasks divided by non-cancelled tasks, grouped by due month and department.

## Department ranking
Departments are ranked by cumulative positive monthly payroll variances (gross overspend). Net variance is reported separately.

## Recommendations and caveat
Engineering and Sales are the two highest gross-overspend departments. Recommendations focus on reconciling paid headcount, employer-cost components, hiring-freeze timing, approved exceptions, vacancies, backfills and one-off payments.

Budgets may not have been refreshed after the hiring freeze. Rankings are review priorities, not proof of avoidable spending.

## Verification
Run:

python verify_task10.py

Result: 3 of 3 manually checked department-month examples matched both dashboard actuals and variances.

Evidence:
- verification/manual_verification.csv
- verification/manual_verification.txt
- evidence/top_two_overspend_departments.csv
- evidence/recommendations.txt

## Run the project

Install dependencies:

pip install -r requirements.txt

Build the database:

python build_task10.py

Run verification:

python verify_task10.py

Launch dashboard:

streamlit run app.py
