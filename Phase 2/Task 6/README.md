# PulseIQ — Task 6: Attendance and Leave Dashboard

## Objective
Explore monthly attendance, department attendance, late arrivals, overtime, approved leave and calendar holiday context.

## Run the dashboard
Activate the project virtual environment, then run:

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

## Data sources
The dashboard reads these validated Task 1 CSV files:
- `fact_attendance_monthly.csv`
- `fact_leave.csv`
- `dim_date.csv`

Expected source directory:
Phase 1/Task 1/validated/

## Metric definitions
- Attendance rate = total present days / total scheduled days × 100.
- Late arrivals and overtime are summed across the selected departments.
- Leave analysis counts approved requests and sums their reported leave days by leave type.
- Approved leave is grouped by request start date where monthly analysis is used; days are not spread across the entire leave period.
- Holiday and weekend charts provide calendar context only. They do not prove holidays caused attendance changes.
- Unusual months are flagged using the largest absolute difference from the median monthly attendance rate. Investigate these months before attributing causes.

## Evidence
Save dashboard screenshots in the `evidence/` directory after verifying the filters and charts.
