# Power BI Dashboard Specification

**Title:** Marketplace Profitability & Fulfillment Leakage Diagnostic  
**Target Audience:** Chief Operating Officer (COO), VP of Marketplace Operations, Head of Logistics  
**Page Budget:** Exactly 1 Executive Operations Dashboard Page  

---

## 1. Data Model & Star Schema Architecture

The dashboard is built on a clean star schema centered around order and line-item analytics, connected to validated dimensional tables.

```
                  ┌──────────────────────┐
                  │     dim_calendar     │
                  └──────────┬───────────┘
                             │ 1
                             │ 
                             │ *
┌──────────────────┐  *   ┌──┴──────────────────┐   *   ┌──────────────────────┐
│    dim_seller    ├──────┤  fact_orders_model  ├───────┤ dim_product_category │
└──────────────────┘ 1    └──┬──────────────────┘    1  └──────────────────────┘
                             │ 1
                             │
                             │ *
                  ┌──────────┴───────────┐
                  │ corridor_root_cause  │
                  └──────────────────────┘
```

### Table Dictionary & Relationships

| From Table (Dimension) | From Column | To Table (Fact) | To Column | Cardinality | Cross-Filter |
|---|---|---|---|---|---|
| `dim_calendar` | `date` | `fact_orders_model` | `order_purchase_date` | 1 to Many (`1:*`) | Single |
| `dim_seller` | `seller_id` | `seller_intervention_scorecard` | `seller_id` | 1 to 1 (`1:1`) | Both |
| `dim_product_category` | `product_category` | `category_root_cause` | `product_category` | 1 to 1 (`1:1`) | Both |
| `corridor_root_cause` | `corridor` | `corridor_root_cause` | `corridor` | Direct Analysis Table | Single |

---

## 2. Core DAX Measures Dictionary

Copy-pasteable DAX definitions organized across the 6-layer analytical framework:

### Layer 1: Commercial Performance
```dax
Total GMV = 
SUM(fact_orders_model[gmv])

Total Orders = 
DISTINCTCOUNT(fact_orders_model[order_id])

Platform AOV = 
DIVIDE([Total GMV], [Total Orders], 0)
```

### Layer 2: Fulfillment Performance
```dax
Delivered Orders = 
CALCULATE(
    COUNTROWS(fact_orders_model),
    fact_orders_model[is_delivered] = 1
)

Late Orders = 
CALCULATE(
    COUNTROWS(fact_orders_model),
    fact_orders_model[is_late] = 1
)

Late Delivery Rate % = 
DIVIDE([Late Orders], [Delivered Orders], 0)

Avg Delivery Delay Days = 
AVERAGE(fact_orders_model[delivery_delay_days])
```

### Layer 3: Logistics Economics
```dax
Total Freight = 
SUM(fact_orders_model[total_freight])

Freight Burden % = 
DIVIDE([Total Freight], [Total GMV], 0)

Avg Freight Per Order = 
DIVIDE([Total Freight], [Total Orders], 0)
```

### Layer 4: Customer Experience
```dax
Average Review Score = 
AVERAGE(fact_orders_model[avg_review_score])

Low Review Count = 
CALCULATE(
    COUNTROWS(fact_orders_model),
    fact_orders_model[is_low_review] = 1
)

Low Review Rate % = 
DIVIDE([Low Review Count], [Total Orders], 0)
```

### Layer 5: Economic Exposure (Observable)
```dax
Late Order GMV Exposure = 
SUM(seller_intervention_scorecard[late_gmv_exposure])

Late Order Freight Exposure = 
SUM(seller_intervention_scorecard[late_freight_exposure])

Total Late Transaction Exposure = 
SUM(seller_intervention_scorecard[total_late_transaction_exposure])

High Freight GMV Exposure = 
SUM(seller_intervention_scorecard[high_freight_gmv_exposure])
```

### Layer 6: Scenario-Based Recoverable Exposure
```dax
Recoverable Exposure Conservative (10%) = 
CALCULATE(
    [Total Late Transaction Exposure] * 0.10,
    dim_seller[priority_tier] = "P1 - Immediate Intervention"
)

Recoverable Exposure Base (25%) = 
CALCULATE(
    [Total Late Transaction Exposure] * 0.25,
    dim_seller[priority_tier] = "P1 - Immediate Intervention"
)

Recoverable Exposure Optimistic (40%) = 
CALCULATE(
    [Total Late Transaction Exposure] * 0.40,
    dim_seller[priority_tier] = "P1 - Immediate Intervention"
)
```

---

## 3. Executive Dashboard Layout & Visual Wireframe

The dashboard is structured into 4 distinct functional zones across a standard 16:9 canvas (1920 × 1080 px):

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ HEADER: Marketplace Profitability & Fulfillment Diagnostic        [Slicers: Date, Tier]│
├────────────────────────────────────────────────────────────────────────────────────────┤
│ [ GMV: R$13.59M ] [ Orders: 98.7K ] [ Late Rate: 7.9% ] [ Freight: 16.6% ] [ Rev: 4.03 ] [ P1 Exp: R$378K ]│
├───────────────────────────────────────────┬────────────────────────────────────────────┤
│ VISUAL 1: Business Trend Inflection       │ VISUAL 2: Pareto Concentration Curve       │
│ Dual-Axis: Monthly GMV vs Late Rate %     │ Cumulative % of Exposure vs Seller Decile  │
│ (Highlights Nov '17 & Mar '18 Spikes)     │ (Proves Top 10% Sellers = 75.8% Exposure)  │
├───────────────────────────────────────────┼────────────────────────────────────────────┤
│ VISUAL 3: Volume × Severity Matrix        │ VISUAL 4: High-Friction Corridors          │
│ Scatter: Late Rate (X) vs Exposure (Y)    │ Bar/Matrix: Seller State -> Customer State │
│ Bubble: Volume | Color: Priority Tier     │ (Focus on SP -> RJ/BA/MG Interstate Lanes) │
├───────────────────────────────────────────┴────────────────────────────────────────────┤
│ VISUAL 5: Priority Intervention & Operational Action Scorecard                         │
│ Columns: Seller ID | Tier | Orders | Late Rate | Total Exposure | Action Playbook      │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### Visual Specifications

1. **Top KPI Cards Ribbon:**
   - 6 KPI Cards formatted with clear currency (`R$`) and percentage (`%`) formatting.
   - P1 Exposure card highlighted in operational amber/red.
2. **Visual 1 (Monthly Macro Trend):**
   - Line and Clustered Column Chart.
   - Shared Axis: `monthly_business_kpis[year_month]`.
   - Column: `gmv`. Line 1: `late_delivery_rate_pct`. Line 2: `freight_burden_pct`.
   - Clear operational callout flags at Nov 2017 (Black Friday strain: 14.3% late) and March 2018 (Severe fulfillment failure: 21.4% late).
3. **Visual 2 (Pareto Concentration Curve):**
   - Stepped Area / Line Chart.
   - X-Axis: `view_seller_pareto_deciles[exposure_decile]`.
   - Y-Axis: `cumulative_exposure_share_pct`.
   - Reference line at 80% exposure mark demonstrating decile concentration.
4. **Visual 3 (Volume × Severity Matrix - Signature Visual):**
   - Scatter Chart.
   - X-Axis: `late_item_rate_pct` (Operational Severity).
   - Y-Axis: `total_late_transaction_exposure` (Economic Exposure).
   - Bubble Size: `total_orders` (Volume).
   - Legend / Color: `priority_tier` (P1: Red, P2: Orange, P3: Yellow, P4: Grey).
   - Demonstrates volume decoupling (why a seller with 20% late rate and R$20K exposure outranks a seller with 80% late rate and R$500 exposure).
5. **Visual 4 (Origin-Destination Corridor Matrix):**
   - Clustered Bar Chart of Top 15 Interstate Lanes sorted by `late_transaction_exposure`.
   - Primary focus on SP $\to$ RJ, SP $\to$ BA, and SP $\to$ MG routes.
6. **Visual 5 (Interactive Action Scorecard):**
   - Table Visual showing Sellers and Categories.
   - Slicers enabled for `priority_tier` (P1 to P4).
   - Displays deterministic action playbooks (e.g., "Direct Seller SLA Review & Mandatory Lead-Time Calibration").

---

## 4. Power BI Desktop Import Instructions

1. Open Power BI Desktop $\to$ **Get Data** $\to$ **Folder** (or **Text/CSV**).
2. Point to `dashboard/powerbi_data/`.
3. Load the 6 core files:
   - `fact_orders_model.csv`
   - `dim_calendar.csv`
   - `dim_seller.csv`
   - `monthly_business_kpis.csv`
   - `seller_intervention_scorecard.csv`
   - `corridor_root_cause.csv`
4. Confirm relationships match the Star Schema table in Section 1.
5. Create a new measure table `_Measures` and paste the DAX definitions above.
