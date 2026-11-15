# Data Documentation & Lineage Dictionary

**Project:** Marketplace Profitability & Fulfillment Leakage Diagnostic  
**Dataset Source:** [Brazilian E-Commerce Public Dataset by Olist (Kaggle)](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)  
**Time Horizon:** September 2016 – October 2018 (Core active window: January 2017 – August 2018)  
**Geography:** Brazil (All 27 federal states and federal district)  

---

## 1. Raw Dataset Catalog & Record Reconciliation

The raw dataset comprises nine relational tables stored in `data/raw/`:

| Table Name | File Name | Record Count | Primary Key / Grain | Description |
|---|---|---|---|---|
| `olist_orders` | `olist_orders_dataset.csv` | 99,441 | `order_id` | Core order lifecycle table tracking status and fulfillment timestamps (purchase, approved, carrier dispatched, customer delivered, estimated delivery). |
| `olist_order_items` | `olist_order_items_dataset.csv` | 112,650 | `order_id + order_item_id` | Physical line items sold per order, containing item price, freight charge, seller ID, and shipping limit timestamp. |
| `olist_order_payments` | `olist_order_payments_dataset.csv` | 103,886 | `order_id + payment_sequential` | Payment transaction records capturing payment methods (credit card, boleto, voucher, debit), installments, and value. |
| `olist_order_reviews` | `olist_order_reviews_dataset.csv` | 99,224 | `review_id + order_id` | Customer post-purchase satisfaction reviews including numerical score (1–5), survey comments, and response timestamps. |
| `olist_products` | `olist_products_dataset.csv` | 32,951 | `product_id` | Product catalog with category designations and physical logistics specifications (weight in grams, length, height, width in cm). |
| `olist_sellers` | `olist_sellers_dataset.csv` | 3,095 | `seller_id` | Merchant directory with zip prefix, city, and state origins. |
| `olist_customers` | `olist_customers_dataset.csv` | 99,441 | `customer_id` | Buyer directory linking transaction instances (`customer_id`) to unique human buyers (`customer_unique_id`) and regional delivery locations. |
| `olist_geolocation` | `olist_geolocation_dataset.csv` | 1,000,163 | `zip_code_prefix + lat + lng` | Brazilian geographic coordinate mapping for postal codes. |
| `product_category_name_translation` | `product_category_name_translation.csv` | 71 | `product_category_name` | Translation dictionary mapping Portuguese catalog categories to standardized English names. |

---

## 2. Critical Relational Grains & Deduplication Guardrails

### The Multi-Item & Multi-Seller Complication
A foundational complexity of the Olist dataset is that **an order can contain multiple items, and each item can be fulfilled by a different seller**:
- **Total Orders with Items:** 98,666 distinct orders.
- **Single-Item Orders:** 84,986 orders (86.1%).
- **Multi-Item Orders:** 13,680 orders (13.9% of orders contain 2 to 21 line items).
- **Multi-Seller Orders:** 1,278 orders involve split fulfillment across multiple distinct merchants.

### Controlled Analytical Modeling
To prevent fan-out multiplication of commercial totals:
1. **`fact_order_items` (Line-Item Grain):** Contains exactly 112,650 rows representing one physical line item. Financial sums across this table reconcile perfectly with raw totals (Total GMV: R$ 13,591,643.70; Total Freight: R$ 2,251,909.54).
2. **`fact_orders` (Order Grain):** Contains exactly 99,441 rows representing distinct order entities. Operational rates (e.g. 97.02% delivery rate, 0.63% cancellation rate) are strictly calculated at this grain.
3. **Decoupled KPI Aggregation:** In executive KPI summaries, order-level status counts are isolated into dedicated CTEs and decoupled from line-item counts. Naive joins calculate 110,197 delivered items against 98,666 itemized orders (an invalid 111.69%), whereas decoupled aggregation produces the exact 97.02% delivered order rate.
4. **Order Value Tiering:** Commercial pricing is categorized into five standardized tiers: `1. Under R$50`, `2. R$50 - R$100`, `3. R$100 - R$250`, `4. R$250 - R$500`, `5. R$500+`.
5. **Reviews Deduplication:** Multiple review responses for a single order are pre-aggregated to the mean score (`ROUND(AVG(review_score), 2)`) before joining to fact tables.
6. **Payments Deduplication:** Split payments (e.g., voucher + credit card installments) are rolled up to `total_payment_value` at the order grain before joining.

---

## 3. Data Quality & Inclusion Rules

1. **Delivered Status Audit:** Out of 96,478 orders marked with `order_status = 'delivered'`, exactly 8 records lack a customer delivery timestamp (`order_delivered_customer_date IS NULL`). These are excluded from delay duration calculations but retained in volume reconciliations.
2. **Fulfillment Delay Calculation:**
   $$\text{Delivery Delay Days} = \text{DateDiff}('day', \text{order\_estimated\_delivery\_date}, \text{order\_delivered\_customer\_date})$$
   - Delivered on or before EDD: $\text{Delay Days} \le 0$ (On-Time / Early).
   - Delivered after EDD: $\text{Delay Days} > 0$ (Late).
3. **Active Operating Window:** The platform began initial pilot transactions in late 2016 and ceased recording in October 2018. The active, statistically valid operating window used for monthly trends is **January 2017 through August 2018 (20 consecutive months)**.

