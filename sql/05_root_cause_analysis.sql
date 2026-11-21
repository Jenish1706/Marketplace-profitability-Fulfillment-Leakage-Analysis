-- ============================================================================
-- 05_ROOT_CAUSE_ANALYSIS.SQL: MULTI-DIMENSIONAL DECOMPOSITION
-- Project: Marketplace Profitability & Fulfillment Leakage Diagnostic
-- Dialect: DuckDB-first analytical SQL with PostgreSQL-portable queries
-- Purpose: Deconstructs operational failures and economic exposure across:
--          1. Seller Performance & Volume vs Severity decoupling
--          2. Category Structural Logistics Economics (Weight, Cube, Freight/kg)
--          3. Geographic Fulfillment Corridors (Origin-Destination Lanes)
--          4. Order Value vs Freight Burden Matrix
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. SELLER PERFORMANCE SCORECARD VIEW
-- Evaluates sellers across volume, operational severity, and economic exposure.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW view_seller_root_cause AS
SELECT 
    oi.seller_id,
    COALESCE(s.seller_state, 'Unknown') AS seller_state,
    COALESCE(s.seller_city, 'Unknown') AS seller_city,
    
    -- Volume & Scale
    COUNT(DISTINCT oi.order_id) AS total_orders,
    COUNT(oi.order_item_id) AS total_items,
    ROUND(SUM(oi.item_price), 2) AS gmv,
    ROUND(SUM(oi.freight_value), 2) AS total_freight,
    ROUND(SUM(oi.item_price) / COUNT(DISTINCT oi.order_id), 2) AS seller_aov,
    
    -- Fulfillment Performance
    SUM(CASE WHEN oi.is_delivered = 1 THEN 1 ELSE 0 END) AS delivered_items,
    SUM(CASE WHEN oi.is_late = 1 THEN 1 ELSE 0 END) AS late_items,
    ROUND(100.0 * SUM(CASE WHEN oi.is_late = 1 THEN 1 ELSE 0 END) / 
          NULLIF(SUM(CASE WHEN oi.is_delivered = 1 THEN 1 ELSE 0 END), 0), 2) AS late_item_rate_pct,
    
    -- P0-2 Decomposition: Seller dispatch delay vs post-handover delay (carrier_* column names kept for compatibility)
    SUM(CASE WHEN oi.is_seller_caused_late = 1 THEN 1 ELSE 0 END) AS seller_late_items,
    ROUND(100.0 * SUM(CASE WHEN oi.is_seller_caused_late = 1 THEN 1 ELSE 0 END) / 
          NULLIF(SUM(CASE WHEN oi.is_delivered = 1 THEN 1 ELSE 0 END), 0), 2) AS seller_late_item_rate_pct,
    SUM(CASE WHEN oi.is_carrier_caused_late = 1 THEN 1 ELSE 0 END) AS carrier_late_items,
    ROUND(100.0 * SUM(CASE WHEN oi.is_carrier_caused_late = 1 THEN 1 ELSE 0 END) / 
          NULLIF(SUM(CASE WHEN oi.is_delivered = 1 THEN 1 ELSE 0 END), 0), 2) AS carrier_late_item_rate_pct,
    
    ROUND(AVG(CASE WHEN oi.is_late = 1 THEN oi.delivery_delay_days END), 2) AS avg_delay_days_late_items,
    
    -- Logistics Economics (Level 2 Cost Burden)
    ROUND(100.0 * SUM(oi.freight_value) / NULLIF(SUM(oi.item_price), 0), 2) AS freight_burden_pct,
    
    -- Customer Experience
    ROUND(AVG(oi.order_review_score), 2) AS avg_review_score,
    ROUND(100.0 * SUM(CASE WHEN oi.is_low_review = 1 THEN 1 ELSE 0 END) / COUNT(*), 2) AS low_review_rate_pct,
    
    -- Level 1: Transaction Exposure
    ROUND(SUM(CASE WHEN oi.is_late = 1 THEN oi.item_price ELSE 0 END), 2) AS late_gmv_exposure,
    ROUND(SUM(CASE WHEN oi.is_late = 1 THEN oi.freight_value ELSE 0 END), 2) AS late_freight_exposure,
    ROUND(SUM(CASE WHEN oi.is_late = 1 THEN (oi.item_price + oi.freight_value) ELSE 0 END), 2) AS total_late_transaction_exposure,
    ROUND(SUM(CASE WHEN oi.is_seller_caused_late = 1 THEN (oi.item_price + oi.freight_value) ELSE 0 END), 2) AS seller_late_exposure,
    ROUND(SUM(CASE WHEN oi.is_carrier_caused_late = 1 THEN (oi.item_price + oi.freight_value) ELSE 0 END), 2) AS carrier_late_exposure,
    
    -- Level 2: High-Freight Burden Exposure (freight_ratio >= 0.30)
    ROUND(SUM(CASE WHEN oi.freight_ratio >= 0.30 THEN oi.item_price ELSE 0 END), 2) AS high_freight_gmv_exposure,
    
    -- Operational Volume Threshold Flag (Minimum N >= 30)
    CASE WHEN COUNT(DISTINCT oi.order_id) >= 30 THEN 1 ELSE 0 END AS meets_min_volume_30

FROM fact_order_items oi
LEFT JOIN olist_sellers s ON oi.seller_id = s.seller_id
GROUP BY oi.seller_id, s.seller_state, s.seller_city;

-- ----------------------------------------------------------------------------
-- 2. CATEGORY LOGISTICS ECONOMICS VIEW
-- Identifies categories suffering structural unit-economics deficits.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW view_category_root_cause AS
SELECT 
    oi.product_category,
    
    -- Commercial Volume
    COUNT(DISTINCT oi.order_id) AS total_orders,
    COUNT(oi.order_item_id) AS total_items,
    ROUND(SUM(oi.item_price), 2) AS gmv,
    ROUND(SUM(oi.freight_value), 2) AS total_freight,
    ROUND(SUM(oi.item_price) / COUNT(DISTINCT oi.order_id), 2) AS aov,
    ROUND(AVG(oi.item_price), 2) AS avg_item_price,
    
    -- Physical Dimensions & Freight Intensity
    ROUND(AVG(oi.product_weight_kg), 3) AS avg_weight_kg,
    ROUND(AVG(oi.product_volume_cm3), 2) AS avg_volume_cm3,
    ROUND(AVG(oi.freight_per_kg), 2) AS avg_freight_per_kg,
    
    -- Logistics Burden
    ROUND(100.0 * SUM(oi.freight_value) / NULLIF(SUM(oi.item_price), 0), 2) AS freight_burden_pct,
    ROUND(100.0 * SUM(CASE WHEN oi.freight_ratio >= 0.30 THEN 1 ELSE 0 END) / COUNT(*), 2) AS high_freight_item_pct,
    
    -- Fulfillment Performance
    SUM(CASE WHEN oi.is_delivered = 1 THEN 1 ELSE 0 END) AS delivered_items,
    SUM(CASE WHEN oi.is_late = 1 THEN 1 ELSE 0 END) AS late_items,
    ROUND(100.0 * SUM(CASE WHEN oi.is_late = 1 THEN 1 ELSE 0 END) / 
          NULLIF(SUM(CASE WHEN oi.is_delivered = 1 THEN 1 ELSE 0 END), 0), 2) AS late_delivery_rate_pct,
    
    -- Customer Experience
    ROUND(AVG(oi.order_review_score), 2) AS avg_review_score,
    ROUND(100.0 * SUM(CASE WHEN oi.is_low_review = 1 THEN 1 ELSE 0 END) / COUNT(*), 2) AS low_review_rate_pct,
    
    -- Exposure Metrics
    ROUND(SUM(CASE WHEN oi.is_late = 1 THEN (oi.item_price + oi.freight_value) ELSE 0 END), 2) AS late_transaction_exposure,
    ROUND(SUM(CASE WHEN oi.freight_ratio >= 0.30 THEN oi.item_price ELSE 0 END), 2) AS high_freight_gmv_exposure

FROM fact_order_items oi
GROUP BY oi.product_category;

-- ----------------------------------------------------------------------------
-- 3. GEOGRAPHIC FULFILLMENT CORRIDOR VIEW (ORIGIN -> DESTINATION LANES)
-- Pinpoints interstate logistics corridors with disproportionate friction.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW view_corridor_root_cause AS
SELECT 
    oi.seller_state,
    oi.customer_state,
    oi.corridor,
    oi.is_interstate,
    
    -- Volume
    COUNT(DISTINCT oi.order_id) AS total_orders,
    COUNT(oi.order_item_id) AS total_items,
    ROUND(SUM(oi.item_price), 2) AS gmv,
    ROUND(SUM(oi.freight_value), 2) AS total_freight,
    
    -- Logistics Burden
    ROUND(100.0 * SUM(oi.freight_value) / NULLIF(SUM(oi.item_price), 0), 2) AS freight_burden_pct,
    ROUND(SUM(oi.freight_value) / COUNT(DISTINCT oi.order_id), 2) AS avg_freight_per_order,
    
    -- Fulfillment Performance
    SUM(CASE WHEN oi.is_delivered = 1 THEN 1 ELSE 0 END) AS delivered_items,
    SUM(CASE WHEN oi.is_late = 1 THEN 1 ELSE 0 END) AS late_items,
    ROUND(100.0 * SUM(CASE WHEN oi.is_late = 1 THEN 1 ELSE 0 END) / 
          NULLIF(SUM(CASE WHEN oi.is_delivered = 1 THEN 1 ELSE 0 END), 0), 2) AS late_delivery_rate_pct,
    
    -- P0-2 Decomposition: Post-handover vs Seller Dispatch Breakdown by Corridor
    SUM(CASE WHEN oi.is_carrier_caused_late = 1 THEN 1 ELSE 0 END) AS carrier_late_items,
    ROUND(100.0 * SUM(CASE WHEN oi.is_carrier_caused_late = 1 THEN 1 ELSE 0 END) / 
          NULLIF(SUM(CASE WHEN oi.is_delivered = 1 THEN 1 ELSE 0 END), 0), 2) AS carrier_late_rate_pct,
    ROUND(SUM(CASE WHEN oi.is_carrier_caused_late = 1 THEN (oi.item_price + oi.freight_value) ELSE 0 END), 2) AS carrier_late_transaction_exposure,
    SUM(CASE WHEN oi.is_seller_caused_late = 1 THEN 1 ELSE 0 END) AS seller_late_items,
    ROUND(SUM(CASE WHEN oi.is_seller_caused_late = 1 THEN (oi.item_price + oi.freight_value) ELSE 0 END), 2) AS seller_late_transaction_exposure,
    
    ROUND(AVG(CASE WHEN oi.is_delivered = 1 THEN oi.delivery_delay_days END), 2) AS avg_delay_days,
    ROUND(AVG(CASE WHEN oi.is_late = 1 THEN oi.delivery_delay_days END), 2) AS avg_delay_days_late_items,
    
    -- Customer Experience
    ROUND(AVG(oi.order_review_score), 2) AS avg_review_score,
    ROUND(100.0 * SUM(CASE WHEN oi.is_low_review = 1 THEN 1 ELSE 0 END) / COUNT(*), 2) AS low_review_rate_pct,
    
    -- Exposure
    ROUND(SUM(CASE WHEN oi.is_late = 1 THEN (oi.item_price + oi.freight_value) ELSE 0 END), 2) AS late_transaction_exposure

FROM fact_order_items oi
WHERE oi.seller_state IS NOT NULL AND oi.customer_state IS NOT NULL
GROUP BY oi.seller_state, oi.customer_state, oi.corridor, oi.is_interstate;

-- ----------------------------------------------------------------------------
-- 4. ORDER VALUE BAND × FREIGHT BURDEN INTERACTION MATRIX
-- Demonstrates how lower-priced items carry punitive logistics burdens.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW view_value_freight_matrix AS
SELECT 
    order_value_band,
    freight_burden_band,
    COUNT(DISTINCT order_id) AS total_orders,
    COUNT(order_item_id) AS total_items,
    ROUND(SUM(item_price), 2) AS total_gmv,
    ROUND(SUM(freight_value), 2) AS total_freight,
    ROUND(100.0 * SUM(freight_value) / NULLIF(SUM(item_price), 0), 2) AS freight_burden_pct,
    ROUND(100.0 * SUM(is_late) / NULLIF(SUM(is_delivered), 0), 2) AS late_rate_pct,
    ROUND(AVG(order_review_score), 2) AS avg_review_score
FROM fact_order_items
GROUP BY order_value_band, freight_burden_band
ORDER BY order_value_band, freight_burden_band;

-- ----------------------------------------------------------------------------
-- 6. POST-HANDOVER DELAY: TRANSIT VS PROMISE (MP-09)
-- Terminology: a late delivery whose seller handed the parcel over by
-- shipping_limit_date is called a POST-HANDOVER delay. The identifier
-- is_carrier_caused_late is kept for compatibility, but the data cannot name the
-- party responsible: the second gate is the platform's PROMISED date
-- (order_estimated_delivery_date), not a carrier SLA, and there are no carrier scans.
-- This view supports the test that separates "the leg took long" (transit) from
-- "the promise was tight" (promise-setting).
-- One row per delivered (order, seller) pair with a recorded handover date that is
-- not after the delivery date. Day counts are date-level (same convention as is_late).
--   promise_days      = purchase date  -> promised date
--   pre_handover_days = purchase date  -> handover date
--   transit_days      = handover date  -> delivery date
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW view_post_handover_pairs AS
WITH pairs AS (
    SELECT
        order_id,
        seller_id,
        ANY_VALUE(corridor) AS corridor,
        CAST(MIN(order_purchase_timestamp) AS DATE) AS purchase_date,
        CAST(MIN(order_delivered_carrier_date) AS DATE) AS handover_date,
        CAST(MIN(order_delivered_customer_date) AS DATE) AS delivered_date,
        CAST(MIN(order_estimated_delivery_date) AS DATE) AS promised_date,
        MAX(is_late) AS is_late,
        MAX(is_seller_caused_late) AS seller_caused
    FROM fact_order_items
    WHERE is_delivered = 1
    GROUP BY order_id, seller_id
)
SELECT
    order_id,
    seller_id,
    corridor,
    purchase_date,
    handover_date,
    delivered_date,
    promised_date,
    CASE
        WHEN is_late = 0 THEN 'on_time'
        WHEN seller_caused = 1 THEN 'late_seller_dispatch'
        ELSE 'late_post_handover'
    END AS delay_class,
    DATE_DIFF('day', purchase_date, promised_date) AS promise_days,
    DATE_DIFF('day', purchase_date, handover_date) AS pre_handover_days,
    DATE_DIFF('day', handover_date, delivered_date) AS transit_days
FROM pairs
WHERE handover_date IS NOT NULL
  AND handover_date <= delivered_date;
