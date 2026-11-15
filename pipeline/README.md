# Lightweight Data Engineering Pipeline

**Project:** Marketplace Profitability & Fulfillment Leakage Diagnostic  
**Architecture:** Python + DuckDB + Declarative Configuration + Structured Logging  
**Role:** Ingestion, validation, orchestration, and automated reconciliation wrapper around the **frozen analytical core**.

---

## 1. Why a Lightweight Data Engineering Layer?

The analytical core of this project is frozen and fully validated. However, a credible production-ready Business Analytics engagement requires more than static SQL scripts:
- **Determinism & Idempotency:** The pipeline can be re-run indefinitely against raw data without producing duplicate staging records or corrupted metrics.
- **Fail-Fast Ingestion Gates:** Missing source datasets, missing columns, or corrupted timestamps are intercepted before expensive analytical queries run.
- **Declarative Configuration:** File paths, schema mappings, and validation rules are centralized in `config.yaml` rather than hard-coded into Python scripts.
- **Structured Audit Logging:** Every run emits both human-readable console summaries and machine-readable JSON log artifacts tracking stage-by-stage latencies, row counts, and analytical snapshots.
- **Zero Production Over-Engineering:** We intentionally avoid heavy orchestrators (Airflow, dbt, Spark, Kafka, Docker, Kubernetes) because this static ~100k-order dataset is an analytical decision study, not an unbounded streaming platform.

---

## 2. Pipeline Architecture & Data Flow

```
                         RAW DATASET (9 CSV Tables)
                                    │
                                    ▼
                 STAGE 1: SOURCE FILE VALIDATION GATE
                   ├── Expected CSV files exist in data/raw/
                   └── File byte sizes > 0
                                    │
                                    ▼
                STAGE 2: DETERMINISTIC STAGING INGESTION
                   ├── CREATE OR REPLACE staging tables in DuckDB
                   └── Record table row counts and load latencies
                                    │
                                    ▼
               STAGE 3: PIPELINE STAGING HEALTH VALIDATION
                   ├── Table existence & row counts > 0
                   ├── Required column presence check
                   ├── Primary key nullity audit
                   ├── Non-negative financial validation (price >= 0, freight >= 0)
                   └── Parameterized timestamp parseability checks
                                    │
                                    ▼
               STAGE 4: SQL ANALYTICAL SUITE EXECUTION
                   ├── 01_schema.sql (Staging DDL)
                   ├── 02_data_quality.sql (Analytical DQ audits)
                   ├── 03_order_item_fact.sql (Controlled fact tables)
                   ├── 04_kpi_layer.sql (Decoupled 6-layer KPI views)
                   ├── 05_root_cause_analysis.sql (Seller, Cat, Corridor)
                   ├── 06_pareto_analysis.sql (Window functions & Deciles)
                   └── 07_intervention_priority.sql (P1-P4 Tiers)
                                    │
                                    ▼
               STAGE 5: VERIFICATION GATE (SUBPROCESS EXECUTION)
                   ├── Subprocess: python tests/verify_pipeline.py
                   ├── Asserts zero PK duplicates & referential integrity
                   └── Asserts delivery rate bounds (0 <= rate <= 100%)
                                    │
                                    ▼
               RECONCILIATION SNAPSHOT & STRUCTURED AUDIT LOGGING
                   ├── Dynamic extraction of 8 core business invariants
                   ├── Formatted console execution card
                   └── JSON artifact: logs/run_<run_id>.json
```

---

## 3. Component Reference & Hardening

| Module | File Path | Responsibilities & Production Hardening |
|---|---|---|
| **Configuration** | [`pipeline/config.yaml`](file:///d:/Placements/Projects/Marketplace%20profitabilty%20&%20Fulfillment%20Leakage%20Analysis/pipeline/config.yaml) | Declarative mapping of source files, target staging tables, primary keys, required columns, validation rules, and script sequences. |
| **Ingestion** | [`pipeline/ingestion.py`](file:///d:/Placements/Projects/Marketplace%20profitabilty%20&%20Fulfillment%20Leakage%20Analysis/pipeline/ingestion.py) | Deterministic CSV ingestion into DuckDB. Rebuilds staging tables cleanly via `CREATE OR REPLACE TABLE`, ensuring complete idempotency. Anchored to `PROJECT_ROOT` for environment portability. |
| **Validation** | [`pipeline/validation.py`](file:///d:/Placements/Projects/Marketplace%20profitabilty%20&%20Fulfillment%20Leakage%20Analysis/pipeline/validation.py) | Dual-stage health gate (Pre-ingestion source check + Post-ingestion schema and non-negative financial check). Uses parameterized timestamp validation (`SELECT CAST(? AS TIMESTAMP)`). |
| **Logger** | [`pipeline/logger.py`](file:///d:/Placements/Projects/Marketplace%20profitabilty%20&%20Fulfillment%20Leakage%20Analysis/pipeline/logger.py) | Emits structured stage timestamps, durations, row counts, and JSON run logs in `logs/`. |
| **Orchestrator** | [`pipeline/run_pipeline.py`](file:///d:/Placements/Projects/Marketplace%20profitabilty%20&%20Fulfillment%20Leakage%20Analysis/pipeline/run_pipeline.py) | Master CLI entrypoint coordinating the entire end-to-end execution flow. Guaranteed database connection cleanup via `try ... finally: con.close()` to prevent Windows file-lock contention. |

---

## 4. Execution & CLI Usage

### Complete Pipeline Run
Run the master orchestrator from the project root:
```bash
python pipeline/run_pipeline.py
# Or on Windows:
py pipeline/run_pipeline.py
```

### Running the Unit Test Suite & Idempotency Audit
To validate the Data Engineering layer (missing file handling, schema validation, fail-fast behavior, and dual-run idempotency):
```bash
python -m unittest tests/test_pipeline.py
# Or with discovery:
python -m unittest discover -s tests -p "test_*.py"
```

---

## 5. Failure Handling & Fail-Fast Behavior

The orchestrator enforces strict fail-fast rules:
- **Missing Source File:** Halts immediately before database connection, logging the missing file path.
- **Missing Schema Column:** Halts post-ingestion before analytical queries execute, preventing SQL syntax errors downstream.
- **Negative Financial Value:** Halts if prices or freight charges violate non-negative boundary rules.
- **Analytical Verification Failure:** If `tests/verify_pipeline.py` fails any assertion (e.g. delivery rate out of bounds or duplicate PKs), the subprocess return code halts the orchestrator, records the error trace, and exits with code `1`.
- **Resource Leak Prevention:** Persistent DuckDB handles are strictly terminated in `finally` blocks, releasing file system locks even on unhandled runtime crashes.
