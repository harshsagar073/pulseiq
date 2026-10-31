# PulseIQ — Task 7: Attrition Analytics

## 1. Objective

Analyze workforce attrition using governed metrics. The dashboard presents monthly exits where data can safely be released, monthly attrition rates, tenure at exit where sufficient data is available, voluntary versus other exits where permitted, and aggregated predicted attrition risk.

Predictions are estimates for supportive HR conversations. They are not facts and must not be used as the sole basis for decisions about individuals.

## 2. Data Source

The dashboard reads the Task 4 governed database in read-only mode:

`Phase 1/Task 4/pulseiq_task4.duckdb`

Governed views used:

- `governed.m03_exits`
- `governed.m04_monthly_attrition`
- `governed.m05_rolling_12m_attrition`
- `governed.m06_voluntary_attrition`
- `governed.m27_high_risk_share`

## 3. Dashboard Features

- Monthly exit analysis using released governed counts.
- Department-level monthly attrition-rate comparison.
- Tenure-at-exit analysis when the minimum group size is met.
- Voluntary versus other exits where the governed data permits.
- Aggregated high-risk share without individual predictions.
- Filters for exploring available periods and departments, where provided by the app.

## 4. Privacy and Responsible Interpretation

- No employee names, employee IDs, individual risk scores, or individual prediction reasons are displayed.
- Governed exit counts that are suppressed are not reconstructed from raw counts.
- Tenure results require at least five matching exit records; tenure buckets with fewer than five are hidden.
- Risk groups require at least ten records and must not be suppressed in the governed metric view.
- Suppressed values are not treated as zero.
- Predicted risk is an estimate, not proof that an employee will leave.
- Predictions should support constructive HR conversations, not determine employment decisions.

## 5. How to Run

From the PulseIQ project root, install the Task 6 environment dependencies if they are not already installed:

```bash
"Phase 2/Task 6/.venv/bin/python" -m pip install -r "Phase 2/Task 7/requirements.txt"
```

Launch the Task 7 dashboard:

```bash
"Phase 2/Task 6/.venv/bin/python" -m streamlit run "Phase 2/Task 7/app.py"
```

The app uses the existing governed database in read-only mode. It does not create or modify the database.

## 6. Findings

1. **Department attrition comparison:** The governed monthly attrition-rate view has released values for multiple departments, allowing comparison using the rates that pass privacy checks.
2. **Exit-count privacy:** In the inspected dataset, 891 department-month records were present in the governed exit view; only one exit count was released and 890 were suppressed under the minimum-count rule.
3. **Prediction limitations:** Aggregated risk estimates can help guide supportive conversations, but they do not establish that any individual will leave.

Findings are based on the available governed data and may change when filters or the dataset change.

## 7. Evidence

Evidence is stored in `evidence/`:

- `task7_dashboard.png` — main dashboard screenshot.
- `task7_department_attrition.png` — department attrition-rate summary.
- `task7_attrition_risk_predictions.png` — aggregated risk feed and prediction disclaimer.
- `task7_Three Find.png` — additional screenshot, if retained.
- `findings.md` — written findings.
