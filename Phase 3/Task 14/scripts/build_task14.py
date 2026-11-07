from pathlib import Path
import duckdb
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "pulseiq_task14.duckdb"
SQL_PATH = BASE_DIR / "sql" / "task14_views.sql"
EVIDENCE_DIR = BASE_DIR / "evidence"

EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

required_files = [
    BASE_DIR / "data/source/fact_anomaly.csv",
    BASE_DIR / "data/source/fact_forecast.csv",
    BASE_DIR / "data/source/fact_attrition_risk.csv",
    BASE_DIR / "data/source/fact_headcount_monthly.csv",
    BASE_DIR / "data/reference/dim_department.csv",
]

missing = [str(path) for path in required_files if not path.exists()]
if missing:
    raise FileNotFoundError(
        "Required Task 14 files are missing:\n" + "\n".join(missing)
    )

if not SQL_PATH.exists():
    raise FileNotFoundError(f"SQL file not found: {SQL_PATH}")

print("Connecting to Task 14 DuckDB database...")
con = duckdb.connect(str(DB_PATH))

try:
    print("Executing SQL transformations...")
    con.execute(SQL_PATH.read_text(encoding="utf-8"))

    exports = {
        "anomaly_exposure_by_type.csv": """
            SELECT *
            FROM mart_anomaly_exposure
            ORDER BY known_money_at_risk DESC NULLS LAST,
                     anomaly_count DESC
        """,
        "forecast_error_table.csv": """
            SELECT *
            FROM mart_forecast_error
            ORDER BY metric, department_id, month
        """,
        "attrition_risk_band_summary.csv": """
            SELECT *
            FROM mart_attrition_risk_bands
            ORDER BY CASE risk_band
                WHEN 'Low' THEN 1
                WHEN 'Medium' THEN 2
                WHEN 'High' THEN 3
                ELSE 4
            END
        """,
        "historical_headcount_all.csv": """
            SELECT *
            FROM mart_actual_headcount_all
            ORDER BY month_start_date
        """,
        "historical_attrition_all.csv": """
            SELECT *
            FROM mart_actual_attrition_all
            ORDER BY month_start_date
        """,
    }

    for filename, query in exports.items():
        output_path = EVIDENCE_DIR / filename
        result = con.execute(query).df()
        result.to_csv(output_path, index=False)
        print(f"Created {output_path.name}: {len(result)} rows")

    counts = con.execute("""
        SELECT
            (SELECT COUNT(*) FROM stg_anomaly) AS anomaly_rows,
            (SELECT COUNT(*) FROM stg_forecast) AS forecast_rows,
            (SELECT COUNT(*) FROM stg_attrition_risk) AS risk_rows,
            (SELECT COUNT(*) FROM stg_headcount) AS headcount_rows,
            (SELECT COUNT(*) FROM mart_forecast_error) AS error_rows
    """).df()

    print("\nTask 14 database summary:")
    print(counts.to_string(index=False))

finally:
    con.close()

print("\nTask 14 database build completed.")
print("Database:", DB_PATH)
