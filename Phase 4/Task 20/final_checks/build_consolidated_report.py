from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether
)
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent / "PulseIQ_Consolidated_Report_DRAFT.pdf"
TASK20 = ROOT / "Phase 4" / "Task 20"

NAVY = colors.HexColor("#17324D")
BLUE = colors.HexColor("#246B9E")
PALE = colors.HexColor("#EAF1F7")
LIGHT = colors.HexColor("#F4F6F8")
GREY = colors.HexColor("#59636E")
GREEN = colors.HexColor("#287A55")
AMBER = colors.HexColor("#A66A16")
RED = colors.HexColor("#A33A3A")

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(
    name="CoverTitle", parent=styles["Title"], fontName="Helvetica-Bold",
    fontSize=27, leading=33, textColor=NAVY, alignment=TA_CENTER,
    spaceAfter=12
))
styles.add(ParagraphStyle(
    name="CoverSub", parent=styles["Normal"], fontSize=12, leading=18,
    textColor=GREY, alignment=TA_CENTER
))
styles.add(ParagraphStyle(
    name="Section", parent=styles["Heading1"], fontSize=17, leading=21,
    textColor=NAVY, spaceBefore=8, spaceAfter=9
))
styles.add(ParagraphStyle(
    name="SubSection", parent=styles["Heading2"], fontSize=11.5,
    leading=15, textColor=BLUE, spaceBefore=8, spaceAfter=5
))
styles.add(ParagraphStyle(
    name="BodyCustom", parent=styles["BodyText"], fontSize=9,
    leading=13, spaceAfter=6, textColor=colors.HexColor("#263238")
))
styles.add(ParagraphStyle(
    name="SmallCustom", parent=styles["BodyText"], fontSize=7.5,
    leading=10, textColor=GREY
))
styles.add(ParagraphStyle(
    name="Callout", parent=styles["BodyText"], fontSize=9.2,
    leading=14, textColor=NAVY, backColor=PALE,
    borderPadding=8, spaceBefore=5, spaceAfter=9
))
styles.add(ParagraphStyle(
    name="TableHead", parent=styles["BodyText"], fontSize=8,
    leading=10, textColor=colors.white
))
styles.add(ParagraphStyle(
    name="TableBody", parent=styles["BodyText"], fontSize=7.6,
    leading=10, textColor=colors.HexColor("#263238")
))

def P(text, style="BodyCustom"):
    return Paragraph(text, styles[style])

def make_table(rows, widths, header=True):
    converted = []
    for r, row in enumerate(rows):
        converted.append([
            Paragraph(str(cell), styles["TableHead"] if header and r == 0
                      else styles["TableBody"])
            for cell in row
        ])
    t = Table(converted, colWidths=widths, repeatRows=1 if header else 0,
              hAlign="LEFT")
    commands = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CFD7DF")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    if header:
        commands += [
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.white, LIGHT]),
        ]
    t.setStyle(TableStyle(commands))
    return t

def footer(canvas, doc):
    canvas.saveState()
    w, h = A4
    canvas.setStrokeColor(colors.HexColor("#D7DEE5"))
    canvas.line(18*mm, 14*mm, w-18*mm, 14*mm)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(GREY)
    canvas.drawString(18*mm, 9*mm, "PulseIQ | Consolidated Project Report | Final review copy")
    canvas.drawRightString(w-18*mm, 9*mm, f"Page {doc.page}")
    canvas.restoreState()

story = []

# COVER
story += [
    Spacer(1, 28*mm),
    P("PULSEIQ", "CoverTitle"),
    P("Data Analytics Project<br/>Consolidated Report", "CoverTitle"),
    Spacer(1, 5*mm),
    P("Phases 1-4 | Tasks 1-20", "CoverSub"),
    Spacer(1, 8*mm),
    P("Executive analytics, financial insight, workforce intelligence, governed metrics and API delivery", "CoverSub"),
    Spacer(1, 22*mm),
    make_table([
        ["Project information", "Details"],
        ["Repository", '<link href="https://github.com/harshsagar073/pulseiq" color="#246B9E">github.com/harshsagar073/pulseiq</link>'],
        ["Branch", "main"],
        ["Reporting snapshot", "September 2026, where monthly KPI data is referenced"],
        ["Prepared", "21 November 2026"],
        ["Release state", "Final review copy - demo and AI-assisted Final Challenge evidence included"],
    ], [45*mm, 115*mm]),
    Spacer(1, 18*mm),
    P("Prepared as a consolidated handover summary. Values are presented with their relevant period, grain and known limitations; different task outputs are not assumed to share identical source scopes.", "Callout"),
    PageBreak()
]

# EXECUTIVE SUMMARY
story += [
    P("1. Executive Summary", "Section"),
    P("PulseIQ is a multi-phase analytics project that develops a path from source-data preparation and governed metrics to financial and workforce analysis, role-oriented exploration, an API and an executive board pack."),
    P("The project brings together data quality checks, KPI definitions, financial analysis, department comparisons, anomaly signals and API-based access. The September 2026 executive snapshot provides a common point of reference for selected company KPIs."),
    make_table([
        ["September 2026 KPI", "Reported value", "Context"],
        ["Headcount", "440", "Task 17 company KPI export"],
        ["Monthly attrition", "0.70%", "Target 1.00%"],
        ["Payroll cost", "INR 55.01 million", "Approximately INR 5.50 Cr"],
        ["Attendance rate", "95.18%", "Target 94.00%"],
        ["Revenue", "INR 80.27 million", "Approximately INR 8.03 Cr"],
        ["Net profit", "INR 14.99 million", "Approximately INR 1.50 Cr"],
        ["Operating margin", "18.67%", "Task 17 company KPI export"],
    ], [43*mm, 42*mm, 75*mm]),
    Spacer(1, 5*mm),
    P("<b>Management takeaway:</b> September payroll cost rose while revenue and net profit declined compared with August. This is a signal to investigate workforce mix, hiring, overtime, department-level cost and business activity; the comparison alone does not establish causation.", "Callout"),
    P("2. Project Delivery Across Four Phases", "Section"),
    make_table([
        ["Phase", "Scope", "Main deliverables"],
        ["Phase 1 - Foundation", "Tasks 1-5", "Source data loading, data preparation, DuckDB foundation and governed metric layer."],
        ["Phase 2 - Analytics", "Tasks 6-10", "Analytical workflows, payroll analysis and reconciliation, dashboards and validation."],
        ["Phase 3 - Business intelligence", "Tasks 11-15", "P&L and expense analysis, receivables and cash flow, department comparison, AI signals and executive scorecard."],
        ["Phase 4 - Product and handover", "Tasks 16-20", "Monthly reporting, public KPI export, role-oriented exploration, metrics API and lineage, board pack and final handover."],
    ], [35*mm, 25*mm, 100*mm]),
    PageBreak()
]

# FINANCIAL INSIGHTS
story += [
    P("3. Key Business Findings", "Section"),
    P("3.1 Payroll cost and profitability", "SubSection"),
    make_table([
        ["KPI", "August 2026", "September 2026"],
        ["Payroll cost", "INR 48.89 million", "INR 55.01 million"],
        ["Revenue", "INR 81.46 million", "INR 80.27 million"],
        ["Net profit", "INR 22.13 million", "INR 14.99 million"],
        ["Operating margin", "27.16%", "18.67%"],
        ["Headcount", "426", "440"],
    ], [55*mm, 65*mm, 65*mm]),
    P("Payroll cost increased by approximately 12.5% month over month, while headcount increased by 14 (about 3.3%). Revenue decreased by approximately 1.5%, net profit decreased by approximately 32.3%, and operating margin fell by 8.49 percentage points."),
    P("<b>Recommendation:</b> Review payroll growth by department and employee mix, overtime, hiring dates and cost per head. Compare cost movements with revenue-generating activity before attributing the change to any one factor."),
    P("3.2 P&L and expense analytics", "SubSection"),
    P("Task 11's tie-out summary reports total revenue of INR 1,260,930,052.00, total expenses of INR 1,036,264,914.42, net profit of INR 224,665,137.58 and profit margin of 17.82% for its analysed period. The source summary covers 6,784 ledger rows, 47 accounts, 501 expense bills and 30 vendors."),
    P("<b>Scope caution:</b> These are Task 11 analysed-period totals. They must not be presented as September 2026-only figures or directly substituted for Task 17's monthly snapshot."),
    P("3.3 Receivables and cash movement", "SubSection"),
    make_table([
        ["Receivables ageing category", "Invoices", "Open balance"],
        ["Current / not yet due", "49", "INR 112,283,412"],
        ["0-30 days", "10", "INR 22,133,626"],
        ["61-90 days", "1", "INR 1,940,982"],
        ["90+ days", "2", "INR 3,036,258"],
        ["Total open balance", "62", "INR 139,394,278"],
    ], [65*mm, 30*mm, 90*mm]),
    P("The 90+ day bucket is INR 3.04 million (about INR 30.36 lakh). Task 12's September payment-record cash movement reports cash-in of INR 84,334,373.40, cash-out of INR 8,899,338.40 and net cash flow of INR 75,435,035.00."),
    P("<b>Recommendation:</b> Prioritise follow-up on overdue balances while maintaining collection discipline on the current bucket. Treat the cash movement as payment-record-based analysis, not a complete statutory cash flow statement."),
    PageBreak()
]

# PEOPLE + AI SIGNALS
story += [
    P("4. People, Teams and AI Signals", "Section"),
    P("4.1 Workforce and department comparison", "SubSection"),
    P("Task 13 provides a department-month comparison across 11 departments and 18 months, representing 198 department-month records. The later reconciliation summary reports 198/198 matches for employer cost, gross pay, overtime pay, employees paid, payroll overtime hours, headcount, hires and exits. Task productivity comparisons report 162/162 matches for tasks, tasks done, story points and task completion rate."),
    P("The same reconciliation summary records 196/198 matches for late arrivals and 195/198 matches for calculated attendance rate. These exceptions remain disclosed rather than being described as fully reconciled."),
    P("For September 2026, department task-completion examples include D03 at 91.40% and D08 at 79.31%. Groups with suppressed or blank productivity values should not be ranked or treated as zero."),
    P("<b>Recommendation:</b> Use department-level comparisons to target operational follow-up, while checking group size, metric definition and suppression rules before drawing conclusions."),
    P("4.2 Anomaly and risk signals", "SubSection"),
    P("Task 14 contains 405 anomaly records, 72 forecast records, 430 attrition-risk records and 891 historical headcount records. It identifies INR 31,421,239.07 (about INR 3.14 Cr) in quantified flagged exposure across 184 quantified anomaly records. A further 221 anomaly records are unquantified."),
    P("The attrition-risk summary contains 43 high-risk, 86 medium-risk and 301 low-risk records. The forecast horizon runs from October 2026 to March 2027, while historical actuals run from January 2020 to September 2026."),
    P("<b>Important interpretation:</b> Quantified flagged exposure is not confirmed loss, fraud or recoverable value. Forecast months are future relative to the historical actuals, so forecast accuracy cannot yet be evaluated against those months."),
    P("<b>Recommendation:</b> Treat anomalies as investigation leads. Validate source records and business context before taking action, and evaluate forecasts only after actual observations become available."),
    P("5. Governed Metrics API and Product Delivery", "Section"),
    P("Task 19 exposes five governed metrics through a FastAPI service: headcount, payroll cost, attendance rate, revenue and operating margin. The documented metric views are governed.m01_headcount, governed.m09_payroll_cost, governed.m13_attendance_rate, governed.m16_revenue and governed.m18_operating_margin."),
    make_table([
        ["API resource", "Purpose"],
        ["<link href='https://pulseiqmetricsapi-guest.blue.sola.inc/health' color='#246B9E'>/health</link>", "Health endpoint"],
        ["<link href='https://pulseiqmetricsapi-guest.blue.sola.inc/openapi.json' color='#246B9E'>/openapi.json</link>", "OpenAPI schema (JSON)"],
        ["<link href='https://pulseiqmetricsapi-guest.blue.sola.inc/api/v1/metrics' color='#246B9E'>/api/v1/metrics</link>", "Metrics catalogue"],
    ], [65*mm, 120*mm]),
    P("The Task 19 local verification script passed API health, metric catalogue and all five metric checks. The deployed Blue service is password-protected; evaluators require the viewing password to access it. The API's last_refresh value reflects the DuckDB file modification time, not a verified upstream source-ingestion timestamp."),
    P("Department-level metrics apply small-group suppression. Where the group is below the configured threshold, the metric value is returned as null with a suppression indicator. The lineage documentation also records that the original Task 4 raw-table loading method was not available for full documentation."),
    PageBreak()
]

# QA / RECOMMENDATIONS / LIMITATIONS
story += [
    P("6. Reconciliation and Quality Review", "Section"),
    make_table([
        ["Task", "Verification evidence", "Outcome / disclosed issue"],
        ["Task 13", "Department-month reconciliation summary", "198/198 matches for core payroll and workforce fields; 162/162 productivity matches; late arrivals 196/198 and attendance 195/198."],
        ["Task 14", "Verification results", "405 anomalies, 72 forecasts, 430 attrition-risk records, 891 historical actuals; 0 invalid forecast interval orderings."],
        ["Task 16", "Report verification", "7/7 checks passed; August and September 2026 PDFs generated; 11-department dimension available."],
        ["Task 17", "Export verification", "16/16 checks passed; 81 CSV rows; reporting cutoff 2026-09-01."],
        ["Task 18", "Role explorer verification", "27 checks passed; 0 failed checks."],
        ["Task 19", "API verification", "Local API health, catalogue and five metric checks passed."],
        ["Task 20", "Board pack and Final Challenge", "9-slide PowerPoint verified; AI-assisted Payroll Cost Drill-down completed with 16/16 automated checks passed."],
    ], [24*mm, 54*mm, 107*mm]),
    P("7. Known Exceptions and Limitations", "Section"),
    P("• Task 12 invoice INV-00385 has a INR 100 difference: the invoice amount paid is INR 1,049,828 against invoice total and transaction payment total of INR 1,049,728. The invoice balance is negative INR 100."),
    P("• Task 13 late-arrival reconciliation has 2 mismatches and calculated attendance reconciliation has 3 mismatches in the final summary."),
    P("• Task 14 quantified anomaly exposure is a flagged amount, not a confirmed financial loss. Pattern-shift, attendance and other unquantified alerts are not included in that amount."),
    P("• Task 14 forecasts extend from October 2026 to March 2027. Forecast accuracy has not yet been established against future actuals."),
    P("• Task 11 P&L totals cover its analysed period and are not a September-only monthly result."),
    P("• Task 12 cash movement is based on payment records and should not be described as a complete statutory cash flow statement."),
    P("• Task 19 API access is password-protected. Share the viewing password with authorised evaluators privately, never in the public repository or report."),
    P("• Task 19 freshness uses the database file modification time and does not independently confirm upstream data-feed freshness."),
    P("• Task 18 and Task 17 monthly figures can differ because they use different task-specific source and aggregation scopes. Do not combine their figures without reconciling definitions."),
    P("7.1 Final Challenge - Payroll Cost Drill-down", "SubSection"),
    P("A separate branch, final-challenge/payroll-cost-drilldown, contains an AI-assisted Streamlit dashboard for investigating monthly payroll cost movements and department contributions. The existing Task 9 application was used as a reference; it was not modified."),
    P("The dashboard reads Phase 1 Task 4 DuckDB data through a read-only connection. It retains the four Task 9 excluded payroll IDs and suppresses department groups with fewer than five employees."),
    make_table([
        ["September 2026 measure", "Final Challenge result"],
        ["Employees paid", "444"],
        ["Gross pay", "INR 54,788,660.03"],
        ["Net pay", "INR 48,089,678.30"],
        ["Employer cost", "INR 55,519,621.87"],
        ["Payroll records after exclusions", "7,340"],
        ["Monthly history", "18 months"],
        ["Automated verification", "16/16 checks passed"],
    ], [75*mm, 110*mm]),
    P("The Final Challenge payroll figures come from its Task 4 database scope and are not interchangeable with Task 17's company KPI export. The September employer-cost movement is an investigation signal, not proof of cause."),
    P("Evidence screenshots: Phase 4/Task 20/final_challenge/payroll_cost_drilldown/evidence/. Implementation and verification code: Phase 4/Task 20/final_challenge/payroll_cost_drilldown/."),
    P("<b>Assistance disclosure:</b> AI assistance was used to draft implementation and verification code. The dashboard was run and its results were checked against the project database. This work is represented as AI-assisted, not as an entirely independent implementation."),
    P("8. Management Recommendations", "Section"),
    P("1. Investigate the September payroll increase by department, headcount, employee mix and overtime; compare these drivers with revenue and margin movements."),
    P("2. Strengthen receivables follow-up, especially the 90+ day balances, and resolve the INR 100 invoice exception."),
    P("3. Review attendance and late-arrival reconciliation exceptions before using the affected figures for performance decisions."),
    P("4. Establish a review workflow for anomaly alerts that records validation, owner, resolution and financial impact separately."),
    P("5. Monitor forecasts against actual outcomes as future periods close, and document forecast error before using the model for planning."),
    PageBreak()
]

# HANDOVER
story += [
    P("9. Handover and Release Information", "Section"),
    P("Source repository: <link href='https://github.com/harshsagar073/pulseiq' color='#246B9E'>https://github.com/harshsagar073/pulseiq</link>"),
    P("Live API: <link href='https://pulseiqmetricsapi-guest.blue.sola.inc' color='#246B9E'>https://pulseiqmetricsapi-guest.blue.sola.inc</link>"),
    P("API documentation: <link href='https://pulseiqmetricsapi-guest.blue.sola.inc/openapi.json' color='#246B9E'>OpenAPI schema (JSON)</link>"),
    P("Metrics catalogue: <link href='https://pulseiqmetricsapi-guest.blue.sola.inc/api/v1/metrics' color='#246B9E'>Metrics catalogue</link>"),
    P("Board presentation: Phase 4/Task 20/board_presentation/PulseIQ_Board_Presentation_v1.0.0.pptx"),
    P("Monthly report PDFs: Phase 4/Task 16/reports/"),
    P("Task 20 release notes: Phase 4/Task 20/RELEASE_NOTES.md"),
    P("Demo agenda and recording link: Phase 4/Task 20/demo/DEMO_LINK_AND_AGENDA.md"),
    P("Final Challenge notes: Phase 4/Task 20/final_challenge/FINAL_CHALLENGE_NOTES.md"),
    Spacer(1, 4*mm),
    P("10. Remaining Final Handover Actions", "Section"),
    make_table([
        ["Action", "Current state"],
        ["Consolidated report", "Updated report generated; final visual review remains."],
        ["Recorded demo", "Available at the submitted link; duration 8 minutes 3 seconds, longer than the suggested five-minute target."],
        ["Final Challenge", "AI-assisted Payroll Cost Drill-down completed; 16/16 automated checks passed and evidence screenshots saved."],
        ["Release notes", "Updated to reflect delivered scope; final commit and release tag remain pending."],
        ["Final release tags", "Update phase-4 and create v1.0.0 only after final work is committed and verified."],
    ], [55*mm, 130*mm]),
    Spacer(1, 5*mm),
    P("<b>Release integrity note:</b> This report consolidates the recorded outputs and verification summaries for Tasks 1-20. The submitted demo and AI-assisted Final Challenge are included with their actual status and limitations. Final release tags must point to the reviewed commit containing the complete Phase 4 deliverables.", "Callout"),
    Spacer(1, 8*mm),
    P("End of report", "CoverSub"),
]

doc = SimpleDocTemplate(
    str(OUT), pagesize=A4,
    rightMargin=18*mm, leftMargin=18*mm,
    topMargin=17*mm, bottomMargin=20*mm,
    title="PulseIQ Consolidated Project Report",
    author="PulseIQ Project",
    subject="Phases 1-4, Tasks 1-20"
)
doc.build(story, onFirstPage=footer, onLaterPages=footer)

print("CREATED:", OUT)
print("SIZE:", OUT.stat().st_size, "bytes")
print("STATUS: GENERATED - final visual review required before release")
