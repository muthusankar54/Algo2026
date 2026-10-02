"""Pre-registered, literature-driven intraday strategies (not data-mined).

Each is specified up front with fixed parameters, so a plain t-test is legitimate
(only a handful of variants are tried, reported together).
  H1  Intraday momentum (Gao, Han, Li & Zhou 2018): sign of the return from the previous
      close to 09:45 picks the direction of the 15:00 -> 15:30 trade.
  H2  Opening-range breakout (15 / 30 minute range), stop at the far side of the range,
      exit 15:15.
  H3  Gap fade / gap-and-go: after a gap larger than 0.5 daily sigma, trade 09:20 -> 15:15
      against (fade) or with (go) the gap.
  H4  Weekly-expiry days: does intraday range or late-day drift differ?
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .data import IntradayPanel, minute_index
from .discovery import price_col


def _summ(name: str, net: np.ndarray, dates: pd.DatetimeIndex) -> dict:
    net = net[~np.isnan(net)] if dates is None else net
    n = len(net)
    sd = net.std(ddof=1)
    return {"strategy": name, "n_trades": n, "net_bps_per_trade": net.mean(),
            "t": net.mean() / (sd / np.sqrt(n)), "win_rate": (net > 0).mean(),
            "total_net_pct": net.sum() / 100}


def _split(name, net, dates, periods):
    rows = []
    for label, (a, b) in periods.items():
        m = (dates >= a) & (dates < b) & ~np.isnan(net)
        if m.sum() > 5:
            rows.append({**_summ(name, net[m], None), "period": label})
    return rows


def intraday_momentum(panel, ctx, cost_bps):
    prev_close = ctx["prev_close"].reindex(panel.dates).to_numpy()
    signal = np.sign(np.log(panel.close[:, price_col("09:45")] / prev_close))
    last30 = 1e4 * np.log(panel.close[:, price_col("15:30")] / panel.close[:, price_col("15:00")])
    net = signal * last30 - cost_bps
    net[signal == 0] = np.nan  # no signal, no trade
    return net


def opening_range_breakout(panel, minutes: int, cost_bps: float, use_stop: bool = True):
    """First close outside the opening range triggers entry at that close."""
    h, l, c = panel.high, panel.low, panel.close
    orh, orl = h[:, :minutes].max(1), l[:, :minutes].min(1)
    last = price_col("15:15")
    net = np.full(len(panel), np.nan)
    for d in range(len(panel)):
        seg = c[d, minutes:last]
        up = np.flatnonzero(seg > orh[d])
        dn = np.flatnonzero(seg < orl[d])
        first_up = up[0] if len(up) else 10 ** 6
        first_dn = dn[0] if len(dn) else 10 ** 6
        if first_up == first_dn:  # no breakout
            continue
        side = 1 if first_up < first_dn else -1
        k = minutes + min(first_up, first_dn)
        entry = c[d, k]
        exit_ = c[d, last]
        if use_stop:
            stop = orl[d] if side == 1 else orh[d]
            path_low, path_high = l[d, k + 1:last + 1], h[d, k + 1:last + 1]
            hit = np.flatnonzero(path_low <= stop) if side == 1 else np.flatnonzero(path_high >= stop)
            if len(hit):
                exit_ = stop
        net[d] = side * 1e4 * np.log(exit_ / entry) - cost_bps
    return net


def gap_trade(panel, ctx, cost_bps, mode: str):
    prev_close = ctx["prev_close"].reindex(panel.dates).to_numpy()
    sig = ctx["sigma20"].reindex(panel.dates).to_numpy()
    gap_z = (panel.open[:, 0] / prev_close - 1) / sig
    r = 1e4 * np.log(panel.close[:, price_col("15:15")] / panel.close[:, price_col("09:20")])
    sign = -np.sign(gap_z) if mode == "fade" else np.sign(gap_z)
    net = sign * r - cost_bps
    net[~(np.abs(gap_z) > 0.5)] = np.nan
    return net


def expiry_day_profile(panel, ctx) -> pd.DataFrame:
    cx = ctx.reindex(panel.dates)
    on = (panel.dates >= "2019-02-11")
    rng = 1e4 * (panel.high.max(1) - panel.low.min(1)) / panel.open[:, 0]
    late = 1e4 * np.log(panel.close[:, 374] / panel.close[:, price_col("13:15")])
    out = []
    for label, m in (("weekly expiry", on & cx["weekly_expiry"].to_numpy().astype(bool)),
                     ("non-expiry", on & ~cx["weekly_expiry"].to_numpy().astype(bool))):
        out.append({"day_type": label, "n_days": int(m.sum()),
                    "median_range_bps": float(np.median(rng[m])),
                    "mean_13:15->close_bps": float(late[m].mean()),
                    "sd_13:15->close_bps": float(late[m].std())})
    return pd.DataFrame(out)


def run_all(panel: IntradayPanel, ctx: pd.DataFrame, cost_bps: float, periods: dict) -> pd.DataFrame:
    dates = panel.dates
    strategies = {
        "H1 intraday momentum (prev close->09:45 sign, trade 15:00->15:30)": intraday_momentum(panel, ctx, cost_bps),
        "H2a ORB-15 with stop": opening_range_breakout(panel, 15, cost_bps, True),
        "H2b ORB-30 with stop": opening_range_breakout(panel, 30, cost_bps, True),
        "H2c ORB-15 no stop": opening_range_breakout(panel, 15, cost_bps, False),
        "H3a gap fade |gap|>0.5 sigma, 09:20->15:15": gap_trade(panel, ctx, cost_bps, "fade"),
        "H3b gap-and-go |gap|>0.5 sigma, 09:20->15:15": gap_trade(panel, ctx, cost_bps, "go"),
    }
    rows = []
    for name, net in strategies.items():
        rows += _split(name, net, dates, periods)
    out = pd.DataFrame(rows)
    out.insert(3, "gross_bps_per_trade", out["net_bps_per_trade"] + cost_bps)
    return out, strategies
