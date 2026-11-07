-- ============================================================
-- PULSEIQ PHASE 3 - TASK 12
-- SQL 01: OPEN INVOICES
-- Purpose: Identify all outstanding invoices.
-- Source: fact_invoice and dim_client
-- ============================================================

SELECT
    i.invoice_id,
    i.invoice_number,
    i.client_id,
    c.client_name,
    c.industry,
    c.city,
    i.invoice_date,
    i.due_date,
    i.status,
    i.total_amount,
    i.amount_paid,
    i.balance_due,
    c.payment_terms_days,
    c.payment_behaviour
FROM fact_invoice i
LEFT JOIN dim_client c
    USING (client_id)
WHERE UPPER(TRIM(i.status)) IN (
    'SENT',
    'OVERDUE',
    'PARTIALLY_PAID'
)
ORDER BY
    i.due_date ASC,
    i.balance_due DESC;
