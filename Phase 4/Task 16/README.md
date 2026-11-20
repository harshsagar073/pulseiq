
# PulseIQ — Task 16
## Automated Monthly Report Builder and Release Candidate

### Overview
Automated monthly PDF report generation using the governed Task 4 metric layer.

### Report Contents
1. Executive KPI Summary
2. Department Performance
3. Department Payroll Chart
4. Department Headcount Chart
5. Revenue and Net Profit Trend
6. Anomaly Monitoring
7. Forward Headcount Forecast
8. Methodology and Limitations

### Requirements
- Python 3.13 recommended
- Complete PulseIQ project repository
- Phase 1 Task 4 DuckDB database

### Installation
From the project root:

    python3 -m venv .venv
    source .venv/bin/activate
    cd "Phase 4/Task 16"
    python -m pip install -r requirements.txt

### Generate a Monthly Report

    python build_report.py --month 2026-09

Replace 2026-09 with the required YYYY-MM reporting month.

### Verification

    python scripts/verify_task16.py

### Data Rules
- Actual KPI values come from governed Task 4 metric views.
- Suppressed groups are excluded, not treated as zero.
- Leadership department D00 is excluded from department comparisons.
- Attrition and attendance use governed group_size weighting.
- Revenue is aggregated from visible account-level records.
- Task completion is sprint/team grain, not a monthly KPI.
- Forecasts are estimates, separate from actual results.
- Anomaly flags are monitoring signals, not proof of fraud.

### Dynamic Departments
Department names are read from the source department dimension, not hardcoded.

### Sample Reports
- PulseIQ_Monthly_Report_2026-08.pdf
- PulseIQ_Monthly_Report_2026-09.pdf

### Current Validation
- Automated checks: 7 passed
- Failed checks: 0
- August and September 2026 reports generated.
- Clean-folder test completed on 20 November 2026: 7/7 checks passed.
- Permanent Python 3.13.12 environment tested successfully.
- Local macOS LaunchAgent registered for monthly execution.
- GitHub Actions is not configured; the source database remains local because this repository is public.

### Limitations
- Suppressed values are unavailable.
- Attendance and attrition are governed aggregate estimates.
- Forecasts are estimates, not actual results.
- Report completeness depends on source data availability.

### Local Monthly Automation

A macOS LaunchAgent runs the report builder on the first day of each month at 9:00 AM local time.

- LaunchAgent: `com.pulseiq.monthly-report`
- Schedule file: `~/Library/LaunchAgents/com.pulseiq.monthly-report.plist`
- Runtime and logs: `~/Library/Application Support/PulseIQ/Task16/`
- The runner automatically selects the previous calendar month.
- The Mac must be available and the project database must remain at its configured location.
- The generated PDF is saved in the Task 16 `reports/` folder.

The schedule is registered on the development Mac. It is not a GitHub Actions workflow. The DuckDB database is intentionally excluded from the public repository to protect workforce and payroll data.
