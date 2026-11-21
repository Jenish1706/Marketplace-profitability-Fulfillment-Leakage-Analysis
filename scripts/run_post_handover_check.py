"""MP-09: is a late post-handover delay a transit problem or a promise-setting problem?

A late (order, seller) pair whose seller handed the parcel over by shipping_limit_date is a
"post-handover delay". The platform's second gate is the PROMISED date (order_estimated_delivery_date),
not a carrier SLA, so "the post-handover leg exceeded the promise" mixes how long the leg took with how
tight the promise was. For late versus on-time pairs on the same corridor this module compares

  promise_days  = purchase -> promised date        (how generous the promise was)
  transit_days  = handover -> delivery             (how long the leg actually took)

and runs a descriptive counterfactual on each late pair: would it have been on time with the corridor's
typical transit (median over all analysed pairs of the corridor), or with the corridor's typical promise?

If late pairs had normal transit but shorter promises, the cause would be promise-setting; if they had
longer transit it is the post-handover leg. The data has no carrier scans, so this cannot name WHICH party
caused a long leg.

Uncertainty: 95% percentile bootstrap intervals (N_BOOT resamples, fixed seed). Medians are bootstrapped
from the day-count histograms (multinomial resampling); the late pairs and the reference medians are
resampled separately, an approximation that is accurate because late pairs are a small share of a corridor.
"""
import os
import sys

import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

N_BOOT = 2000
SEED = 20261122
CORRIDORS = ("SP -> SP", "SP -> RJ", "SP -> MG", "SP -> BA")
MIN_POOLED_PAIRS = 100
LATE = "late_post_handover"
ONTIME = "on_time"
FIELDS = (("promise_days", "promise"), ("pre_handover_days", "pre"), ("transit_days", "transit"))


def load_pairs(con):
    # ORDER BY matters: DuckDB's parallel scan does not guarantee row order, and the bootstrap indexes into rows.
    return con.execute("SELECT * FROM view_post_handover_pairs ORDER BY order_id, seller_id").df()


def _hist(values):
    vals, cnt = np.unique(np.asarray(values, dtype=np.int64), return_counts=True)
    return vals.astype(float), cnt / cnt.sum(), int(cnt.sum())


def _boot_medians(values, rng, n_boot):
    """Bootstrap distribution of the median of integer data via multinomial resampling of its histogram."""
    vals, probs, n = _hist(values)
    cum = rng.multinomial(n, probs, size=n_boot).cumsum(axis=1)
    i_lo = (cum >= (n + 1) // 2).argmax(axis=1)
    i_hi = (cum >= n // 2 + 1).argmax(axis=1)
    return (vals[i_lo] + vals[i_hi]) / 2.0


def _ci(samples):
    lo, hi = np.percentile(samples, [2.5, 97.5])
    return float(lo), float(hi)


def corridor_stats(pairs, corridor, n_boot=N_BOOT, seed=SEED):
    rng = np.random.default_rng(seed)
    d = pairs[pairs["corridor"] == corridor]
    late = d[d["delay_class"] == LATE]
    ont = d[d["delay_class"] == ONTIME]
    out = {"corridor": corridor, "n_late": int(len(late)), "n_on_time": int(len(ont))}
    for col, key in FIELDS:
        m_late, m_ont = float(np.median(late[col])), float(np.median(ont[col]))
        gap_samples = _boot_medians(late[col], rng, n_boot) - _boot_medians(ont[col], rng, n_boot)
        out[f"{key}_late"], out[f"{key}_on_time"] = m_late, m_ont
        out[f"{key}_gap"], out[f"{key}_gap_ci"] = m_late - m_ont, _ci(gap_samples)

    # Counterfactuals with corridor-typical references (all analysed pairs, so not selected on the outcome)
    t_ref, p_ref = float(np.median(d["transit_days"])), float(np.median(d["promise_days"]))
    pre, prom, trans = (late[c].to_numpy(dtype=np.int64) for c in ("pre_handover_days", "promise_days", "transit_days"))
    out["t_ref"], out["p_ref"] = t_ref, p_ref
    out["share_transit"] = float(np.mean(pre + t_ref <= prom))      # on time with typical transit
    out["share_promise"] = float(np.mean(pre + trans <= p_ref))     # on time with typical promise
    t_boot, p_boot = _boot_medians(d["transit_days"], rng, n_boot), _boot_medians(d["promise_days"], rng, n_boot)
    idx = rng.integers(0, len(late), size=(n_boot, len(late)))
    out["share_transit_ci"] = _ci(np.mean(pre[idx] + t_boot[:, None] <= prom[idx], axis=1))
    out["share_promise_ci"] = _ci(np.mean(pre[idx] + trans[idx] <= p_boot[:, None], axis=1))
    return out


def pooled_stats(pairs):
    """Point estimates over every corridor with enough pairs, using each corridor's own references."""
    sizes = pairs.groupby("corridor")["order_id"].transform("size")
    d = pairs[sizes >= MIN_POOLED_PAIRS].copy()
    d["t_ref"] = d.groupby("corridor")["transit_days"].transform("median")
    d["p_ref"] = d.groupby("corridor")["promise_days"].transform("median")
    late = d[d["delay_class"] == LATE]
    return {
        "n_late": int(len(late)),
        "n_corridors": int(d["corridor"].nunique()),
        "share_transit": float(np.mean(late["pre_handover_days"] + late["t_ref"] <= late["promise_days"])),
        "share_promise": float(np.mean(late["pre_handover_days"] + late["transit_days"] <= late["p_ref"])),
    }


def counts(con, pairs):
    headline = con.execute(
        "SELECT COUNT(*) FROM (SELECT 1 FROM fact_order_items WHERE is_late = 1 GROUP BY order_id, seller_id)"
    ).fetchone()[0]
    n_post = int((pairs["delay_class"] == LATE).sum())
    n_seller = int((pairs["delay_class"] == "late_seller_dispatch").sum())
    return {"headline_late": int(headline), "post_handover": n_post, "seller_dispatch": n_seller,
            "excluded": int(headline) - n_post - n_seller}


def compute(con, n_boot=N_BOOT, seed=SEED):
    pairs = load_pairs(con)
    return {
        "counts": counts(con, pairs),
        "corridors": [corridor_stats(pairs, c, n_boot, seed) for c in CORRIDORS],
        "pooled": pooled_stats(pairs),
    }


def _d(x, signed=False):
    return f"{x:+.0f}" if signed else f"{x:.0f}"


def _ci_i(ci):
    return f"[{ci[0]:+.0f}, {ci[1]:+.0f}]"


def _pct(x):
    return f"{100 * x:.1f}%"


def _pct_ci(x, ci):
    return f"{_pct(x)} [{_pct(ci[0])}, {_pct(ci[1])}]"


def _transit_driven(res):
    """True when, in every listed corridor, the late pairs' transit gap dwarfs their promise gap and the typical
    transit would have rescued far more of them than the typical promise."""
    return all(c["transit_gap"] > 3 * abs(c["promise_gap"]) and c["share_transit"] > c["share_promise"]
               for c in res["corridors"])


def summary_sentence(res):
    c = res["counts"]
    by = {r["corridor"]: r for r in res["corridors"]}
    rj, sp = by["SP -> RJ"], by["SP -> SP"]
    share = 100.0 * c["post_handover"] / c["headline_late"]
    verdict = (
        "so the extra delay is transit-driven rather than a promise-setting artefact"
        if _transit_driven(res) else
        "so promise-setting cannot be ruled out as a driver"
    )
    return (
        f"**Post-handover delay (transit vs promise).** Of {c['headline_late']:,} late (order, seller) pairs, {c['post_handover']:,} "
        f"({share:.2f}%) were handed over by the shipping limit, so the delay arose after handover; {c['seller_dispatch']:,} were already late at dispatch. "
        f"On the same corridor these late pairs spent a median of {_d(rj['transit_late'])} days in transit versus {_d(rj['transit_on_time'])} for on-time pairs on SP → RJ "
        f"({_d(sp['transit_late'])} versus {_d(sp['transit_on_time'])} on SP → SP), while their promises were only {_d(abs(rj['promise_gap']))} days shorter on SP → RJ "
        f"and {_d(abs(sp['promise_gap']))} on SP → SP, {verdict}. The dataset has no carrier scans, so it cannot say which party caused the extra transit. "
        "Method and corridor table: guide 09."
    )


def render_split_markdown(con, n_boot=N_BOOT, seed=SEED):
    res = compute(con, n_boot, seed)
    c, pooled = res["counts"], res["pooled"]
    lines = [
        "### Post-Handover Delay: Transit vs Promise",
        "",
        f"Scope: {c['post_handover']:,} late post-handover (order, seller) pairs (seller handed over by `shipping_limit_date`, delivery after the "
        f"promised date) against on-time pairs on the same corridor. {c['seller_dispatch']:,} late pairs were already late at dispatch and "
        f"{c['excluded']:,} late pair(s) have no recorded handover date; both are outside this table. Days are date-level. Intervals are 95% bootstrap percentile "
        f"intervals ({n_boot:,} resamples, fixed seed).",
        "",
        "**Median days, late post-handover pairs vs on-time pairs (gap, interval)**",
        "",
        "| Corridor | Pairs (late / on-time) | Purchase → promised date | Purchase → handover | Handover → delivery (transit) |",
        "|---|---|---|---|---|",
    ]
    for r in res["corridors"]:
        lines.append(
            f"| {r['corridor']} | {r['n_late']:,} / {r['n_on_time']:,} "
            f"| {_d(r['promise_late'])} vs {_d(r['promise_on_time'])} ({_d(r['promise_gap'], True)} {_ci_i(r['promise_gap_ci'])}) "
            f"| {_d(r['pre_late'])} vs {_d(r['pre_on_time'])} ({_d(r['pre_gap'], True)} {_ci_i(r['pre_gap_ci'])}) "
            f"| **{_d(r['transit_late'])} vs {_d(r['transit_on_time'])}** ({_d(r['transit_gap'], True)} {_ci_i(r['transit_gap_ci'])}) |"
        )
    lines += [
        "",
        "**Would the late pairs have been on time? (descriptive counterfactual)**",
        "",
        "| Corridor | Late post-handover pairs | On time with the corridor's typical transit | On time with the corridor's typical promise |",
        "|---|---|---|---|",
    ]
    for r in res["corridors"]:
        lines.append(
            f"| {r['corridor']} | {r['n_late']:,} | **{_pct_ci(r['share_transit'], r['share_transit_ci'])}** "
            f"(typical transit {_d(r['t_ref'])} d) | {_pct_ci(r['share_promise'], r['share_promise_ci'])} (typical promise {_d(r['p_ref'])} d) |"
        )
    lines.append(
        f"| All {pooled['n_corridors']} corridors with at least {MIN_POOLED_PAIRS} pairs (point estimates) | {pooled['n_late']:,} "
        f"| {_pct(pooled['share_transit'])} | {_pct(pooled['share_promise'])} |"
    )
    reading = (
        "**Reading:** late pairs spent far longer in transit than on-time pairs on the same corridor, while their promises were only slightly shorter; "
        "giving them the corridor's typical transit would have put most of them on time, whereas a typical promise would have rescued few. "
        "The delay is therefore transit-driven rather than a promise-setting artefact."
        if _transit_driven(res) else
        "**Reading:** the transit and promise differences are of comparable size in at least one corridor, so promise-setting cannot be ruled out as a driver."
    )
    lines += [
        "",
        reading,
        "",
        "*Limits:* the dataset has no carrier scans, so a long post-handover leg cannot be attributed to the carrier, to last-mile or to customer availability; "
        "handover dates are recorded by sellers, so a manifest scanned before the parcel physically left would hide dispatch delay inside transit; "
        "the counterfactuals are descriptive, not causal.",
    ]
    return "\n".join(lines)


def render_summary_markdown(con, n_boot=N_BOOT, seed=SEED):
    return summary_sentence(compute(con, n_boot, seed))


if __name__ == "__main__":
    from scripts.run_review_econometrics import get_db_connection

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    connection = get_db_connection(read_only=True)
    try:
        print(render_split_markdown(connection))
        print()
        print(render_summary_markdown(connection))
    finally:
        connection.close()
