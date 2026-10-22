from pathlib import Path
import re
import shutil
import pandas as pd
import duckdb

# ------------------------------------------------------------
# PulseIQ ETL Pipeline
# Raw source tables are never modified by this script.
# ------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "pulseiq.duckdb"
QUARANTINE_DIR = BASE_DIR / "quarantine"
VALIDATED_DIR = BASE_DIR / "validated"

# Only these four feeds have formal row-level contracts in the
# supplied data_contracts worksheet.
FORMAL_TABLES = {
    "fact_anomaly",
    "fact_attrition_risk",
    "fact_forecast",
    "fact_task",
}


def is_blank(value):
    """True for missing values and strings containing only spaces."""
    if pd.isna(value):
        return True
    return isinstance(value, str) and not value.strip()


def parse_date(value):
    """Return a Timestamp, or None when missing/unparseable."""
    if is_blank(value):
        return None
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.normalize()


def parse_number(value):
    if is_blank(value):
        return None
    try:
        number = float(value)
        if pd.isna(number):
            return None
        return number
    except (TypeError, ValueError):
        return None


def clean_text(value):
    return "" if is_blank(value) else str(value).strip()


def load_lookup(con, table, column):
    """Read lookup IDs from a raw dimension table."""
    try:
        result = con.execute(
            f'SELECT "{column}" FROM raw."{table}"'
        ).fetchdf()
        return {
            clean_text(value)
            for value in result[column].tolist()
            if not is_blank(value)
        }
    except Exception:
        return set()


def add_error(errors, message):
    if message not in errors:
        errors.append(message)


def validate_anomaly(row, lookups):
    errors = []

    required = [
        "result_id", "source_dataset", "record_id", "employee_id",
        "period", "anomaly_score", "flagged", "reason_code",
        "reason_text", "model_version", "scored_at",
    ]
    for col in required:
        if col not in row.index or is_blank(row.get(col)):
            add_error(errors, f"{col}: required value is blank")

    result_id = clean_text(row.get("result_id"))
    if result_id and not re.fullmatch(r"AN-\d{4}", result_id):
        add_error(errors, "result_id: expected format AN-nnnn")

    source = clean_text(row.get("source_dataset"))
    allowed_sources = {
        "attendance_monthly_features",
        "payroll_monthly_features",
    }
    if source and source not in allowed_sources:
        add_error(errors, "source_dataset: value is not allowed")

    employee_id = clean_text(row.get("employee_id"))
    if employee_id and employee_id not in lookups["employee_ids"]:
        add_error(errors, "employee_id: not found in dim_employee")

    period = parse_date(row.get("period"))
    if not is_blank(row.get("period")) and period is None:
        add_error(errors, "period: invalid date")
    elif period is not None:
        if period.day not in (1, period.days_in_month):
            add_error(errors, "period: must be first or last day of month")

    score = parse_number(row.get("anomaly_score"))
    if score is None:
        add_error(errors, "anomaly_score: must be numeric")
    elif not 0 <= score <= 1:
        add_error(errors, "anomaly_score: must be between 0 and 1")

    flagged = clean_text(row.get("flagged"))
    if flagged and flagged not in {"Y", "N"}:
        add_error(errors, "flagged: expected Y or N")

    if not is_blank(row.get("money_at_risk")):
        money = parse_number(row.get("money_at_risk"))
        if money is None:
            add_error(errors, "money_at_risk: must be numeric or blank")

    if not is_blank(row.get("scored_at")):
        timestamp = pd.to_datetime(row.get("scored_at"), errors="coerce", utc=True)
        if pd.isna(timestamp):
            add_error(errors, "scored_at: invalid timestamp")

    return errors


def validate_attrition(row, lookups):
    errors = []

    required = [
        "prediction_id", "employee_id", "department_id", "as_of_date",
        "risk_score_12m", "risk_band", "model_version",
    ]
    for col in required:
        if col not in row.index or is_blank(row.get(col)):
            add_error(errors, f"{col}: required value is blank")

    prediction_id = clean_text(row.get("prediction_id"))
    if prediction_id and not re.fullmatch(r"AR-\d{4}", prediction_id):
        add_error(errors, "prediction_id: expected format AR-nnnn")

    employee_id = clean_text(row.get("employee_id"))
    if employee_id and employee_id not in lookups["employee_ids"]:
        add_error(errors, "employee_id: not found in dim_employee")

    department_id = clean_text(row.get("department_id"))
    if department_id and department_id not in lookups["department_ids"]:
        add_error(errors, "department_id: not found in dim_department")

    score = parse_number(row.get("risk_score_12m"))
    if score is None:
        add_error(errors, "risk_score_12m: must be numeric")
    elif not 0 <= score <= 1:
        add_error(errors, "risk_score_12m: must be between 0 and 1")

    band = clean_text(row.get("risk_band"))
    if band and band not in {"Low", "Medium", "High"}:
        add_error(errors, "risk_band: expected Low, Medium, or High")

    date = parse_date(row.get("as_of_date"))
    if not is_blank(row.get("as_of_date")) and date is None:
        add_error(errors, "as_of_date: invalid date")

    return errors


def validate_forecast(row, lookups):
    errors = []

    required = [
        "forecast_id", "metric", "department_id", "forecast_month",
        "forecast_value", "lower_80", "upper_80", "method",
        "trained_through",
    ]
    for col in required:
        if col not in row.index or is_blank(row.get(col)):
            add_error(errors, f"{col}: required value is blank")

    forecast_id = clean_text(row.get("forecast_id"))
    if forecast_id and not re.fullmatch(r"FC-\d{4}", forecast_id):
        add_error(errors, "forecast_id: expected format FC-nnnn")

    metric = clean_text(row.get("metric"))
    if metric and metric not in {
        "headcount_end", "attrition_rate_monthly_pct"
    }:
        add_error(errors, "metric: value is not allowed")

    department_id = clean_text(row.get("department_id"))
    if (
        department_id
        and department_id != "ALL"
        and department_id not in lookups["department_ids"]
    ):
        add_error(errors, "department_id: not found in dim_department or ALL")

    forecast_month = parse_date(row.get("forecast_month"))
    if not is_blank(row.get("forecast_month")) and forecast_month is None:
        add_error(errors, "forecast_month: invalid date")
    elif forecast_month is not None and forecast_month.day != 1:
        add_error(errors, "forecast_month: must be the first day of the month")

    value = parse_number(row.get("forecast_value"))
    lower = parse_number(row.get("lower_80"))
    upper = parse_number(row.get("upper_80"))

    if value is None:
        add_error(errors, "forecast_value: must be numeric")
    elif value < 0:
        add_error(errors, "forecast_value: must be >= 0")

    if lower is None:
        add_error(errors, "lower_80: must be numeric")
    if upper is None:
        add_error(errors, "upper_80: must be numeric")

    if value is not None and lower is not None and lower > value:
        add_error(errors, "lower_80: must be <= forecast_value")
    if value is not None and upper is not None and upper < value:
        add_error(errors, "upper_80: must be >= forecast_value")

    trained = clean_text(row.get("trained_through"))
    if trained and not re.fullmatch(r"\d{4}-\d{2}", trained):
        add_error(errors, "trained_through: expected YYYY-MM")

    return errors


def validate_task(row, lookups):
    errors = []

    required = [
        "task_id", "team_id", "sprint_id", "assignee_employee_id",
        "task_type", "priority", "story_points", "created_date",
        "due_date", "status", "reopened_count",
    ]
    for col in required:
        if col not in row.index or is_blank(row.get(col)):
            add_error(errors, f"{col}: required value is blank")

    task_id = clean_text(row.get("task_id"))
    if task_id and not re.fullmatch(r"TASK-\d{5}", task_id):
        add_error(errors, "task_id: expected format TASK-nnnnn")

    team_id = clean_text(row.get("team_id"))
    if team_id and team_id not in lookups["team_ids"]:
        add_error(errors, "team_id: not found in dim_team")

    sprint_id = clean_text(row.get("sprint_id"))
    if sprint_id and sprint_id not in lookups["sprint_ids"]:
        add_error(errors, "sprint_id: not found in dim_sprint")

    employee_id = clean_text(row.get("assignee_employee_id"))
    if employee_id and employee_id not in lookups["employee_ids"]:
        add_error(errors, "assignee_employee_id: not found in dim_employee")

    task_type = clean_text(row.get("task_type"))
    if task_type and task_type not in {"Feature", "Bug", "Chore", "Spike"}:
        add_error(errors, "task_type: value is not allowed")

    priority = clean_text(row.get("priority"))
    if priority and priority not in {"P1", "P2", "P3", "P4"}:
        add_error(errors, "priority: expected P1, P2, P3, or P4")

    points = parse_number(row.get("story_points"))
    if points is None or points not in {1, 2, 3, 5, 8, 13}:
        add_error(errors, "story_points: expected 1, 2, 3, 5, 8, or 13")

    status = clean_text(row.get("status"))
    allowed_statuses = {"Done", "In Progress", "Blocked", "To Do", "Cancelled"}
    if status and status not in allowed_statuses:
        add_error(errors, "status: value is not allowed")

    created = parse_date(row.get("created_date"))
    started = parse_date(row.get("started_date"))
    due = parse_date(row.get("due_date"))
    completed = parse_date(row.get("completed_date"))

    for col in ("created_date", "due_date"):
        if not is_blank(row.get(col)) and parse_date(row.get(col)) is None:
            add_error(errors, f"{col}: invalid date")
    for col in ("started_date", "completed_date"):
        if not is_blank(row.get(col)) and parse_date(row.get(col)) is None:
            add_error(errors, f"{col}: invalid date")

    if created is not None and started is not None and created > started:
        add_error(errors, "created_date: must be <= started_date")

    if status == "To Do" and started is not None:
        add_error(errors, "started_date: must be blank when status is To Do")
    if status != "To Do" and started is None:
        add_error(errors, "started_date: required unless status is To Do")

    if status == "Done" and completed is None:
        add_error(errors, "completed_date: required when status is Done")
    if completed is not None and started is not None and completed < started:
        add_error(errors, "completed_date: must be >= started_date")

    if sprint_id in lookups["sprint_end_by_id"] and due is not None:
        expected_due = lookups["sprint_end_by_id"][sprint_id]
        if expected_due is not None and due != expected_due:
            add_error(errors, "due_date: must equal sprint end date")

    reopened = parse_number(row.get("reopened_count"))
    if reopened is None or reopened < 0 or not reopened.is_integer():
        add_error(errors, "reopened_count: must be a non-negative integer")

    return errors


def validate_row(table, row, lookups):
    if table == "fact_anomaly":
        return validate_anomaly(row, lookups)
    if table == "fact_attrition_risk":
        return validate_attrition(row, lookups)
    if table == "fact_forecast":
        return validate_forecast(row, lookups)
    if table == "fact_task":
        return validate_task(row, lookups)
    return []


def main():
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}. Run 05_Starter/load_to_duckdb.py first."
        )

    QUARANTINE_DIR.mkdir(exist_ok=True)
    VALIDATED_DIR.mkdir(exist_ok=True)

    # Remove outputs from the previous run so reruns are reproducible.
    for folder in (QUARANTINE_DIR, VALIDATED_DIR):
        for file in folder.glob("*.csv"):
            file.unlink()

    con = duckdb.connect(str(DB_PATH))

    try:
        tables = [
            row[0]
            for row in con.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'raw'
                ORDER BY table_name
            """).fetchall()
        ]

        if not tables:
            raise RuntimeError("No tables found in DuckDB schema raw.")

        lookups = {
            "employee_ids": load_lookup(con, "dim_employee", "employee_id"),
            "department_ids": load_lookup(con, "dim_department", "department_id"),
            "team_ids": load_lookup(con, "dim_team", "team_id"),
            "sprint_ids": load_lookup(con, "dim_sprint", "sprint_id"),
        }

        sprint_rows = con.execute(
            'SELECT sprint_id, end_date FROM raw."dim_sprint"'
        ).fetchdf()
        lookups["sprint_end_by_id"] = {
            clean_text(row["sprint_id"]): parse_date(row["end_date"])
            for _, row in sprint_rows.iterrows()
        }

        summary = []

        print("\nPulseIQ ETL validation")
        print("=" * 86)
        print(f"{'Table':30} {'Rows in':>10} {'Passed':>10} {'Quarantined':>13}  Scope")
        print("-" * 86)

        for table in tables:
            df = con.execute(f'SELECT * FROM raw."{table}"').fetchdf()
            original_columns = list(df.columns)

            # Warn about contract columns not present and extra columns.
            if table in FORMAL_TABLES:
                if table == "fact_anomaly":
                    expected = {
                        "result_id", "source_dataset", "record_id", "employee_id",
                        "period", "anomaly_score", "flagged", "reason_code",
                        "reason_text", "money_at_risk", "model_version", "scored_at",
                    }
                elif table == "fact_attrition_risk":
                    expected = {
                        "prediction_id", "employee_id", "department_id", "as_of_date",
                        "risk_score_12m", "risk_band", "top_reason_1", "top_reason_2",
                        "top_reason_3", "model_version",
                    }
                elif table == "fact_forecast":
                    expected = {
                        "forecast_id", "metric", "department_id", "forecast_month",
                        "forecast_value", "lower_80", "upper_80", "method",
                        "trained_through",
                    }
                else:
                    expected = {
                        "task_id", "team_id", "sprint_id", "assignee_employee_id",
                        "task_type", "priority", "story_points", "created_date",
                        "started_date", "due_date", "completed_date", "status",
                        "reopened_count",
                    }

                missing_columns = sorted(expected - set(original_columns))
                extra_columns = sorted(set(original_columns) - expected)

                if missing_columns:
                    raise ValueError(
                        f"{table}: missing contract columns: {missing_columns}"
                    )
                if extra_columns:
                    print(
                        f"WARNING {table}: extra columns retained: "
                        f"{', '.join(extra_columns)}"
                    )

            passed_rows = []
            rejected_rows = []

            for _, row in df.iterrows():
                errors = validate_row(table, row, lookups)

                if errors:
                    rejected = row.to_dict()
                    rejected["_quarantine_reason"] = " | ".join(errors)
                    rejected["_source_table"] = table
                    rejected_rows.append(rejected)
                else:
                    passed_rows.append(row.to_dict())

            pd.DataFrame(passed_rows, columns=original_columns).to_csv(
                VALIDATED_DIR / f"{table}.csv", index=False
            )

            if rejected_rows:
                pd.DataFrame(rejected_rows).to_csv(
                    QUARANTINE_DIR / f"{table}.csv", index=False
                )

            rows_in = len(df)
            passed = len(passed_rows)
            quarantined = len(rejected_rows)

            # The four formally contracted tables get row-level checks.
            # Other tables are counted and exported unchanged; their workbook
            # contracts are not defined in the supplied formal contract sheet.
            scope = "formal contract" if table in FORMAL_TABLES else "structural only"

            summary.append({
                "table_name": table,
                "rows_in": rows_in,
                "passed": passed,
                "quarantined": quarantined,
                "validation_scope": scope,
            })

            print(
                f"{table:30} {rows_in:10,} {passed:10,} "
                f"{quarantined:13,}  {scope}"
            )

        summary_df = pd.DataFrame(summary)
        summary_df.to_csv(BASE_DIR / "etl_summary.csv", index=False)

        print("-" * 86)
        print(f"TOTAL{'':25} "
              f"{summary_df['rows_in'].sum():10,} "
              f"{summary_df['passed'].sum():10,} "
              f"{summary_df['quarantined'].sum():13,}")
        print("\nOutputs:")
        print(f"  Summary:   {BASE_DIR / 'etl_summary.csv'}")
        print(f"  Validated: {VALIDATED_DIR}")
        print(f"  Quarantine:{QUARANTINE_DIR}")
        print("\nRaw DuckDB tables were not modified.")

    finally:
        con.close()


if __name__ == "__main__":
    main()