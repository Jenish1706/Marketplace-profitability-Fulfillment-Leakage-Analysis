# Marketplace Profitability & Fulfillment Leakage Analysis
### Operational Unit Economics · Root-Cause Attribution · Pareto Allocation · Econometric Modeling

[![SQL](https://img.shields.io/badge/SQL-DuckDB-blue.svg)](sql/)
[![Python](https://img.shields.io/badge/Python-3.9.13-green.svg)](requirements.txt)
[![Documentation](https://img.shields.io/badge/Documentation-Guide%2000--09-orange.svg)](docs/guide/00_START_HERE.md)
[![Report](https://img.shields.io/badge/Report-Executive%20Decision%20Memo-red.svg)](report/decision_memo.pdf)
[![Tests](https://img.shields.io/badge/Verification-34%20Passed-brightgreen.svg)](tests/)

---

## 1. Executive Business Problem & Approach

As marketplace Gross Merchandise Value (GMV) scales, fulfillment friction frequently compresses contribution economics. This project analyzes **99,441 commercial orders** across Brazilian e-commerce (Olist dataset) to answer three executive operations questions:
1. **Fulfillment Attribution:** Are delivery delays driven by merchant dispatch breaches or carrier line-haul transit bottlenecks?
2. **Customer Sentiment Econometrics:** Does delivery delay degrade customer review scores through linear daily decay, or does automated survey timing create an unarrived-package step function penalty?
3. **Targeted Intervention:** Can high-friction merchants be isolated into a high-leverage priority cohort rather than penalizing sellers indiscriminately, and how much of that targeting carries over to the following year?

For the comprehensive 10-part technical documentation, start with the **[Public Guide: 00_START_HERE.md](docs/guide/00_START_HERE.md)**.

---

## 2. Three-Level Economic Framework

To avoid fabricating unobserved platform overheads (commissions, payment gateway fees, return processing costs), financial impact is evaluated strictly across three levels:

<!-- BEGIN_ECONOMIC_FRAMEWORK -->
```
LEVEL 1 — Late-Order GMV & Freight (Observable)
  ├── Late-Order GMV:                 E_late^GMV = R$ 985,924.34
  ├── Late-Order Freight:             E_late^freight = R$ 164,967.79
  └── Total Late-Order Value:         E_late = R$ 1,150,892.13 (Late-order GMV + freight)

LEVEL 2 — Cost Burden (Observable)
  ├── Platform Freight Burden:        Total Freight / Total GMV = 16.57%
  └── High-Freight Exposure:          R$ 1,855,750.93 GMV where Freight-to-Value >= 30%

LEVEL 3 — Illustrative Scenarios (Assumed Rates, Not Measured)
  Focuses on Priority 1 (P1) Sellers (R$ 181,377.55 Seller Late GMV+Freight across 113 merchants):
  ├── Conservative Scenario (10% Assumed Mitigation): R$ 18,137.76
  ├── Base Scenario (25% Assumed Mitigation):         R$ 45,344.39
  └── Optimistic Scenario (40% Assumed Mitigation):   R$ 72,551.02
```
<!-- END_ECONOMIC_FRAMEWORK -->

---

## 3. Audited Headline Results

### Priority Tiers ($N \ge 30$ Orders)
Sellers are segmented into transparent priority tiers based on seller-caused dispatch delay exposure:

<!-- BEGIN_TIER_TABLE -->
| Priority Tier | Seller Count | % Seller Base | Total Orders* | Total GMV (R$) | Seller Late Exp (R$) | % Platform Seller Exp | Late Mitigation (Base 25%) | Recommended Operational Action |
|---|---|---|---|---|---|---|---|---|
| **P1 - Immediate Intervention** | **113** | **3.65%** | 20,576 | R$ 2.79M | **R$ 181,377.55** | **48.85%** | **R$ 45,344.39** | Lead-time calibration, packaging audit, carrier handoff inspection |
| P2 - Operational Investigation | 211 | 6.82% | 33,823 | R$ 3.72M | R$ 54,637.04 | 14.72% | R$ 13,659.26 | Carrier dispatch inspection, lane-specific carrier re-allocation |
| P3 - Operational Monitoring | 323 | 10.44% | 29,095 | R$ 3.98M | R$ 39,267.34 | 10.58% | R$ 9,816.83 | Automated portal threshold warnings; 30-day monitoring window |
| P4 - Low Volume / Not Prioritised | 2,448 | 79.10% | 16,516 | R$ 3.10M | R$ 95,999.21 | 25.86% | R$ 23,999.80 | Routine partner management; low-volume sellers ($N < 30$) and standard baseline operations |
<!-- END_TIER_TABLE -->
*\*Total orders across tiers sum to 100,010 because multi-seller orders (1,278 orders) represent multiple seller fulfillment engagements.*

<!-- BEGIN_PERSISTENCE_CHECK -->
### Out-of-Sample Persistence Check (2017 → 2018)

The 2017 P1 cohort is chosen with the same tier rule as the headline P1 tier, applied to 2017 orders only (`view_seller_tiers_by_period`). Rates are item-level (late items ÷ delivered items), pooled over sellers active in both years; gaps are computed from unrounded rates. Intervals are 95% seller-level bootstrap percentile intervals (5,000 resamples, fixed seed).

| Outcome | Cohort | 2017 | 2018 | Change |
|---|---|---|---|---|
| Seller-caused late rate (primary) | 2017 P1 sellers (n = 52) | 4.99% | 2.97% | -2.02 pts |
| | All other sellers (n = 1,023) | 0.97% | 1.54% | +0.57 pts |
| | **Gap (P1 − other)** | 4.02 pts | **1.44 pts** [0.54, 2.77] | **-2.59 pts** [-4.78, -1.01] |
| All-cause late rate (secondary) | 2017 P1 sellers (n = 52) | 9.17% | 8.26% | -0.91 pts |
| | All other sellers (n = 1,023) | 4.68% | 7.75% | +3.06 pts |
| | **Gap (P1 − other)** | 4.49 pts | **0.51 pts** [-0.86, 2.14] | **-3.98 pts** [-6.04, -2.18] |

**Reading:** the seller-caused gap between 2017 P1 sellers and other sellers was 4.02 pts in 2017 and 1.44 pts in 2018, which is still positive (its interval excludes zero); the change of -2.59 pts is a decrease whose interval excludes zero. About 36% of the 2017 gap remains in 2018. Part of the P1 excess therefore persists, but most of it does not carry over. Shrinkage of this kind is what selecting sellers on a high 2017 rate produces even when underlying performance is stable (regression to the mean), and this check cannot separate that from genuine improvement. The P1 tier is a prioritisation list for review, not evidence that these sellers have a fixed trait.

*Sensitivity:* weighting every seller equally (unweighted means of seller-level rates) gives seller-caused rates of 7.63% → 4.89% for P1 sellers and 2.09% → 3.04% for other sellers, a gap of 5.55 pts in 2017 and 1.85 pts in 2018 (33% remains).

*Limits:* sellers that stopped selling after 2017 are not in the 2018 comparison, and the all-cause outcome also counts carrier and promise-setting delay that sellers do not control.
<!-- END_PERSISTENCE_CHECK -->

<!-- BEGIN_REGRESSION_TABLE -->
| Dependent Variable | Predictor | Coef (β) | Odds Ratio | Primary SE (seller_id) | Robust SE (seller_state) | Robust SE (HC1) | p-value |
|---|---|---|---|---|---|---|---|
| Low Review (≤ 2★) | Undelivered at Review | +3.5153 | 33.63x | 0.0506 | 0.0216 | 0.0377 | < 0.001 |
| Low Review (≤ 2★) | Days Overdue at Review | +0.0036 | 1.0036 | 0.0008 | 0.0006 | 0.0008 | < 0.001 |
| Low Review (≤ 2★) | Freight Burden Ratio | +0.6160 | 1.8515 | 0.1013 | 0.0910 | 0.0681 | < 0.001 |
| Low Review (≤ 2★) | Log Order GMV | +0.2903 | 1.3369 | 0.0353 | 0.0163 | 0.0187 | < 0.001 |
| Low Review (≤ 2★) | Interstate Route | +0.0623 | 1.0643 | 0.0343 | 0.0134 | 0.0255 | 0.069 |
| Review Score (1–5) | Undelivered at Review | -2.5125 | — | 0.0252 | 0.0161 | 0.0193 | < 0.001 |
| Review Score (1–5) | Days Overdue at Review | -0.0013 | — | 0.0005 | 0.0003 | 0.0005 | 0.006 |
| Review Score (1–5) | Freight Burden Ratio | -0.2486 | — | 0.0501 | 0.0593 | 0.0331 | < 0.001 |
| Review Score (1–5) | Log Order GMV | -0.0968 | — | 0.0168 | 0.0133 | 0.0083 | < 0.001 |
| Review Score (1–5) | Interstate Route | -0.0467 | — | 0.0130 | 0.0069 | 0.0092 | < 0.001 |
<!-- END_REGRESSION_TABLE -->

---

## 4. Quickstart & Master Verification

### Setup Environment
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Run End-to-End Master Verification
```powershell
python scripts/run_all.py
```
Executes staging ingestion, analytical SQL transformations, pipeline integrity assertions, documentation drift checks, and full pytest suite in ~45 seconds.

---

## 5. Documentation Navigation

- **[00: Start Here & Reading Order](docs/guide/00_START_HERE.md)**
- **[01: Core Concepts & Formulas](docs/guide/01_CONCEPTS.md)**
- **[02: Architecture & Data Flow](docs/guide/02_ARCHITECTURE.md)**
- **[03: Data Catalog & Schemas](docs/guide/03_DATA.md)**
- **[04: Methodology & Falsification](docs/guide/04_METHODOLOGY.md)**
- **[05: Code Walkthrough](docs/guide/05_CODE_WALKTHROUGH.md)**
- **[06: Operational Runbook](docs/guide/06_RUNBOOK.md)**
- **[07: Testing Strategy](docs/guide/07_TESTING.md)**
- **[08: Architecture Decision Records (ADRs)](docs/guide/08_DESIGN_DECISIONS.md)**
- **[09: Results & Limitations](docs/guide/09_RESULTS_AND_LIMITATIONS.md)**
- **[Alphabetical Glossary](docs/guide/GLOSSARY.md)**
- **[Executive Decision Memo (PDF)](report/decision_memo.pdf)**

---

## 6. Key Limitations & Threats to Validity

1. **Carrier Intermediate Telemetry:** The public dataset lacks sorting scan events, recording only handover and doorstep delivery. Couriers cannot be audited for transit milestones.
2. **Observational Bounds:** Financial mitigation numbers represent addressable exposure, not accounting profit or realized cash.
3. **Macro Context:** Analysis reflects Brazilian e-commerce logistics during 2017–2018 (including March 2018 postal disruptions).

---

## 7. License

Released under the [MIT License](https://opensource.org/licenses/MIT). Raw Olist dataset released on Kaggle under [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/).
