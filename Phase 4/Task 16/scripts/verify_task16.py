from pathlib import Path
import sys
import duckdb

TASK_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = TASK_DIR.parents[1]

DB_PATH = PROJECT_ROOT / "Phase 1" / "Task 4" / "pulseiq_task4.duckdb"
REQUIREMENTS = TASK_DIR / "requirements.txt"
BUILDER = TASK_DIR / "build_report.py"
REPORT_DIR = TASK_DIR / "reports"

checks = []

def check(description, condition):
    status = "PASS" if condition else "FAIL"
    checks.append(condition)
    print(f"[{status}] {description}")

print("=" * 55)
print("PULSEIQ TASK 16 — AUTOMATED VERIFICATION")
print("=" * 55)

check("Report builder exists", BUILDER.is_file())
check("Pinned requirements file exists", REQUIREMENTS.is_file())
check("Source DuckDB database exists", DB_PATH.is_file())

requirements_ok = False
if REQUIREMENTS.is_file():
    lines = [
        line.strip()
        for line in REQUIREMENTS.read_text().splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    requirements_ok = bool(lines) and all("==" in line for line in lines)

check("All dependencies have pinned versions", requirements_ok)

for month in ["2026-08", "2026-09"]:
    pdf = REPORT_DIR / f"PulseIQ_Monthly_Report_{month}.pdf"
    valid_pdf = (
        pdf.is_file()
        and pdf.stat().st_size > 5000
        and pdf.read_bytes()[:5] == b"%PDF-"
    )
    check(f"Valid PDF generated for {month}", valid_pdf)

department_check = False
if DB_PATH.is_file():
    try:
        connection = duckdb.connect(str(DB_PATH), read_only=True)
        result = connection.execute("""
            SELECT COUNT(DISTINCT department_id)
            FROM raw.dim_department
        """).fetchone()[0]
        connection.close()
        department_check = result > 0
        print(f"      Departments in source dimension: {result}")
    except Exception as error:
        print(f"      Database check error: {error}")

check("Department dimension is available for dynamic reporting",
      department_check)

print("=" * 55)
passed = sum(checks)
failed = len(checks) - passed
print(f"RESULT: {passed}/{len(checks)} checks passed")
print(f"FAILED: {failed}")
print("=" * 55)

sys.exit(0 if failed == 0 else 1)
