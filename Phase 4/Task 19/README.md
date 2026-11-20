# Task 19 — Metrics API and Data Lineage

## Overview

Task 19 exposes five governed PulseIQ business metrics through a FastAPI REST API. Each response includes the metric value, definition, formula, source table, transformation, governed metric view, dashboard consumer, and data freshness information.

The API reads the Task 4 DuckDB database in read-only mode.

## Selected Metrics

| Metric ID | Metric | Governed View | Source Table |
|---|---|---|---|
| M01 | Headcount | `governed.m01_headcount` | `raw.fact_headcount_monthly` |
| M09 | Payroll Cost | `governed.m09_payroll_cost` | `raw.fact_payroll` |
| M13 | Attendance Rate | `governed.m13_attendance_rate` | `raw.fact_attendance_monthly` |
| M16 | Revenue | `governed.m16_revenue` | `raw.fact_ledger` |
| M18 | Operating Margin | `governed.m18_operating_margin` | `raw.fact_ledger` |

## Run Locally

From the repository root:

```bash
cd "/Users/admin/Desktop/PulseIQ"

"Phase 4/Task 19/.venv/bin/python3" -m uvicorn "Phase 4.Task 19.app:app" --host 127.0.0.1 --port 8000
```

## API Documentation

When the API is running, open:

- Swagger UI: `http://127.0.0.1:8000/docs`
- OpenAPI schema: `http://127.0.0.1:8000/openapi.json`
- Health check: `http://127.0.0.1:8000/health`
- Metric catalogue: `http://127.0.0.1:8000/api/v1/metrics`

## Metric Endpoints

| Metric | Endpoint |
|---|---|
| Headcount | `/api/v1/metrics/headcount` |
| Payroll Cost | `/api/v1/metrics/payroll-cost` |
| Attendance Rate | `/api/v1/metrics/attendance-rate` |
| Revenue | `/api/v1/metrics/revenue` |
| Operating Margin | `/api/v1/metrics/operating-margin` |

Use the optional `period` query parameter in `YYYY-MM` format.

Example:

```bash
curl "http://127.0.0.1:8000/api/v1/metrics/headcount?period=2026-09"
```

## Example Response

A metric response includes:

- Metric ID and name
- Reporting period
- Metric values and dimensions
- Definition and formula
- Source table and transformation
- Governed metric view
- Dashboard consumer
- Last database modification timestamp
- Latest available data period
- Freshness statement

Suppressed department-level values are returned as null and marked as suppressed. They must not be interpreted as zero.

## Metric Notes

- **M01 Headcount:** monthly department-level headcount; groups below five are suppressed.
- **M09 Payroll Cost:** sum of employer cost by month and department; groups below five are suppressed. Unit: INR.
- **M13 Attendance Rate:** adjusted present days divided by scheduled days; groups below five are suppressed. API values are ratios, not percentages.
- **M16 Revenue:** revenue account values for account codes 4001–4004. Results retain account-level detail and must not be mistaken for a consolidated company total.
- **M18 Operating Margin:** company-level monthly net profit divided by revenue, expressed as a percentage.

## Data Freshness

The latest available reporting period for the selected metrics is September 2026.

The Task 4 database file modification timestamp is recorded separately from the latest data period. A file modification timestamp does not prove when the source data was originally ingested.

The API reports both pieces of information so consumers can assess freshness without assuming that a recent file timestamp means recent source data.

## Data Lineage

The five end-to-end metric lineage diagrams are maintained in:

`lineage/metric_lineage.md`

The documented upstream path is:

PulseIQ Dataset.xlsx → Task 1 ETL and validation → validated CSV files → Task 2 DuckDB warehouse → Task 4 raw tables → Task 4 governed metric views → Task 15 Executive Scorecard.

The Task 4 raw-table loading method was not recorded in the available project documentation. This gap is explicitly shown as a dotted connection in each diagram.

## Verification

The five metric endpoints were tested locally for reporting period `2026-09`. The health check and metric catalogue endpoints also returned successfully.

## Deployment

The API is designed to run as a separate service from the Streamlit dashboard using the same GitHub repository. A deployment requires a hosting service configured with the repository and access to the Task 4 DuckDB database. No public deployment is claimed by this local verification.

## Technology

- Python
- FastAPI
- Uvicorn
- DuckDB
- Mermaid
