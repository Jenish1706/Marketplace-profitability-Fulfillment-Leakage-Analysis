# pipeline/run_pipeline.py
"""
Master Orchestrator for Marketplace Profitability & Fulfillment Leakage Diagnostic Data Pipeline.

Execution Flow:
    1. Configuration Loading & Validation (pipeline/config.yaml)
    2. Structured Run Logging Initialization (logs/run_<timestamp>.json)
    3. Stage 1: Source File Validation Gate (Pre-Ingestion)
    4. Stage 2: Deterministic Staging Ingestion (Raw CSV -> DuckDB Staging)
    5. Stage 3: Pipeline Staging Health Validation Gate (Post-Ingestion)
    6. Stage 4: Sequential Execution of Analytical SQL Suite (01 to 07)
    7. Stage 5: Analytical Reconciliation Snapshot Extraction
    8. Stage 6: Isolated Verification Gate (Subprocess tests/verify_pipeline.py)
    9. Run Log Finalization & Resource Cleanup (try ... finally)
"""

import os
import sys
import time
import yaml
import subprocess

# Ensure project root is in sys.path regardless of execution context
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import duckdb
from pipeline.logger import PipelineLogger
from pipeline.validation import validate_sources_exist, validate_staging_health, PipelineValidationError
from pipeline.ingestion import ingest_raw_sources, IngestionError

def load_config(config_path="pipeline/config.yaml") -> dict:
    """
    Loads and parses the centralized declarative YAML configuration file.

    Parameters:
        config_path (str): Relative or absolute path to config.yaml.

    Returns:
        dict: Parsed configuration dictionary containing database, source,
              validation, and orchestration parameters.

    Raises:
        FileNotFoundError: If the specified configuration file does not exist.
    """
    if not os.path.isabs(config_path):
        config_path = os.path.join(project_root, config_path)
    if not os.path.isfile(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def run_pipeline(config_path="pipeline/config.yaml", logger=None, return_snapshot=False):
    """
    Executes the complete end-to-end data pipeline from raw source files to analytical reconciliation.

    Parameters:
        config_path (str): Path to declarative YAML configuration.
        logger (PipelineLogger, optional): Pre-instantiated structured logger.
        return_snapshot (bool): If True, returns (success: bool, snapshot: dict).

    Returns:
        bool or tuple: Success status flag, or (success, snapshot) if return_snapshot=True.
    """
    config = load_config(config_path)
    log_dir = os.path.join(project_root, config.get("orchestration", {}).get("logging_directory", "logs"))
    
    if logger is None:
        logger = PipelineLogger(log_dir=log_dir)
    
    logger.print_banner("MARKETPLACE PROFITABILITY & FULFILLMENT DIAGNOSTIC PIPELINE")
    
    # 1. Connect to DuckDB database
    db_name = config.get("database", {}).get("path", ":memory:")
    db_path = os.path.join(project_root, db_name) if db_name != ":memory:" else ":memory:"
    con = duckdb.connect(db_path)
    
    try:
        # -------------------------------------------------------------
        # STAGE 1: SOURCE VALIDATION GATE (Pre-ingestion)
        # -------------------------------------------------------------
        t0 = time.time()
        logger.log_stage_start("1. Source File Validation")
        validate_sources_exist(config, logger)
        logger.log_stage_end("1. Source File Validation", "PASS", time.time() - t0)

        # -------------------------------------------------------------
        # STAGE 2: DETERMINISTIC INGESTION (Raw CSV -> DuckDB)
        # -------------------------------------------------------------
        t0 = time.time()
        logger.log_stage_start("2. Deterministic Staging Ingestion")
        ingestion_results = ingest_raw_sources(con, config, logger)
        logger.log_stage_end("2. Deterministic Staging Ingestion", "PASS", time.time() - t0, details=ingestion_results)

        # -------------------------------------------------------------
        # STAGE 3: PIPELINE HEALTH VALIDATION GATE (Post-ingestion)
        # -------------------------------------------------------------
        t0 = time.time()
        logger.log_stage_start("3. Pipeline Staging Health Validation")
        validate_staging_health(con, config, logger)
        logger.log_stage_end("3. Pipeline Staging Health Validation", "PASS", time.time() - t0)

        # -------------------------------------------------------------
        # STAGE 4: EXECUTE FROZEN SQL ANALYTICAL SUITE
        # -------------------------------------------------------------
        sql_dir = os.path.join(project_root, config.get("orchestration", {}).get("sql_scripts_directory", "sql"))
        sql_scripts = config.get("orchestration", {}).get("sql_scripts", [])

        for sql_file in sql_scripts:
            t_sql = time.time()
            stage_name = f"4. SQL Analytical Layer: {sql_file}"
            logger.log_stage_start(stage_name)
            
            full_sql_path = os.path.join(sql_dir, sql_file)
            if not os.path.isfile(full_sql_path):
                raise FileNotFoundError(f"Missing required SQL script: {full_sql_path}")
            
            with open(full_sql_path, "r", encoding="utf-8") as f:
                sql_content = f.read()
            
            con.execute(sql_content)
            logger.log_stage_end(stage_name, "PASS", time.time() - t_sql)

        # -------------------------------------------------------------
        # STAGE 5: EXTRACT ANALYTICAL RECONCILIATION SNAPSHOT
        # -------------------------------------------------------------
        snapshot = {
            "orders": int(con.execute("SELECT count(*) FROM fact_orders").fetchone()[0]),
            "items": int(con.execute("SELECT count(*) FROM fact_order_items").fetchone()[0]),
            "gmv": float(con.execute("SELECT sum(item_price) FROM fact_order_items").fetchone()[0]),
            "freight": float(con.execute("SELECT sum(freight_value) FROM fact_order_items").fetchone()[0]),
            "freight_burden_pct": round(float(con.execute("SELECT 100.0 * sum(freight_value) / sum(item_price) FROM fact_order_items").fetchone()[0]), 2),
            "p1_seller_count": int(con.execute("SELECT seller_count FROM view_intervention_tier_summary WHERE priority_tier = 'P1 - Immediate Intervention'").fetchone()[0]),
            "p1_seller_late_exposure": float(con.execute("SELECT total_seller_late_exposure FROM view_intervention_tier_summary WHERE priority_tier = 'P1 - Immediate Intervention'").fetchone()[0]),
            "base_mitigation_25pct": float(con.execute("SELECT scenario_mitigation_base_25pct FROM view_intervention_tier_summary WHERE priority_tier = 'P1 - Immediate Intervention'").fetchone()[0])
        }
        logger.record_snapshot(snapshot)

        # -------------------------------------------------------------
        # STAGE 6: FROZEN VERIFICATION GATE (Subprocess Execution)
        # -------------------------------------------------------------
        t0 = time.time()
        rel_verif = config.get("orchestration", {}).get("verification_script", "tests/verify_pipeline.py")
        verif_script = os.path.join(project_root, rel_verif)
        logger.log_stage_start(f"5. Verification Gate (Subprocess: {rel_verif})")
        
        proc = subprocess.run(
            [sys.executable, verif_script],
            cwd=project_root,
            capture_output=True,
            text=True
        )
        
        if proc.returncode != 0:
            err_msg = f"Verification script failed with exit code {proc.returncode}:\n{proc.stderr}\n{proc.stdout}"
            logger.log_error("Verification Gate", err_msg)
            logger.finalize("FAILED")
            return (False, snapshot) if return_snapshot else False
            
        print("  -> Subprocess verification returned exit code 0 (PASS)")
        logger.log_stage_end("5. Verification Gate", "PASS", time.time() - t0)

        # -------------------------------------------------------------
        # FINAL PIPELINE STATUS: SUCCESS
        # -------------------------------------------------------------
        logger.finalize("SUCCESS")
        return (True, snapshot) if return_snapshot else True

    except Exception as e:
        logger.log_error("Pipeline Execution", str(e))
        logger.finalize("FAILED")
        if return_snapshot:
            return False, {}
        return False
    finally:
        # Guarantee that DuckDB database connection is always closed cleanly,
        # releasing file locks on Windows and flushing write-ahead logs (WAL).
        con.close()

if __name__ == "__main__":
    success = run_pipeline()
    if not success:
        sys.exit(1)
