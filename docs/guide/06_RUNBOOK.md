# 06: Operational Runbook & Troubleshooting Guide

**Project:** Marketplace Profitability & Fulfillment Leakage Analysis  
**Author:** Jenish Patel  
**Platform:** Windows 10/11 (PowerShell) / Linux / macOS  
**Target Audience:** Operations engineers, data analysts, and technical evaluators  

---

## 1. Environment Setup (Windows PowerShell)

Follow these exact commands to configure a pristine environment:

### Step 1: Open PowerShell and Verify Python
Python 3.9+ is required (Python 3.9.13 tested):
```powershell
python --version
```

### Step 2: Create and Activate Virtual Environment
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```
*(If PowerShell blocks script execution, run: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`)*

### Step 3: Install Version-Pinned Dependencies
```powershell
pip install -r requirements.txt
```

---

## 2. Pipeline Commands & Execution Order

All commands are executed from the repository root directory.

| Order | Command | Expected Runtime | Output / Deliverable |
|---|---|---|---|
| **1** | `python pipeline/run_pipeline.py` | 10–15 seconds | Ingests 9 CSVs, builds DuckDB staging and analytical views, generates `logs/run_<id>.json`. |
| **2** | `python tests/verify_pipeline.py` | 1–2 seconds | Validates 7 core pipeline invariants (PK uniqueness, financial sums, rate bounds). |
| **3** | `python scripts/render_readme_tables.py --check` | 2–3 seconds | Asserts that `README.md` and `report/decision_memo.md` match database views. |
| **4** | `python scripts/run_review_econometrics.py` | 5–8 seconds | Runs Kruskal-Wallis, Mann-Whitney, and cluster-robust logistic regressions; updates `report/econometrics_results.json`. |
| **5** | `python dashboard/generate_powerbi_data.py` | 3–5 seconds | Exports 9 clean star-schema CSV tables into `dashboard/powerbi_data/`. |
| **6** | `python report/generate_decision_memo_pdf.py` | 2–3 seconds | Compiles two-page executive memorandum to `report/decision_memo.pdf`. |
| **7** | `python scripts/generate_writeup_pdf.py` | 2–3 seconds | Compiles technical whitepaper to `report/writeup.pdf`. |
| **Master** | `python scripts/run_all.py` | 45–50 seconds | Executes pipeline, verification gate, table check, and full test suite sequentially. |

---

## 3. How to Regenerate Every Result Number in the Documentation

This repository enforces an automated ground-truth rule: **no result number in public documentation is typed by hand**.

If underlying data or SQL logic changes, run:
```powershell
python scripts/render_readme_tables.py
```
This script queries DuckDB views directly and replaces the content between `<!-- BEGIN_* -->` and `<!-- END_* -->` comment blocks in both `README.md` and `report/decision_memo.md`:
1. Intervention Priority Tier Summary (`view_intervention_tier_summary`)
2. Pareto Concentration Deciles & Lift (`view_pareto_seller_deciles`)
3. Out-of-Sample Holdout Persistence (`view_seller_persistence_check`)
4. Econometric Regression Table (`view_econometric_regression_results`)

To verify whether documentation matches database ground truth without modifying files:
```powershell
python scripts/render_readme_tables.py --check
```

---

## 4. How to Run the Automated Test Suite

### Run All Pytest Tests
```powershell
python -m pytest tests/
```
Runs all 41 unit and regression tests in `tests/test_pipeline.py` and `tests/test_audit_fixes.py`. *(Note: in PowerShell without an active virtual environment, prefer `python -m pytest` over bare `pytest`).*

### Run Specific Test Modules
```powershell
# Pipeline data engineering tests (idempotency, fail-fast, validation)
python -m pytest tests/test_pipeline.py

# Audit fixes & statistical regression tests
python -m pytest tests/test_audit_fixes.py
```

---

## 5. Troubleshooting & Solutions for Errors Actually Hit

### Error 1: DuckDB Database File Locked (`IOException: Cannot open database ... Permission denied`)
- **Cause:** DuckDB enforces single-process write locks on file databases. If a previous Python script or interactive notebook crashed without closing its connection, the `.duckdb` file remains locked by Windows.
- **Solution:** 
  1. Close any running Jupyter kernels or zombie Python processes:
     ```powershell
     Get-Process python | Stop-Process -Force
     ```
  2. All pipeline scripts in this repository wrap database access in `try ... finally: con.close()` to guarantee connection release.

### Error 2: Fresh Clone Missing `marketplace.duckdb`
- **Cause:** `marketplace.duckdb` is git-ignored and not tracked in version control. Running scripts that query the database in read-only mode throws an error on a brand new clone before the pipeline has run.
- **Solution:**
  - `scripts/render_readme_tables.py` and `scripts/run_review_econometrics.py` include an automated fallback in `get_db_connection()`: if `marketplace.duckdb` does not exist on disk, they instantiate an in-memory connection and load staging tables directly from `data/raw/*.csv`.
  - Alternatively, run `python pipeline/run_pipeline.py` once to create the file database.

### Error 3: Git Lock Permission Denied on Windows (`fatal: Unable to create '.git/index.lock'`)
- **Cause:** Background file scanners or Windows sandboxing can hold transient locks on `.git/index.lock` during automated commits.
- **Solution:**
  - Run git commands with sandbox bypass or elevated privileges.
  - If a stale lock file persists after a crash, remove it:
    ```powershell
    Remove-Item -Force .git/index.lock
    ```

### Error 4: Metric Substring Formatting Collisions in Logger
- **Cause:** Suffix matching on `"pct"` in logging formatters can collide with economic metrics such as `base_mitigation_25pct`, formatting currency amounts (R\$ 45,344.39) as percentages (`45344.39%`).
- **Solution:**
  - In `pipeline/logger.py`, metric keys containing `"mitigation"`, `"exposure"`, or `"gmv"` are explicitly prioritized to format as currency (`R$ {v:,.2f}`) before percentage matching.

### Error 5: Windows PowerShell Multi-Line Quoting in `-c` Strings
- **Cause:** PowerShell parses double quotes and backslashes inside `python -c "..."` differently from bash, leading to `SyntaxError: EOL while scanning string literal`.
- **Solution:**
  - Prefer executing small dedicated Python scripts or use single-quoted multi-line raw strings in PowerShell.
