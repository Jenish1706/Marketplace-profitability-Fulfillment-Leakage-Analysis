"""
Audit Test Suite: Verifies P0 and P1 fixes against rigorous ground-truth criteria.
"""
import os
import sys
import unittest
import duckdb

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

class TestAuditFixes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.con = duckdb.connect()
        # Ingest staging
        with open(os.path.join(project_root, "sql", "01_schema.sql"), "r", encoding="utf-8") as f:
            cls.con.execute(f.read())
            
        tables = [
            ("olist_orders", os.path.join(project_root, "data", "raw", "olist_orders_dataset.csv")),
            ("olist_order_items", os.path.join(project_root, "data", "raw", "olist_order_items_dataset.csv")),
            ("olist_order_payments", os.path.join(project_root, "data", "raw", "olist_order_payments_dataset.csv")),
            ("olist_order_reviews", os.path.join(project_root, "data", "raw", "olist_order_reviews_dataset.csv")),
            ("olist_products", os.path.join(project_root, "data", "raw", "olist_products_dataset.csv")),
            ("olist_sellers", os.path.join(project_root, "data", "raw", "olist_sellers_dataset.csv")),
            ("olist_customers", os.path.join(project_root, "data", "raw", "olist_customers_dataset.csv")),
            ("olist_geolocation", os.path.join(project_root, "data", "raw", "olist_geolocation_dataset.csv")),
            ("product_category_name_translation", os.path.join(project_root, "data", "raw", "product_category_name_translation.csv"))
        ]
        for tbl, path in tables:
            cls.con.execute(f"INSERT INTO {tbl} SELECT * FROM read_csv_auto('{path.replace(chr(92), '/')}')")
            
        # Execute analytical SQL suite 02 through 07
        for sql_file in ["02_data_quality.sql", "03_order_item_fact.sql", "04_kpi_layer.sql", 
                         "05_root_cause_analysis.sql", "06_pareto_analysis.sql", "07_intervention_priority.sql"]:
            with open(os.path.join(project_root, "sql", sql_file), "r", encoding="utf-8") as f:
                cls.con.execute(f.read())

    @classmethod
    def tearDownClass(cls):
        cls.con.close()

    def test_p01_same_day_delivery_not_late(self):
        """P0-1 Fix Test: Same-day delivery on estimated date must be marked on-time (is_late = 0)."""
        # Synthetic row test
        q_synthetic = """
        SELECT 
            CASE 
                WHEN CAST('2018-05-10 15:30:00' AS DATE) > CAST('2018-05-10 00:00:00' AS DATE) THEN 1 
                ELSE 0 
            END AS is_late_fixed,
            CASE 
                WHEN TIMESTAMP '2018-05-10 15:30:00' > TIMESTAMP '2018-05-10 00:00:00' THEN 1 
                ELSE 0 
            END AS is_late_buggy
        """
        fixed, buggy = self.con.execute(q_synthetic).fetchone()
        self.assertEqual(fixed, 0, "Fixed logic must treat same-day delivery as on-time")
        self.assertEqual(buggy, 1, "Buggy logic falsely treated same-day delivery as late")

        # Database Fact layer verification:
        q_real_same_day = """
        SELECT is_late 
        FROM fact_orders
        WHERE order_delivered_customer_date IS NOT NULL
          AND CAST(order_delivered_customer_date AS DATE) = CAST(order_estimated_delivery_date AS DATE)
          AND order_delivered_customer_date > order_estimated_delivery_date
        LIMIT 1;
        """
        row = self.con.execute(q_real_same_day).fetchone()
        if row:
            self.assertEqual(row[0], 0, "Same-day delivery in fact_orders must have is_late = 0")

        # Check total late count in fact_orders
        q_total_late = "SELECT COUNT(*) FROM fact_orders WHERE order_status = 'delivered' AND is_late = 1"
        total_late = self.con.execute(q_total_late).fetchone()[0]
        self.assertEqual(total_late, 6534, f"Expected 6,534 date-level late orders, got {total_late}")

    def test_p02_seller_vs_carrier_attribution(self):
        """P0-2 Fix Test: Split late deliveries into seller dispatch breach vs carrier transit delay."""
        # Check that fact_order_items contains the explicit attribution columns
        cols = [col[0] for col in self.con.execute("DESCRIBE fact_order_items").fetchall()]
        self.assertIn("is_seller_caused_late", cols, "fact_order_items must contain is_seller_caused_late")
        self.assertIn("is_carrier_caused_late", cols, "fact_order_items must contain is_carrier_caused_late")

        # Verify that carrier transit delay is attributed to carrier, not seller
        q = """
        SELECT 
            SUM(is_late) as total_late,
            SUM(is_seller_caused_late) as seller_late,
            SUM(is_carrier_caused_late) as carrier_late
        FROM fact_order_items
        WHERE is_delivered = 1;
        """
        total_late, seller_late, carrier_late = self.con.execute(q).fetchone()
        self.assertEqual(seller_late + carrier_late, total_late, "Seller + carrier late items must equal total late items")
        self.assertGreater(carrier_late, seller_late, "Carrier transit delay accounts for majority (~71%) of late items")

    def test_p04_exposure_and_scenarios(self):
        """P0-4 Fix Test: Metric is named late-order exposure and scenarios, no 'recoverable' claims."""
        cols = [col[0] for col in self.con.execute("DESCRIBE view_intervention_tier_summary").fetchall()]
        for col in cols:
            self.assertNotIn("recoverable", col.lower(), f"Column {col} must not claim 'recoverable'")
        self.assertIn("scenario_mitigation_base_25pct", cols)

    def test_p16_pareto_concentration_lift(self):
        """P1-6 Fix Test: Pareto view provides commercial baseline and concentration lift."""
        row = self.con.execute("SELECT decile_gmv_share_pct, decile_exposure_share_pct, concentration_lift FROM view_seller_pareto_deciles WHERE exposure_decile = 1").fetchone()
        gmv_share, exp_share, lift = row
        self.assertAlmostEqual(gmv_share, 60.78, places=1)
        self.assertAlmostEqual(exp_share, 77.38, places=1)
        self.assertAlmostEqual(lift, 1.27, places=1)

    def test_p18_tier_naming_and_documentation(self):
        """P1-8 Fix Test: P4 tier is properly designated as Low Volume / Standard Governance."""
        tiers = [row[0] for row in self.con.execute("SELECT priority_tier FROM view_intervention_tier_summary").fetchall()]
        self.assertIn("P4 - Low Volume / Standard Governance", tiers)

    def test_open_lead1_unfulfilled_orders_breakdown(self):
        """Open Lead 1 Fix Test: Quantify unfulfilled/undelivered orders outside the delivered rate."""
        cnt = self.con.execute("SELECT SUM(order_count) FROM view_unfulfilled_orders_breakdown").fetchone()[0]
        self.assertEqual(cnt, 2963, f"Expected 2,963 unfulfilled orders, got {cnt}")

    def test_readme_tables_match_database(self):
        """Authoritative Check: Re-renders README tables from database and asserts zero diff."""
        import subprocess
        res = subprocess.run([sys.executable, os.path.join(project_root, "scripts", "render_readme_tables.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"README tables drifted from database artifacts: {res.stdout} {res.stderr}")

if __name__ == "__main__":
    unittest.main()
