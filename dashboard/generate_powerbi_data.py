import duckdb
import os

def export_powerbi_tables():
    print("Exporting clean Star-Schema data models for Power BI...")
    os.makedirs("dashboard/powerbi_data", exist_ok=True)
    
    con = duckdb.connect()
    
    # Run full analytical setup
    with open("sql/01_schema.sql", "r", encoding="utf-8") as f:
        con.execute(f.read())
    
    tables = [
        ("olist_orders", "data/raw/olist_orders_dataset.csv"),
        ("olist_order_items", "data/raw/olist_order_items_dataset.csv"),
        ("olist_order_payments", "data/raw/olist_order_payments_dataset.csv"),
        ("olist_order_reviews", "data/raw/olist_order_reviews_dataset.csv"),
        ("olist_products", "data/raw/olist_products_dataset.csv"),
        ("olist_sellers", "data/raw/olist_sellers_dataset.csv"),
        ("olist_customers", "data/raw/olist_customers_dataset.csv"),
        ("olist_geolocation", "data/raw/olist_geolocation_dataset.csv"),
        ("product_category_name_translation", "data/raw/product_category_name_translation.csv")
    ]
    for tbl, path in tables:
        con.execute(f"INSERT INTO {tbl} SELECT * FROM read_csv_auto('{path}')")
    
    for sql_file in [
        "sql/03_order_item_fact.sql",
        "sql/04_kpi_layer.sql",
        "sql/05_root_cause_analysis.sql",
        "sql/06_pareto_analysis.sql",
        "sql/07_intervention_priority.sql"
    ]:
        with open(sql_file, "r", encoding="utf-8") as f:
            con.execute(f.read())
            
    # 1. Dimension Tables
    print("  -> Exporting Dimension Tables...")
    con.execute("""
        COPY (
            SELECT DISTINCT 
                order_purchase_date AS date,
                EXTRACT(YEAR FROM order_purchase_date) AS year,
                EXTRACT(MONTH FROM order_purchase_date) AS month,
                STRFTIME(order_purchase_date, '%Y-%m') AS year_month,
                STRFTIME(order_purchase_date, '%b %Y') AS month_name,
                EXTRACT(DOW FROM order_purchase_date) AS day_of_week
            FROM fact_orders
            WHERE order_purchase_date IS NOT NULL
            ORDER BY date
        ) TO 'dashboard/powerbi_data/dim_calendar.csv' (HEADER, DELIMITER ',')
    """)

    con.execute("""
        COPY (
            SELECT 
                seller_id,
                seller_state,
                seller_city,
                priority_tier,
                recommended_operational_action
            FROM view_seller_intervention_matrix
        ) TO 'dashboard/powerbi_data/dim_seller.csv' (HEADER, DELIMITER ',')
    """)

    con.execute("""
        COPY (
            SELECT DISTINCT
                product_category,
                ROUND(AVG(product_weight_kg), 3) AS avg_weight_kg,
                ROUND(AVG(product_volume_cm3), 2) AS avg_volume_cm3
            FROM fact_order_items
            GROUP BY product_category
        ) TO 'dashboard/powerbi_data/dim_product_category.csv' (HEADER, DELIMITER ',')
    """)

    # 2. Fact Tables & Summary Layers
    print("  -> Exporting Fact & Rollup Tables...")
    con.execute("""
        COPY (
            SELECT * FROM view_monthly_business_kpis
        ) TO 'dashboard/powerbi_data/monthly_business_kpis.csv' (HEADER, DELIMITER ',')
    """)

    con.execute("""
        COPY (
            SELECT * FROM view_seller_intervention_matrix
        ) TO 'dashboard/powerbi_data/seller_intervention_scorecard.csv' (HEADER, DELIMITER ',')
    """)

    con.execute("""
        COPY (
            SELECT * FROM view_category_root_cause
        ) TO 'dashboard/powerbi_data/category_root_cause.csv' (HEADER, DELIMITER ',')
    """)

    con.execute("""
        COPY (
            SELECT * FROM view_corridor_root_cause
        ) TO 'dashboard/powerbi_data/corridor_root_cause.csv' (HEADER, DELIMITER ',')
    """)

    con.execute("""
        COPY (
            SELECT * FROM view_pareto_sellers
        ) TO 'dashboard/powerbi_data/pareto_sellers.csv' (HEADER, DELIMITER ',')
    """)

    con.execute("""
        COPY (
            SELECT * FROM view_intervention_tier_summary
        ) TO 'dashboard/powerbi_data/intervention_tier_summary.csv' (HEADER, DELIMITER ',')
    """)

    # Export a streamlined fact_orders for fast Power BI responsiveness
    con.execute("""
        COPY (
            SELECT 
                order_id,
                customer_id,
                order_status,
                order_purchase_date,
                order_purchase_year_month,
                customer_state,
                total_items,
                distinct_sellers,
                is_multi_seller,
                gmv,
                total_freight,
                total_order_value,
                order_freight_burden,
                is_delivered,
                is_late,
                delivery_delay_days,
                avg_review_score,
                is_low_review
            FROM fact_orders
        ) TO 'dashboard/powerbi_data/fact_orders_model.csv' (HEADER, DELIMITER ',')
    """)
    
    print("All Power BI modeling datasets successfully exported to dashboard/powerbi_data/")

if __name__ == "__main__":
    export_powerbi_tables()
