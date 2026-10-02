"""Eval gates: the pass/fail checklist every candidate strategy must clear before real money.

Treated like an ML eval suite: a fixed hold-out set that discovery never sees, an
adversarial "noise" set (placebo), stress sets (higher costs, bad years), and pre-declared
thresholds taken from the literature (Harvey-Liu-Zhu 2016 t>3; Bailey & Lopez de Prado
DSR>0.95 and PBO<0.2).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Gate:
    key: str
    description: str
    threshold: str


GATES = [
    Gate("net_positive", "Net-of-cost mean per trade > 0 in discovery period", "> 0 bps"),
    Gate("t_stat", "t-statistic of net returns (Harvey, Liu & Zhu hurdle)", ">= 3.0"),
    Gate("fwer", "Family-wise p-value over all patterns tried (Hansen SPA; Bonferroni for pre-registered)", "< 0.05"),
    Gate("dsr", "Deflated Sharpe Ratio given number of trials", ">= 0.95"),
    Gate("pbo", "Probability of Backtest Overfitting of the selection process (CSCV; authors suggest 0.05)", "<= 0.20"),
    Gate("oos_positive", "Hold-out (2021-2024Q1) net mean per trade", "> 0 bps"),
    Gate("oos_t", "Hold-out t-statistic", ">= 1.5"),
    Gate("decay", "Hold-out / in-sample net edge", ">= 0.5"),
    Gate("stress_cost", "Hold-out net mean at stress cost (3 pts slippage per side)", "> 0 bps"),
    Gate("yearly", "Share of calendar years with positive net P&L (all data)", ">= 70%"),
    Gate("sample", "Trades in discovery period", ">= 100"),
]


def scorecard(name: str, m: dict) -> pd.DataFrame:
    """m holds the measured values; a missing value (None) is reported as not applicable."""
    checks = {
        "net_positive": lambda v: v > 0,
        "t_stat": lambda v: v >= 3.0,
        "fwer": lambda v: v < 0.05,
        "dsr": lambda v: v >= 0.95,
        "pbo": lambda v: v <= 0.20,
        "oos_positive": lambda v: v > 0,
        "oos_t": lambda v: v >= 1.5,
        "decay": lambda v: v >= 0.5,
        "stress_cost": lambda v: v > 0,
        "yearly": lambda v: v >= 0.70,
        "sample": lambda v: v >= 100,
    }
    rows = []
    for g in GATES:
        v = m.get(g.key)
        ok = None if v is None or (isinstance(v, float) and np.isnan(v)) else bool(checks[g.key](v))
        rows.append({"candidate": name, "gate": g.key, "description": g.description,
                     "threshold": g.threshold, "value": v,
                     "result": "n/a" if ok is None else ("PASS" if ok else "FAIL")})
    return pd.DataFrame(rows)


def yearly_hit_rate(net: np.ndarray, dates: pd.DatetimeIndex) -> float:
    s = pd.Series(net, index=dates).dropna()
    by_year = s.groupby(s.index.year).sum()
    return float((by_year > 0).mean())
