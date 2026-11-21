# Executive Decision Memorandum

**TO:** Chief Operating Officer (COO), VP of Marketplace Operations  
**FROM:** Marketplace Commercial & Operational Analytics  
**DATE:** September 10, 2026 (Audited & Reconciled: November 2026)  
**SUBJECT:** Operational Diagnostic & Priority Intervention Strategy: Recovering Fulfillment Leakage  

---

### 1. Executive Summary

Between January 2017 and August 2018, the marketplace achieved strong commercial scale: **Gross Merchandise Value (GMV)** expanded from R$120K to ~R$1M monthly, processing **99,441 total orders** (96,478 delivered, 97.02% delivered rate) and generating **R$ 13.59M in cumulative GMV**. However, this top-line expansion masked severe operational friction and unit-economic compression:
1. **Fulfillment Deterioration Spikes:** Platform late delivery rates surged during high-volume periods, spiking to **12.40%** during Black Friday 2017 and collapsing to **18.96% in March 2018** (nearly 1 in 5 orders delivered late under calendar date comparison).
2. **Structural Logistics Cost Inflation:** Overall platform freight burden reached **16.57%** (R$ 2.25M freight on R$ 13.59M GMV), rising above **18.2%** by mid-2018, eroding contribution economics.
3. **Severe Exposure Concentration:** Operational failure is concentrated in high-volume merchants. **Decile 1 (top 10% of sellers, 310 sellers) accounts for 60.78% of GMV and 77.38% of total late-order GMV and freight (1.27× lift)**.
4. **Targeted Operational Mitigation:** By decoupling seller dispatch delays from post-handover delays, we identify a prioritized cohort of **113 Priority 1 (P1) sellers** representing **R$ 181,377.55 in seller-caused late exposure** (48.85% of platform seller-caused exposure). Under our Base Case scenario (25% operational mitigation), targeted operations management addresses **R$ 45,344.39 in addressable late-order GMV exposure**.

---

### 2. Macro Performance Inflection & Diagnostic Evidence

Longitudinal analysis demonstrates that platform logistics networks strained under peak commercial throughput:
- **Nov 2017 (Black Friday):** Orders jumped +63% month-over-month (to 7,544 orders), driving late delivery rates to 12.40% and late-order value to R$ 143.8K in a single month.
- **Q1 2018 Logistics Breakdown:** In February and March 2018, late delivery rates remained persistently elevated at **14.13%** and **18.96%**, with average delays for late shipments exceeding **+8.8 days** beyond estimated delivery dates.
- **Customer Satisfaction Impact:** Econometric and non-parametric analysis confirms severe degradation in customer ratings. Average review scores for on-time deliveries average **4.29 / 5.00** (9.2% low reviews $\le 2$ stars), but drop to **2.47** for orders delayed 3–5 days (56.7% low reviews) and **1.74** for orders delayed >5 days (78.1% low reviews). 
- **Review Timing Confounder (P0-3):** Among late orders, **70.10%** of customer reviews were submitted *before* package arrival (evaluating an order that was on average 3.73 days overdue at survey response, vs 13.82 days overdue at final delivery).
- **Statistical Significance & Econometrics:** Kruskal-Wallis test ($H = 10,167.48, p < 10^{-15}$) and rank-biserial effect sizes ($r = -0.781$) confirm strong negative association between delay and review scores. Logistic regression with seller-level cluster-robust standard errors (`seller_id`, 2,953 clusters; sensitivity-tested against `seller_state` and HC1) yields an odds ratio of **1.229 per late day** ($p < 0.001$, $\beta = 0.2060$) in the conventional model. When conditioning on the customer's information set at review time, the **binary unarrived state dominates** ($\text{OR} = 33.63\times, p < 10^{-15}$, $\beta = 3.5153, \text{SE} = 0.0506$; OLS $\beta = -2.5125$ stars, $\text{SE} = 0.0252$), proving that customer dissatisfaction is driven by breach of the delivery promise window rather than linear daily decay.

---

### 3. Root-Cause Decomposition

Fulfillment leakage is driven by three distinct operational mechanisms:
1. **Seller Volume vs Severity Decoupling:** Uncontrolled rankings mistake low-volume noise for business liability. Sellers with 100% late delivery rates on 2 orders generate negligible impact (R$ 72 exposure). Conversely, high-volume operational sellers (e.g., Seller `4a3ca93a...`, 1,806 orders, 16.0% late rate) generate **R$ 29,420.57 in late exposure** alone.
2. **Seller Dispatch vs Post-Handover Delay Attribution:** In **72.25% of late (order, seller) pairs** (4,730 of 6,547), the merchant handed the parcel over on or before `shipping_limit_date`, so the delay arose after handover. Platform late exposure is dominated by these post-handover delays (R$ 779,610.99, 67.74%), while seller dispatch breaches account for R$ 371,281.14 (32.26%). The test below shows the post-handover leg took far longer than on-time deliveries on the same corridor, not merely against a tighter promise.
3. **Category Structural Deficits:** Categories such as `furniture_decor`, `office_furniture`, and `bed_bath_table` exhibit heavy physical profiles (average volume >25,000 cm³, weight >3 kg) driving structural freight burdens of **20% to 25%**, severely penalizing basket economics.
4. **Cross-Regional Bottlenecks:** Intra-state deliveries within São Paulo (SP $\to$ SP) operate efficiently (freight burden 13.21%, late rate 6.10%). However, long-haul interstate corridors (SP $\to$ RJ, SP $\to$ BA, SP $\to$ MG) account for the bulk of platform delay, with SP $\to$ RJ generating **R$ 197K in late-order GMV and freight** with a 14.85% late delivery rate.

<!-- BEGIN_POST_HANDOVER_SUMMARY -->
**Post-handover delay (transit vs promise).** Of 6,547 late (order, seller) pairs, 4,730 (72.25%) were handed over by the shipping limit, so the delay arose after handover; 1,816 were already late at dispatch. On the same corridor these late pairs spent a median of 32 days in transit versus 8 for on-time pairs on SP → RJ (19 versus 3 on SP → SP), while their promises were only 2 days shorter on SP → RJ and 2 on SP → SP, so the extra delay is transit-driven rather than a promise-setting artefact. The dataset has no carrier scans, so it cannot say which party caused the extra transit. Method and corridor table: guide 09.
<!-- END_POST_HANDOVER_SUMMARY -->

---

### 4. Intervention Prioritization Framework

Rather than arbitrary weighted scoring, sellers are classified into deterministic tiers using percentile cutoffs applied to qualified operational sellers ($N \ge 30$ orders) based on seller-caused delay exposure:

| Priority Tier | Seller Count | % Seller Base | Order Volume* | GMV (R$) | Seller Late Exp (R$) | % Platform Seller Exp | Late Mitigation (Base 25%) | Recommended Operational Action |
|---|---|---|---|---|---|---|---|---|
| **P1 — Immediate Intervention** | **113** | **3.65%** | 20,576 | R$ 2.79M | **R$ 181,377.55** | **48.85%** | **R$ 45,344.39** | Mandatory 24–48hr dispatch SLA, dynamic EDD recalibration |
| **P2 — Operational Investigation** | 211 | 6.82% | 33,823 | R$ 3.72M | R$ 54,637.04 | 14.72% | R$ 13,659.26 | Carrier dispatch inspection, packaging dimension audit |
| **P3 — Operational Monitoring** | 323 | 10.44% | 29,095 | R$ 3.98M | R$ 39,267.34 | 10.58% | R$ 9,816.84 | Automated dashboard threshold alerts; 30-day monitoring |
| **P4 — Low Volume / Not Prioritised** | 2,448 | 79.10% | 16,516 | R$ 3.10M | R$ 95,999.21 | 25.86% | R$ 23,999.80 | Standard commercial governance; volume threshold qualification |

*\*Order volumes represent seller-order engagements across tiers (multi-seller orders mapped to each seller).*  
*Volume Cutoff Sensitivity:* Testing alternative volume cutoffs demonstrates stability:
- $N \ge 20$: 150 P1 sellers (R$ 204,479.66 seller late exposure)
- $N \ge 30$ (Base): 113 P1 sellers (R$ 181,377.55 seller late exposure)
- $N \ge 50$: 69 P1 sellers (R$ 145,544.23 seller late exposure)  
The core 69 high-exposure sellers are captured across all thresholds, confirming that the core P1 sellers do not depend on the exact volume cutoff.

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

---

### 5. Quantified Economic Impact & Scenario-Based Mitigation

We distinguish strictly between **observable late-order metrics** and **illustrative scenario-based mitigation models (assumed rates, not measured)**:
- **Observable Platform Late Exposure ($E_{late}$):** R$ 985,924.34 (GMV) + R$ 164,967.79 (Freight) = **R$ 1,150,892.13** (8.47% of platform gross flow).
  - Seller-Caused Late Exposure: **R$ 371,281.14** (32.26%)
  - Post-Handover-Delay Late Exposure: **R$ 779,610.99** (67.74%)
- **P1 Seller Mitigation Modeling (113 Sellers, R$ 181,377.55 Seller Exposure):**
  - **Conservative Scenario (10% Mitigation):** **R$ 18,137.76**
  - **Base Case Scenario (25% Mitigation):** **R$ 45,344.39**
  - **Optimistic Scenario (40% Mitigation):** **R$ 72,551.02**

---

### 6. Operational Recommendations for Leadership

1. **Deploy Dedicated Partner Operations to P1 Cohort (Immediate):** Assign partner managers to the 113 high-exposure sellers to enforce mandatory 24–48hr carrier dispatch SLAs, dynamic Estimated Delivery Date (EDD) lead-time adjustments in checkout algorithms, and inventory staging audits.
2. **Restructure Bulky Category Shipping Policies:** For structurally freight-heavy categories (`furniture_decor`, `office_furniture`), eliminate subsidized flat rates and introduce volumetric freight tiers or mandatory regional fulfillment.
3. **Corridor Optimization on SP $\to$ RJ/BA:** Because 72.25% of late (order, seller) pairs were delayed after handover, seller SLAs alone cannot solve regional failure. The data cannot show which party causes the extra transit, so first review post-handover transit times with the carriers on these lanes, then pilot regional consolidation for São Paulo sellers shipping into Rio de Janeiro and the Northeast before committing to sorting hubs.
4. **Automated Governance Alerts:** Implement automated SLA warnings in the seller portal when a merchant's rolling 30-day seller dispatch delay rate exceeds 12%.

---

### 7. Methodological Governance & Limitations

1. **Date-Level Precision:** Lateness is evaluated strictly at calendar date granularity, eliminating the midnight-boundary distortion that previously misclassified 1,292 same-day on-time deliveries as late.
2. **Pure Observational Diagnostics:** Zero fabricated profit metrics or unobserved platform overheads. All metrics reconcile to the penny against DuckDB fact tables.
3. **Post-Handover Visibility Limitation:** Public dataset lacks intermediate sorting hub scans or first-attempt delivery timestamps, and the second gate is the platform's promised date, not a carrier SLA. All post-handover transit calculations reflect handover-to-doorstep duration, so they cannot attribute the delay to the carrier, last-mile or customer availability.
