# 08: Architecture Decision Records (ADRs)

**Project:** Marketplace Profitability & Fulfillment Leakage Analysis  
**Author:** Jenish Patel  
**Purpose:** Formal record of key technical and analytical architecture decisions, trade-offs evaluated, alternatives rejected, and operational consequences.

---

## Table of Decision Records
1. [ADR-01: DuckDB as Embedded Analytical Processing Engine](#adr-01-duckdb-as-embedded-analytical-processing-engine)
2. [ADR-02: Calendar Date Casting vs Timestamp Precision for Delivery Lateness](#adr-02-calendar-date-casting-vs-timestamp-precision-for-delivery-lateness)
3. [ADR-03: Two-Gate Fulfillment Attribution (Seller Dispatch vs Post-Handover Delay)](#adr-03-two-gate-fulfillment-attribution-seller-dispatch-vs-post-handover-delay)
4. [ADR-04: Customer Information-Set Formulation at Review Survey Submission](#adr-04-customer-information-set-formulation-at-review-survey-submission)
5. [ADR-05: Three-Level Economic Exposure Framework vs "Recovered Cash" Claims](#adr-05-three-level-economic-exposure-framework-vs-recovered-cash-claims)
6. [ADR-06: Primary Cluster-Robust Standard Errors on `seller_id`](#adr-06-primary-cluster-robust-standard-errors-on-seller_id)
7. [ADR-07: Minimum Volume Qualification Threshold ($N \ge 30$) for Intervention Tiers](#adr-07-minimum-volume-qualification-threshold-n-ge-30-for-intervention-tiers)
8. [ADR-08: Pre-Aggregation CTEs to Prevent Relational Grain Fan-Out](#adr-08-pre-aggregation-ctes-to-prevent-relational-grain-fan-out)
9. [ADR-09: 2017 $\to$ 2018 Temporal Holdout Persistence Validation](#adr-09-2017--2018-temporal-holdout-persistence-validation)
10. [ADR-10: Lightweight Version-Pinned Dependencies over Heavy Orchestrators](#adr-10-lightweight-version-pinned-dependencies-over-heavy-orchestrators)

---

### ADR-01: DuckDB as Embedded Analytical Processing Engine
- **Context:** The raw dataset comprises ~100k orders (~112k items) across 9 CSV tables totaling ~120 MB. We needed a fast, zero-dependency analytical SQL engine that supports full ANSI SQL, window functions, and seamless integration with Python and pandas.
- **Decision:** Use **DuckDB** as the embedded relational engine (`marketplace.duckdb`).
- **Alternatives Considered:**
  - *PostgreSQL / MySQL:* Rejected due to external server daemon overhead, configuration friction, and CI portability barriers.
  - *Apache Spark / PySpark:* Rejected as massive over-engineering for a 120 MB dataset that fits entirely in RAM.
  - *Pure Pandas:* Rejected because complex multi-table analytical joins and window functions are far more readable, maintainable, and verifiable in declarative SQL.
- **Consequences:** Near-instant query execution ($<1.5$ seconds for all 7 analytical scripts), columnar vectorization, zero database server administration, and trivial distribution.

---

### ADR-02: Calendar Date Casting vs Timestamp Precision for Delivery Lateness
- **Context:** The database stored `order_estimated_delivery_date` truncated to midnight (`YYYY-MM-DD 00:00:00`), whereas actual delivery timestamps recorded the exact time of day (`15:30:00`). Naive timestamp comparison marked 1,292 afternoon same-day deliveries as late.
- **Decision:** Cast both delivery timestamp and estimated delivery timestamp to `DATE` before comparing: `CAST(order_delivered_customer_date AS DATE) > CAST(order_estimated_delivery_date AS DATE)`.
- **Alternatives Considered:**
  - *Timestamp Comparison (`delivered > estimated`):* Rejected because it artificially inflated platform late delivery rate from 6.77% to 8.11% (a 16.5% relative error).
  - *Adding 23:59:59 Buffer:* Rejected because calendar date casting is cleaner, standardized across SQL dialects, and mathematically identical.
- **Consequences:** Corrects the platform late delivery rate to 6.77% (6,534 orders) and ensures SLA breach metrics align with customer expectations in Brazilian commercial law.

---

### ADR-03: Two-Gate Fulfillment Attribution (Seller Dispatch vs Post-Handover Delay)
- **Context:** Initial exploratory analysis attributed 100% of delivery delays to merchants. However, fulfillment has two gates: merchant dispatch against `shipping_limit_date`, and everything after handover, judged against the platform's promised date (`order_estimated_delivery_date`), which is not a carrier SLA.
- **Decision:** Decompose delivery delay into explicit handover flags: `is_seller_late_dispatch` (against `shipping_limit_date`) and the post-handover flag (handed over on time but delivered late; the identifier `is_carrier_caused_late` is kept for compatibility, but the responsible party is not observable). A transit-vs-promise test (guide 09) checks whether post-handover delay reflects a long leg or a tight promise.
- **Alternatives Considered:**
  - *Sole Merchant Accountability:* Rejected because 72.25% of late (order, seller) pairs were handed over on time; penalizing sellers would misdirect operational resources.
  - *Sole Carrier Accountability:* Rejected because 27.75% of late pairs involved seller dispatch failure (or no recorded handover), and because the dataset has no carrier scans to name a responsible party.
- **Consequences:** Enables decoupled operational playbooks: Seller Operations enforces dispatch deadlines on the 27.75% of late pairs late at dispatch, while Logistics reviews post-handover transit on the 72.25% delayed after handover. The transit-vs-promise test finds those late pairs spent far longer in transit than on-time pairs on the same corridor, so the delay is transit-driven rather than a promise-setting artefact.

---

### ADR-04: Customer Information-Set Formulation at Review Survey Submission
- **Context:** Regressing customer review scores against final delivery delay days introduces forward-looking bias because 70.10% of late-order reviews were submitted *before* package arrival.
- **Decision:** Formulate Model B conditioning on the customer's observable state at survey timestamp: `undelivered_at_review` and `days_overdue_at_review`.
- **Alternatives Considered:**
  - *Model A (Final Delivery Delay):* Shows an odds ratio of 1.229 per day late, but obscures the underlying survey dispatch mechanism.
  - *Excluding Pre-Delivery Reviews:* Rejected because discarding 70.10% of late reviews would induce catastrophic selection bias.
<!-- BEGIN_MODEL_B_ADR -->
- **Consequences:** Proves customer dissatisfaction is driven by the binary promise breach (`undelivered_at_review`, $\text{OR} = 33.63\times, p < 10^{-15}$), while marginal delay days have an economically small effect ($\text{OR} = 1.0036$ per day, $p < 0.001$, $z = 4.65$; 30 days overdue yields only $\sim 1.11\times$ vs $33.63\times$ for non-arrival).
<!-- END_MODEL_B_ADR -->

---

### ADR-05: Three-Level Economic Exposure Framework vs "Recovered Cash" Claims
- **Context:** Early documentation claimed the project "recovered R\$ 94K in operational cash". This claim is indefensible: historical observational data cannot execute live interventions, and late orders are completed sales where GMV was collected.
- **Decision:** Replace fabricated cost savings with a rigorous Three-Level Economic Exposure Framework:
  - Level 1: Observable Late-Order GMV & Freight (R\$ 1.15M total).
  - Level 2: Observable Freight Cost Burden (16.57%).
  - Level 3: Illustrative Operational Mitigation Scenarios (10%, 25%, 40% assumed rates, not measured).
- **Alternatives Considered:**
  - *Estimating Net Profit Impact:* Rejected because seller commission rates, payment gateway fees, and platform overhead are unobserved in the public dataset.
- **Consequences:** Eliminates corporate credibility risks and provides leadership with defensible scenario-based addressable opportunity bounds.

---

### ADR-06: Primary Cluster-Robust Standard Errors on `seller_id`
- **Context:** Orders fulfilled by the same seller share merchant practices, inventory quality, and warehouse processes. In earlier revisions, standard errors were clustered at the `seller_state` level (27 clusters), with São Paulo accounting for $>70\%$ of shipments.
- **Decision:** Shift primary clustering from `seller_state` to `seller_id` ($G = 2,953$ independent clusters), with `seller_state` and `HC1` reported as sensitivity checks.
- **Alternatives Considered:**
  - *State-Level Clustering:* Violates asymptotic requirements ($G \to \infty$ with balanced clusters), deflating standard errors and creating false precision.
  - *Unclustered OLS/Logit:* Assumes $i.i.d.$ observations, ignoring within-seller correlation entirely.
- **Consequences:** Provides econometrically robust inference ($\text{OR} = 33.63\times, \text{SE} = 0.0506, p < 10^{-15}$) meeting peer-reviewed statistical standards.

---

### ADR-07: Minimum Volume Qualification Threshold ($N \ge 30$) for Intervention Tiers
- **Context:** In unthresholded seller rankings, sellers with 1 order that was late have a 100% late delivery rate but generate negligible impact (R\$ 70 exposure), while high-volume sellers with a 15% late rate generate thousands of Reais in exposure.
- **Decision:** Apply a minimum operational qualification threshold of $N \ge 30$ lifetime orders to qualify for Priority Tiers P1–P3. Low-volume sellers ($N < 30$) are assigned to P4 ("Low Volume / Not Prioritised").
- **Alternatives Considered:**
  - *No Volume Cutoff:* Ranks noisy low-volume sellers as high priority.
  - *Threshold at $N \ge 20$ or $N \ge 50$:* Sensitivity analysis confirms that the core 69 high-exposure merchants are captured across all cutoffs; $N \ge 30$ optimizes coverage (113 merchants, 48.85% of seller-caused late exposure).
- **Consequences:** Eliminates sample variance noise and focuses partner operations resources on commercially impactful merchants.

---

### ADR-08: Pre-Aggregation CTEs to Prevent Relational Grain Fan-Out
- **Context:** Orders frequently have multiple line items, split payment vouchers, and multiple review survey records. Naive joins across these tables multiply line items, doubling GMV and freight.
- **Decision:** Pre-aggregate payments (`int_order_payments_rollup`) and reviews (`int_order_reviews_dedup`) to the `order_id` grain in Common Table Expressions (CTEs) before joining to `olist_order_items`.
- **Alternatives Considered:**
  - *Direct Multi-Table Joins:* Corrupts financial totals ($200\%+$ of true GMV).
  - *Separate Analytical Databases:* Creates maintenance overhead and sync complexity.
- **Consequences:** Guarantees line-item integrity in `fact_order_items` (112,650 rows) and exact penny reconciliation with raw sources (GMV: R\$ 13,591,643.70; Freight: R\$ 2,251,909.54).

---

### ADR-09: 2017 $\to$ 2018 Temporal Holdout Persistence Validation
- **Context:** Tiering sellers on the entire historical dataset simultaneously introduces look-ahead bias: did P1 sellers experience bad luck during peak seasons, or does their excess carry over to a later year?
- **Decision:** Formalize a temporal holdout check (`view_seller_persistence_check`) tiering merchants solely on 2017 data with the same tier rule as the headline (`view_seller_tiers_by_period`) and evaluating their seller-caused lateness out-of-sample across 2018 with seller-level bootstrap intervals.
- **Alternatives Considered:**
  - *Cross-Sectional Evaluation:* Evaluates in-sample performance only, vulnerable to overfitting.
  - *Random Train-Test Split:* Ignores the temporal arrow of time in operations.
- **Consequences:** Shows partial persistence: the 2017 P1 cohort's seller-caused excess shrinks but stays positive in 2018 (rates and intervals in guide 09). Part of the shrinkage is regression to the mean from selecting on a high year, so P1 is used as a prioritisation list, not as proof of a fixed seller trait. An earlier version of this check used a looser cohort rule and an all-cause outcome and overstated persistence; it was replaced (MP-06).

---

### ADR-10: Lightweight Version-Pinned Dependencies over Heavy Orchestrators
- **Context:** Analytical projects frequently suffer from environment drift and over-engineering (e.g. Docker containers, Airflow DAGs, dbt packages for a single static dataset).
- **Decision:** Lock dependencies to exact tested versions in `requirements.txt` (`duckdb==1.4.5`, `pandas==2.3.3`, `numpy==1.26.4`, `scipy==1.13.1`, `statsmodels==0.14.6`, `reportlab==5.0.1`, `pytest==8.4.2`) and orchestrate verification via Python script `scripts/run_all.py`.
- **Alternatives Considered:**
  - *Docker Containerization:* Adds Docker desktop installation friction on Windows with zero performance benefit for local analytical execution.
  - *Unpinned `requirements.txt`:* Subject to upstream library API breaking changes.
- **Consequences:** 100% reproducible execution on any Python 3.9+ environment in under 50 seconds with zero infrastructure overhead.
