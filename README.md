# Marketplace Profitability & Fulfillment Leakage Diagnostic
### Operational Unit Economics · Root-Cause Decomposition · Pareto Allocation · Decision Modeling

[![SQL](https://img.shields.io/badge/SQL-DuckDB%20%7C%20PostgreSQL-blue.svg)](sql/)
[![Python](https://img.shields.io/badge/Python-3.9%20%7C%20Pandas%20%7C%20Statsmodels-green.svg)](notebooks/)
[![Data Models](https://img.shields.io/badge/Data%20Models-Star%20Schema%20Exports-yellow.svg)](dashboard/)
[![PDF Report](https://img.shields.io/badge/Executive%20Report-2--Page%20Decision%20Memo-red.svg)](report/decision_memo.pdf)
[![Tests](https://img.shields.io/badge/Verification-Automated%20Pipeline%20Passed-brightgreen.svg)](tests/verify_pipeline.py)

---

## 1. Executive Business Problem

> *"GMV and order volume are growing, but marketplace economics are under pressure. Which sellers, product categories, and delivery regions are responsible for the largest operational and contribution-margin leakage, and which interventions should be prioritized based on recoverable economic impact?"*

This project is a rigorous, business-oriented diagnostic engagement designed for an executive operations leadership team (COO, VP of Marketplace Operations, Head of Logistics). It addresses the core marketplace paradox: **rapid commercial expansion accompanied by operational fulfillment breakdown and unit-economic compression**.

It is deliberately **NOT**:
- A generic sales dashboard or retrospective revenue tracker
- An ML predictive model or delivery delay classifier
- An artificial end-to-end software demo

Instead, it demonstrates **business judgment, relational data modeling, controlled analytical grains, non-parametric econometrics, Pareto concentration analysis, and quantified operational decision-making**.

---

## Engineering & Impact Highlights

```text
( Quantified operational fulfillment friction and unit economics using DuckDB analytical SQL, non-parametric statistics, and star-schema dimensional modeling )
```

• **Quantified late-order economic exposure** across 99.4K orders, decomposing fulfillment bottlenecks between seller dispatch handling and carrier transit  
• **Decoupled order and item analytical grains** using dedicated DuckDB CTEs, isolating 99.4K orders from 112.7K order items to prevent fan-out distortion  
• **Analyzed customer sentiment degradation** across delivery cohorts with non-parametric Kruskal-Wallis tests and logistic regression, isolating pre- vs post-delivery review timing  

---

## 2. Methodological Guardrails: Three-Level Economic Framework

A critical flaw in standard marketplace portfolio projects is fabricating unobserved platform overheads (seller commission rates, payment gateway fees, carrier contract settlements, reverse logistics costs) and claiming to calculate "actual company profit."

This diagnostic enforces a defensible **Three-Level Economic Architecture**:

<!-- BEGIN_ECONOMIC_FRAMEWORK -->
```
LEVEL 1 — Transaction Exposure (Observable)
  ├── Late-Order GMV Exposure:       E_late^GMV = R$ 985,924.34
  ├── Late-Order Freight Exposure:   E_late^freight = R$ 164,967.79
  └── Total Late Transaction Value:  E_late = R$ 1,150,892.13 (Date-level late delivery exposure)

LEVEL 2 — Cost Burden (Observable)
  ├── Platform Freight Burden:       Total Freight / Total GMV = 16.57%
  └── High-Freight Exposure:         R$ 1,855,750.93 GMV where Freight-to-Value >= 30%

LEVEL 3 — Operational Risk Mitigation Scenarios (Scenario-Based)
  Focuses on Priority 1 (P1) Sellers (R$ 181,377.55 Seller-Caused Late Exposure across 113 merchants):
  ├── Conservative Scenario (10% Operational Mitigation): R$ 18,137.76
  ├── Base Scenario (25% Operational Mitigation):         R$ 45,344.39
  └── Optimistic Scenario (40% Operational Mitigation):   R$ 72,551.02
```
<!-- END_ECONOMIC_FRAMEWORK -->

---

## 3. End-to-End Analytical Architecture

```
                    OLIST RAW DATASET (9 CSV Tables)
                                   │
                                   ▼
               DUCKDB-FIRST ANALYTICAL EXECUTION ENGINE
                 (Broadly portable SQL with Postgres DDL)
                                   │
      ┌────────────────────────────┴────────────────────────────┐
      ▼                                                         ▼
01_schema.sql (Staging DDL)                               02_data_quality.sql (PK, Nulls, Orphans)
      │                                                         │
      └────────────────────────────┬────────────────────────────┘
                                   │
                                   ▼
          03_order_item_fact.sql (Controlled Analytical Grains)
             ├── fact_order_items (Line-item grain: 112,650 rows)
             └── fact_orders (Order grain: 99,441 rows)
                                   │
                                   ▼
          04_kpi_layer.sql (Six-Layer Modular KPI Architecture)
             ├── 1. Commercial Performance      4. Customer Experience
             ├── 2. Fulfillment Performance     5. Economic Exposure
             └── 3. Logistics Economics         6. Monthly Trends
                                   │
      ┌────────────────────────────┼────────────────────────────┐
      ▼                            ▼                            ▼
05_root_cause_analysis.sql   06_pareto_analysis.sql   07_intervention_priority.sql
(Seller, Cat, Corridor)      (Decile Concentration)   (Rule-based P1 to P4 Tiers)
      │                            │                            │
      └────────────────────────────┼────────────────────────────┘
                                   │
                                   ▼
          PYTHON STATISTICAL & ECONOMETRIC DIAGNOSTIC NOTEBOOK
             ├── Kruskal-Wallis & Mann-Whitney U Non-Parametric Tests
             ├── Multivariate Logistic Regression: P(Low Review <= 2)
             ├── Signature Visual: Volume x Severity Scatter Matrix
             └── Sensitivity Audits (N >= 20, 30, 50 cutoffs)
                                   │
                ┌──────────────────┴──────────────────┐
                ▼                                     ▼
     POWER BI STAR SCHEMA MODEL           2-PAGE EXECUTIVE DECISION MEMO
     (Single-page Operations Canvas)      (Publication-Grade ReportLab PDF)
```

---

## 4. Key Diagnostic Discoveries

### 1. Macro Inflection: Growth vs Fulfillment Breakdown
- **Holiday Throughput Shock (Nov 2017):** Orders surged +63% MoM (7,544 orders), overwhelming carrier dispatch and driving late delivery rates to **14.31%**.
- **Severe Q1 2018 Fulfillment Collapse:** Rather than recovering post-holiday, late delivery rates spiked to **15.99% in Feb** and peaked at **21.36% in March 2018** (over 1 in 5 orders delivered late), with average delays of **+8.87 days** for late shipments.
- **Freight Inflation:** Platform freight burden rose steadily from 14.03% in Jan 2017 to over **18.23% by mid-2018**.

### 2. Pareto Concentration & Commercial Baseline
Cumulative exposure window functions reveal concentration, though strongly coupled to commercial scale:
- **Decile 1 (Top 310 sellers, 10% of seller base):** Generates **61.27% of total GMV (R$ 8.33M)** and accounts for **75.83% (R$ 1,024,909.34)** of late transaction exposure (concentration lift of **1.24×**).
- **Top 20% of sellers:** Account for **90.47%** of cumulative late exposure.
- **Bottom 50% of sellers:** Zero late items delivered.

### 3. Volume × Severity Decoupling
Standard failure-rate rankings flag low-volume noise (e.g., sellers with 2 orders and 100% late rate, representing R$ 72 exposure). Real business liability is concentrated in high-volume partners. For example, seller `4a3ca93a...` had a 16.0% late rate across 1,806 orders, generating **R$ 29,420.57 in late exposure** alone.

### 4. Product Category Structural Deficits
Heavy and voluminous categories (`furniture_decor`, `office_furniture`, `bed_bath_table`) carry physical volumes exceeding 25,000 cm³ and unit weights >3 kg, driving structural freight burdens of **25% to 35%**, severely eroding contribution margins.

### 5. Cross-Regional Corridor Friction
Intra-state São Paulo deliveries (SP $\to$ SP) operate efficiently (5.5% late rate, 12% freight burden). In contrast, long-haul inter-state corridors (SP $\to$ RJ, SP $\to$ BA, SP $\to$ MG) suffer acute bottlenecks: **SP $\to$ RJ alone accounts for R$ 138K in late exposure** with an 11.2% late delivery rate.

### 6. Statistical Confirmation: Delivery Delay & Customer Sentiment
- **On-Time Baseline:** Average Review Score = **4.29 / 5.00** (6.6% low reviews $\le 2$ stars).
- **1–2 Days Late:** Drops to **3.77** (13.7% low reviews).
- **3–5 Days Late:** Collapses to **2.47** (48.4% low reviews).
- **>5 Days Late:** Plummets to **1.74** (68.6% low reviews $\le 2$ stars).
- **Review Timing Nuance:** Among late orders, 70.2% of reviews were submitted *before* the order was delivered (reflecting prompt arrival survey response upon promised date breach, rather than post-delivery satisfaction).
- **Non-Parametric Tests:** Kruskal-Wallis $H = 10,316.60$ ($p < 10^{-15}$); Mann-Whitney $U$ rank-biserial effect size $r = -0.76$ for $>5$ days late.
- **Multivariate Logistic Regression:** Delivery delay is strongly conditionally associated with poor reviews ($\text{OR} = 1.064 \text{ per delay day}, p < 0.001$, coef = 0.0617), controlling for price, freight ratio, and interstate routing.

---

## 5. Intervention Prioritization Matrix

To ensure defensibility, sellers are classified into deterministic tiers using percentile thresholds across operational sellers meeting the **Minimum Volume Cutoff ($N \ge 30$)**:

$$\text{P1 Tier} = \{s \in \text{Sellers} \mid N_s \ge 30 \land E_s \ge P_{75}(E) \land (\text{LateRate}_s \ge P_{75}(\text{LateRate}) \lor \text{FreightBurden}_s \ge P_{75}(\text{FreightBurden}))\}$$

<!-- BEGIN_TIER_TABLE -->
| Priority Tier | Seller Count | % Seller Base | Total Orders* | Total GMV (R$) | Seller Late Exp (R$) | % Platform Seller Exp | Late Mitigation (Base 25%) | Recommended Operational Action |
|---|---|---|---|---|---|---|---|---|
| **P1 - Immediate Intervention** | **113** | **3.65%** | 20,576 | R$ 2.79M | **R$ 181,377.55** | **48.85%** | **R$ 45,344.39** | Lead-time calibration, packaging audit, carrier handoff inspection |
| P2 - Operational Investigation | 211 | 6.82% | 33,823 | R$ 3.72M | R$ 54,637.04 | 14.72% | R$ 13,659.26 | Carrier dispatch inspection, lane-specific carrier re-allocation |
| P3 - Operational Monitoring | 323 | 10.44% | 29,095 | R$ 3.98M | R$ 39,267.34 | 10.58% | R$ 9,816.83 | Automated portal threshold warnings; 30-day monitoring window |
| P4 - Low Volume / Standard Governance | 2,448 | 79.10% | 16,516 | R$ 3.10M | R$ 95,999.21 | 25.86% | R$ 23,999.80 | Routine partner management; low-volume sellers ($N < 30$) and healthy benchmarks |
<!-- END_TIER_TABLE -->

*\*Note: Total orders across tiers sum to 100,010 because multi-seller orders (1,278 orders) represent multiple seller-order fulfillment engagements.*

<!-- BEGIN_SENSITIVITY_CHECK -->
### Volume Cutoff Sensitivity Check
- **$N \ge 20$:** 150 P1 sellers, R$ 204.5K seller late exposure
- **$N \ge 30$ (Base):** 113 P1 sellers, R$ 181.4K seller late exposure
- **$N \ge 50$:** 69 P1 sellers, R$ 145.5K seller late exposure
<!-- END_SENSITIVITY_CHECK -->

---

## 6. Repository Architecture

```
marketplace-profitability-diagnostic/
│
├── README.md                                # Master project documentation & business narrative
│
├── pipeline/                                # LIGHTWEIGHT DATA ENGINEERING WRAPPER
│   ├── README.md                            # DE layer architecture & failure handling guide
│   ├── config.yaml                          # Declarative source, table, and validation configs
│   ├── logger.py                            # Structured run logger (console + JSON run logs)
│   ├── validation.py                        # Pre-ingestion and post-ingestion validation gates
│   ├── ingestion.py                         # Deterministic, idempotent CSV loader into DuckDB
│   └── run_pipeline.py                      # Master CLI orchestrator executing the 5-stage flow
│
├── logs/
│   ├── .gitkeep                             # Tracked log directory
│   └── run_*.json                           # Machine-readable pipeline run logs (gitignored)
│
├── data/
│   ├── raw/                                 # 9 official Olist CSV tables (downloaded & verified)
│   └── README.md                            # Data dictionary, grain definitions, and lineage
│
├── docs/
│   ├── stakeholder_requirements.md          # Translation: Business Question -> KPI -> Data -> Decision
│   └── data_lineage.md                      # End-to-end data lineage & grain control architecture
│
├── sql/                                     # FROZEN ANALYTICAL SQL CORE
│   ├── 01_schema.sql                        # Table definitions, constraints, portable data types
│   ├── 02_data_quality.sql                  # Null audits, multi-item/seller grain audits, anomaly checks
│   ├── 03_order_item_fact.sql               # fact_order_items (item grain) & fact_orders (order grain)
│   ├── 04_kpi_layer.sql                     # Decoupled 6-layer KPI views (Commercial, Fulfillment, Logistics)
│   ├── 05_root_cause_analysis.sql           # Dimensional breakdowns: Seller, Category, Corridor, Ticket
│   ├── 06_pareto_analysis.sql               # Cumulative exposure window functions & concentration curves
│   └── 07_intervention_priority.sql         # Rule-based percentile classification (P1 to P4 tiers)
│
├── notebooks/
│   └── business_analysis.ipynb              # 14-section Python diagnostic notebook with stats & visuals
│
├── dashboard/
│   ├── dashboard_spec.md                    # Power BI Star Schema, DAX dictionary, 1-page visual spec
│   ├── generate_powerbi_data.py             # Direct export of clean modeling tables to CSV
│   └── powerbi_data/                        # Ready-to-import CSVs for Power BI / Tableau
│
├── report/
│   ├── decision_memo.md                     # Markdown decision memo
│   ├── generate_decision_memo_pdf.py        # ReportLab publication-quality PDF generator
│   └── decision_memo.pdf                    # Exactly 2-page executive decision memo
│
└── tests/
    ├── verify_pipeline.py                   # FROZEN authoritative analytical reconciliation test
    └── test_pipeline.py                     # Standalone unit test suite for the DE layer (9 tests)
```

---

## 7. Reproduction & Execution Instructions

### Prerequisites
- Python 3.9+ installed
- Packages: `duckdb`, `pandas`, `numpy`, `scipy`, `statsmodels`, `matplotlib`, `reportlab`, `pyyaml`

Install dependencies:
```bash
pip install duckdb pandas numpy scipy statsmodels matplotlib reportlab pyyaml
```

### 1. Execute Complete End-to-End Pipeline
Executes the master orchestrator (source validation, deterministic ingestion, pipeline health checks, the 7-stage analytical SQL suite, and automated verification gate):
```bash
python pipeline/run_pipeline.py
# Or on Windows:
py pipeline/run_pipeline.py
```

### 2. Run Data Engineering Unit Tests & Idempotency Check
Executes the 9 unit tests covering missing files, schema validation, empty tables, and dual-run idempotency reconciliation:
```bash
python -m unittest tests/test_pipeline.py
# Or on Windows:
py -m unittest tests/test_pipeline.py
```

### 3. Run Standalone Authoritative Analytical Reconciliation
Executes the analytical verification suite asserting row counts, foreign key integrity, financial reconciliation, bounded delivery rates ($97.02\% \le 100\%$), and priority allocations:
```bash
python tests/verify_pipeline.py
# Or on Windows:
py tests/verify_pipeline.py
```

### 4. Export Clean Power BI Star-Schema Tables
Generates pre-calculated dimensional and fact tables into `dashboard/powerbi_data/`:
```bash
python dashboard/generate_powerbi_data.py
# Or on Windows:
py dashboard/generate_powerbi_data.py
```

### 5. Generate Executive Decision Memo PDF
Compiles the publication-grade 2-page PDF memo:
```bash
python report/generate_decision_memo_pdf.py
# Or on Windows:
py report/generate_decision_memo_pdf.py
```

---

## 8. Defensibility & Interview Talking Points

| Common Interview Challenge | Methodologically Defensible Answer |
|---|---|
| *"How did you calculate profitability?"* | *"We explicitly avoided claiming actual profit because the dataset lacks unobserved platform costs (commissions, gateway fees, warehousing, carrier settlements). Instead, we separated observed metrics from derived transaction exposure and modeled scenario-based recoverable exposure."* |
| *"How did you catch and fix the 111.7% delivery rate anomaly?"* | *"Joining raw order items directly to parent orders created a multi-grain Cartesian fan-out where 110,197 delivered items were divided by 98,666 distinct orders. We decoupled the executive KPI query into separate order-level and item-level CTEs, mathematically restoring the true 97.02% delivery rate and 0.63% cancellation rate."* |
| *"Why did you add a lightweight data engineering layer?"* | *"To make the analytical engagement robust, testable, and reproducible. The pipeline features declarative YAML configuration, source validation gates, deterministic staging rebuilds, structured run logging, and an automated verification gate, without over-engineering with heavy production tools like Airflow or Spark."* |
| *"Why didn't you build an ML delay prediction model?"* | *"The business question was diagnostic and resource-allocation oriented: identifying which entities account for economic leakage and how to prioritize operations teams. A predictive model answers 'will this order be late?' whereas management needed to know 'which sellers and corridors should operations intervene on today to recover the most economic value?'"* |
| *"Why not prioritize sellers with the highest failure rates?"* | *"A seller with 2 orders and 100% late rate represents R$72 in exposure. Ranking purely by percentage misallocates operations capacity to statistical noise. We enforced a minimum volume cutoff (N >= 30) and cross-tabulated severity with economic exposure."* |
| *"Why use percentile rules instead of weighted scoring formulas?"* | *"Arbitrary weights (e.g. 0.5*Exposure + 0.3*Severity) cannot be defended in an executive meeting. Percentile thresholds (Volume >= 30, Exposure >= 75th percentile, Severity >= 75th percentile) are transparent, reproducible, and mathematically defensible."* |
| *"How do you guarantee DuckDB concurrency safety on Windows?"* | *"Persistent DuckDB connections hold exclusive file locks. We guaranteed lock release across all pipeline orchestrators and test runners via explicit `try ... finally: con.close()` cleanup, while secondary export tools connect in read-only mode (`read_only=True`)."* |
