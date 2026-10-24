from pathlib import Path
import shutil
import duckdb

TASK5_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = TASK5_DIR.parent
DB = TASK5_DIR / "pulseiq_task5.duckdb"
SOURCE_DB = REPO_DIR / "pulseiq.duckdb"

if not DB.exists():
    if not SOURCE_DB.exists():
        raise FileNotFoundError(
            f"Task 5 database not found at {DB}, and source database "
            f"not found at {SOURCE_DB}. Place the original pulseiq.duckdb "
            "in the repository root before running setup."
        )
    shutil.copy2(SOURCE_DB, DB)
    print(f"Copied source database to: {DB}")

con = duckdb.connect(str(DB))

def columns(table):
    return [
        row[1]
        for row in con.execute(f"PRAGMA table_info('{table}')").fetchall()
    ]

def choose(options, available):
    return next((name for name in options if name in available), None)

con.execute("CREATE SCHEMA IF NOT EXISTS governed")

# Department labels are detected from the available warehouse schema.
dept_cols = columns("raw.dim_department")
dept_id = choose(["department_id", "dept_id"], dept_cols)
dept_name = choose(
    ["department_name", "department", "name", "department_title"],
    dept_cols,
)

if not dept_id:
    raise RuntimeError("Could not find department ID in raw.dim_department")

if dept_name:
    dept_join = (
        f"LEFT JOIN raw.dim_department d ON "
        f"CAST(h.department_id AS VARCHAR) = CAST(d.{dept_id} AS VARCHAR)"
    )
    dept_label = f"COALESCE(CAST(d.{dept_name} AS VARCHAR), CAST(h.department_id AS VARCHAR))"
else:
    dept_join = ""
    dept_label = "CAST(h.department_id AS VARCHAR)"

# The dashboard's headcount trend comes from the governed metric layer.
con.execute(f"""
CREATE OR REPLACE VIEW governed.v_dashboard_headcount AS
SELECT
    CAST(h.month_start_date AS DATE) AS month_start_date,
    CAST(h.department_id AS VARCHAR) AS department_id,
    {dept_label} AS department_name,
    TRY_CAST(h.metric_value AS DOUBLE) AS headcount
FROM governed.m01_headcount h
{dept_join}
WHERE h.month_start_date IS NOT NULL
  AND h.metric_value IS NOT NULL
  AND (
      h.suppressed IS NULL
      OR LOWER(CAST(h.suppressed AS VARCHAR)) NOT IN ('true', '1', 'y')
  )
""")

# Supporting KPI metrics are sourced from governed views too.
for metric, view_name in [
    ("m02_hires", "v_dashboard_hires"),
    ("m03_exits", "v_dashboard_exits"),
]:
    con.execute(f"""
    CREATE OR REPLACE VIEW governed.{view_name} AS
    SELECT
        CAST(month_start_date AS DATE) AS month_start_date,
        CAST(department_id AS VARCHAR) AS department_id,
        TRY_CAST(metric_value AS DOUBLE) AS metric_value
    FROM governed.{metric}
    WHERE month_start_date IS NOT NULL
      AND metric_value IS NOT NULL
      AND (
          suppressed IS NULL
          OR LOWER(CAST(suppressed AS VARCHAR)) NOT IN ('true', '1', 'y')
      )
    """)

emp_cols = columns("raw.dim_employee")
emp_id = choose(["employee_id", "employee_key"], emp_cols)
emp_dept = choose(["department_id"], emp_cols)
emp_current = choose(["is_current"], emp_cols)
emp_status = choose(["employment_status"], emp_cols)
emp_location = choose(["work_location"], emp_cols)
emp_mode = choose(["work_mode"], emp_cols)

if not emp_id or not emp_dept or not emp_current:
    raise RuntimeError(
        "Employee table needs employee ID, department_id and is_current columns"
    )

current_filter = f"""
    COALESCE(LOWER(CAST(e.{emp_current} AS VARCHAR)), '') IN ('y', 'yes', 'true', '1')
"""
if emp_status:
    current_filter += f"""
    AND LOWER(COALESCE(CAST(e.{emp_status} AS VARCHAR), '')) IN
        ('active', 'employed', 'currently employed')
"""

con.execute(f"""
CREATE OR REPLACE VIEW governed.v_dashboard_current_employee AS
SELECT
    CAST(e.{emp_id} AS VARCHAR) AS employee_id,
    CAST(e.{emp_dept} AS VARCHAR) AS department_id,
    {("CAST(e." + emp_location + " AS VARCHAR)") if emp_location else "CAST('Unknown' AS VARCHAR)"} AS work_location,
    {("CAST(e." + emp_mode + " AS VARCHAR)") if emp_mode else "CAST('Unknown' AS VARCHAR)"} AS work_mode
FROM raw.dim_employee e
WHERE {current_filter}
""")

con.execute(f"""
CREATE OR REPLACE VIEW governed.v_dashboard_department_mix AS
SELECT
    e.department_id,
    {dept_label.replace("h.department_id", "e.department_id").replace("d.", "d.")} AS department_name,
    COUNT(DISTINCT e.employee_id) AS employee_count
FROM governed.v_dashboard_current_employee e
{("LEFT JOIN raw.dim_department d ON CAST(e.department_id AS VARCHAR) = CAST(d." + dept_id + " AS VARCHAR)") if dept_name else ""}
GROUP BY 1, 2
""")

# Location tier is enriched during setup; the app reads only this governed view.
loc_cols = columns("raw.dim_location")
loc_key = choose(["work_location", "location_name", "location", "location_id"], loc_cols)
tier_col = choose(["city_tier", "tier_number", "location_tier", "tier"], loc_cols)

if emp_location and loc_key and tier_col:
    con.execute(f"""
    CREATE OR REPLACE VIEW governed.v_dashboard_location_tier AS
    SELECT
        COALESCE(CAST(l.{tier_col} AS VARCHAR), 'Unknown') AS location_tier,
        COUNT(DISTINCT e.employee_id) AS employee_count
    FROM governed.v_dashboard_current_employee e
    LEFT JOIN raw.dim_location l
      ON LOWER(TRIM(e.work_location)) = LOWER(TRIM(CAST(l.{loc_key} AS VARCHAR)))
    GROUP BY 1
    """)
else:
    con.execute("""
    CREATE OR REPLACE VIEW governed.v_dashboard_location_tier AS
    SELECT 'Unknown' AS location_tier, COUNT(DISTINCT employee_id) AS employee_count
    FROM governed.v_dashboard_current_employee
    """)

con.execute("""
CREATE OR REPLACE VIEW governed.v_dashboard_work_mode AS
SELECT
    COALESCE(NULLIF(TRIM(work_mode), ''), 'Unknown') AS work_mode,
    COUNT(DISTINCT employee_id) AS employee_count
FROM governed.v_dashboard_current_employee
GROUP BY 1
""")

# Simple, auditable view inventory.
views = con.execute("""
    SELECT table_name
    FROM information_schema.views
    WHERE table_schema = 'governed'
      AND table_name LIKE 'v_dashboard_%'
    ORDER BY table_name
""").fetchall()

con.close()
print(f"Database: {DB}")
print("Dashboard views created:")
for (name,) in views:
    print(f"  governed.{name}")
print(f"Total dashboard views: {len(views)}")
