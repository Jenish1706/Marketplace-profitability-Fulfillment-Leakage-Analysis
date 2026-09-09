-- ============================================================================
-- 06_PARETO_ANALYSIS.SQL: CUMULATIVE CONCENTRATION WINDOW QUERIES
-- Project: Marketplace Profitability & Fulfillment Leakage Diagnostic
-- Dialect: DuckDB-first analytical SQL with PostgreSQL-portable queries
-- Purpose: Employs analytical window functions to quantify the degree of
--          economic exposure concentration across sellers, categories, and lanes.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. SELLER EXPOSURE PARETO CUMULATIVE DISTRIBUTION VIEW
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW view_pareto_sellers AS
WITH seller_base AS (
    SELECT 
        seller_id,
        seller_state,
        total_orders,
        total_items,
        gmv,
        late_items,
        late_item_rate_pct,
        total_late_transaction_exposure,
        meets_min_volume_30
    FROM view_seller_root_cause
    WHERE total_late_transaction_exposure > 0
),
ranked_sellers AS (
    SELECT 
        seller_id,
        seller_state,
        total_orders,
        gmv,
        late_items,
        late_item_rate_pct,
        total_late_transaction_exposure,
        meets_min_volume_30,
        ROW_NUMBER() OVER (ORDER BY total_late_transaction_exposure DESC) AS seller_rank,
        COUNT(*) OVER () AS total_exposed_sellers,
        (SELECT COUNT(*) FROM olist_sellers) AS total_marketplace_sellers,
        SUM(total_late_transaction_exposure) OVER (
            ORDER BY total_late_transaction_exposure DESC 
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS cumulative_late_exposure,
        SUM(total_late_transaction_exposure) OVER () AS total_platform_late_exposure
    FROM seller_base
)
SELECT 
    seller_rank,
    seller_id,
    seller_state,
    total_orders,
    gmv,
    late_items,
    late_item_rate_pct,
    total_late_transaction_exposure,
    meets_min_volume_30,
    ROUND(100.0 * seller_rank / total_marketplace_sellers, 2) AS pct_of_all_sellers,
    ROUND(100.0 * seller_rank / total_exposed_sellers, 2) AS pct_of_exposed_sellers,
    ROUND(cumulative_late_exposure, 2) AS cumulative_late_exposure,
    ROUND(100.0 * cumulative_late_exposure / total_platform_late_exposure, 2) AS cumulative_exposure_pct,
    CASE 
        WHEN 100.0 * cumulative_late_exposure / total_platform_late_exposure <= 50.0 THEN 'Top 50% Exposure Tier'
        WHEN 100.0 * cumulative_late_exposure / total_platform_late_exposure <= 80.0 THEN '50-80% Exposure Tier'
        ELSE 'Long Tail (>80%)'
    END AS pareto_exposure_tier
FROM ranked_sellers;

-- ----------------------------------------------------------------------------
-- 2. SELLER PARETO DECILE SUMMARY TABLE
-- Aggregates sellers into 10 deciles of cumulative population to prove concentration.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW view_seller_pareto_deciles AS
WITH deciled AS (
    SELECT 
        seller_id,
        total_orders,
        gmv,
        total_late_transaction_exposure,
        NTILE(10) OVER (ORDER BY total_late_transaction_exposure DESC) AS exposure_decile
    FROM view_seller_root_cause
)
SELECT 
    exposure_decile,
    COUNT(*) AS seller_count,
    ROUND(SUM(total_orders), 0) AS total_orders,
    ROUND(SUM(gmv), 2) AS total_gmv,
    ROUND(SUM(total_late_transaction_exposure), 2) AS decile_late_exposure,
    ROUND(100.0 * SUM(total_late_transaction_exposure) / 
          SUM(SUM(total_late_transaction_exposure)) OVER (), 2) AS decile_exposure_share_pct,
    ROUND(100.0 * SUM(SUM(total_late_transaction_exposure)) OVER (
        ORDER BY exposure_decile ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) / SUM(SUM(total_late_transaction_exposure)) OVER (), 2) AS cumulative_exposure_share_pct
FROM deciled
GROUP BY exposure_decile
ORDER BY exposure_decile;

-- ----------------------------------------------------------------------------
-- 3. PRODUCT CATEGORY PARETO CUMULATIVE VIEW
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW view_pareto_categories AS
WITH ranked_categories AS (
    SELECT 
        product_category,
        total_orders,
        gmv,
        freight_burden_pct,
        late_delivery_rate_pct,
        late_transaction_exposure,
        high_freight_gmv_exposure,
        ROW_NUMBER() OVER (ORDER BY late_transaction_exposure DESC) AS category_rank,
        COUNT(*) OVER () AS total_categories,
        SUM(late_transaction_exposure) OVER (
            ORDER BY late_transaction_exposure DESC 
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS cumulative_late_exposure,
        SUM(late_transaction_exposure) OVER () AS total_category_exposure
    FROM view_category_root_cause
    WHERE late_transaction_exposure > 0
)
SELECT 
    category_rank,
    product_category,
    total_orders,
    gmv,
    freight_burden_pct,
    late_delivery_rate_pct,
    late_transaction_exposure,
    ROUND(100.0 * category_rank / total_categories, 2) AS pct_of_categories,
    ROUND(cumulative_late_exposure, 2) AS cumulative_late_exposure,
    ROUND(100.0 * cumulative_late_exposure / total_category_exposure, 2) AS cumulative_exposure_pct
FROM ranked_categories;

-- ----------------------------------------------------------------------------
-- 4. GEOGRAPHIC CORRIDOR PARETO CUMULATIVE VIEW
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW view_pareto_corridors AS
WITH ranked_corridors AS (
    SELECT 
        corridor,
        seller_state,
        customer_state,
        is_interstate,
        total_orders,
        gmv,
        late_delivery_rate_pct,
        avg_delay_days_late_items,
        late_transaction_exposure,
        ROW_NUMBER() OVER (ORDER BY late_transaction_exposure DESC) AS corridor_rank,
        COUNT(*) OVER () AS total_corridors,
        SUM(late_transaction_exposure) OVER (
            ORDER BY late_transaction_exposure DESC 
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS cumulative_late_exposure,
        SUM(late_transaction_exposure) OVER () AS total_corridor_exposure
    FROM view_corridor_root_cause
    WHERE late_transaction_exposure > 0
)
SELECT 
    corridor_rank,
    corridor,
    seller_state,
    customer_state,
    is_interstate,
    total_orders,
    gmv,
    late_delivery_rate_pct,
    late_transaction_exposure,
    ROUND(100.0 * corridor_rank / total_corridors, 2) AS pct_of_corridors,
    ROUND(cumulative_late_exposure, 2) AS cumulative_late_exposure,
    ROUND(100.0 * cumulative_late_exposure / total_corridor_exposure, 2) AS cumulative_exposure_pct
FROM ranked_corridors;
