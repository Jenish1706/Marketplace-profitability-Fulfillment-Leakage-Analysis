# tests/test_pipeline.py
# Unit Test Suite for Data Engineering Pipeline Layer

import os
import sys
import unittest
import yaml
import duckdb

# Ensure project root is in sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from pipeline.validation import validate_sources_exist, validate_staging_health, PipelineValidationError
from pipeline.ingestion import ingest_raw_sources, IngestionError
from pipeline.run_pipeline import load_config, run_pipeline

class TestDataEngineeringPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config_path = os.path.join(project_root, "pipeline", "config.yaml")
        cls.config = load_config(cls.config_path)

    def test_01_config_structure(self):
        """Verifies that config.yaml contains all required top-level blocks."""
        self.assertIn("data_source", self.config)
        self.assertIn("database", self.config)
        self.assertIn("sources", self.config)
        self.assertIn("validation", self.config)
        self.assertIn("orchestration", self.config)
        self.assertEqual(len(self.config["sources"]), 9)

    def test_02_source_files_exist(self):
        """Pre-ingestion Gate: Verifies all 9 CSV files exist in data/raw/."""
        passed = validate_sources_exist(self.config)
        self.assertTrue(passed)

    def test_03_missing_source_file_detection(self):
        """Pre-ingestion Gate: Asserts that a missing CSV raises PipelineValidationError."""
        bad_config = yaml.safe_load(yaml.dump(self.config))
        bad_config["sources"]["fake_table"] = {
            "file": "non_existent_file_xyz123.csv",
            "table": "fake_table"
        }
        with self.assertRaises(PipelineValidationError):
            validate_sources_exist(bad_config)

    def test_04_successful_ingestion(self):
        """Ingestion: Ingests all 9 tables into an in-memory DuckDB instance and checks row counts."""
        con = duckdb.connect(":memory:")
        ingestion_results = ingest_raw_sources(con, self.config)
        self.assertEqual(len(ingestion_results), 9)
        self.assertEqual(ingestion_results["olist_orders"]["row_count"], 99441)
        self.assertEqual(ingestion_results["olist_order_items"]["row_count"], 112650)
        self.assertEqual(ingestion_results["olist_sellers"]["row_count"], 3095)

    def test_05_idempotent_rebuild(self):
        """Idempotency: Confirms running ingestion twice produces identical row counts (zero duplication)."""
        con = duckdb.connect(":memory:")
        ingest_raw_sources(con, self.config)
        cnt1 = con.execute("SELECT count(*) FROM olist_orders").fetchone()[0]
        ingest_raw_sources(con, self.config)
        cnt2 = con.execute("SELECT count(*) FROM olist_orders").fetchone()[0]
        self.assertEqual(cnt1, cnt2)
        self.assertEqual(cnt2, 99441)

    def test_06_staging_health_validation(self):
        """Post-ingestion Gate: Validates schema, required columns, and non-negative constraints."""
        con = duckdb.connect(":memory:")
        ingest_raw_sources(con, self.config)
        passed = validate_staging_health(con, self.config)
        self.assertTrue(passed)

    def test_07_empty_table_detection(self):
        """Post-ingestion Gate: Asserts that an empty staging table triggers PipelineValidationError."""
        con = duckdb.connect(":memory:")
        ingest_raw_sources(con, self.config)
        con.execute("DELETE FROM olist_sellers")
        with self.assertRaises(PipelineValidationError):
            validate_staging_health(con, self.config)

    def test_08_missing_column_detection(self):
        """Post-ingestion Gate: Asserts that a missing required column triggers PipelineValidationError."""
        con = duckdb.connect(":memory:")
        ingest_raw_sources(con, self.config)
        bad_config = yaml.safe_load(yaml.dump(self.config))
        bad_config["sources"]["orders"]["required_columns"].append("fake_missing_column")
        with self.assertRaises(PipelineValidationError):
            validate_staging_health(con, bad_config)

    def test_09_full_pipeline_orchestration_and_idempotency(self):
        """Orchestrator: Executes Run 1 and Run 2, asserting identical analytical snapshots (zero drift)."""
        # Run 1
        success1, snap1 = run_pipeline(self.config_path, return_snapshot=True)
        self.assertTrue(success1)
        
        # Run 2
        success2, snap2 = run_pipeline(self.config_path, return_snapshot=True)
        self.assertTrue(success2)

        # Print comparison card
        print("\n" + "=" * 54)
        print(" IDEMPOTENT RUN RECONCILIATION SNAPSHOT")
        print("=" * 54)
        print(f"{'Metric':<22} | {'RUN 1':>14} | {'RUN 2':>14}")
        print("-" * 54)
        print(f"{'orders':<22} | {snap1['orders']:>14,} | {snap2['orders']:>14,}")
        print(f"{'items':<22} | {snap1['items']:>14,} | {snap2['items']:>14,}")
        print(f"{'GMV':<22} | {snap1['gmv']:>14,.2f} | {snap2['gmv']:>14,.2f}")
        print(f"{'freight':<22} | {snap1['freight']:>14,.2f} | {snap2['freight']:>14,.2f}")
        print(f"{'freight burden %':<22} | {snap1['freight_burden_pct']:>13.2f}% | {snap2['freight_burden_pct']:>13.2f}%")
        print(f"{'P1 sellers':<22} | {snap1['p1_seller_count']:>14} | {snap2['p1_seller_count']:>14}")
        print(f"{'P1 exposure':<22} | {snap1['p1_late_exposure']:>14,.2f} | {snap2['p1_late_exposure']:>14,.2f}")
        print(f"{'base recovery':<22} | {snap1['base_recovery_25pct']:>14,.2f} | {snap2['base_recovery_25pct']:>14,.2f}")
        print("-" * 54)
        print(" DETERMINISM CHECK: PASS")
        print("=" * 54 + "\n")

        # Strict equality assertion
        self.assertEqual(snap1, snap2)
        self.assertEqual(snap1["orders"], 99441)
        self.assertEqual(snap1["items"], 112650)
        self.assertEqual(snap1["p1_seller_count"], 83)
        self.assertAlmostEqual(snap1["gmv"], 13591643.70, places=2)
        self.assertAlmostEqual(snap1["freight"], 2251909.54, places=2)

if __name__ == "__main__":
    unittest.main(verbosity=2)
