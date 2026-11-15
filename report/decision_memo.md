# Executive Decision Memorandum

**TO:** Chief Operating Officer (COO), VP of Marketplace Operations  
**FROM:** Marketplace Commercial & Operational Analytics  
**DATE:** September 10, 2026  
**SUBJECT:** Operational Diagnostic & Priority Intervention Strategy: Recovering Fulfillment Leakage  

---

### 1. Executive Summary

Between January 2017 and August 2018, the marketplace achieved strong commercial scale: **Gross Merchandise Value (GMV)** expanded from R$120K to ~R$1M monthly, processing **99,441 total orders** (96,478 delivered) and generating **R$ 13.59M in cumulative GMV**. However, this top-line expansion masked severe operational friction and unit-economic compression:
1. **Fulfillment Deterioration Spikes:** Platform late delivery rates surged during high-volume periods, spiking to **14.31%** during Black Friday 2017 and collapsing to **21.36% in March 2018** (over 1 in 5 orders delivered late).
2. **Structural Logistics Cost Inflation:** Overall platform freight burden increased from **14.03%** in early 2017 to over **18.2%** by mid-2018, eroding contribution economics.
3. **Severe Exposure Concentration:** Operational failure is concentrated in high-volume merchants. **Decile 1 (top 10% of sellers, 310 sellers) accounts for 61.27% of GMV and 75.83% of total late-order transaction exposure (1.24× lift)**.
4. **Targeted Operational Mitigation:** By decoupling operational failure rate from economic scale, we identify a prioritized cohort of **83 Priority 1 (P1) sellers** representing **R$ 377,768.41 in late transaction exposure** (pending Stage A date-level recalculation). Under our Base Case scenario (25% operational mitigation), targeted operations management addresses **R$ 94,442.10 in late-order GMV exposure**.

---

### 2. Macro Performance Inflection & Diagnostic Evidence

Longitudinal analysis demonstrates that platform logistics networks strained under peak commercial throughput:
- **Nov 2017 (Black Friday):** Orders jumped +63% month-over-month (to 7,544 orders), driving late delivery rates to 14.31% and late transaction exposure to R$ 168.9K in a single month.
- **Q1 2018 Logistics Breakdown:** In February and March 2018, late delivery rates remained persistently elevated at **15.99%** and **21.36%**, with average delays for late shipments exceeding **+8.8 days** beyond estimated delivery dates.
- **Customer Satisfaction Impact:** Econometric and non-parametric analysis confirms degradation in customer ratings. Average review scores for on-time deliveries average **4.29 / 5.00** (6.6% low reviews), but drop to **2.47** for orders delayed 3–5 days (48.4% low reviews) and **1.74** for orders delayed >5 days (68.6% low reviews). However, 70.2% of reviews on late orders were submitted prior to package delivery, reflecting arrival-prompt survey responses upon promised date breach rather than post-delivery satisfaction. Kruskal-Wallis test ($H = 10,316.6, p < 10^{-15}$) and rank-biserial effect sizes ($r = -0.76$) confirm strong conditional association between delay and negative review score.

---

### 3. Root-Cause Decomposition

Fulfillment leakage is driven by three distinct operational mechanisms:
1. **Seller Volume vs Severity Decoupling:** Uncontrolled rankings mistake low-volume noise for business liability. Sellers with 100% late delivery rates on 2 orders generate negligible impact (R$ 72 exposure). Conversely, high-volume operational sellers (e.g., Seller `4a3ca93a...`, 1,806 orders, 16.0% late rate) generate **R$ 29,420.57 in late exposure** alone.
2. **Category Structural Deficits:** Categories such as `furniture_decor`, `office_furniture`, and `bed_bath_table` exhibit heavy physical profiles (average volume >25,000 cm³, weight >3 kg) driving structural freight burdens of **25% to 35%**, severely penalizing basket economics.
3. **Cross-Regional Bottlenecks:** Intra-state deliveries within São Paulo (SP $\to$ SP) operate efficiently (freight burden ~12%, late rate ~5.5%). However, long-haul interstate corridors (SP $\to$ RJ, SP $\to$ BA, SP $\to$ MG) account for the bulk of platform delay, with SP $\to$ RJ generating **R$ 138K in late transaction exposure** with an 11.2% late delivery rate.

---

### 4. Intervention Prioritization Framework

Rather than arbitrary weighted scoring, sellers are classified into deterministic tiers using percentile cutoffs applied to qualified operational sellers ($N \ge 30$ orders):

| Priority Tier | Seller Count | % Seller Base | Order Volume* | GMV (R$) | Late-Order Exposure (R$) | % Platform Late Exp | Recommended Operational Action |
|---|---|---|---|---|---|---|---|
| **P1 — Immediate Intervention** | **83** | **2.68%** | 19,046 | R$ 2.35M | **R$ 377,768.41** | **27.95%** | Lead-time calibration, packaging audit, carrier handoff inspection |
| **P2 — Operational Investigation** | 272 | 8.79% | 43,025 | R$ 5.30M | R$ 504,623.53 | 37.33% | Carrier dispatch inspection, lane-level logistics routing review |
| **P3 — Operational Monitoring** | 149 | 4.81% | 10,962 | R$ 1.55M | R$ 153,332.79 | 11.34% | Automated dashboard threshold alerts; 30-day monitoring |
| **P4 — Low Volume / Standard Governance** | 2,591 | 83.72% | 26,977 | R$ 4.39M | R$ 315,900.23 | 23.37% | Routine commercial governance; standard SLA adherence |

*\*Order volumes represent seller-order engagements across tiers (multi-seller orders mapped to each seller).*  
*Volume Cutoff Sensitivity:* Testing alternative volume cutoffs demonstrates stability: $N \ge 20$ yields 104 P1 sellers (R$ 415.6K exposure), while $N \ge 50$ yields 51 P1 sellers (R$ 314.4K exposure). The $N \ge 30$ baseline captures 83 sellers controlling 28% of platform late exposure (pending Stage A date-level recalculation).

---

### 5. Quantified Economic Impact & Scenario-Based Mitigation

We distinguish strictly between **observable transaction exposure** and **scenario-based mitigation models**:
- **Observable Platform Late Exposure ($E_{late}$):** R$ 1,158,920.51 (GMV) + R$ 192,704.45 (Freight) = **R$ 1,351,624.96** (pending Stage A date-level recalculation).
- **P1 Mitigation Modeling (83 Sellers):**
  - **Conservative Scenario (10% Mitigation):** **R$ 37,776.84**
  - **Base Case Scenario (25% Mitigation):** **R$ 94,442.10**
  - **Optimistic Scenario (40% Mitigation):** **R$ 151,107.36**

---

### 6. Operational Recommendations for Leadership

1. **Deploy Dedicated Partner Operations to P1 Cohort (Immediate):** Assign partner managers to high-exposure sellers to audit seller-to-carrier handoff lead-times, evaluate carrier transit times, and recalibrate platform estimated delivery dates (EDDs).
2. **Restructure Bulky Category Shipping Policies:** For structurally freight-heavy categories (`furniture_decor`, `bed_bath_table`), eliminate subsidized flat rates and introduce volumetric freight tiers or mandatory seller-fulfilled delivery.
3. **Corridor Optimization on SP $\to$ RJ/BA:** Establish regional 3PL line-haul consolidation for São Paulo sellers shipping into Rio de Janeiro and the Northeast, replacing standard postal routing with dedicated hub transit.
4. **Automated Governance Alerts:** Implement automated SLA warnings in the seller portal when a seller's rolling 30-day late dispatch rate exceeds 12%.

---

### 7. Methodological Governance & Limitations

- **No Unobserved Profit Claims:** The dataset records item prices, freight values, and delivery timestamps, but excludes seller commission rates, payment gateway fees, carrier contract settlements, and return processing overheads. Therefore, metrics are strictly designated as *Transaction Exposure* and *Cost Burden*, never fabricated actual net profit.
- **Observational Nature:** Regression models indicate strong conditional associations between delivery delay and customer review scores, but do not imply experimental causality. Confounders (seller quality, product packaging) are controlled where observable.
