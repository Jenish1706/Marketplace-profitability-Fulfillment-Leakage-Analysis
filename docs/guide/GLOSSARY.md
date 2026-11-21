# Glossary of Operational, Economic & Statistical Terms

**Project:** Marketplace Profitability & Fulfillment Leakage Analysis  
**Author:** Jenish Patel  
**Purpose:** Comprehensive alphabetical dictionary of all acronyms, domain terms, metric formulas, and statistical nomenclature used across the repository.

---

### 3PL (Third-Party Logistics)
External courier and freight transportation providers (e.g. Correios, private regional delivery networks) contracted by marketplace merchants to handle parcel pickup, line-haul transit, sorting, and last-mile doorstep delivery.

### Analytical Grain
The atomic level of detail represented by a single row in a database table. In this project, `fact_order_items` operates at the line-item grain (`order_id + order_item_id`, 112,650 rows), while `fact_orders` operates at the order grain (`order_id`, 99,441 rows).

### AOV (Average Order Value)
The mean commercial value of completed transactions: $\text{AOV} = \text{GMV} / N_{\text{orders}}$. For delivered orders in Olist, platform AOV is R\$ 140.88.

### Post-Handover Delay
A late delivery where the merchant handed the parcel over on or before the `shipping_limit_date`, but the customer received it after the `order_estimated_delivery_date`. Represents 72.25% of late (order, seller) pairs. The SQL identifier `is_carrier_caused_late` is kept for compatibility, but the data cannot name the responsible party (carrier, last-mile or customer availability): the second gate is the platform's promised date, not a carrier SLA.

### Post-Handover Transit
The time from handover (`order_delivered_carrier_date`) until physical customer receipt (`order_delivered_customer_date`), compared with the promise length (purchase to `order_estimated_delivery_date`) in the transit-vs-promise test in guide 09. There is no carrier SLA in this dataset.

### Cluster-Robust Standard Errors
A variance-covariance estimator (Liang-Zeger sandwich estimator) that relaxes the assumption of independent and identically distributed ($i.i.d.$) errors by allowing arbitrary correlation between observations within the same cluster. In this project, standard errors are clustered at the merchant level (`seller_id`, 2,953 clusters).

### CTE (Common Table Expression)
A temporary, named relational result set defined within an execution scope using the SQL `WITH` clause. Used extensively in `sql/03_order_item_fact.sql` to isolate payments and reviews before joining.

### Delivery Delay Days
The signed calendar difference between the actual delivery date and the promised estimated delivery date:
$$\text{Delivery Delay Days} = \text{CAST}(t_{\text{delivered}} \text{ AS DATE}) - \text{CAST}(t_{\text{estimated}} \text{ AS DATE})$$
A value $\le 0$ indicates on-time or early arrival; a value $> 0$ indicates late arrival.

### DuckDB
An embedded, columnar analytical database engine optimized for fast local OLAP SQL queries, vectorized execution, and seamless integration with Python.

### EDD (Estimated Delivery Date)
The date communicated to the customer at checkout by which delivery is promised (`order_estimated_delivery_date`).

### Fan-Out Duplication
An artificial inflation of row counts and financial metrics caused by executing a multi-table join across entities with one-to-many relationships (e.g. joining orders to multiple line items, split payment vouchers, and reviews simultaneously).

### Freight Burden (%)
The proportion of merchandise value consumed by shipping charges:
$$\text{Freight Burden} = \frac{\sum \text{freight\_value}}{\sum \text{price}} \times 100$$
Platform baseline freight burden is 16.57%.

### GMV (Gross Merchandise Value)
The total sales dollar value of merchandise sold on the marketplace, calculated strictly as the sum of item prices ($\sum \text{price} = \text{R\$} 13,591,643.70$), excluding shipping charges and installment financing fees.

### HC1 (Heteroskedasticity-Consistent Covariance Estimator)
A robust variance estimator (MacKinnon and White, 1985) that corrects for heteroskedasticity in observation-level errors with finite-sample degrees-of-freedom adjustment: $\frac{n}{n - k}$. Used as a sensitivity benchmark for econometric regressions.

### Handover Gate
The operational checkpoint where custody of a package transfers from the independent merchant to the logistics carrier (`order_delivered_carrier_date`).

### Kruskal-Wallis Test
A non-parametric rank-based statistical test evaluating whether independent groups originate from identical distributions, avoiding normal distribution assumptions required by ANOVA.

### Late Delivery Rate (%)
The proportion of delivered orders whose actual calendar delivery date exceeded the promised estimated delivery date:
$$\text{Late Delivery Rate} = \frac{\sum \mathbb{I}(\text{is\_late} = 1)}{\sum \mathbb{I}(\text{status} = \text{'delivered'})} \times 100$$
Platform baseline rate is 6.77% (6,534 orders).

### Late-Order Freight
The total shipping charges paid by customers on orders that arrived after the estimated delivery date (R\$ 164,967.79).

### Late-Order GMV
The total merchandise value of orders that arrived after the estimated delivery date (R\$ 985,924.34).

### Late-Order Total Value ($E_{\text{late}}$)
The total gross commercial flow associated with late deliveries: $\text{Late GMV} + \text{Late Freight} = \text{R\$} 1,150,892.13$.

### Mann-Whitney U Test
A non-parametric statistical hypothesis test used to determine whether two independent groups have different stochastic distributions based on rank sums.

### Multi-Item Order
An order containing 2 or more line items (13,680 orders, 13.9% of platform orders).

### Multi-Seller Order
An order containing line items fulfilled by two or more distinct merchants (1,278 orders, representing 2,668 order-seller fulfillment engagements).

### Odds Ratio (OR)
The ratio of the odds of an event occurring in the presence of an exposure to the odds of it occurring in its absence: $\text{OR} = \exp(\beta)$. An $\text{OR} > 1.0$ indicates increased probability of low customer ratings.

### OLS (Ordinary Least Squares)
A linear regression estimator that minimizes the sum of squared residuals between observed and predicted continuous outcomes.

### Pareto Concentration Lift
The ratio of a decile's share of platform operational failure to its share of platform GMV:
$$\text{Pareto Lift} = \frac{\text{Late Exposure Share}}{\text{GMV Share}}$$
Decile 1 achieves a 1.27× lift ($77.38\% / 60.78\%$).

### Percent Rank
A relative cumulative frequency calculation mapping an entity's rank to a uniform interval $[0, 1]$:
$$\text{Percent Rank} = \frac{\text{Rank} - 1}{N - 1}$$

### Priority Tiers (P1–P4)
A rule-based operational prioritization matrix segmenting qualified merchants ($N \ge 30$ orders):
- **P1 (Immediate Intervention):** Top 25th percentile in seller-caused late exposure and late rate (113 sellers, R\$ 181.4K seller exposure).
- **P2 (Operational Investigation):** High exposure or high failure severity requiring inspection (211 sellers).
- **P3 (Operational Monitoring):** Moderate volume and failure rates tracked via dashboard alerts (323 sellers).
- **P4 (Low Volume / Not Prioritised):** Sellers with $N < 30$ orders or standard fulfillment performance (2,448 sellers).

### Rank-Biserial Correlation ($r$)
A standardized effect size measure for the Mann-Whitney U test bounded in $[-1, 1]$: $r = 1 - \frac{2U_1}{n_1 n_2}$.

### Review Timing Confounder
An observational bias where 70.10% of customer reviews for late orders were submitted *before* package delivery, caused by automated survey emails triggering around the promised delivery date.

### Right-Censoring
An observation condition where the terminal event of interest (customer delivery) has not occurred before the end of the data collection window or was interrupted by cancellation.

### Seller-Caused Late
An operational failure where the order arrived after the estimated delivery date AND the merchant dispatched the parcel after `shipping_limit_date`. Accounts for 27.75% of platform late items (R\$ 371,281.14 exposure).

### Seller Dispatch SLA
The contractual deadline by which a merchant must hand over a packaged order to the shipping carrier (`shipping_limit_date`).

### Star Schema
A relational database modeling technique organizing data into central fact tables (`fact_order_items`, `fact_orders`) connected to surrounding dimensional lookup tables (`dim_sellers`, `dim_customers`, `dim_products`).

### Survivorship Bias
A statistical error caused by evaluating performance metrics only on entities that reached terminal status (e.g. measuring delay only on delivered orders while ignoring lost or canceled orders).

### Unfulfilled Orders
Orders that never achieved `delivered` status (2,963 orders, 2.98% of platform orders), including shipped/lost (1,107), canceled (625), and unavailable stock-outs (609).

### Window Function
A SQL calculation evaluated across a set of table rows related to the current row without collapsing them into a single summary row (`OVER (PARTITION BY ... ORDER BY ...)`).
