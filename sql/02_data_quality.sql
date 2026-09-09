-- ============================================================================
-- 02_DATA_QUALITY.SQL: SYSTEMATIC DATA QUALITY AUDIT SUITE
-- Project: Marketplace Profitability & Fulfillment Leakage Diagnostic
-- Dialect: DuckDB-first analytical SQL with PostgreSQL-portable queries
-- Purpose: Rigorously inspects table completeness, primary key uniqueness,
--          referential integrity, timestamp logic, and grain complications.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. RECORD COUNT RECONCILIATION
-- ----------------------------------------------------------------------------
SELECT 'olist_orders' AS table_name, COUNT(*) AS total_rows FROM olist_orders
UNION ALL
SELECT 'olist_order_items', COUNT(*) FROM olist_order_items
UNION ALL
SELECT 'olist_order_payments', COUNT(*) FROM olist_order_payments
UNION ALL
SELECT 'olist_order_reviews', COUNT(*) FROM olist_order_reviews
UNION ALL
SELECT 'olist_products', COUNT(*) FROM olist_products
UNION ALL
SELECT 'olist_sellers', COUNT(*) FROM olist_sellers
UNION ALL
SELECT 'olist_customers', COUNT(*) FROM olist_customers
UNION ALL
SELECT 'olist_geolocation', COUNT(*) FROM olist_geolocation
UNION ALL
SELECT 'product_category_name_translation', COUNT(*) FROM product_category_name_translation;

-- ----------------------------------------------------------------------------
-- 2. PRIMARY KEY UNIQUENESS AUDIT
-- Expected: 0 duplicate rows across all entity tables
-- ----------------------------------------------------------------------------
SELECT 'orders_pk_duplicate' AS check_name, COUNT(*) AS duplicate_count
FROM (
    SELECT order_id, COUNT(*) FROM olist_orders GROUP BY order_id HAVING COUNT(*) > 1
)
UNION ALL
SELECT 'order_items_pk_duplicate', COUNT(*)
FROM (
    SELECT order_id, order_item_id, COUNT(*) FROM olist_order_items GROUP BY order_id, order_item_id HAVING COUNT(*) > 1
)
UNION ALL
SELECT 'products_pk_duplicate', COUNT(*)
FROM (
    SELECT product_id, COUNT(*) FROM olist_products GROUP BY product_id HAVING COUNT(*) > 1
)
UNION ALL
SELECT 'sellers_pk_duplicate', COUNT(*)
FROM (
    SELECT seller_id, COUNT(*) FROM olist_sellers GROUP BY seller_id HAVING COUNT(*) > 1
)
UNION ALL
SELECT 'customers_pk_duplicate', COUNT(*)
FROM (
    SELECT customer_id, COUNT(*) FROM olist_customers GROUP BY customer_id HAVING COUNT(*) > 1
);

-- ----------------------------------------------------------------------------
-- 3. MULTI-ITEM & MULTI-SELLER GRAIN COMPLICATION AUDIT
-- Quantifies how many orders contain multiple items and multiple distinct sellers.
-- ----------------------------------------------------------------------------
WITH order_item_summary AS (
    SELECT 
        order_id,
        COUNT(*) AS item_count,
        COUNT(DISTINCT seller_id) AS seller_count,
        COUNT(DISTINCT product_id) AS distinct_product_count
    FROM olist_order_items
    GROUP BY order_id
)
SELECT 
    COUNT(*) AS total_orders_in_items,
    SUM(CASE WHEN item_count = 1 THEN 1 ELSE 0 END) AS single_item_orders,
    SUM(CASE WHEN item_count > 1 THEN 1 ELSE 0 END) AS multi_item_orders,
    ROUND(100.0 * SUM(CASE WHEN item_count > 1 THEN 1 ELSE 0 END) / COUNT(*), 2) AS multi_item_order_pct,
    SUM(CASE WHEN seller_count = 1 THEN 1 ELSE 0 END) AS single_seller_orders,
    SUM(CASE WHEN seller_count > 1 THEN 1 ELSE 0 END) AS multi_seller_orders,
    ROUND(100.0 * SUM(CASE WHEN seller_count > 1 THEN 1 ELSE 0 END) / COUNT(*), 2) AS multi_seller_order_pct
FROM order_item_summary;

-- ----------------------------------------------------------------------------
-- 4. ORDER STATUS & LIFECYCLE AUDIT
-- Documents order status breakdown and flags delivered orders with missing dates.
-- ----------------------------------------------------------------------------
SELECT 
    order_status,
    COUNT(*) AS order_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 2) AS order_pct,
    SUM(CASE WHEN order_delivered_customer_date IS NULL THEN 1 ELSE 0 END) AS missing_delivered_date_count,
    SUM(CASE WHEN order_approved_at IS NULL THEN 1 ELSE 0 END) AS missing_approved_date_count
FROM olist_orders
GROUP BY order_status
ORDER BY order_count DESC;

-- ----------------------------------------------------------------------------
-- 5. TIMESTAMP SEQUENCE LOGIC VALIDATION
-- Flags chronological anomalies in fulfillment timestamps.
-- ----------------------------------------------------------------------------
SELECT 
    'delivered_before_carrier' AS anomaly_type,
    COUNT(*) AS anomaly_count
FROM olist_orders
WHERE order_delivered_customer_date < order_delivered_carrier_date
UNION ALL
SELECT 
    'carrier_before_approved',
    COUNT(*)
FROM olist_orders
WHERE order_delivered_carrier_date < order_approved_at
UNION ALL
SELECT 
    'approved_before_purchase',
    COUNT(*)
FROM olist_orders
WHERE order_approved_at < order_purchase_timestamp;

-- ----------------------------------------------------------------------------
-- 6. REVIEWS & PAYMENTS FAN-OUT RISK AUDIT
-- Demonstrates that joining raw reviews or raw payments creates duplicate order items.
-- ----------------------------------------------------------------------------
SELECT 
    'orders_with_multiple_reviews' AS check_name,
    COUNT(*) AS order_count
FROM (
    SELECT order_id, COUNT(*) AS review_count
    FROM olist_order_reviews
    GROUP BY order_id
    HAVING COUNT(*) > 1
)
UNION ALL
SELECT 
    'orders_with_multiple_payments',
    COUNT(*)
FROM (
    SELECT order_id, COUNT(*) AS payment_count
    FROM olist_order_payments
    GROUP BY order_id
    HAVING COUNT(*) > 1
);

-- ----------------------------------------------------------------------------
-- 7. REFERENTIAL INTEGRITY / ORPHAN RECORD AUDIT
-- Confirms all foreign keys in order_items resolve cleanly to parent tables.
-- ----------------------------------------------------------------------------
SELECT 
    'items_without_orders' AS check_name,
    COUNT(*) AS orphan_count
FROM olist_order_items oi
LEFT JOIN olist_orders o ON oi.order_id = o.order_id
WHERE o.order_id IS NULL
UNION ALL
SELECT 
    'items_without_sellers',
    COUNT(*)
FROM olist_order_items oi
LEFT JOIN olist_sellers s ON oi.seller_id = s.seller_id
WHERE s.seller_id IS NULL
UNION ALL
SELECT 
    'items_without_products',
    COUNT(*)
FROM olist_order_items oi
LEFT JOIN olist_products p ON oi.product_id = p.product_id
WHERE p.product_id IS NULL;
