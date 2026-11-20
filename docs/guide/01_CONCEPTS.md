# 01: Core Concepts & Mathematical Formulations

**Project:** Marketplace Profitability & Fulfillment Leakage Analysis  
**Author:** Jenish Patel  
**Purpose:** Foundational reference covering every statistical, econometric, and data engineering concept used in this repository.

---

## Table of Contents
1. [Analytical Grain & Fan-Out Prevention](#1-analytical-grain--fan-out-prevention)
2. [Window Functions & Cumulative Aggregations](#2-window-functions--cumulative-aggregations)
3. [Percentile Tiers & Pareto Concentration Lift](#3-percentile-tiers--pareto-concentration-lift)
4. [Kruskal–Wallis & Mann–Whitney U Tests (with Rank-Biserial Effect Size)](#4-kruskalwallis--mannwhitney-u-tests-with-rank-biserial-effect-size)
5. [Logistic Regression Odds Ratios & Cluster-Robust Standard Errors](#5-logistic-regression-odds-ratios--cluster-robust-standard-errors)
6. [Association vs Causation, Confounders vs Mediators](#6-association-vs-causation-confounders-vs-mediators)
7. [Review-Timing Information Sets](#7-review-timing-information-sets)
8. [Right-Censoring & Survivorship Bias](#8-right-censoring--survivorship-bias)

---

## 1. Analytical Grain & Fan-Out Prevention

### Intuition
In a relational database, an entity often has a one-to-many relationship with subordinate events. For example, a single customer order may contain three items, be paid using two separate vouchers, and have two customer review submissions. If you perform a naive relational join across these tables simultaneously, the resulting row count is the Cartesian product of the branches: $1 \times 3 \times 2 \times 2 = 12$ rows! Summing price or payment values across that naive join multiplies the true financial amounts, generating an artificial data artifact known as **fan-out duplication**.

### Mathematical Formulation
Let an order $i$ have set of items $I_i$, set of payments $P_i$, and set of reviews $R_i$.
A naive join yields a relation whose row count for order $i$ is:
$$\text{Rows}_i = |I_i| \times |P_i| \times |R_i|$$

The naive sum of item prices $\tilde{S}_{\text{GMV}}$ over-counts the true GMV:
$$\tilde{S}_{\text{GMV}} = \sum_{i} \sum_{j \in I_i} \text{price}_{ij} \cdot (|P_i| \times |R_i|)$$
Which equals the true GMV $S_{\text{GMV}} = \sum_{i} \sum_{j \in I_i} \text{price}_{ij}$ if and only if $|P_i| = 1$ and $|R_i| = 1$ for all orders. When $|P_i| > 1$, metrics are corrupted.

### Tiny Worked Example
Consider Order `ORD-101`:
- 2 items: Item 1 = R\$ 100.00, Item 2 = R\$ 50.00. (True GMV = R\$ 150.00)
- 2 payment methods: Credit Card = R\$ 100.00, Voucher = R\$ 50.00.
- Naive join produces $2 \times 2 = 4$ rows:
  - Row 1: Item 1 (R\$ 100), Payment 1 (R\$ 100)
  - Row 2: Item 1 (R\$ 100), Payment 2 (R\$ 50)
  - Row 3: Item 2 (R\$ 50), Payment 1 (R\$ 100)
  - Row 4: Item 2 (R\$ 50), Payment 2 (R\$ 50)
- Sum of item price in naive join: $100 + 100 + 50 + 50 = \text{R\$} 300.00$ (**200% of true GMV!**).
- Sum of payment value in naive join: $100 + 50 + 100 + 50 = \text{R\$} 300.00$ (**200% of true payment value!**).

### Implementation Link
- Implemented in [`sql/03_order_item_fact.sql`](../../sql/03_order_item_fact.sql#L10-L65) using CTEs `int_order_payments_rollup` and `int_order_reviews_dedup` to pre-aggregate payments and reviews to the `order_id` grain *prior* to joining onto `olist_order_items`.

---

## 2. Window Functions & Cumulative Aggregations

### Intuition
Standard SQL `GROUP BY` collapses individual records into a single summary row per group. In contrast, a **window function** evaluates an aggregate or ranking calculation across a defined set of rows related to the current row without collapsing the rows. This enables calculations of cumulative running totals, decile segmentations, and order ranks alongside granular row-level data.

### Mathematical Formulation
For a metric $x_k$ ordered descending across $N$ entities ($k = 1, \dots, N$ where $x_1 \ge x_2 \ge \dots \ge x_N$):
$$\text{Cumulative Sum}_k = \sum_{j=1}^{k} x_j$$
$$\text{Cumulative Share}_k = \frac{\sum_{j=1}^{k} x_j}{\sum_{j=1}^{N} x_j}$$
For decile binning ($D \in \{1, \dots, 10\}$):
$$\text{Decile}_k = \left\lceil \frac{k \cdot 10}{N} \right\rceil$$

### Tiny Worked Example
Suppose 4 sellers have late-order exposure:
- Seller A: R\$ 500
- Seller B: R\$ 300
- Seller C: R\$ 150
- Seller D: R\$ 50
- Total Exposure = R\$ 1,000.

| Seller | Exposure | Window Running Total (`SUM() OVER`) | Window Cumulative Share | Decile / NTILE(2) |
|---|---|---|---|---|
| A | R\$ 500 | R\$ 500 | 50.0% | 1 |
| B | R\$ 300 | R\$ 800 | 80.0% | 1 |
| C | R\$ 150 | R\$ 950 | 95.0% | 2 |
| D | R\$ 50 | R\$ 1,000 | 100.0% | 2 |

### Implementation Link
- Implemented in [`sql/06_pareto_analysis.sql`](../../sql/06_pareto_analysis.sql#L15-L48) using `NTILE(10) OVER (ORDER BY total_exposure_late DESC)` and `SUM(total_exposure_late) OVER (ORDER BY total_exposure_late DESC ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)`.

---

## 3. Percentile Tiers & Pareto Concentration Lift

### Intuition
In e-commerce, commercial volume naturally follows a power-law distribution (Pareto principle: 80% of sales come from 20% of sellers). If a dashboard announces that "Top 10% of sellers cause 75% of late delivery exposure", that statistic may simply reflect that those same sellers generate 75% of all orders. 
To prove that high-volume merchants represent a true operational dysfunction rather than just scale, we must calculate the **Pareto concentration lift** (or simply **Pareto lift**): the ratio of exposure share to commercial GMV share.

### Mathematical Formulation
For merchant decile $d$:
$$\text{Exposure Share}_d = \frac{\sum_{s \in d} \text{Late Exposure}_s}{\sum_{\text{all } s} \text{Late Exposure}_s}$$
$$\text{GMV Share}_d = \frac{\sum_{s \in d} \text{GMV}_s}{\sum_{\text{all } s} \text{GMV}_s}$$
$$\text{Concentration Lift}_d = \frac{\text{Exposure Share}_d}{\text{GMV Share}_d}$$
- If $\text{Lift} = 1.0$: Operational failure perfectly mirrors revenue (no excess risk).
- If $\text{Lift} > 1.0$: The cohort generates disproportionate fulfillment failure per real of merchandise sold.

For multi-criteria intervention tiering:
$$\text{Percent Rank}(s) = \frac{\text{Rank}(s) - 1}{N - 1}$$
Sellers qualified with $N \ge 30$ orders are placed into Priority 1 (P1) if their seller-caused exposure and failure severity exceed the 75th percentile ($> 0.75$).

### Tiny Worked Example
In Olist Decile 1 (top 10% sellers by exposure, 310 merchants):
- Total GMV = R\$ 8.26M of R\$ 13.59M platform GMV $\implies \text{GMV Share} = 60.78\%$.
- Total Late Exposure = R\$ 890.6K of R\$ 1.15M platform late value $\implies \text{Exposure Share} = 77.38\%$.
- Concentration Lift:
  $$\text{Lift} = \frac{77.38\%}{60.78\%} = 1.273\times$$
Interpretation: Decile 1 merchants produce **27.3% more fulfillment failure per dollar of GMV** than the platform average.

### Implementation Link
- Implemented in [`sql/06_pareto_analysis.sql`](../../sql/06_pareto_analysis.sql#L45-L65) and [`sql/07_intervention_priority.sql`](../../sql/07_intervention_priority.sql#L20-L75).

---

## 4. Kruskal–Wallis & Mann–Whitney U Tests (with Rank-Biserial Effect Size)

### Intuition
Customer review ratings are ordinal discrete values ($1, 2, 3, 4, 5$), not unbounded Gaussian distributions. Parametric tests (such as Student's t-test or ANOVA) assume normality and equal variance, which are severely violated by review scores (bimodal distribution clustered at 1-star and 5-stars). Non-parametric rank tests evaluate whether groups originate from the same distribution without assuming normality.

### Mathematical Formulation
**1. Kruskal-Wallis $H$-Test:**
Tests the null hypothesis that $k$ independent groups have equal medians.
$$H = \frac{12}{N(N+1)} \sum_{j=1}^{k} \frac{R_j^2}{n_j} - 3(N+1)$$
where $N = \sum n_j$, $n_j$ is sample size of group $j$, and $R_j$ is the sum of ranks for group $j$. Under $H_0$, $H$ is asymptotically distributed as $\chi^2(k - 1)$.

**2. Mann-Whitney $U$-Test:**
Tests whether a randomly selected observation from group 1 is likely to be greater than one from group 2.
$$U_1 = n_1 n_2 + \frac{n_1(n_1 + 1)}{2} - R_1$$
$$U_2 = n_1 n_2 - U_1$$
$$U = \min(U_1, U_2)$$

**3. Rank-Biserial Correlation ($r$):**
Quantifies effect size bounded in $[-1, 1]$:
$$r = 1 - \frac{2U_1}{n_1 n_2}$$
where $r = -1$ indicates that all members of group 1 scored strictly lower than all members of group 2.

### Tiny Worked Example
Comparing ratings of On-Time ($n_1 = 3$) vs Late ($n_2 = 3$):
- On-Time ratings: $[5, 5, 4]$
- Late ratings: $[1, 2, 1]$
- Combined sorted ranks:
  - 1 (rank 1.5), 1 (rank 1.5), 2 (rank 3), 4 (rank 4), 5 (rank 5.5), 5 (rank 5.5).
- Sum of Late ranks $R_{\text{late}} = 1.5 + 1.5 + 3 = 6$.
- $U_{\text{late}} = (3)(3) + \frac{3(4)}{2} - 6 = 9 + 6 - 6 = 9$.
- $U_{\text{on-time}} = (3)(3) - 9 = 0$.
- Rank-biserial effect size:
  $$r = 1 - \frac{2(9)}{3 \times 3} = 1 - \frac{18}{9} = -1.0$$
Perfect negative association: late orders systematically rank lower.

### Implementation Link
- Implemented in [`scripts/run_review_econometrics.py`](../../scripts/run_review_econometrics.py#L90-L135). For Olist late orders $>5$ days late vs on-time: $H = 10,167.48$ ($p < 10^{-15}$), $r = -0.781$.

---

## 5. Logistic Regression Odds Ratios & Cluster-Robust Standard Errors

### Intuition
When modeling a binary outcome (e.g. $Y = 1$ if review score $\le 2$ stars, 0 otherwise), ordinary least squares (OLS) can predict probabilities outside $[0, 1]$ and assumes homoskedastic errors. Logistic regression models the log-odds as a linear combination of predictors. Furthermore, individual orders shipped by the same seller share merchant practices, inventory quality, and warehouse processes. Observations are therefore not independently and identically distributed ($i.i.d.$). Ignoring within-seller correlation produces artificially small standard errors, inflating false significance. We correct this using **cluster-robust standard errors**.

### Mathematical Formulation
**1. Logit Model:**
$$\Pr(Y_i = 1 \mid X_i) = p_i = \frac{1}{1 + e^{-X_i \beta}}$$
$$\ln\left(\frac{p_i}{1 - p_i}\right) = X_i \beta = \beta_0 + \beta_1 X_{1i} + \dots + \beta_k X_{ki}$$
The **Odds Ratio (OR)** for a 1-unit increase in predictor $X_j$ is:
$$\text{OR}_j = \exp(\beta_j)$$

**2. Cluster-Robust Variance Estimator (Sandwich Estimator):**
For $G$ independent clusters (merchants $g = 1, \dots, G$):
$$V_{\text{cluster}} = (X^T W X)^{-1} \left( \sum_{g=1}^{G} X_g^T u_g u_g^T X_g \right) (X^T W X)^{-1}$$
where $u_g = \sum_{i \in g} (y_i - \hat{p}_i)$ is the cluster residual score vector.
Cluster asymptotics require $G \to \infty$ with reasonably balanced clusters. Clustering on `seller_id` ($G = 2,953$) satisfies this condition, whereas clustering on `seller_state` ($G = 27$, with São Paulo accounting for $>70\%$) violates cluster balance.

### Tiny Worked Example
Suppose $\beta = 3.5153$ for binary indicator $\text{undelivered\_at\_review}$:
$$\text{OR} = \exp(3.5153) \approx 33.626$$
Interpretation: Holding other covariates constant, an order that has not yet been delivered when the customer completes the review survey has **33.6 times higher odds** of receiving a low review ($\le 2$ stars) compared to an on-time delivered order.

### Implementation Link
- Implemented in [`scripts/run_review_econometrics.py`](../../scripts/run_review_econometrics.py#L140-L245) using `sm.Logit(y, X).fit(cov_type='cluster', cov_kwds={'groups': df_reg['seller_id']})`.

---

## 6. Association vs Causation, Confounders vs Mediators

### Intuition
Observing that two variables correlate does not mean one causes the other:
- A **Confounder** ($Z$) is a common prior cause of both treatment ($X$) and outcome ($Y$). Failing to control for $Z$ induces spurious correlation between $X$ and $Y$.
- A **Mediator** ($M$) lies on the causal chain between $X$ and $Y$ ($X \to M \to Y$). Controlling for a mediator blocks the causal effect of $X$ on $Y$, leading to post-treatment conditioning bias.

### Causal DAG Formulations

**Confounding:**
```
     Z (e.g., Seller Fulfillment Capability / Geographic Distance)
    / \
   ▼   ▼
  X     Y
(Delay) (Low Review)
```
Controlling for seller identity or geographic corridor eliminates spurious confounding.

**Mediation vs Information Confounding:**
```
Order Dispatched ──► Automated Review Email Fired ──► Customer Submits Review
                           │                                   │
                           ▼                                   ▼
                  Package Not Delivered ───────────► 1-Star Review ("Where is my order?")
```

### Tiny Worked Example
- Suppose long-haul interstate shipments (SP $\to$ RJ) have both higher carrier delays and lower review ratings due to transit damage. If we do not control for shipping lane, we might attribute transit damage dissatisfaction to seller processing delay.

### Implementation Link
- Analyzed in [`sql/05_root_cause_analysis.sql`](../../sql/05_root_cause_analysis.sql) and [`scripts/run_review_econometrics.py`](../../scripts/run_review_econometrics.py#L30-L75).

---

## 7. Review-Timing Information Sets

### Intuition
In econometric modeling of survey responses, a critical requirement is that explanatory variables must be part of the agent's **information set** at the time the decision was made. 
In the Olist dataset, automated review request emails were dispatched around the `order_estimated_delivery_date`. If the package had not arrived, customers filled out the survey immediately. 
Regressing review score on *final delivery delay* (e.g. $+14$ days late) creates **forward-looking bias** because the customer submitted their review when the order was only $+3$ days late and undelivered!

### Mathematical Formulation
Let:
- $t_{\text{review}}$: Timestamp of review survey submission.
- $t_{\text{delivery}}$: Timestamp of physical customer delivery.
- $t_{\text{estimated}}$: Timestamp of promised estimated delivery date.

For an order $i$, we define the customer's observable state at $t_{\text{review}}$:
$$\text{undelivered\_at\_review}_i = \mathbb{I}(t_{\text{review}, i} < t_{\text{delivery}, i})$$
$$\text{days\_overdue\_at\_review}_i = \max\left(0, \text{DateDiff}(t_{\text{estimated}, i}, t_{\text{review}, i})\right)$$

**Model Specifications:**
- **Model A (Conventional / Forward-Looking):**
  $$\text{logit}(p_i) = \beta_0 + \beta_1 \cdot \text{delay\_days\_late}_i + \beta_2 \cdot \ln(\text{price}_i) + \beta_3 \cdot \text{freight\_ratio}_i$$
  Yields $\text{OR} = 1.229$ per day late ($p < 0.001$).
<!-- BEGIN_MODEL_B_CONCEPTS -->
- **Model B (Information Set at Review Time):**
  $$\text{logit}(p_i) = \gamma_0 + \gamma_1 \cdot \text{undelivered\_at\_review}_i + \gamma_2 \cdot \text{days\_overdue\_at\_review}_i + \gamma_3 \cdot \ln(\text{price}_i) + \gamma_4 \cdot \text{freight\_ratio}_i$$
  Yields $\text{OR} = 33.63\times$ ($p < 10^{-15}$) for $\text{undelivered\_at\_review}$, while $\gamma_2$ is economically small: $\text{OR} = 1.0036$ per day overdue ($p < 0.001$, $z = 4.65$, $\text{SE} = 0.0008$). A 30-day overdue delay increases odds by only $1.11\times$, compared to $33.63\times$ for non-receipt at review time.

Conclusion: Customer dissatisfaction is driven by the **binary non-receipt event** at the promised date (an immediate step-function penalty), while subsequent overdue days have an economically small incremental effect.
<!-- END_MODEL_B_CONCEPTS -->

### Tiny Worked Example
Order `ORD-202`:
- Promised EDD: May 10
- Review submitted: May 13 ($t_{\text{review}} - t_{\text{estimated}} = +3$ days)
- Package physically delivered: May 24 ($t_{\text{delivery}} - t_{\text{estimated}} = +14$ days)
- Customer rating: 1 star.
- In Model A: The 1-star review is attributed to 14 days of delay.
- In Model B: The 1-star review is attributed to the fact that on May 13, the package was unarrived (`undelivered_at_review = 1`), with 3 days overdue.

### Implementation Link
- Implemented in [`scripts/run_review_econometrics.py`](../../scripts/run_review_econometrics.py#L40-L85).

---

## 8. Right-Censoring & Survivorship Bias

### Intuition
In fulfillment and survival analysis, **right-censoring** occurs when an event of interest (customer delivery) has not yet occurred by the end of the observation window, or when an order is terminated prior to completion (cancellation, lost in transit). 
If an analyst measures "average delivery time" by filtering `WHERE order_status = 'delivered'`, they induce **survivorship bias**: the worst-performing orders (lost shipments, indefinite transit delays) are discarded from the metric, artificially painting an overly optimistic picture of operations.

### Mathematical Formulation
Let $T_i^*$ be the true delivery duration for order $i$, and $C_i$ be the censoring time (e.g. order cancellation or snapshot cutoff).
The observed delivery duration is:
$$T_i = \min(T_i^*, C_i)$$
with censoring indicator:
$$\delta_i = \mathbb{I}(T_i^* \le C_i)$$
Evaluating fulfillment performance solely on $\delta_i = 1$ (delivered orders) biases the expected delay downward:
$$\mathbb{E}[T \mid \delta = 1] < \mathbb{E}[T^*]$$

### Tiny Worked Example
In the Olist dataset:
- Total orders: 99,441
- Delivered orders: 96,478 (97.02%)
- Unfulfilled orders: 2,963 orders (2.98%):
  - 1,107 orders shipped but never marked delivered (lost or indefinite line-haul transit).
  - 625 canceled orders.
  - 609 unavailable stock-outs.
  - 622 orders trapped in early fulfillment stages (invoiced, processing, approved).
If these 2,963 orders are ignored, late delivery exposure is understated because indefinite transit represents the most severe failure mode.

### Implementation Link
- Implemented in [`sql/04_kpi_layer.sql`](../../sql/04_kpi_layer.sql#L15-L55) via view `view_unfulfilled_orders_breakdown`, decoupling delivered order delay metrics from platform unfulfilled order rates.
