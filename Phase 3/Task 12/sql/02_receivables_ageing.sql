-- ============================================================
-- PULSEIQ PHASE 3 - TASK 12
-- SQL 02: RECEIVABLES AGEING
-- Purpose: Reconcile outstanding invoices by ageing bucket.
-- Source: v_open_invoices
-- ============================================================

SELECT
    CASE
        WHEN ageing_bucket_at_cutoff = 'Not yet due'
            THEN 'Current / Not yet due'

        WHEN ageing_bucket_at_cutoff IN ('0-30 days', '1-30 days')
            THEN '0-30 days'

        WHEN ageing_bucket_at_cutoff IN ('31-60 days', '31–60 days')
            THEN '31-60 days'

        WHEN ageing_bucket_at_cutoff IN ('61-90 days', '61–90 days')
            THEN '61-90 days'

        WHEN ageing_bucket_at_cutoff IN ('90+ days', '90+')
            THEN '90+ days'

        ELSE 'Other / Review'
    END AS ageing_group,

    COUNT(*) AS invoice_count,
    SUM(balance_due) AS outstanding_amount

FROM v_open_invoices

GROUP BY 1

ORDER BY
    CASE ageing_group
        WHEN 'Current / Not yet due' THEN 1
        WHEN '0-30 days' THEN 2
        WHEN '31-60 days' THEN 3
        WHEN '61-90 days' THEN 4
        WHEN '90+ days' THEN 5
        ELSE 6
    END;
