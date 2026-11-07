# PulseIQ – Phase 3, Task 11
## Profit & Loss and Expense Analytics

### 1. Project Overview

This project provides a financial analytics dashboard to analyse revenue, expenses, profitability, monthly financial performance and vendor spending from April 2025 to September 2026.

### 2. Objectives

- Calculate revenue, expenses, net profit and profit margin.
- Analyse monthly financial performance.
- Build a monthly Profit & Loss statement.
- Analyse expenses by category.
- Identify the top 10 vendors by spending.
- Present business findings and possible explanations for margin changes.

### 3. Data Sources

| Table | Description |
|---|---|
| fact_ledger | Financial ledger transactions |
| dim_account | Account classifications and hierarchy |
| fact_expense | Invoice-level expense records |
| dim_vendor | Vendor information |

### 4. Data Processing and Methodology

- Only active Profit & Loss detail accounts are included.
- Group accounts are excluded to prevent double counting.
- Revenue = Credit - Debit.
- Expenses = Debit - Credit.
- Net Profit = Revenue - Expenses.
- Profit Margin (%) = (Net Profit / Revenue) × 100.

### 5. Overall Financial Results

Reporting period: April 2025 – September 2026.

| Metric | Calculated Result |
|---|---:|
| Total Revenue | ₹1,260,930,052.00 |
| Total Expenses | ₹1,036,264,914.42 |
| Net Profit | ₹224,665,137.58 |
| Profit Margin | 17.817415% |

### 6. Dashboard Features

- Overall financial KPI cards.
- Monthly revenue and expense trends.
- Monthly Profit & Loss statement with month selector.
- Monthly net profit and profit margin.
- Expense breakdown by category.
- Top 10 vendors by spending.
- Key business findings and interpretation.

### 7. Expense Analysis

Category and vendor charts use `fact_expense.amount_excl_gst`, representing invoice-level amounts excluding GST.

These invoice-level values are not the full ledger P&L expense total and should not be added to the ledger expense total.

- Largest expense category: Office Rent, approximately ₹3.82 crore across 54 bills.
- Highest-spend vendor: Skyline Realty Holdings, approximately ₹1.69 crore across 22 bills.

### 8. Key Business Findings

1. **Margin variation:** Monthly profit margin ranged from approximately 8.27% in July 2025 to 27.16% in August 2026.
2. **Expense concentration:** Office Rent was the largest category in the invoice-level expense analysis.
3. **Vendor spending:** Skyline Realty Holdings was the highest-spend vendor in the invoice-level analysis.

### 9. Interpretation: Revenue Growth but Falling Margin

Possible causes to investigate:

1. Operating costs may be increasing faster than revenue. Compare monthly expense growth with revenue growth by account.
2. Employee costs or overtime may be increasing. Compare salary, incentives and overtime expenses with monthly revenue.
3. Vendor or infrastructure spending may be increasing. Compare monthly category and vendor bills to identify increases.

These are hypotheses, not confirmed causes. Further analysis is needed to establish causation.

### 10. Validation and Reconciliation

The supplied workbook sheet index confirms:

| Source Table | Rows |
|---|---:|
| fact_ledger | 6,784 |
| dim_account | 47 |
| fact_expense | 501 |
| dim_vendor | 30 |

Financial summary evidence is stored in `evidence/tie_out_summary.csv`.

**Reconciliation limitation:** The supplied workbook sheet index does not contain a README sheet or separate headline P&L figures. Therefore, external headline comparison is marked **Not Verifiable**. This is not an independently verified tie-out.

### 11. Project Structure

```text
Task 11/
├── app.py
├── requirements.txt
├── README.md
├── pulseiq_task11.duckdb
├── sql/
│   └── task11_views.sql
├── scripts/
│   ├── inspect_data.py
│   └── load_task11.py
├── docs/
│   └── initial_data_inspection.txt
└── evidence/
    ├── tie_out_summary.csv
    └── task11_dashboard.png (to be added)
