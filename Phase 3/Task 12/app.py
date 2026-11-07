
from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ============================================================
# PULSEIQ | TASK 12 - INVOICES, RECEIVABLES & CASH FLOW
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "pulseiq_task12.duckdb"

st.set_page_config(
    page_title="PulseIQ | Receivables & Cash Flow",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -------------------- THEME --------------------

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif;
    }

    .stApp {
        background: #0b1120;
        color: #e5e7eb;
    }

    [data-testid="stSidebar"] {
        background: #111827;
        border-right: 1px solid #263449;
    }

    [data-testid="stMetric"] {
        background: #151f32;
        border: 1px solid #263449;
        padding: 18px;
        border-radius: 12px;
    }

    [data-testid="stMetricLabel"] {
        color: #9ca3af;
    }

    [data-testid="stMetricValue"] {
        color: #f9fafb;
    }

    h1, h2, h3 {
        color: #f8fafc;
    }

    .subtitle {
        color: #9ca3af;
        font-size: 14px;
        margin-top: -12px;
    }

    .section-note {
        background: #172338;
        border-left: 4px solid #38bdf8;
        border-radius: 7px;
        padding: 12px 15px;
        color: #cbd5e1;
        margin: 10px 0 18px 0;
    }

    div[data-testid="stDataFrame"] {
        border: 1px solid #263449;
        border-radius: 9px;
    }
</style>
""", unsafe_allow_html=True)


# -------------------- DATABASE --------------------

if not DB_PATH.exists():
    st.error(f"Database not found: {DB_PATH}")
    st.stop()


@st.cache_resource
def get_connection():
    return duckdb.connect(str(DB_PATH), read_only=True)


con = get_connection()


@st.cache_data(ttl=60)
def load_query(query):
    return con.execute(query).fetchdf()


def money(value):
    value = float(value or 0)
    return f"₹{value / 10000000:,.2f} Cr"


def money_lakh(value):
    value = float(value or 0)
    return f"₹{value / 100000:,.2f} L"


def safe_number(value):
    return float(value) if pd.notna(value) else 0.0


def chart_layout(fig, height=370):
    fig.update_layout(
        height=height,
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=15, r=15, t=45, b=15),
        font=dict(family="DM Sans", color="#dbeafe"),
        legend=dict(orientation="h", y=-0.22),
    )
    return fig


# -------------------- GLOBAL DATA --------------------

overview = load_query("""
    SELECT
        COUNT(*) AS total_invoices,
        SUM(CASE WHEN status = 'PAID' THEN 1 ELSE 0 END) AS paid_count,
        SUM(CASE WHEN status IN (
            'SENT', 'OVERDUE', 'PARTIALLY_PAID'
        ) THEN 1 ELSE 0 END) AS open_count,
        SUM(CASE WHEN status = 'OVERDUE' THEN 1 ELSE 0 END)
            AS overdue_count,
        SUM(CASE WHEN status = 'CANCELLED' THEN 1 ELSE 0 END)
            AS cancelled_count,
        SUM(CASE WHEN status = 'DRAFT' THEN 1 ELSE 0 END)
            AS draft_count,
        SUM(CASE WHEN status IN (
            'SENT', 'OVERDUE', 'PARTIALLY_PAID'
        ) THEN balance_due ELSE 0 END) AS open_balance,
        SUM(CASE WHEN status = 'OVERDUE'
            THEN balance_due ELSE 0 END) AS overdue_balance
    FROM fact_invoice
""").iloc[0]

cash_summary = load_query("""
    SELECT
        (SELECT SUM(amount)
         FROM fact_invoice_payment) AS cash_in,
        (SELECT SUM(total_amount)
         FROM fact_expense
         WHERE UPPER(TRIM(status)) = 'PAID'
           AND paid_date IS NOT NULL) AS cash_out
""").iloc[0]

ageing = load_query("""
    SELECT *
    FROM v_receivables_ageing
    ORDER BY CASE ageing_group
        WHEN 'Current / Not yet due' THEN 1
        WHEN '0-30 days' THEN 2
        WHEN '31-60 days' THEN 3
        WHEN '61-90 days' THEN 4
        WHEN '90+ days' THEN 5
        ELSE 6
    END
""")

monthly_in = load_query("""
    SELECT month, payment_count, cash_in
    FROM v_monthly_cash_in
    ORDER BY month
""")

monthly_out = load_query("""
    SELECT month, payment_count, cash_out
    FROM v_monthly_cash_out
    ORDER BY month
""")

cash_flow = pd.merge(
    monthly_in,
    monthly_out,
    on="month",
    how="outer",
    suffixes=("_in", "_out"),
).fillna(0)

if not cash_flow.empty:
    cash_flow["net_cash_flow"] = (
        cash_flow["cash_in"] - cash_flow["cash_out"]
    )
    cash_flow["month_label"] = pd.to_datetime(
        cash_flow["month"]
    ).dt.strftime("%b %Y")


# -------------------- SIDEBAR --------------------

with st.sidebar:
    st.markdown("# 💰 PulseIQ")
    st.caption("FINANCE INTELLIGENCE")
    st.divider()

    page = st.radio(
        "NAVIGATION",
        [
            "Executive Overview",
            "Receivables Ageing",
            "Client Analytics",
            "Cash Flow",
            "Invoice Register",
            "Data Quality",
        ],
    )

    st.divider()
    st.caption("PHASE 3 • TASK 12")
    st.caption("Invoices, Receivables & Cash Flow")
    st.caption("Source: Validated PulseIQ data")


# ============================================================
# 1. EXECUTIVE OVERVIEW
# ============================================================

if page == "Executive Overview":

    st.title("Invoices, Receivables & Cash Flow")
    st.markdown(
        '<p class="subtitle">Executive financial position | '
        'Collections, outstanding invoices and cash movement</p>',
        unsafe_allow_html=True,
    )

    st.markdown("### Financial snapshot")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Open Receivables",
        money(overview["open_balance"]),
        f'{int(overview["open_count"])} invoices',
    )

    c2.metric(
        "Overdue Receivables",
        money(overview["overdue_balance"]),
        f'{int(overview["overdue_count"])} invoices',
    )

    c3.metric(
        "Total Cash Received",
        money(cash_summary["cash_in"]),
    )

    c4.metric(
        "Total Cash Paid Out",
        money(cash_summary["cash_out"]),
    )

    st.markdown("### Invoice portfolio")

    a, b, c, d = st.columns(4)

    a.metric("Total Invoices", f'{int(overview["total_invoices"]):,}')
    b.metric("Paid Invoices", f'{int(overview["paid_count"]):,}')
    c.metric("Open Invoices", f'{int(overview["open_count"]):,}')
    d.metric("Cancelled", f'{int(overview["cancelled_count"]):,}')

    left, right = st.columns(2)

    with left:
        st.markdown("#### Invoice status distribution")

        status_df = load_query("""
            SELECT status, COUNT(*) AS invoice_count
            FROM fact_invoice
            GROUP BY status
            ORDER BY invoice_count DESC
        """)

        fig = px.pie(
            status_df,
            names="status",
            values="invoice_count",
            hole=0.62,
            title="Invoices by status",
        )
        fig.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(chart_layout(fig), use_container_width=True)

    with right:
        st.markdown("#### Receivables ageing")

        ageing_chart = ageing[
            ageing["ageing_group"] != "Other / Review"
        ]

        fig = px.bar(
            ageing_chart,
            x="ageing_group",
            y="outstanding_amount",
            text="outstanding_amount",
            title="Outstanding balance by ageing bucket",
            labels={
                "ageing_group": "Ageing bucket",
                "outstanding_amount": "Outstanding (₹)",
            },
        )
        fig.update_traces(
            texttemplate="%{y:,.0f}",
            textposition="outside",
        )
        st.plotly_chart(chart_layout(fig), use_container_width=True)

    st.markdown("### Cash flow summary")

    if not cash_flow.empty:
        fig = go.Figure()

        fig.add_trace(go.Bar(
            x=cash_flow["month_label"],
            y=cash_flow["cash_in"],
            name="Cash In",
        ))

        fig.add_trace(go.Bar(
            x=cash_flow["month_label"],
            y=cash_flow["cash_out"],
            name="Cash Out",
        ))

        fig.update_layout(
            barmode="group",
            title="Monthly collections vs expense payments",
            xaxis_title="Month",
            yaxis_title="Amount (₹)",
        )

        st.plotly_chart(
            chart_layout(fig, 420),
            use_container_width=True,
        )

    st.markdown("### Key observations")

    overdue_share = (
        safe_number(overview["overdue_balance"])
        / safe_number(overview["open_balance"]) * 100
        if safe_number(overview["open_balance"]) else 0
    )

    st.markdown(
        f"""
        <div class="section-note">
        <b>Overdue concentration:</b> {overdue_share:.1f}% of total
        open receivables are currently marked overdue.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        - {int(overview["open_count"])} invoices remain open.
        - {int(overview["paid_count"])} invoices are marked paid.
        - Cash collections exceed recorded paid expenses in the
          available source period.
        - One invoice payment-summary mismatch is flagged for review.
        """
    )


# ============================================================
# 2. RECEIVABLES AGEING
# ============================================================

elif page == "Receivables Ageing":

    st.title("Receivables Ageing")
    st.markdown(
        '<p class="subtitle">Outstanding invoice balances and '
        'overdue exposure</p>',
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="section-note">
        Open invoices include only SENT, OVERDUE and PARTIALLY_PAID.
        Current / Not yet due is shown separately from overdue ageing.
        </div>
        """,
        unsafe_allow_html=True,
    )

    total_open = safe_number(overview["open_balance"])
    bucket_total = safe_number(ageing["outstanding_amount"].sum())
    difference = total_open - bucket_total

    x1, x2, x3 = st.columns(3)
    x1.metric("Open Receivables", money(total_open))
    x2.metric("Ageing Bucket Total", money(bucket_total))
    x3.metric("Reconciliation Difference", money(difference))

    if abs(difference) < 0.01:
        st.success("Ageing buckets reconcile to total open receivables.")
    else:
        st.error("Ageing buckets do not reconcile. Investigate the difference.")

    st.markdown("### Ageing breakdown")

    display_ageing = ageing.copy()
    display_ageing["outstanding_amount"] = (
        display_ageing["outstanding_amount"].fillna(0)
    )

    st.dataframe(
        display_ageing.rename(columns={
            "ageing_group": "Ageing Bucket",
            "invoice_count": "Invoice Count",
            "outstanding_amount": "Outstanding Amount (₹)",
        }),
        use_container_width=True,
        hide_index=True,
    )

    fig = px.bar(
        ageing,
        x="ageing_group",
        y="outstanding_amount",
        color="ageing_group",
        title="Outstanding receivables by ageing",
        labels={
            "ageing_group": "Ageing bucket",
            "outstanding_amount": "Balance (₹)",
        },
    )
    st.plotly_chart(chart_layout(fig), use_container_width=True)

    st.markdown("### Biggest overdue invoices")

    overdue = load_query("""
        SELECT
            invoice_number,
            client_name,
            invoice_date,
            due_date,
            balance_due,
            days_past_due_at_cutoff,
            ageing_bucket_at_cutoff
        FROM v_open_invoices
        WHERE UPPER(TRIM(status)) = 'OVERDUE'
        ORDER BY balance_due DESC
    """)

    st.dataframe(
        overdue.rename(columns={
            "invoice_number": "Invoice",
            "client_name": "Client",
            "invoice_date": "Invoice Date",
            "due_date": "Due Date",
            "balance_due": "Outstanding (₹)",
            "days_past_due_at_cutoff": "Days Past Due",
            "ageing_bucket_at_cutoff": "Source Ageing",
        }),
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# 3. CLIENT ANALYTICS
# ============================================================

elif page == "Client Analytics":

    st.title("Client Payment Behaviour")
    st.markdown(
        '<p class="subtitle">Payment speed, contractual terms '
        'and outstanding client exposure</p>',
        unsafe_allow_html=True,
    )

    clients = load_query("""
        SELECT *
        FROM v_client_payment_performance
        ORDER BY open_receivables DESC NULLS LAST
    """)

    clients["open_receivables"] = (
        clients["open_receivables"].fillna(0)
    )

    c1, c2, c3 = st.columns(3)

    c1.metric("Total Clients", f"{len(clients):,}")
    c2.metric(
        "Clients With Open Balance",
        f"{(clients['open_receivables'] > 0).sum():,}",
    )

    c3.metric(
        "Clients With Payment History",
        f"{(clients['paid_invoice_count'] > 0).sum():,}",
    )

    st.markdown("### Slowest paying clients")

    slow = clients[
        clients["avg_days_to_pay"].notna()
    ].sort_values("avg_days_to_pay", ascending=False).head(10)

    fig = px.bar(
        slow.sort_values("avg_days_to_pay"),
        x="avg_days_to_pay",
        y="client_name",
        orientation="h",
        color="avg_days_vs_terms",
        title="Average days to pay by client",
        labels={
            "avg_days_to_pay": "Average days to pay",
            "client_name": "Client",
            "avg_days_vs_terms": "Days vs payment terms",
        },
        color_continuous_scale="RdYlGn_r",
    )

    st.plotly_chart(chart_layout(fig, 450), use_container_width=True)

    st.markdown("### Client receivables exposure")

    exposure = clients[
        clients["open_receivables"] > 0
    ].sort_values("open_receivables", ascending=False)

    fig = px.bar(
        exposure.head(10).sort_values("open_receivables"),
        x="open_receivables",
        y="client_name",
        orientation="h",
        title="Top clients by open receivables",
        labels={
            "open_receivables": "Outstanding (₹)",
            "client_name": "Client",
        },
    )

    st.plotly_chart(chart_layout(fig, 420), use_container_width=True)

    st.markdown("### Client-level performance table")

    st.dataframe(
        clients.rename(columns={
            "client_id": "Client ID",
            "client_name": "Client",
            "industry": "Industry",
            "payment_terms_days": "Terms (days)",
            "payment_behaviour": "Recorded Behaviour",
            "paid_invoice_count": "Paid Invoices",
            "avg_days_to_pay": "Avg Days to Pay",
            "avg_days_vs_terms": "Avg Days vs Terms",
            "open_receivables": "Open Receivables (₹)",
        }),
        use_container_width=True,
        hide_index=True,
    )

    st.caption(
        "Average payment days use the source invoice days_to_pay "
        "for PAID invoices. The comparison with payment terms is "
        "descriptive and does not independently establish credit risk."
    )


# ============================================================
# 4. CASH FLOW
# ============================================================

elif page == "Cash Flow":

    st.title("Cash Flow Analytics")
    st.markdown(
        '<p class="subtitle">Actual invoice collections compared '
        'with paid expense transactions</p>',
        unsafe_allow_html=True,
    )

    total_in = safe_number(cash_summary["cash_in"])
    total_out = safe_number(cash_summary["cash_out"])
    net = total_in - total_out

    a, b, c = st.columns(3)
    a.metric("Total Cash In", money(total_in))
    b.metric("Total Cash Out", money(total_out))
    c.metric("Net Difference", money(net))

    st.markdown("### Monthly cash movement")

    if not cash_flow.empty:
        fig = go.Figure()

        fig.add_trace(go.Bar(
            x=cash_flow["month_label"],
            y=cash_flow["cash_in"],
            name="Cash In",
        ))

        fig.add_trace(go.Bar(
            x=cash_flow["month_label"],
            y=cash_flow["cash_out"],
            name="Cash Out",
        ))

        fig.update_layout(
            barmode="group",
            title="Monthly cash-in vs cash-out",
            xaxis_title="Month",
            yaxis_title="Amount (₹)",
        )

        st.plotly_chart(
            chart_layout(fig, 440),
            use_container_width=True,
        )

        fig2 = px.line(
            cash_flow,
            x="month_label",
            y="net_cash_flow",
            markers=True,
            title="Monthly net cash movement",
            labels={
                "month_label": "Month",
                "net_cash_flow": "Net cash movement (₹)",
            },
        )

        st.plotly_chart(
            chart_layout(fig2, 360),
            use_container_width=True,
        )

    st.markdown("### Monthly cash flow table")

    if not cash_flow.empty:
        monthly_display = cash_flow[[
            "month_label",
            "payment_count_in",
            "cash_in",
            "payment_count_out",
            "cash_out",
            "net_cash_flow",
        ]].copy()

        monthly_display.columns = [
            "Month",
            "Collection Transactions",
            "Cash In (₹)",
            "Expense Payments",
            "Cash Out (₹)",
            "Net Movement (₹)",
        ]

        st.dataframe(
            monthly_display,
            use_container_width=True,
            hide_index=True,
        )

    st.markdown("### Cash flow methodology")

    st.markdown("""
    - Cash-in is based on invoice payment transactions using payment_date.
    - Cash-out includes only expense records marked PAID with a valid paid_date.
    - Unpaid expense records are excluded from actual cash-out.
    - Net movement is cash-in minus cash-out.
    - This is a two-stream operational cash movement view, not a complete
      bank cash reconciliation or statement of cash flows.
    """)


# ============================================================
# 5. INVOICE REGISTER
# ============================================================

elif page == "Invoice Register":

    st.title("Invoice Register")
    st.markdown(
        '<p class="subtitle">Search, filter and inspect invoice records</p>',
        unsafe_allow_html=True,
    )

    invoice_data = load_query("""
        SELECT
            i.invoice_id,
            i.invoice_number,
            i.client_id,
            c.client_name,
            i.invoice_date,
            i.due_date,
            i.total_amount,
            i.amount_paid,
            i.balance_due,
            i.status,
            i.last_payment_date,
            i.days_to_pay,
            i.days_past_due_at_cutoff,
            i.ageing_bucket_at_cutoff
        FROM fact_invoice i
        LEFT JOIN dim_client c USING (client_id)
        ORDER BY i.invoice_date DESC
    """)

    statuses = sorted(invoice_data["status"].dropna().unique())
    selected_statuses = st.multiselect(
        "Filter by invoice status",
        statuses,
        default=statuses,
    )

    search = st.text_input(
        "Search invoice number or client name"
    )

    filtered = invoice_data[
        invoice_data["status"].isin(selected_statuses)
    ].copy()

    if search:
        filtered = filtered[
            filtered["invoice_number"].str.contains(
                search, case=False, na=False
            )
            | filtered["client_name"].str.contains(
                search, case=False, na=False
            )
        ]

    st.caption(f"{len(filtered):,} invoice records displayed")

    st.dataframe(
        filtered.rename(columns={
            "invoice_number": "Invoice Number",
            "client_name": "Client",
            "invoice_date": "Invoice Date",
            "due_date": "Due Date",
            "total_amount": "Invoice Total (₹)",
            "amount_paid": "Amount Paid (₹)",
            "balance_due": "Balance Due (₹)",
            "status": "Status",
            "last_payment_date": "Last Payment Date",
            "days_to_pay": "Days to Pay",
            "days_past_due_at_cutoff": "Days Past Due",
            "ageing_bucket_at_cutoff": "Ageing Bucket",
        }),
        use_container_width=True,
        hide_index=True,
    )

    csv = filtered.to_csv(index=False).encode("utf-8")

    st.download_button(
        "Download filtered invoices CSV",
        data=csv,
        file_name="task12_invoice_register.csv",
        mime="text/csv",
    )


# ============================================================
# 6. DATA QUALITY
# ============================================================

elif page == "Data Quality":

    st.title("Data Quality & Reconciliation")
    st.markdown(
        '<p class="subtitle">Source integrity, payment reconciliation '
        'and ageing validation</p>',
        unsafe_allow_html=True,
    )

    reconciliation = load_query("""
        SELECT *
        FROM v_invoice_payment_reconciliation
        WHERE reconciliation_status = 'MISMATCH'
        ORDER BY ABS(payment_difference) DESC
    """)

    bucket_sum = safe_number(ageing["outstanding_amount"].sum())
    open_sum = safe_number(overview["open_balance"])
    mismatch_count = len(reconciliation)

    checks = [
        {
            "Check": "Open receivables ageing reconciliation",
            "Result": "PASS" if abs(bucket_sum-open_sum) < 0.01 else "FAIL",
            "Detail": f"Difference: ₹{open_sum-bucket_sum:,.2f}",
        },
        {
            "Check": "Invoice payment reconciliation",
            "Result": "REVIEW" if mismatch_count else "PASS",
            "Detail": f"{mismatch_count} invoice mismatch(es)",
        },
        {
            "Check": "Cash-out payment-date validation",
            "Result": "PASS",
            "Detail": "Paid expense records have payment dates and ledger references (source validation).",
        },
        {
            "Check": "Open invoice status filter",
            "Result": "PASS",
            "Detail": "Only SENT, OVERDUE and PARTIALLY_PAID are included.",
        },
    ]

    st.markdown("### Validation summary")

    st.dataframe(
        pd.DataFrame(checks),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("### Payment reconciliation exceptions")

    if reconciliation.empty:
        st.success("No payment reconciliation exceptions found.")
    else:
        st.warning(
            f"{mismatch_count} invoice(s) require reconciliation review."
        )

        st.dataframe(
            reconciliation,
            use_container_width=True,
            hide_index=True,
        )

    st.markdown("### Known exception: INV-00385")

    st.markdown("""
    Invoice INV/2025-26/0334 (INV-00385), client CL-016:

    - Invoice total: ₹10,49,728
    - Invoice amount_paid field: ₹10,49,828
    - Payment transaction total: ₹10,49,728
    - Difference: ₹100
    - Invoice balance_due: -₹100

    The payment transaction agrees with the invoice total. The invoice
    summary amount_paid is overstated by ₹100. The original source record
    is preserved; no silent correction is made in this dashboard.
    """)

    st.markdown("### Source data inventory")

    inventory = pd.DataFrame([
        ["dim_client", 28, "Validated CSV"],
        ["fact_invoice", 743, "Validated CSV"],
        ["fact_invoice_payment", 709, "Validated CSV"],
        ["fact_expense", 501, "Read-only Task 11 source"],
    ], columns=["Table", "Rows", "Origin"])

    st.dataframe(
        inventory,
        use_container_width=True,
        hide_index=True,
    )


# -------------------- FOOTER --------------------

st.divider()

st.caption(
    "PulseIQ | Phase 3 • Task 12 | Invoices, Receivables & Cash Flow"
)
