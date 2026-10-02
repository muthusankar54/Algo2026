"""Loading and cleaning of the Nifty minute and daily datasets.

Intraday data is reshaped into per-day matrices of shape (n_days, 375): column 0 is
the 09:15 bar and column 374 the 15:29 bar. Working on fixed-shape matrices keeps every
feature and backtest vectorised and makes look-ahead easy to audit: anything decided at
minute k may only read columns < k.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path(os.environ.get("PATTERNLAB_DATA", Path(__file__).resolve().parents[1] / "data"))

SESSION_START = "09:15"
SESSION_MINUTES = 375  # 09:15 .. 15:29 inclusive
MIN_BARS_PER_DAY = 370  # drops Muhurat sessions, half days and exchange-glitch days


def minute_index(hhmm: str) -> int:
    """Column index of the 1-minute bar that *starts* at hh:mm (09:15 -> 0)."""
    h, m = map(int, hhmm.split(":"))
    idx = (h * 60 + m) - (9 * 60 + 15)
    if not 0 <= idx < SESSION_MINUTES:
        raise ValueError(f"{hhmm} is outside the 09:15-15:29 session")
    return idx


@dataclass
class IntradayPanel:
    dates: pd.DatetimeIndex  # one entry per trading day
    open: np.ndarray  # (n_days, 375)
    high: np.ndarray
    low: np.ndarray
    close: np.ndarray

    def __len__(self) -> int:
        return len(self.dates)

    def subset(self, mask: np.ndarray) -> "IntradayPanel":
        return IntradayPanel(self.dates[mask], self.open[mask], self.high[mask],
                             self.low[mask], self.close[mask])


def load_minute_panel(path: Path | str | None = None) -> IntradayPanel:
    path = Path(path) if path else DATA_DIR / "nifty50_1min.csv"
    raw = pd.read_csv(path)
    ts = pd.to_datetime(raw["Date"] + " " + raw["Time"], format="%d-%m-%Y %H:%M:%S").dt.floor("min")
    df = raw[["Open", "High", "Low", "Close"]].astype(float)
    df.index = ts
    df = df[~df.index.duplicated(keep="first")].sort_index()

    tod = df.index.hour * 60 + df.index.minute - (9 * 60 + 15)
    df = df[(tod >= 0) & (tod < SESSION_MINUTES)]
    tod = df.index.hour * 60 + df.index.minute - (9 * 60 + 15)

    day = df.index.normalize()
    counts = pd.Series(1, index=day).groupby(level=0).size()
    first = pd.Series(tod, index=day).groupby(level=0).min()
    good = counts[(counts >= MIN_BARS_PER_DAY) & (first == 0)].index
    keep = day.isin(good)
    df, tod, day = df[keep], np.asarray(tod)[keep], day[keep]

    dates = pd.DatetimeIndex(good.sort_values())
    row = dates.get_indexer(day)
    mats = {}
    for col in ("Open", "High", "Low", "Close"):
        m = np.full((len(dates), SESSION_MINUTES), np.nan)
        m[row, tod] = df[col].to_numpy()
        mats[col] = m
    # Fill the rare missing minute with the previous close (flat bar).
    close = pd.DataFrame(mats["Close"]).ffill(axis=1).to_numpy()
    for col in ("Open", "High", "Low"):
        mats[col] = np.where(np.isnan(mats[col]), close, mats[col])
    return IntradayPanel(dates, mats["Open"], mats["High"], mats["Low"], close)


def load_minute_sessions(path: Path | str | None = None) -> pd.DataFrame:
    """Daily OHLC of *every* session in the minute file, including Muhurat and special
    sessions that load_minute_panel drops. Used to fill sessions missing from the daily file,
    so that "previous close" is always the true previous session."""
    path = Path(path) if path else DATA_DIR / "nifty50_1min.csv"
    raw = pd.read_csv(path)
    day = pd.to_datetime(raw["Date"], format="%d-%m-%Y")
    ts = pd.to_datetime(raw["Date"] + " " + raw["Time"], format="%d-%m-%Y %H:%M:%S")
    df = raw[["Open", "High", "Low", "Close"]].astype(float).assign(day=day, ts=ts).sort_values("ts")
    g = df.groupby("day")
    out = pd.DataFrame({"Open": g["Open"].first(), "High": g["High"].max(),
                        "Low": g["Low"].min(), "Close": g["Close"].last()})
    out.index.name = "Date"
    return out


def patch_daily(daily: pd.DataFrame, sessions: pd.DataFrame) -> pd.DataFrame:
    """Official daily values where present; minute-derived values for missing sessions."""
    sessions = sessions[(sessions.index >= daily.index[0]) & (sessions.index <= daily.index[-1])]
    return daily.combine_first(sessions)[["Open", "High", "Low", "Close"]].sort_index()


def load_daily(name: str) -> pd.DataFrame:
    """Daily OHLC from eod2_data, e.g. load_daily('nifty_50') or load_daily('india_vix')."""
    df = pd.read_csv(DATA_DIR / f"{name}_daily.csv", parse_dates=["Date"])
    df = df.set_index("Date").sort_index()
    df = df[~df.index.duplicated(keep="last")]
    return df[["Open", "High", "Low", "Close"]].astype(float).dropna()
