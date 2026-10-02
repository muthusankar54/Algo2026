"""Static charts for the report (results/*.png). Run after run_all:  python -m patternlab.charts"""
from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .data import load_daily
from .regime import decompose
from .run_all import IS_END, RESULTS

BLUE, ORANGE = "#2a78d6", "#eb6834"
INK, INK2, MUTED, GRID, BASE, SURFACE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "font.family": "sans-serif", "font.size": 10, "text.color": INK, "axes.labelcolor": INK2,
    "axes.edgecolor": BASE, "axes.linewidth": 0.8, "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
    "axes.spines.top": False, "axes.spines.right": False, "legend.frameon": False,
    "axes.titlesize": 12, "axes.titleweight": "bold", "axes.titlelocation": "left",
})


def _title(fig, text):
    fig.suptitle(text, x=0.012, ha="left", fontsize=12, fontweight="bold", color=INK)


def _save(fig, name):
    fig.tight_layout()
    fig.savefig(RESULTS / name, dpi=150)
    plt.close(fig)


def overnight_vs_intraday():
    d = decompose(load_daily("nifty_50"))
    fig, ax = plt.subplots(figsize=(9, 4.2))
    for col, color, label in (("overnight", BLUE, "Overnight (prev close → open)"),
                              ("intraday", ORANGE, "Intraday (open → close)")):
        s = 100 * d[col].cumsum()
        ax.plot(s.index, s, color=color, lw=2, label=label)
        ax.annotate(f"{s.iloc[-1]:+.0f}%", (s.index[-1], s.iloc[-1]), xytext=(6, 0),
                    textcoords="offset points", va="center", color=INK, fontsize=10)
    ax.axhline(0, color=BASE, lw=1)
    _title(fig, "Nifty 50: all of the gain since 2012 came overnight")
    ax.set_ylabel("Cumulative log return, %")
    ax.legend(loc="upper left")
    ax.text(0, -0.16, "Daily NSE data Feb 2012 – Sep 2026. Part of the intraday loss is the 09:15 opening-print "
            "effect (see time-of-day chart).", transform=ax.transAxes, color=MUTED, fontsize=8)
    _save(fig, "chart_overnight_vs_intraday.png")


def discovery_funnel(s):
    ho = s["hold_out"]
    steps = [("Patterns tested (in-sample 2015-2020)", s["discovery"]["candidates_tested"]),
             ("Look good: t > 2 after costs", s["discovery"]["naive_t_gt_2"]),
             ("...still profitable in 2021-24 hold-out", round(ho["naive_discoveries"] * ho["naive_pct_positive_oos"] / 100)),
             ("...hold-out t > 2", round(ho["naive_discoveries"] * ho["naive_pct_oos_t_gt_2"] / 100)),
             ("Survive Reality Check over all 24,488 (FWER < 5%)", s["reality_check"]["patterns_with_fwer_p_lt_0.05"])]
    fig, ax = plt.subplots(figsize=(9, 3.6))
    y = np.arange(len(steps))[::-1]
    vals = [max(v, 0.8) for _, v in steps]
    ax.barh(y, vals, color=BLUE, height=0.55)
    ax.set_xscale("log")
    ax.set_yticks(y, [label for label, _ in steps])
    for yi, (_, v) in zip(y, steps):
        ax.text(max(v, 0.8) * 1.15, yi, f"{v:,}", va="center", color=INK, fontsize=10)
    ax.set_xlim(0.7, 2e5)
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("Number of patterns (log scale)")
    _title(fig, "Pattern-discovery funnel at today's costs (6.9 bps round trip)")
    _save(fig, "chart_discovery_funnel.png")


def is_vs_oos():
    t = pd.read_csv(RESULTS / "top_patterns_in_sample.csv")
    fig, ax = plt.subplots(figsize=(6.5, 5))
    naive = t["t"] > 2
    ax.scatter(t.loc[~naive, "net_bps"], t.loc[~naive, "oos_net_bps"], s=22, color=BLUE, alpha=0.7,
               edgecolor=SURFACE, linewidth=0.8, label="Next 139 by in-sample t")
    ax.scatter(t.loc[naive, "net_bps"], t.loc[naive, "oos_net_bps"], s=28, color=ORANGE,
               edgecolor=SURFACE, linewidth=0.8, label="'Discoveries' (in-sample t > 2)")
    lim = [0, max(40, t["net_bps"].max() + 2)]
    ax.plot(lim, lim, color=MUTED, lw=1)
    ax.text(lim[1] * 0.72, lim[1] * 0.76, "hold-out = in-sample", color=MUTED, fontsize=8, rotation=35)
    ax.axhline(0, color=INK2, lw=1)
    ax.set_xlabel("In-sample net edge, bps per trade (2015-2020)")
    ax.set_ylabel("Hold-out net edge, bps per trade (2021-2024)")
    _title(fig, "Top 200 mined patterns: the edge does not carry over")
    ax.legend(loc="upper left")
    _save(fig, "chart_in_sample_vs_hold_out.png")


def null_distributions(s):
    boot = np.load(RESULTS / "max_t_bootstrap.npy")
    placebo = pd.read_csv(RESULTS / "placebo_runs.csv")
    fig, ax = plt.subplots(figsize=(8, 3.8))
    bins = np.linspace(2, 6.5, 46)
    ax.hist(boot, bins=bins, color=BLUE, alpha=0.75, label="Reality-Check bootstrap: best t under 'no edge'")
    ax.hist(placebo["max_t"], bins=bins, color=ORANGE, alpha=0.75, label="Placebo: best t on shuffled outcomes")
    obs = s["discovery"]["max_t"]
    ax.axvline(obs, color=INK, lw=2)
    ax.text(obs - 0.05, ax.get_ylim()[1] * 0.95, f"best real pattern\nt = {obs:.2f}", color=INK, fontsize=9,
            va="top", ha="right")
    ax.set_xlabel("Best t-statistic among 24,488 patterns")
    ax.set_ylabel("Runs")
    _title(fig, "The best real pattern sits inside the range of pure luck")
    ax.legend(loc="upper right", fontsize=8)
    _save(fig, "chart_best_t_vs_noise.png")


def top10_equity():
    p = pd.read_csv(RESULTS / "top10_portfolio_daily_pnl.csv", index_col=0, parse_dates=True)["net_bps"]
    cum = p.cumsum() / 100
    fig, ax = plt.subplots(figsize=(9, 3.8))
    ins, oos = cum[cum.index < IS_END], cum[cum.index >= IS_END]
    ax.plot(ins.index, ins, color=BLUE, lw=2, label="In-sample (patterns chosen here)")
    ax.plot(oos.index, oos, color=ORANGE, lw=2, label="Hold-out (never seen by discovery)")
    ax.axvline(pd.Timestamp(IS_END), color=MUTED, lw=1)
    ax.axhline(0, color=BASE, lw=1)
    ax.set_ylabel("Cumulative net return, % of notional")
    _title(fig, "Top-10 mined patterns traded together, after today's costs")
    ax.legend(loc="upper left")
    _save(fig, "chart_top10_equity.png")


def event_study():
    ev = pd.read_csv(RESULTS / "geopolitical_event_study.csv")
    ev = ev.iloc[::-1]
    fig, ax = plt.subplots(figsize=(9, 6.2))
    y = np.arange(len(ev))
    ax.barh(y + 0.2, ev["gap_pct"], height=0.38, color=BLUE, label="Overnight gap at 09:15")
    ax.barh(y - 0.2, ev["intraday_pct"], height=0.38, color=ORANGE, label="Open → close")
    ax.set_yticks(y, [f"{d}  {e}" for d, e in zip(ev["date"], ev["event"])], fontsize=8)
    ax.axvline(0, color=INK2, lw=1)
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("Nifty 50 move, %")
    _title(fig, "Geopolitical shock days: most of the move lands in the 09:15 gap")
    ax.legend(loc="lower left", fontsize=8)
    _save(fig, "chart_event_study.png")


def edge_vs_cost(s):
    h = pd.read_csv(RESULTS / "hypotheses.csv")
    h = h[h["period"].str.startswith("hold-out")]
    names = {"H1": "Intraday momentum (Gao et al.)", "H2a": "Opening-range breakout 15m + stop",
             "H2b": "Opening-range breakout 30m + stop", "H2c": "Opening-range breakout 15m",
             "H3a": "Gap fade", "H3b": "Gap-and-go"}
    labels = [names[x.split()[0]] for x in h["strategy"]]
    vals = h["gross_bps_per_trade"].tolist()
    zero = next(x for x in s["cost_sensitivity"] if x["scenario"] == "zero")
    labels.append("Top-50 mined patterns")
    vals.append(zero["top50_mean_oos_net_bps"])
    fig, ax = plt.subplots(figsize=(9, 3.8))
    y = np.arange(len(vals))[::-1]
    ax.barh(y, vals, color=BLUE, height=0.55)
    ax.set_yticks(y, labels)
    for yi, v in zip(y, vals):
        ax.text(v + (0.15 if v >= 0 else -0.15), yi, f"{v:+.1f}", va="center",
                ha="left" if v >= 0 else "right", fontsize=9, color=INK,
                bbox=dict(facecolor=SURFACE, edgecolor="none", pad=1))
    c = s["costs_bps_round_trip"]
    for val, lab, ypos in ((c["pre_apr2026"], "cost before\nApr 2026", y[-1] - 0.45), (c["base"], "cost now", y[-1] - 0.45)):
        ax.axvline(val, color=INK, lw=1.2)
        ax.text(val + 0.12, ypos, f"{lab}: {val:.1f} bps", fontsize=8, color=INK, va="bottom")
    ax.axvline(0, color=BASE, lw=1)
    ax.set_xlim(min(vals) - 2, 9)
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("Gross edge before costs in the 2021-2024 hold-out, bps per trade")
    _title(fig, "Every gross edge found is smaller than one round-trip cost")
    _save(fig, "chart_edge_vs_cost.png")


def time_of_day():
    t = pd.read_csv(RESULTS / "time_of_day_drift.csv")
    segs = t["segment"].unique()
    fig, ax = plt.subplots(figsize=(8, 3.6))
    x = np.arange(len(segs))
    for off, (per, color) in zip((-0.2, 0.2), (("in-sample 2015-2020", BLUE), ("hold-out 2021-2024Q1", ORANGE))):
        v = t[t["period"] == per].set_index("segment").loc[segs, "mean_bps"]
        ax.bar(x + off, v, width=0.38, color=color, label=per)
    ax.axhline(0, color=INK2, lw=1)
    ax.set_xticks(x, segs, fontsize=9)
    ax.grid(axis="x", visible=False)
    ax.set_ylabel("Mean return per day, bps")
    _title(fig, "Much of the intraday drift is the untradeable 09:15 opening print")
    ax.legend(loc="lower right", fontsize=8)
    _save(fig, "chart_time_of_day.png")


def main():
    s = json.loads((RESULTS / "summary.json").read_text())
    overnight_vs_intraday()
    discovery_funnel(s)
    is_vs_oos()
    null_distributions(s)
    top10_equity()
    event_study()
    edge_vs_cost(s)
    time_of_day()


if __name__ == "__main__":
    main()
