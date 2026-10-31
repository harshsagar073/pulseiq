# PulseIQ – Task 9: Payroll Cost Dashboard and Reconciliation

## Objective
Analyze payroll costs by month and department, calculate cost per employee, and reconcile monthly payroll totals against the official PQ-09 answer key.

## Features
- Gross payroll, net payroll, and employer cost KPIs
- Monthly payroll cost trends
- Department-wise payroll analysis
- Cost per employee-month
- Monthly reconciliation against PQ-09
- Small-group privacy suppression (minimum group size: 5)
- Documentation of four excluded payroll records

## Data and reconciliation
The dashboard reads the Task 4 DuckDB database in read-only mode. Original source data is preserved.

Four records are excluded from Task 9 reporting calculations:
- PI-X0001 – duplicate employee-month record
- PI-X0002 – duplicate employee-month record
- PI-X0003 – employee ID missing from the employee master
- PI-X0004 – employee ID missing from the employee master

All 18 months from April 2025 through September 2026 reconcile with the official PQ-09 answer key.

## Evidence
- evidence/monthly_reconciliation.csv
- evidence/excluded_payroll_rows.csv

## Run the dashboard
pip install -r requirements.txt
streamlit run app.py

## Data protection
The source database is accessed read-only. Original payroll records are not deleted or modified. Department-month groups with fewer than five employees are suppressed.
