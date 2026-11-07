-- ============================================================
-- PULSEIQ PHASE 3 - TASK 12
-- SQL 04: CLIENT PAYMENT PERFORMANCE
-- Purpose: Analyse client payment behaviour and slow payers.
-- Source: dim_client and fact_invoice
-- ============================================================

SELECT
    c.client_id,
    c.client_name,
    c.industry,
    c.payment_terms_days,
    c.payment_behaviour,

    COUNT(i.invoice_id) FILTER (
        WHERE UPPER(TRIM(i.status)) = 'PAID'
    ) AS paid_invoice_count,

    ROUND(
        AVG(i.days_to_pay) FILTER (
            WHERE UPPER(TRIM(i.status)) = 'PAID'
              AND i.days_to_pay IS NOT NULL
        ),
        2
    ) AS avg_days_to_pay,

    ROUND(
        AVG(i.days_to_pay) FILTER (
            WHERE UPPER(TRIM(i.status)) = 'PAID'
              AND i.days_to_pay IS NOT NULL
        ) - c.payment_terms_days,
        2
    ) AS avg_days_vs_terms,

    SUM(i.balance_due) FILTER (
        WHERE UPPER(TRIM(i.status)) IN (
            'SENT', 'OVERDUE', 'PARTIALLY_PAID'
        )
    ) AS open_receivables

FROM dim_client c
LEFT JOIN fact_invoice i
    USING (client_id)

GROUP BY
    c.client_id,
    c.client_name,
    c.industry,
    c.payment_terms_days,
    c.payment_behaviour

ORDER BY
    open_receivables DESC NULLS LAST;
