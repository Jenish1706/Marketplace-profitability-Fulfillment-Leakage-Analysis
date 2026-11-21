-- ============================================================================
-- 07_INTERVENTION_PRIORITY.SQL: RULE-BASED PRIORITIZATION MATRIX
-- Project: Marketplace Profitability & Fulfillment Leakage Diagnostic
-- Dialect: DuckDB-first analytical SQL with PostgreSQL-portable queries
-- Purpose: Classifies sellers and categories into operational action tiers (P1-P4)
--          using defensible percentile thresholds and volume cutoffs.
--          Enforces P0-2 seller-caused lateness attribution and P0-4 scenario mitigation.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. SELLER PERIOD METRICS, THE SINGLE TIER RULE, AND THE HEADLINE MATRIX
-- view_seller_period_metrics builds the seller metrics the tier rule needs for
-- each period ('ALL' = whole dataset, '2017', '2018'), with the same definitions
-- as view_seller_root_cause (item-level rates; seller-caused exposure = item price
-- plus freight on seller-caused late items). view_seller_tiers_by_period applies
-- the P1-P4 rule once, with percentile benchmarks computed inside each period.
-- The headline matrix (period 'ALL') and the 2017 -> 2018 persistence check
-- (period '2017') both read their tiers from that one view: the rule is not copied.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW view_seller_period_metrics AS
WITH period_items AS (
    SELECT 'ALL' AS period, * FROM fact_order_items
    UNION ALL
    SELECT '2017' AS period, * FROM fact_order_items WHERE year(order_purchase_timestamp) = 2017
    UNION ALL
    SELECT '2018' AS period, * FROM fact_order_items WHERE year(order_purchase_timestamp) = 2018
)
SELECT
    period,
    seller_id,
    COUNT(DISTINCT order_id) AS total_orders,
    CASE WHEN COUNT(DISTINCT order_id) >= 30 THEN 1 ELSE 0 END AS meets_min_volume_30,
    SUM(CASE WHEN is_delivered = 1 THEN 1 ELSE 0 END) AS delivered_items,
    SUM(CASE WHEN is_late = 1 THEN 1 ELSE 0 END) AS late_items,
    SUM(CASE WHEN is_seller_caused_late = 1 THEN 1 ELSE 0 END) AS seller_late_items,
    ROUND(100.0 * SUM(CASE WHEN is_seller_caused_late = 1 THEN 1 ELSE 0 END) /
          NULLIF(SUM(CASE WHEN is_delivered = 1 THEN 1 ELSE 0 END), 0), 2) AS seller_late_item_rate_pct,
    ROUND(100.0 * SUM(freight_value) / NULLIF(SUM(item_price), 0), 2) AS freight_burden_pct,
    ROUND(SUM(CASE WHEN is_seller_caused_late = 1 THEN item_price + freight_value ELSE 0 END), 2) AS seller_late_exposure
FROM period_items
GROUP BY period, seller_id;

CREATE OR REPLACE VIEW view_seller_tiers_by_period AS
WITH qualified_seller_benchmarks AS (
    -- Percentile thresholds exclusively across operational sellers (N >= 30), per period
    SELECT
        period,
        PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY seller_late_exposure) AS exp_p75,
        PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY seller_late_exposure) AS exp_p50,
        PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY seller_late_item_rate_pct) AS late_p75,
        PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY seller_late_item_rate_pct) AS late_p50,
        PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY freight_burden_pct) AS freight_p75
    FROM view_seller_period_metrics
    WHERE total_orders >= 30
    GROUP BY period
)
SELECT
    s.*,

    -- Deterministic Percentile Tier Rules (P0-2: Evaluates seller-caused friction)
    CASE
        -- P1: High Volume + High Seller Exposure (>= 75th) + High Severity (>= 75th)
        WHEN s.meets_min_volume_30 = 1
         AND s.seller_late_exposure >= b.exp_p75
         AND (s.seller_late_item_rate_pct >= b.late_p75 OR s.freight_burden_pct >= b.freight_p75)
        THEN 'P1 - Immediate Intervention'

        -- P2: High Volume + Either High Seller Exposure OR High Severity
        WHEN s.meets_min_volume_30 = 1
         AND (s.seller_late_exposure >= b.exp_p75
              OR s.seller_late_item_rate_pct >= b.late_p75
              OR s.freight_burden_pct >= b.freight_p75)
        THEN 'P2 - Operational Investigation'

        -- P3: Moderate Volume / Moderate Friction, OR Low-Volume High-Late-Rate Sellers
        WHEN (s.meets_min_volume_30 = 1 AND (s.seller_late_exposure >= b.exp_p50 OR s.seller_late_item_rate_pct >= b.late_p50))
          OR (s.meets_min_volume_30 = 0 AND s.total_orders >= 10 AND s.seller_late_item_rate_pct >= 25.0)
        THEN 'P3 - Operational Monitoring'

        -- P4: Low Volume or Not Prioritised
        ELSE 'P4 - Low Volume / Not Prioritised'
    END AS priority_tier,

    CASE
        WHEN s.meets_min_volume_30 = 1
         AND s.seller_late_exposure >= b.exp_p75
         AND s.seller_late_item_rate_pct >= b.late_p75
        THEN 'Direct Seller SLA Review & Handover Lead-Time Calibration'
        WHEN s.meets_min_volume_30 = 1
         AND s.seller_late_exposure >= b.exp_p75
         AND s.freight_burden_pct >= b.freight_p75
        THEN 'Packaging & Volumetric Freight Audit; Regional Fulfillment Re-routing'
        WHEN s.meets_min_volume_30 = 1
         AND s.seller_late_exposure >= b.exp_p75
        THEN 'High-Exposure Merchant Operational Inspection'
        WHEN s.meets_min_volume_30 = 1
         AND s.seller_late_item_rate_pct >= b.late_p75
        THEN 'Carrier Handoff & Dispatch Speed Diagnostic'
        ELSE 'Automated Dashboard Monitoring'
    END AS recommended_operational_action
FROM view_seller_period_metrics s
JOIN qualified_seller_benchmarks b ON s.period = b.period;

CREATE OR REPLACE VIEW view_seller_intervention_matrix AS
SELECT
    s.seller_id,
    s.seller_state,
    s.seller_city,
    s.total_orders,
    s.total_items,
    s.gmv,
    s.seller_aov,
    s.late_items,
    s.late_item_rate_pct,
    s.seller_late_items,
    s.seller_late_item_rate_pct,
    s.carrier_late_items,
    s.carrier_late_item_rate_pct,
    s.avg_delay_days_late_items,
    s.freight_burden_pct,
    s.avg_review_score,
    s.low_review_rate_pct,
    s.total_late_transaction_exposure,
    s.seller_late_exposure,
    s.carrier_late_exposure,
    s.high_freight_gmv_exposure,
    s.meets_min_volume_30,
    t.priority_tier,
    t.recommended_operational_action
FROM view_seller_root_cause s
JOIN view_seller_tiers_by_period t ON t.period = 'ALL' AND t.seller_id = s.seller_id;

-- ----------------------------------------------------------------------------
-- 2. TIER SUMMARY & SCENARIO-BASED MITIGATION EXPOSURE
-- Evaluates Conservative (10%), Base (25%), and Optimistic (40%) mitigation cases.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW view_intervention_tier_summary AS
SELECT 
    priority_tier,
    COUNT(*) AS seller_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_of_seller_base,
    SUM(total_orders) AS total_orders,
    ROUND(SUM(gmv), 2) AS total_gmv,
    SUM(seller_late_items) AS total_seller_late_items,
    ROUND(SUM(seller_late_exposure), 2) AS total_seller_late_exposure,
    ROUND(100.0 * SUM(seller_late_exposure) / 
          NULLIF(SUM(SUM(seller_late_exposure)) OVER (), 0), 2) AS pct_of_platform_seller_exposure,
    SUM(late_items) AS total_late_items,
    ROUND(SUM(total_late_transaction_exposure), 2) AS total_late_transaction_exposure,
    
    -- Level 3: Scenario-Based Late GMV Exposure Mitigation (10%, 25%, 40% scenarios)
    ROUND(ROUND(SUM(seller_late_exposure), 2) * 0.10, 2) AS scenario_mitigation_conservative_10pct,
    ROUND(ROUND(SUM(seller_late_exposure), 2) * 0.25, 2) AS scenario_mitigation_base_25pct,
    ROUND(ROUND(SUM(seller_late_exposure), 2) * 0.40, 2) AS scenario_mitigation_optimistic_40pct
FROM view_seller_intervention_matrix
GROUP BY priority_tier
ORDER BY priority_tier;

-- ----------------------------------------------------------------------------
-- 3. VOLUME THRESHOLD SENSITIVITY AUDIT (N >= 20 vs N >= 30 vs N >= 50)
-- Validates robustness of the P1 seller cohort against cutoff choice under P0-2.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW view_threshold_sensitivity_check AS
WITH b_20 AS (
    SELECT PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY seller_late_exposure) AS exp_p75,
           PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY seller_late_item_rate_pct) AS late_p75,
           PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY freight_burden_pct) AS freight_p75
    FROM view_seller_root_cause WHERE total_orders >= 20
),
b_30 AS (
    SELECT PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY seller_late_exposure) AS exp_p75,
           PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY seller_late_item_rate_pct) AS late_p75,
           PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY freight_burden_pct) AS freight_p75
    FROM view_seller_root_cause WHERE total_orders >= 30
),
b_50 AS (
    SELECT PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY seller_late_exposure) AS exp_p75,
           PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY seller_late_item_rate_pct) AS late_p75,
           PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY freight_burden_pct) AS freight_p75
    FROM view_seller_root_cause WHERE total_orders >= 50
)
SELECT 
    'N >= 20 Threshold' AS scenario,
    COUNT(CASE WHEN s.total_orders >= 20 AND s.seller_late_exposure >= b_20.exp_p75 AND (s.seller_late_item_rate_pct >= b_20.late_p75 OR s.freight_burden_pct >= b_20.freight_p75) THEN 1 END) AS p1_sellers_count,
    ROUND(SUM(CASE WHEN s.total_orders >= 20 AND s.seller_late_exposure >= b_20.exp_p75 AND (s.seller_late_item_rate_pct >= b_20.late_p75 OR s.freight_burden_pct >= b_20.freight_p75) THEN s.seller_late_exposure ELSE 0 END), 2) AS p1_seller_exposure_total
FROM view_seller_root_cause s CROSS JOIN b_20
UNION ALL
SELECT 
    'N >= 30 Threshold (Base)',
    COUNT(CASE WHEN s.total_orders >= 30 AND s.seller_late_exposure >= b_30.exp_p75 AND (s.seller_late_item_rate_pct >= b_30.late_p75 OR s.freight_burden_pct >= b_30.freight_p75) THEN 1 END),
    ROUND(SUM(CASE WHEN s.total_orders >= 30 AND s.seller_late_exposure >= b_30.exp_p75 AND (s.seller_late_item_rate_pct >= b_30.late_p75 OR s.freight_burden_pct >= b_30.freight_p75) THEN s.seller_late_exposure ELSE 0 END), 2)
FROM view_seller_root_cause s CROSS JOIN b_30
UNION ALL
SELECT 
    'N >= 50 Threshold',
    COUNT(CASE WHEN s.total_orders >= 50 AND s.seller_late_exposure >= b_50.exp_p75 AND (s.seller_late_item_rate_pct >= b_50.late_p75 OR s.freight_burden_pct >= b_50.freight_p75) THEN 1 END),
    ROUND(SUM(CASE WHEN s.total_orders >= 50 AND s.seller_late_exposure >= b_50.exp_p75 AND (s.seller_late_item_rate_pct >= b_50.late_p75 OR s.freight_burden_pct >= b_50.freight_p75) THEN s.seller_late_exposure ELSE 0 END), 2)
FROM view_seller_root_cause s CROSS JOIN b_50;

-- ----------------------------------------------------------------------------
-- 4. TEMPORAL PERSISTENCE CHECK (2017 -> 2018 OUT-OF-SAMPLE HOLDOUT)
-- Cohort: sellers the SAME tier rule (view_seller_tiers_by_period, period '2017')
-- puts in P1 using 2017 orders only; 'Other' = every other seller active in both
-- years. A seller is active in a year if it has at least one delivered item that
-- year. Sellers that stopped selling after 2017 are not in the 2018 comparison.
-- Rates are item-level (late or seller-late items / delivered items), pooled over
-- sellers, so a seller counts in proportion to its volume. The primary outcome is
-- seller-caused lateness (the headline tier's outcome); all-cause is secondary.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW view_seller_persistence_detail AS
SELECT
    t17.seller_id,
    CASE WHEN t17.priority_tier = 'P1 - Immediate Intervention' THEN 'P1_2017' ELSE 'Other_2017' END AS tier_2017,
    t17.delivered_items AS delivered_items_2017,
    t17.seller_late_items AS seller_late_items_2017,
    t17.late_items AS late_items_2017,
    t18.total_orders AS orders_2018,
    t18.delivered_items AS delivered_items_2018,
    t18.seller_late_items AS seller_late_items_2018,
    t18.late_items AS late_items_2018
FROM view_seller_tiers_by_period t17
JOIN view_seller_period_metrics t18 ON t18.period = '2018' AND t18.seller_id = t17.seller_id
WHERE t17.period = '2017'
  AND t17.delivered_items > 0
  AND t18.delivered_items > 0;

CREATE OR REPLACE VIEW view_seller_persistence_check AS
SELECT
    tier_2017,
    COUNT(*) AS sellers_active_both_years,
    SUM(delivered_items_2017) AS delivered_items_2017,
    SUM(delivered_items_2018) AS delivered_items_2018,
    ROUND(100.0 * SUM(seller_late_items_2017) / SUM(delivered_items_2017), 2) AS seller_late_rate_2017,
    ROUND(100.0 * SUM(seller_late_items_2018) / SUM(delivered_items_2018), 2) AS seller_late_rate_2018,
    ROUND(100.0 * SUM(late_items_2017) / SUM(delivered_items_2017), 2) AS all_cause_late_rate_2017,
    ROUND(100.0 * SUM(late_items_2018) / SUM(delivered_items_2018), 2) AS all_cause_late_rate_2018
FROM view_seller_persistence_detail
GROUP BY tier_2017
ORDER BY tier_2017;
