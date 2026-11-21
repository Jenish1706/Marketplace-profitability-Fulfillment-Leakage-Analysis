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
| **RES-03** | Late-Delivery Attribution | **72.25% post-handover delay** ($4{,}730 / 6{,}547$ late (order, seller) pairs; R\$ 779,610.99 exposure); **27.75% late at dispatch** ($1{,}817 / 6{,}547$ pairs, including one pair with no recorded handover date; R\$ 371,281.14 exposure). The transit-vs-promise table below shows the post-handover leg is long, not merely promised tightly. | [`sql/05_root_cause_analysis.sql`](../../sql/05_root_cause_analysis.sql) |
| **RES-04** | Pareto Decile 1 Concentration Lift | **60.78% GMV share** vs **77.38% late exposure share** $\implies$ **1.27× concentration lift** across top 310 merchants. | [`sql/06_pareto_analysis.sql`](../../sql/06_pareto_analysis.sql) |
| **RES-05** | P1 Intervention Priority Cohort | **113 merchants** account for **R\$ 181,377.55** in seller late exposure (48.85% of platform seller exposure). Modeled addressable exposure: **R\$ 45,344.39** (Base 25%). | [`sql/07_intervention_priority.sql`](../../sql/07_intervention_priority.sql) |
| **RES-06** | Out-of-Sample Holdout Persistence | Partial persistence: the 2017 P1 cohort's seller-caused excess shrinks but stays positive in 2018. Rates, gaps and bootstrap intervals are rendered in Section 2 below. | [`sql/07_intervention_priority.sql`](../../sql/07_intervention_priority.sql) |
| **RES-07** | Review Survey Mechanism Confounder | **70.10%** of late-order reviews were submitted before delivery ($3.73$ days late at survey vs $13.82$ days at delivery). | [`scripts/run_review_econometrics.py`](../../scripts/run_review_econometrics.py) |
| **RES-08** | Non-Receipt Econometric Penalty | Binary non-receipt at survey (`undelivered_at_review`) yields $\text{OR} = \mathbf{33.63\times}$ ($p < 10^{-15}$, cluster-robust $\text{SE} = 0.0506$) and OLS rating drop of $\mathbf{-2.5125\text{ stars}}$ ($\text{SE} = 0.0252$). | [`scripts/run_review_econometrics.py`](../../scripts/run_review_econometrics.py) |

---

The attribution in RES-03 rests on the platform's *promised* date, not a carrier SLA, so "handed over on time but delivered late" mixes how long the leg took with how tight the promise was. This test separates the two:

<!-- BEGIN_POST_HANDOVER_SPLIT -->
### Post-Handover Delay: Transit vs Promise

Scope: 4,730 late post-handover (order, seller) pairs (seller handed over by `shipping_limit_date`, delivery after the promised date) against on-time pairs on the same corridor. 1,816 late pairs were already late at dispatch and 1 late pair(s) have no recorded handover date; both are outside this table. Days are date-level. Intervals are 95% bootstrap percentile intervals (2,000 resamples, fixed seed).

**Median days, late post-handover pairs vs on-time pairs (gap, interval)**

| Corridor | Pairs (late / on-time) | Purchase → promised date | Purchase → handover | Handover → delivery (transit) |
|---|---|---|---|---|
| SP -> SP | 845 / 29,733 | 16 vs 18 (-2 [-2, -1]) | 3 vs 2 (+1 [+0, +1]) | **19 vs 3** (+16 [+15, +17]) |
| SP -> RJ | 917 / 7,117 | 23 vs 25 (-2 [-3, -2]) | 3 vs 2 (+1 [+0, +1]) | **32 vs 8** (+24 [+22, +25]) |
| SP -> MG | 286 / 7,164 | 21 vs 24 (-3 [-3, -2]) | 2 vs 2 (+0 [+0, +1]) | **24 vs 7** (+17 [+16, +18]) |
| SP -> BA | 260 / 2,043 | 26 vs 30 (-4 [-5, -3]) | 2 vs 2 (+0 [+0, +1]) | **31 vs 13** (+18 [+17, +19]) |

**Would the late pairs have been on time? (descriptive counterfactual)**

| Corridor | Late post-handover pairs | On time with the corridor's typical transit | On time with the corridor's typical promise |
|---|---|---|---|
| SP -> SP | 845 | **90.2% [88.2%, 93.7%]** (typical transit 4 d) | 34.7% [31.8%, 37.9%] (typical promise 18 d) |
| SP -> RJ | 917 | **99.5% [99.0%, 99.9%]** (typical transit 9 d) | 14.9% [12.6%, 17.3%] (typical promise 25 d) |
| SP -> MG | 286 | **99.3% [98.3%, 100.0%]** (typical transit 7 d) | 35.3% [29.4%, 40.6%] (typical promise 24 d) |
| SP -> BA | 260 | **99.2% [98.1%, 100.0%]** (typical transit 14 d) | 28.5% [23.1%, 33.8%] (typical promise 30 d) |
| All 71 corridors with at least 100 pairs (point estimates) | 4,452 | 97.3% | 25.1% |

**Reading:** late pairs spent far longer in transit than on-time pairs on the same corridor, while their promises were only slightly shorter; giving them the corridor's typical transit would have put most of them on time, whereas a typical promise would have rescued few. The delay is therefore transit-driven rather than a promise-setting artefact.

*Limits:* the dataset has no carrier scans, so a long post-handover leg cannot be attributed to the carrier, to last-mile or to customer availability; handover dates are recorded by sellers, so a manifest scanned before the parcel physically left would hide dispatch delay inside transit; the counterfactuals are descriptive, not causal.
<!-- END_POST_HANDOVER_SPLIT -->

The "exposure" framing treats late-order value as value exposed to customer churn, but Stage A never measured churn. This measures the lateness-to-repurchase link directly:

<!-- BEGIN_REPURCHASE_LINK -->
### Lateness → Repurchase: The Measured Link to Churn

Cohort: 55,523 customers whose first delivered order was placed before 2018-03-01, so a full 180-day follow-up fits in the data. A customer "repurchased" if they placed another order (not canceled or unavailable) within 180 days of the first. Observational association, not a causal effect. Intervals are 95% (Wilson for rates; 5,000 bootstrap resamples with a fixed seed for differences and value bounds).

| First order | Customers | Repurchased within 180 days |
|---|---|---|
| Delivered on time | 51,849 | 2.86% [2.72%, 3.01%] |
| Delivered late | 3,674 | 2.45% [2.00%, 3.00%] |
| **Difference (late − on time)** | | **-0.41 pts [-0.94, +0.13]** (relative -14.3%) |

**Adjusted association (logit, HC1 robust SE; 18 customer-state groups, 25 category groups and 15 first-order-month groups; levels with fewer than 300 customers are pooled into "other")**

| Controls | Odds ratio, late vs on time | p-value | Average marginal effect |
|---|---|---|---|
| State + first-order category | 0.860 [0.691, 1.071] | 0.179 | -0.39 pts [-0.92, +0.14] |
| State + category + first-order month | 0.868 [0.695, 1.084] | 0.211 | -0.37 pts [-0.91, +0.18] |

**How much value can lateness-driven churn explain? (bound on the "exposure")**

| Quantity | Estimate | 95% interval |
|---|---|---|
| Mean repeat-purchase value per repurchaser (180 days) | R$ 159.87 | R$ 151.14 to R$ 169.28 |
| Repurchasers "missing" among late customers if the gap were causal | 15.0 | -4.8 to 34.6 |
| Implied repeat value at stake | R$ 2,400 | R$ -786 to R$ 5,511 |
| … as a share of these late first orders' value (R$ 661,028) | 0.36% | -0.12% to 0.83% |
| **Ceiling**: share of a late order's value at stake if lateness removed every repeat purchase an on-time customer would make | **2.54%** | 2.35% to 2.74% |

**Reading:** late first orders go with a lower repurchase rate, but the difference is not statistically distinguishable from zero, raw or adjusted. Repeat purchase is rare (about 3% within 180 days), so lateness-driven churn can explain at most a few percent of late-order value even in the extreme case. "Exposure" is therefore an upper bound on revenue at risk, not a measured loss.

*Limits:* a 180-day window and one cohort of first orders; repurchase is not lifetime value; lateness can also act through reviews and reputation, which this does not isolate; unobserved customer differences are not controlled.
<!-- END_REPURCHASE_LINK -->

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
- **Unobserved Handover Scans:** We evaluate seller dispatch SLA against `shipping_limit_date` using `order_delivered_carrier_date`. If sellers generate shipping labels electronically prior to physical carrier handover (manifest pre-scanning), actual seller delay could be masked as post-handover transit time.
- **Survey Trigger Timing:** Olist automated review requests around the estimated delivery date. This mechanism explains why pre-delivery reviews correlate with delivery lateness, but survey response rate itself may be subject to voluntary response bias (unhappy customers are more motivated to respond).

### External Validity
- **Temporal & Macro Specificity:** Data reflects Brazilian e-commerce operations in 2016–2018. During March 2018, the national postal service (Correios) experienced nationwide logistics disruptions and strikes, contributing to the 18.96% late delivery spike observed in Q1 2018. Findings cannot be naively generalized to modern Amazon-style private fulfillment networks (FBA).
- **Geography:** Brazil's continental scale and reliance on road freight create unique regional logistics frictions that differ from high-density geographies.

### Construct Validity
- **Economic Exposure vs Out-of-Pocket Loss:** Observable late-order GMV (R\$ 985.9K) is transaction value that was collected, not an accounting loss; the repurchase table in Section 1 measures how much of it can plausibly be churn (an upper bound of a few percent of the value, with no statistically distinguishable effect). Because actual marketplace take-rates and customer acquisition costs are unobserved, illustrative mitigation scenarios (10%, 25%, 40%) model addressable exposure, not guaranteed cash recovery.

---

## 4. Recommended Next Steps & Roadmap

If extended into a live production operations environment, the analytical roadmap should prioritize:
1. **API Integration with 3PL Carrier Milestones:** Ingest detailed checkpoint telemetry (origin hub scan, sorting scan, out-for-delivery scan) to separate line-haul transit delay from last-mile carrier failure.
2. **Repeat Purchase & LTV Decay Modeling:** Merge customer transaction histories into a survival model to measure the exact reduction in 90-day repeat purchase probability caused by experiencing an unarrived delivery.
3. **Quasi-Experimental SLA Pilot:** Deploy a randomized control trial (RCT) or difference-in-differences pilot across the 113 P1 merchants, applying dynamic checkout EDD buffering and testing whether cancellation rates decrease.
