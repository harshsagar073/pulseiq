# PulseIQ Task 3 — Data Quality Gatekeeper

## Objective
Run 14 data-quality checks, record auditable results, and test SQL
predicates using deliberately invalid data in isolated DuckDB tables.

## Project structure
- `scripts/run_dq_checks.py` — production-style runner and result history
- `sql/dq_checks.sql` — SQL reference generated from the runner definitions
- `tests/test_dq_checks.py` — isolated predicate tests
- `docs/data_quality_notes.md` — definitions, limitations, and interpretation
- `docs/severity_classification.md` — block, warn, and privacy policy
- `evidence/` — result CSVs, comparison report, and handover

## Run checks
From the project root:

```bash
/Users/admin/Desktop/PulseIQ/task1/.venv/bin/python task3/scripts/run_dq_checks.py
```

## Run isolated tests
```bash
/Users/admin/Desktop/PulseIQ/task1/.venv/bin/python -m unittest discover -s task3/tests -p 'test_*.py' -v
```

## Safety
The runner uses `task3/pulseiq_dq.duckdb`, an isolated copy of the Task 2
warehouse. Tests use in-memory DuckDB tables. Do not load quarantined rows
into Task 2 just to make a quality check fail.

## Known limitations
- `etl_run_log` is absent from the Task 2 warehouse, so DQ-C13 is
  UNAVAILABLE until a genuine successful-load timestamp is recorded.
- DQ-C14 thresholds require confirmation from the business owner.
- DQ-C06 differences require business-rule review.
- The separate `unlock_PQ-03` file was not found during the local search.
