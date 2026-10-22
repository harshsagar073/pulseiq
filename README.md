# PulseIQ ETL Pipeline

## Overview

This project implements a Python ETL validation pipeline for the PulseIQ analytics dataset. It reads tables from the existing DuckDB source, validates data against implemented structural and formal contract rules, and exports validated records, quarantined records, and a summary report.

## Objectives

- Process the available source tables.
- Apply implemented data-contract checks to formally contracted feeds.
- Preserve source data without modifying raw DuckDB tables.
- Quarantine rejected records for investigation.
- Produce repeatable validation outputs and row-count summaries.

## Technology Stack

- Python
- pandas
- DuckDB
- CSV

## Validation Results

| Metric | Result |
|---|---:|
| Tables processed | 25 |
| Total input rows | 62,315 |
| Passed rows | 62,295 |
| Quarantined rows | 20 |

The row-accounting check passed for all 25 tables. A second execution produced an identical `etl_summary.csv`.

## Formal Contract Tables

- `fact_task`
- `fact_forecast`
- `fact_attrition_risk`
- `fact_anomaly`

The other tables currently receive structural processing rather than equivalent full row-level business-rule validation.

## Output Files

- `etl_summary.csv` — per-table input, passed, and quarantined counts.
- `validated/` — accepted records.
- `quarantine/` — records rejected by implemented checks.
- `first_run_summary.csv` — saved summary used for repeatability comparison.
- `contract_notes.md` — contract rules, validation scope, and limitations.

## How to Run

Activate the project virtual environment, then run:

```bash
python etl.py
```

Compare the summary with the saved first-run results:

```bash
diff -u first_run_summary.csv etl_summary.csv
```

No output from `diff` indicates that the files are identical.

## Limitations

Validation coverage depends on the rules implemented in `etl.py`. Passing these checks does not establish that every field and business rule across all 25 tables has been fully validated. Quarantined records should be reviewed before downstream use.
