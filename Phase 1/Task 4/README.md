
# PulseIQ Task 4 — Governed Metric Layer

## Objective

Create reusable SQL views for the 28 official PulseIQ metrics so dashboards can use consistent definitions from a governed metric layer.

## Folder Structure

- `06_Metric_Layer/metric_catalog.sql` — official metric definitions and metadata.
- `06_Metric_Layer/metric_views.sql` — SQL definitions for the 28 governed metrics.
- `06_Metric_Layer/hand_checks.sql` — source-to-view comparison queries and forecast availability checks.
- `pulseiq_task4.duckdb` — Task 4 working copy of the database.
- `evidence/` — supporting validation evidence.

## Metric Views

The governed schema contains these 28 views:

1. `m01_headcount`
2. `m02_hires`
3. `m03_exits`
4. `m04_monthly_attrition`
5. `m05_rolling_12m_attrition`
6. `m06_voluntary_attrition`
7. `m07_gross_pay`
8. `m08_net_pay`
9. `m09_payroll_cost`
10. `m10_cost_per_head`
11. `m11_overtime_share`
12. `m12_variable_pay_share`
13. `m13_attendance_rate`
14. `m14_late_arrival_rate`
15. `m15_lop_days`
16. `m16_revenue`
17. `m17_net_profit`
18. `m18_operating_margin`
19. `m19_payroll_pct_revenue`
20. `m20_dso`
21. `m21_overdue_receivables`
22. `m22_task_completion_rate`
23. `m23_on_time_delivery_rate`
24. `m24_velocity`
25. `m25_average_cycle_time`
26. `m26_anomaly_flag_rate`
27. `m27_high_risk_share`
28. `m28_forecast_error_mape`

## Governance and Privacy

- Metrics are exposed as reusable SQL views in the `governed` schema.
- The raw source tables are read as inputs; they are not intended to be changed by the metric layer.
- Minimum group-size rules are applied where specified in the metric dictionary.
- Suppressed metric values are returned as `NULL`, with a `suppressed` indicator where implemented.
- M22, M23, and M26 report percentage values using the `percent` unit.
- M26 anomaly flags are investigation leads, not proof of an error or misconduct.
- High-risk reporting is aggregated by department; named employees should not be ranked.

## Validation and Hand Checks

The SQL files were executed against the Task 4 database copy. All 28 governed views were created successfully.

Hand checks were run for M01 headcount, M02 hires, M03 exits, M04 monthly attrition, and M28 forecast availability.

- M01 values matched the source for departments D01–D10 for September 2026.
- M02 and M03 contain suppressed values for groups below the minimum group size. These must not be treated as ordinary numeric mismatches.
- M04 monthly attrition matched the independently calculated formula for departments D01–D10 for September 2026.

## Known Data Limitations

### M26 — Anomaly Flag Rate

All 405 records in `raw.fact_anomaly` currently have `flagged = 'Y'`. Consequently, the observed flag rate is 100% for each represented source-period group. This reflects the current source data and does not demonstrate that all records are genuine anomalies.

### M28 — Forecast Error (MAPE)

Forecasts for `headcount_end` cover October 2026 through March 2027. Actual monthly headcount currently ends in September 2026. Therefore, there are no matching actual values yet and the M28 view currently returns zero rows. MAPE should be calculated when actuals for forecast months become available; actual values must not be invented.

## Re-running the Metric Views

From the Task 4 directory, activate the project's virtual environment if needed, then run:

```bash
python - <<'PY'
import duckdb

con = duckdb.connect("pulseiq_task4.duckdb")
con.execute(open("06_Metric_Layer/metric_views.sql").read())

views = con.execute("""
    SELECT table_name
    FROM information_schema.views
    WHERE table_schema = 'governed'
    ORDER BY table_name
""").fetchall()

print("Governed views:", len(views))
for view in views:
    print(view[0])

con.close()
PY
```

Expected result: 28 governed metric views.

## Scope Note

This README records the current implementation and observed validation results. The existence of a view confirms that its SQL executes, but does not alone prove that every metric has been fully reconciled to every business rule or source ledger.
