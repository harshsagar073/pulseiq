# PulseIQ — Task 19 Metric Lineage

## 1. M01 — Headcount

```mermaid
flowchart TD
 A["PulseIQ Dataset.xlsx"] --> B["Task 1 ETL and validation"]
 B --> C["Task 1 validated CSVs"]
 C --> D["Task 2 DuckDB warehouse"]
 D -. "Task 4 raw-table loading method not recorded" .-> E["raw.fact_headcount_monthly"]
 E --> F["Task 4 metric_views.sql"]
 F --> G["governed.m01_headcount"]
 G --> H["Task 15 Executive Scorecard"]
```

- Grain: month and department
- Suppression: groups smaller than 5

## 2. M09 — Payroll Cost

```mermaid
flowchart TD
 A["PulseIQ Dataset.xlsx"] --> B["Task 1 ETL and validation"]
 B --> C["Task 1 validated CSVs"]
 C --> D["Task 2 DuckDB warehouse"]
 D -. "Task 4 raw-table loading method not recorded" .-> E["raw.fact_payroll"]
 E --> F["Task 4 metric_views.sql"]
 F --> G["governed.m09_payroll_cost"]
 G --> H["Task 15 Executive Scorecard"]
```

- Formula: SUM(employer_cost)
- Grain: month and department
- Suppression: groups smaller than 5
- Unit: INR

## 3. M13 — Attendance Rate

```mermaid
flowchart TD
 A["PulseIQ Dataset.xlsx"] --> B["Task 1 ETL and validation"]
 B --> C["Task 1 validated CSVs"]
 C --> D["Task 2 DuckDB warehouse"]
 D -. "Task 4 raw-table loading method not recorded" .-> E["raw.fact_attendance_monthly"]
 E --> F["Task 4 metric_views.sql"]
 F --> G["governed.m13_attendance_rate"]
 G --> H["Task 15 Executive Scorecard"]
```

- Formula: (present_days + 0.5 * half_days_unpaid) / scheduled_days
- Grain: month and department
- Suppression: groups smaller than 5
- Unit: ratio; multiply by 100 for percentage display

## 4. M16 — Revenue

```mermaid
flowchart TD
 A["PulseIQ Dataset.xlsx"] --> B["Task 1 ETL and validation"]
 B --> C["Task 1 validated CSVs"]
 C --> D["Task 2 DuckDB warehouse"]
 D -. "Task 4 raw-table loading method not recorded" .-> E["raw.fact_ledger"]
 E --> F["Task 4 metric_views.sql"]
 F --> G["governed.m16_revenue"]
 G --> H["Task 15 Executive Scorecard"]
```

- Formula: -SUM(signed_amount_debit_positive)
- Grain: posting month and account code
- Revenue account codes: 4001–4004
- Unit: INR; preserve account-level values

## 5. M18 — Operating Margin

```mermaid
flowchart TD
 A["PulseIQ Dataset.xlsx"] --> B["Task 1 ETL and validation"]
 B --> C["Task 1 validated CSVs"]
 C --> D["Task 2 DuckDB warehouse"]
 D -. "Task 4 raw-table loading method not recorded" .-> E["raw.fact_ledger"]
 E --> F["Task 4 metric_views.sql"]
 F --> G["governed.m18_operating_margin"]
 G --> H["Task 15 Executive Scorecard"]
```

- Formula: 100 * net_profit / revenue, rounded to 2 decimal places
- Grain: company and posting month
- Unit: percent
