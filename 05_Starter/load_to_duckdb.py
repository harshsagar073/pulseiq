"""Load CSV exports into the raw schema of a local DuckDB database."""

from pathlib import Path
import duckdb

BASE_DIR = Path(__file__).resolve().parent.parent
CSV_DIR = BASE_DIR / "03_Data" / "csv"
DB_PATH = BASE_DIR / "pulseiq.duckdb"

if not CSV_DIR.exists():
    raise FileNotFoundError(f"CSV folder not found: {CSV_DIR}")

csv_files = sorted(CSV_DIR.glob("*.csv"))

if not csv_files:
    raise FileNotFoundError(
        f"No CSV files found in {CSV_DIR}. Export the Excel sheets first."
    )

con = duckdb.connect(str(DB_PATH))

try:
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")

    for csv_file in csv_files:
        table_name = csv_file.stem

        # The names are taken from our controlled CSV filenames.
        con.execute(
            f'CREATE OR REPLACE TABLE raw."{table_name}" '
            f"AS SELECT * FROM read_csv_auto('{csv_file.as_posix()}', "
            "header=true, sample_size=-1)"
        )

        count = con.execute(
            f'SELECT COUNT(*) FROM raw."{table_name}"'
        ).fetchone()[0]

        print(f"raw.{table_name:<30} {count:>8} rows")

    print(f"\nDatabase created/updated: {DB_PATH}")
    print(f"CSV files loaded: {len(csv_files)}")

finally:
    con.close()
