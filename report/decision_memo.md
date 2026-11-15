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
3. **Severe Exposure Concentration:** Operational failure is concentrated in high-volume merchants. **Decile 1 (top 10% of sellers, 310 sellers) accounts for 60.78% of GMV and 77.38% of total late-order transaction exposure (1.27× lift)**.
4. **Targeted Operational Mitigation:** By decoupling seller dispatch delays from carrier transit delays, we identify a prioritized cohort of **113 Priority 1 (P1) sellers** representing **R$ 181,377.55 in seller-caused late exposure** (48.85% of platform seller-caused exposure). Under our Base Case scenario (25% operational mitigation), targeted operations management addresses **R$ 45,344.39 in addressable late-order GMV exposure**.

---

### 2. Macro Performance Inflection & Diagnostic Evidence

Longitudinal analysis demonstrates that platform logistics networks strained under peak commercial throughput:
- **Nov 2017 (Black Friday):** Orders jumped +63% month-over-month (to 7,544 orders), driving late delivery rates to 12.40% and late transaction exposure to R$ 143.8K in a single month.
- **Q1 2018 Logistics Breakdown:** In February and March 2018, late delivery rates remained persistently elevated at **14.13%** and **18.96%**, with average delays for late shipments exceeding **+8.8 days** beyond estimated delivery dates.
- **Customer Satisfaction Impact:** Econometric and non-parametric analysis confirms severe degradation in customer ratings. Average review scores for on-time deliveries average **4.29 / 5.00** (9.2% low reviews $\le 2$ stars), but drop to **2.47** for orders delayed 3–5 days (56.7% low reviews) and **1.74** for orders delayed >5 days (78.1% low reviews). 
- **Review Timing Confounder (P0-3):** Among late orders, **70.10%** of customer reviews were submitted *before* package arrival (evaluating an order that was on average 3.73 days overdue at survey response, vs 13.82 days overdue at final delivery).
- **Statistical Significance & Econometrics:** Kruskal-Wallis test ($H = 10,167.48, p < 10^{-15}$) and rank-biserial effect sizes ($r = -0.781$) confirm strong negative association between delay and review scores. Logistic regression with cluster-robust standard errors yields an odds ratio of **1.229 per late day** ($p < 0.001$, $\beta = 0.2060$) in the conventional model. When conditioning on the customer's information set at review time, the **binary unarrived state dominates** ($\text{OR} = 33.63\times, p < 10^{-15}$, $\beta = 3.5153$; OLS $\beta = -2.5125$ stars), proving that customer dissatisfaction is driven by breach of the delivery promise window rather than linear daily decay.

---

### 3. Root-Cause Decomposition

Fulfillment leakage is driven by three distinct operational mechanisms:
1. **Seller Volume vs Severity Decoupling:** Uncontrolled rankings mistake low-volume noise for business liability. Sellers with 100% late delivery rates on 2 orders generate negligible impact (R$ 72 exposure). Conversely, high-volume operational sellers (e.g., Seller `4a3ca93a...`, 1,806 orders, 16.0% late rate) generate **R$ 29,420.57 in late exposure** alone.
2. **Seller vs Carrier Delay Attribution:** In **72.25% of late orders** (4,730 of 6,547 orders), the merchant handed over to the carrier on or before `shipping_limit_date`. Platform late exposure is dominated by carrier transit delays (R$ 779,610.99, 67.74%), while seller dispatch breaches account for R$ 371,281.14 (32.26%).
3. **Category Structural Deficits:** Categories such as `furniture_decor`, `office_furniture`, and `bed_bath_table` exhibit heavy physical profiles (average volume >25,000 cm³, weight >3 kg) driving structural freight burdens of **20% to 25%**, severely penalizing basket economics.
4. **Cross-Regional Bottlenecks:** Intra-state deliveries within São Paulo (SP $\to$ SP) operate efficiently (freight burden 13.21%, late rate 6.10%). However, long-haul interstate corridors (SP $\to$ RJ, SP $\to$ BA, SP $\to$ MG) account for the bulk of platform delay, with SP $\to$ RJ generating **R$ 197K in late transaction exposure** with a 14.85% late delivery rate.

---

### 4. Intervention Prioritization Framework

Rather than arbitrary weighted scoring, sellers are classified into deterministic tiers using percentile cutoffs applied to qualified operational sellers ($N \ge 30$ orders) based on seller-caused delay exposure:

| Priority Tier | Seller Count | % Seller Base | Order Volume* | GMV (R$) | Seller Late Exp (R$) | % Platform Seller Exp | Late Mitigation (Base 25%) | Recommended Operational Action |
|---|---|---|---|---|---|---|---|---|
| **P1 — Immediate Intervention** | **113** | **3.65%** | 20,576 | R$ 2.79M | **R$ 181,377.55** | **48.85%** | **R$ 45,344.39** | Mandatory 24–48hr dispatch SLA, dynamic EDD recalibration |
| **P2 — Operational Investigation** | 211 | 6.82% | 33,823 | R$ 3.72M | R$ 54,637.04 | 14.72% | R$ 13,659.26 | Carrier dispatch inspection, packaging dimension audit |
| **P3 — Operational Monitoring** | 323 | 10.44% | 29,095 | R$ 3.98M | R$ 39,267.34 | 10.58% | R$ 9,816.84 | Automated dashboard threshold alerts; 30-day monitoring |
| **P4 — Low Volume / Standard Governance** | 2,448 | 79.10% | 16,516 | R$ 3.10M | R$ 95,999.21 | 25.86% | R$ 23,999.80 | Standard commercial governance; volume threshold qualification |

*\*Order volumes represent seller-order engagements across tiers (multi-seller orders mapped to each seller).*  
*Volume Cutoff Sensitivity:* Testing alternative volume cutoffs demonstrates stability:
- $N \ge 20$: 150 P1 sellers (R$ 204,479.66 seller late exposure)
- $N \ge 30$ (Base): 113 P1 sellers (R$ 181,377.55 seller late exposure)
- $N \ge 50$: 69 P1 sellers (R$ 145,544.23 seller late exposure)  
The core 69 high-exposure sellers are captured across all thresholds, confirming that P1 captures structural operational liabilities rather than boundary noise.

---

### 5. Quantified Economic Impact & Scenario-Based Mitigation

We distinguish strictly between **observable transaction exposure** and **scenario-based mitigation models**:
- **Observable Platform Late Exposure ($E_{late}$):** R$ 985,924.34 (GMV) + R$ 164,967.79 (Freight) = **R$ 1,150,892.13** (8.47% of platform gross flow).
  - Seller-Caused Late Exposure: **R$ 371,281.14** (32.26%)
  - Carrier-Caused Late Exposure: **R$ 779,610.99** (67.74%)
- **P1 Seller Mitigation Modeling (113 Sellers, R$ 181,377.55 Seller Exposure):**
  - **Conservative Scenario (10% Mitigation):** **R$ 18,137.76**
  - **Base Case Scenario (25% Mitigation):** **R$ 45,344.39**
  - **Optimistic Scenario (40% Mitigation):** **R$ 72,551.02**

---

### 6. Operational Recommendations for Leadership

1. **Deploy Dedicated Partner Operations to P1 Cohort (Immediate):** Assign partner managers to the 113 high-exposure sellers to enforce mandatory 24–48hr carrier dispatch SLAs, dynamic Estimated Delivery Date (EDD) lead-time adjustments in checkout algorithms, and inventory staging audits.
2. **Restructure Bulky Category Shipping Policies:** For structurally freight-heavy categories (`furniture_decor`, `office_furniture`), eliminate subsidized flat rates and introduce volumetric freight tiers or mandatory regional fulfillment.
3. **Corridor Optimization on SP $\to$ RJ/BA:** Because 72.25% of delay items are carrier-transit delays, seller SLAs alone cannot solve regional failure. Establish regional sorting hubs and multi-carrier 3PL line-haul consolidation for São Paulo sellers shipping into Rio de Janeiro and the Northeast.
4. **Automated Governance Alerts:** Implement automated SLA warnings in the seller portal when a merchant's rolling 30-day seller dispatch delay rate exceeds 12%.

---

### 7. Methodological Governance & Limitations

1. **Date-Level Precision:** Lateness is evaluated strictly at calendar date granularity, eliminating the midnight-boundary distortion that previously misclassified 1,292 same-day on-time deliveries as late.
2. **Pure Observational Diagnostics:** Zero fabricated profit metrics or unobserved platform overheads. All metrics reconcile to the penny against DuckDB fact tables.
3. **Carrier Visibility Limitation:** Public dataset lacks intermediate sorting hub scans or first-attempt delivery timestamps. All carrier transit calculations reflect dock-to-doorstep duration.
