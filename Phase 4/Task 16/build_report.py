from pathlib import Path
from datetime import date, datetime
import argparse
import calendar
import tempfile

import duckdb
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table,
    TableStyle, Image, PageBreak
)

TASK_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TASK_DIR.parents[1]
DEFAULT_DB = PROJECT_ROOT / "Phase 1" / "Task 4" / "pulseiq_task4.duckdb"
REPORT_DIR = TASK_DIR / "reports"


def fmt_number(value):
    return "N/A" if pd.isna(value) else f"{float(value):,.2f}"


def fmt_money(value):
    return "N/A" if pd.isna(value) else f"INR {float(value):,.2f}"


def fmt_percent(value):
    return "N/A" if pd.isna(value) else f"{float(value):.2f}%"


def read_df(con, sql, params=None):
    return con.execute(sql, params or []).df()


def monthly_total(con, view, date_column, month):
    if view in ("m04_monthly_attrition", "m13_attendance_rate"):
        expression = """
            SUM(metric_value * group_size) /
            NULLIF(SUM(group_size), 0)
        """
    else:
        expression = "SUM(metric_value)"

    result = read_df(
        con,
        f"""
        SELECT {expression} AS value
        FROM governed.{view}
        WHERE strftime({date_column}, '%Y-%m') = ?
          AND COALESCE(suppressed, FALSE) = FALSE
          AND metric_value IS NOT NULL
        """,
        [month],
    )
    value = result.iloc[0]["value"]
    return None if pd.isna(value) else float(value)


def financial_value(con, view, month, aggregation):
    result = read_df(
        con,
        f"""
        SELECT {aggregation}(metric_value) AS value
        FROM governed.{view}
        WHERE posting_period = ?
          AND COALESCE(suppressed, FALSE) = FALSE
        """,
        [month],
    )
    value = result.iloc[0]["value"]
    return None if pd.isna(value) else float(value)


def make_charts(con, month, folder):
    charts = {}

    payroll = read_df(
        con,
        """
        SELECT d.department_name, p.metric_value
        FROM governed.m09_payroll_cost p
        JOIN raw.dim_department d USING (department_id)
        WHERE strftime(p.period_end_date, '%Y-%m') = ?
          AND COALESCE(p.suppressed, FALSE) = FALSE
          AND COALESCE(d.is_leadership, 'N') <> 'Y'
        ORDER BY p.metric_value DESC
        """,
        [month],
    )

    headcount = read_df(
        con,
        """
        SELECT d.department_name, h.metric_value
        FROM governed.m01_headcount h
        JOIN raw.dim_department d USING (department_id)
        WHERE strftime(h.month_start_date, '%Y-%m') = ?
          AND COALESCE(h.suppressed, FALSE) = FALSE
          AND COALESCE(d.is_leadership, 'N') <> 'Y'
        ORDER BY h.metric_value DESC
        """,
        [month],
    )

    for key, data, title, xlabel in [
        ("payroll", payroll, "Department Payroll Cost", "INR"),
        ("headcount", headcount, "Department Headcount", "Employees"),
    ]:
        if not data.empty:
            fig, ax = plt.subplots(figsize=(9, 4.5))
            ax.barh(data["department_name"], data["metric_value"])
            ax.invert_yaxis()
            ax.set_title(f"{title} — {month}")
            ax.set_xlabel(xlabel)
            if key == "payroll":
                ax.ticklabel_format(style="plain", axis="x")
            fig.tight_layout()
            path = Path(folder) / f"{key}.png"
            fig.savefig(path, dpi=160)
            plt.close(fig)
            charts[key] = path

    trend = read_df(
        con,
        """
        WITH months AS (
            SELECT DISTINCT posting_period AS month
            FROM governed.m17_net_profit
            WHERE posting_period <= ?
            ORDER BY month DESC
            LIMIT 6
        ),
        revenue AS (
            SELECT posting_period AS month, SUM(metric_value) AS revenue
            FROM governed.m16_revenue
            WHERE posting_period <= ?
              AND COALESCE(suppressed, FALSE) = FALSE
            GROUP BY posting_period
        ),
        profit AS (
            SELECT posting_period AS month, MAX(metric_value) AS net_profit
            FROM governed.m17_net_profit
            WHERE posting_period <= ?
              AND COALESCE(suppressed, FALSE) = FALSE
            GROUP BY posting_period
        )
        SELECT m.month, r.revenue, p.net_profit
        FROM months m
        LEFT JOIN revenue r USING (month)
        LEFT JOIN profit p USING (month)
        ORDER BY m.month
        """,
        [month, month, month],
    )

    if not trend.empty:
        fig, ax = plt.subplots(figsize=(9, 4.5))
        ax.plot(trend["month"], trend["revenue"], marker="o", label="Revenue")
        ax.plot(trend["month"], trend["net_profit"], marker="o", label="Net profit")
        ax.set_title("Revenue and Net Profit — Recent Months")
        ax.set_ylabel("INR")
        ax.ticklabel_format(style="plain", axis="y")
        ax.tick_params(axis="x", rotation=30)
        ax.legend()
        fig.tight_layout()
        path = Path(folder) / "financial_trend.png"
        fig.savefig(path, dpi=160)
        plt.close(fig)
        charts["trend"] = path

    return charts


def build_report(month, db_path, output_path):
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    year, month_number = map(int, month.split("-"))
    first_day = date(year, month_number, 1)
    last_day = date(
        year, month_number,
        calendar.monthrange(year, month_number)[1]
    )

    con = duckdb.connect(str(db_path), read_only=True)

    try:
        kpis = {
            "Headcount": monthly_total(
                con, "m01_headcount", "month_start_date", month
            ),
            "Attrition": monthly_total(
                con, "m04_monthly_attrition", "month_start_date", month
            ),
            "Payroll": monthly_total(
                con, "m09_payroll_cost", "period_end_date", month
            ),
            "Attendance": monthly_total(
                con, "m13_attendance_rate", "period_end_date", month
            ),
            "Revenue": financial_value(
                con, "m16_revenue", month, "SUM"
            ),
            "Net profit": financial_value(
                con, "m17_net_profit", month, "MAX"
            ),
            "Operating margin": financial_value(
                con, "m18_operating_margin", month, "MAX"
            ),
        }

        missing = [name for name, value in kpis.items() if value is None]
        if missing:
            raise ValueError(
                f"Missing monthly data for {', '.join(missing)}. "
                "Choose a month with complete reporting data."
            )

        departments = read_df(
            con,
            """
            SELECT
                d.department_name,
                h.metric_value AS headcount,
                a.metric_value AS attrition,
                p.metric_value AS payroll,
                att.metric_value AS attendance
            FROM raw.dim_department d
            LEFT JOIN governed.m01_headcount h
              ON h.department_id = d.department_id
             AND strftime(h.month_start_date, '%Y-%m') = ?
             AND COALESCE(h.suppressed, FALSE) = FALSE
            LEFT JOIN governed.m04_monthly_attrition a
              ON a.department_id = d.department_id
             AND strftime(a.month_start_date, '%Y-%m') = ?
             AND COALESCE(a.suppressed, FALSE) = FALSE
            LEFT JOIN governed.m09_payroll_cost p
              ON p.department_id = d.department_id
             AND strftime(p.period_end_date, '%Y-%m') = ?
             AND COALESCE(p.suppressed, FALSE) = FALSE
            LEFT JOIN governed.m13_attendance_rate att
              ON att.department_id = d.department_id
             AND strftime(att.period_end_date, '%Y-%m') = ?
             AND COALESCE(att.suppressed, FALSE) = FALSE
            WHERE COALESCE(d.is_leadership, 'N') <> 'Y'
            ORDER BY d.department_name
            """,
            [month, month, month, month],
        )

        anomalies = read_df(
            con,
            """
            SELECT
                COUNT(*) AS flagged_count,
                COUNT(DISTINCT employee_id) AS affected_employees
            FROM raw.fact_anomaly
            WHERE strftime(period, '%Y-%m') = ?
              AND UPPER(flagged) = 'Y'
            """,
            [month],
        ).iloc[0]

        forecasts = read_df(
            con,
            """
            SELECT forecast_month, forecast_value, lower_80, upper_80,
                   trained_through, method
            FROM raw.fact_forecast
            WHERE metric = 'headcount_end'
              AND department_id = 'ALL'
              AND forecast_month > CAST(? || '-01' AS DATE)
            ORDER BY forecast_month
            LIMIT 3
            """,
            [month],
        )

        cutoffs = read_df(
            con,
            """
            SELECT
              (SELECT MAX(period_end_date)
               FROM governed.m09_payroll_cost
               WHERE strftime(period_end_date, '%Y-%m') = ?) AS payroll_cutoff,
              (SELECT MAX(period_end_date)
               FROM governed.m13_attendance_rate
               WHERE strftime(period_end_date, '%Y-%m') = ?) AS attendance_cutoff
            """,
            [month, month],
        ).iloc[0]

        cutoff_dates = [
            value for value in [
                cutoffs["payroll_cutoff"],
                cutoffs["attendance_cutoff"],
            ] if pd.notna(value)
        ]
        cutoff = min(cutoff_dates).strftime("%d %B %Y")

        with tempfile.TemporaryDirectory() as temp_folder:
            charts = make_charts(con, month, temp_folder)

            styles = getSampleStyleSheet()
            styles.add(ParagraphStyle(
                name="MainTitle",
                parent=styles["Title"],
                alignment=TA_CENTER,
                fontSize=19,
                leading=24,
            ))
            styles.add(ParagraphStyle(
                name="Section",
                parent=styles["Heading2"],
                textColor=colors.HexColor("#17365D"),
                spaceBefore=10,
                spaceAfter=6,
            ))
            styles.add(ParagraphStyle(
                name="SmallNote",
                parent=styles["BodyText"],
                fontSize=8,
                leading=11,
            ))

            doc = SimpleDocTemplate(
                str(output_path),
                pagesize=A4,
                rightMargin=15 * mm,
                leftMargin=15 * mm,
                topMargin=15 * mm,
                bottomMargin=15 * mm,
                title=f"PulseIQ Monthly Report {month}",
            )

            story = [
                Paragraph("PulseIQ — Monthly Company Report", styles["MainTitle"]),
                Spacer(1, 8),
                Paragraph(
                    f"<b>Reporting period:</b> {first_day:%d %B %Y} "
                    f"to {last_day:%d %B %Y}<br/>"
                    f"<b>Data cut-off:</b> {cutoff}<br/>"
                    f"<b>Generated:</b> {datetime.now().astimezone():%d %B %Y, %H:%M %Z}<br/>"
                    f"<b>Reporting month:</b> {month}",
                    styles["BodyText"],
                ),
                Paragraph("1. Executive KPI Summary", styles["Section"]),
            ]

            kpi_rows = [["KPI", "Reported value"]]
            kpi_rows += [
                ["Visible department headcount", fmt_number(kpis["Headcount"])],
                ["Monthly attrition (weighted)", fmt_percent(kpis["Attrition"])],
                ["Visible department payroll", fmt_money(kpis["Payroll"])],
                ["Attendance rate (weighted)", fmt_percent(kpis["Attendance"] * 100)],
                ["Revenue (visible accounts)", fmt_money(kpis["Revenue"])],
                ["Net profit", fmt_money(kpis["Net profit"])],
                ["Operating margin", fmt_percent(kpis["Operating margin"])],
            ]

            table = Table(kpi_rows, colWidths=[90 * mm, 80 * mm], repeatRows=1)
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17365D")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1),
                 [colors.white, colors.HexColor("#F2F5F9")]),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]))
            story.extend([table, Paragraph(
                "2. Department Performance", styles["Section"]
            )])

            dept_rows = [[
                "Department", "Headcount", "Attrition", "Payroll (INR)", "Attendance"
            ]]
            for _, row in departments.iterrows():
                dept_rows.append([
                    row["department_name"],
                    fmt_number(row["headcount"]),
                    fmt_percent(row["attrition"]),
                    fmt_money(row["payroll"]),
                    "N/A" if pd.isna(row["attendance"])
                    else fmt_percent(row["attendance"] * 100),
                ])

            dept_table = Table(
                dept_rows,
                colWidths=[44 * mm, 22 * mm, 22 * mm, 45 * mm, 27 * mm],
                repeatRows=1,
            )
            dept_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17365D")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.grey),
                ("PADDING", (0, 0), (-1, -1), 5),
            ]))
            story.extend([dept_table, Spacer(1, 10)])

            for key, heading in [
                ("payroll", "Department Payroll Chart"),
                ("headcount", "Department Headcount Chart"),
                ("trend", "Revenue and Net Profit Trend"),
            ]:
                if key in charts:
                    story.append(Paragraph(heading, styles["Section"]))
                    story.append(Image(
                        str(charts[key]), width=170 * mm, height=82 * mm
                    ))

            story.extend([
                PageBreak(),
                Paragraph("3. Anomaly Monitoring", styles["Section"]),
                Paragraph(
                    f"Flagged anomaly records in {month}: "
                    f"<b>{int(anomalies['flagged_count'])}</b><br/>"
                    f"Distinct affected employees: "
                    f"<b>{int(anomalies['affected_employees'])}</b>",
                    styles["BodyText"],
                ),
                Paragraph("4. Forward Headcount Forecast", styles["Section"]),
            ])

            if not forecasts.empty:
                forecast_rows = [[
                    "Forecast month", "Forecast", "Lower 80%", "Upper 80%"
                ]]
                for _, row in forecasts.iterrows():
                    forecast_rows.append([
                        pd.to_datetime(row["forecast_month"]).strftime("%b %Y"),
                        fmt_number(row["forecast_value"]),
                        fmt_number(row["lower_80"]),
                        fmt_number(row["upper_80"]),
                    ])

                forecast_table = Table(
                    forecast_rows,
                    colWidths=[42 * mm, 42 * mm, 42 * mm, 42 * mm],
                    repeatRows=1,
                )
                forecast_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17365D")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                    ("PADDING", (0, 0), (-1, -1), 6),
                ]))
                story.append(forecast_table)
                story.append(Paragraph(
                    f"Forecast model trained through "
                    f"{forecasts.iloc[0]['trained_through']}. "
                    "Forecast values are estimates, not actual results.",
                    styles["SmallNote"],
                ))
            else:
                story.append(Paragraph(
                    "No future headcount forecast is available for this month.",
                    styles["BodyText"],
                ))

            story.append(Paragraph(
                "5. Methodology and Limitations", styles["Section"]
            ))

            notes = [
                "All actual KPI values come from the governed Task 4 metric views.",
                "Suppressed groups are excluded, not treated as zero.",
                "Leadership department D00 is excluded from department comparisons.",
                "Attrition and attendance are weighted by the governed group_size field; these are estimates and not a reconstruction from employee-level denominators.",
                "Revenue is summed from visible account-level records.",
                "Task completion is sprint/team grain, not monthly grain, so it is not presented as a monthly KPI.",
                "Forecast values are shown separately from actual results.",
                "Anomaly flags are monitoring signals and do not independently establish confirmed loss or fraud.",
            ]
            for note in notes:
                story.append(Paragraph(f"• {note}", styles["SmallNote"]))
                story.append(Spacer(1, 4))

            story.append(Spacer(1, 10))
            story.append(Paragraph(
                f"Source database: {db_path.name}<br/>"
                "Generated by the PulseIQ Task 16 Automated Report Builder.",
                styles["SmallNote"],
            ))

            doc.build(story)

    finally:
        con.close()

    print("========== REPORT GENERATED ==========")
    print(f"Reporting month : {month}")
    print(f"Period          : {first_day} to {last_day}")
    print(f"Data cut-off    : {cutoff}")
    print(f"PDF             : {output_path}")
    print(f"File size       : {output_path.stat().st_size:,} bytes")


def main():
    parser = argparse.ArgumentParser(
        description="Generate a PulseIQ monthly PDF report."
    )
    parser.add_argument(
        "--month", required=True,
        help="Reporting month in YYYY-MM format, e.g. 2026-09"
    )
    parser.add_argument(
        "--database", default=str(DEFAULT_DB),
        help="Path to the PulseIQ DuckDB database"
    )
    parser.add_argument(
        "--output", default=None,
        help="Optional output PDF path"
    )
    args = parser.parse_args()

    try:
        datetime.strptime(args.month, "%Y-%m")
    except ValueError:
        parser.error("--month must use YYYY-MM format")

    db_path = Path(args.database).expanduser().resolve()
    output_path = (
        Path(args.output).expanduser().resolve()
        if args.output
        else REPORT_DIR / f"PulseIQ_Monthly_Report_{args.month}.pdf"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    build_report(args.month, db_path, output_path)


if __name__ == "__main__":
    main()
