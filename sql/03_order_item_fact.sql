-- ============================================================================
-- 03_ORDER_ITEM_FACT.SQL: CONTROLLED ANALYTICAL FACT TABLES
-- Project: Marketplace Profitability & Fulfillment Leakage Diagnostic
-- Dialect: DuckDB-first analytical SQL with PostgreSQL-portable queries
-- Purpose: Builds the foundational fact tables at two controlled grains:
--          1. fact_order_items (Line-item grain: order_id + order_item_id)
--          2. fact_orders (Order grain: order_id)
--          Explicitly deduplicates reviews and payments to eliminate fan-out.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- STEP 1: PRE-AGGREGATE REVIEWS TO ORDER GRAIN
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW int_order_reviews_dedup AS
SELECT 
    order_id,
    ROUND(AVG(review_score), 2) AS avg_review_score,
    MIN(review_score) AS min_review_score,
    MAX(review_score) AS max_review_score,
    COUNT(review_id) AS total_reviews_for_order
FROM olist_order_reviews
GROUP BY order_id;

-- ----------------------------------------------------------------------------
-- STEP 2: PRE-AGGREGATE PAYMENTS TO ORDER GRAIN
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW int_order_payments_rollup AS
SELECT 
    order_id,
    ROUND(SUM(payment_value), 2) AS total_payment_value,
    MAX(payment_installments) AS max_installments,
    COUNT(payment_sequential) AS payment_methods_count,
    STRING_AGG(DISTINCT payment_type, ', ') AS payment_types_used
FROM olist_order_payments
GROUP BY order_id;

-- ----------------------------------------------------------------------------
-- STEP 3: BUILD FACT_ORDER_ITEMS (Grain: order_id + order_item_id)
-- Exactly 112,650 rows representing individual line items sold.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE TABLE fact_order_items AS
SELECT 
    -- Primary line-item keys
    oi.order_id,
    oi.order_item_id,
    
    -- Foreign entity keys
    oi.seller_id,
    oi.product_id,
    o.customer_id,
    c.customer_unique_id,
    
    -- Status & Timestamps
    o.order_status,
    o.order_purchase_timestamp,
    CAST(o.order_purchase_timestamp AS DATE) AS order_purchase_date,
    STRFTIME(CAST(o.order_purchase_timestamp AS TIMESTAMP), '%Y-%m') AS order_purchase_year_month,
    o.order_approved_at,
    o.order_delivered_carrier_date,
    o.order_delivered_customer_date,
    o.order_estimated_delivery_date,
    oi.shipping_limit_date,
    
    -- Financials (Observed)
    oi.price AS item_price,
    oi.freight_value,
    ROUND(oi.price + oi.freight_value, 2) AS total_item_cost_to_buyer,
    
    -- Derived Financial Ratios (Level 2 Cost Burden)
    ROUND(oi.freight_value / NULLIF(oi.price, 0), 4) AS freight_ratio,
    CASE 
        WHEN oi.freight_value / NULLIF(oi.price, 0) < 0.15 THEN '1. Low (<15%)'
        WHEN oi.freight_value / NULLIF(oi.price, 0) < 0.30 THEN '2. Moderate (15-30%)'
        WHEN oi.freight_value / NULLIF(oi.price, 0) < 0.50 THEN '3. High (30-50%)'
        ELSE '4. Extreme (>50%)'
    END AS freight_burden_band,
    
    -- Value Banding (Categorizes merchandise ticket size into standard commercial tiers)
    CASE 
        WHEN oi.price < 50 THEN '1. Under R$50'
        WHEN oi.price < 100 THEN '2. R$50 - R$100'
        WHEN oi.price < 250 THEN '3. R$100 - R$250'
        WHEN oi.price < 500 THEN '4. R$250 - R$500'
        ELSE '5. R$500+'
    END AS order_value_band,

    -- Fulfillment Performance Attributes
    CASE 
        WHEN o.order_status = 'delivered' AND o.order_delivered_customer_date IS NOT NULL THEN 1 
        ELSE 0 
    END AS is_delivered,
    
    CASE 
        WHEN o.order_status = 'delivered' 
         AND CAST(o.order_delivered_customer_date AS DATE) > CAST(o.order_estimated_delivery_date AS DATE) 
        THEN 1 
        ELSE 0 
    END AS is_late,
    
    -- P0-2 Decomposition: Seller Dispatch Delay vs Carrier Transit Delay
    CASE 
        WHEN o.order_delivered_carrier_date IS NOT NULL AND o.order_delivered_carrier_date > oi.shipping_limit_date 
        THEN 1 
        ELSE 0 
    END AS is_seller_late_dispatch,
    
    CASE 
        WHEN o.order_status = 'delivered' 
         AND CAST(o.order_delivered_customer_date AS DATE) > CAST(o.order_estimated_delivery_date AS DATE)
         AND o.order_delivered_carrier_date > oi.shipping_limit_date 
        THEN 1 
        ELSE 0 
    END AS is_seller_caused_late,
    
    CASE 
        WHEN o.order_status = 'delivered' 
         AND CAST(o.order_delivered_customer_date AS DATE) > CAST(o.order_estimated_delivery_date AS DATE)
         AND (o.order_delivered_carrier_date IS NULL OR o.order_delivered_carrier_date <= oi.shipping_limit_date) 
        THEN 1 
        ELSE 0 
    END AS is_carrier_caused_late,
    
    CASE 
        WHEN o.order_status = 'delivered' AND o.order_delivered_customer_date IS NOT NULL 
        THEN DATE_DIFF('day', CAST(o.order_estimated_delivery_date AS DATE), CAST(o.order_delivered_customer_date AS DATE))
        ELSE NULL
    END AS delivery_delay_days,
    
    CASE 
        WHEN o.order_status <> 'delivered' OR o.order_delivered_customer_date IS NULL THEN 'Undelivered / In-Transit'
        WHEN CAST(o.order_delivered_customer_date AS DATE) <= CAST(o.order_estimated_delivery_date AS DATE) THEN '1. On-Time / Early'
        WHEN DATE_DIFF('day', CAST(o.order_estimated_delivery_date AS DATE), CAST(o.order_delivered_customer_date AS DATE)) <= 2 THEN '2. 1-2 Days Late'
        WHEN DATE_DIFF('day', CAST(o.order_estimated_delivery_date AS DATE), CAST(o.order_delivered_customer_date AS DATE)) <= 5 THEN '3. 3-5 Days Late'
        ELSE '4. >5 Days Late'
    END AS delay_bucket,
    
    -- Geographic Lane & Corridor Attributes
    s.seller_state,
    s.seller_city,
    c.customer_state,
    c.customer_city,
    (s.seller_state || ' -> ' || c.customer_state) AS corridor,
    CASE WHEN s.seller_state <> c.customer_state THEN 1 ELSE 0 END AS is_interstate,
    
    -- Product Catalog & Physical Dimensional Attributes
    COALESCE(t.product_category_name_english, p.product_category_name, 'unknown') AS product_category,
    p.product_weight_g,
    ROUND(p.product_weight_g / 1000.0, 3) AS product_weight_kg,
    ROUND((p.product_length_cm * p.product_height_cm * p.product_width_cm) / 1000.0, 2) AS product_volume_cm3,
    ROUND(oi.freight_value / NULLIF(p.product_weight_g / 1000.0, 0), 2) AS freight_per_kg,
    
    -- Deduplicated Customer Experience
    r.avg_review_score AS order_review_score,
    CASE WHEN r.avg_review_score <= 2 THEN 1 ELSE 0 END AS is_low_review

FROM olist_order_items oi
JOIN olist_orders o ON oi.order_id = o.order_id
LEFT JOIN olist_sellers s ON oi.seller_id = s.seller_id
LEFT JOIN olist_customers c ON o.customer_id = c.customer_id
LEFT JOIN olist_products p ON oi.product_id = p.product_id
LEFT JOIN product_category_name_translation t ON p.product_category_name = t.product_category_name
LEFT JOIN int_order_reviews_dedup r ON o.order_id = r.order_id;

-- ----------------------------------------------------------------------------
-- STEP 4: BUILD FACT_ORDERS (Grain: order_id)
-- Exactly 99,441 rows representing distinct customer orders.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE TABLE fact_orders AS
WITH order_item_aggregates AS (
    SELECT 
        order_id,
        COUNT(order_item_id) AS total_items,
        COUNT(DISTINCT seller_id) AS distinct_sellers,
        COUNT(DISTINCT product_id) AS distinct_products,
        MAX(shipping_limit_date) AS max_shipping_limit_date,
        ROUND(SUM(price), 2) AS gmv,
        ROUND(SUM(freight_value), 2) AS total_freight,
        ROUND(SUM(freight_value) / NULLIF(SUM(price), 0), 4) AS order_freight_burden
    FROM olist_order_items
    GROUP BY order_id
)
SELECT 
    o.order_id,
    o.customer_id,
    c.customer_unique_id,
    o.order_status,
    o.order_purchase_timestamp,
    CAST(o.order_purchase_timestamp AS DATE) AS order_purchase_date,
    STRFTIME(CAST(o.order_purchase_timestamp AS TIMESTAMP), '%Y-%m') AS order_purchase_year_month,
    o.order_approved_at,
    o.order_delivered_carrier_date,
    o.order_delivered_customer_date,
    o.order_estimated_delivery_date,
    
    -- Location
    c.customer_state,
    c.customer_city,
    
    -- Commercial Totals (NULL if order has no items, e.g. canceled prior to booking)
    COALESCE(oia.total_items, 0) AS total_items,
    COALESCE(oia.distinct_sellers, 0) AS distinct_sellers,
    CASE WHEN COALESCE(oia.distinct_sellers, 0) > 1 THEN 1 ELSE 0 END AS is_multi_seller,
    COALESCE(oia.gmv, 0.0) AS gmv,
    COALESCE(oia.total_freight, 0.0) AS total_freight,
    ROUND(COALESCE(oia.gmv, 0.0) + COALESCE(oia.total_freight, 0.0), 2) AS total_order_value,
    oia.order_freight_burden,
    
    -- Fulfillment Performance
    CASE 
        WHEN o.order_status = 'delivered' AND o.order_delivered_customer_date IS NOT NULL THEN 1 
        ELSE 0 
    END AS is_delivered,
    
    CASE 
        WHEN o.order_status = 'delivered' 
         AND CAST(o.order_delivered_customer_date AS DATE) > CAST(o.order_estimated_delivery_date AS DATE) 
        THEN 1 
        ELSE 0 
    END AS is_late,
    
    -- P0-2 Decomposition: Seller Dispatch Delay vs Carrier Transit Delay
    CASE 
        WHEN o.order_delivered_carrier_date IS NOT NULL AND o.order_delivered_carrier_date > oia.max_shipping_limit_date 
        THEN 1 
        ELSE 0 
    END AS is_seller_late_dispatch,
    
    CASE 
        WHEN o.order_status = 'delivered' 
         AND CAST(o.order_delivered_customer_date AS DATE) > CAST(o.order_estimated_delivery_date AS DATE)
         AND o.order_delivered_carrier_date > oia.max_shipping_limit_date 
        THEN 1 
        ELSE 0 
    END AS is_seller_caused_late,
    
    CASE 
        WHEN o.order_status = 'delivered' 
         AND CAST(o.order_delivered_customer_date AS DATE) > CAST(o.order_estimated_delivery_date AS DATE)
         AND (o.order_delivered_carrier_date IS NULL OR o.order_delivered_carrier_date <= oia.max_shipping_limit_date) 
        THEN 1 
        ELSE 0 
    END AS is_carrier_caused_late,
    
    CASE 
        WHEN o.order_status = 'delivered' AND o.order_delivered_customer_date IS NOT NULL 
        THEN DATE_DIFF('day', CAST(o.order_estimated_delivery_date AS DATE), CAST(o.order_delivered_customer_date AS DATE))
        ELSE NULL
    END AS delivery_delay_days,
    
    -- Customer Satisfaction & Payments
    r.avg_review_score,
    CASE WHEN r.avg_review_score <= 2 THEN 1 ELSE 0 END AS is_low_review,
    p.total_payment_value,
    p.max_installments,
    p.payment_types_used

FROM olist_orders o
LEFT JOIN olist_customers c ON o.customer_id = c.customer_id
LEFT JOIN order_item_aggregates oia ON o.order_id = oia.order_id
LEFT JOIN int_order_reviews_dedup r ON o.order_id = r.order_id
LEFT JOIN int_order_payments_rollup p ON o.order_id = p.order_id;
