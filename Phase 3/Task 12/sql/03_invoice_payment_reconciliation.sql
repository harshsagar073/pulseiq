-- ============================================================
-- PULSEIQ PHASE 3 - TASK 12
-- SQL 03: INVOICE PAYMENT RECONCILIATION
-- Purpose: Compare invoice paid amount with payment transactions.
-- Source: fact_invoice and fact_invoice_payment
-- ============================================================

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

    COALESCE(p.payment_count, 0)
        AS payment_count,

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
LEFT JOIN payment_totals p
    USING (invoice_id)

ORDER BY
    CASE
        WHEN ABS(
            i.amount_paid - COALESCE(p.transaction_payment_total, 0)
        ) > 0.01 THEN 0
        ELSE 1
    END,
    ABS(
        i.amount_paid - COALESCE(p.transaction_payment_total, 0)
    ) DESC;
