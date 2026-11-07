from pathlib import Path
import duckdb
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "pulseiq_task14.duckdb"
EVIDENCE_DIR = BASE_DIR / "evidence"

if not DB_PATH.exists():
    raise FileNotFoundError(
        "Task 14 database not found. Run scripts/build_task14.py first."
    )

con = duckdb.connect(str(DB_PATH), read_only=True)
checks = []

def record_check(name, passed, detail):
    checks.append({
        "check": name,
        "status": "PASS" if passed else "FAIL",
        "detail": str(detail),
    })
    print(f"[{'PASS' if passed else 'FAIL'}] {name}: {detail}")


try:
    counts = con.execute("""
        SELECT
            (SELECT COUNT(*) FROM stg_anomaly),
            (SELECT COUNT(*) FROM stg_forecast),
            (SELECT COUNT(*) FROM stg_attrition_risk),
            (SELECT COUNT(*) FROM stg_headcount)
    """).fetchone()

    anomaly_count, forecast_count, risk_count, headcount_count = counts

    record_check(
        "Anomaly source row count",
        anomaly_count == 405,
        f"{anomaly_count} rows; expected 405",
    )
    record_check(
        "Forecast source row count",
        forecast_count == 72,
        f"{forecast_count} rows; expected 72",
    )
    record_check(
        "Attrition risk source row count",
        risk_count == 430,
        f"{risk_count} rows; expected 430",
    )
    record_check(
        "Historical headcount source row count",
        headcount_count == 891,
        f"{headcount_count} rows; expected 891",
    )

    money = con.execute("""
        SELECT
            COUNT(money_at_risk),
            COUNT(*) - COUNT(money_at_risk),
            SUM(money_at_risk)
        FROM stg_anomaly
    """).fetchone()

    quantified, unquantified, total_money = money

    record_check(
        "Quantified anomaly records",
        quantified == 184,
        f"{quantified} quantified records; expected 184",
    )
    record_check(
        "Unquantified anomaly records",
        unquantified == 221,
        f"{unquantified} unquantified records; expected 221",
    )
    record_check(
        "Known money-at-risk total",
        total_money is not None and abs(total_money - 31421239.07) < 0.02,
        f"₹{total_money:,.2f}",
    )

    bad_ranges = con.execute("""
        SELECT COUNT(*)
        FROM stg_forecast
        WHERE lower_80 > forecast_value
           OR forecast_value > upper_80
    """).fetchone()[0]

    record_check(
        "Forecast interval ordering",
        bad_ranges == 0,
        f"{bad_ranges} invalid forecast intervals",
    )

    date_check = con.execute("""
        SELECT
            MIN(month_start_date),
            MAX(month_start_date),
            MIN(forecast_month),
            MAX(forecast_month)
        FROM stg_headcount
        CROSS JOIN stg_forecast
    """).fetchone()

    actual_range = con.execute("""
        SELECT MIN(month_start_date), MAX(month_start_date)
        FROM stg_headcount
    """).fetchone()

    forecast_range = con.execute("""
        SELECT MIN(forecast_month), MAX(forecast_month)
        FROM stg_forecast
    """).fetchone()

    record_check(
        "Historical actual date range",
        str(actual_range[0]) == "2020-01-01"
        and str(actual_range[1]) == "2026-09-01",
        f"{actual_range[0]} to {actual_range[1]}",
    )
    record_check(
        "Forecast date range",
        str(forecast_range[0]) == "2026-10-01"
        and str(forecast_range[1]) == "2027-03-01",
        f"{forecast_range[0]} to {forecast_range[1]}",
    )

    error_count = con.execute("""
        SELECT COUNT(*) FROM mart_forecast_error
    """).fetchone()[0]

    record_check(
        "Forecast error overlap status",
        error_count == 0,
        f"{error_count} overlapping forecast/actual rows; "
        "zero is expected because forecast periods are future months",
    )

    risk_total = con.execute("""
        SELECT SUM(employee_count)
        FROM mart_attrition_risk_bands
    """).fetchone()[0]

    record_check(
        "Aggregated attrition risk count",
        risk_total == 430,
        f"{risk_total} employees represented in aggregate bands",
    )

finally:
    con.close()

report = pd.DataFrame(checks)
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

report_path = EVIDENCE_DIR / "verification_results.csv"
report.to_csv(report_path, index=False)

print("\n========== TASK 14 VERIFICATION SUMMARY ==========")
print(report.to_string(index=False))

failed = int((report["status"] == "FAIL").sum())
passed = int((report["status"] == "PASS").sum())

print(f"\nPassed: {passed}")
print(f"Failed: {failed}")
print("Evidence:", report_path)

if failed:
    raise SystemExit("Verification failed. Review the checks above.")

print("\nALL TASK 14 CHECKS PASSED.")
