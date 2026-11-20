from pathlib import Path
import json
from datetime import date, datetime

import duckdb

ROOT = Path(__file__).resolve().parents[3]
TASK_DIR = ROOT / "Phase 4" / "Task 17"
DB_PATH = ROOT / "Phase 1" / "Task 4" / "pulseiq_task4.duckdb"
DATA_DIR = TASK_DIR / "data"

DATA_DIR.mkdir(parents=True, exist_ok=True)

if not DB_PATH.exists():
    raise FileNotFoundError(f"Source database not found: {DB_PATH}")

con = duckdb.connect(str(DB_PATH), read_only=True)

# Monthly company-level metrics.
# Suppressed records are excluded from all published calculations.
monthly_sql = """
WITH headcount AS (
    SELECT
        month_start_date AS month,
        SUM(metric_value)::DOUBLE AS headcount
    FROM governed.m01_headcount
    WHERE NOT suppressed AND metric_value IS NOT NULL
    GROUP BY 1
),
attrition AS (
    SELECT
        month_start_date AS month,
        SUM(metric_value * group_size)
            / NULLIF(SUM(group_size), 0) AS monthly_attrition_pct
    FROM governed.m04_monthly_attrition
    WHERE NOT suppressed
      AND metric_value IS NOT NULL
      AND group_size > 0
    GROUP BY 1
),
payroll AS (
    SELECT
        DATE_TRUNC('month', period_end_date)::DATE AS month,
        SUM(metric_value) AS payroll_cost_inr
    FROM governed.m09_payroll_cost
    WHERE NOT suppressed AND metric_value IS NOT NULL
    GROUP BY 1
),
attendance AS (
    SELECT
        DATE_TRUNC('month', period_end_date)::DATE AS month,
        SUM(metric_value * group_size)
            / NULLIF(SUM(group_size), 0) * 100
            AS attendance_rate_pct
    FROM governed.m13_attendance_rate
    WHERE NOT suppressed
      AND metric_value IS NOT NULL
      AND group_size > 0
    GROUP BY 1
),
revenue AS (
    SELECT
        STRPTIME(posting_period || '-01', '%Y-%m-%d')::DATE AS month,
        SUM(metric_value) AS revenue_inr
    FROM governed.m16_revenue
    WHERE NOT suppressed AND metric_value IS NOT NULL
    GROUP BY 1
),
profit AS (
    SELECT
        STRPTIME(posting_period || '-01', '%Y-%m-%d')::DATE AS month,
        SUM(metric_value) AS net_profit_inr
    FROM governed.m17_net_profit
    WHERE NOT suppressed AND metric_value IS NOT NULL
    GROUP BY 1
),
margin AS (
    SELECT
        STRPTIME(posting_period || '-01', '%Y-%m-%d')::DATE AS month,
        AVG(metric_value) AS operating_margin_pct
    FROM governed.m18_operating_margin
    WHERE NOT suppressed AND metric_value IS NOT NULL
    GROUP BY 1
),
targets AS (
    SELECT
        month,
        AVG(attendance_rate_target) * 100 AS attendance_target_pct,
        AVG(attrition_monthly_target_pct) AS attrition_target_pct,
        AVG(task_completion_target_pct) AS task_completion_target_pct
    FROM raw.kpi_targets
    GROUP BY 1
),
combined AS (
    SELECT month FROM headcount
    UNION SELECT month FROM attrition
    UNION SELECT month FROM payroll
    UNION SELECT month FROM attendance
    UNION SELECT month FROM revenue
    UNION SELECT month FROM profit
    UNION SELECT month FROM margin
    UNION SELECT month FROM targets
)
SELECT
    c.month,
    h.headcount,
    a.monthly_attrition_pct,
    p.payroll_cost_inr,
    att.attendance_rate_pct,
    r.revenue_inr,
    pr.net_profit_inr,
    m.operating_margin_pct,
    t.attendance_target_pct,
    t.attrition_target_pct,
    t.task_completion_target_pct
FROM combined c
LEFT JOIN headcount h USING (month)
LEFT JOIN attrition a USING (month)
LEFT JOIN payroll p USING (month)
LEFT JOIN attendance att USING (month)
LEFT JOIN revenue r USING (month)
LEFT JOIN profit pr USING (month)
LEFT JOIN margin m USING (month)
LEFT JOIN targets t USING (month)
ORDER BY c.month
"""

df = con.execute(monthly_sql).fetchdf()

if df.empty:
    raise RuntimeError("No monthly KPI data was returned.")

# Find the latest reporting cutoff from the governed target calendar.
cutoff = con.execute(
    "SELECT MAX(month) FROM raw.kpi_targets"
).fetchone()[0]

# Select the latest sprint using its numeric suffix.
sprint_sql = """
WITH latest_sprint AS (
    SELECT sprint_id
    FROM governed.m22_task_completion_rate
    WHERE sprint_id IS NOT NULL
    ORDER BY TRY_CAST(REGEXP_EXTRACT(sprint_id, '[0-9]+$') AS INTEGER) DESC
    LIMIT 1
)
SELECT
    m.sprint_id,
    SUM(m.metric_value * m.group_size)
        / NULLIF(SUM(m.group_size), 0) AS task_completion_pct
FROM governed.m22_task_completion_rate m
JOIN latest_sprint s USING (sprint_id)
WHERE NOT m.suppressed
  AND m.metric_value IS NOT NULL
  AND m.group_size > 0
GROUP BY m.sprint_id
"""

sprint_result = con.execute(sprint_sql).fetchone()

if not sprint_result:
    sprint_id = None
    task_completion_pct = None
else:
    sprint_id, task_completion_pct = sprint_result

# Export only company-level KPI values.
# No employee, department, team, client or source-record identifiers.
csv_path = DATA_DIR / "company_kpis.csv"
df.to_csv(csv_path, index=False, date_format="%Y-%m-%d")

metadata = {
    "reporting_cutoff": cutoff.isoformat() if cutoff else None,
    "exported_at_utc": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
    "monthly_rows": int(len(df)),
    "task_completion_sprint": sprint_id,
    "task_completion_pct": (
        float(task_completion_pct)
        if task_completion_pct is not None else None
    ),
    "data_source": "PulseIQ governed metric views",
    "privacy": "Company-level aggregates only; suppressed rows excluded.",
    "refresh_note": (
        "This is a point-in-time export. New reporting values require "
        "an updated approved source database."
    )
}

metadata_path = DATA_DIR / "metadata.json"
metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

con.close()

print("========== PUBLIC DATA EXPORT ==========")
print(f"CSV: {csv_path}")
print(f"Metadata: {metadata_path}")
print(f"Monthly rows: {len(df)}")
print(f"Reporting cutoff: {metadata['reporting_cutoff']}")
print(f"Latest task-completion sprint: {sprint_id}")
print(f"Task completion: {task_completion_pct}")
print(f"CSV size: {csv_path.stat().st_size:,} bytes")
print("Employee-level data: NOT EXPORTED")
print("Department/team identifiers: NOT EXPORTED")
print("Suppressed records: EXCLUDED")
print("RESULT: EXPORT COMPLETE")
