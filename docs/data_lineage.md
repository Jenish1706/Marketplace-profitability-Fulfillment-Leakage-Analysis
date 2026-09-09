# End-to-End Data Lineage & Grain Architecture

**Project:** Marketplace Profitability & Fulfillment Leakage Diagnostic  
**Subject:** Data Lineage, Entity Flow, and Granular Fan-Out Prevention  

---

## 1. Macro Data Flow Architecture

The data pipeline transitions raw commercial records through four progressive stages of abstraction:

```
┌────────────────────────────┐
│      RAW SOURCE DATA       │ 9 Official Olist CSV tables in data/raw/
└─────────────┬──────────────┘
              │ (pipeline/ingestion.py: Deterministic DuckDB staging)
              ▼
┌────────────────────────────┐
│     STAGING DUCKDB TBLS    │ 9 Raw relational tables (1-to-1 schema mapping)
└─────────────┬──────────────┘
              │ (sql/03_order_item_fact.sql: Pre-aggregation & grain isolation)
              ▼
┌────────────────────────────┐
│   CONTROLLED FACT LAYER    │ fact_order_items (Line-item grain: 112,650 rows)
│                            │ fact_orders (Order grain: 99,441 rows)
└─────────────┬──────────────┘
              │ (sql/04_kpi_layer.sql to sql/07_intervention_priority.sql)
              ▼
┌────────────────────────────┐
│     ANALYTICAL VIEWS       │ 6-Layer KPIs, Root Cause, Pareto Deciles, P1-P4 Tiers
└─────────────┬──────────────┘
              │
      ┌───────┴──────────────────────────┐
      ▼                                  ▼
┌────────────────────────────┐ ┌────────────────────────────┐
│   POWER BI STAR SCHEMA     │ │   EXECUTIVE DECISION MEMO  │
│ Clean modeling data exports│ │ 2-Page publication PDF     │
└────────────────────────────┘ └────────────────────────────┘
```

---

## 2. Table-by-Table Lineage Matrix

| Raw Source CSV | Staging Table | Analytical Fact / View Usage | Final Business Outputs & Decisions |
|---|---|---|---|
| `olist_orders_dataset.csv` | `olist_orders` | Joins into `fact_order_items` and `fact_orders` for order lifecycle timestamps (`purchase`, `carrier_delivered`, `customer_delivered`, `estimated_delivery`). | Defines delivery delay days, late delivery flag, cancellation rate, and monthly macro inflection trends. |
| `olist_order_items_dataset.csv` | `olist_order_items` | Defines primary grain for `fact_order_items` (`order_id + order_item_id`); links `seller_id` and `product_id`. | Produces GMV, line-item freight charges, freight-to-price ratio, and seller performance metrics. |
| `olist_order_payments_dataset.csv` | `olist_order_payments` | Pre-aggregated via `int_order_payments_rollup` to order grain (`SUM(payment_value)`, `MAX(installments)`). | Prevents payment installment records from multiplying line items; reconciles total transaction cash flow. |
| `olist_order_reviews_dataset.csv` | `olist_order_reviews` | Pre-aggregated via `int_order_reviews_dedup` to order grain (`AVG(review_score)`, `MIN(review_score)`). | Provides clean customer satisfaction metrics without fan-out; powers econometric regression models. |
| `olist_products_dataset.csv` | `olist_products` | Joined into `fact_order_items` to attach catalog physical attributes (weight in g, length, height, width in cm). | Computes product cube volume (cm³), freight-per-kg intensity, and identifies structural logistics deficits. |
| `olist_sellers_dataset.csv` | `olist_sellers` | Joined into `fact_order_items` to attach merchant origin state (`seller_state`) and city. | Powers seller scorecard, Pareto decile rankings, Volume × Severity matrix, and P1–P4 intervention tiers. |
| `olist_customers_dataset.csv` | `olist_customers` | Joined into `fact_order_items` and `fact_orders` to attach delivery destination state (`customer_state`). | Constructs 417 origin-destination corridors (`seller_state -> customer_state`) to pinpoint cross-regional bottlenecks. |
| `olist_geolocation_dataset.csv` | `olist_geolocation` | Reference geographic coordinate mapping for postal codes. | Validates state and postal code conventions across Brazilian logistics routes. |
| `product_category_name_translation.csv` | `product_category_name_translation` | Standardizes Portuguese product category names into English. | Produces category-level root-cause tables, freight burden matrices, and packaging restructuring playbooks. |

---

## 3. Grain Integrity & Fan-Out Prevention

### The Multi-Item & Multi-Seller Dilemma
In real e-commerce marketplaces, relational schemas are not simple 1-to-1 hierarchies:
- **Multi-Item Orders:** 13.9% of orders contain more than one line item (up to 21 items in a single order).
- **Multi-Seller Orders:** 1,278 orders contain items fulfilled by different independent merchants.
- **Multi-Payment Orders:** Customers frequently split transactions across multiple payment methods or vouchers.
- **Multiple Reviews:** A customer may submit multiple survey updates for a single order.

### Why Direct Joins Corrupt Commercial KPIs
Executing a naive join query:
```sql
-- NAIVE DIRECT JOIN (ANTI-PATTERN):
SELECT SUM(oi.price), SUM(p.payment_value)
FROM olist_orders o
JOIN olist_order_items oi ON o.order_id = oi.order_id
JOIN olist_order_payments p ON o.order_id = p.order_id
JOIN olist_order_reviews r ON o.order_id = r.order_id;
```
Multiplies line-item prices by payment installment rows and review rows. This artificial fan-out corrupts GMV, doubles freight values, and distorts average order value (AOV).

### The Controlled Grain Solution
Our data engineering architecture enforces two strictly separated analytical facts:
1. **`fact_order_items` (Line-Item Grain: `order_id + order_item_id`):** Exactly **112,650 rows**. Financial sums across this table reconcile perfectly with raw source totals (GMV: R$ 13,591,643.70; Freight: R$ 2,251,909.54). Reviews and payments are pre-aggregated to the order grain before joining.
2. **`fact_orders` (Order Grain: `order_id`):** Exactly **99,441 rows**. Rollups compute distinct order-level metrics (distinct sellers, total order value, is_multi_seller, is_late).
