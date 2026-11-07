from pathlib import Path
import sys
import duckdb

TASK_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = TASK_DIR.parents[1]
DB_PATH = PROJECT_DIR / "Phase 1" / "Task 4" / "pulseiq_task4.duckdb"

print("=" * 60)
print("PULSEIQ TASK 15 - VERIFICATION")
print("=" * 60)

errors = []
warnings = []

# 1. Check required files
required_files = [
    TASK_DIR / "app.py",
    TASK_DIR / "README.md",
    TASK_DIR / "requirements.txt",
]

for file_path in required_files:
    if file_path.exists() and file_path.stat().st_size > 0:
        print(f"PASS: {file_path.relative_to(TASK_DIR)} exists")
    else:
        errors.append(f"Missing or empty file: {file_path}")

# 2. Check database
if not DB_PATH.exists():
    errors.append(f"Task 4 database not found: {DB_PATH}")
else:
    print(f"PASS: Task 4 database found")

    try:
        con = duckdb.connect(str(DB_PATH), read_only=True)

        required_views = [
            "m01_headcount",
            "m04_monthly_attrition",
            "m09_payroll_cost",
            "m13_attendance_rate",
            "m16_revenue",
            "m17_net_profit",
            "m18_operating_margin",
            "m22_task_completion_rate",
        ]

        for view in required_views:
            result = con.execute(
                """
                SELECT COUNT(*)
                FROM information_schema.views
                WHERE table_schema = 'governed'
                  AND table_name = ?
                """,
                [view],
            ).fetchone()[0]

            if result:
                print(f"PASS: governed.{view} exists")
            else:
                errors.append(f"Missing governed view: {view}")

        target_exists = con.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = 'raw'
              AND table_name = 'kpi_targets'
            """
        ).fetchone()[0]

        if target_exists:
            target_count = con.execute(
                "SELECT COUNT(*) FROM raw.kpi_targets"
            ).fetchone()[0]

            print(f"PASS: raw.kpi_targets exists ({target_count} rows)")

            if target_count != 180:
                warnings.append(
                    f"Expected 180 KPI target rows; found {target_count}"
                )
        else:
            errors.append("Missing raw.kpi_targets table")

        con.close()

    except Exception as exc:
        errors.append(f"Database verification error: {exc}")

# 3. Check evidence
evidence_dir = TASK_DIR / "evidence"
if evidence_dir.exists():
    screenshots = list(evidence_dir.glob("*.png"))
    print(f"PASS: Evidence folder contains {len(screenshots)} PNG screenshot(s)")

    for screenshot in screenshots:
        if screenshot.stat().st_size == 0:
            warnings.append(f"Empty screenshot: {screenshot.name}")
else:
    errors.append("Evidence folder is missing")

# 4. Results
print("\n" + "=" * 60)
print("VERIFICATION SUMMARY")
print("=" * 60)

for warning in warnings:
    print(f"WARNING: {warning}")

for error in errors:
    print(f"FAIL: {error}")

if errors:
    print(f"\nRESULT: FAILED ({len(errors)} issue(s))")
    sys.exit(1)

print("\nRESULT: PASSED")
if warnings:
    print(f"Warnings: {len(warnings)}")
else:
    print("Warnings: 0")
