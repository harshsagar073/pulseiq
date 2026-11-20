# PulseIQ — Phase 4, Task 17
## Public Production Release Candidate

PulseIQ is a public-facing executive dashboard presenting historical company-level KPI aggregates.

## Dashboard sections

1. Executive Overview — company-level KPI cards for a selected reporting month.
2. Monthly Trends — historical trends for available monthly KPI records.
3. Data & Methodology — metric definitions, source information, privacy controls, and limitations.

## Technology

- Python
- Streamlit
- Pandas
- GitHub
- Streamlit Community Cloud

## Data source and reporting cutoff

The dashboard uses a point-in-time export of governed company-level KPI views from the PulseIQ warehouse.

Current reporting cutoff: **2026-09-01**

The public dataset contains company-level aggregates only. It does not publish employee-level records, department identifiers, team identifiers, client identifiers, or raw payroll records. Suppressed records are excluded from the public export.

## Data refresh and limitations

The published CSV and metadata files are a point-in-time snapshot. New reporting values require an updated approved source database.

The reporting cutoff represents the latest available reporting period in the exported data, not the deployment date. Do not describe the dashboard as refreshed unless the underlying approved data has actually been updated.

## Run locally

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r "Phase 4/Task 17/requirements.txt"
cd "Phase 4/Task 17"
streamlit run app.py
fv
plain text
