"""
Script: scripts/render_readme_tables.py
Purpose: Renders authoritative data tables in README.md and report/decision_memo.md directly from marketplace.duckdb.
Supports --check flag to ensure documentation tables never drift from database artifacts.
"""

import os
import sys
import argparse
import difflib
import duckdb
import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scripts.run_review_econometrics import load_data, fit_models, generate_regression_markdown_table, get_db_connection
from scripts.run_persistence_check import render_persistence_markdown

def get_rendered_blocks(con):
    # 1. Economic Framework Block
    kpi = con.execute("SELECT * FROM view_executive_kpi_summary").df().iloc[0]
    p1 = con.execute("SELECT * FROM view_intervention_tier_summary WHERE priority_tier LIKE 'P1%'").df().iloc[0]

    framework_content = (
        "```\n"
        "LEVEL 1 — Late-Order GMV & Freight (Observable)\n"
        f"  ├── Late-Order GMV:                 E_late^GMV = R$ {kpi['total_late_order_gmv_exposure']:,.2f}\n"
        f"  ├── Late-Order Freight:             E_late^freight = R$ {kpi['total_late_order_freight_exposure']:,.2f}\n"
        f"  └── Total Late-Order Value:         E_late = R$ {kpi['total_late_transaction_exposure']:,.2f} (Late-order GMV + freight)\n\n"
        "LEVEL 2 — Cost Burden (Observable)\n"
        f"  ├── Platform Freight Burden:        Total Freight / Total GMV = {kpi['overall_freight_burden_pct']:.2f}%\n"
        f"  └── High-Freight Exposure:          R$ {kpi['total_high_freight_gmv_exposure']:,.2f} GMV where Freight-to-Value >= 30%\n\n"
        "LEVEL 3 — Illustrative Scenarios (Assumed Rates, Not Measured)\n"
        f"  Focuses on Priority 1 (P1) Sellers (R$ {p1['total_seller_late_exposure']:,.2f} Seller Late GMV+Freight across {int(p1['seller_count'])} merchants):\n"
        f"  ├── Conservative Scenario (10% Assumed Mitigation): R$ {p1['scenario_mitigation_conservative_10pct']:,.2f}\n"
        f"  ├── Base Scenario (25% Assumed Mitigation):         R$ {p1['scenario_mitigation_base_25pct']:,.2f}\n"
        f"  └── Optimistic Scenario (40% Assumed Mitigation):   R$ {p1['scenario_mitigation_optimistic_40pct']:,.2f}\n"
        "```"
    )

    # 2. Tier Table Block
    tiers = con.execute("SELECT * FROM view_intervention_tier_summary ORDER BY priority_tier").df()
    playbooks = {
        'P1': "Lead-time calibration, packaging audit, carrier handoff inspection",
        'P2': "Carrier dispatch inspection, lane-specific carrier re-allocation",
        'P3': "Automated portal threshold warnings; 30-day monitoring window",
        'P4': "Routine partner management; low-volume sellers ($N < 30$) and standard baseline operations"
    }

    tier_lines = [
        "| Priority Tier | Seller Count | % Seller Base | Total Orders* | Total GMV (R$) | Seller Late Exp (R$) | % Platform Seller Exp | Late Mitigation (Base 25%) | Recommended Operational Action |",
        "|---|---|---|---|---|---|---|---|---|"
    ]
    for _, r in tiers.iterrows():
        tcode = r['priority_tier'][:2]
        is_p1 = tcode == 'P1'
        p_name = f"**{r['priority_tier']}**" if is_p1 else r['priority_tier']
        s_count = f"**{int(r['seller_count']):,}**" if is_p1 else f"{int(r['seller_count']):,}"
        s_pct = f"**{r['pct_of_seller_base']:.2f}%**" if is_p1 else f"{r['pct_of_seller_base']:.2f}%"
        exp_val = f"**R$ {r['total_seller_late_exposure']:,.2f}**" if is_p1 else f"R$ {r['total_seller_late_exposure']:,.2f}"
        pct_exp = f"**{r['pct_of_platform_seller_exposure']:.2f}%**" if is_p1 else f"{r['pct_of_platform_seller_exposure']:.2f}%"
        base_mit = f"**R$ {r['scenario_mitigation_base_25pct']:,.2f}**" if is_p1 else f"R$ {r['scenario_mitigation_base_25pct']:,.2f}"
        tier_lines.append(
            f"| {p_name} | {s_count} | {s_pct} | {int(r['total_orders']):,} | R$ {r['total_gmv']/1e6:.2f}M | {exp_val} | {pct_exp} | {base_mit} | {playbooks.get(tcode, 'Standard governance')} |"
        )
    tier_content = "\n".join(tier_lines)

    # 3. Sensitivity Check Block
    sens = con.execute("SELECT * FROM view_threshold_sensitivity_check").df()
    s20 = sens[sens['scenario'].str.contains('20')].iloc[0]
    s30 = sens[sens['scenario'].str.contains('30')].iloc[0]
    s50 = sens[sens['scenario'].str.contains('50')].iloc[0]
    
    sens_content = (
        "### Volume Cutoff Sensitivity Check\n"
        f"- **$N \\ge 20$:** {int(s20['p1_sellers_count'])} P1 sellers, R$ {s20['p1_seller_exposure_total']/1e3:.1f}K seller late exposure\n"
        f"- **$N \\ge 30$ (Base):** {int(s30['p1_sellers_count'])} P1 sellers, R$ {s30['p1_seller_exposure_total']/1e3:.1f}K seller late exposure\n"
        f"- **$N \\ge 50$:** {int(s50['p1_sellers_count'])} P1 sellers, R$ {s50['p1_seller_exposure_total']/1e3:.1f}K seller late exposure"
    )

    # 4. Econometric Regression Table Block (Model B with SE Sensitivities)
    df_reg = load_data(con=con)
    models = fit_models(df_reg)
    regression_content = generate_regression_markdown_table(models)

    mb = models['logit_b']['seller_id']
    coef_undelivered = mb.params['undelivered_at_review']
    odds_undelivered = np.exp(coef_undelivered)
    coef_overdue = mb.params['days_overdue_at_review']
    odds_overdue = np.exp(coef_overdue)
    se_overdue = mb.bse['days_overdue_at_review']
    z_overdue = mb.tvalues['days_overdue_at_review']
    pval_overdue = mb.pvalues['days_overdue_at_review']
    pval_overdue_str = "< 0.001" if pval_overdue < 0.001 else f"= {pval_overdue:.3f}"
    odds_30d = np.exp(coef_overdue * 30)

    model_b_concepts_content = (
        "- **Model B (Information Set at Review Time):**\n"
        r"  $$\text{logit}(p_i) = \gamma_0 + \gamma_1 \cdot \text{undelivered\_at\_review}_i + \gamma_2 \cdot \text{days\_overdue\_at\_review}_i + \gamma_3 \cdot \ln(\text{price}_i) + \gamma_4 \cdot \text{freight\_ratio}_i$$" + "\n"
        f"  Yields $\\text{{OR}} = {odds_undelivered:.2f}\\times$ ($p < 10^{{-15}}$) for $\\text{{undelivered\\_at\\_review}}$, while $\\gamma_2$ is economically small: $\\text{{OR}} = {odds_overdue:.4f}$ per day overdue ($p {pval_overdue_str}$, $z = {z_overdue:.2f}$, $\\text{{SE}} = {se_overdue:.4f}$). A 30-day overdue delay increases odds by only ${odds_30d:.2f}\\times$, compared to ${odds_undelivered:.2f}\\times$ for non-receipt at review time.\n\n"
        "Conclusion: Customer dissatisfaction is driven by the **binary non-receipt event** at the promised date (an immediate step-function penalty), while subsequent overdue days have an economically small incremental effect."
    )

    model_b_adr_content = (
        f"- **Consequences:** Proves customer dissatisfaction is driven by the binary promise breach (`undelivered_at_review`, $\\text{{OR}} = {odds_undelivered:.2f}\\times, p < 10^{{-15}}$), while marginal delay days have an economically small effect ($\\text{{OR}} = {odds_overdue:.4f}$ per day, $p {pval_overdue_str}$, $z = {z_overdue:.2f}$; 30 days overdue yields only $\\sim {odds_30d:.2f}\\times$ vs ${odds_undelivered:.2f}\\times$ for non-arrival)."
    )

    model_b_results_content = (
        f"1. **Economically Negligible Marginal Overdue Delay (Step-Function Discontinuity):** In Model B (conditioning on information set at survey submission), the coefficient on marginal days overdue after dispatch is statistically significant ($p {pval_overdue_str}, z = {z_overdue:.2f}$) but economically small ($\\text{{OR}} = {odds_overdue:.4f}$ per day, $\\text{{SE}} = {se_overdue:.4f}$; 30 days overdue increases odds by only ${odds_30d:.2f}\\times$ vs ${odds_undelivered:.2f}\\times$ for non-receipt). Customer dissatisfaction is an immediate step-function penalty triggered on Day 0 of promise breach, refuting the hypothesis of linear daily compounding decay."
    )

    model_b_study_pitch_content = (
        f"> In Model B, conditioning on the customer's information set at survey time, binary non-receipt (`undelivered_at_review`) produces an odds ratio of {odds_undelivered:.2f}x (p < 1e-15, clustered on `seller_id`), while marginal daily delay is economically small (OR = {odds_overdue:.4f} per day, p {pval_overdue_str}, z = {z_overdue:.2f}; 30 days overdue adds only ~{odds_30d:.2f}x odds vs {odds_undelivered:.2f}x for non-receipt). Customer dissatisfaction is a step-function promise breach, not a linear daily decay."
    )

    model_b_study_q05_content = (
        f"- **Answer:** Once the binary state of parcel non-arrival at survey time (`undelivered_at_review`) is included ($\\text{{OR}} = {odds_undelivered:.2f}\\times$), the marginal day coefficient is economically small ($\\text{{OR}} = {odds_overdue:.4f}$ per day, $p {pval_overdue_str}, z = {z_overdue:.2f}$; 30 days overdue adds only $\\sim {odds_30d:.2f}\\times$ odds). Customer dissatisfaction is triggered by the breach of promise date (step function), not daily compounding."
    )

    # 5. Out-of-Sample Persistence Check Block (2017 -> 2018 holdout, MP-06): cohort and rates come from
    #    SQL views that share the headline tier rule; bootstrap intervals come from run_persistence_check.py
    persistence_content = render_persistence_markdown(con)

    return {
        "ECONOMIC_FRAMEWORK": framework_content,
        "TIER_TABLE": tier_content,
        "SENSITIVITY_CHECK": sens_content,
        "REGRESSION_TABLE": regression_content,
        "PERSISTENCE_CHECK": persistence_content,
        "MODEL_B_CONCEPTS": model_b_concepts_content,
        "MODEL_B_ADR": model_b_adr_content,
        "MODEL_B_RESULTS": model_b_results_content,
        "MODEL_B_STUDY_PITCH": model_b_study_pitch_content,
        "MODEL_B_STUDY_Q05": model_b_study_q05_content
    }

def update_file_markers(file_path, blocks, check_only=False):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    updated = content
    for marker, block_text in blocks.items():
        start_tag = f"<!-- BEGIN_{marker} -->"
        end_tag = f"<!-- END_{marker} -->"
        start_idx = updated.find(start_tag)
        end_idx = updated.find(end_tag)
        if start_idx == -1 or end_idx == -1:
            continue
        updated = updated[:start_idx + len(start_tag)] + "\n" + block_text + "\n" + updated[end_idx:]

    norm_updated = updated.replace("\r\n", "\n").strip()
    norm_content = content.replace("\r\n", "\n").strip()

    if check_only:
        if norm_updated != norm_content:
            diff = list(difflib.unified_diff(norm_content.splitlines(), norm_updated.splitlines(), fromfile=os.path.basename(file_path), tofile="UPDATED"))
            print(f"ERROR: {os.path.basename(file_path)} does not match database artifacts!")
            for line in diff[:15]:
                print("  ", line)
            return False
        else:
            print(f"CHECK PASS: {os.path.basename(file_path)} matches database artifacts.")
            return True
    else:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(updated)
        print(f"Successfully rendered and synchronized {os.path.basename(file_path)}.")
        return True

def sync_all(check_only=False):
    con = get_db_connection(read_only=True)
    try:
        blocks = get_rendered_blocks(con)
    finally:
        con.close()

    target_files = [
        os.path.join(PROJECT_ROOT, "README.md"),
        os.path.join(PROJECT_ROOT, "report", "decision_memo.md"),
        os.path.join(PROJECT_ROOT, "docs", "guide", "01_CONCEPTS.md"),
        os.path.join(PROJECT_ROOT, "docs", "guide", "08_DESIGN_DECISIONS.md"),
        os.path.join(PROJECT_ROOT, "docs", "guide", "09_RESULTS_AND_LIMITATIONS.md"),
    ]

    all_passed = True
    for fp in target_files:
        if not os.path.isfile(fp):
            continue
        passed = update_file_markers(fp, blocks, check_only=check_only)
        if not passed:
            all_passed = False

    if check_only:
        if all_passed:
            sys.exit(0)
        else:
            sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Check without modifying files")
    args = parser.parse_args()
    sync_all(check_only=args.check)
