cd "/Users/admin/Desktop/PulseIQ"

cat > "Phase 4/Task 18/README.md" <<'EOF'
# PulseIQ — Phase 4, Task 18
## Self-service KPI Explorer with Privacy

### Objective
Provide a self-service explorer for approved company, department, and team metrics while protecting employee privacy through role-specific metric access, minimum group sizes, and complementary suppression.

### Application
Task 18 is integrated into the Phase 4 Task 17 Streamlit application. Select **Self-service KPI Explorer** in the sidebar.

### Demo roles and access
The explorer uses synthetic demo personas from `data/demo_users.csv`:

- **ADMIN:** Approved workforce and productivity metrics; Company, Department, and Team dimensions.
- **HR:** Approved HR workforce metrics and productivity metrics; Company, Department, and Team dimensions.
- **MANAGER:** Productivity metrics only, restricted to assigned demo team T01.
- **EXECUTIVE:** Approved workforce/payroll metrics; Company and Department dimensions, without Team drill-down.

The role selector is a demonstration only. It does not authenticate users and is not production-grade role-based access control.

### Privacy controls
- Minimum group size: **10** for employee-derived department metrics.
- Minimum team productivity group size: **10 distinct task assignees**.
- Small department groups are suppressed.
- Complementary suppression hides an additional department when necessary to prevent deriving a suppressed value from a company total and the remaining visible departments.
- Employee-level records and personal identifiers are not included in exported aggregate datasets.
- Missing payroll or attendance counts represent unavailable data, not zero.

For September 2026, D00 is suppressed because its group size is below the threshold. D10 is additionally suppressed through complementary suppression. The remaining eligible department aggregates are displayed.

### Data outputs
The exporter reads approved source CSVs from Phase 3 Task 13 and creates:

- `data/company_month.csv`
- `data/department_month.csv`
- `data/team_sprint.csv`
- `data/metric_dictionary.json`
- `data/metadata.json`

`data/demo_users.csv` contains synthetic demo personas only.

### Rebuild and verify
Run these commands from the repository root:

```bash
python "Phase 4/Task 18/scripts/export_task18_data.py"
python "Phase 4/Task 18/scripts/verify_task18.py"