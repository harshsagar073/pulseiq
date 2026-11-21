# Phase 4 — Task 20: Board Pack and Final Handover

## Deliverables
- `board_presentation/PulseIQ_Board_Presentation_v1.0.0.pptx`
- `board_presentation/build_board_deck.py`
- `RELEASE_NOTES.md`
- `final_checks/`
- `final_challenge/`
- `demo/`
- `evidence/`

## Board pack
The presentation contains nine slides covering the September 2026 executive snapshot, workforce health, payroll and profitability, payroll anomaly exposure, receivables ageing, payment-record cash movement, department productivity, reconciliation quality, and board decisions.

## Important interpretation limits
- Task 11 P&L figures are for its analysed period, not September-only.
- Task 12 cash movement is based on payment records, not a complete cash-flow statement.
- Task 14 quantified anomaly exposure is a flagged amount, not confirmed loss.
- Forecast accuracy is not measurable yet because all forecast periods are future months.
- Task 13 attendance and late-arrival reconciliation exceptions remain disclosed.
- Task 12 invoice INV-00385 has a ₹100 difference.
- Do not rank suppressed or unavailable department productivity values.

## Verification
See the original verification outputs in the Phase 4 task folders and the final check summary in `final_checks/`.

## Final challenge — Payroll Cost Drill-down

Implemented on the separate branch `final-challenge/payroll-cost-drilldown`.

The AI-assisted Streamlit improvement includes monthly payroll KPIs, department contribution, month-on-month cost movement, department drill-down and privacy suppression for groups below five employees.

- App: `final_challenge/payroll_cost_drilldown/app.py`
- Verification: `final_challenge/payroll_cost_drilldown/verify_payroll_drilldown.py`
- Evidence: `final_challenge/payroll_cost_drilldown/evidence/`
- Automated verification: 16/16 checks passed.
- Source database: Task 4 DuckDB, accessed read-only.
- Task 9 exclusions: four payroll records remain excluded.

The implementation used AI assistance and is documented transparently in `final_challenge/FINAL_CHALLENGE_NOTES.md`.

## Demo

The submitted walkthrough is linked in `demo/DEMO_LINK_AND_AGENDA.md`. Its recorded duration is 8 minutes 3 seconds, longer than the suggested five-minute target.

## Links
- GitHub: https://github.com/harshsagar073/pulseiq
- Live API: https://pulseiqmetricsapi-guest.blue.sola.inc
- API health: https://pulseiqmetricsapi-guest.blue.sola.inc/health
- API documentation: https://pulseiqmetricsapi-guest.blue.sola.inc/openapi.json
- Metrics catalogue: https://pulseiqmetricsapi-guest.blue.sola.inc/api/v1/metrics

The live API is password-protected. Share the viewing password privately with the evaluator; never publish it in this repository.
