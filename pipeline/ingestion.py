# pipeline/ingestion.py
# Deterministic & Idempotent Ingestion Layer for Marketplace Diagnostic Pipeline

import os
import time

class IngestionError(Exception):
    pass

def ingest_raw_sources(con, config, logger=None):
    """
    Idempotent, deterministic ingestion of raw CSVs into DuckDB staging tables.
    Uses CREATE OR REPLACE TABLE to guarantee clean rebuilds without record duplication.
    """
    raw_dir = config["data_source"]["raw_directory"]
    sources = config["sources"]
    ingestion_results = {}

    for src_key, src_meta in sources.items():
        tbl = src_meta["table"]
        filename = src_meta["file"]
        full_path = os.path.join(raw_dir, filename)

        if not os.path.exists(full_path):
            raise IngestionError(f"Cannot ingest missing file: {full_path}")

        t0 = time.time()
        
        # Load cleanly with CREATE OR REPLACE TABLE to guarantee idempotency
        # Normalizing path for DuckDB SQL cross-platform compatibility
        normalized_path = full_path.replace("\\", "/")
        query = f"CREATE OR REPLACE TABLE {tbl} AS SELECT * FROM read_csv_auto('{normalized_path}')"
        
        try:
            con.execute(query)
            row_count = con.execute(f"SELECT count(*) FROM {tbl}").fetchone()[0]
            duration = time.time() - t0
            
            ingestion_results[tbl] = {
                "filename": filename,
                "row_count": row_count,
                "duration_seconds": duration
            }

            if logger:
                logger.log_ingestion(tbl, filename, row_count, "PASS", duration)

        except Exception as e:
            if logger:
                logger.log_ingestion(tbl, filename, 0, "FAIL")
            raise IngestionError(f"Failed to ingest '{filename}' into table '{tbl}': {str(e)}")

    return ingestion_results
