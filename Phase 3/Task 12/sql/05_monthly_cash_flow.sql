-- ============================================================
-- PULSEIQ PHASE 3 - TASK 12
-- SQL 05: MONTHLY CASH FLOW
-- Purpose: Analyse monthly cash received and cash paid.
-- Cash-in source: fact_invoice_payment.payment_date
-- Cash-out source: fact_expense.paid_date
-- ============================================================

WITH cash_in AS (
    SELECT
        DATE_TRUNC(
            'month',
            CAST(payment_date AS DATE)
        )::DATE AS month,
        COUNT(*) AS payment_count_in,
        SUM(amount) AS cash_in
    FROM fact_invoice_payment
    GROUP BY 1
),

cash_out AS (
    SELECT
        DATE_TRUNC(
            'month',
            CAST(paid_date AS DATE)
        )::DATE AS month,
        COUNT(*) AS payment_count_out,
        SUM(total_amount) AS cash_out
    FROM fact_expense
    WHERE UPPER(TRIM(status)) = 'PAID'
      AND paid_date IS NOT NULL
    GROUP BY 1
)

SELECT
    COALESCE(i.month, o.month) AS month,
    COALESCE(i.payment_count_in, 0) AS payment_count_in,
    COALESCE(i.cash_in, 0) AS cash_in,
    COALESCE(o.payment_count_out, 0) AS payment_count_out,
    COALESCE(o.cash_out, 0) AS cash_out,

    COALESCE(i.cash_in, 0) - COALESCE(o.cash_out, 0)
        AS net_cash_flow

FROM cash_in i
FULL OUTER JOIN cash_out o
    USING (month)

ORDER BY month;
