# 00: Start Here — Project Overview & Quickstart

**Project:** Marketplace Profitability & Fulfillment Leakage Analysis  
**Author:** Jenish Patel  
**Target Audience:** Operations leadership, data engineers, economists, and interview evaluators  

---

## 1. What This Project Is

This repository is a production-grade analytical diagnostic and data engineering pipeline built over the [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce), covering 99,441 commercial orders across 2016–2018.

Rather than treating e-commerce datasets as generic Kaggle machine learning exercises or surface-level dashboards, this project performs a deep **unit-economics and operational fulfillment diagnostic**. It establishes an audited, reproducible analytical layer that investigates how fulfillment failures degrade customer retention, isolates root causes across marketplace participants, and formulates an economically defensible intervention framework.

---

## 2. The Core Questions It Answers, in the Order They Arise

Each step answers the question the previous one raised.

<!-- BEGIN_STORYLINE_GUIDE -->
1. **Can the data be trusted?** Orders, items, payments and reviews are joined at the right grain, and GMV and freight reconcile to the cent between layers, so no row is multiplied by a join. ([Data guide](03_DATA.md).) *This raises the next question: Is "late" measured correctly?*
2. **Is "late" measured correctly?** A date-level comparison replaces a timestamp comparison that counted same-day afternoon deliveries as late, which removes a boundary bug and lowers the late rate. ([Methodology guide](04_METHODOLOGY.md).) *This raises the next question: Who is responsible for the lateness?*
3. **Who is responsible for the lateness?** Late deliveries are split into those already late at seller dispatch and those delayed after handover, and the second group is tested for transit versus promise-setting. Most late deliveries arise after handover and reflect long transit rather than tight promises; the dataset has no carrier scans, so it cannot say which party causes the long leg. ([Results guide](09_RESULTS_AND_LIMITATIONS.md).) *This raises the next question: What does lateness do to customers?*
4. **What does lateness do to customers?** Review timing and a model of what the customer knew at review time show a step-function penalty for a parcel that has not arrived, not a linear daily decay; repurchase after a late first order is measured directly, and the difference is not statistically distinguishable from zero. ([Concepts guide](01_CONCEPTS.md).) *This raises the next question: How much money is at stake?*
5. **How much money is at stake?** Three levels keep what is observed apart from what is assumed: late-order value that was collected, the cost burden, and illustrative mitigation scenarios with assumed rates. There is no recovered cash, and the repurchase result bounds how much of the late value can be churn. ([Methodology guide](04_METHODOLOGY.md).) *This raises the next question: Where should operations intervene?*
6. **Where should operations intervene?** Deterministic percentile tiers on seller-caused exposure rank sellers for review, and Pareto concentration lift shows that late exposure is more concentrated than sales. ([Design decisions](08_DESIGN_DECISIONS.md).) *This raises the next question: Does the targeting hold next year?*
7. **Does the targeting hold next year?** The same tier rule applied to the first year alone and followed into the next shows partial persistence: part of the excess carries over and much of it does not, so the tier is a prioritisation list, not proof of a fixed seller trait. ([Results guide](09_RESULTS_AND_LIMITATIONS.md).) *This closes the chain.*
<!-- END_STORYLINE_GUIDE -->

---

## 3. Honest Headline Results

All metrics below are derived directly from committed analytical artifacts and SQL views executed against DuckDB.

| Metric / Dimension | Audited Finding | Artifact Source |
|---|---|---|
| **Commercial Scale** | 99,441 total orders, 96,478 delivered orders (97.02%), R$ 13,591,643.70 GMV, R$ 2,251,909.54 freight. | [`sql/04_kpi_layer.sql`](../../sql/04_kpi_layer.sql) |
| **Logistics Freight Burden** | 16.57% platform freight burden ($\text{Freight} / \text{GMV}$), rising above 18.2% during 2018 volume peaks. | [`sql/04_kpi_layer.sql`](../../sql/04_kpi_layer.sql) |
| **Late Delivery Rate** | **6.77%** of delivered orders (6,534 orders) breached promised delivery date under strict calendar date comparison. | [`sql/03_order_item_fact.sql`](../../sql/03_order_item_fact.sql) |
| **Fulfillment Attribution** | **72.25% of late (order, seller) pairs** were handed over by the shipping limit, so the delay arose after handover; only 27.75% involved late merchant dispatch. | [`sql/05_root_cause_analysis.sql`](../../sql/05_root_cause_analysis.sql) |
| **Observable Late-Order Value** | **R$ 1,150,892.13 total late-order value** (GMV: R$ 985,924.34 + Freight: R$ 164,967.79). Late at dispatch (seller-caused): R$ 371,281.14 (32.26%); post-handover delay: R$ 779,610.99 (67.74%). | [`sql/07_intervention_priority.sql`](../../sql/07_intervention_priority.sql) |
| **Pareto Concentration Lift** | Decile 1 (top 10% sellers) generates 60.78% of GMV but 77.38% of late exposure (**1.27× concentration lift**). | [`sql/06_pareto_analysis.sql`](../../sql/06_pareto_analysis.sql) |
| **P1 Priority Cohort** | **113 merchants** ($N \ge 30$) account for **R$ 181,377.55** in seller-caused late exposure (48.85% of platform total). | [`sql/07_intervention_priority.sql`](../../sql/07_intervention_priority.sql) |
| **Illustrative Mitigation** | Under an assumed 25% operational mitigation rate, P1 addressable late-order exposure is **R$ 45,344.39**. | [`sql/07_intervention_priority.sql`](../../sql/07_intervention_priority.sql) |
| **Out-of-Sample Persistence** | Partial persistence: sellers the headline tier rule flags using 2017 orders only still ran above other sellers on seller-caused lateness in 2018, but the gap shrank sharply. Rates and bootstrap intervals are in [guide 09](09_RESULTS_AND_LIMITATIONS.md). | [`sql/07_intervention_priority.sql`](../../sql/07_intervention_priority.sql) |
| **Review Survey Mechanism** | **70.10% of late-order reviews** were submitted *before* package arrival. Package non-receipt (`undelivered_at_review`) drives an **Odds Ratio of 33.63×** ($p < 10^{-15}$, cluster-robust SE on `seller_id`), proving a step-function promise breach rather than linear daily decay. | [`scripts/run_review_econometrics.py`](../../scripts/run_review_econometrics.py) |

### Key Deliverables & Artifacts
- **Executive Summary:** [`README.md`](../../README.md)
- **Executive Decision Memorandum:** [`report/decision_memo.md`](../../report/decision_memo.md) and [`report/decision_memo.pdf`](../../report/decision_memo.pdf)
- **Technical Writeup:** [`report/writeup.pdf`](../../report/writeup.pdf)
- **Power BI Star-Schema Export Data:** [`dashboard/powerbi_data/`](../../dashboard/powerbi_data/)
- **Data Engineering Configuration:** [`pipeline/config.yaml`](../../pipeline/config.yaml)

---

## 4. Reading Order for the Guide

This guide is structured sequentially to take an engineer, data scientist, or operations leader from foundational principles to full deployment:

1. **[`01_CONCEPTS.md`](01_CONCEPTS.md):** Foundational analytical concepts explained from scratch (analytical grain, window functions, Pareto lift, non-parametric tests, cluster-robust logistic regressions, and survey information sets).
2. **[`02_ARCHITECTURE.md`](02_ARCHITECTURE.md):** Complete architectural data flow diagram (Mermaid), module responsibilities, and the lifecycle of a record from raw CSV to business metric.
3. **[`03_DATA.md`](03_DATA.md):** Source schemas, license, row count reconciliations, data quality filters, and deliberate exclusions.
4. **[`04_METHODOLOGY.md`](04_METHODOLOGY.md):** Experimental protocol, baseline metrics, econometric formulations, statistical test selection, and explicit falsification criteria.
5. **[`05_CODE_WALKTHROUGH.md`](05_CODE_WALKTHROUGH.md):** Detailed code walkthrough of the pipeline stages, configuration, and econometric scripts.
6. **[`06_RUNBOOK.md`](06_RUNBOOK.md):** Step-by-step Windows runbook, execution times, artifact verification, and actual troubleshooting solutions.
7. **[`07_TESTING.md`](07_TESTING.md):** Test suite structure, unit and regression test coverage, fresh-clone tests, and how to add new tests.
8. **[`08_DESIGN_DECISIONS.md`](08_DESIGN_DECISIONS.md):** Ten Architecture Decision Records (ADRs) explaining key design trade-offs.
9. **[`09_RESULTS_AND_LIMITATIONS.md`](09_RESULTS_AND_LIMITATIONS.md):** In-depth findings, uncertainty bounds, null results, threats to validity, and future roadmap.
10. **[`GLOSSARY.md`](GLOSSARY.md):** Comprehensive dictionary of terms, acronyms, and metric definitions.

---

## 5. 10-Minute Quickstart

Follow these steps to reproduce the entire project from scratch on Windows:

### Step 1: Clone and Inspect Environment
Ensure Python 3.9 to 3.12 is installed (the pinned `numpy==1.26.4` has no Python 3.13 wheel):
```powershell
python --version
```

### Step 2: Install Version-Pinned Dependencies
Install the exact tested package versions:
```powershell
pip install -r requirements.txt
```

### Step 3: Execute Master Verification Orchestrator
Run the end-to-end master script, which executes all pipeline stages, referential integrity tests, documentation consistency checks, and unit tests:
```powershell
python scripts/run_all.py
```

### What `scripts/run_all.py` Executes:
1. **Pipeline Execution (`pipeline/run_pipeline.py`):** Ingests raw CSVs, builds staging tables, runs SQL transformations `01_schema.sql` through `07_intervention_priority.sql`, logs row counts and financial invariants.
2. **Pipeline Verification Gate (`tests/verify_pipeline.py`):** Runs 7 automated assertions on primary key uniqueness, foreign key integrity, non-negative amounts, and bounded rates.
3. **Documentation Drift Check (`scripts/render_readme_tables.py --check`):** Queries DuckDB views directly and confirms that the dynamic tables in `README.md` and `report/decision_memo.md` match database ground truth.
4. **Pytest Regression Suite (`pytest`):** Runs all 46 unit and regression tests in `tests/test_pipeline.py` and `tests/test_audit_fixes.py`.

Execution takes about 100 seconds (1.5 to 2 minutes) on the author's Windows machine and exits 0 when every stage passes.
