import duckdb
import statsmodels.formula.api as smf
import numpy as np

con = duckdb.connect('marketplace.duckdb', read_only=True)
df_reg = con.execute('''
    SELECT 
        o.order_id,
        o.gmv,
        o.order_freight_burden AS freight_ratio,
        o.delivery_delay_days,
        r.review_score,
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
            MIN(seller_state) AS seller_state,
            MAX(is_interstate) AS is_interstate
        FROM fact_order_items
        GROUP BY order_id
    ) oi_seller ON o.order_id = oi_seller.order_id
    WHERE o.order_status = 'delivered' AND o.order_delivered_customer_date IS NOT NULL
''').df()

df_reg['delay_days_late'] = np.maximum(0, df_reg['delivery_delay_days'])
df_reg['log_price'] = np.log1p(df_reg['gmv'])
df_reg['low_review'] = (df_reg['review_score'] <= 2).astype(int)

logit_a = smf.logit('low_review ~ delay_days_late + freight_ratio + log_price + is_interstate', data=df_reg).fit(cov_type='cluster', cov_kwds={'groups': df_reg['seller_state']}, disp=False)
logit_b = smf.logit('low_review ~ undelivered_at_review + days_overdue_at_review + freight_ratio + log_price + is_interstate', data=df_reg).fit(cov_type='cluster', cov_kwds={'groups': df_reg['seller_state']}, disp=False)

ols_a = smf.ols('review_score ~ delay_days_late + freight_ratio + log_price + is_interstate', data=df_reg).fit(cov_type='HC1')
ols_b = smf.ols('review_score ~ undelivered_at_review + days_overdue_at_review + freight_ratio + log_price + is_interstate', data=df_reg).fit(cov_type='HC1')

print("=== MODEL A: Conventional Specification (Delivery Date Overdue Days) ===")
print(logit_a.summary().tables[1].as_text())
print(f"\nOdds Ratio per Late Delivery Day: exp({logit_a.params['delay_days_late']:.4f}) = {np.exp(logit_a.params['delay_days_late']):.4f}")

print("\n=== MODEL B: Customer Information Set at Review Time (P0-3 Resolution) ===")
print(logit_b.summary().tables[1].as_text())
print(f"\nOdds Ratio for Undelivered at Review: exp({logit_b.params['undelivered_at_review']:.4f}) = {np.exp(logit_b.params['undelivered_at_review']):.2f}x")
print(f"Odds Ratio per Overdue Day at Review: exp({logit_b.params['days_overdue_at_review']:.4f}) = {np.exp(logit_b.params['days_overdue_at_review']):.4f}")

print("\n=== OLS REGRESSION (MODEL B): Continuous Review Score [HC1 Robust SE] ===")
print(ols_b.summary().tables[1].as_text())
