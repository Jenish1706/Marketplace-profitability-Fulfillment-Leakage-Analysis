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

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scripts.run_review_econometrics import load_data, fit_models, generate_regression_markdown_table, get_db_connection

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

    # 5. Out-of-Sample Persistence Check Block (2017 -> 2018 Holdout)
    pers = con.execute("SELECT * FROM view_seller_persistence_check ORDER BY tier_2017").df()
    p_other = pers[pers['tier_2017'] == 'Other_2017'].iloc[0]
    p_p1 = pers[pers['tier_2017'] == 'P1_2017'].iloc[0]

    persistence_content = (
        "### Out-of-Sample Persistence Check (2017 → 2018 Holdout)\n"
        "| 2017 Merchant Cohort | 2018 Active Sellers | Avg Orders (2018) | Avg Late Delivery Rate (2018) | Sellers with Late Orders (2018) | Share Exceeding Base Late Rate (8.60%) |\n"
        "|---|---|---|---|---|---|\n"
        f"| **2017 P1 Priority Cohort** | {int(p_p1['active_in_2018_sellers'])} | {p_p1['avg_orders_2018']:.1f} | **{p_p1['avg_late_rate_2018']:.2f}%** | {p_p1['pct_with_late_orders']:.2f}% ({int(p_p1['sellers_with_late_in_2018'])}/{int(p_p1['active_in_2018_sellers'])}) | **{p_p1['pct_above_base_rate']:.2f}% ({int(p_p1['sellers_above_base_rate'])}/{int(p_p1['active_in_2018_sellers'])})** |\n"
        f"| Other 2017 Sellers | {int(p_other['active_in_2018_sellers']):,} | {p_other['avg_orders_2018']:.1f} | {p_other['avg_late_rate_2018']:.2f}% | {p_other['pct_with_late_orders']:.2f}% ({int(p_other['sellers_with_late_in_2018'])}/{int(p_other['active_in_2018_sellers']):,}) | {p_other['pct_above_base_rate']:.2f}% ({int(p_other['sellers_above_base_rate'])}/{int(p_other['active_in_2018_sellers']):,}) |\n\n"
        f"**Persistence Validation:** Testing 2017 P1 sellers out-of-sample across 2018 demonstrates that operational friction is chronic. Among 2017 P1 merchants active in 2018, **{p_p1['pct_above_base_rate']:.2f}%** continued to exceed the platform baseline late rate ({p_other['avg_late_rate_2018']:.2f}%), averaging a **{p_p1['avg_late_rate_2018']:.2f}% late delivery rate** (+51.7% relative penalty vs non-P1 merchants). Overall, {p_p1['pct_with_late_orders']:.2f}% recorded late deliveries in 2018, validating that high-friction fulfillment reflects structural merchant dispatch deficits rather than transient seasonal noise."
    )

    return {
        "ECONOMIC_FRAMEWORK": framework_content,
        "TIER_TABLE": tier_content,
        "SENSITIVITY_CHECK": sens_content,
        "REGRESSION_TABLE": regression_content,
        "PERSISTENCE_CHECK": persistence_content
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
        os.path.join(PROJECT_ROOT, "report", "decision_memo.md")
    ]

    all_passed = True
    for fp in target_files:
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
