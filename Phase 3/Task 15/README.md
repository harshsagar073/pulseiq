# PulseIQ — Task 15: Executive Company Health Scorecard

## 1. Project Overview

Task 15 delivers a one-page executive company health scorecard for PulseIQ.

The dashboard presents eight headline KPIs for a selected reporting month, including their current values, available targets, period-over-period trends and target status. It also provides KPI detail sections explaining metric definitions, data sources and interpretation.

The dashboard is built with Streamlit and uses the official governed metric layer from Phase 1, Task 4.

## 2. Technology Stack

- Python
- Streamlit
- DuckDB
- Pandas
- Plotly (where used by the dashboard)
- SQL

## 3. Data Source and Governance

Primary database:

`Phase 1/Task 4/pulseiq_task4.duckdb`

The scorecard reads metrics from the official `governed` schema rather than independently recalculating metrics from raw fact tables.

The dashboard uses these governed views:

| KPI | Governed metric view |
|---|---|
| Headcount | `governed.m01_headcount` |
| Monthly Attrition | `governed.m04_monthly_attrition` |
| Revenue | `governed.m16_revenue` |
| Net Profit | `governed.m17_net_profit` |
| Operating Margin | `governed.m18_operating_margin` |
| Payroll Cost | `governed.m09_payroll_cost` |
| Attendance Rate | `governed.m13_attendance_rate` |
| Task Completion | `governed.m22_task_completion_rate` |

KPI target information is sourced from `raw.kpi_targets`.

## 4. Selected Executive KPIs

1. **Headcount** — workforce size and staffing context.
2. **Monthly Attrition** — employee exits relative to opening headcount.
3. **Revenue** — company revenue performance.
4. **Net Profit** — financial result after expenses.
5. **Operating Margin** — operating profitability relative to revenue.
6. **Payroll Cost** — workforce compensation cost.
7. **Attendance Rate** — workforce attendance performance.
8. **Task Completion** — operational delivery performance.

These eight KPIs combine workforce, financial and operational perspectives in one executive view.

## 5. Targets and Status Rules

Targets are available for the following selected KPIs:

| KPI | Target | Status interpretation |
|---|---:|---|
| Monthly Attrition | 1.00% | At or below target is on target |
| Attendance Rate | 94.00% | At or above target is on target |
| Task Completion | 80.00% | At or above target is on target |

Targets are not configured for headcount, revenue, net profit, operating margin or payroll cost. These metrics are therefore labelled **Not Configured**, rather than being assigned invented targets.

The target table contains 180 department-month records across 18 months. Task completion target coverage is 162 records; some department-month target values are missing.

## 6. Metric Interpretation and Limitations

- **Headcount:** The displayed value is the sum of visible, unsuppressed department values. Suppressed department groups are excluded, so this should not automatically be interpreted as the complete company headcount.
- **Payroll Cost:** The displayed value is a visible-department subtotal. Suppressed department groups are excluded.
- **Attendance Rate:** The displayed value is an employee-weighted estimate using the governed department attendance ratios. It is not an exact company-wide attendance ratio because the governed view does not expose the scheduled-day denominator.
- **Monthly Attrition:** Department percentages are weighted using opening headcount. Suppressed groups are excluded.
- **Revenue:** Department/account-level visible revenue records are aggregated for the reporting month.
- **Net Profit and Operating Margin:** These are read from the company-level governed monthly metrics.
- **Task Completion:** The dashboard uses the latest available sprint, not a monthly task-completion period. The displayed target is a benchmark derived from available department target records.
- **Suppression:** Suppressed values are excluded, not treated as zero.

Trends compare the selected reporting month with the previous calendar month for monthly KPIs. Task completion compares the latest available sprint with its preceding sprint.

## 7. Why Eight KPIs?

Eight KPIs provide a balanced executive overview across three business dimensions:

- Workforce health: Headcount, Monthly Attrition and Attendance Rate.
- Financial health: Revenue, Net Profit, Operating Margin and Payroll Cost.
- Operational health: Task Completion.

This selection helps leadership see business outcomes alongside workforce and delivery context.

## 8. Suggested Five-KPI Executive Version

For a shorter executive summary, retain:

1. Revenue
2. Net Profit
3. Operating Margin
4. Monthly Attrition
5. Attendance Rate

The following three KPIs can be removed from the shorter version:

- **Headcount:** Useful context, but not a direct measure of business performance.
- **Payroll Cost:** Its financial impact is also reflected in net profit and operating margin.
- **Task Completion:** Important for operational management, but more detailed than the five-KPI executive summary.

The eight-KPI version remains the full scorecard; the five-KPI version is a proposed concise alternative.

## 9. Run the Dashboard

From the Task 15 folder:

```bash
python -m pip install -r requirements.txt
streamlit run app.py

```
