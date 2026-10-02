"""Point-in-time predicates ("pattern atoms") for each trading day and decision minute.

Every predicate evaluated for decision minute k may only use:
  * daily data up to and including the previous session, and
  * intraday bars with column index < k of the current session.
tests/test_no_lookahead.py enforces this by scrambling the future and checking that no
predicate changes.

A pattern is a conjunction of one or two predicates from different families, plus a
direction (long/short) and an entry/exit time.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .data import IntradayPanel

WEEKLY_EXPIRY_START = pd.Timestamp("2019-02-11")  # first Nifty weekly options series


def expiry_flags(trading_days: pd.DatetimeIndex) -> pd.DataFrame:
    """Weekly (Thursday) and monthly (last Thursday) Nifty expiry days for 2015-2024 data.

    When Thursday is a holiday the contract expires on the previous trading day. Expiry
    moved to Tuesday in Sept 2025, which is after the end of the intraday sample.
    """
    days = pd.Series(trading_days, index=trading_days)
    iso = trading_days.isocalendar()
    week_key = iso["year"].astype(str) + "-" + iso["week"].astype(str)
    thursday = trading_days - pd.to_timedelta(trading_days.dayofweek, unit="D") + pd.Timedelta(days=3)
    on_or_before_thu = trading_days <= thursday
    weekly = (days[on_or_before_thu].groupby(week_key[on_or_before_thu].to_numpy()).transform("max")
              .reindex(trading_days))
    is_weekly = (weekly.index == weekly.to_numpy()) & (trading_days >= WEEKLY_EXPIRY_START)

    month_key = trading_days.to_period("M")
    month_end = trading_days + pd.offsets.MonthEnd(0)
    last_thu = month_end - pd.to_timedelta((month_end.dayofweek - 3) % 7, unit="D")
    ok = trading_days <= last_thu
    monthly = days[ok].groupby(month_key[ok]).transform("max").reindex(trading_days)
    is_monthly = monthly.index == monthly.to_numpy()
    return pd.DataFrame({"weekly_expiry": is_weekly, "monthly_expiry": is_monthly}, index=trading_days)


def daily_context(daily: pd.DataFrame, vix: pd.DataFrame) -> pd.DataFrame:
    """Per-day context known before the open of day t (all inputs shifted by one day)."""
    c, h, l = daily["Close"], daily["High"], daily["Low"]
    ret = np.log(c).diff()
    rng = (h - l) / c
    ctx = pd.DataFrame(index=daily.index)
    ctx["prev_close"] = c.shift(1)
    ctx["sigma20"] = ret.rolling(20).std().shift(1)
    ctx["prev_ret_z"] = (ret / ret.rolling(20).std()).shift(1)
    ctx["prev_clv"] = ((c - l) / (h - l).replace(0, np.nan)).shift(1)
    ctx["prev_nr7"] = (rng <= rng.rolling(7).min()).shift(1).astype(float)
    ctx["prev_inside"] = ((h < h.shift(1)) & (l > l.shift(1))).shift(1).astype(float)
    ctx["above_sma20"] = (c > c.rolling(20).mean()).shift(1).astype(float)
    ctx["ret5"] = (c / c.shift(5) - 1).shift(1)
    v = vix["Close"].reindex(daily.index).ffill()
    ctx["vix_prev"] = v.shift(1)
    ctx["vix_pct"] = v.rolling(250, min_periods=200).rank(pct=True).shift(1)
    flags = expiry_flags(daily.index)
    ctx = ctx.join(flags)
    ctx["dow"] = daily.index.dayofweek
    return ctx


@dataclass
class PredicateSet:
    names: list[str]  # "family=level"
    families: list[str]
    mask: np.ndarray  # (n_predicates, n_days) bool

    def family_index(self) -> np.ndarray:
        fam = {f: i for i, f in enumerate(dict.fromkeys(self.families))}
        return np.array([fam[f] for f in self.families])


def _bucket(x: np.ndarray, edges: list[float], labels: list[str]) -> dict[str, np.ndarray]:
    out = {}
    lo = -np.inf
    for edge, label in zip(edges + [np.inf], labels):
        out[label] = (x >= lo) & (x < edge)
        lo = edge
    return out


def build_predicates(panel: IntradayPanel, ctx: pd.DataFrame, k: int) -> PredicateSet:
    """All pattern atoms for decision at the start of minute k (using bars < k)."""
    cx = ctx.reindex(panel.dates)
    o, h, l, c = panel.open, panel.high, panel.low, panel.close
    sig = cx["sigma20"].to_numpy()
    prev_close = cx["prev_close"].to_numpy()
    open0 = o[:, 0]
    price = c[:, k - 1]
    fams: dict[str, dict[str, np.ndarray]] = {}

    # ---- day-level context (known pre-open) ----
    gap_z = (open0 / prev_close - 1) / sig
    fams["gap"] = _bucket(gap_z, [-0.5, -0.15, 0.15, 0.5], ["big_down", "down", "flat", "up", "big_up"])
    fams["prev_day"] = _bucket(cx["prev_ret_z"].to_numpy(), [-1, 0, 1], ["big_down", "down", "up", "big_up"])
    fams["prev_clv"] = _bucket(cx["prev_clv"].to_numpy(), [0.25, 0.75], ["near_low", "mid", "near_high"])
    fams["prev_nr7"] = {"yes": cx["prev_nr7"].to_numpy() == 1}
    fams["prev_inside"] = {"yes": cx["prev_inside"].to_numpy() == 1}
    above = cx["above_sma20"].to_numpy()
    fams["trend20"] = {"above": above == 1, "below": above == 0}
    r5 = cx["ret5"].to_numpy()
    fams["ret5"] = {"up": r5 > 0, "down": r5 <= 0}
    fams["vix_regime"] = _bucket(cx["vix_pct"].to_numpy(), [1 / 3, 2 / 3], ["low", "mid", "high"])
    dow = cx["dow"].to_numpy()
    fams["dow"] = {d: dow == i for i, d in enumerate(["mon", "tue", "wed", "thu", "fri"])}
    fams["expiry"] = {"weekly": cx["weekly_expiry"].to_numpy().astype(bool),
                      "monthly": cx["monthly_expiry"].to_numpy().astype(bool)}

    # ---- intraday state at decision time ----
    fams["open_to_now"] = _bucket((price / open0 - 1) / sig, [-0.4, -0.1, 0.1, 0.4],
                                  ["big_down", "down", "flat", "up", "big_up"])
    fams["pclose_to_now"] = _bucket((price / prev_close - 1) / sig, [-0.2, 0.2], ["down", "flat", "up"])
    for n in (15, 30):
        if k >= n:
            orh, orl = h[:, :n].max(1), l[:, :n].min(1)
            fams[f"or{n}"] = {"above": price > orh, "inside": (price <= orh) & (price >= orl),
                              "below": price < orl}
    hi_so_far, lo_so_far = h[:, :k].max(1), l[:, :k].min(1)
    up_gap, dn_gap = open0 > prev_close, open0 < prev_close
    fams["gap_fill"] = {"up_filled": up_gap & (lo_so_far <= prev_close),
                        "up_open": up_gap & (lo_so_far > prev_close),
                        "down_filled": dn_gap & (hi_so_far >= prev_close),
                        "down_open": dn_gap & (hi_so_far < prev_close)}
    if k >= 15:
        body = c[:, 14] - open0
        span = np.maximum(h[:, :15].max(1) - l[:, :15].min(1), 1e-9)
        strong = np.abs(body) / span > 0.6
        fams["first15"] = {"bull_strong": (body > 0) & strong, "bull_weak": (body > 0) & ~strong,
                           "bear_weak": (body <= 0) & ~strong, "bear_strong": (body <= 0) & strong}
    rng_now = pd.Series((hi_so_far - lo_so_far) / open0)
    rel = (rng_now / rng_now.rolling(60, min_periods=40).median().shift(1)).to_numpy()
    fams["range_so_far"] = _bucket(rel, [0.75, 1.33], ["narrow", "normal", "wide"])
    twap = c[:, :k].mean(1)
    fams["vs_twap"] = {"above": price > twap, "below": price <= twap}
    if k >= 31:
        m30 = price / c[:, k - 31] - 1
        fams["last30"] = {"up": m30 > 0, "down": m30 <= 0}

    names, families, masks = [], [], []
    for fam, levels in fams.items():
        for lvl, m in levels.items():
            names.append(f"{fam}={lvl}")
            families.append(fam)
            masks.append(np.nan_to_num(m, nan=0).astype(bool))
    return PredicateSet(names, families, np.vstack(masks))


def eligible_days(panel: IntradayPanel, ctx: pd.DataFrame) -> np.ndarray:
    """Days where every day-level input is defined (enough history for sigma20, VIX rank)."""
    cx = ctx.reindex(panel.dates)
    need = ["prev_close", "sigma20", "prev_ret_z", "prev_clv", "vix_pct", "ret5"]
    return cx[need].notna().all(axis=1).to_numpy()
