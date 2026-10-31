# Task 8: Team Productivity Analytics

## Overview

This task develops a Team Productivity Analytics dashboard to evaluate team performance, delivery efficiency, workload health, and work-item progress.

## Objectives

- Analyse team productivity and delivery performance.
- Monitor blocked and reopened work items.
- Review team health and performance indicators.
- Present productivity insights through an interactive dashboard.
- Validate important calculations independently.

## Project Files

| File / Folder | Description |
|---|---|
| `app.py` | Streamlit dashboard application |
| `sql/team_productivity_views.sql` | SQL views for team productivity metrics |
| `requirements.txt` | Python dependencies |
| `evidence/` | Dashboard screenshots and visual evidence |
| `verification/` | Manual verification scripts, SQL, calculations, and results |

## Dashboard Sections

- Team Performance
- Delivery Performance
- Blocked and Reopened Work
- Team Health

## Verification

The `verification/` directory contains:

- `manual_verification.py` — independent verification script
- `manual_verification.sql` — SQL-based checks
- `manual_calculation_worksheet.txt` — manual calculation reference
- `manual_verification_report.txt` — verification summary
- `manual_verification_results.csv` — recorded verification results

## Technology Stack

- Python
- SQL
- DuckDB
- Streamlit
- Pandas

## Run the Dashboard

From the Task 8 directory:

```bash
pip install -r requirements.txt
streamlit run app.py


```

## Evidence

Dashboard screenshots are available in the `evidence/` directory.

## Deliverable

A team productivity analytics dashboard supported by SQL metric views, independent verification, and visual evidence.
