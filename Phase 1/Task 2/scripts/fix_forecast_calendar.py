from pathlib import Path
from datetime import date, timedelta
import calendar
import duckdb

BASE = Path(__file__).resolve().parent.parent
DB = BASE / "pulseiq_warehouse.duckdb"

con = duckdb.connect(str(DB))

try:
    # Add the missing forecast dates through 31 March 2027.
    existing = {
        row[0] for row in
        con.execute("SELECT date FROM warehouse.dim_date").fetchall()
    }

    rows = []
    current = date(2027, 1, 1)
    last = date(2027, 3, 31)

    while current <= last:
        if current not in existing:
            year = current.year
            month = current.month
            month_start = current.replace(day=1)
            month_end = current.replace(
                day=calendar.monthrange(year, month)[1]
            )
            weekday = current.weekday()

            rows.append((
                current,
                int(current.strftime("%Y%m%d")),
                year,
                (month - 1) // 3 + 1,
                month,
                current.strftime("%B"),
                current.strftime("%Y-%m"),
                current.isocalendar().week,
                current.strftime("%A"),
                "Y" if weekday >= 5 else "N",
                "N",  # Future public-holiday data was not supplied.
                "Y" if weekday < 5 else "N",
                "FY2026-27",
                "Q4",
                month + 9,
                "Y" if current == month_end else "N",
                month_start,
                month_end,
            ))
        current += timedelta(days=1)

    if rows:
        con.executemany("""
            INSERT INTO warehouse.dim_date (
                date, date_key, year, quarter, month_number, month_name,
                year_month, week_of_year, day_of_week, is_weekend,
                is_holiday, is_working_day, financial_year, fiscal_quarter,
                fiscal_month_number, is_month_end, month_start_date,
                month_end_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, rows)

    # "ALL" means company-wide, not a real department.
    con.execute("""
        ALTER TABLE warehouse.fact_forecast
        ADD COLUMN IF NOT EXISTS forecast_scope VARCHAR
    """)
    con.execute("""
        UPDATE warehouse.fact_forecast
        SET forecast_scope = 'COMPANY',
            department_id = NULL
        WHERE department_id = 'ALL'
    """)
    con.execute("""
        UPDATE warehouse.fact_forecast
        SET forecast_scope = 'DEPARTMENT'
        WHERE forecast_scope IS NULL
    """)

    print("CALENDAR AND FORECAST UPDATE COMPLETE")
    print("New calendar rows inserted:", len(rows))
    print("Calendar range:", con.execute("""
        SELECT MIN(date), MAX(date), COUNT(*)
        FROM warehouse.dim_date
    """).fetchone())

    print("\nForecast scopes:")
    print(con.execute("""
        SELECT forecast_scope, COUNT(*)
        FROM warehouse.fact_forecast
        GROUP BY forecast_scope
        ORDER BY forecast_scope
    """).fetchdf().to_string(index=False))

    print("\nRemaining company-wide department markers:",
          con.execute("""
              SELECT COUNT(*) FROM warehouse.fact_forecast
              WHERE department_id = 'ALL'
          """).fetchone()[0])

finally:
    con.close()
