# PulseIQ Task 5 — Workforce & Headcount Dashboard

## Objective
Build a Streamlit dashboard for workforce and headcount analysis.

## Features
- KPI cards for headcount, hires, exits, and current employee records
- Monthly headcount trend
- Department mix
- Employees by location tier
- Employees by work mode
- Department and date filters
- Insight sentence below each chart

## Files
- app.py: Main dashboard
- pages/1_Workforce_Insights.py: Additional workforce insights
- scripts/setup_database.py: Creates dashboard-specific governed views
- sql/dashboard_views.sql: SQL documentation
- docs/ceo_questions.md: Five CEO questions
- evidence/validation.txt: Validation evidence

## Run
From the PulseIQ project root, run:
1. python task5/scripts/setup_database.py
2. python -m streamlit run task5/app.py

Open http://localhost:8501 in your browser.

## Governance
The Streamlit application should read from views in the governed schema. The setup script creates dashboard views using the existing metric layer and workforce source data.

## Design
Use clear chart titles, restrained colours, whole-number employee counts, working filters, and a short insight for each chart. Validate business definitions before making staffing decisions.
