import importlib.util
import unittest
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "run_dq_checks.py"

spec = importlib.util.spec_from_file_location("dq_runner", RUNNER)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

CHECKS = {c["id"]: c for c in runner.CHECKS}


class DataQualityRuleTests(unittest.TestCase):
    """Test each SQL predicate using isolated in-memory DuckDB data."""

    def setUp(self):
        self.con = duckdb.connect(":memory:")
        self.con.execute("CREATE SCHEMA warehouse")

    def tearDown(self):
        self.con.close()

    def detect(self, check_id):
        sql = CHECKS[check_id]["sql"]
        self.assertIsNotNone(sql, f"{check_id} is a special non-SQL check")
        return self.con.execute(sql).fetchall()

    def test_c01_payroll_ledger_mismatch(self):
        self.con.execute("""
            CREATE TABLE warehouse.fact_payroll (
                period_end_date DATE, employer_cost DOUBLE
            );
            CREATE TABLE warehouse.fact_ledger (
                entry_date DATE, account_code INTEGER,
                debit DOUBLE, credit DOUBLE
            );
            INSERT INTO warehouse.fact_payroll VALUES ('2026-06-30', 1000);
            INSERT INTO warehouse.fact_ledger
            VALUES ('2026-06-30', 5001, 900, 0);
        """)
        self.assertGreater(len(self.detect("DQ-C01")), 0)

    def test_c02_unbalanced_ledger(self):
        self.con.execute("""
            CREATE TABLE warehouse.fact_ledger (
                entry_id VARCHAR, debit DOUBLE, credit DOUBLE
            );
            INSERT INTO warehouse.fact_ledger VALUES ('TEST-1', 100, 90);
        """)
        self.assertGreater(len(self.detect("DQ-C02")), 0)

    def test_c03_duplicate_payroll_key(self):
        self.con.execute("""
            CREATE TABLE warehouse.fact_payroll (
                employee_id VARCHAR, run_id VARCHAR
            );
            INSERT INTO warehouse.fact_payroll VALUES
                ('EMP-TEST', 'RUN-1'), ('EMP-TEST', 'RUN-1');
        """)
        self.assertGreater(len(self.detect("DQ-C03")), 0)

    def test_c04_orphan_employee(self):
        self.con.execute("""
            CREATE TABLE warehouse.fact_payroll (employee_id VARCHAR);
            CREATE TABLE warehouse.dim_employee (employee_id VARCHAR);
            INSERT INTO warehouse.fact_payroll VALUES ('EMP-MISSING');
        """)
        self.assertGreater(len(self.detect("DQ-C04")), 0)

    def test_c05_attendance_after_exit(self):
        self.con.execute("""
            CREATE TABLE warehouse.fact_attendance_monthly (
                attendance_fact_id VARCHAR, employee_id VARCHAR,
                period_end_date DATE
            );
            CREATE TABLE warehouse.dim_employee (
                employee_id VARCHAR, is_current VARCHAR, exit_date DATE
            );
            INSERT INTO warehouse.fact_attendance_monthly
            VALUES ('A-1', 'EMP-1', '2026-06-30');
            INSERT INTO warehouse.dim_employee
            VALUES ('EMP-1', 'Y', '2026-05-15');
        """)
        self.assertGreater(len(self.detect("DQ-C05")), 0)

    def test_c06_unpaid_leave_mismatch(self):
        self.con.execute("""
            CREATE TABLE warehouse.fact_attendance_monthly (
                employee_id VARCHAR, period_end_date DATE,
                unpaid_absence_days DOUBLE
            );
            CREATE TABLE warehouse.fact_payroll (
                employee_id VARCHAR, period_end_date DATE, lop_days DOUBLE
            );
            INSERT INTO warehouse.fact_attendance_monthly
            VALUES ('EMP-1', '2026-06-30', 2);
            INSERT INTO warehouse.fact_payroll
            VALUES ('EMP-1', '2026-06-30', 0);
        """)
        self.assertGreater(len(self.detect("DQ-C06")), 0)

    def test_c07_overpaid_invoice(self):
        self.con.execute("""
            CREATE TABLE warehouse.fact_invoice (
                invoice_id VARCHAR, total_amount DOUBLE,
                amount_paid DOUBLE, balance_due DOUBLE
            );
            INSERT INTO warehouse.fact_invoice
            VALUES ('INV-TEST', 100, 110, -10);
        """)
        self.assertGreater(len(self.detect("DQ-C07")), 0)

    def test_c08_expense_arithmetic(self):
        self.con.execute("""
            CREATE TABLE warehouse.fact_expense (
                expense_id VARCHAR, amount_excl_gst DOUBLE,
                gst_amount DOUBLE, total_amount DOUBLE
            );
            INSERT INTO warehouse.fact_expense
            VALUES ('EXP-TEST', 100, 18, 150);
        """)
        self.assertGreater(len(self.detect("DQ-C08")), 0)

    def test_c09_invalid_task_dates(self):
        self.con.execute("""
            CREATE TABLE warehouse.fact_task (
                task_id VARCHAR, status VARCHAR,
                started_date DATE, completed_date DATE
            );
            INSERT INTO warehouse.fact_task
            VALUES ('TASK-TEST', 'Done', '2026-06-10', '2026-06-01');
        """)
        self.assertGreater(len(self.detect("DQ-C09")), 0)

    def test_c10_invalid_leave_dates(self):
        self.con.execute("""
            CREATE TABLE warehouse.fact_leave (
                leave_request_id VARCHAR, start_date DATE, end_date DATE
            );
            INSERT INTO warehouse.fact_leave
            VALUES ('LEAVE-TEST', '2026-06-10', '2026-06-09');
        """)
        self.assertGreater(len(self.detect("DQ-C10")), 0)

    def test_c11_stale_prediction(self):
        self.con.execute("""
            CREATE TABLE warehouse.fact_attrition_risk (
                prediction_id VARCHAR, as_of_date DATE
            );
            INSERT INTO warehouse.fact_attrition_risk VALUES
                ('OLD', '2026-01-01'),
                ('LATEST', '2026-10-01');
        """)
        self.assertGreater(len(self.detect("DQ-C11")), 0)

    def test_c12_overlapping_employee_history(self):
        self.con.execute("""
            CREATE TABLE warehouse.dim_employee (
                employee_id VARCHAR, employee_key INTEGER,
                valid_from DATE, valid_to DATE
            );
            INSERT INTO warehouse.dim_employee VALUES
                ('EMP-1', 1, '2026-01-01', '2026-06-10'),
                ('EMP-1', 2, '2026-06-01', '2026-12-31');
        """)
        self.assertGreater(len(self.detect("DQ-C12")), 0)

    def test_c13_pipeline_freshness_requires_real_log(self):
        # The runner handles this check specially rather than through SQL.
        # Do not manufacture a successful ETL timestamp for the test.
        self.assertIsNone(CHECKS["DQ-C13"]["sql"])
        self.assertEqual(CHECKS["DQ-C13"]["table"], "etl_run_log")

    def test_c14_small_group_is_flagged(self):
        self.con.execute("""
            CREATE TABLE warehouse.fact_headcount_monthly (
                month_start_date DATE, department_id INTEGER,
                headcount_end INTEGER
            );
            CREATE TABLE warehouse.fact_attrition_risk (
                as_of_date DATE, department_id INTEGER, employee_id VARCHAR
            );
            CREATE TABLE warehouse.fact_payroll (
                period_end_date DATE, department_id INTEGER, employee_id VARCHAR
            );
            CREATE TABLE warehouse.fact_attendance_monthly (
                period_end_date DATE, department_id INTEGER, employee_id VARCHAR
            );
            INSERT INTO warehouse.fact_headcount_monthly
            VALUES ('2026-06-01', 1, 2);
        """)
        self.assertGreater(len(self.detect("DQ-C14")), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
