"""Statistics for judging data-mined patterns.

* Holm and Benjamini-Hochberg corrections on one-sided p-values.
* Stationary bootstrap (Politis & Romano 1994) day weights for White's Reality Check /
  studentised max-t family-wise p-values (Romano & Wolf 2005 single step).
* Deflated Sharpe Ratio (Bailey & Lopez de Prado 2014).
* Probability of Backtest Overfitting via CSCV (Bailey, Borwein, Lopez de Prado & Zhu 2017).
"""
from __future__ import annotations

from itertools import combinations

import numpy as np
from scipy import stats as sps

EULER_GAMMA = 0.5772156649015329


def holm(p: np.ndarray) -> np.ndarray:
    p = np.asarray(p, float)
    n = len(p)
    order = np.argsort(p)
    adj = np.empty(n)
    running = 0.0
    for rank, idx in enumerate(order):
        running = max(running, min(1.0, (n - rank) * p[idx]))
        adj[idx] = running
    return adj


def benjamini_hochberg(p: np.ndarray) -> np.ndarray:
    p = np.asarray(p, float)
    n = len(p)
    order = np.argsort(p)[::-1]
    adj = np.empty(n)
    running = 1.0
    for i, idx in enumerate(order):
        rank = n - i
        running = min(running, p[idx] * n / rank)
        adj[idx] = running
    return adj


def stationary_bootstrap_weights(n: int, n_boot: int, mean_block: float, rng: np.random.Generator) -> np.ndarray:
    """(n_boot, n) array: how many times each day appears in each bootstrap resample."""
    w = np.zeros((n_boot, n))
    p = 1.0 / mean_block
    for b in range(n_boot):
        idx = np.empty(n, dtype=int)
        idx[0] = rng.integers(n)
        new_block = rng.random(n) < p
        starts = rng.integers(n, size=n)
        for t in range(1, n):
            idx[t] = starts[t] if new_block[t] else (idx[t - 1] + 1) % n
        w[b] = np.bincount(idx, minlength=n)
    return w


def expected_max_sharpe(n_trials: int, var_sr: float) -> float:
    """E[max SR] of n_trials unskilled strategies (False Strategy Theorem)."""
    if n_trials < 2:
        return 0.0
    z = sps.norm.ppf
    return np.sqrt(var_sr) * ((1 - EULER_GAMMA) * z(1 - 1 / n_trials) + EULER_GAMMA * z(1 - 1 / (n_trials * np.e)))


def deflated_sharpe(returns: np.ndarray, n_trials: int, var_sr_trials: float) -> dict:
    """DSR for per-trade returns of the selected strategy, given all trials tried."""
    r = np.asarray(returns, float)
    t = len(r)
    sr = r.mean() / r.std(ddof=1)
    skew = sps.skew(r)
    kurt = sps.kurtosis(r, fisher=False)
    sr0 = expected_max_sharpe(n_trials, var_sr_trials)
    denom = np.sqrt(max(1e-12, 1 - skew * sr + (kurt - 1) / 4 * sr ** 2))
    dsr = sps.norm.cdf((sr - sr0) * np.sqrt(t - 1) / denom)
    psr0 = sps.norm.cdf(sr * np.sqrt(t - 1) / denom)
    return {"sr_per_trade": sr, "sr0_expected_max_noise": sr0, "n_trials": n_trials,
            "n_obs": t, "skew": skew, "kurtosis": kurt, "psr_vs_zero": psr0, "dsr": dsr}


def min_backtest_length_years(n_trials: int, target_annual_sr: float = 1.0) -> float:
    """Bailey et al. (2014) MinBTL: years of data needed so that the best of n_trials
    noise strategies is not expected to show an annual Sharpe of target_annual_sr."""
    e = (1 - EULER_GAMMA) * sps.norm.ppf(1 - 1 / n_trials) + EULER_GAMMA * sps.norm.ppf(1 - 1 / (n_trials * np.e))
    return float((e / target_annual_sr) ** 2)


def pbo_cscv(block_sum: np.ndarray, block_sumsq: np.ndarray, block_count: np.ndarray,
             min_count: int = 10) -> dict:
    """Probability of Backtest Overfitting.

    Inputs are (n_blocks, n_candidates) sums of per-trade net returns, squared returns and
    trade counts per time block. For every split of the blocks into two halves the
    candidate with the best in-sample Sharpe is located in the out-of-sample ranking.
    """
    n_blocks = block_sum.shape[0]
    logits, is_best_oos_sr = [], []
    for train in combinations(range(n_blocks), n_blocks // 2):
        train = list(train)
        test = [b for b in range(n_blocks) if b not in train]
        sr_tr = _sharpe(block_sum[train].sum(0), block_sumsq[train].sum(0), block_count[train].sum(0), min_count)
        sr_te = _sharpe(block_sum[test].sum(0), block_sumsq[test].sum(0), block_count[test].sum(0), min_count)
        valid = ~np.isnan(sr_tr) & ~np.isnan(sr_te)
        if valid.sum() < 10:
            continue
        tr, te = sr_tr[valid], sr_te[valid]
        best = np.argmax(tr)
        rank = (te < te[best]).sum() + 0.5 * ((te == te[best]).sum() - 1) + 1
        omega = rank / (len(te) + 1)
        logits.append(np.log(omega / (1 - omega)))
        is_best_oos_sr.append(te[best])
    logits = np.array(logits)
    return {"pbo": float((logits <= 0).mean()), "n_splits": len(logits),
            "median_logit": float(np.median(logits)),
            "best_is_candidate_median_oos_sr": float(np.median(is_best_oos_sr))}


def _sharpe(s, q, n, min_count):
    with np.errstate(invalid="ignore", divide="ignore"):
        mean = s / n
        var = (q - n * mean ** 2) / (n - 1)
        sr = mean / np.sqrt(var)
    sr[(n < min_count) | ~np.isfinite(sr)] = np.nan
    return sr
