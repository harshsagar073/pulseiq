# PulseIQ — Phase 4, Task 17
## Public Production Release Candidate

PulseIQ is a public-facing executive dashboard presenting historical company-level KPI aggregates.

## Live dashboard

**Public URL:** https://pulseiq-hjeftkz9upquduptdraafg.streamlit.app/

The application is hosted on Streamlit Community Cloud and deployed from the GitHub repository.

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

## Hosting platform comparison

| Platform | Free hosting considerations | Suitability |
|---|---|---|
| Streamlit Community Cloud | Free hosting for Streamlit applications, with platform resource and usage limits | Direct fit for this Streamlit dashboard and GitHub deployment |
| Render | Free web services spin down after 15 minutes without incoming traffic; waking can take around a minute | Possible alternative, but requires additional deployment configuration |
| Railway | Free plan provides limited monthly resource credit; usage beyond available credit may require payment | Possible alternative, but less predictable for ongoing free hosting |

### Hosting decision

Streamlit Community Cloud was selected because the application is built with Streamlit, deployment integrates directly with GitHub, and the current public dataset is a small CSV export of approximately 5.1 KB.

This hosting arrangement is suitable for a portfolio and demonstration release. It is not represented as a guaranteed enterprise production hosting arrangement.

Platform documentation:

- Streamlit Community Cloud: https://docs.streamlit.io/deploy/streamlit-community-cloud
- Render free services: https://render.com/docs/free
- Railway pricing: https://docs.railway.com/pricing

## Data source and reporting cutoff

The dashboard uses a point-in-time export of governed company-level KPI views from the PulseIQ warehouse.

Current reporting cutoff: **2026-09-01**

The public dataset contains company-level aggregates only. It does not publish employee-level records, department identifiers, team identifiers, client identifiers, or raw payroll records. Suppressed records are excluded from the public export.

The exported CSV contains 81 monthly records and is approximately 5.1 KB.

## Data refresh schedule and limitations

**Automated schedule:** Monthly, on the first calendar day at 9:00 AM India local time, using a macOS LaunchAgent on the approved local machine.

**Automation script:** `scripts/run_scheduled_refresh.py`

The scheduled process:

1. Checks whether the approved local source database has changed since the last public export.
2. Skips publication when the source database has not changed.
3. If the source has changed, runs the public-data export script.
4. Runs the Task 17 verification script.
5. Stages only `data/company_kpis.csv` and `data/metadata.json`.
6. Commits and pushes the verified public aggregates to the GitHub `main` branch.
7. Allows Streamlit Community Cloud to receive the updated repository data.

**Scheduler status:** The macOS LaunchAgent `com.pulseiq.task17-refresh` is installed and enabled. A manual trigger completed successfully with exit code 0. The test correctly skipped publication because the approved source database had not changed.

**Important operating limitations:**

- This is local Mac automation, not a cloud-hosted scheduler. The Mac must be powered on, awake, and logged in for the scheduled process to run.
- GitHub authentication must remain available to the scheduled process for an updated-data push to succeed.
- The approved source database remains local and is not uploaded to GitHub.
- Only verified, sanitized company-level aggregates are published.
- New reporting values require an updated approved source database. If no updated source is available, the existing snapshot and reporting cutoff are retained.
- A scheduled run, GitHub deployment, or app restart does not itself create new reporting data.

The reporting cutoff represents the latest available reporting period in the exported data, not the deployment date.

## Privacy and security

- Publish company-level aggregates only.
- Do not publish employee-level or department-level records.
- Exclude suppressed records from public exports.
- Do not commit passwords, API keys, access tokens, or other secrets.
- Use platform-managed secrets if future integrations require credentials.

## Evidence

The Task 17 evidence folder contains:

- `05_mobile_executive_overview.png`
- `06_mobile_monthly_trends.png`
- `07_pulseiq_nav.png`

These screenshots document the mobile dashboard and navigation.

## Verification

Run the verification script from the repository root:

```bash
python "Phase 4/Task 17/scripts/verify_task17.py"
```

The latest verification completed successfully with **16/16 checks passed**.

## Run locally

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd "Phase 4/Task 17"
streamlit run app.py
```

## Release status

- Public Streamlit deployment: completed.
- Public dashboard URL: available above.
- Mobile screenshots: saved in the evidence folder.
- Data validation: 16/16 checks passed.
- Privacy controls: documented and verified.
- Data refresh: monthly review procedure documented; updated source data is required before publishing new KPI values.
