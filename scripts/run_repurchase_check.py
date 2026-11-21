"""MP-10: the measured link from late delivery to repurchase (the churn that "exposure" only assumed).

Cohort (view_first_order_repurchase): customers whose first delivered order was placed before 2018-03-01, so a
full 180-day follow-up fits inside the data. Outcome: another order (not canceled/unavailable) within 180 days of
the first one. Exposure: the first order was delivered after its promised date (date-level, same convention as
is_late).

What this module reports
  1. Raw repurchase rates with Wilson intervals and the late-minus-on-time difference (parametric bootstrap).
  2. Logistic regressions of repurchase on first-order lateness, controlling for customer state and the category
     of the first order (the specification asked for), and again adding the month of the first order (lateness
     spiked in the Nov 2017 and Feb-Mar 2018 peaks, when promotional customers also repurchase less). HC1 robust
     standard errors; one row per customer, so no clustering is needed.
  3. A value bound: how much repeat-purchase value the measured gap implies is at stake, and the ceiling if
     lateness removed every repeat purchase an on-time customer would make.

These are associations in observational data, not causal effects.
"""
import os
import sys

import numpy as np
import pandas as pd

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

N_BOOT = 5000
SEED = 20261123
MIN_LEVEL_CUSTOMERS = 300
Z = 1.959963984540054


def load_df(con):
    df = con.execute("SELECT * FROM view_first_order_repurchase ORDER BY customer_unique_id").df()
    df["first_month"] = pd.to_datetime(df["first_purchase_ts"]).dt.strftime("%Y-%m")
    # Pool sparse levels so no cell is empty or (quasi-)separated: levels with few customers go to "other"
    for source, target in (("first_order_category", "category_group"), ("customer_state", "state_group"), ("first_month", "month_group")):
        counts = df[source].value_counts()
        keep = set(counts[counts >= MIN_LEVEL_CUSTOMERS].index)
        df[target] = df[source].where(df[source].isin(keep), "other")
    df["late"] = df["first_order_late"].astype(int)
    df["y"] = df["repurchased_180d"].astype(int)
    return df


def wilson(k, n):
    p = k / n
    denom = 1 + Z ** 2 / n
    centre = (p + Z ** 2 / (2 * n)) / denom
    half = Z * np.sqrt(p * (1 - p) / n + Z ** 2 / (4 * n ** 2)) / denom
    return float(centre - half), float(centre + half)


def _ci(samples):
    lo, hi = np.percentile(samples, [2.5, 97.5])
    return float(lo), float(hi)


def raw_and_bound(df, n_boot=N_BOOT, seed=SEED):
    rng = np.random.default_rng(seed)
    late, ont = df[df["late"] == 1], df[df["late"] == 0]
    n1, n0 = len(late), len(ont)
    k1, k0 = int(late["y"].sum()), int(ont["y"].sum())
    p1, p0 = k1 / n1, k0 / n0

    # Parametric bootstrap of both rates (customers are independent, one row each)
    b1 = rng.binomial(n1, p1, size=n_boot) / n1
    b0 = rng.binomial(n0, p0, size=n_boot) / n0
    diff, diff_ci = p1 - p0, _ci(b1 - b0)

    # Value bound. v_bar = mean repeat-purchase value per repurchaser (all repurchasers pooled).
    rep_values = df.loc[df["y"] == 1, "repeat_value_180d"].to_numpy(dtype=float)
    v_bar = float(rep_values.mean())
    v_boot = rng.choice(rep_values, size=(n_boot, len(rep_values))).mean(axis=1)
    late_value = float(late["first_order_value"].sum())
    lost = (p0 - p1) * n1                       # repurchasers "missing" among late customers (if the gap were causal)
    lost_boot = (b0 - b1) * n1
    implied = lost * v_bar
    implied_boot = lost_boot * v_boot
    mean_first = late_value / n1
    ceiling_share = p0 * v_bar / mean_first     # if lateness removed every repeat purchase at the on-time rate
    ceiling_boot = b0 * v_boot / mean_first
    return {
        "n_late": n1, "n_on_time": n0, "k_late": k1, "k_on_time": k0,
        "rate_late": p1, "rate_on_time": p0,
        "rate_late_ci": wilson(k1, n1), "rate_on_time_ci": wilson(k0, n0),
        "diff": diff, "diff_ci": diff_ci,
        "relative_change": diff / p0, "relative_change_ci": _ci((b1 - b0) / b0),
        "v_bar": v_bar, "v_bar_ci": _ci(v_boot),
        "lost_repurchasers": lost, "lost_repurchasers_ci": _ci(lost_boot),
        "implied_value": implied, "implied_value_ci": _ci(implied_boot),
        "late_first_order_value": late_value,
        "implied_share": implied / late_value, "implied_share_ci": (_ci(implied_boot)[0] / late_value, _ci(implied_boot)[1] / late_value),
        "ceiling_share": ceiling_share, "ceiling_share_ci": _ci(ceiling_boot),
        "n_boot": n_boot,
    }


def fit_logits(df):
    import statsmodels.formula.api as smf

    specs = (
        ("State + first-order category", "y ~ late + C(state_group) + C(category_group)"),
        ("State + category + first-order month", "y ~ late + C(state_group) + C(category_group) + C(month_group)"),
    )
    out = []
    for label, formula in specs:
        res = smf.logit(formula, data=df).fit(disp=0, cov_type="HC1", maxiter=200)
        b, se, p = float(res.params["late"]), float(res.bse["late"]), float(res.pvalues["late"])
        ame, ame_se = average_marginal_effect(res, "late")
        out.append({
            "label": label, "n": int(res.nobs), "converged": bool(res.mle_retvals.get("converged", True)),
            "or": float(np.exp(b)), "or_ci": (float(np.exp(b - Z * se)), float(np.exp(b + Z * se))), "p": p,
            "ame_pts": 100 * ame, "ame_ci": (100 * (ame - Z * ame_se), 100 * (ame + Z * ame_se)),
        })
    return out


def average_marginal_effect(res, name):
    """Average marginal effect of a 0/1 regressor in a logit (mean over customers of P(y|x, d=1) - P(y|x, d=0)) with a
    delta-method standard error from the fitted (robust) covariance. Equivalent to statsmodels' get_margeff(at="overall",
    dummy=True) for this regressor, without computing effects for every control dummy."""
    X = np.asarray(res.model.exog, dtype=float)
    j = list(res.model.exog_names).index(name)
    beta, cov = np.asarray(res.params, dtype=float), np.asarray(res.cov_params(), dtype=float)
    x1, x0 = X.copy(), X.copy()
    x1[:, j], x0[:, j] = 1.0, 0.0
    p1, p0 = 1.0 / (1.0 + np.exp(-(x1 @ beta))), 1.0 / (1.0 + np.exp(-(x0 @ beta)))
    ame = float(np.mean(p1 - p0))
    grad = np.mean((p1 * (1 - p1))[:, None] * x1 - (p0 * (1 - p0))[:, None] * x0, axis=0)
    return ame, float(np.sqrt(grad @ cov @ grad))


def compute(con, n_boot=N_BOOT, seed=SEED):
    df = load_df(con)
    return {"raw": raw_and_bound(df, n_boot, seed), "logit": fit_logits(df), "n_categories": int(df["category_group"].nunique()),
            "n_states": int(df["state_group"].nunique()), "n_months": int(df["month_group"].nunique())}


def _pct(x):
    return f"{100 * x:.2f}%"


def _pct_ci(x, ci):
    return f"{_pct(x)} [{_pct(ci[0])}, {_pct(ci[1])}]"


def _pts(x, ci=None):
    s = f"{100 * x:+.2f} pts"
    return s if ci is None else f"{s} [{100 * ci[0]:+.2f}, {100 * ci[1]:+.2f}]"


def _p(p):
    return "< 0.001" if p < 0.001 else f"{p:.3f}"


def _verdict(res):
    raw, logit = res["raw"], res["logit"]
    raw_sig = raw["diff_ci"][1] < 0 or raw["diff_ci"][0] > 0
    adj_sig = all(l["or_ci"][1] < 1 or l["or_ci"][0] > 1 for l in logit)
    if raw_sig and adj_sig:
        return "sig"
    if not raw_sig and not adj_sig:
        return "none"
    return "mixed"


def framework_line(res):
    r = res["raw"]
    return (
        f"  └── Measured churn link (association): first-order-late customers repurchased within 180 days at {_pct(r['rate_late'])} vs {_pct(r['rate_on_time'])} "
        f"({_pts(r['diff'], r['diff_ci'])}); even if lateness removed every repeat purchase, at most {_pct(r['ceiling_share'])} of a late order's value is at stake"
    )


def render_all(con, n_boot=N_BOOT, seed=SEED):
    """(guide table markdown, one-line summary for the README Level-1 framing), computed once."""
    res = compute(con, n_boot, seed)
    return render_markdown(con, n_boot, seed, res=res), framework_line(res)


def render_markdown(con, n_boot=N_BOOT, seed=SEED, res=None):
    res = res if res is not None else compute(con, n_boot, seed)
    r, logit = res["raw"], res["logit"]
    verdict = _verdict(res)
    lines = [
        "### Lateness → Repurchase: The Measured Link to Churn",
        "",
        f"Cohort: {r['n_late'] + r['n_on_time']:,} customers whose first delivered order was placed before 2018-03-01, so a full 180-day follow-up fits in the data. "
        "A customer \"repurchased\" if they placed another order (not canceled or unavailable) within 180 days of the first. Observational association, not a causal effect. "
        f"Intervals are 95% (Wilson for rates; {r['n_boot']:,} bootstrap resamples with a fixed seed for differences and value bounds).",
        "",
        "| First order | Customers | Repurchased within 180 days |",
        "|---|---|---|",
        f"| Delivered on time | {r['n_on_time']:,} | {_pct_ci(r['rate_on_time'], r['rate_on_time_ci'])} |",
        f"| Delivered late | {r['n_late']:,} | {_pct_ci(r['rate_late'], r['rate_late_ci'])} |",
        f"| **Difference (late − on time)** | | **{_pts(r['diff'], r['diff_ci'])}** (relative {100 * r['relative_change']:+.1f}%) |",
        "",
        f"**Adjusted association (logit, HC1 robust SE; {res['n_states']} customer-state groups, {res['n_categories']} category groups and {res['n_months']} first-order-month groups; "
        f"levels with fewer than {MIN_LEVEL_CUSTOMERS} customers are pooled into \"other\")**",
        "",
        "| Controls | Odds ratio, late vs on time | p-value | Average marginal effect |",
        "|---|---|---|---|",
    ]
    for l in logit:
        lines.append(
            f"| {l['label']} | {l['or']:.3f} [{l['or_ci'][0]:.3f}, {l['or_ci'][1]:.3f}] | {_p(l['p'])} "
            f"| {l['ame_pts']:+.2f} pts [{l['ame_ci'][0]:+.2f}, {l['ame_ci'][1]:+.2f}] |"
        )
    lines += [
        "",
        "**How much value can lateness-driven churn explain? (bound on the \"exposure\")**",
        "",
        "| Quantity | Estimate | 95% interval |",
        "|---|---|---|",
        f"| Mean repeat-purchase value per repurchaser (180 days) | R$ {r['v_bar']:,.2f} | R$ {r['v_bar_ci'][0]:,.2f} to R$ {r['v_bar_ci'][1]:,.2f} |",
        f"| Repurchasers \"missing\" among late customers if the gap were causal | {r['lost_repurchasers']:.1f} | {r['lost_repurchasers_ci'][0]:.1f} to {r['lost_repurchasers_ci'][1]:.1f} |",
        f"| Implied repeat value at stake | R$ {r['implied_value']:,.0f} | R$ {r['implied_value_ci'][0]:,.0f} to R$ {r['implied_value_ci'][1]:,.0f} |",
        f"| … as a share of these late first orders' value (R$ {r['late_first_order_value']:,.0f}) | {_pct(r['implied_share'])} | {_pct(r['implied_share_ci'][0])} to {_pct(r['implied_share_ci'][1])} |",
        f"| **Ceiling**: share of a late order's value at stake if lateness removed every repeat purchase an on-time customer would make | **{_pct(r['ceiling_share'])}** | {_pct(r['ceiling_share_ci'][0])} to {_pct(r['ceiling_share_ci'][1])} |",
        "",
    ]
    if verdict == "none":
        reading = (
            "**Reading:** late first orders go with a lower repurchase rate, but the difference is not statistically distinguishable from zero, raw or adjusted. "
            "Repeat purchase is rare (about 3% within 180 days), so lateness-driven churn can explain at most a few percent of late-order value even in the extreme case. "
            "\"Exposure\" is therefore an upper bound on revenue at risk, not a measured loss."
        )
    elif verdict == "sig":
        reading = (
            "**Reading:** late first orders go with a lower repurchase rate, raw and adjusted, and the gap is statistically distinguishable from zero. "
            "It is small in value terms: repeat purchase is rare (about 3% within 180 days), so lateness-driven churn can explain at most a few percent of late-order value even in the extreme case."
        )
    else:
        reading = (
            "**Reading:** late first orders go with a lower repurchase rate, but statistical significance differs between the raw and adjusted comparisons, so the effect is not robustly "
            "distinguishable from zero. Repeat purchase is rare (about 3% within 180 days), so lateness-driven churn can explain at most a few percent of late-order value even in the extreme case."
        )
    lines += [
        reading,
        "",
        "*Limits:* a 180-day window and one cohort of first orders; repurchase is not lifetime value; lateness can also act through reviews and reputation, which this does not isolate; "
        "unobserved customer differences are not controlled.",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    from scripts.run_review_econometrics import get_db_connection

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    connection = get_db_connection(read_only=True)
    try:
        table_md, level1_line = render_all(connection)
        print(table_md)
        print()
        print(level1_line)
    finally:
        connection.close()
