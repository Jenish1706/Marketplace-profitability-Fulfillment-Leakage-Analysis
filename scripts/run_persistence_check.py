"""MP-06: seller-level bootstrap and markdown rendering for the 2017 -> 2018 persistence check.

The cohort and the rates come from SQL (view_seller_persistence_detail, which reads its P1 cohort from
view_seller_tiers_by_period, the same tier rule as the headline P1 tier). This module only resamples
sellers and formats the result, so every number in the docs is produced by one committed script.

Method: stratified seller-level bootstrap. Within each cohort (2017 P1 / all other sellers) sellers are
resampled with replacement N_BOOT times; pooled item-level rates, the P1-minus-other gap in each year,
and the change in the gap are recomputed for every resample. Intervals are 95% percentile intervals.
The seed is fixed so the rendered text is reproducible and the README render check is stable.
"""
import os
import sys

import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

N_BOOT = 5000
SEED = 20261121
P1_LABEL = "P1_2017"
OTHER_LABEL = "Other_2017"

# (outcome key, label, numerator column prefix)
OUTCOMES = (
    ("seller", "Seller-caused late rate (primary)", "seller_late_items"),
    ("all", "All-cause late rate (secondary)", "late_items"),
)


def load_detail(con):
    """Seller-level rows for sellers active in both years, with their 2017 cohort."""
    return con.execute("SELECT * FROM view_seller_persistence_detail ORDER BY seller_id").df()


def _rates(sums, outcome_col):
    """Pooled item-level rates (percent) for 2017 and 2018 from summed counts."""
    r17 = 100.0 * sums[f"{outcome_col}_2017"] / sums["delivered_items_2017"]
    r18 = 100.0 * sums[f"{outcome_col}_2018"] / sums["delivered_items_2018"]
    return r17, r18


def _group_arrays(detail, label):
    sub = detail[detail["tier_2017"] == label]
    cols = ["delivered_items_2017", "delivered_items_2018",
            "seller_late_items_2017", "seller_late_items_2018",
            "late_items_2017", "late_items_2018"]
    return len(sub), {c: sub[c].to_numpy(dtype=np.int64) for c in cols}


def _ci(samples):
    lo, hi = np.percentile(samples, [2.5, 97.5])
    return float(lo), float(hi)


def bootstrap_persistence(detail, n_boot=N_BOOT, seed=SEED):
    """Point estimates and 95% seller-level bootstrap intervals for both outcomes.

    Returns {outcome_key: {...}} with, per cohort, the 2017 and 2018 pooled rates, and for the gap
    (P1 minus other) the 2017 value, the 2018 value with its interval, the change with its interval,
    and the share of the 2017 gap still present in 2018.
    """
    rng = np.random.default_rng(seed)
    n1, g1 = _group_arrays(detail, P1_LABEL)
    n0, g0 = _group_arrays(detail, OTHER_LABEL)
    if n1 == 0 or n0 == 0:
        raise ValueError("persistence check needs sellers in both cohorts")

    # Point estimates on the full sample
    full = {lab: {c: int(a.sum()) for c, a in arrs.items()} for lab, arrs in ((P1_LABEL, g1), (OTHER_LABEL, g0))}

    # Bootstrap sums: one (n_boot,) vector per column and cohort
    idx1 = rng.integers(0, n1, size=(n_boot, n1))
    idx0 = rng.integers(0, n0, size=(n_boot, n0))
    boot = {
        P1_LABEL: {c: a[idx1].sum(axis=1) for c, a in g1.items()},
        OTHER_LABEL: {c: a[idx0].sum(axis=1) for c, a in g0.items()},
    }

    out = {}
    for key, _label, col in OUTCOMES:
        p1_17, p1_18 = _rates(full[P1_LABEL], col)
        ot_17, ot_18 = _rates(full[OTHER_LABEL], col)
        gap17, gap18 = p1_17 - ot_17, p1_18 - ot_18
        b1_17, b1_18 = _rates(boot[P1_LABEL], col)
        b0_17, b0_18 = _rates(boot[OTHER_LABEL], col)
        bgap17, bgap18 = b1_17 - b0_17, b1_18 - b0_18
        out[key] = {
            "n_p1": n1,
            "n_other": n0,
            "p1_2017": p1_17, "p1_2018": p1_18,
            "other_2017": ot_17, "other_2018": ot_18,
            "gap_2017": gap17, "gap_2017_ci": _ci(bgap17),
            "gap_2018": gap18, "gap_2018_ci": _ci(bgap18),
            "gap_change": gap18 - gap17, "gap_change_ci": _ci(bgap18 - bgap17),
            "share_remaining_pct": 100.0 * gap18 / gap17 if gap17 else float("nan"),
            "n_boot": n_boot,
        }
    return out


def unweighted_sensitivity(detail):
    """Seller-caused rates with every seller weighted equally (mean of seller-level rates), point estimates only."""
    d = detail.copy()
    for year in ("2017", "2018"):
        d[f"rate_{year}"] = 100.0 * d[f"seller_late_items_{year}"] / d[f"delivered_items_{year}"]
    means = d.groupby("tier_2017")[["rate_2017", "rate_2018"]].mean()
    p1, other = means.loc[P1_LABEL], means.loc[OTHER_LABEL]
    gap17, gap18 = p1["rate_2017"] - other["rate_2017"], p1["rate_2018"] - other["rate_2018"]
    return {
        "p1_2017": float(p1["rate_2017"]), "p1_2018": float(p1["rate_2018"]),
        "other_2017": float(other["rate_2017"]), "other_2018": float(other["rate_2018"]),
        "gap_2017": float(gap17), "gap_2018": float(gap18),
        "share_remaining_pct": float(100.0 * gap18 / gap17) if gap17 else float("nan"),
    }


def _pts(x, signed=False):
    return f"{x:+.2f} pts" if signed else f"{x:.2f} pts"


def _ci_text(ci, signed=False):
    lo, hi = ci
    return f"[{lo:+.2f}, {hi:+.2f}]" if signed else f"[{lo:.2f}, {hi:.2f}]"


def render_persistence_markdown(con, n_boot=N_BOOT, seed=SEED):
    """Markdown block injected between the PERSISTENCE_CHECK markers (README, memo, guide 09)."""
    detail = load_detail(con)
    res = bootstrap_persistence(detail, n_boot=n_boot, seed=seed)
    s, a = res["seller"], res["all"]

    lines = [
        "### Out-of-Sample Persistence Check (2017 → 2018)",
        "",
        "The 2017 P1 cohort is chosen with the same tier rule as the headline P1 tier, applied to 2017 orders only "
        "(`view_seller_tiers_by_period`). Rates are item-level (late items ÷ delivered items), pooled over sellers "
        "active in both years; gaps are computed from unrounded rates. Intervals are 95% seller-level bootstrap "
        f"percentile intervals ({res['seller']['n_boot']:,} resamples, fixed seed).",
        "",
        "| Outcome | Cohort | 2017 | 2018 | Change |",
        "|---|---|---|---|---|",
    ]
    for key, label, _col in OUTCOMES:
        r = res[key]
        lines += [
            f"| {label} | 2017 P1 sellers (n = {r['n_p1']:,}) | {r['p1_2017']:.2f}% | {r['p1_2018']:.2f}% | {r['p1_2018'] - r['p1_2017']:+.2f} pts |",
            f"| | All other sellers (n = {r['n_other']:,}) | {r['other_2017']:.2f}% | {r['other_2018']:.2f}% | {r['other_2018'] - r['other_2017']:+.2f} pts |",
            f"| | **Gap (P1 − other)** | {_pts(r['gap_2017'])} | **{_pts(r['gap_2018'])}** {_ci_text(r['gap_2018_ci'])} | **{_pts(r['gap_change'], signed=True)}** {_ci_text(r['gap_change_ci'], signed=True)} |",
        ]

    still_positive = s["gap_2018_ci"][0] > 0
    shrinks = s["gap_change_ci"][1] < 0
    gap18_clause = (
        "is still positive (its interval excludes zero)" if still_positive
        else "is not distinguishable from zero (its interval includes zero)"
    )
    shrink_clause = (
        "a decrease whose interval excludes zero" if shrinks
        else "a change whose interval includes zero"
    )
    most_fades = s["share_remaining_pct"] < 50.0
    reading = (
        f"**Reading:** the seller-caused gap between 2017 P1 sellers and other sellers was {_pts(s['gap_2017'])} in 2017 "
        f"and {_pts(s['gap_2018'])} in 2018, which {gap18_clause}; the change of {_pts(s['gap_change'], signed=True)} is {shrink_clause}. "
        f"About {s['share_remaining_pct']:.0f}% of the 2017 gap remains in 2018. "
    )
    if most_fades:
        reading += (
            "Part of the P1 excess therefore persists, but most of it does not carry over. Shrinkage of this kind is what selecting "
            "sellers on a high 2017 rate produces even when underlying performance is stable (regression to the mean), and this check "
            "cannot separate that from genuine improvement. The P1 tier is a prioritisation list for review, not evidence that these "
            "sellers have a fixed trait."
        )
    else:
        reading += (
            "Most of the P1 excess therefore carries over into 2018. Selection on a high 2017 rate can still inflate the 2017 gap "
            "(regression to the mean), so this is one split of one year pair, not proof of a fixed seller trait."
        )
    u = unweighted_sensitivity(detail)
    sensitivity = (
        "*Sensitivity:* weighting every seller equally (unweighted means of seller-level rates) gives seller-caused rates of "
        f"{u['p1_2017']:.2f}% → {u['p1_2018']:.2f}% for P1 sellers and {u['other_2017']:.2f}% → {u['other_2018']:.2f}% for other sellers, "
        f"a gap of {u['gap_2017']:.2f} pts in 2017 and {u['gap_2018']:.2f} pts in 2018 ({u['share_remaining_pct']:.0f}% remains)."
    )
    lines += [
        "",
        reading,
        "",
        sensitivity,
        "",
        "*Limits:* sellers that stopped selling after 2017 are not in the 2018 comparison, and the all-cause outcome also counts "
        "carrier and promise-setting delay that sellers do not control.",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    from scripts.run_review_econometrics import get_db_connection

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252
    connection = get_db_connection(read_only=True)
    try:
        print(render_persistence_markdown(connection))
    finally:
        connection.close()
