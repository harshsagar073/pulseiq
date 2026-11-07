from pathlib import Path
import duckdb
import pandas as pd

ROOT = Path("/Users/admin/Desktop/PulseIQ")
TASK_DIR = ROOT / "Phase 3" / "Task 12"
SOURCE_DIR = ROOT / "Phase 1" / "Task 1" / "validated"

DB_PATH = TASK_DIR / "pulseiq_task12.duckdb"
TASK11_DB = ROOT / "Phase 3" / "Task 11" / "pulseiq_task11.duckdb"

FILES = {
    "dim_client": SOURCE_DIR / "dim_client.csv",
    "fact_invoice": SOURCE_DIR / "fact_invoice.csv",
    "fact_invoice_payment": SOURCE_DIR / "fact_invoice_payment.csv",
}

OPEN_STATUSES = ["SENT", "OVERDUE", "PARTIALLY_PAID"]

def main():
    print("=" * 65)
    print("PULSEIQ - TASK 12 DATABASE BUILDER")
    print("=" * 65)

    for name, path in FILES.items():
        if not path.exists():
            raise FileNotFoundError(f"Missing source file: {path}")
        print(f"Found {name}: {path}")

    if not TASK11_DB.exists():
        raise FileNotFoundError(f"Missing Task 11 DB: {TASK11_DB}")

    # Build only the Task 12 database.
    if DB_PATH.exists():
        DB_PATH.unlink()
        print("\nRebuilding Task 12 database only.")

    con = duckdb.connect(str(DB_PATH))

    try:
        # Load the three validated source CSVs.
        for table, path in FILES.items():
            path_sql = str(path).replace("'", "''")
            con.execute(f"""
                CREATE TABLE {table} AS
                SELECT * FROM read_csv_auto(
                    '{path_sql}',
                    header = true,
                    sample_size = -1
                )
            """)
            count = con.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()[0]
            print(f"Loaded {table}: {count:,} rows")

        # Read Task 11 expense data without changing Task 11.
        task11_sql = str(TASK11_DB).replace("'", "''")
        con.execute(f"""
            ATTACH '{task11_sql}' AS task11 (READ_ONLY)
        """)

        con.execute("""
            CREATE TABLE fact_expense AS
            SELECT *
            FROM task11.fact_expense
        """)

        expense_count = con.execute(
            "SELECT COUNT(*) FROM fact_expense"
        ).fetchone()[0]
        print(f"Loaded fact_expense: {expense_count:,} rows")

        con.execute("DETACH task11")

        # Open invoice view: use only the three specified statuses.
        con.execute("""
            CREATE VIEW v_open_invoices AS
            SELECT
                i.*,
                c.client_name,
                c.industry,
                c.city,
                c.payment_terms_days,
                c.payment_behaviour
            FROM fact_invoice i
            LEFT JOIN dim_client c USING (client_id)
            WHERE UPPER(TRIM(i.status)) IN (
                'SENT', 'OVERDUE', 'PARTIALLY_PAID'
            )
        """)

        # Preserve current invoices separately from overdue ageing.
        con.execute("""
            CREATE VIEW v_receivables_ageing AS
            SELECT
                CASE
                    WHEN ageing_bucket_at_cutoff = 'Not yet due'
                        THEN 'Current / Not yet due'
                    WHEN ageing_bucket_at_cutoff IN ('0-30 days', '1-30 days')
                        THEN '0-30 days'
                    WHEN ageing_bucket_at_cutoff IN ('31-60 days', '31–60 days')
                        THEN '31-60 days'
                    WHEN ageing_bucket_at_cutoff IN ('61-90 days', '61–90 days')
                        THEN '61-90 days'
                    WHEN ageing_bucket_at_cutoff IN ('90+ days', '90+')
                        THEN '90+ days'
                    ELSE 'Other / Review'
                END AS ageing_group,
                COUNT(*) AS invoice_count,
                SUM(balance_due) AS outstanding_amount
            FROM v_open_invoices
            GROUP BY 1
        """)

        # Invoice payment totals for reconciliation.
        con.execute("""
            CREATE VIEW v_invoice_payment_reconciliation AS
            WITH payment_totals AS (
                SELECT
                    invoice_id,
                    SUM(amount) AS transaction_payment_total,
                    COUNT(*) AS payment_count
                FROM fact_invoice_payment
                GROUP BY invoice_id
            )
            SELECT
                i.invoice_id,
                i.invoice_number,
                i.client_id,
                i.status,
                i.total_amount,
                i.amount_paid AS invoice_amount_paid,
                i.balance_due,
                COALESCE(p.transaction_payment_total, 0)
                    AS transaction_payment_total,
                COALESCE(p.payment_count, 0) AS payment_count,
                i.amount_paid - COALESCE(p.transaction_payment_total, 0)
                    AS payment_difference,
                CASE
                    WHEN ABS(
                        i.amount_paid - COALESCE(p.transaction_payment_total, 0)
                    ) > 0.01
                    THEN 'MISMATCH'
                    ELSE 'MATCH'
                END AS reconciliation_status
            FROM fact_invoice i
            LEFT JOIN payment_totals p USING (invoice_id)
        """)

        # Monthly cash-in from actual payment transactions.
        con.execute("""
            CREATE VIEW v_monthly_cash_in AS
            SELECT
                DATE_TRUNC('month', CAST(payment_date AS DATE))::DATE
                    AS month,
                COUNT(*) AS payment_count,
                SUM(amount) AS cash_in
            FROM fact_invoice_payment
            GROUP BY 1
        """)

        # Monthly cash-out from paid expense records only.
        con.execute("""
            CREATE VIEW v_monthly_cash_out AS
            SELECT
                DATE_TRUNC('month', CAST(paid_date AS DATE))::DATE
                    AS month,
                COUNT(*) AS payment_count,
                SUM(total_amount) AS cash_out
            FROM fact_expense
            WHERE UPPER(TRIM(status)) = 'PAID'
              AND paid_date IS NOT NULL
            GROUP BY 1
        """)

        # Client payment behaviour based on paid invoice records.
        con.execute("""
            CREATE VIEW v_client_payment_performance AS
            SELECT
                c.client_id,
                c.client_name,
                c.industry,
                c.payment_terms_days,
                c.payment_behaviour,
                COUNT(i.invoice_id) FILTER (
                    WHERE UPPER(TRIM(i.status)) = 'PAID'
                ) AS paid_invoice_count,
                ROUND(AVG(i.days_to_pay) FILTER (
                    WHERE UPPER(TRIM(i.status)) = 'PAID'
                      AND i.days_to_pay IS NOT NULL
                ), 2) AS avg_days_to_pay,
                ROUND(AVG(i.days_to_pay) FILTER (
                    WHERE UPPER(TRIM(i.status)) = 'PAID'
                      AND i.days_to_pay IS NOT NULL
                ) - c.payment_terms_days, 2) AS avg_days_vs_terms,
                SUM(i.balance_due) FILTER (
                    WHERE UPPER(TRIM(i.status)) IN (
                        'SENT', 'OVERDUE', 'PARTIALLY_PAID'
                    )
                ) AS open_receivables
            FROM dim_client c
            LEFT JOIN fact_invoice i USING (client_id)
            GROUP BY
                c.client_id,
                c.client_name,
                c.industry,
                c.payment_terms_days,
                c.payment_behaviour
        """)

        # Validation results.
        print("\n" + "=" * 65)
        print("DATABASE VALIDATION")
        print("=" * 65)

        for table in [
            "dim_client",
            "fact_invoice",
            "fact_invoice_payment",
            "fact_expense",
        ]:
            result = con.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()[0]
            print(f"{table}: {result:,} rows")

        print("\nOpen receivables:")
        print(con.execute("""
            SELECT
                COUNT(*) AS open_invoices,
                SUM(balance_due) AS open_balance
            FROM v_open_invoices
        """).fetchdf().to_string(index=False))

        print("\nAgeing reconciliation:")
        print(con.execute("""
            SELECT *
            FROM v_receivables_ageing
            ORDER BY CASE ageing_group
                WHEN 'Current / Not yet due' THEN 1
                WHEN '0-30 days' THEN 2
                WHEN '31-60 days' THEN 3
                WHEN '61-90 days' THEN 4
                WHEN '90+ days' THEN 5
                ELSE 6
            END
        """).fetchdf().to_string(index=False))

        print("\nPayment reconciliation exceptions:")
        print(con.execute("""
            SELECT *
            FROM v_invoice_payment_reconciliation
            WHERE reconciliation_status = 'MISMATCH'
        """).fetchdf().to_string(index=False))

        print("\nCash-flow totals:")
        print(con.execute("""
            SELECT
                (SELECT SUM(amount) FROM fact_invoice_payment)
                    AS total_cash_in,
                (SELECT SUM(total_amount)
                 FROM fact_expense
                 WHERE UPPER(TRIM(status)) = 'PAID'
                   AND paid_date IS NOT NULL)
                    AS total_cash_out
        """).fetchdf().to_string(index=False))

        print("\nDatabase created successfully:")
        print(DB_PATH)

    finally:
        con.close()

if __name__ == "__main__":
    main()
