from pathlib import Path
import json, re, sys
import pandas as pd

base = Path(__file__).resolve().parents[1]
data = base / "data"
errors = []

def check(ok, label):
    print(("PASS: " if ok else "FAIL: ") + label)
    if not ok:
        errors.append(label)

files = ["company_month.csv", "department_month.csv", "team_sprint.csv",
         "demo_users.csv", "metric_dictionary.json", "metadata.json"]
for f in files:
    check((data / f).is_file(), f + " exists")
if errors:
    sys.exit(1)

meta = json.loads((data / "metadata.json").read_text())
company = pd.read_csv(data / "company_month.csv")
dept = pd.read_csv(data / "department_month.csv")
teams = pd.read_csv(data / "team_sprint.csv")
check(meta.get("minimum_group_size") == 10, "minimum group size is 10")
check(meta.get("complementary_suppression") is True, "complementary suppression enabled")
check(meta.get("employee_level_data_exported") is False, "no employee-level export")
check(meta.get("employee_identifiers_exported") is False, "no employee identifiers exported")
for col in ["headcount_start", "headcount_end", "payroll_employees", "attendance_employees"]:
    check(col in dept.columns and (dept[col].dropna() >= 10).all(),
          "department " + col + " is at least 10")
check("distinct_assignees" in teams.columns and len(teams) > 0 and
      (teams["distinct_assignees"] >= 10).all(), "team groups have at least 10 distinct assignees")
for label, frame in [("company", company), ("department", dept), ("team", teams)]:
    forbidden = [c for c in frame.columns if re.search(
        r"employee_id|full_name|assignee_employee_id|email|phone|address|person_name", c, re.I)]
    check(not forbidden, label + " export has no personal identifier columns")
check(len(company) > 0 and len(dept) > 0 and len(teams) > 0, "all aggregate exports contain rows")
latest = dept["month"].astype(str).max()
latest_ids = set(dept.loc[dept["month"].astype(str) == latest, "department_id"])
check(not ({"D00", "D10"} & latest_ids), "latest month omits D00 and complementary-suppressed D10")

exporter = (base / "scripts" / "export_task18_data.py").read_text()
explorer = (base / "explorer_page.py").read_text()
app = (base.parent / "Task 17" / "app.py").read_text()
check("primary_suppressed" in exporter and "secondary_suppressed" in exporter,
      "exporter contains primary and complementary suppression")
manager = explorer.split('elif role == "MANAGER":', 1)[1].split("\nelse:", 1)[0]
check('allowed = list(productivity' in manager and 'dimensions = ["Team"]' in manager,
      "manager is restricted to productivity and Team")
check('view = view.loc[view["team_id"] == assigned_team]' in explorer,
      "manager is scoped to assigned team")
check("Monthly attrition rate" not in manager, "manager cannot select attrition")
check("DEMO ROLE SIMULATION ONLY" in explorer, "demo role limitation is disclosed")
check("Self-service KPI Explorer" in app and 'Phase 4 Task 18 | Self-service KPI Explorer' in app,
      "Task 18 page and footer are integrated")
print("\nTASK 18 VERIFICATION:", "FAILED" if errors else "ALL CHECKS PASSED")
print("Failed checks:", len(errors))
sys.exit(1 if errors else 0)
