from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

OUT = Path(__file__).resolve().parent
prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)

NAVY = RGBColor(24, 43, 71)
BLUE = RGBColor(48, 105, 165)
GREY = RGBColor(90, 100, 115)
WHITE = RGBColor(255, 255, 255)

slides = [
    ("PulseIQ | Board Review",
     "September 2026 executive snapshot",
     "Headcount 440 | Attrition 0.70% | Attendance 95.18% | Payroll ₹5.50 Cr | Revenue ₹8.03 Cr | Net profit ₹1.50 Cr",
     "September KPI snapshot (₹ Cr for financial measures)",
     ["Payroll", "Revenue", "Net profit"], [5.50, 8.03, 1.50],
     "Recommendation: maintain workforce controls while reviewing the September cost and profitability movement.",
     "Source: Task 17 company_kpis.csv; reporting month 2026-09."),
    ("1 | People and workforce health",
     "Workforce indicators were within their stated targets in September.",
     "Headcount was 440. Monthly attrition was 0.70% against a 1.00% target; attendance was 95.18% against a 94.00% target.",
     "Actual versus target (%)",
     ["Attrition actual", "Attrition target", "Attendance actual", "Attendance target"],
     [0.70, 1.00, 95.18, 94.00],
     "Recommendation: sustain attendance practices and monitor attrition monthly; do not infer causation from one month.",
     "Source: Task 17 company_kpis.csv, September 2026."),
    ("2 | Payroll cost and profitability",
     "September payroll increased while revenue and net profit were lower than August.",
     "Payroll rose from ₹4.89 Cr to ₹5.50 Cr; revenue moved from ₹8.15 Cr to ₹8.03 Cr; net profit moved from ₹2.21 Cr to ₹1.50 Cr. This is a signal to investigate, not proof of cause.",
     "August versus September 2026 (₹ Cr)",
     ["Payroll Aug", "Payroll Sep", "Revenue Aug", "Revenue Sep", "Net profit Aug", "Net profit Sep"],
     [4.889, 5.501, 8.146, 8.027, 2.213, 1.499],
     "Recommendation: investigate department-level payroll drivers, overtime, staffing changes and ledger movements before approving cost actions.",
     "Source: Task 17 company_kpis.csv. Rounded to 3 decimals."),
    ("3 | Payroll anomaly exposure",
     "The anomaly workflow quantified ₹3.14 Cr of flagged exposure.",
     "Task 14 verification reports ₹31,421,239.07 across 184 quantified anomaly records. This is flagged exposure, not confirmed loss or fraud.",
     "Anomaly counts by selected reason",
     ["Statistical outlier", "Pattern shift", "No attendance", "Long unpaid absence"],
     [145, 125, 50, 43],
     "Recommendation: prioritize review by amount, reason and supporting payroll evidence; resolve flags before treating them as losses.",
     "Source: Task 14 verification_results.csv and anomaly_exposure_by_type.csv."),
    ("4 | Receivables ageing",
     "Open receivables total ₹13.94 Cr; ₹30.36 lakh is over 90 days.",
     "₹11.23 Cr is current/not yet due. The 90+ day balance is ₹3,036,258 across two invoices.",
     "Open receivables by ageing bucket (₹ Cr)",
     ["Current / not due", "0–30 days", "61–90 days", "90+ days"],
     [11.228, 2.213, 0.194, 0.304],
     "Recommendation: focus collection follow-up on overdue balances and validate disputed invoices before escalation.",
     "Source: Task 12 verification/ageing_reconciliation.csv. Categories as supplied."),
    ("5 | Cash movement",
     "September payment-record cash-in exceeded cash-out by ₹7.54 Cr.",
     "September cash-in was ₹8.43 Cr; cash-out was ₹0.89 Cr; net payment-record movement was ₹7.54 Cr.",
     "September 2026 payment records (₹ Cr)",
     ["Cash-in", "Cash-out", "Net movement"],
     [8.433, 0.890, 7.543],
     "Recommendation: monitor collections and payment timing; do not present this payment-record view as a full cash-flow statement.",
     "Source: Task 12 verification/monthly_cash_flow.csv."),
    ("6 | Department productivity",
     "September task completion differed across the departments shown.",
     "D03 recorded 91.40% completion and D08 recorded 79.31%. D00 and D10 have suppressed/missing productivity values and are not ranked.",
     "Task completion rate (%)",
     ["D03", "D08"], [91.40, 79.31],
     "Recommendation: review workflow blockers and task mix with department leads; compare like-for-like workload before setting targets.",
     "Source: Task 13 evidence/department_month_comparison.csv, September 2026."),
    ("7 | Reconciliation and data quality",
     "Most core reconciliations matched, but attendance and late-arrival exceptions remain.",
     "Task 13: payroll cost, gross pay, overtime pay and paid employees matched 198/198; attendance matched 195/198; late arrivals matched 196/198; productivity matched 162/162.",
     "Reconciliation match rate (%)",
     ["Payroll cost", "Attendance", "Late arrivals", "Productivity"],
     [100.00, 98.48, 98.99, 100.00],
     "Recommendation: retain the three attendance and two late-arrival variances in the handover log and investigate before using them for operational decisions.",
     "Source: Task 13 evidence/task13_reconciliation_summary.csv."),
    ("8 | Decisions, limitations and next steps",
     "Prioritize controlled investigation over premature intervention.",
     "43 employees are in the high attrition-risk band. Forecast accuracy is not yet measurable because all forecast months are future periods. Invoice INV-00385 has a ₹100 reconciliation difference.",
     "Attrition risk bands (employees)",
     ["High", "Medium", "Low"], [43, 86, 301],
     "Board asks: review payroll drivers; assign owners for aged receivables; resolve reconciliation exceptions. Do not yet recommend individual retention action from risk scores alone—the predictive signal needs outcome validation.",
     "Sources: Task 14 attrition_risk_band_summary.csv and forecast_accuracy_status.csv; Task 12 payment_reconciliation.csv.")
]

def add_text(slide, text, x, y, w, h, size, color=NAVY, bold=False):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = text
    p.font.name = "Aptos"
    p.font.size = Pt(size)
    p.font.bold = bold
    p.font.color.rgb = color
    return box

for idx, item in enumerate(slides):
    title, finding, detail, chart_title, cats, vals, rec, source = item
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = WHITE

    # Header band
    band = slide.shapes.add_shape(1, Inches(0), Inches(0), Inches(13.333), Inches(0.72))
    band.fill.solid()
    band.fill.fore_color.rgb = NAVY
    band.line.fill.background()
    add_text(slide, title, 0.55, 0.12, 12.2, 0.45, 22, WHITE, True)

    add_text(slide, finding, 0.65, 1.02, 12.0, 0.55, 20, NAVY, True)
    add_text(slide, detail, 0.68, 1.66, 11.9, 0.85, 14, GREY)

    chart_data = CategoryChartData()
    chart_data.categories = cats
    chart_data.add_series("Value", vals)
    chart = slide.shapes.add_chart(
        XL_CHART_TYPE.COLUMN_CLUSTERED,
        Inches(1.0), Inches(2.55), Inches(11.3), Inches(3.25),
        chart_data
    ).chart
    chart.has_legend = False
    chart.has_title = True
    chart.chart_title.text_frame.text = chart_title
    chart.chart_title.text_frame.paragraphs[0].font.size = Pt(13)
    chart.chart_title.text_frame.paragraphs[0].font.bold = True
    chart.has_plot = True
    chart.value_axis.has_major_gridlines = True
    chart.value_axis.tick_labels.font.size = Pt(10)
    chart.category_axis.tick_labels.font.size = Pt(10)
    plot = chart.plots[0]
    plot.has_data_labels = True
    plot.data_labels.font.size = Pt(10)
    plot.data_labels.number_format = '0.00'
    plot.gap_width = 65

    # Recommendation footer
    rec_box = slide.shapes.add_shape(1, Inches(0.65), Inches(6.00), Inches(12.0), Inches(0.78))
    rec_box.fill.solid()
    rec_box.fill.fore_color.rgb = RGBColor(238, 243, 249)
    rec_box.line.color.rgb = RGBColor(215, 224, 235)
    tf = rec_box.text_frame
    tf.word_wrap = True
    tf.margin_left = Inches(0.18)
    tf.margin_right = Inches(0.18)
    tf.margin_top = Inches(0.10)
    p = tf.paragraphs[0]
    p.text = rec
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = NAVY

    add_text(slide, source, 0.68, 6.92, 11.8, 0.25, 8, GREY)
    add_text(slide, f"PulseIQ | Board pack | {idx+1}/9", 10.8, 7.18, 2.0, 0.18, 8, GREY)

out = OUT / "PulseIQ_Board_Presentation_v1.0.0.pptx"
prs.save(out)
print(f"CREATED: {out}")
print(f"SLIDES: {len(prs.slides)}")
