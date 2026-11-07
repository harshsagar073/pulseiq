from pathlib import Path
import csv
import math
import duckdb

BASE = Path(__file__).resolve().parent.parent
DB = BASE / "pulseiq_task12.duckdb"
OUT = BASE / "verification"

EXPECTED_OPEN_COUNT = 62
EXPECTED_OPEN_BALANCE = 139394278.00
EXPECTED_CASH_IN = 1419349558.00
EXPECTED_CASH_OUT = 185831316.70


def save_csv(filename, headers, rows):
    with open(OUT / filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)


def close_enough(a, b):
    return math.isclose(float(a or 0), float(b), abs_tol=0.01)


def main():
    if not DB.exists():
        raise FileNotFoundError(f"Database missing: {DB}")

    con = duckdb.connect(str(DB), read_only=True)
    results = []
    exceptions = []

    def check(name, passed, actual, expected):
        results.append((name, "PASS" if passed else "FAIL", actual, expected))

    try:
        # Open invoices
        count, balance = con.execute("""
            SELECT COUNT(*), COALESCE(SUM(balance_due), 0)
            FROM v_open_invoices
        """).fetchone()

        check("Open invoice count", count == EXPECTED_OPEN_COUNT,
              count, EXPECTED_OPEN_COUNT)
        check("Open receivables balance",
              close_enough(balance, EXPECTED_OPEN_BALANCE),
              round(balance, 2), EXPECTED_OPEN_BALANCE)

        # Ageing reconciliation
        ageing = con.execute("""
            SELECT ageing_group, invoice_count, outstanding_amount
            FROM v_receivables_ageing
            ORDER BY ageing_group
        """).fetchall()

        save_csv(
            "ageing_reconciliation.csv",
            ["ageing_group", "invoice_count", "outstanding_amount"],
            ageing
        )

        ageing_count = sum(row[1] for row in ageing)
        ageing_balance = sum(float(row[2] or 0) for row in ageing)

        check("Ageing invoice count reconciliation",
              ageing_count == count, ageing_count, count)
        check("Ageing balance reconciliation",
              close_enough(ageing_balance, balance),
              round(ageing_balance, 2), round(balance, 2))

        # Payment reconciliation exceptions
        mismatch = con.execute("""
            SELECT invoice_id, invoice_number, client_id, status,
                   total_amount, invoice_amount_paid, balance_due,
                   transaction_payment_total, payment_count,
                   payment_difference, reconciliation_status
            FROM v_invoice_payment_reconciliation
            WHERE reconciliation_status = 'MISMATCH'
            ORDER BY invoice_id
        """).fetchall()

        headers = [
            "invoice_id", "invoice_number", "client_id", "status",
            "total_amount", "invoice_amount_paid", "balance_due",
            "transaction_payment_total", "payment_count",
            "payment_difference", "reconciliation_status"
        ]
        save_csv("payment_reconciliation.csv", headers, mismatch)

        check("Payment mismatch count", len(mismatch) == 1,
              len(mismatch), 1)

        known = any(
            row[0] == "INV-00385" and close_enough(row[9], 100)
            for row in mismatch
        )
        check("Known INV-00385 ₹100 exception", known,
              "Found" if known else "Not found", "Found")

        if known:
            exceptions.append(
                "INV-00385: invoice paid amount is ₹1,049,828, "
                "but payment transactions total ₹1,049,728. "
                "Difference ₹100. Source data was not modified."
            )

        # Cash-in
        cash_in = con.execute("""
            SELECT COALESCE(SUM(cash_in), 0)
            FROM v_monthly_cash_in
        """).fetchone()[0]

        check("Total cash-in", close_enough(cash_in, EXPECTED_CASH_IN),
              round(cash_in, 2), EXPECTED_CASH_IN)

        # Cash-out
        cash_out = con.execute("""
            SELECT COALESCE(SUM(cash_out), 0)
            FROM v_monthly_cash_out
        """).fetchone()[0]

        check("Total cash-out", close_enough(cash_out, EXPECTED_CASH_OUT),
              round(cash_out, 2), EXPECTED_CASH_OUT)

        # Monthly cash flow export
        cash_flow = con.execute("""
            WITH cash_in AS (
                SELECT month, payment_count, cash_in
                FROM v_monthly_cash_in
            ),
            cash_out AS (
                SELECT month, payment_count, cash_out
                FROM v_monthly_cash_out
            )
            SELECT
                COALESCE(i.month, o.month) AS month,
                COALESCE(i.payment_count, 0),
                COALESCE(i.cash_in, 0),
                COALESCE(o.payment_count, 0),
                COALESCE(o.cash_out, 0),
                COALESCE(i.cash_in, 0) - COALESCE(o.cash_out, 0)
            FROM cash_in i
            FULL OUTER JOIN cash_out o USING (month)
            ORDER BY month
        """).fetchall()

        save_csv(
            "monthly_cash_flow.csv",
            ["month", "payment_count_in", "cash_in",
             "payment_count_out", "cash_out", "net_cash_flow"],
            cash_flow
        )

        # Client performance export
        client_data = con.execute("""
            SELECT * FROM v_client_payment_performance
            ORDER BY open_receivables DESC NULLS LAST
        """)
        client_rows = client_data.fetchall()
        client_headers = [col[0] for col in client_data.description]

        save_csv("client_payment_performance.csv",
                 client_headers, client_rows)

    finally:
        con.close()

    passed = sum(row[1] == "PASS" for row in results)
    failed = sum(row[1] == "FAIL" for row in results)

    report = [
        "PULSEIQ PHASE 3 - TASK 12 VALIDATION REPORT",
        "=" * 55,
        f"Database: {DB.name}",
        f"Checks passed: {passed}",
        f"Checks failed: {failed}",
        ""
    ]

    for name, status, actual, expected in results:
        report.extend([
            f"[{status}] {name}",
            f"Actual: {actual}",
            f"Expected: {expected}",
            ""
        ])

    report.extend(["DOCUMENTED EXCEPTIONS", "-" * 55])
    report.extend(exceptions or ["No known exception detected."])
    report.extend([
        "",
        "Overall result: " + ("PASS" if failed == 0 else "REVIEW REQUIRED")
    ])

    (OUT / "validation_summary.txt").write_text(
        "\n".join(report), encoding="utf-8"
    )

    print("\n".join(report))
    print(f"\nReports saved in: {OUT}")

    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
