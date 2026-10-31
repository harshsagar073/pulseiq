
# PulseIQ — Task 2: Analytics Warehouse

## Overview

This project builds a DuckDB analytics warehouse from 25 PulseIQ source tables. It includes warehouse construction, relationship validation, row-count reconciliation, and documentation of reviewed data-quality exceptions.

## Project structure

- `scripts/build_warehouse.py` — builds the warehouse and tables.
- `scripts/fix_forecast_calendar.py` — extends the date dimension through March 2027.
- `scripts/check_relationships.py` — checks relationships and exports orphan evidence.
- `docs/er_diagram.md` — Mermaid warehouse relationship diagram.
- `docs/data_quality_notes.md` — row-count reconciliation and data-quality explanations.
- `evidence/row_count_reconciliation.csv` — source-to-warehouse row counts.
- `evidence/orphan_check_summary.csv` — relationship validation summary.
- `evidence/orphan_rows.csv` — unmatched relationship rows.
- `.gitignore` — excludes local database and temporary files.

## Requirements

- Python 3
- DuckDB Python package

Install DuckDB if needed:

    python -m pip install duckdb

## Build and validate

Run these commands from the Task 2 directory:

    python scripts/build_warehouse.py
    python scripts/fix_forecast_calendar.py
    python scripts/check_relationships.py

Run the calendar repair after the build because the build recreates the source date dimension.

## Validation notes

- 25 source tables loaded.
- 62,295 source rows reconciled.
- 90 additional calendar rows support forecasts through 2027-03-31.
- 34 relationships are checked.
- Two payroll employee-key exceptions are documented and retained for source-data review.
- Join employee-history facts through `employee_key` where applicable to preserve the correct historical employee version.

## Local database

The generated `pulseiq_warehouse.duckdb` file is local and excluded from Git. Run the build scripts to recreate the warehouse.
cat README.md
