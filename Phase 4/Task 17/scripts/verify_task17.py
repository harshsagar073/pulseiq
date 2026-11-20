import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CSV_FILE = ROOT / "data" / "company_kpis.csv"
META_FILE = ROOT / "data" / "metadata.json"

REQUIRED_COLUMNS = [
    "month",
    "headcount",
    "monthly_attrition_pct",
    "payroll_cost_inr",
    "attendance_rate_pct",
    "revenue_inr",
    "net_profit_inr",
    "operating_margin_pct",
    "attendance_target_pct",
    "attrition_target_pct",
    "task_completion_target_pct",
]

passed = 0
failed = 0


def check(label, condition):
    global passed, failed
    if condition:
        passed += 1
        print(f"PASS: {label}")
    else:
        failed += 1
        print(f"FAIL: {label}")


print("=" * 55)
print("PULSEIQ PHASE 4 TASK 17 VERIFICATION")
print("=" * 55)

check("Public KPI CSV exists", CSV_FILE.is_file())
check("Metadata JSON exists", META_FILE.is_file())

if not CSV_FILE.is_file() or not META_FILE.is_file():
    print("Required data file missing. Verification stopped.")
    sys.exit(1)

try:
    df = pd.read_csv(CSV_FILE)
    metadata = json.loads(META_FILE.read_text(encoding="utf-8"))
except Exception as exc:
    print(f"ERROR: Could not read data files: {exc}")
    sys.exit(1)

check("All 11 expected CSV columns exist",
      all(c in df.columns for c in REQUIRED_COLUMNS))
check("CSV contains reporting records", len(df) > 0)

if all(c in df.columns for c in REQUIRED_COLUMNS):
    dates = pd.to_datetime(df["month"], errors="coerce")

    check("All reporting months are valid", dates.notna().all())
    check("No duplicate monthly records", dates.nunique() == len(df))
    check("Monthly records are chronological", dates.is_monotonic_increasing)

    latest = dates.max().strftime("%Y-%m-%d") if dates.notna().any() else None
    check("Metadata cutoff matches latest CSV month",
          metadata.get("reporting_cutoff") == latest)

    numeric_columns = [c for c in REQUIRED_COLUMNS if c != "month"]
    numeric_ok = True
    for column in numeric_columns:
        original = df[column]
        nonblank = original.notna() & original.astype(str).str.strip().ne("")
        converted = pd.to_numeric(original, errors="coerce")
        if not ((~nonblank) | converted.notna()).all():
            numeric_ok = False
            break
    check("KPI and target columns contain numeric values", numeric_ok)

check("Metadata row count matches CSV",
      metadata.get("monthly_rows") == len(df))
check("Governed metric source is documented",
      metadata.get("data_source") == "PulseIQ governed metric views")
check("Point-in-time refresh limitation is documented",
      "point-in-time" in metadata.get("refresh_note", "").lower())
check("Company-level privacy statement is present",
      "company-level aggregates only" in metadata.get("privacy", "").lower())

sprint_pct = metadata.get("task_completion_pct")
check("Sprint completion percentage is between 0 and 100",
      isinstance(sprint_pct, (int, float)) and 0 <= sprint_pct <= 100)
check("Sprint identifier is present",
      bool(metadata.get("task_completion_sprint")))

sensitive_terms = (
    "employee_id", "employee_name", "email", "phone",
    "department_id", "department_name", "team_id", "client_id"
)
sensitive_columns = [
    c for c in df.columns
    if any(term in c.lower() for term in sensitive_terms)
]
check("No employee or organizational identifier columns",
      len(sensitive_columns) == 0)

print("\n" + "=" * 55)
print(f"RESULT: {passed}/{passed + failed} checks passed")
print(f"FAILED: {failed}")
print(f"CSV rows: {len(df)}")
print(f"CSV size: {CSV_FILE.stat().st_size:,} bytes")
print(f"Reporting cutoff: {metadata.get('reporting_cutoff')}")
print("=" * 55)

sys.exit(0 if failed == 0 else 1)
