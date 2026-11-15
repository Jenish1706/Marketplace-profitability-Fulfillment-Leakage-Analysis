import os
import sys
import duckdb

# Ensure project root is resolved dynamically regardless of execution working directory
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def run_pipeline():
    print("====================================================================")
    print("STARTING AUTOMATED PIPELINE VERIFICATION")
    print("====================================================================")
    con = duckdb.connect()
    
    try:
        print("\n[1/7] Ingesting raw CSV datasets into DuckDB staging tables...")
        with open(os.path.join(project_root, "sql", "01_schema.sql"), "r", encoding="utf-8") as f:
            schema_sql = f.read()
        con.execute(schema_sql)
        
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
            cnt = con.execute(f"SELECT count(*) FROM {tbl}").fetchone()[0]
            print(f"  -> Loaded {tbl}: {cnt:,} records")

        print("\n[2/7] Running Data Quality Audits (02_data_quality.sql)...")
        q_pk = "SELECT 'orders' as tbl, count(*) as dups FROM (SELECT order_id FROM olist_orders GROUP BY order_id HAVING count(*) > 1) UNION ALL SELECT 'items', count(*) FROM (SELECT order_id, order_item_id FROM olist_order_items GROUP BY order_id, order_item_id HAVING count(*) > 1) UNION ALL SELECT 'sellers', count(*) FROM (SELECT seller_id FROM olist_sellers GROUP BY seller_id HAVING count(*) > 1) UNION ALL SELECT 'customers', count(*) FROM (SELECT customer_id FROM olist_customers GROUP BY customer_id HAVING count(*) > 1)"
        for tbl, dups in con.execute(q_pk).fetchall():
            assert dups == 0, f"Duplicate PK in {tbl}"
            print(f"  -> PK uniqueness passed: {tbl} (0 duplicates)")

        orphans = con.execute("SELECT count(*) FROM olist_order_items oi LEFT JOIN olist_orders o ON oi.order_id = o.order_id WHERE o.order_id IS NULL").fetchone()[0]
        assert orphans == 0, "Found orphaned items!"
        print("  -> Referential integrity passed: 0 orphaned items without valid orders.")

        print("\n[3/7] Building Analytical Fact Layer (03_order_item_fact.sql)...")
        with open(os.path.join(project_root, "sql", "03_order_item_fact.sql"), "r", encoding="utf-8") as f:
            con.execute(f.read())
        item_count = con.execute("SELECT count(*) FROM fact_order_items").fetchone()[0]
        order_count = con.execute("SELECT count(*) FROM fact_orders").fetchone()[0]
        total_gmv = float(con.execute("SELECT sum(item_price) FROM fact_order_items").fetchone()[0])
        total_freight = float(con.execute("SELECT sum(freight_value) FROM fact_order_items").fetchone()[0])
        assert item_count == 112650, f"Expected 112,650 items, got {item_count}"
        assert order_count == 99441, f"Expected 99,441 orders, got {order_count}"
        print(f"  -> fact_order_items verified: {item_count:,} rows")
        print(f"  -> fact_orders verified: {order_count:,} rows")
        print(f"  -> Total GMV reconciled: R$ {total_gmv:,.2f}")
        print(f"  -> Total Freight reconciled: R$ {total_freight:,.2f}")
        print(f"  -> Overall Freight Burden: {100.0 * total_freight / total_gmv:.2f}%")

        print("\n[4/7] Deploying Six-Layer KPI Views (04_kpi_layer.sql)...")
        with open(os.path.join(project_root, "sql", "04_kpi_layer.sql"), "r", encoding="utf-8") as f:
            con.execute(f.read())
        exec_df = con.execute("SELECT * FROM view_executive_kpi_summary").df()
        print(exec_df.to_string(index=False))

        # Grain integrity assertions: Ensure delivered rate does NOT fan out above 100%
        delivered_rate = float(exec_df["delivered_rate_pct"].iloc[0])
        orders_total = int(exec_df["total_orders"].iloc[0])
        assert 0.0 <= delivered_rate <= 100.0, f"Invalid delivered_rate_pct: {delivered_rate}% (must be <= 100%)"
        assert orders_total == 99441, f"Expected 99,441 total orders in executive KPI summary, got {orders_total}"
        print(f"  -> Executive summary KPI validation passed: Delivered Rate = {delivered_rate}%, Orders = {orders_total:,}")

        print("\n[5/7] Deploying Multi-Dimensional Root Cause Views (05_root_cause_analysis.sql)...")
        with open(os.path.join(project_root, "sql", "05_root_cause_analysis.sql"), "r", encoding="utf-8") as f:
            con.execute(f.read())
        s_cnt = con.execute("SELECT count(*) FROM view_seller_root_cause").fetchone()[0]
        c_cnt = con.execute("SELECT count(*) FROM view_category_root_cause").fetchone()[0]
        l_cnt = con.execute("SELECT count(*) FROM view_corridor_root_cause").fetchone()[0]
        print(f"  -> Root cause views: {s_cnt:,} sellers, {c_cnt:,} categories, {l_cnt:,} corridors")

        print("\n[6/7] Calculating Pareto Concentration Curves (06_pareto_analysis.sql)...")
        with open(os.path.join(project_root, "sql", "06_pareto_analysis.sql"), "r", encoding="utf-8") as f:
            con.execute(f.read())
        pareto_df = con.execute("SELECT * FROM view_seller_pareto_deciles").df()
        print(pareto_df.to_string(index=False))

        print("\n[7/7] Computing Intervention Priority Matrix (07_intervention_priority.sql)...")
        with open(os.path.join(project_root, "sql", "07_intervention_priority.sql"), "r", encoding="utf-8") as f:
            con.execute(f.read())
        tier_df = con.execute("SELECT * FROM view_intervention_tier_summary").df()
        print(tier_df.to_string(index=False))
        sens_df = con.execute("SELECT * FROM view_threshold_sensitivity_check").df()
        print("\n  -> Volume Sensitivity Check (N>=20 vs N>=30 vs N>=50):")
        print(sens_df.to_string(index=False))
        
        print("\n====================================================================")
        print("ALL AUTOMATED QUALITY AND RECONCILIATION TESTS PASSED CLEANLY!")
        print("====================================================================")
        return True
    finally:
        con.close()

if __name__ == "__main__":
    if not run_pipeline():
        sys.exit(1)
