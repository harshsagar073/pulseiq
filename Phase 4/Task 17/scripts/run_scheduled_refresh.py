from pathlib import Path
from datetime import datetime, timezone
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
TASK_DIR = ROOT / "Phase 4" / "Task 17"

DB_PATH = ROOT / "Phase 1" / "Task 4" / "pulseiq_task4.duckdb"
METADATA_PATH = TASK_DIR / "data" / "metadata.json"
CSV_PATH = TASK_DIR / "data" / "company_kpis.csv"

EXPORT_SCRIPT = TASK_DIR / "scripts" / "export_public_data.py"
VERIFY_SCRIPT = TASK_DIR / "scripts" / "verify_task17.py"

PUBLIC_FILES = [
    "Phase 4/Task 17/data/company_kpis.csv",
    "Phase 4/Task 17/data/metadata.json",
]


def run(command):
    print(f"\n$ {' '.join(map(str, command))}", flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def main():
    print("=" * 60)
    print("PULSEIQ TASK 17 — SCHEDULED PUBLIC DATA REFRESH")
    print("=" * 60)

    if not DB_PATH.exists():
        raise FileNotFoundError(f"Source database not found: {DB_PATH}")

    if not METADATA_PATH.exists():
        raise FileNotFoundError(f"Published metadata not found: {METADATA_PATH}")

    if not EXPORT_SCRIPT.exists() or not VERIFY_SCRIPT.exists():
        raise FileNotFoundError("Export or verification script is missing.")

    # Never include unrelated, previously staged changes in this commit.
    staged = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=ROOT,
        check=False,
    )
    if staged.returncode != 0:
        raise RuntimeError(
            "Git already has staged changes. Unstage or commit them before "
            "running the scheduled refresh."
        )

    with METADATA_PATH.open("r", encoding="utf-8") as file:
        metadata = json.load(file)

    exported_at = datetime.fromisoformat(
        metadata["exported_at_utc"].replace("Z", "+00:00")
    )
    source_modified_at = datetime.fromtimestamp(
        DB_PATH.stat().st_mtime,
        tz=timezone.utc,
    )

    print(f"Source database: {DB_PATH}")
    print(f"Source modified (UTC): {source_modified_at.isoformat()}")
    print(f"Last public export (UTC): {exported_at.isoformat()}")

    if source_modified_at <= exported_at:
        print("\nSKIPPED: The approved source database has not changed")
        print("since the last public export. No files were published.")
        return

    print("\nUPDATED SOURCE DETECTED — exporting public aggregates.")

    run([sys.executable, str(EXPORT_SCRIPT)])
    run([sys.executable, str(VERIFY_SCRIPT)])

    if not CSV_PATH.exists() or not METADATA_PATH.exists():
        raise RuntimeError("Expected public export files are missing.")

    # Stage only sanitized, company-level public outputs.
    run(["git", "add", "--", *PUBLIC_FILES])

    changed = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=ROOT,
        check=False,
    )

    if changed.returncode == 0:
        print("\nNo public data changes to commit.")
        return

    if changed.returncode != 1:
        raise RuntimeError("Could not inspect staged Git changes.")

    run([
        "git",
        "commit",
        "-m",
        "Refresh Task 17 public company KPI data",
    ])

    run(["git", "push", "origin", "main"])

    print("\nSUCCESS: Updated public KPI data pushed to GitHub.")
    print("Streamlit Community Cloud can now receive the updated data.")


if __name__ == "__main__":
    main()
