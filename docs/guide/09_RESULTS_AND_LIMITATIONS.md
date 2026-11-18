# 09: Empirical Results, Limitations & Validity Threats

**Project:** Marketplace Profitability & Fulfillment Leakage Analysis  
**Author:** Jenish Patel  
**Purpose:** Comprehensive catalogue of empirical findings with uncertainty estimates, null results, validity threats, and research roadmap.

---

## 1. Primary Empirical Findings & Confidence Bounds

All findings are derived directly from reproducible SQL views and statistical scripts:

| Finding Ref | Empirical Result | Point Estimate & Uncertainty | Artifact Source |
|---|---|---|---|
| **RES-01** | Platform Late Delivery Baseline | **6.77%** ($6,534 / 96,478$ delivered orders). Exact finite-sample parameter under date casting. | [`sql/03_order_item_fact.sql`](../../sql/03_order_item_fact.sql) |
| **RES-02** | Observable Late-Order Value ($E_{\text{late}}$) | **R\$ 1,150,892.13 total** (GMV: R\$ 985,924.34 + Freight: R\$ 164,967.79), representing 8.47% of platform gross flow. | [`sql/07_intervention_priority.sql`](../../sql/07_intervention_priority.sql) |
| **RES-03** | Logistics Fulfillment Attribution | **72.25% Carrier-Caused** ($4,730 / 6,547$ late items, R\$ 779,610.99); **27.75% Seller-Caused** ($1,817 / 6,547$ items, R\$ 371,281.14). | [`sql/05_root_cause_analysis.sql`](../../sql/05_root_cause_analysis.sql) |
| **RES-04** | Pareto Decile 1 Concentration Lift | **60.78% GMV share** vs **77.38% late exposure share** $\implies$ **1.27× concentration lift** across top 310 merchants. | [`sql/06_pareto_analysis.sql`](../../sql/06_pareto_analysis.sql) |
| **RES-05** | P1 Intervention Priority Cohort | **113 merchants** account for **R\$ 181,377.55** in seller late exposure (48.85% of platform seller exposure). Modeled addressable exposure: **R\$ 45,344.39** (Base 25%). | [`sql/07_intervention_priority.sql`](../../sql/07_intervention_priority.sql) |
| **RES-06** | Out-of-Sample Holdout Persistence | Active 2017 P1 sellers repeat a **13.05% late rate in 2018** (vs 8.60% for non-P1); **54.17%** exceed baseline and **87.50%** record late orders. | [`sql/07_intervention_priority.sql`](../../sql/07_intervention_priority.sql) |
| **RES-07** | Review Survey Mechanism Confounder | **70.10%** of late-order reviews were submitted before delivery ($3.73$ days late at survey vs $13.82$ days at delivery). | [`scripts/run_review_econometrics.py`](../../scripts/run_review_econometrics.py) |
| **RES-08** | Non-Receipt Econometric Penalty | Binary non-receipt at survey (`undelivered_at_review`) yields $\text{OR} = \mathbf{33.63\times}$ ($p < 10^{-15}$, cluster-robust $\text{SE} = 0.0506$) and OLS rating drop of $\mathbf{-2.5125\text{ stars}}$ ($\text{SE} = 0.0252$). | [`scripts/run_review_econometrics.py`](../../scripts/run_review_econometrics.py) |

---

## 2. Null & Negative Results

Documenting what was *not* supported by data is essential for executive decision-making:

1. **Null Finding on Marginal Overdue Delay:** In Model B (conditioning on information set at survey submission), the coefficient on marginal days overdue after dispatch is statistically indistinguishable from zero ($\text{OR} = 1.004, p = 0.52$). Customer dissatisfaction is an immediate step-function penalty triggered on Day 0 of promise breach, not a daily compounding penalty.
2. **Negative Finding on Merchant Responsibility:** Merchant dispatch delays do not account for the majority of delivery failures. Attributing 100% of failure to sellers is soundly refuted by data (sellers dispatched on time in 72.25% of late orders).
3. **Negative Finding on Intra-State Logistics:** Intra-state delivery within São Paulo (SP $\to$ SP) is not the driver of platform logistics strain. SP $\to$ SP maintains a healthy 6.10% late rate and 13.21% freight burden. Platform logistics failure is overwhelmingly concentrated in long-haul interstate corridors (e.g. SP $\to$ RJ: 14.85% late rate, R\$ 197K in late value).

---

## 3. Threats to Validity

### Internal Validity
- **Unobserved Handover Scans:** We evaluate seller dispatch SLA against `shipping_limit_date` using `order_delivered_carrier_date`. If sellers generate shipping labels electronically prior to physical carrier handover (manifest pre-scanning), actual seller delay could be masked as carrier transit time.
- **Survey Trigger Timing:** Olist automated review requests around the estimated delivery date. This mechanism explains why pre-delivery reviews correlate with delivery lateness, but survey response rate itself may be subject to voluntary response bias (unhappy customers are more motivated to respond).

### External Validity
- **Temporal & Macro Specificity:** Data reflects Brazilian e-commerce operations in 2016–2018. During March 2018, the national postal service (Correios) experienced nationwide logistics disruptions and strikes, contributing to the 18.96% late delivery spike observed in Q1 2018. Findings cannot be naively generalized to modern Amazon-style private fulfillment networks (FBA).
- **Geography:** Brazil's continental scale and reliance on road freight create unique regional logistics frictions that differ from high-density geographies.

### Construct Validity
- **Economic Exposure vs Out-of-Pocket Loss:** Observable late-order GMV (R\$ 985.9K) represents transaction value at risk of customer churn, not direct accounting losses. Because actual marketplace take-rates and customer acquisition costs are unobserved, illustrative mitigation scenarios (10%, 25%, 40%) model addressable exposure, not guaranteed cash recovery.

---

## 4. Recommended Next Steps & Roadmap

If extended into a live production operations environment, the analytical roadmap should prioritize:
1. **API Integration with 3PL Carrier Milestones:** Ingest detailed checkpoint telemetry (origin hub scan, sorting scan, out-for-delivery scan) to separate line-haul transit delay from last-mile carrier failure.
2. **Repeat Purchase & LTV Decay Modeling:** Merge customer transaction histories into a survival model to measure the exact reduction in 90-day repeat purchase probability caused by experiencing an unarrived delivery.
3. **Quasi-Experimental SLA Pilot:** Deploy a randomized control trial (RCT) or difference-in-differences pilot across the 113 P1 merchants, applying dynamic checkout EDD buffering and testing whether cancellation rates decrease.
