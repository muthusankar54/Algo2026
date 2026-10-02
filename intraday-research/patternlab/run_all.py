"""End-to-end study. Usage:  python -m patternlab.run_all [--boot 500] [--placebo 100]

Writes results/*.csv, results/summary.json; charts are drawn by patternlab.charts.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats as sps

from . import discovery as disc
from . import hypotheses, regime
from .costs import COST_SCENARIOS_BPS
from .data import load_daily, load_minute_panel
from .evals import scorecard, yearly_hit_rate
from .features import daily_context, eligible_days
from .stats import deflated_sharpe, min_backtest_length_years, pbo_cscv

RESULTS = Path(__file__).resolve().parents[1] / "results"
IS_END = "2021-01-01"  # discovery: Mar 2015 - Dec 2020 ; hold-out: Jan 2021 - Mar 2024
MIN_TRADES = 50
PERIODS = {"in-sample 2015-2020": ("2015-01-01", IS_END), "hold-out 2021-2024Q1": (IS_END, "2024-04-01")}


def _pattern_trades(combos, row, cost, dates):
    cd = combos[int(row.combo)]
    m = (cd.mask[int(row.i)] * cd.mask[int(row.j)]).astype(bool)
    sign = 1.0 if row.direction == "long" else -1.0
    return pd.Series(sign * cd.r[m] - cost, index=dates[m])


def _decay(is_edge: float, oos_edge: float):
    """Share of the in-sample edge kept out of sample; undefined if there was no edge."""
    return oos_edge / is_edge if is_edge > 0 else None


def main(n_boot: int = 500, n_placebo: int = 100, seed: int = 11) -> dict:
    t0 = time.time()
    RESULTS.mkdir(exist_ok=True)
    cost = COST_SCENARIOS_BPS["base"]
    stress = COST_SCENARIOS_BPS["stress"]
    panel = load_minute_panel()
    daily, vix = load_daily("nifty_50"), load_daily("india_vix")
    ctx = daily_context(daily, vix)
    elig = eligible_days(panel, ctx)
    is_mask = elig & (panel.dates < IS_END)
    oos_mask = elig & (panel.dates >= IS_END)
    summary: dict = {"data": {"minute_days_total": len(panel), "eligible_days": int(elig.sum()),
                              "in_sample_days": int(is_mask.sum()), "hold_out_days": int(oos_mask.sum()),
                              "in_sample": [str(panel.dates[is_mask][0].date()), str(panel.dates[is_mask][-1].date())],
                              "hold_out": [str(panel.dates[oos_mask][0].date()), str(panel.dates[oos_mask][-1].date())],
                              "daily_last_date": str(daily.index[-1].date())},
                     "costs_bps_round_trip": COST_SCENARIOS_BPS}

    # ---------------- 1. exhaustive discovery on the in-sample period ----------------
    c_is = disc.prepare(panel, ctx, is_mask)
    c_oos = disc.prepare(panel, ctx, oos_mask)
    c_all = disc.prepare(panel, ctx, elig)
    dates_all = panel.dates[elig]
    table = disc.score(c_is, cost, MIN_TRADES)
    table["pattern"] = [disc.pattern_name(c_is, r) for r in table.itertuples()]
    n_trials = len(table)
    summary["discovery"] = {
        "candidates_tested": n_trials,
        "naive_t_gt_2": int((table.t > 2).sum()),
        "naive_t_gt_2_and_win_gt_55pct": int(((table.t > 2) & (table.win_rate > 0.55)).sum()),
        "t_gt_3": int((table.t > 3).sum()),
        "bh_fdr_q_lt_0.10": int((table.p_bh < 0.10).sum()),
        "holm_p_lt_0.05": int((table.p_holm < 0.05).sum()),
        "max_t": float(table.t.max()),
    }

    # ---------------- 2. White's Reality Check (studentised max-t bootstrap) ----------
    max_t_boot = disc.reality_check(c_is, table, cost, MIN_TRADES, n_boot=n_boot, seed=seed)
    table["p_fwer"] = disc.fwer_pvalues(table.t.to_numpy(), max_t_boot)
    summary["reality_check"] = {"n_boot": n_boot, "max_t_boot_p50": float(np.median(max_t_boot)),
                                "max_t_boot_p95": float(np.quantile(max_t_boot, 0.95)),
                                "observed_max_t": float(table.t.max()),
                                "fwer_p_of_best": float(table.p_fwer.min()),
                                "patterns_with_fwer_p_lt_0.05": int((table.p_fwer < 0.05).sum())}
    np.save(RESULTS / "max_t_bootstrap.npy", max_t_boot)
    max_t_spa = disc.spa_check(c_is, cost, MIN_TRADES, n_boot=n_boot, seed=seed)
    table["p_spa"] = disc.fwer_pvalues(table.t.to_numpy(), max_t_spa)
    summary["spa"] = {"n_boot": n_boot, "max_t_null_p50": float(np.median(max_t_spa)),
                      "max_t_null_p95": float(np.quantile(max_t_spa, 0.95)),
                      "spa_p_of_best": float(table.p_spa.min()),
                      "patterns_with_spa_p_lt_0.05": int((table.p_spa < 0.05).sum())}
    np.save(RESULTS / "max_t_spa.npy", max_t_spa)

    # ---------------- 3. placebo: same pipeline on outcomes shuffled across days -------
    rng = np.random.default_rng(seed)
    placebo = []
    for _ in range(n_placebo):
        perm = rng.permutation(len(c_is[0].r))
        tab_p = disc.score(c_is, cost, MIN_TRADES, outcomes=[cd.r[perm] for cd in c_is])
        placebo.append({"naive_t_gt_2": int((tab_p.t > 2).sum()), "t_gt_3": int((tab_p.t > 3).sum()),
                        "max_t": float(tab_p.t.max())})
    placebo = pd.DataFrame(placebo)
    placebo.to_csv(RESULTS / "placebo_runs.csv", index=False)
    summary["placebo"] = {
        "n_runs": n_placebo,
        "naive_t_gt_2_mean": float(placebo.naive_t_gt_2.mean()),
        "naive_t_gt_2_p95": float(placebo.naive_t_gt_2.quantile(0.95)),
        "t_gt_3_mean": float(placebo.t_gt_3.mean()),
        "max_t_mean": float(placebo.max_t.mean()),
        "max_t_p95": float(placebo.max_t.quantile(0.95)),
        "real_naive_t_gt_2_percentile_vs_placebo": float((placebo.naive_t_gt_2 < summary["discovery"]["naive_t_gt_2"]).mean()),
        "real_max_t_percentile_vs_placebo": float((placebo.max_t < table.t.max()).mean()),
    }

    # ---------------- 4. PBO of the "pick the best backtest" process -------------------
    bs, bq, bn = disc.block_stats(c_is, table, cost, n_blocks=10)
    summary["pbo"] = pbo_cscv(bs, bq, bn, min_count=10)

    # ---------------- 5. hold-out evaluation of what discovery picked ------------------
    table = table.sort_values("t", ascending=False).reset_index(drop=True)
    oos = disc.evaluate_on(c_oos, table, cost)
    oos_stress = disc.evaluate_on(c_oos, table, stress)
    table = table.join(oos).join(oos_stress[["oos_net_bps"]].rename(columns={"oos_net_bps": "oos_net_bps_stress"}))
    naive = table[table.t > 2]
    top10 = table.head(10)
    valid = table[table.oos_n >= 20]
    summary["hold_out"] = {
        "naive_discoveries": len(naive),
        "naive_pct_positive_oos": float(100 * (naive.oos_net_bps > 0).mean()),
        "naive_median_is_net_bps": float(naive.net_bps.median()),
        "naive_median_oos_net_bps": float(naive.oos_net_bps.median()),
        "naive_pct_oos_t_gt_2": float(100 * (naive.oos_t > 2).mean()),
        "top10_mean_is_net_bps": float(top10.net_bps.mean()),
        "top10_mean_oos_net_bps": float(top10.oos_net_bps.mean()),
        "spearman_is_t_vs_oos_t_all": float(sps.spearmanr(valid.t, valid.oos_t, nan_policy="omit")[0]),
        "all_candidates_pct_positive_oos": float(100 * (valid.oos_net_bps > 0).mean()),
    }
    cols = ["pattern", "n", "gross_bps", "net_bps", "t", "win_rate", "p_bh", "p_fwer", "p_spa",
            "oos_n", "oos_net_bps", "oos_t", "oos_win_rate", "oos_net_bps_stress"]
    table.head(200)[cols].to_csv(RESULTS / "top_patterns_in_sample.csv", index=False, float_format="%.4f")

    # Equal-weight portfolio of the top-10 in-sample patterns, traded in the hold-out.
    port = pd.concat([_pattern_trades(c_all, r, cost, dates_all) for r in top10.itertuples()], axis=1)
    daily_pnl = port.fillna(0).sum(axis=1) / 10
    daily_pnl.rename("net_bps").to_csv(RESULTS / "top10_portfolio_daily_pnl.csv")

    # ---------------- 6. scorecards (eval gates) --------------------------------------
    best = table.iloc[0]
    best_trades = disc.trades(c_is, best, cost)
    var_sr = float((table.net_bps / table.sd_bps).var())
    dsr = deflated_sharpe(best_trades, n_trials, var_sr)
    summary["best_pattern"] = {"pattern": best.pattern, **{k: float(v) if isinstance(v, (int, float, np.floating)) else v
                                                         for k, v in dsr.items()}}
    summary["min_backtest_length_years_for_annual_sr_1"] = min_backtest_length_years(n_trials, 1.0)
    full_best = _pattern_trades(c_all, best, cost, dates_all)
    cards = [scorecard(f"Best mined pattern: {best.pattern}", {
        "net_positive": best.net_bps, "t_stat": best.t, "fwer": best.p_spa, "dsr": dsr["dsr"],
        "pbo": summary["pbo"]["pbo"], "oos_positive": best.oos_net_bps, "oos_t": best.oos_t,
        "decay": _decay(best.net_bps, best.oos_net_bps), "stress_cost": best.oos_net_bps_stress,
        "yearly": yearly_hit_rate(full_best.to_numpy(), full_best.index), "sample": int(best.n)})]
    is_p = daily_pnl[daily_pnl.index < IS_END]
    oos_p = daily_pnl[daily_pnl.index >= IS_END]
    cards.append(scorecard("Top-10 mined patterns, equal weight", {
        "net_positive": is_p.mean(), "t_stat": is_p.mean() / (is_p.std() / np.sqrt(len(is_p))),
        "fwer": None, "dsr": None, "pbo": summary["pbo"]["pbo"],
        "oos_positive": oos_p.mean(), "oos_t": oos_p.mean() / (oos_p.std() / np.sqrt(len(oos_p))),
        "decay": _decay(is_p.mean(), oos_p.mean()), "stress_cost": None,
        "yearly": yearly_hit_rate(daily_pnl.to_numpy(), daily_pnl.index), "sample": int((is_p != 0).sum())}))

    # ---------------- 7. pre-registered literature hypotheses --------------------------
    hyp_panel = panel.subset(elig)
    hyp, strat_net = hypotheses.run_all(hyp_panel, ctx, cost, PERIODS)
    hyp_stress, _ = hypotheses.run_all(hyp_panel, ctx, stress, PERIODS)
    hyp["net_bps_at_stress_cost"] = hyp_stress["net_bps_per_trade"].to_numpy()
    hyp.to_csv(RESULTS / "hypotheses.csv", index=False, float_format="%.4f")
    hypotheses.expiry_day_profile(hyp_panel, ctx).to_csv(RESULTS / "expiry_day_profile.csv", index=False,
                                                          float_format="%.3f")
    for name, net in strat_net.items():
        s = pd.Series(net, index=hyp_panel.dates)
        i_s, o_s = s[s.index < IS_END].dropna(), s[s.index >= IS_END].dropna()
        _, o_s_stress = (lambda x: (None, x[x.index >= IS_END].dropna() - (stress - cost)))(s)
        cards.append(scorecard(name, {
            "net_positive": i_s.mean(), "t_stat": i_s.mean() / (i_s.std() / np.sqrt(len(i_s))),
            "fwer": min(1.0, len(strat_net) * sps.norm.sf(i_s.mean() / (i_s.std() / np.sqrt(len(i_s))))),
            "dsr": None, "pbo": None, "oos_positive": o_s.mean(),
            "oos_t": o_s.mean() / (o_s.std() / np.sqrt(len(o_s))), "decay": _decay(i_s.mean(), o_s.mean()),
            "stress_cost": o_s_stress.mean(), "yearly": yearly_hit_rate(s.to_numpy(), s.index),
            "sample": len(i_s)}))
    cards = pd.concat(cards, ignore_index=True)
    cards.to_csv(RESULTS / "eval_scorecards.csv", index=False, float_format="%.4f")
    summary["scorecards"] = (cards.groupby("candidate", sort=False)["result"]
                             .apply(lambda r: f"{(r == 'PASS').sum()} pass / {(r == 'FAIL').sum()} fail / {(r == 'n/a').sum()} n/a")
                             .to_dict())

    # ---------------- 8. cost sensitivity of discovery --------------------------------
    sens = []
    for label, cbps in COST_SCENARIOS_BPS.items():
        tab_c = disc.score(c_is, cbps, MIN_TRADES).sort_values("t", ascending=False).head(50)
        ev = disc.evaluate_on(c_oos, tab_c, cbps)
        sens.append({"scenario": label, "cost_bps": cbps,
                     "in_sample_t_gt_2": int((disc.score(c_is, cbps, MIN_TRADES).t > 2).sum()),
                     "top50_mean_is_net_bps": float(tab_c.net_bps.mean()),
                     "top50_mean_oos_net_bps": float(ev.oos_net_bps.mean()),
                     "top50_pct_positive_oos": float(100 * (ev.oos_net_bps > 0).mean())})
    pd.DataFrame(sens).to_csv(RESULTS / "cost_sensitivity.csv", index=False, float_format="%.3f")
    summary["cost_sensitivity"] = sens

    # ---------------- 9. daily-data regime analyses (to Sep 2026) ----------------------
    d = regime.decompose(daily)
    yp = regime.yearly_profile(d, vix, cost)
    yp.to_csv(RESULTS / "yearly_overnight_vs_intraday.csv", float_format="%.4f")
    ev = regime.event_study(d, vix)
    ev.to_csv(RESULTS / "geopolitical_event_study.csv", index=False, float_format="%.3f")
    eras = {"2015-2020": ("2015-01-01", IS_END), "2021-2024Q1": (IS_END, "2024-04-01"),
            "2024Q2-2026Q3": ("2024-04-01", "2026-12-31")}
    regime.gap_conditional_open_to_close(d, eras, cost).to_csv(RESULTS / "gap_open_to_close_by_era.csv",
                                                               index=False, float_format="%.3f")
    neg = ev[ev.gap_pct < 0]
    summary["regime"] = {
        "overnight_cum_log_pct_2012_2026": float(100 * d["overnight"].sum()),
        "intraday_cum_log_pct_2012_2026": float(100 * d["intraday"].sum()),
        "overnight_var_share_2026": float(yp.loc[2026, "overnight_var_share"]),
        "overnight_var_share_median_2012_2025": float(yp.loc[:2025, "overnight_var_share"].median()),
        "tail_attribution_top50_since_2012": regime.tail_attribution(d, 50),
        "event_days_negative_gap": len(neg),
        "event_days_negative_gap_intraday_rebound": int((neg.intraday_pct > 0).sum()),
        "nifty_sensex": regime.nifty_sensex_correlation(daily, load_daily("sensexietf")),
        "nifty_vs_nifty_etf_rho": float(regime.nifty_sensex_correlation(daily, load_daily("niftybees"))["rho_daily"]),
    }
    tod = []
    for label, (a, b) in PERIODS.items():
        m = elig & (panel.dates >= a) & (panel.dates < b)
        for seg, x, y in (("09:15 open print->09:16", panel.open[m, 0], panel.close[m, 0]),
                          ("09:16->09:30", panel.close[m, 0], panel.close[m, disc.price_col("09:30")]),
                          ("09:30->12:00", panel.close[m, disc.price_col("09:30")], panel.close[m, disc.price_col("12:00")]),
                          ("12:00->15:00", panel.close[m, disc.price_col("12:00")], panel.close[m, disc.price_col("15:00")]),
                          ("15:00->15:30", panel.close[m, disc.price_col("15:00")], panel.close[m, 374])):
            r = 1e4 * np.log(y / x)
            tod.append({"period": label, "segment": seg, "mean_bps": r.mean(),
                        "t": r.mean() / (r.std() / np.sqrt(len(r))), "cum_pct": r.sum() / 100})
    pd.DataFrame(tod).to_csv(RESULTS / "time_of_day_drift.csv", index=False, float_format="%.3f")

    summary["runtime_sec"] = round(time.time() - t0, 1)
    (RESULTS / "summary.json").write_text(json.dumps(summary, indent=2, default=float))
    return summary


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--boot", type=int, default=500)
    ap.add_argument("--placebo", type=int, default=100)
    args = ap.parse_args()
    s = main(args.boot, args.placebo)
    print(json.dumps(s, indent=2, default=float))
