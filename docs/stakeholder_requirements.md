# Stakeholder Requirements Specification

**Project:** Marketplace Profitability & Fulfillment Leakage Diagnostic  
**Target Stakeholders:** Chief Operating Officer (COO), VP of Marketplace Operations, Head of Logistics  
**Analytical Role:** Senior Business / Operations Data Analyst  

---

## 1. Executive Business Problem

The marketplace is experiencing top-line expansion in Gross Merchandise Value (GMV) and order volume, but contribution economics are under severe margin compression. Leadership needs an operational and unit-economics diagnostic to identify which sellers, product categories, and delivery corridors are driving fulfillment leakage, and to prioritize concrete operational interventions based on recoverable economic exposure.

---

## 2. Requirements Translation Matrix

| Ref | Executive Business Question | Target KPI / Metric | Source Data / Grain | Analytical Method | Actionable Operational Decision |
|---|---|---|---|---|---|
| **REQ-01** | Is marketplace growth accompanied by operational deterioration? | Monthly GMV, Distinct Orders, Late Delivery Rate (%), Freight Burden (%), Cancellation Rate (%) | orders, order_items<br>Grain: Monthly aggregate | Longitudinal time-series & cohort analysis (Jan 2017 – Aug 2018) | Identify macro operational inflection points (e.g., peak strain, freight inflation) to adjust platform fulfillment commitments. |
| **REQ-02** | Which sellers are driving the largest fulfillment failures, and is it a volume or rate problem? | Seller Order Volume, Late Delivery Rate (%), Seller Late-Order Transaction Exposure ({late}$), Avg Review Score | order_items, orders, sellers<br>Grain: seller_id | Volume × Severity matrix; 30-order operational volume threshold; Percentile ranking | Separate high-rate/low-volume noise from high-exposure partners. Issue targeted SLA warnings, operational audits, or platform delisting. |
| **REQ-03** | How concentrated is operational exposure across the seller base? | Cumulative Exposure Share (%), Seller Concentration Deciles | order_items, orders<br>Grain: seller_id | Pareto Cumulative Distribution (SUM() OVER (ORDER BY exposure DESC)) | Establish resource allocation rule: focus account management on the top Pareto cohort responsible for the majority of leakage. |
| **REQ-04** | Which product categories exhibit structurally defective unit economics? | Category GMV, Freight Burden (%), Freight per kg ($), Avg Review Score | order_items, products, 	ranslation<br>Grain: product_category_name_english | Structural logistics analysis (Weight, Cube volume, Freight-to-Value) | Redesign category shipping subsidies, introduce volumetric freight surcharges, or mandate seller-fulfilled bulky shipping. |
| **REQ-05** | Are specific geographic delivery lanes failing customer commitments? | Corridor Orders, Corridor Late Rate (%), Freight per Order, Avg Delay Days | sellers, customers, orders<br>Grain: Corridor (seller_state $\\to$ customer_state) | Origin-Destination Corridor Matrix & Regional Hotspot Analysis | Re-evaluate carrier contracts on chronic bottleneck routes (e.g., SP $\\to$ Northeast/RJ) and adjust estimated delivery lead times (EDD buffer). |
| **REQ-06** | Does delivery delay measurably degrade customer satisfaction? | Review Score Distribution (1–5), Low-Review Rate ($\\le 2$ stars), Avg Delay Days | orders, order_reviews<br>Grain: Deduplicated order_id | Non-parametric tests (Kruskal-Wallis, Mann-Whitney U); Multivariate Logistic Regression | Quantify customer experience risk to justify operational remediation investments and customer service buffering. |
| **REQ-07** | How should leadership rank intervention priorities, and what is the addressable economic impact? | Priority Tier (P1–P4), Total P1 Exposure, Addressable Recovery ($) under Conservative (10%), Base (25%), Optimistic (40%) | Analytical fact layer<br>Grain: Seller & Category | Multi-criteria rule-based matrix (Volume $\\ge 30$, Exposure $\\ge$ 75th percentile, Severity $\\ge$ 75th percentile) | Deploy operations team to P1 targets; establish governance cadence; forecast addressable economic upside for leadership review. |

---

## 3. Methodological Governance & Operational Constraints

1. **No Speculative Profit Figures:** The dataset contains observable prices, freight charges, and timestamps, but lacks unobserved platform overheads (seller commission rate, gateway fees, customer service costs). All financial impact metrics are strictly designated as **Transaction Exposure** or **Freight Burden**, never fabricated actual profit.
2. **Strict Grain Separation:** Line-item calculations (order_id + order_item_id) are isolated from order-level metrics (order_id) to prevent fan-out duplication across multi-item and multi-seller orders.
3. **Transparent Prioritization Rules:** Priority tiers (P1 to P4) are assigned using deterministic percentile thresholds rather than arbitrary weighted scoring formulas, ensuring reproducibility and executive defensibility.
