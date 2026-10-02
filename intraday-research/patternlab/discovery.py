"""Exhaustive pattern discovery with honest bookkeeping of how many things were tried.

For each (entry time, exit time) the per-day outcome r is the log return in bps from the
entry price (close of the bar before the entry minute) to the exit price. With M the
(predicates x days) boolean matrix, every 1- and 2-predicate conjunction is scored at once:

    S = (M * r) @ M.T      sum of outcomes on days where both predicates hold
    Q = (M * r^2) @ M.T    sum of squares
    C = M @ M.T            number of such days

so all ~12k patterns x 2 directions are evaluated per run, and the same algebra with bootstrap
day weights gives White's Reality Check without materialising 24k return series.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats as sps

from .data import IntradayPanel, minute_index
from .features import build_predicates
from .stats import benjamini_hochberg, holm, stationary_bootstrap_weights

ENTRY_EXIT = [("09:30", "10:30"), ("09:30", "15:15"),
              ("09:45", "10:45"), ("09:45", "15:15"),
              ("10:15", "11:15"), ("10:15", "15:15"),
              ("11:15", "12:15"), ("11:15", "15:15"),
              ("13:15", "14:15"), ("13:15", "15:15"),
              ("15:00", "15:30")]


def price_col(hhmm: str) -> int:
    """Column whose close is the traded price at hh:mm (15:30 = session close)."""
    return 374 if hhmm == "15:30" else minute_index(hhmm) - 1


def outcome_bps(panel: IntradayPanel, entry: str, exit_: str, entry_delay: int = 0) -> np.ndarray:
    """entry_delay > 0 fills that many minutes after the signal (latency sensitivity)."""
    return 1e4 * np.log(panel.close[:, price_col(exit_)] / panel.close[:, price_col(entry) + entry_delay])


@dataclass
class ComboData:
    entry: str
    exit: str
    names: list[str]
    mask: np.ndarray  # (P, D) float 0/1 on the selected days
    r: np.ndarray  # (D,) gross outcome in bps
    I: np.ndarray  # predicate pair indices (i <= j, different families unless i == j)
    J: np.ndarray


def prepare(panel: IntradayPanel, ctx: pd.DataFrame, day_mask: np.ndarray,
            combos=ENTRY_EXIT, entry_delay: int = 0) -> list[ComboData]:
    out = []
    for entry, exit_ in combos:
        preds = build_predicates(panel, ctx, minute_index(entry))
        fam = preds.family_index()
        P = len(preds.names)
        I, J = np.triu_indices(P)
        keep = (I == J) | (fam[I] != fam[J])
        r = outcome_bps(panel, entry, exit_, entry_delay)[day_mask]
        out.append(ComboData(entry, exit_, preds.names, preds.mask[:, day_mask].astype(float), r,
                             I[keep], J[keep]))
    return out


def _pair_sums(cd: ComboData, r: np.ndarray, w: np.ndarray | None = None):
    M = cd.mask if w is None else cd.mask * w
    S = (M * r) @ cd.mask.T
    Q = (M * r * r) @ cd.mask.T
    C = M @ cd.mask.T
    return S[cd.I, cd.J], Q[cd.I, cd.J], C[cd.I, cd.J]


def score(combos: list[ComboData], cost_bps: float, min_trades: int, outcomes=None) -> pd.DataFrame:
    """One row per (pattern, direction) with net-of-cost per-trade statistics.

    `outcomes` optionally replaces each combo's r (used by the placebo test)."""
    rows = []
    for ci, cd in enumerate(combos):
        r = cd.r if outcomes is None else outcomes[ci]
        S, Q, C = _pair_sums(cd, r)
        ok = C >= min_trades
        S, Q, C, I, J = S[ok], Q[ok], C[ok], cd.I[ok], cd.J[ok]
        mean = S / C
        sd = np.sqrt(np.maximum((Q - C * mean ** 2) / (C - 1), 1e-12))
        se = sd / np.sqrt(C)
        win_long = (cd.mask * (r > cost_bps)) @ cd.mask.T
        win_short = (cd.mask * (-r > cost_bps)) @ cd.mask.T
        for direction, sign, wins in (("long", 1, win_long), ("short", -1, win_short)):
            net = sign * mean - cost_bps
            rows.append(pd.DataFrame({
                "combo": ci, "entry": cd.entry, "exit": cd.exit, "i": I, "j": J,
                "direction": direction, "n": C.astype(int), "gross_bps": sign * mean,
                "net_bps": net, "sd_bps": sd, "t": net / se,
                "win_rate": wins[I, J] / C,
            }))
    df = pd.concat(rows, ignore_index=True)
    df["p"] = sps.norm.sf(df["t"])
    df["p_holm"] = holm(df["p"].to_numpy())
    df["p_bh"] = benjamini_hochberg(df["p"].to_numpy())
    return df


def pattern_name(combos: list[ComboData], row) -> str:
    cd = combos[int(row.combo)]
    a, b = cd.names[int(row.i)], cd.names[int(row.j)]
    cond = a if a == b else f"{a} & {b}"
    return f"{row.direction.upper()} {cd.entry}->{cd.exit} if {cond}"


def reality_check(combos: list[ComboData], min_trades: int, n_boot: int = 500,
                  mean_block: float = 5.0, seed: int = 7) -> np.ndarray:
    """Studentised max-t bootstrap over *all* candidates (White 2000; Romano-Wolf single step).

    Returns the bootstrap distribution of max_k t*_k, where t*_k is candidate k's
    recentred t-statistic. A candidate's family-wise p-value is P(max t* >= t_k)."""
    rng = np.random.default_rng(seed)
    D = len(combos[0].r)
    W = stationary_bootstrap_weights(D, n_boot, mean_block, rng)
    max_t = np.full(n_boot, -np.inf)
    for ci, cd in enumerate(combos):
        S0, Q0, C0 = _pair_sums(cd, cd.r)
        ok = C0 >= min_trades
        S0, Q0, C0 = S0[ok], Q0[ok], C0[ok]
        mean0 = S0 / C0
        # Studentise with the full-sample standard error, as in Hansen's (2005) SPA test;
        # bootstrap standard errors explode for resamples that catch only a few trades.
        se0 = np.sqrt(np.maximum((Q0 - C0 * mean0 ** 2) / (C0 - 1), 1e-12) / C0)
        for b in range(n_boot):
            S, _, C = _pair_sums(cd, cd.r, W[b])
            S, C = S[ok], C[ok]
            with np.errstate(invalid="ignore", divide="ignore"):
                t = np.abs(S / C - mean0) / se0  # covers long and short at once
            t = t[np.isfinite(t) & (C >= min_trades // 2)]
            if len(t):
                max_t[b] = max(max_t[b], t.max())
    return max_t


def fwer_pvalues(t_obs: np.ndarray, max_t_boot: np.ndarray) -> np.ndarray:
    srt = np.sort(max_t_boot)
    exceed = len(srt) - np.searchsorted(srt, t_obs, side="left")
    return (1 + exceed) / (1 + len(srt))


def block_stats(combos: list[ComboData], table: pd.DataFrame, cost_bps: float, n_blocks: int = 10):
    """Per-time-block net sums for every candidate row, for CSCV/PBO."""
    D = len(combos[0].r)
    edges = np.linspace(0, D, n_blocks + 1).astype(int)
    out_s = np.zeros((n_blocks, len(table)))
    out_q = np.zeros_like(out_s)
    out_n = np.zeros_like(out_s)
    for ci, cd in enumerate(combos):
        rows = np.flatnonzero(table["combo"].to_numpy() == ci)
        if not len(rows):
            continue
        sub = table.iloc[rows]
        pair_pos = {(i, j): k for k, (i, j) in enumerate(zip(cd.I, cd.J))}
        idx = np.array([pair_pos[(i, j)] for i, j in zip(sub["i"], sub["j"])])
        sign = np.where(sub["direction"].to_numpy() == "long", 1.0, -1.0)
        for b in range(n_blocks):
            w = np.zeros(D)
            w[edges[b]:edges[b + 1]] = 1
            S, Q, C = _pair_sums(cd, cd.r, w)
            S, Q, C = S[idx], Q[idx], C[idx]
            out_s[b, rows] = sign * S - cost_bps * C
            out_q[b, rows] = Q - 2 * cost_bps * sign * S + cost_bps ** 2 * C
            out_n[b, rows] = C
    return out_s, out_q, out_n


def trades(combos: list[ComboData], row, cost_bps: float, panel_days_mask=None) -> np.ndarray:
    """Per-trade net returns (bps) of one candidate on the days its combo was prepared for."""
    cd = combos[int(row.combo)]
    m = (cd.mask[int(row.i)] * cd.mask[int(row.j)]).astype(bool)
    sign = 1.0 if row.direction == "long" else -1.0
    return sign * cd.r[m] - cost_bps


def evaluate_on(combos_other: list[ComboData], table: pd.DataFrame, cost_bps: float) -> pd.DataFrame:
    """Score the given candidate rows on another period (e.g. the untouched hold-out)."""
    out = []
    for row in table.itertuples():
        x = trades(combos_other, row, cost_bps)
        n = len(x)
        mean = x.mean() if n else np.nan
        sd = x.std(ddof=1) if n > 1 else np.nan
        out.append({"oos_n": n, "oos_net_bps": mean,
                    "oos_t": mean / (sd / np.sqrt(n)) if n > 1 and sd > 0 else np.nan,
                    "oos_win_rate": (x > 0).mean() if n else np.nan})
    return pd.DataFrame(out, index=table.index)


def spa_check(combos: list[ComboData], cost_bps: float, min_trades: int, n_boot: int = 500,
              mean_block: float = 5.0, seed: int = 7) -> np.ndarray:
    """Hansen's (2005) consistent SPA test: like the Reality Check, but candidates whose net
    t-statistic is clearly negative (t < -sqrt(2 ln ln n)) are not recentred to zero, so the
    thousands of patterns that costs make hopeless no longer inflate the null. Returns the
    bootstrap distribution of the max studentised statistic (same day weights as reality_check)."""
    rng = np.random.default_rng(seed)
    D = len(combos[0].r)
    W = stationary_bootstrap_weights(D, n_boot, mean_block, rng)
    thresh = np.sqrt(2 * np.log(np.log(D)))
    max_t = np.full(n_boot, -np.inf)
    for cd in combos:
        S0, Q0, C0 = _pair_sums(cd, cd.r)
        ok = C0 >= min_trades
        S0, Q0, C0 = S0[ok], Q0[ok], C0[ok]
        mean0 = S0 / C0
        se0 = np.sqrt(np.maximum((Q0 - C0 * mean0 ** 2) / (C0 - 1), 1e-12) / C0)
        t_long, t_short = (mean0 - cost_bps) / se0, (-mean0 - cost_bps) / se0
        keep_long = np.where(t_long < -thresh, t_long, 0.0)  # Hansen's g(.) for hopeless candidates
        keep_short = np.where(t_short < -thresh, t_short, 0.0)
        for b in range(n_boot):
            S, _, C = _pair_sums(cd, cd.r, W[b])
            S, C = S[ok], C[ok]
            with np.errstate(invalid="ignore", divide="ignore"):
                z = (S / C - mean0) / se0
            valid = np.isfinite(z) & (C >= min_trades // 2)
            if valid.any():
                stat = np.maximum(z + keep_long, -z + keep_short)[valid]
                max_t[b] = max(max_t[b], stat.max())
    return max_t
