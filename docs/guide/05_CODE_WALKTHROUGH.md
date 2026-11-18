# 05: Codebase & Module Walkthrough

**Project:** Marketplace Profitability & Fulfillment Leakage Analysis  
**Author:** Jenish Patel  
**Purpose:** Comprehensive guide to every script, module, configuration file, SQL script, and verification test in the repository.

---

## 1. Overview of Codebase Organization

The repository is structured into distinct, decoupled subsystems:
```
├── pipeline/                 # Data engineering: ingestion, validation, logging, orchestration
│   ├── config.yaml           # Declarative pipeline configuration
│   ├── ingestion.py          # Deterministic DuckDB staging ingestion
│   ├── validation.py         # Dual-stage data health and referential gates
│   ├── logger.py             # Structured timing, metric snapshots, JSON run logs
│   └── run_pipeline.py       # Master pipeline CLI runner
├── sql/                      # Frozen analytical core: staging DDL to P1-P4 priority tiers
│   ├── 01_schema.sql         # Staging table schemas
│   ├── 02_data_quality.sql   # Data quality checks
│   ├── 03_order_item_fact.sql# Controlled fact tables (fact_order_items, fact_orders)
│   ├── 04_kpi_layer.sql      # Decoupled 6-layer KPI views
│   ├── 05_root_cause_analysis.sql # Seller vs carrier attribution & corridor analysis
│   ├── 06_pareto_analysis.sql# Windowed cumulative exposure & Pareto lift
│   └── 07_intervention_priority.sql # Percentile-ranked P1-P4 tiers & persistence check
├── scripts/                  # Downstream analytics, rendering, and master orchestrator
│   ├── run_all.py            # Master end-to-end verification orchestrator
│   ├── render_readme_tables.py # Dynamic DB-to-Markdown table injector with --check mode
│   ├── run_review_econometrics.py # Non-parametric tests & cluster-robust logit models
│   └── generate_writeup_pdf.py # Compiles executive technical PDF report
├── tests/                    # Automated testing suite
│   ├── verify_pipeline.py    # Pipeline post-run invariant assertions (7 checks)
│   ├── test_pipeline.py      # Unit tests for data engineering idempotency and fail-fast
│   └── test_audit_fixes.py   # Regression tests for audit fixes (P0, P1, MP-01 to MP-05)
└── dashboard/                # Power BI reporting layer
    ├── generate_powerbi_data.py # Star-schema CSV exporter
    └── powerbi_data/         # Exported dimensional modeling CSV tables
```

---

## 2. Stage-by-Stage Module Walkthrough

### Stage 1: Pipeline Configuration (`pipeline/config.yaml`)
- **Responsibility:** Centralizes all project parameters, file locations, staging table names, primary key definitions, required columns, and SQL execution sequence.
- **Key Structure:**
  - `database.path`: Relative path to `marketplace.duckdb`.
  - `source_files`: Mapping of 9 raw CSV names to DuckDB staging table names and expected schema definitions.
  - `validation_rules`: Declarative constraints: primary keys must be non-null and unique, price and freight amounts must be $\ge 0$, and timestamp columns must be parseable.
  - `sql_scripts`: Ordered list of SQL transformation files executed in Stage 4.

---

### Stage 2: Staging Ingestion Engine (`pipeline/ingestion.py`)
- **Key Function:** `run_ingestion(db_path: str, config: dict, logger: PipelineLogger) -> dict`
- **Execution Mechanism:**
  - Connects to DuckDB at `db_path`.
  - Iterates through `config["source_files"]`.
  - For each raw CSV file, executes:
    ```sql
    CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM read_csv_auto('{csv_path}')
    ```
  - Records execution time and row counts for every table into the logger.
- **Non-Obvious Lines:**
  - Uses `CREATE OR REPLACE TABLE` rather than `INSERT INTO` or `CREATE TABLE IF NOT EXISTS`. This guarantees **idempotency**: running the ingestion multiple times leaves the database in an identical clean state without duplicate records or stale rows.
  - Resolves file paths relative to `PROJECT_ROOT` to prevent working-directory dependency bugs on different operating systems.

---

### Stage 3: Data Quality & Schema Validation (`pipeline/validation.py`)
- **Key Functions:**
  - `validate_source_files(raw_dir: str, config: dict, logger: PipelineLogger) -> bool`: Pre-ingestion check ensuring all 9 CSV files exist on disk and have file size $> 0$ bytes.
  - `validate_staging_data(con: duckdb.DuckDBPyConnection, config: dict, logger: PipelineLogger) -> bool`: Post-ingestion health gate.
- **Non-Obvious Lines:**
  - Parameterized timestamp check: Rather than converting timestamps in Python, validates parseability directly in DuckDB using `TRY_CAST(col AS TIMESTAMP)`. If any row fails to parse, raises a descriptive `ValueError`.
  - Non-negative financial assertion: Executes `SELECT COUNT(*) FROM {table} WHERE price < 0 OR freight_value < 0` to immediately abort the pipeline if corrupted commercial transactions are detected.

---

### Stage 4: Fact Modeling & Analytical SQL Layer (`sql/`)
1. **`sql/01_schema.sql`:** Declares explicit schema types and creates baseline staging tables.
2. **`sql/02_data_quality.sql`:** Performs exploratory data quality audits (orphan order items, null delivery timestamps).
3. **`sql/03_order_item_fact.sql`:**
   - Pre-aggregates payments via CTE `int_order_payments_rollup` (`SUM(payment_value)`, `MAX(payment_installments)`).
   - Pre-aggregates reviews via CTE `int_order_reviews_dedup` (`ROUND(AVG(review_score), 2)`).
   - Joins onto `olist_order_items` to build `fact_order_items` (112,650 rows).
   - Implements date-level lateness comparison:
     ```sql
     CAST(order_delivered_customer_date AS DATE) > CAST(order_estimated_delivery_date AS DATE)
     ```
   - Implements handover attribution: `is_seller_late_dispatch`, `is_seller_caused_late`, and `is_carrier_caused_late`.
   - Aggregates to order grain in `fact_orders` (99,441 rows).
4. **`sql/04_kpi_layer.sql`:** Constructs decoupled 6-layer KPI views (`view_macro_kpi_monthly`, `view_unfulfilled_orders_breakdown`).
5. **`sql/05_root_cause_analysis.sql`:** Produces seller vs carrier delay attribution breakdowns and 417 origin-destination shipping corridor matrices.
6. **`sql/06_pareto_analysis.sql`:** Computes decile-level cumulative distributions and the 1.27× concentration lift over GMV baseline using window functions.
7. **`sql/07_intervention_priority.sql`:** Classifies sellers with $N \ge 30$ orders into P1–P4 tiers via `PERCENT_RANK()` and deploys `view_seller_persistence_check` for the 2017 $\to$ 2018 holdout validation.

---

### Stage 5: Verification & Integrity Assertions (`tests/verify_pipeline.py`)
- **Key Function:** `main() -> int`
- **7 Automated Invariant Assertions:**
  1. `fact_orders` primary key uniqueness (`COUNT(*) == COUNT(DISTINCT order_id)`).
  2. `fact_order_items` composite key uniqueness (`COUNT(*) == COUNT(DISTINCT order_id || '-' || order_item_id)`).
  3. Total GMV non-negativity and exact parity with raw items sum (`R$ 13,591,643.70`).
  4. Total Freight non-negativity and exact parity with raw items sum (`R$ 2,251,909.54`).
  5. Delivered order rate bounded between 0% and 100% (asserts exact 97.02%).
  6. Cancellation rate bounded between 0% and 100% (asserts exact 0.63%).
  7. Late delivery rate non-negativity and bounded within realistic bounds (asserts exact 6.77%).

---

### Downstream Analytics & Tooling (`scripts/`)

#### 1. Dynamic Table Renderer (`scripts/render_readme_tables.py`)
- **Key Functions:**
  - `get_db_connection(db_path: str) -> duckdb.DuckDBPyConnection`: Attempts to open `marketplace.duckdb` in read-only mode. If the file does not exist (e.g. on a fresh git clone), automatically constructs in-memory tables directly from raw CSVs so checks pass instantly.
  - `fetch_table_data(con)`: Executes analytical queries against DuckDB views (`view_intervention_tier_summary`, `view_pareto_seller_deciles`, `view_seller_persistence_check`, `view_econometric_regression_results`).
  - `render_markdown_table(headers, rows)`: Formats data into clean GitHub-flavored markdown.
  - `--check` flag: Compares current markdown tables in `README.md` and `report/decision_memo.md` against live database query results. Exits with code 1 if drift is detected.

#### 2. Review Econometrics Engine (`scripts/run_review_econometrics.py`)
- **Key Functions:**
  - `run_econometric_analysis()`:
    - Extracts orders with customer review timestamps and delivery timestamps.
    - Fits Kruskal-Wallis $H$-test across delivery delay cohorts.
    - Fits Mann-Whitney $U$-test and calculates rank-biserial correlation $r$.
    - Fits Model A (delivery delay) and Model B (information set at survey time) using `statsmodels.api.Logit`.
    - Implements Liang-Zeger cluster-robust covariance matrix with `cov_type='cluster'`, `cov_kwds={'groups': df['seller_id']}`.
    - Runs sensitivity checks comparing `seller_id` SEs against `seller_state` and `HC1`.
    - Updates `report/econometrics_results.json`.

#### 3. Master Verification Orchestrator (`scripts/run_all.py`)
- **Key Function:** `main() -> int`
- **Execution Order:**
  1. Executes `python pipeline/run_pipeline.py`.
  2. Executes `python tests/verify_pipeline.py`.
  3. Executes `python scripts/render_readme_tables.py --check`.
  4. Executes `pytest` across all tests in `tests/`.
- Guaranteed single-command exit code 0 on complete pass.
