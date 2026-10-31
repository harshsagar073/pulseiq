import duckdb
import csv
from decimal import Decimal, ROUND_HALF_UP

DB = "/Users/admin/Desktop/PulseIQ/Phase 1/Task 4/pulseiq_task4.duckdb"
EXCLUDED = ("PI-X0001", "PI-X0002", "PI-X0003", "PI-X0004")

def money(value):
    return Decimal(str(value)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

with open("answer_key.csv", newline="") as f:
    reference = {row["month"]: row for row in csv.DictReader(f)}

con = duckdb.connect(DB, read_only=True)

actual_rows = con.execute("""
    SELECT
        strftime(period_end_date, '%Y-%m-01') AS month,
        COUNT(DISTINCT employee_id) AS employees_paid,
        ROUND(SUM(gross_pay), 2) AS gross_pay,
        ROUND(SUM(net_pay), 2) AS net_pay,
        ROUND(SUM(employer_cost), 2) AS employer_cost
    FROM raw.fact_payroll
    WHERE payroll_item_id NOT IN (?, ?, ?, ?)
    GROUP BY 1
    ORDER BY 1
""", EXCLUDED).fetchall()

con.close()

output = []

for month, employees, gross, net, employer in actual_rows:
    ref = reference[month]

    gross_diff = money(gross) - money(ref["payroll_gross_pay"])
    net_diff = money(net) - money(ref["payroll_net_pay"])
    employer_diff = money(employer) - money(ref["payroll_employer_cost"])
    ledger_diff = money(employer) - money(ref["ledger_salary_related_expense"])
    employee_diff = employees - int(ref["employees_paid"])

    status = (
        "PASS"
        if employee_diff == 0
        and gross_diff == 0
        and net_diff == 0
        and employer_diff == 0
        and ledger_diff == 0
        else "CHECK"
    )

    output.append({
        "month": month,
        "actual_employees_paid": employees,
        "expected_employees_paid": ref["employees_paid"],
        "employee_count_difference": employee_diff,
        "actual_gross_pay": money(gross),
        "expected_gross_pay": money(ref["payroll_gross_pay"]),
        "gross_difference": gross_diff,
        "actual_net_pay": money(net),
        "expected_net_pay": money(ref["payroll_net_pay"]),
        "net_difference": net_diff,
        "actual_employer_cost": money(employer),
        "expected_employer_cost": money(ref["payroll_employer_cost"]),
        "employer_cost_difference": employer_diff,
        "expected_ledger_salary_expense": money(ref["ledger_salary_related_expense"]),
        "employer_vs_ledger_difference": ledger_diff,
        "status": status
    })

fields = list(output[0].keys())

with open("evidence/monthly_reconciliation.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(output)

passed = sum(row["status"] == "PASS" for row in output)
failed = len(output) - passed

print("\n===== MONTHLY RECONCILIATION =====")
for row in output:
    print(
        row["month"],
        "| Employees:", row["employee_count_difference"],
        "| Gross:", row["gross_difference"],
        "| Net:", row["net_difference"],
        "| Employer:", row["employer_cost_difference"],
        "| Ledger:", row["employer_vs_ledger_difference"],
        "|", row["status"]
    )

print("\n===== RESULT =====")
print("Months checked:", len(output))
print("Passed:", passed)
print("Needs investigation:", failed)
print("Excluded payroll rows:", len(EXCLUDED))
print("Evidence: evidence/monthly_reconciliation.csv")

if failed:
    raise SystemExit("Some months did not reconcile. Do not submit yet.")

print("\nSUCCESS: All 18 months reconcile with the official PQ-09 answer key.")
