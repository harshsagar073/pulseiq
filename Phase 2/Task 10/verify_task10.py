from pathlib import Path
import duckdb
import pandas as pd

BASE = Path(__file__).resolve().parent
SOURCE = "/Users/admin/Desktop/PulseIQ/Phase 1/Task 4/pulseiq_task4.duckdb"
OUTPUT = BASE / "pulseiq_task10.duckdb"
EXCLUDED = {"PI-X0001", "PI-X0002", "PI-X0003", "PI-X0004"}

src = duckdb.connect(SOURCE, read_only=True)
out = duckdb.connect(str(OUTPUT), read_only=True)

try:
    examples = out.execute("""
        SELECT month, department_id, department_name,
               budget_payroll_cost, actual_payroll_cost, variance_amount
        FROM budget_actual
        WHERE variance_amount > 0
        ORDER BY variance_amount DESC
        LIMIT 3
    """).fetchdf()

    results = []

    for r in examples.itertuples(index=False):
        month = pd.Timestamp(r.month)
        next_month = month + pd.offsets.MonthBegin(1)

        payroll = src.execute("""
            SELECT payroll_item_id, employer_cost
            FROM raw.fact_payroll
            WHERE period_end_date >= ?
              AND period_end_date < ?
              AND department_id = ?
        """, [month.date(), next_month.date(), r.department_id]).fetchall()

        manual_actual = sum(
            float(cost or 0)
            for item_id, cost in payroll
            if item_id not in EXCLUDED
        )

        manual_variance = manual_actual - float(r.budget_payroll_cost)

        results.append({
            "month": month.strftime("%Y-%m"),
            "department_id": r.department_id,
            "department_name": r.department_name,
            "budget": float(r.budget_payroll_cost),
            "manual_actual": round(manual_actual, 2),
            "manual_variance": round(manual_variance, 2),
            "dashboard_actual": round(float(r.actual_payroll_cost), 2),
            "dashboard_variance": round(float(r.variance_amount), 2),
            "actual_match": abs(manual_actual - float(r.actual_payroll_cost)) < 0.01,
            "variance_match": abs(manual_variance - float(r.variance_amount)) < 0.01
        })

    df = pd.DataFrame(results)
    df.to_csv(BASE / "verification" / "manual_verification.csv", index=False)

    lines = [
        "TASK 10 — MANUAL VERIFICATION",
        "Method: Python independently sums raw employer_cost.",
        "Excluded payroll IDs: PI-X0001, PI-X0002, PI-X0003, PI-X0004.",
        "Variance = actual employer cost minus budget.",
        ""
    ]

    for r in results:
        lines.append(
            f"{r['month']} | {r['department_id']} {r['department_name']} | "
            f"Budget={r['budget']:,.2f} | "
            f"Manual actual={r['manual_actual']:,.2f} | "
            f"Manual variance={r['manual_variance']:,.2f} | "
            f"Actual match={r['actual_match']} | "
            f"Variance match={r['variance_match']}"
        )

    matched = sum(r["actual_match"] and r["variance_match"] for r in results)
    lines += ["", f"Result: {matched}/{len(results)} examples matched."]

    (BASE / "verification" / "manual_verification.txt").write_text(
        "\n".join(lines) + "\n"
    )

    ranking = out.execute("""
        SELECT department_id, department_name,
               ROUND(SUM(GREATEST(variance_amount, 0)), 2) AS gross_overspend,
               ROUND(SUM(variance_amount), 2) AS net_variance,
               COUNT(*) FILTER (WHERE variance_amount > 0) AS over_budget_months
        FROM budget_actual
        GROUP BY department_id, department_name
        ORDER BY gross_overspend DESC
        LIMIT 2
    """).fetchdf()

    ranking.to_csv(
        BASE / "evidence" / "top_two_overspend_departments.csv",
        index=False
    )

    recommendations = [
        "TASK 10 — TOP TWO DEPARTMENT RECOMMENDATIONS",
        "Ranking basis: cumulative positive monthly variances (gross overspend).",
        "Net variance is reported separately.",
        "Hiring-freeze caveat: budgets may not have been refreshed after the freeze.",
        "Treat these departments as review priorities, not proof of avoidable spending.",
        ""
    ]

    for i, r in enumerate(ranking.itertuples(index=False), 1):
        recommendations.extend([
            f"{i}. {r.department_name} ({r.department_id})",
            f"Gross overspend: {r.gross_overspend:,.2f}",
            f"Net variance: {r.net_variance:,.2f}",
            f"Over-budget months: {r.over_budget_months}",
            "Action: reconcile paid headcount and employer-cost components against "
            "the approved budget. Check hiring-freeze timing, approved exceptions, "
            "vacancies, backfills and one-off payments before proposing cost reductions.",
            ""
        ])

    (BASE / "evidence" / "recommendations.txt").write_text(
        "\n".join(recommendations) + "\n"
    )

    print("===== MANUAL VERIFICATION =====")
    print(df.to_string(index=False))
    print(f"\nMatched examples: {matched}/{len(results)}")

    print("\n===== TOP TWO OVERS PEND DEPARTMENTS =====")
    print(ranking.to_string(index=False))

finally:
    src.close()
    out.close()
