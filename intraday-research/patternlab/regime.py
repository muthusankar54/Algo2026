"""Daily-data analyses, 2012-2026: where does index risk actually arrive?

The premise of switching to intraday is "geopolitical risk is too high to hold positions".
That only helps if the risk arrives overnight (as gaps). These functions measure how
Nifty's variance and its largest moves split between the overnight gap and the session.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# Geopolitical / macro shock sessions. "date" is the first Indian session after the news.
# 2019-2025 entries are well documented; 2026 entries come from the Oct 2026 research
# notes and were cross-checked against the eod2 daily open/close.
EVENTS = [
    ("2019-02-26", "Balakot air strike (India-Pakistan)"),
    ("2020-01-03", "US kills Soleimani (strike before the open)"),
    ("2020-01-08", "Iran missile strike on US bases in Iraq"),
    ("2020-06-16", "Galwan clash (India-China; news broke intraday)"),
    ("2022-02-24", "Russia invades Ukraine"),
    ("2023-10-09", "Hamas attack on Israel"),
    ("2024-04-15", "Iran drone/missile attack on Israel"),
    ("2024-10-03", "Iran ballistic missiles on Israel"),
    ("2025-04-07", "US 'Liberation Day' tariff crash"),
    ("2025-05-07", "Operation Sindoor (India-Pakistan)"),
    ("2025-05-12", "India-Pakistan ceasefire"),
    ("2025-06-13", "Israel strikes Iran"),
    ("2025-06-23", "US strikes Iranian nuclear sites"),
    ("2026-03-02", "US/Israel war on Iran begins (28 Feb)"),
    ("2026-03-04", "Iran war escalation, Gulf strikes"),
    ("2026-03-09", "Brent near $120 intraday"),
    ("2026-03-23", "Trump 48-hour Hormuz ultimatum"),
    ("2026-04-08", "US-Iran ceasefire"),
]


def decompose(daily: pd.DataFrame) -> pd.DataFrame:
    d = daily.copy()
    d["overnight"] = np.log(d["Open"] / d["Close"].shift(1))
    d["intraday"] = np.log(d["Close"] / d["Open"])
    d["close_to_close"] = d["overnight"] + d["intraday"]
    d["range"] = (d["High"] - d["Low"]) / d["Open"]
    return d.dropna(subset=["overnight"])


def yearly_profile(d: pd.DataFrame, vix: pd.DataFrame, cost_bps: float) -> pd.DataFrame:
    x = d.join(vix["Close"].rename("vix"))
    g = x.groupby(x.index.year)
    out = pd.DataFrame({
        "days": g.size(),
        "overnight_cum_pct": 100 * g["overnight"].sum(),
        "intraday_cum_pct": 100 * g["intraday"].sum(),
        # additive share: var(o) / (var(o) + var(i)), which stays in [0, 1] when o and i are correlated
        "overnight_var_share": g.apply(lambda s: s["overnight"].var() / (s["overnight"].var() + s["intraday"].var())),
        "median_abs_gap_bps": 1e4 * g["overnight"].apply(lambda s: s.abs().median()),
        "median_range_bps": 1e4 * g["range"].median(),
        "median_abs_open_to_close_bps": 1e4 * g["intraday"].apply(lambda s: s.abs().median()),
        "avg_india_vix": g["vix"].mean(),
    })
    out["cost_as_pct_of_median_range"] = 100 * cost_bps / out["median_range_bps"]
    return out


def tail_attribution(d: pd.DataFrame, top: int = 50) -> dict:
    """For the largest close-to-close moves, how much came from the overnight gap?"""
    big = d.reindex(d["close_to_close"].abs().sort_values(ascending=False).index[:top])
    same_sign = np.sign(big["overnight"]) == np.sign(big["close_to_close"])
    share = (big["overnight"] / big["close_to_close"]).clip(-2, 2)
    return {"n": top, "median_gap_share_of_move": float(share.median()),
            "pct_where_gap_has_same_sign": float(100 * same_sign.mean()),
            "pct_where_intraday_reverses_gap": float(100 * (np.sign(big["intraday"]) != np.sign(big["overnight"])).mean())}


def event_study(d: pd.DataFrame, vix: pd.DataFrame) -> pd.DataFrame:
    rows = []
    med_range = d["range"].rolling(250, min_periods=60).median().shift(1)
    for date, label in EVENTS:
        ts = pd.Timestamp(date)
        if ts not in d.index:
            continue
        r = d.loc[ts]
        rows.append({"date": date, "event": label,
                     "gap_pct": 100 * r["overnight"], "intraday_pct": 100 * r["intraday"],
                     "close_to_close_pct": 100 * r["close_to_close"],
                     "range_vs_1y_median": r["range"] / med_range.loc[ts],
                     "india_vix": vix["Close"].get(ts, np.nan)})
    return pd.DataFrame(rows)


def gap_conditional_open_to_close(d: pd.DataFrame, periods: dict, cost_bps: float) -> pd.DataFrame:
    """Open->close drift after gaps, by era. Uses only daily data, so it can be checked on
    Apr 2024 - Sep 2026, after the end of the minute data. Caveat: the official open is the
    09:15 print, so this includes the untradeable first-minute move (see minute_split)."""
    sig = d["close_to_close"].rolling(20).std().shift(1)
    gz = d["overnight"] / sig
    bucket = pd.cut(gz, [-np.inf, -0.5, -0.15, 0.15, 0.5, np.inf],
                    labels=["big_down", "down", "flat", "up", "big_up"])
    rows = []
    for label, (a, b) in periods.items():
        m = (d.index >= a) & (d.index < b)
        for lvl in bucket.cat.categories:
            x = 1e4 * d.loc[m & (bucket == lvl).to_numpy(), "intraday"]
            if len(x) < 5:
                continue
            fade = -np.sign(0.5 if "up" in lvl else -0.5 if "down" in lvl else 0) * x - cost_bps
            rows.append({"period": label, "gap": lvl, "n": len(x), "mean_open_to_close_bps": x.mean(),
                         "t": x.mean() / (x.std(ddof=1) / np.sqrt(len(x))),
                         "fade_net_bps": fade.mean() if lvl != "flat" else np.nan})
    return pd.DataFrame(rows)


def minute_split(panel, daily: pd.DataFrame) -> pd.DataFrame:
    """Overnight vs intraday by year from minute data, with the session measured from the
    09:15 print (as daily data does) and from the 09:16 price (first tradeable minute)."""
    close = daily["Close"]
    prev = close.shift(1).reindex(panel.dates).to_numpy()
    off = close.reindex(panel.dates).to_numpy()
    print_ = panel.open[:, 0]
    first = panel.close[:, 0]
    df = pd.DataFrame({"overnight_to_print": np.log(print_ / prev), "intraday_from_print": np.log(off / print_),
                       "overnight_to_0916": np.log(first / prev), "intraday_from_0916": np.log(off / first)},
                      index=panel.dates).dropna()
    yearly = 100 * df.groupby(df.index.year).sum()
    yearly.loc["total"] = 100 * df.sum()
    return yearly


def nifty_sensex_correlation(nifty: pd.DataFrame, sensex_etf: pd.DataFrame) -> dict:
    a = np.log(nifty["Close"]).diff()
    b = np.log(sensex_etf["Close"]).diff()
    j = pd.concat([a, b], axis=1, keys=["nifty", "sensex"]).dropna()
    # The Sensex ETF is thinly traded before 2021, which depresses the correlation.
    j = j[(j.index >= "2021-01-01") & (j["sensex"].abs() < 0.15)]
    rho = float(j.corr().iloc[0, 1])
    yearly = j.groupby(j.index.year).apply(lambda x: x.corr().iloc[0, 1])
    return {"rho_daily": rho, "rho_by_year": yearly.round(3).to_dict(),
            "diversification_gain_two_index_same_signal": float(np.sqrt(2 / (1 + rho)))}
