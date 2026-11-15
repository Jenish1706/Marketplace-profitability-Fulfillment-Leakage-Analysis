-- ============================================================================
-- 04_KPI_LAYER.SQL: SIX-LAYER MODULAR ANALYTICAL KPI VIEWS
-- Project: Marketplace Profitability & Fulfillment Leakage Diagnostic
-- Dialect: DuckDB-first analytical SQL with PostgreSQL-portable queries
-- Purpose: Builds modular analytical views reflecting the 6-layer KPI framework:
--          1. Commercial Performance
--          2. Fulfillment Performance
--          3. Logistics Economics
--          4. Customer Experience
--          5. Economic Exposure (Level 1 Transaction & Level 2 Cost Burden)
--          6. Monthly Business Trend Integration
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. MONTHLY BUSINESS PERFORMANCE TREND VIEW (INTEGRATED 6-LAYER VIEW)
-- Filter: Core active operational window (Jan 2017 - Aug 2018)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW view_monthly_business_kpis AS
WITH order_monthly AS (
    SELECT 
        order_purchase_year_month AS year_month,
        COUNT(DISTINCT order_id) AS total_orders,
        SUM(CASE WHEN order_status = 'delivered' THEN 1 ELSE 0 END) AS delivered_orders,
        SUM(CASE WHEN order_status = 'delivered' AND is_late = 1 THEN 1 ELSE 0 END) AS late_orders,
        SUM(CASE WHEN order_status = 'canceled' THEN 1 ELSE 0 END) AS canceled_orders,
        ROUND(AVG(CASE WHEN order_status = 'delivered' THEN delivery_delay_days END), 2) AS avg_delivery_delay_days,
        ROUND(AVG(CASE WHEN order_status = 'delivered' AND is_late = 1 THEN delivery_delay_days END), 2) AS avg_delay_days_late_only,
        ROUND(AVG(avg_review_score), 2) AS avg_monthly_review_score,
        ROUND(100.0 * SUM(CASE WHEN is_low_review = 1 THEN 1 ELSE 0 END) / NULLIF(COUNT(avg_review_score), 0), 2) AS low_review_rate_pct
    FROM fact_orders
    WHERE order_purchase_year_month >= '2017-01' AND order_purchase_year_month <= '2018-08'
    GROUP BY order_purchase_year_month
),
item_monthly AS (
    SELECT 
        order_purchase_year_month AS year_month,
        COUNT(*) AS total_items,
        ROUND(SUM(item_price), 2) AS gmv,
        ROUND(SUM(freight_value), 2) AS total_freight,
        ROUND(AVG(item_price), 2) AS avg_item_price,
        
        -- Level 1: Transaction Exposure (Late Orders)
        ROUND(SUM(CASE WHEN is_late = 1 THEN item_price ELSE 0 END), 2) AS late_order_gmv_exposure,
        ROUND(SUM(CASE WHEN is_late = 1 THEN freight_value ELSE 0 END), 2) AS late_order_freight_exposure,
        ROUND(SUM(CASE WHEN is_late = 1 THEN (item_price + freight_value) ELSE 0 END), 2) AS total_late_order_exposure,
        
        -- Level 2: Cost Burden (High Freight Burden: freight_ratio >= 0.30)
        ROUND(SUM(CASE WHEN freight_ratio >= 0.30 THEN item_price ELSE 0 END), 2) AS high_freight_gmv_exposure,
        ROUND(SUM(CASE WHEN freight_ratio >= 0.30 THEN freight_value ELSE 0 END), 2) AS high_freight_value_exposure,
        COUNT(CASE WHEN freight_ratio >= 0.30 THEN 1 END) AS high_freight_items_count
    FROM fact_order_items
    WHERE order_purchase_year_month >= '2017-01' AND order_purchase_year_month <= '2018-08'
    GROUP BY order_purchase_year_month
)
SELECT 
    o.year_month,
    
    -- 1. Commercial Performance
    o.total_orders,
    i.total_items,
    i.gmv,
    ROUND(i.gmv / NULLIF(o.total_orders, 0), 2) AS aov,
    i.avg_item_price,
    
    -- 2. Fulfillment Performance
    o.delivered_orders,
    o.late_orders,
    ROUND(100.0 * o.late_orders / NULLIF(o.delivered_orders, 0), 2) AS late_delivery_rate_pct,
    o.canceled_orders,
    ROUND(100.0 * o.canceled_orders / NULLIF(o.total_orders, 0), 2) AS cancellation_rate_pct,
    o.avg_delivery_delay_days,
    o.avg_delay_days_late_only,
    
    -- 3. Logistics Economics
    i.total_freight,
    ROUND(i.total_freight / NULLIF(o.total_orders, 0), 2) AS freight_per_order,
    ROUND(100.0 * i.total_freight / NULLIF(i.gmv, 0), 2) AS freight_burden_pct,
    ROUND(100.0 * i.high_freight_items_count / NULLIF(i.total_items, 0), 2) AS high_freight_item_pct,
    
    -- 4. Customer Experience
    o.avg_monthly_review_score,
    o.low_review_rate_pct,
    
    -- 5. Economic Exposure (Observable)
    i.late_order_gmv_exposure,
    i.late_order_freight_exposure,
    i.total_late_order_exposure,
    ROUND(100.0 * i.total_late_order_exposure / NULLIF(i.gmv + i.total_freight, 0), 2) AS late_exposure_rate_pct,
    i.high_freight_gmv_exposure

FROM order_monthly o
JOIN item_monthly i ON o.year_month = i.year_month
ORDER BY o.year_month;

-- ----------------------------------------------------------------------------
-- 2. EXECUTIVE LIFETIME KPI SUMMARY CARDS
-- Strictly decouples order grain (fact_orders: 99,441 rows) from line-item grain
-- (fact_order_items: 112,650 rows) via CTE cross-join to eliminate fan-out distortion.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW view_executive_kpi_summary AS
WITH order_stats AS (
    SELECT 
        COUNT(order_id) AS total_orders,
        ROUND(100.0 * SUM(CASE WHEN order_status = 'delivered' THEN 1 ELSE 0 END) / COUNT(order_id), 2) AS delivered_rate_pct,
        ROUND(100.0 * SUM(CASE WHEN order_status = 'delivered' AND is_late = 1 THEN 1 ELSE 0 END) / 
              NULLIF(SUM(CASE WHEN order_status = 'delivered' THEN 1 ELSE 0 END), 0), 2) AS overall_late_rate_pct,
        ROUND(100.0 * SUM(CASE WHEN order_status = 'canceled' THEN 1 ELSE 0 END) / COUNT(order_id), 2) AS cancellation_rate_pct,
        ROUND(AVG(avg_review_score), 2) AS overall_avg_review_score,
        ROUND(100.0 * SUM(CASE WHEN is_low_review = 1 THEN 1 ELSE 0 END) / NULLIF(COUNT(avg_review_score), 0), 2) AS low_review_rate_pct
    FROM fact_orders
),
item_stats AS (
    SELECT 
        COUNT(order_item_id) AS total_items_sold,
        ROUND(SUM(item_price), 2) AS total_gmv,
        ROUND(SUM(freight_value), 2) AS total_freight,
        ROUND(100.0 * SUM(freight_value) / NULLIF(SUM(item_price), 0), 2) AS overall_freight_burden_pct,
        ROUND(SUM(CASE WHEN is_late = 1 THEN item_price ELSE 0 END), 2) AS total_late_order_gmv_exposure,
        ROUND(SUM(CASE WHEN is_late = 1 THEN freight_value ELSE 0 END), 2) AS total_late_order_freight_exposure,
        ROUND(SUM(CASE WHEN is_late = 1 THEN (item_price + freight_value) ELSE 0 END), 2) AS total_late_transaction_exposure,
        ROUND(SUM(CASE WHEN freight_ratio >= 0.30 THEN item_price ELSE 0 END), 2) AS total_high_freight_gmv_exposure
    FROM fact_order_items
)
SELECT 
    o.total_orders,
    i.total_items_sold,
    i.total_gmv,
    i.total_freight,
    ROUND(i.total_gmv / NULLIF(o.total_orders, 0), 2) AS platform_aov,
    o.delivered_rate_pct,
    o.overall_late_rate_pct,
    o.cancellation_rate_pct,
    i.overall_freight_burden_pct,
    ROUND(i.total_freight / NULLIF(o.total_orders, 0), 2) AS avg_freight_per_order,
    o.overall_avg_review_score,
    o.low_review_rate_pct,
    i.total_late_order_gmv_exposure,
    i.total_late_order_freight_exposure,
    i.total_late_transaction_exposure,
    i.total_high_freight_gmv_exposure
FROM order_stats o
CROSS JOIN item_stats i;
