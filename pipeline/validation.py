# pipeline/validation.py
# Pipeline & Ingestion Health Validation Gate for Marketplace Diagnostic Pipeline

import os

class PipelineValidationError(Exception):
    pass

def validate_sources_exist(config, logger=None):
    """
    Pre-ingestion Gate: Verifies that all expected raw CSV files exist and are non-empty.
    """
    raw_dir = config["data_source"]["raw_directory"]
    sources = config["sources"]
    all_passed = True

    if not os.path.isdir(raw_dir):
        msg = f"Raw directory does not exist: {raw_dir}"
        if logger:
            logger.log_validation("raw_directory_exists", "FAIL", msg)
        raise PipelineValidationError(msg)

    for src_key, src_meta in sources.items():
        filename = src_meta["file"]
        full_path = os.path.join(raw_dir, filename)
        check_name = f"source_file_exists_{filename}"

        if not os.path.isfile(full_path):
            msg = f"Missing required source CSV file: {full_path}"
            if logger:
                logger.log_validation(check_name, "FAIL", msg)
            all_passed = False
            raise PipelineValidationError(msg)

        size_bytes = os.path.getsize(full_path)
        if size_bytes == 0:
            msg = f"Source CSV file is empty (0 bytes): {full_path}"
            if logger:
                logger.log_validation(check_name, "FAIL", msg)
            all_passed = False
            raise PipelineValidationError(msg)

        if logger:
            logger.log_validation(check_name, "PASS", f"{size_bytes:,} bytes")

    return all_passed

def validate_staging_health(con, config, logger=None):
    """
    Post-ingestion Gate: Verifies staging table health, schema adherence, and basic data integrity.
    Does NOT duplicate analytical SQL data-quality tests (which are handled by 02_data_quality.sql).
    """
    sources = config["sources"]
    validation_cfg = config.get("validation", {})
    all_passed = True

    # 1. Table existence and non-empty checks
    for src_key, src_meta in sources.items():
        tbl = src_meta["table"]
        check_tbl = f"staging_table_loaded_{tbl}"

        # Check table exists in DuckDB
        table_exists = con.execute(f"SELECT count(*) FROM information_schema.tables WHERE table_name = '{tbl}'").fetchone()[0] > 0
        if not table_exists:
            msg = f"Staging table '{tbl}' was not created in DuckDB"
            if logger:
                logger.log_validation(check_tbl, "FAIL", msg)
            raise PipelineValidationError(msg)

        # Check table has rows
        row_count = con.execute(f"SELECT count(*) FROM {tbl}").fetchone()[0]
        if row_count == 0:
            msg = f"Staging table '{tbl}' is unexpectedly empty (0 rows)"
            if logger:
                logger.log_validation(check_tbl, "FAIL", msg)
            raise PipelineValidationError(msg)

        if logger:
            logger.log_validation(check_tbl, "PASS", f"{row_count:,} records")

        # 2. Required columns check
        table_cols = [row[0] for row in con.execute(f"DESCRIBE {tbl}").fetchall()]
        for req_col in src_meta.get("required_columns", []):
            check_col = f"col_exists_{tbl}.{req_col}"
            if req_col not in table_cols:
                msg = f"Required column '{req_col}' is missing from staging table '{tbl}'"
                if logger:
                    logger.log_validation(check_col, "FAIL", msg)
                raise PipelineValidationError(msg)

        # 3. Primary key nullity check (must not be 100% null)
        for pk_col in src_meta.get("primary_key", []):
            if pk_col in table_cols:
                check_pk_null = f"pk_not_all_null_{tbl}.{pk_col}"
                non_null_cnt = con.execute(f"SELECT count({pk_col}) FROM {tbl} WHERE {pk_col} IS NOT NULL").fetchone()[0]
                if non_null_cnt == 0:
                    msg = f"Primary key column '{pk_col}' in '{tbl}' is completely null"
                    if logger:
                        logger.log_validation(check_pk_null, "FAIL", msg)
                    raise PipelineValidationError(msg)

    # 4. Financial non-negative check (from config)
    for target in validation_cfg.get("financial_non_negative", []):
        tbl, col = target.split(".")
        check_fin = f"non_negative_{tbl}.{col}"
        neg_count = con.execute(f"SELECT count(*) FROM {tbl} WHERE {col} < 0").fetchone()[0]
        if neg_count > 0:
            msg = f"Found {neg_count} negative values in financial column '{col}' of table '{tbl}'"
            if logger:
                logger.log_validation(check_fin, "FAIL", msg)
            raise PipelineValidationError(msg)
        if logger:
            logger.log_validation(check_fin, "PASS", "0 negative records")

    # 5. Date fields parseability check (from config)
    for target in validation_cfg.get("date_fields_parseable", []):
        tbl, col = target.split(".")
        check_date = f"date_parseable_{tbl}.{col}"
        try:
            sample_dates = con.execute(f"SELECT {col} FROM {tbl} WHERE {col} IS NOT NULL LIMIT 5").fetchall()
            for (dt_val,) in sample_dates:
                # DuckDB native cast check
                con.execute(f"SELECT CAST('{dt_val}' AS TIMESTAMP)").fetchone()
            if logger:
                logger.log_validation(check_date, "PASS", "Sample timestamps parsed successfully")
        except Exception as e:
            msg = f"Failed to parse timestamps in '{tbl}.{col}': {str(e)}"
            if logger:
                logger.log_validation(check_date, "FAIL", msg)
            raise PipelineValidationError(msg)

    return all_passed
