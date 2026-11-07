from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

BASE = Path(__file__).resolve().parent
DB_PATH = BASE / "pulseiq_task11.duckdb"

st.set_page_config(
    page_title="PulseIQ | Profit & Loss",
    page_icon="📊",
    layout="wide"
)

st.title("PulseIQ | Profit & Loss & Expense Analytics")
st.caption("Phase 3 · Task 11 · Financial performance | April 2025 – September 2026")

if not DB_PATH.exists():
    st.error("Task 11 database not found. Run scripts/load_task11.py first.")
    st.stop()

@st.cache_data
def load_data():
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        pnl = con.execute(
            "SELECT * FROM v_monthly_pnl ORDER BY month"
        ).fetchdf()

        detail = con.execute(
            "SELECT * FROM v_monthly_pnl_detail ORDER BY month, account_code"
        ).fetchdf()

        categories = con.execute(
            "SELECT * FROM v_expense_by_category ORDER BY expense_amount DESC"
        ).fetchdf()

        vendors = con.execute(
            "SELECT * FROM v_top_10_vendors ORDER BY expense_amount DESC"
        ).fetchdf()
    finally:
        con.close()

    return pnl, detail, categories, vendors


pnl, detail, categories, vendors = load_data()

if pnl.empty:
    st.warning("No monthly P&L data found.")
    st.stop()

def crore(value):
    return f"₹{value / 10000000:,.2f} Cr"

def rupees(value):
    return f"₹{value:,.0f}"

# Overall KPIs
total_revenue = pnl["revenue"].sum()
total_expenses = pnl["expenses"].sum()
total_profit = pnl["net_profit"].sum()
overall_margin = (
    total_profit / total_revenue * 100 if total_revenue else 0
)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Revenue", crore(total_revenue))
c2.metric("Total Expenses", crore(total_expenses))
c3.metric("Net Profit", crore(total_profit))
c4.metric("Profit Margin", f"{overall_margin:.2f}%")

st.divider()

# Monthly trend
st.subheader("Monthly Financial Performance")

fig = go.Figure()
fig.add_trace(go.Bar(
    x=pnl["month"],
    y=pnl["revenue"],
    name="Revenue"
))
fig.add_trace(go.Bar(
    x=pnl["month"],
    y=pnl["expenses"],
    name="Expenses"
))
fig.add_trace(go.Scatter(
    x=pnl["month"],
    y=pnl["net_profit"],
    name="Net Profit",
    mode="lines+markers",
    yaxis="y2"
))
fig.update_layout(
    barmode="group",
    xaxis_title="Month",
    yaxis=dict(title="Amount (₹)", tickformat=",.0f"),
    yaxis2=dict(
        title="Net Profit (₹)",
        overlaying="y",
        side="right",
        showgrid=False
    ),
    legend_title="Financial Measure",
    height=480
)
st.plotly_chart(fig, use_container_width=True)

# Month selector and P&L
st.divider()
st.subheader("Monthly Profit & Loss Statement")

months = pnl["month"].astype(str).tolist()
selected_month = st.selectbox(
    "Select a month",
    months,
    index=len(months) - 1
)

selected = pnl[pnl["month"].astype(str) == selected_month].iloc[0]
month_detail = detail[detail["month"].astype(str) == selected_month].copy()

m1, m2, m3 = st.columns(3)
m1.metric("Revenue", rupees(selected["revenue"]))
m2.metric("Expenses", rupees(selected["expenses"]))
m3.metric(
    "Net Profit",
    rupees(selected["net_profit"]),
    f'{selected["profit_margin_pct"]:.2f}% margin'
)

month_detail = month_detail.rename(columns={
    "account_code": "Account Code",
    "account_name": "Account",
    "account_type": "Type",
    "amount": "Amount (₹)"
})

month_detail["Amount (₹)"] = month_detail["Amount (₹)"].round(2)

st.dataframe(
    month_detail[["Account Code", "Account", "Type", "Amount (₹)"]],
    use_container_width=True,
    hide_index=True
)

st.caption(
    "Revenue is shown as credit less debit. Expenses are shown as debit less credit. "
    "Only active detail accounts classified under Profit & Loss are included."
)

# Full monthly P&L table
with st.expander("View all monthly P&L totals"):
    display_pnl = pnl.copy()
    display_pnl["profit_margin_pct"] = display_pnl["profit_margin_pct"].round(2)
    st.dataframe(display_pnl, use_container_width=True, hide_index=True)

# Category and vendor analytics
st.divider()
st.subheader("Expense Analytics")

left, right = st.columns(2)

with left:
    st.markdown("**Expenses by Category**")
    category_fig = px.bar(
        categories.sort_values("expense_amount"),
        x="expense_amount",
        y="category",
        orientation="h",
        labels={
            "expense_amount": "Expense (₹)",
            "category": "Category"
        },
        hover_data=["bill_count"]
    )
    category_fig.update_layout(height=520)
    st.plotly_chart(category_fig, use_container_width=True)

with right:
    st.markdown("**Top 10 Vendors**")
    vendor_fig = px.bar(
        vendors.sort_values("expense_amount"),
        x="expense_amount",
        y="vendor_name",
        orientation="h",
        labels={
            "expense_amount": "Expense (₹)",
            "vendor_name": "Vendor"
        },
        hover_data=["bill_count"]
    )
    vendor_fig.update_layout(height=520)
    st.plotly_chart(vendor_fig, use_container_width=True)

st.caption(
    "Category and vendor charts use fact_expense.amount_excl_gst "
    "(invoice/bill amount excluding GST). They are not the full ledger P&L expense total."
)

with st.expander("View category and vendor tables"):
    st.markdown("**Category totals**")
    st.dataframe(categories, use_container_width=True, hide_index=True)
    st.markdown("**Top 10 vendors**")
    st.dataframe(vendors, use_container_width=True, hide_index=True)

# Findings
st.divider()
st.subheader("Key Business Findings")

best_month = pnl.loc[pnl["profit_margin_pct"].idxmax()]
worst_month = pnl.loc[pnl["profit_margin_pct"].idxmin()]
top_category = categories.iloc[0]
top_vendor = vendors.iloc[0]

st.markdown(
    f"""
1. **Margin volatility:** Monthly profit margin ranged from
   **{worst_month['profit_margin_pct']:.2f}% ({worst_month['month']})**
   to **{best_month['profit_margin_pct']:.2f}% ({best_month['month']})**.
   This suggests profitability is not consistent across months.

2. **Largest expense category:** **{top_category['category']}**
   recorded **{crore(top_category['expense_amount'])}** across
   {int(top_category['bill_count'])} bills. This category is a useful
   starting point for reviewing recurring commitments and cost efficiency.

3. **Largest vendor spend:** **{top_vendor['vendor_name']}**
   accounted for **{crore(top_vendor['expense_amount'])}** across
   {int(top_vendor['bill_count'])} bills. Review contract terms, renewal
   dates and invoice-level details before deciding on cost reductions.
    """
)

st.divider()
st.subheader("Interpretation Challenge: Revenue Grows but Margin Falls")

st.markdown(
    """
Possible causes to investigate:

- **Operating costs rise faster than revenue:** compare monthly expense
  growth with revenue growth by account.
- **Higher people costs or overtime:** compare salary, incentives and
  overtime expense with monthly revenue.
- **Higher vendor or infrastructure costs:** compare category and vendor
  bills by month, then identify which suppliers or categories increased.

These are hypotheses to test, not confirmed causes from the current dashboard.
"""
)

st.caption(
    "Source: PulseIQ fact_ledger, dim_account, fact_expense and dim_vendor. "
    "Reporting period: April 2025 to September 2026."
)
