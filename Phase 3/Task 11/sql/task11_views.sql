-- Task 11: Profit and Loss and Expense Analytics
-- Exclude group accounts to prevent double counting.

CREATE OR REPLACE VIEW v_account_detail AS
SELECT
    account_code,
    account_name,
    account_type,
    normal_balance,
    statement
FROM dim_account
WHERE COALESCE(is_group, 'N') = 'N'
  AND COALESCE(is_active, 'Y') = 'Y';

CREATE OR REPLACE VIEW v_monthly_pnl AS
WITH account_month AS (
    SELECT
        l.posting_period AS month,
        a.account_type,
        SUM(
            CASE
                WHEN a.account_type = 'INCOME' THEN l.credit - l.debit
                WHEN a.account_type = 'EXPENSE' THEN l.debit - l.credit
                ELSE 0
            END
        ) AS amount
    FROM fact_ledger l
    JOIN v_account_detail a
        ON l.account_code = a.account_code
    WHERE a.statement = 'Profit & Loss'
      AND a.account_type IN ('INCOME', 'EXPENSE')
    GROUP BY 1, 2
)
SELECT
    month,
    SUM(CASE WHEN account_type = 'INCOME' THEN amount ELSE 0 END) AS revenue,
    SUM(CASE WHEN account_type = 'EXPENSE' THEN amount ELSE 0 END) AS expenses,
    SUM(CASE WHEN account_type = 'INCOME' THEN amount ELSE 0 END)
      - SUM(CASE WHEN account_type = 'EXPENSE' THEN amount ELSE 0 END) AS net_profit,
    CASE
        WHEN SUM(CASE WHEN account_type = 'INCOME' THEN amount ELSE 0 END) = 0
        THEN 0
        ELSE (
            SUM(CASE WHEN account_type = 'INCOME' THEN amount ELSE 0 END)
            - SUM(CASE WHEN account_type = 'EXPENSE' THEN amount ELSE 0 END)
        ) / SUM(CASE WHEN account_type = 'INCOME' THEN amount ELSE 0 END) * 100
    END AS profit_margin_pct
FROM account_month
GROUP BY month;

CREATE OR REPLACE VIEW v_expense_by_category AS
SELECT
    e.category_account AS account_code,
    a.account_name AS category,
    SUM(e.amount_excl_gst) AS expense_amount,
    COUNT(*) AS bill_count
FROM fact_expense e
JOIN v_account_detail a
    ON e.category_account = a.account_code
WHERE a.statement = 'Profit & Loss'
  AND a.account_type = 'EXPENSE'
GROUP BY 1, 2;

CREATE OR REPLACE VIEW v_top_10_vendors AS
SELECT
    v.vendor_id,
    v.vendor_name,
    SUM(e.amount_excl_gst) AS expense_amount,
    COUNT(*) AS bill_count
FROM fact_expense e
JOIN dim_vendor v
    ON e.vendor_id = v.vendor_id
GROUP BY 1, 2
ORDER BY expense_amount DESC
LIMIT 10;

CREATE OR REPLACE VIEW v_monthly_pnl_detail AS
SELECT
    l.posting_period AS month,
    l.account_code,
    a.account_name,
    a.account_type,
    SUM(
        CASE
            WHEN a.account_type = 'INCOME' THEN l.credit - l.debit
            WHEN a.account_type = 'EXPENSE' THEN l.debit - l.credit
            ELSE 0
        END
    ) AS amount
FROM fact_ledger l
JOIN v_account_detail a
    ON l.account_code = a.account_code
WHERE a.statement = 'Profit & Loss'
  AND a.account_type IN ('INCOME', 'EXPENSE')
GROUP BY 1, 2, 3, 4;
