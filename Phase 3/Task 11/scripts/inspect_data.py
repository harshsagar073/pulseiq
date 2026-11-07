import csv
from pathlib import Path
from collections import defaultdict
from decimal import Decimal

ROOT = Path("Phase 1/Task 1/validated")

def load(name):
    with open(ROOT / f"{name}.csv", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

ledger = load("fact_ledger")
accounts = load("dim_account")
expenses = load("fact_expense")
vendors = load("dim_vendor")

account_map = {r["account_code"]: r for r in accounts}
vendor_map = {r["vendor_id"]: r["vendor_name"] for r in vendors}

def money(value):
    return Decimal(value or "0")

print("\n========== DATA COUNTS ==========")
for name, rows in [
    ("fact_ledger", ledger),
    ("dim_account", accounts),
    ("fact_expense", expenses),
    ("dim_vendor", vendors),
]:
    print(f"{name}: {len(rows):,} rows")

print("\n========== ACCOUNT CLASSIFICATION ==========")
for typ in ["INCOME", "EXPENSE"]:
    detail = [
        a for a in accounts
        if a["account_type"] == typ and a["is_group"] == "N"
    ]
    groups = [
        a for a in accounts
        if a["account_type"] == typ and a["is_group"] == "Y"
    ]
    print(f"\n{typ}: {len(detail)} detail accounts, {len(groups)} group accounts")
    for a in detail:
        print(a["account_code"], a["account_name"])

print("\n========== LEDGER ACCOUNT SUMMARY ==========")
summary = defaultdict(lambda: Decimal("0"))

for row in ledger:
    account = account_map.get(row["account_code"])
    if not account:
        continue
    if account["is_group"] == "Y":
        continue
    if account["account_type"] in ("INCOME", "EXPENSE"):
        summary[(account["account_type"], row["account_code"])] += money(
            row["signed_amount_debit_positive"]
        )

for (typ, code), amount in sorted(summary.items()):
    print(code, account_map[code]["account_name"], typ, amount)

print("\n========== MONTHLY P&L ==========")
monthly = defaultdict(lambda: {"revenue": Decimal("0"),
                               "expenses": Decimal("0")})

for row in ledger:
    account = account_map.get(row["account_code"])
    if not account or account["is_group"] == "Y":
        continue

    typ = account["account_type"]
    amount = money(row["signed_amount_debit_positive"])
    period = row["posting_period"]

    if typ == "INCOME":
        monthly[period]["revenue"] -= amount
    elif typ == "EXPENSE":
        monthly[period]["expenses"] += amount

for period in sorted(monthly):
    revenue = monthly[period]["revenue"]
    expense = monthly[period]["expenses"]
    profit = revenue - expense
    margin = profit / revenue * 100 if revenue else Decimal("0")
    print(
        period,
        "| Revenue:", round(revenue, 2),
        "| Expenses:", round(expense, 2),
        "| Profit:", round(profit, 2),
        "| Margin:", round(margin, 2), "%"
    )

print("\n========== EXPENSE CATEGORY ==========")
categories = defaultdict(lambda: Decimal("0"))

for row in expenses:
    categories[row["category_account"]] += money(row["amount_excl_gst"])

for code, amount in sorted(categories.items(),
                           key=lambda x: x[1], reverse=True):
    name = account_map.get(code, {}).get("account_name", "Unknown")
    print(code, name, round(amount, 2))

print("\n========== TOP 10 VENDORS ==========")
vendor_totals = defaultdict(lambda: Decimal("0"))

for row in expenses:
    vendor_totals[row["vendor_id"]] += money(row["amount_excl_gst"])

for vendor_id, amount in sorted(
    vendor_totals.items(), key=lambda x: x[1], reverse=True
)[:10]:
    print(vendor_id, vendor_map.get(vendor_id, "Unknown"),
          round(amount, 2))

print("\n========== EXPENSE RECONCILIATION ==========")
expense_csv_total = sum(
    (money(r["amount_excl_gst"]) for r in expenses), Decimal("0")
)
ledger_expense_total = sum(
    (v for (typ, _), v in summary.items() if typ == "EXPENSE"),
    Decimal("0")
)

print("Fact expense (excluding GST):", round(expense_csv_total, 2))
print("Ledger signed expense total:", round(ledger_expense_total, 2))
print("Note: These may differ because the tables can cover different accounting events.")

print("\n========== COMPLETED ==========")
