# Final Challenge — Payroll Cost Drill-down

## Project details

- Branch name: `final-challenge/payroll-cost-drilldown`
- Improvement selected: Payroll Cost Drill-down
- Location: `Phase 4/Task 20/final_challenge/payroll_cost_drilldown/`

## Problem it solves

Management needs to understand monthly payroll cost movements and identify which departments contributed to an increase or decrease.

## Improvement implemented

A Streamlit dashboard was created with:

- Reporting-month selection
- Department selection
- Company payroll KPIs
- Monthly gross, net and employer-cost trend
- Department-wise employer-cost comparison
- Month-on-month department cost movement
- Selected-department payroll breakdown
- Data-quality and interpretation notes

## Data and controls

- Source: `Phase 1/Task 4/pulseiq_task4.duckdb`
- Database connection: read-only
- Four Task 9 excluded payroll IDs remain excluded.
- Department groups below five employees are suppressed.
- Original source database was not modified.

## Why this improvement was selected

The dashboard extends payroll analysis by connecting company-level monthly movement to department-level contributions. It helps management identify where further investigation may be needed.

## Files created

- `payroll_cost_drilldown/app.py`
- `payroll_cost_drilldown/verify_payroll_drilldown.py`
- `payroll_cost_drilldown/evidence/`

## How it was tested

The automated verification script checked application syntax, database availability, payroll loading, exclusions, monthly history, September 2026 figures, privacy threshold, dashboard sections and read-only access.

## Test result

**16/16 automated checks passed.**

September 2026 results:

- Employees paid: 444
- Gross pay: ₹54,788,660.03
- Net pay: ₹48,089,678.30
- Employer cost: ₹55,519,621.87
- Payroll records after exclusions: 7,340
- Available monthly history: 18 months

## Evidence

Four dashboard screenshots were captured and saved:

- `payroll_cost_drilldown/evidence/01_company_payroll_snapshot.png`
- `payroll_cost_drilldown/evidence/02_monthly_payroll_trend.png`
- `payroll_cost_drilldown/evidence/03_department_contribution.png`
- `payroll_cost_drilldown/evidence/04_department_drilldown.png`

## What I learned

The drill-down connects overall payroll movements with department-level analysis. A change in employer cost is an indicator for investigation, not proof of its cause. Headcount, overtime, variable pay and employee mix should be considered before drawing management conclusions.

## Assistance disclosure

AI assistance was used to help draft the implementation and verification code. The dashboard was run and its results were checked against the project database. The work should therefore be represented as AI-assisted rather than as an entirely independent implementation.
