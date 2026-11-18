# 03: Data Catalog, Schemas & Quality Audit

**Project:** Marketplace Profitability & Fulfillment Leakage Analysis  
**Author:** Jenish Patel  
**Purpose:** Technical catalog of raw datasets, database schemas, quality anomalies, and exclusion criteria.

---

## 1. Data Source & Licensing

- **Source:** [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce), released on Kaggle.
- **Licence:** Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0).
- **Time Window:** September 2016 through October 2018 (Core active window: January 2017 through August 2018).
- **Geographic Scope:** All 27 Brazilian federative units (26 states + Federal District).

---

## 2. Table Catalog & Record Counts

The raw relational data consists of 9 CSV files stored in `data/raw/`:

| Source Table Name | Raw File Name | Row Count | Primary Key / Grain | Key Columns Used |
|---|---|---|---|---|
| **`olist_orders`** | `olist_orders_dataset.csv` | **99,441** | `order_id` | `order_status`, `order_purchase_timestamp`, `order_delivered_carrier_date`, `order_delivered_customer_date`, `order_estimated_delivery_date`, `customer_id` |
| **`olist_order_items`** | `olist_order_items_dataset.csv` | **112,650** | `order_id + order_item_id` | `product_id`, `seller_id`, `shipping_limit_date`, `price`, `freight_value` |
| **`olist_order_payments`** | `olist_order_payments_dataset.csv` | **103,886** | `order_id + payment_sequential` | `payment_type`, `payment_installments`, `payment_value` |
| **`olist_order_reviews`** | `olist_order_reviews_dataset.csv` | **99,224** | `review_id + order_id` | `review_score`, `review_creation_date`, `review_answer_timestamp` |
| **`olist_products`** | `olist_products_dataset.csv` | **32,951** | `product_id` | `product_category_name`, `product_weight_g`, `product_length_cm`, `product_height_cm`, `product_width_cm` |
| **`olist_sellers`** | `olist_sellers_dataset.csv` | **3,095** | `seller_id` | `seller_zip_code_prefix`, `seller_city`, `seller_state` |
| **`olist_customers`** | `olist_customers_dataset.csv` | **99,441** | `customer_id` | `customer_unique_id`, `customer_zip_code_prefix`, `customer_city`, `customer_state` |
| **`olist_geolocation`** | `olist_geolocation_dataset.csv` | **1,000,163** | `geolocation_zip_code_prefix + lat + lng` | Reference geographic coordinate mapping for postal codes |
| **`product_category_name_translation`** | `product_category_name_translation.csv` | **71** | `product_category_name` | Maps Portuguese catalog category names to standardized English |

---

## 3. Schema Definitions in Analytical Fact Layer

### `fact_order_items` (Line-Item Grain: 112,650 rows)
Defined in [`sql/03_order_item_fact.sql`](../../sql/03_order_item_fact.sql):
- `order_id` (VARCHAR): Unique transaction identifier.
- `order_item_id` (INTEGER): Sequential item index within the order ($1, 2, \dots, 21$).
- `product_id` (VARCHAR): Product catalog identifier.
- `seller_id` (VARCHAR): Merchant identifier.
- `shipping_limit_date` (TIMESTAMP): Contractual merchant handover deadline.
- `price` (DOUBLE): Item price (GMV) in Brazilian Reais (R$).
- `freight_value` (DOUBLE): Freight charge allocated to line item in R$.
- `total_item_value` (DOUBLE): $\text{price} + \text{freight\_value}$.
- `freight_ratio` (DOUBLE): $\text{freight\_value} / \text{price}$.
- `is_late` (INTEGER): 1 if delivered after estimated delivery date at calendar date level, 0 otherwise.
- `is_seller_late_dispatch` (INTEGER): 1 if carrier handover occurred after `shipping_limit_date`.
- `is_seller_caused_late` (INTEGER): 1 if `is_late = 1` AND `is_seller_late_dispatch = 1`.
- `is_carrier_caused_late` (INTEGER): 1 if `is_late = 1` AND `is_seller_late_dispatch = 0`.
- `delivery_delay_days` (INTEGER): Calendar days between delivery date and estimated delivery date.
- `review_score` (DOUBLE): Average customer review score associated with the order.
- `customer_state` (VARCHAR): Destination state.
- `seller_state` (VARCHAR): Origin merchant state.
- `shipping_corridor` (VARCHAR): `seller_state -> customer_state` route (e.g. `SP -> RJ`).

### `fact_orders` (Order Grain: 99,441 rows)
Defined in [`sql/03_order_item_fact.sql`](../../sql/03_order_item_fact.sql):
- `order_id` (VARCHAR): Primary key.
- `order_status` (VARCHAR): Terminal order status (`delivered`, `shipped`, `canceled`, `unavailable`, etc.).
- `item_count` (INTEGER): Number of physical line items in order ($1$ to $21$).
- `distinct_sellers` (INTEGER): Distinct merchants fulfilling the order.
- `is_multi_seller` (INTEGER): 1 if `distinct_sellers > 1`, 0 otherwise (1,278 orders).
- `order_gmv` (DOUBLE): Sum of item prices.
- `order_freight` (DOUBLE): Sum of freight charges.
- `order_total_value` (DOUBLE): $\text{order\_gmv} + \text{order\_freight}$.
- `total_payment_value` (DOUBLE): Reconciled customer payment value from `olist_order_payments`.
- `is_late` (INTEGER): Order-level late delivery flag (1 if order arrived late).

---

## 4. Known Data Quality Problems & Handling

| Defect / Anomaly | Impact if Ignored | How Handled in Pipeline | Verification Test |
|---|---|---|---|
| **Timestamp Midnight Truncation** | `order_estimated_delivery_date` is truncated to midnight (`00:00:00`). Comparing timestamps marks 1,292 afternoon same-day deliveries as late, inflating late rate from 6.77% to 8.11%. | Evaluated with `CAST(order_delivered_customer_date AS DATE) > CAST(order_estimated_delivery_date AS DATE)`. | `test_p01_same_day_delivery_not_late` in [`tests/test_audit_fixes.py`](../../tests/test_audit_fixes.py) |
| **Missing Delivery Timestamps** | 8 delivered orders have `order_delivered_customer_date IS NULL`. Computing delay produces NULL or error. | Filtered with `WHERE order_delivered_customer_date IS NOT NULL` in delay queries; orders retained in total volume count. | `test_dq_null_delivered_dates` in [`tests/verify_pipeline.py`](../../tests/verify_pipeline.py) |
| **Split-Payment Fan-Out** | Multiple installment or voucher rows in `olist_order_payments` multiply line items on naive join. | Pre-aggregated to order grain in `int_order_payments_rollup` via `SUM(payment_value)` before joining. | `test_pipeline_reconciliation` in [`tests/verify_pipeline.py`](../../tests/verify_pipeline.py) |
| **Multiple Reviews per Order** | Duplicate review submissions (e.g., initial comment + follow-up) fan out line items. | Pre-aggregated in `int_order_reviews_dedup` via `ROUND(AVG(review_score), 2)`. | `test_pipeline_reconciliation` in [`tests/verify_pipeline.py`](../../tests/verify_pipeline.py) |
| **Review Survey Timing Confounder** | 70.10% of late orders were reviewed before delivery, evaluating an unarrived parcel (avg 3.73 days late) rather than final delay (avg 13.82 days late). | Formulated Model B conditioning on information set at survey time: `undelivered_at_review` and `days_overdue_at_review`. | `test_p03_reviews_before_delivery` in [`tests/test_audit_fixes.py`](../../tests/test_audit_fixes.py) |
| **Low-Volume Seller Volatility** | Sellers with 1 order that is late have a 100% late delivery rate, creating statistical noise in operational tiering. | Applied a minimum volume threshold of $N \ge 30$ lifetime orders to qualify for P1–P3 tiers; low-volume sellers assigned to P4. | `test_p18_tier_naming_and_documentation` in [`tests/test_audit_fixes.py`](../../tests/test_audit_fixes.py) |

---

## 5. Exclusions & Population Boundaries

### 1. Active Operating Window Exclusion (Monthly Cohort Trends)
- **Included:** 20 consecutive months from **January 2017 through August 2018**.
- **Excluded:**
  - September–December 2016 (329 orders): Platform beta launch / ramp-up phase with unstable delivery logistics.
  - September–October 2018 (4 orders): System decommission / trailing administrative records.
- **Rationale:** Longitudinal trend analysis requires stable monthly operational baselines. Including months with single-digit orders skews monthly growth rates and variance calculations.

### 2. Undelivered / Unfulfilled Orders Exclusion (Delay Calculations)
- **Delivered Orders:** 96,478 orders (97.02% of 99,441 orders). All delivery delay duration and SLA breach metrics are calculated strictly on this population.
- **Unfulfilled Orders:** 2,963 orders (2.98% of 99,441 orders):
  - 1,107 shipped orders (never confirmed delivered; lost in transit or indefinite 3PL delay).
  - 625 canceled orders.
  - 609 unavailable orders (seller stock-outs).
  - 622 orders trapped in early fulfillment stages (`invoiced`, `processing`, `created`, `approved`).
- **Rationale:** Conflating unfulfilled orders with delivered order delay days creates undefined arithmetic (`NULL - EDD`). They are tracked as an independent operational failure category via `view_unfulfilled_orders_breakdown`.
