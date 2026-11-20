import os
from datetime import datetime
from pathlib import Path
import duckdb
from fastapi import FastAPI, HTTPException

ROOT = Path(__file__).resolve().parents[2]

DB_PATH = Path(
    os.getenv(
        "PULSEIQ_DB_PATH",
        str(ROOT / "Phase 1" / "Task 4" / "pulseiq_task4.duckdb")
    )
)

app = FastAPI(
    title="PulseIQ Metrics API",
    description="Read-only API for five governed PulseIQ business metrics.",
    version="1.0.0",
)


METRICS = {
    "headcount": {
        "id": "M01",
        "name": "Headcount",
        "view": "m01_headcount",
        "source_table": "raw.fact_headcount_monthly",
        "period_expression": "strftime(month_start_date, '%Y-%m')",
        "definition": "Month-end headcount by department. Values are suppressed for groups smaller than 5.",
        "formula": "Governed month-end headcount from fact_headcount_monthly",
        "unit": "employees",
        "grain": "month and department",
        "dashboard": "Phase 3 Task 15 Executive Company Health Scorecard",
        "order_by": "department_id",
    },
    "payroll-cost": {
        "id": "M09",
        "name": "Payroll Cost",
        "view": "m09_payroll_cost",
        "source_table": "raw.fact_payroll",
        "period_expression": "strftime(period_end_date, '%Y-%m')",
        "definition": "Total employer payroll cost by month and department. Groups smaller than 5 are suppressed.",
        "formula": "SUM(employer_cost), subject to governed suppression",
        "unit": "INR",
        "grain": "month and department",
        "dashboard": "Phase 3 Task 15 Executive Company Health Scorecard",
        "order_by": "department_id",
    },
    "attendance-rate": {
        "id": "M13",
        "name": "Attendance Rate",
        "view": "m13_attendance_rate",
        "source_table": "raw.fact_attendance_monthly",
        "period_expression": "strftime(period_end_date, '%Y-%m')",
        "definition": "Attendance ratio by month and department. Groups smaller than 5 are suppressed.",
        "formula": "(present_days + 0.5 * half_days_unpaid) / scheduled_days",
        "unit": "ratio",
        "grain": "month and department",
        "dashboard": "Phase 3 Task 15 Executive Company Health Scorecard",
        "order_by": "department_id",
    },
    "revenue": {
        "id": "M16",
        "name": "Revenue",
        "view": "m16_revenue",
        "source_table": "raw.fact_ledger",
        "period_expression": "posting_period",
        "definition": "Revenue by posting month and account code for revenue accounts 4001–4004.",
        "formula": "-SUM(signed_amount_debit_positive), grouped by posting_period and account_code",
        "unit": "INR",
        "grain": "posting month and account code",
        "dashboard": "Phase 3 Task 15 Executive Company Health Scorecard",
        "order_by": "account_code",
    },
    "operating-margin": {
        "id": "M18",
        "name": "Operating Margin",
        "view": "m18_operating_margin",
        "source_table": "raw.fact_ledger",
        "period_expression": "posting_period",
        "definition": "Company-level operating margin by posting month.",
        "formula": "100 * net_profit / revenue, rounded to 2 decimal places",
        "unit": "percent",
        "grain": "company and posting month",
        "dashboard": "Phase 3 Task 15 Executive Company Health Scorecard",
        "order_by": "period",
    },
}


def read_metric(metric_key: str, period: str | None = None):
    if not DB_PATH.exists():
        raise HTTPException(status_code=500, detail="Task 4 metrics database was not found.")

    metric = METRICS[metric_key]
    view = metric["view"]
    period_expr = metric["period_expression"]

    if metric_key in ("headcount", "payroll-cost", "attendance-rate"):
        columns = (
            f"{period_expr} AS period, department_id, metric_value, "
            "unit, group_size, suppressed"
        )
    elif metric_key == "revenue":
        columns = (
            f"{period_expr} AS period, account_code, metric_value, "
            "unit, group_size, suppressed"
        )
    else:
        columns = (
            f"{period_expr} AS period, metric_value, "
            "unit, group_size, suppressed"
        )

    sql = f"""
        SELECT {columns}
        FROM governed.{view}
        WHERE {period_expr} = COALESCE(
            ?,
            (SELECT MAX({period_expr}) FROM governed.{view})
        )
        ORDER BY {metric["order_by"]}
    """

    with duckdb.connect(str(DB_PATH), read_only=True) as connection:
        rows = connection.execute(sql, [period]).fetchall()
        names = [item[0] for item in connection.description]

    records = []
    for row in rows:
        record = dict(zip(names, row))
        record["period"] = str(record["period"])
        if record.get("suppressed"):
            record["metric_value"] = None
        records.append(record)

    latest_period = records[0]["period"] if records else None
    last_refresh = datetime.fromtimestamp(
        DB_PATH.stat().st_mtime
    ).astimezone().isoformat()

    return {
        "metric": {
            "id": metric["id"],
            "name": metric["name"],
            "definition": metric["definition"],
            "formula": metric["formula"],
            "unit": metric["unit"],
            "grain": metric["grain"],
        },
        "period_requested": period,
        "latest_data_period_returned": latest_period,
        "data": records,
        "lineage": {
            "source_raw_table": metric["source_table"],
            "transformation": "Phase 1/Task 4/06_Metric_Layer/metric_views.sql",
            "warehouse_layer": (
                "Task 4 DuckDB snapshot containing the raw source table; "
                "a separate Task 4 raw-to-warehouse load script is not recorded."
            ),
            "governed_metric_view": f"governed.{view}",
            "dashboard_consumer": metric["dashboard"],
        },
        "freshness": {
            "database_last_modified": last_refresh,
            "latest_data_period": latest_period,
            "statement": (
                "Database last-modified time is the available refresh indicator. "
                "It is not proof of the upstream source-feed ingestion time."
            ),
        },
    }


@app.get("/")
def home():
    return {
        "message": "PulseIQ Metrics API is running.",
        "documentation": "/docs",
        "metrics": "/api/v1/metrics",
    }


@app.get("/health")
def health():
    return {"status": "ok", "database_exists": DB_PATH.exists()}


@app.get("/api/v1/metrics")
def list_metrics():
    return {
        "count": len(METRICS),
        "metrics": [
            {
                "key": key,
                "id": value["id"],
                "name": value["name"],
                "endpoint": f"/api/v1/metrics/{key}",
            }
            for key, value in METRICS.items()
        ],
    }


@app.get("/api/v1/metrics/headcount")
def headcount(period: str | None = None):
    return read_metric("headcount", period)


@app.get("/api/v1/metrics/payroll-cost")
def payroll_cost(period: str | None = None):
    return read_metric("payroll-cost", period)


@app.get("/api/v1/metrics/attendance-rate")
def attendance_rate(period: str | None = None):
    return read_metric("attendance-rate", period)


@app.get("/api/v1/metrics/revenue")
def revenue(period: str | None = None):
    return read_metric("revenue", period)


@app.get("/api/v1/metrics/operating-margin")
def operating_margin(period: str | None = None):
    return read_metric("operating-margin", period)
