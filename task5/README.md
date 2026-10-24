# PulseIQ Task 5 — Workforce & Headcount Dashboard

## Objective

Build a Streamlit dashboard for workforce and headcount analysis using governed metric views.

## Features

- KPI cards for headcount, hires, exits, and current employee records
- Monthly headcount trend
- Department mix
- Employees by location tier
- Employees by work mode
- Department and date filters
- Insight sentence below each chart

## Files

- `app.py`: Main dashboard
- `pages/1_Workforce_Insights.py`: Additional workforce insights
- `scripts/setup_database.py`: Prepares the Task 5 database and creates dashboard views
- `sql/dashboard_views.sql`: SQL definitions exported from the working database
- `docs/ceo_questions.md`: Five CEO questions
- `evidence/validation.txt`: Database validation evidence

## Requirements

Install dependencies in your active Python environment with:

`python -m pip install -r task5/requirements.txt`

## Run from the repository root

1. Ensure the original `pulseiq.duckdb` database exists in the repository root.
2. Run `python task5/scripts/setup_database.py`.
3. Run `python -m streamlit run task5/app.py`.
4. Open `http://localhost:8501` in your browser.

If the Task 5 database does not exist, the setup script copies the repository-root database to `task5/pulseiq_task5.duckdb` before creating the dashboard views. DuckDB files are excluded from Git, so the source database must be provided separately.

## Governance

The Streamlit application should read from views in the `governed` schema instead of querying raw tables directly. The setup script creates seven dashboard views using the existing metric layer and workforce source data.

## Design

Use clear chart titles, restrained colours, whole-number employee counts, working filters, and a short insight for each chart. Validate business definitions before making staffing decisions.
