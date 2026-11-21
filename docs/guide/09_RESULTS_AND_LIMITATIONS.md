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
| **RES-06** | Out-of-Sample Holdout Persistence | Partial persistence: the 2017 P1 cohort's seller-caused excess shrinks but stays positive in 2018. Rates, gaps and bootstrap intervals are rendered in Section 2 below. | [`sql/07_intervention_priority.sql`](../../sql/07_intervention_priority.sql) |
| **RES-07** | Review Survey Mechanism Confounder | **70.10%** of late-order reviews were submitted before delivery ($3.73$ days late at survey vs $13.82$ days at delivery). | [`scripts/run_review_econometrics.py`](../../scripts/run_review_econometrics.py) |
| **RES-08** | Non-Receipt Econometric Penalty | Binary non-receipt at survey (`undelivered_at_review`) yields $\text{OR} = \mathbf{33.63\times}$ ($p < 10^{-15}$, cluster-robust $\text{SE} = 0.0506$) and OLS rating drop of $\mathbf{-2.5125\text{ stars}}$ ($\text{SE} = 0.0252$). | [`scripts/run_review_econometrics.py`](../../scripts/run_review_econometrics.py) |

---

## 2. Null & Negative Results

Documenting what was *not* supported by data is essential for executive decision-making:

<!-- BEGIN_MODEL_B_RESULTS -->
1. **Economically Negligible Marginal Overdue Delay (Step-Function Discontinuity):** In Model B (conditioning on information set at survey submission), the coefficient on marginal days overdue after dispatch is statistically significant ($p < 0.001, z = 4.65$) but economically small ($\text{OR} = 1.0036$ per day, $\text{SE} = 0.0008$; 30 days overdue increases odds by only $1.11\times$ vs $33.63\times$ for non-receipt). Customer dissatisfaction is an immediate step-function penalty triggered on Day 0 of promise breach, refuting the hypothesis of linear daily compounding decay.
<!-- END_MODEL_B_RESULTS -->

The persistence of the P1 tier is also only partly supported. Applying the headline tier rule to 2017 orders alone and following those sellers into 2018 gives:

<!-- BEGIN_PERSISTENCE_CHECK -->
### Out-of-Sample Persistence Check (2017 → 2018)

The 2017 P1 cohort is chosen with the same tier rule as the headline P1 tier, applied to 2017 orders only (`view_seller_tiers_by_period`). Rates are item-level (late items ÷ delivered items), pooled over sellers active in both years; gaps are computed from unrounded rates. Intervals are 95% seller-level bootstrap percentile intervals (5,000 resamples, fixed seed).

| Outcome | Cohort | 2017 | 2018 | Change |
|---|---|---|---|---|
| Seller-caused late rate (primary) | 2017 P1 sellers (n = 52) | 4.99% | 2.97% | -2.02 pts |
| | All other sellers (n = 1,023) | 0.97% | 1.54% | +0.57 pts |
| | **Gap (P1 − other)** | 4.02 pts | **1.44 pts** [0.54, 2.77] | **-2.59 pts** [-4.78, -1.01] |
| All-cause late rate (secondary) | 2017 P1 sellers (n = 52) | 9.17% | 8.26% | -0.91 pts |
| | All other sellers (n = 1,023) | 4.68% | 7.75% | +3.06 pts |
| | **Gap (P1 − other)** | 4.49 pts | **0.51 pts** [-0.86, 2.14] | **-3.98 pts** [-6.04, -2.18] |

**Reading:** the seller-caused gap between 2017 P1 sellers and other sellers was 4.02 pts in 2017 and 1.44 pts in 2018, which is still positive (its interval excludes zero); the change of -2.59 pts is a decrease whose interval excludes zero. About 36% of the 2017 gap remains in 2018. Part of the P1 excess therefore persists, but most of it does not carry over. Shrinkage of this kind is what selecting sellers on a high 2017 rate produces even when underlying performance is stable (regression to the mean), and this check cannot separate that from genuine improvement. The P1 tier is a prioritisation list for review, not evidence that these sellers have a fixed trait.

*Sensitivity:* weighting every seller equally (unweighted means of seller-level rates) gives seller-caused rates of 7.63% → 4.89% for P1 sellers and 2.09% → 3.04% for other sellers, a gap of 5.55 pts in 2017 and 1.85 pts in 2018 (33% remains).

*Limits:* sellers that stopped selling after 2017 are not in the 2018 comparison, and the all-cause outcome also counts carrier and promise-setting delay that sellers do not control.
<!-- END_PERSISTENCE_CHECK -->
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
