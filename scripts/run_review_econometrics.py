"""
Script: scripts/run_review_econometrics.py
Purpose: Runs econometric specifications (Model A conventional delay vs Model B customer information set at review time).
Primary cluster-robust covariance uses seller_id (2,953 clusters).
Sensitivity checks report seller_state (27 clusters) and HC1 robust standard errors.
"""

import duckdb
import statsmodels.formula.api as smf
import numpy as np

def load_data(db_path='marketplace.duckdb'):
    con = duckdb.connect(db_path, read_only=True)
    try:
        df_reg = con.execute('''
            SELECT 
                o.order_id,
                o.gmv,
                o.order_freight_burden AS freight_ratio,
                o.delivery_delay_days,
                r.review_score,
                oi_seller.seller_id,
                oi_seller.seller_state,
                oi_seller.is_interstate,
                CASE WHEN o.order_delivered_customer_date IS NULL OR r.review_answer_timestamp < o.order_delivered_customer_date THEN 1.0 ELSE 0.0 END AS undelivered_at_review,
                GREATEST(0, CAST(r.review_answer_timestamp AS DATE) - CAST(o.order_estimated_delivery_date AS DATE)) AS days_overdue_at_review
            FROM fact_orders o
            JOIN (
                SELECT order_id, AVG(review_score) AS review_score, MAX(review_answer_timestamp) AS review_answer_timestamp
                FROM olist_order_reviews
                GROUP BY order_id
            ) r ON o.order_id = r.order_id
            LEFT JOIN (
                SELECT 
                    order_id, 
                    MIN(seller_id) AS seller_id,
                    MIN(seller_state) AS seller_state,
                    MAX(is_interstate) AS is_interstate
                FROM fact_order_items
                GROUP BY order_id
            ) oi_seller ON o.order_id = oi_seller.order_id
            WHERE o.order_status = 'delivered' AND o.order_delivered_customer_date IS NOT NULL
        ''').df()
    finally:
        con.close()

    df_reg['delay_days_late'] = np.maximum(0, df_reg['delivery_delay_days'])
    df_reg['log_price'] = np.log1p(df_reg['gmv'])
    df_reg['low_review'] = (df_reg['review_score'] <= 2).astype(int)
    return df_reg

def fit_models(df_reg):
    # Model A: Conventional Specification
    f_a = 'low_review ~ delay_days_late + freight_ratio + log_price + is_interstate'
    logit_a_seller = smf.logit(f_a, data=df_reg).fit(cov_type='cluster', cov_kwds={'groups': df_reg['seller_id']}, disp=False)
    logit_a_state = smf.logit(f_a, data=df_reg).fit(cov_type='cluster', cov_kwds={'groups': df_reg['seller_state']}, disp=False)
    logit_a_hc1 = smf.logit(f_a, data=df_reg).fit(cov_type='HC1', disp=False)

    ols_a_seller = smf.ols('review_score ~ delay_days_late + freight_ratio + log_price + is_interstate', data=df_reg).fit(cov_type='cluster', cov_kwds={'groups': df_reg['seller_id']})

    # Model B: Customer Information Set at Review Time
    f_b = 'low_review ~ undelivered_at_review + days_overdue_at_review + freight_ratio + log_price + is_interstate'
    logit_b_seller = smf.logit(f_b, data=df_reg).fit(cov_type='cluster', cov_kwds={'groups': df_reg['seller_id']}, disp=False)
    logit_b_state = smf.logit(f_b, data=df_reg).fit(cov_type='cluster', cov_kwds={'groups': df_reg['seller_state']}, disp=False)
    logit_b_hc1 = smf.logit(f_b, data=df_reg).fit(cov_type='HC1', disp=False)

    f_ols_b = 'review_score ~ undelivered_at_review + days_overdue_at_review + freight_ratio + log_price + is_interstate'
    ols_b_seller = smf.ols(f_ols_b, data=df_reg).fit(cov_type='cluster', cov_kwds={'groups': df_reg['seller_id']})
    ols_b_state = smf.ols(f_ols_b, data=df_reg).fit(cov_type='cluster', cov_kwds={'groups': df_reg['seller_state']})
    ols_b_hc1 = smf.ols(f_ols_b, data=df_reg).fit(cov_type='HC1')

    return {
        'logit_a': {'seller_id': logit_a_seller, 'seller_state': logit_a_state, 'HC1': logit_a_hc1},
        'ols_a': {'seller_id': ols_a_seller},
        'logit_b': {'seller_id': logit_b_seller, 'seller_state': logit_b_state, 'HC1': logit_b_hc1},
        'ols_b': {'seller_id': ols_b_seller, 'seller_state': ols_b_state, 'HC1': ols_b_hc1}
    }

def generate_regression_markdown_table(models):
    mb_logit = models['logit_b']
    mb_ols = models['ols_b']

    lines = [
        "| Dependent Variable | Predictor | Coef (β) | Odds Ratio | Primary SE (seller_id) | Robust SE (seller_state) | Robust SE (HC1) | p-value |",
        "|---|---|---|---|---|---|---|---|"
    ]

    var_labels = [
        ('undelivered_at_review', 'Undelivered at Review'),
        ('days_overdue_at_review', 'Days Overdue at Review'),
        ('freight_ratio', 'Freight Burden Ratio'),
        ('log_price', 'Log Order GMV'),
        ('is_interstate', 'Interstate Route')
    ]

    # Logistic
    for var, label in var_labels:
        coef = mb_logit['seller_id'].params[var]
        odds = np.exp(coef)
        se_seller = mb_logit['seller_id'].bse[var]
        se_state = mb_logit['seller_state'].bse[var]
        se_hc1 = mb_logit['HC1'].bse[var]
        pval = mb_logit['seller_id'].pvalues[var]
        pval_str = "< 0.001" if pval < 0.001 else f"{pval:.3f}"
        odds_str = f"{odds:.2f}x" if odds > 2.0 else f"{odds:.4f}"
        lines.append(f"| Low Review (≤ 2★) | {label} | {coef:+.4f} | {odds_str} | {se_seller:.4f} | {se_state:.4f} | {se_hc1:.4f} | {pval_str} |")

    # OLS
    for var, label in var_labels:
        coef = mb_ols['seller_id'].params[var]
        se_seller = mb_ols['seller_id'].bse[var]
        se_state = mb_ols['seller_state'].bse[var]
        se_hc1 = mb_ols['HC1'].bse[var]
        pval = mb_ols['seller_id'].pvalues[var]
        pval_str = "< 0.001" if pval < 0.001 else f"{pval:.3f}"
        lines.append(f"| Review Score (1–5) | {label} | {coef:+.4f} | — | {se_seller:.4f} | {se_state:.4f} | {se_hc1:.4f} | {pval_str} |")

    return "\n".join(lines)

def main():
    print("Loading data for econometrics analysis...")
    df_reg = load_data()
    print(f"Loaded {len(df_reg):,} records across {df_reg['seller_id'].nunique():,} unique sellers and {df_reg['seller_state'].nunique():,} states.")
    
    print("Fitting models with primary seller_id clusters and sensitivity checks...")
    models = fit_models(df_reg)

    ma = models['logit_a']['seller_id']
    mb = models['logit_b']['seller_id']
    ols_b = models['ols_b']['seller_id']

    print("\n=== MODEL A: Conventional Specification (Primary Clustered on seller_id) ===")
    print(ma.summary().tables[1].as_text())
    print(f"Odds Ratio per Late Delivery Day: exp({ma.params['delay_days_late']:.4f}) = {np.exp(ma.params['delay_days_late']):.4f}")

    print("\n=== MODEL B: Customer Information Set (Primary Clustered on seller_id) ===")
    print(mb.summary().tables[1].as_text())
    print(f"Odds Ratio for Undelivered at Review: exp({mb.params['undelivered_at_review']:.4f}) = {np.exp(mb.params['undelivered_at_review']):.2f}x")
    print(f"Odds Ratio per Overdue Day at Review: exp({mb.params['days_overdue_at_review']:.4f}) = {np.exp(mb.params['days_overdue_at_review']):.4f}")

    print("\n=== OLS REGRESSION (MODEL B): Continuous Review Score (Clustered on seller_id) ===")
    print(ols_b.summary().tables[1].as_text())

    print("\n=== STANDARD ERROR SENSITIVITY CHECK: Logistic Model B ===")
    print(generate_regression_markdown_table(models))

if __name__ == '__main__':
    main()
