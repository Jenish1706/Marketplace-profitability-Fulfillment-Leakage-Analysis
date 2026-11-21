# 04: Evaluation Protocol, Metrics & Falsification Criteria

**Project:** Marketplace Profitability & Fulfillment Leakage Analysis  
**Author:** Jenish Patel  
**Purpose:** Rigorous documentation of experimental windows, metric definitions, statistical justifications, control variables, and falsification criteria.

---

## 1. Evaluation Protocol & Temporal Windows

The analytical methodology divides the dataset into distinct observational windows to prevent look-ahead bias and validate persistence:

1. **Full Platform Historical Baseline (Sep 2016 – Oct 2018):**
   - Population: 99,441 orders (112,650 line items).
   - Used for: Overall platform volume reconciliation, star-schema data export, and core fact table definitions.
2. **Longitudinal Active Operating Window (Jan 2017 – Aug 2018):**
   - Population: 20 consecutive calendar months.
   - Used for: Macro-inflection time series (`view_macro_kpi_monthly`), seasonal strain identification (e.g. Black Friday 2017 vs March 2018 breakdown), and rolling volume trends.
3. **Temporal Holdout Persistence Split (2017 $\to$ 2018):**
   - **Training / Selection Window (2017):** Merchants evaluated solely on 2017 transactions to assign initial P1 priority tier.
   - **Evaluation / Holdout Window (2018):** Tracks the 2018 fulfillment performance of active 2017 P1 merchants without re-fitting tiers.
   - Cohort rule: the identical tier rule as the headline (`view_seller_tiers_by_period`, period 2017), not a separate copy.
   - Purpose: Measure how much of the P1 seller-caused excess carries over to a later year, with seller-level bootstrap intervals (guide 09). Shrinkage is expected from selecting on a high year (regression to the mean), so it is not by itself evidence of improvement or of a fixed seller trait.

---

## 2. Core Metrics & Mathematical Definitions

All metric formulas are implemented strictly in DuckDB SQL:

| Metric Name | Mathematical Definition | Physical Business Meaning |
|---|---|---|
| **Date-Level Late Delivery Flag** | $\mathbb{I}(\text{CAST}(t_{\text{delivered}} \text{ AS DATE}) > \text{CAST}(t_{\text{estimated}} \text{ AS DATE}))$ | Binary indicator that package breached the promised calendar date. |
| **Late Delivery Rate (%)** | $\frac{\sum \text{is\_late}}{\sum \mathbb{I}(\text{status} = \text{'delivered'})} \times 100$ | Baseline platform delivery failure frequency (6.77%). |
| **Freight Burden (%)** | $\frac{\sum \text{freight\_value}}{\sum \text{price}} \times 100$ | Proportion of customer merchandise value consumed by shipping charges (16.57%). |
| **Seller Late Dispatch Flag** | $\mathbb{I}(t_{\text{carrier\_handover}} > t_{\text{shipping\_limit}})$ | Binary indicator that seller missed contractual carrier handover deadline. |
| **Seller-Caused Late Flag** | $\mathbb{I}(\text{is\_late} = 1 \land \text{is\_seller\_late\_dispatch} = 1)$ | Delivery was late AND seller missed dispatch SLA. |
| **Post-Handover Late Flag** (`is_carrier_caused_late`; the identifier is kept for compatibility) | $\mathbb{I}(\text{is\_late} = 1 \land \text{is\_seller\_late\_dispatch} = 0)$ | Delivery was late DESPITE seller dispatching on time, so the delay arose after handover. The second gate is the platform's promised date, not a carrier SLA, and the party responsible is not observable. |
| **Observable Late-Order GMV** | $\sum_{\text{is\_late} = 1} \text{price}$ | Total merchandise value of orders that arrived late (R\$ 985,924.34). |
| **Observable Late-Order Freight** | $\sum_{\text{is\_late} = 1} \text{freight\_value}$ | Total freight charges paid on orders that arrived late (R\$ 164,967.79). |
| **Late-Order Total Value ($E_{\text{late}}$)** | $\text{Late GMV} + \text{Late Freight}$ | Observable gross transaction flow of late orders (R\$ 1,150,892.13). |
| **Concentration Lift** | $\frac{\text{Exposure Share}_{\text{Decile}}}{\text{GMV Share}_{\text{Decile}}}$ | Excess operational failure generated per real of revenue (1.27× for Decile 1). |
| **Illustrative Mitigation** | $\alpha \times \sum_{s \in \text{P1}} \text{Seller-Caused Late Exposure}_s$ | Modeled addressable exposure under assumed operational improvement rate $\alpha \in \{10\%, 25\%, 40\%\}$. |

---

## 3. Statistical Tests & Methodological Rationale

### 1. Kruskal-Wallis $H$-Test
- **Hypothesis:** $H_0$: Customer review score distributions are identical across delay cohorts ($\le 0$ days, 1–2 days, 3–5 days, $>5$ days).
- **Why this test?** Review scores are discrete ordinal integers ($1$ to $5$), heavily skewed towards 5 stars with a secondary mode at 1 star. Ordinary ANOVA assumes Gaussian normality and homoskedasticity, which are severely violated ($p < 10^{-50}$ on Shapiro-Wilk and Levene tests). Kruskal-Wallis relies strictly on ranked sums.
- **Result:** $H = 10,167.48, p < 10^{-15}$. Reject $H_0$.

### 2. Mann-Whitney $U$-Test with Rank-Biserial Effect Size ($r$)
- **Hypothesis:** $H_0$: Ratings for severely delayed orders ($>5$ days late) have equal distribution to on-time orders.
- **Why this test?** Pairwise non-parametric evaluation. While $p$-values confirm statistical significance on large samples ($N > 90,000$), the rank-biserial correlation $r = 1 - \frac{2U}{n_1 n_2}$ quantifies physical effect size.
- **Result:** $U = 4,213,920, p < 10^{-15}, r = -0.781$. Confirms strong negative association.

### 3. Logistic Regression with Cluster-Robust Standard Errors
- **Specification:**
  $$\ln\left(\frac{p_i}{1 - p_i}\right) = \beta_0 + \beta_1 X_{1i} + \dots + \beta_k X_{ki}$$
  where $Y_i = \mathbb{I}(\text{review\_score}_i \le 2)$.
- **Why Cluster-Robust SEs on `seller_id`?**
  Transactions from the same merchant share operational procedures, packing materials, and handling speeds. Treating individual shipments as independent inflates sample size and deflates standard errors. We use the Liang-Zeger sandwich estimator clustered at the merchant level ($G = 2,953$ independent clusters), which satisfies asymptotic cluster-balance requirements.
- **Sensitivity Checks:** We compare `seller_id` standard errors against `seller_state` ($G = 27$, unbalanced) and `HC1` (heteroskedasticity-robust).

---

## 4. Model Specifications & Controlled Covariates

To isolate fulfillment impact from commercial pricing characteristics, regressions incorporate standard economic controls:
- **`ln_price`:** $\ln(\text{price})$. Controls for customer value expectations (higher-priced items carry higher quality standards).
- **`freight_ratio`:** $\text{freight\_value} / \text{price}$. Controls for customer price-to-shipping resentment (high shipping charges relative to item cost induce dissatisfaction).

### Information-Set Model Formulation:
- **Model A (Conventional):** Uses non-negative late days at final delivery: $\text{delay\_days\_late} = \max(0, \text{delivery\_delay\_days})$.
- **Model B (Customer Information Set):** Conditions on variables observable to the customer when submitting the survey:
  - $\text{undelivered\_at\_review} = \mathbb{I}(t_{\text{review}} < t_{\text{delivery}})$
  - $\text{days\_overdue\_at\_review} = \max(0, \text{DateDiff}(t_{\text{estimated}}, t_{\text{review}}))$

---

## 5. Explicit Falsification Criteria

To maintain scientific integrity, every core finding in this repository is paired with an explicit falsification condition:

| Finding / Claim | Core Claim | What Would Falsify This Claim? |
|---|---|---|
| **Falsification 1: Date-Level SLA Baseline** | Platform late delivery rate is 6.77% (6,534 orders). | Finding that calendar date casting misclassifies legitimate courier delivery cutoffs, or finding timestamp-level delivery receipts that prove after-hours delivery failure on the promised date. |
| **Falsification 2: Seller vs Post-Handover Attribution** | 72.25% of late (order, seller) pairs were handed over by the shipping limit, so the delay arose after handover. | (a) Late pairs having normal transit but shorter promises (promise-setting); (b) sellers recording handover before the parcel physically left (manifest pre-scanning), shifting dispatch delay into transit. Result (guide 09): (a) is rejected, since late pairs spent far longer in transit than on-time pairs on the same corridor while their promises were only slightly shorter; (b) cannot be tested without carrier scans. |
| **Falsification 3: Pareto Concentration Lift** | Decile 1 sellers produce 1.27× excess late exposure relative to GMV share. | Finding that Decile 1 exposure share drops to or below its GMV share ($60.78\%$) when controlling for product category mix or order item counts. |
| **Falsification 4: Temporal Persistence** | The seller-caused excess of 2017 P1 sellers carries over to 2018. | Finding that the 2018 seller-caused gap between 2017 P1 sellers and other sellers has a bootstrap interval that includes zero. Result (guide 09): the gap shrinks but its interval stays above zero, so the claim survives in weakened form (some persistence, not a fixed seller trait). |
| **Falsification 5: Review Survey Confounder** | Dissatisfaction is driven by binary non-receipt ($OR = 33.63\times$), not marginal delay days. | Finding that after controlling for automated email timing, the coefficient on marginal overdue days remains large, positive, and statistically significant ($\beta > 0.10, p < 0.01$). |
| **Falsification 6: P1 Economic Framing** | Addressable P1 exposure is R\$ 45,344.39 under an assumed 25% mitigation scenario. | Claiming that R\$ 45,344.39 is "recovered cash", which would be falsified by the fact that historical Kaggle data cannot execute live interventions or collect incremental cash. |
