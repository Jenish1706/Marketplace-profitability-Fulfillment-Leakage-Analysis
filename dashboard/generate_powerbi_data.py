"""
Power BI Data Export Engine
Project: Marketplace Profitability & Fulfillment Leakage Diagnostic

Exports clean Star-Schema dimensional tables, aggregated fact models, and
analytical rollups into dashboard/powerbi_data/ for immediate Power BI consumption.
"""

import os
import sys
import duckdb

# Dynamically resolve project root directory
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def export_powerbi_tables():
    """
    Exports clean, pre-calculated dimension and fact tables to CSV files
    formatted specifically for a Power BI Star-Schema model.
    """
    print("Exporting clean Star-Schema data models for Power BI...")
    output_dir = os.path.join(project_root, "dashboard", "powerbi_data").replace("\\", "/")
    os.makedirs(output_dir, exist_ok=True)
    
    db_path = os.path.join(project_root, "marketplace.duckdb")
    
    # Use persistent database if already built by pipeline, otherwise initialize in-memory
    if os.path.isfile(db_path):
        print(f"  -> Connecting to persistent DuckDB database: {db_path}")
        con = duckdb.connect(db_path, read_only=True)
    else:
        print("  -> Persistent database not found; building analytical views in-memory...")
        con = duckdb.connect()
        with open(os.path.join(project_root, "sql", "01_schema.sql"), "r", encoding="utf-8") as f:
            con.execute(f.read())
        
        tables = [
            ("olist_orders", os.path.join(project_root, "data", "raw", "olist_orders_dataset.csv").replace("\\", "/")),
            ("olist_order_items", os.path.join(project_root, "data", "raw", "olist_order_items_dataset.csv").replace("\\", "/")),
            ("olist_order_payments", os.path.join(project_root, "data", "raw", "olist_order_payments_dataset.csv").replace("\\", "/")),
            ("olist_order_reviews", os.path.join(project_root, "data", "raw", "olist_order_reviews_dataset.csv").replace("\\", "/")),
            ("olist_products", os.path.join(project_root, "data", "raw", "olist_products_dataset.csv").replace("\\", "/")),
            ("olist_sellers", os.path.join(project_root, "data", "raw", "olist_sellers_dataset.csv").replace("\\", "/")),
            ("olist_customers", os.path.join(project_root, "data", "raw", "olist_customers_dataset.csv").replace("\\", "/")),
            ("olist_geolocation", os.path.join(project_root, "data", "raw", "olist_geolocation_dataset.csv").replace("\\", "/")),
            ("product_category_name_translation", os.path.join(project_root, "data", "raw", "product_category_name_translation.csv").replace("\\", "/"))
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
            with open(os.path.join(project_root, sql_file), "r", encoding="utf-8") as f:
                con.execute(f.read())

    try:
        # 1. Dimension Tables
        # 1. Dimension Tables
        print("  -> Exporting Dimension Tables...")
        con.execute(f"""
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
            ) TO '{output_dir}/dim_calendar.csv' (HEADER, DELIMITER ',')
        """)

        con.execute(f"""
            COPY (
                SELECT 
                    seller_id,
                    seller_state,
                    seller_city,
                    priority_tier,
                    recommended_operational_action
                FROM view_seller_intervention_matrix
            ) TO '{output_dir}/dim_seller.csv' (HEADER, DELIMITER ',')
        """)

        con.execute(f"""
            COPY (
                SELECT DISTINCT
                    product_category,
                    ROUND(AVG(product_weight_kg), 3) AS avg_weight_kg,
                    ROUND(AVG(product_volume_cm3), 2) AS avg_volume_cm3
                FROM fact_order_items
                GROUP BY product_category
            ) TO '{output_dir}/dim_product_category.csv' (HEADER, DELIMITER ',')
        """)

        # 2. Fact Tables & Summary Layers
        print("  -> Exporting Fact & Rollup Tables...")
        con.execute(f"""
            COPY (
                SELECT * FROM view_monthly_business_kpis
            ) TO '{output_dir}/monthly_business_kpis.csv' (HEADER, DELIMITER ',')
        """)

        con.execute(f"""
            COPY (
                SELECT * FROM view_seller_intervention_matrix
            ) TO '{output_dir}/seller_intervention_scorecard.csv' (HEADER, DELIMITER ',')
        """)

        con.execute(f"""
            COPY (
                SELECT * FROM view_category_root_cause
            ) TO '{output_dir}/category_root_cause.csv' (HEADER, DELIMITER ',')
        """)

        con.execute(f"""
            COPY (
                SELECT * FROM view_corridor_root_cause
            ) TO '{output_dir}/corridor_root_cause.csv' (HEADER, DELIMITER ',')
        """)

        con.execute(f"""
            COPY (
                SELECT * FROM view_pareto_sellers
            ) TO '{output_dir}/pareto_sellers.csv' (HEADER, DELIMITER ',')
        """)

        con.execute(f"""
            COPY (
                SELECT * FROM view_intervention_tier_summary
            ) TO '{output_dir}/intervention_tier_summary.csv' (HEADER, DELIMITER ',')
        """)

        # Export a streamlined fact_orders for fast Power BI responsiveness
        con.execute(f"""
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
            ) TO '{output_dir}/fact_orders_model.csv' (HEADER, DELIMITER ',')
        """)
        
        print(f"All Power BI modeling datasets successfully exported to {output_dir}")
    finally:
        con.close()

if __name__ == "__main__":
    export_powerbi_tables()
