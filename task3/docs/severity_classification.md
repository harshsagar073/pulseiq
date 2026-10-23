# Severity Classification and Gate Policy

## Critical — block publication when confirmed
- DQ-C01 Payroll-to-ledger reconciliation.
- DQ-C02 Ledger entries balance.
- DQ-C03 Payroll employee/run keys are unique.
- DQ-C04 Payroll employee foreign keys exist.
- DQ-C12 Employee dimension history does not overlap.

A confirmed failure in these integrity checks should block publication
of affected financial or employee reporting until investigated and
resolved, or explicitly accepted by an authorized data owner.

## Critical — operational gate requiring a real signal
- DQ-C13 Pipeline freshness.

If the ETL run log is absent or no successful timestamp can be proven,
freshness is UNAVAILABLE, not PASS. For a release that requires verified
freshness, hold publication until the log is available and validated.
Do not create a synthetic successful timestamp.

## Warning — review before business use
- DQ-C05 Attendance after exit.
- DQ-C06 Unpaid attendance versus payroll LOP.
- DQ-C07 Invoice arithmetic.
- DQ-C08 Expense arithmetic.
- DQ-C09 Task dates.
- DQ-C10 Leave dates.
- DQ-C11 Prediction freshness.

Warnings should be assigned to the relevant data owner. Escalate to a
block when the finding is confirmed to materially affect a published
metric or decision.

## Privacy suppression
- DQ-C14 Minimum group size.

Suppress undersized manager-facing aggregates before display or export.
This is a disclosure-control action, not necessarily a reason to reject
the underlying warehouse load. The currently configured thresholds are
provisional because the local metric dictionary does not specify them.
Obtain policy-owner approval before treating those thresholds as final.

## Status meanings
- PASS: query returned zero findings.
- FAIL: query returned one or more findings.
- UNAVAILABLE: the required evidence/table is missing, so the check
  cannot be evaluated honestly.
- ERROR: execution failed; investigate before relying on the check.

Do not convert FAIL, UNAVAILABLE, or ERROR to PASS merely to obtain a
green summary.
