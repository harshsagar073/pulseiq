from pathlib import Path
import duckdb

BASE = Path(__file__).resolve().parents[1]
DATA = Path("/Users/admin/Desktop/PulseIQ/Phase 1/Task 1/validated")
DB_PATH = BASE / "pulseiq_task11.duckdb"

FILES = {
    "fact_ledger": DATA / "fact_ledger.csv",
    "dim_account": DATA / "dim_account.csv",
    "fact_expense": DATA / "fact_expense.csv",
    "dim_vendor": DATA / "dim_vendor.csv",
}

con = duckdb.connect(str(DB_PATH))

try:
    for table, path in FILES.items():
        if not path.exists():
            raise FileNotFoundError(f"Missing source file: {path}")

        con.execute(
            f'CREATE OR REPLACE TABLE "{table}" AS '
            "SELECT * FROM read_csv_auto(?, header=true)",
            [str(path)]
        )
        count = con.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
        print(f"Loaded {table}: {count:,} rows")

    sql_path = BASE / "sql" / "task11_views.sql"
    con.execute(sql_path.read_text(encoding="utf-8"))

    print("\nViews created successfully.")

    print("\nMonthly P&L:")
    result = con.execute("""
        SELECT * FROM v_monthly_pnl ORDER BY month
    """).fetchdf()
    print(result.to_string(index=False))

    print("\nOverall P&L totals:")
    print(con.execute("""
        SELECT
            SUM(revenue) AS revenue,
            SUM(expenses) AS expenses,
            SUM(net_profit) AS net_profit,
            CASE WHEN SUM(revenue) = 0 THEN 0
                 ELSE SUM(net_profit) / SUM(revenue) * 100
            END AS margin_pct
        FROM v_monthly_pnl
    """).fetchdf().to_string(index=False))

    print("\nExpense categories:")
    print(con.execute("""
        SELECT * FROM v_expense_by_category
        ORDER BY expense_amount DESC
    """).fetchdf().to_string(index=False))

    print("\nTop 10 vendors:")
    print(con.execute("""
        SELECT * FROM v_top_10_vendors
        ORDER BY expense_amount DESC
    """).fetchdf().to_string(index=False))

finally:
    con.close()

print(f"\nDatabase saved at: {DB_PATH}")
