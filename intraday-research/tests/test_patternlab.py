import numpy as np
import pandas as pd
import pytest

from patternlab.costs import FuturesCostModel
from patternlab.data import IntradayPanel, minute_index
from patternlab.discovery import ComboData, _pair_sums
from patternlab.features import build_predicates, daily_context, expiry_flags
from patternlab.stats import benjamini_hochberg, deflated_sharpe, holm, pbo_cscv


def _synthetic(n_days=320, seed=0):
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2019-01-01", periods=n_days)
    steps = rng.normal(0, 0.0005, (n_days, 375))
    opens = 10000 * np.exp(np.cumsum(rng.normal(0, 0.01, n_days)))
    close = opens[:, None] * np.exp(np.cumsum(steps, axis=1))
    open_ = np.concatenate([opens[:, None], close[:, :-1]], axis=1)
    high = np.maximum(open_, close) * (1 + rng.uniform(0, 2e-4, close.shape))
    low = np.minimum(open_, close) * (1 - rng.uniform(0, 2e-4, close.shape))
    panel = IntradayPanel(dates, open_, high, low, close)
    daily = pd.DataFrame({"Open": open_[:, 0], "High": high.max(1), "Low": low.min(1),
                          "Close": close[:, -1]}, index=dates)
    vix = pd.DataFrame({"Close": rng.uniform(10, 30, n_days)}, index=dates)
    return panel, daily, vix


@pytest.mark.parametrize("hhmm", ["09:30", "09:45", "10:15", "13:15", "15:00"])
def test_predicates_ignore_the_future(hhmm):
    panel, daily, vix = _synthetic()
    ctx = daily_context(daily, vix)
    k = minute_index(hhmm)
    before = build_predicates(panel, ctx, k)
    rng = np.random.default_rng(1)
    noise = np.exp(rng.normal(0, 0.01, panel.close[:, k:].shape))
    scrambled = IntradayPanel(panel.dates, panel.open.copy(), panel.high.copy(), panel.low.copy(), panel.close.copy())
    for m in (scrambled.open, scrambled.high, scrambled.low, scrambled.close):
        m[:, k:] *= noise
    after = build_predicates(scrambled, ctx, k)
    assert before.names == after.names
    assert np.array_equal(before.mask, after.mask)


def test_daily_context_uses_only_previous_sessions():
    _, daily, vix = _synthetic()
    ctx = daily_context(daily, vix)
    bumped = daily.copy()
    t = bumped.index[200]
    bumped.loc[t, ["High", "Close"]] *= 1.05
    ctx2 = daily_context(bumped, vix)
    pd.testing.assert_series_equal(ctx.loc[t], ctx2.loc[t])


def test_expiry_moves_to_wednesday_when_thursday_is_a_holiday():
    days = pd.DatetimeIndex(["2019-03-18", "2019-03-19", "2019-03-20", "2019-03-22",  # Holi Thu 21 Mar
                             "2019-03-25", "2019-03-26", "2019-03-27", "2019-03-28", "2019-03-29"])
    f = expiry_flags(days)
    assert f["weekly_expiry"].loc["2019-03-20"]
    assert f["weekly_expiry"].loc["2019-03-28"] and f["monthly_expiry"].loc["2019-03-28"]
    assert f["weekly_expiry"].sum() == 2


def test_pair_sums_match_brute_force():
    rng = np.random.default_rng(3)
    mask = rng.random((6, 200)) < 0.4
    r = rng.normal(0, 30, 200)
    I, J = np.triu_indices(6)
    cd = ComboData("09:45", "15:15", [str(i) for i in range(6)], mask.astype(float), r, I, J)
    S, Q, C = _pair_sums(cd, r)
    for k, (i, j) in enumerate(zip(I, J)):
        m = mask[i] & mask[j]
        assert C[k] == m.sum()
        assert S[k] == pytest.approx(r[m].sum())
        assert Q[k] == pytest.approx((r[m] ** 2).sum())


def test_multiple_testing_corrections():
    p = np.array([0.01, 0.04, 0.03, 0.005])
    np.testing.assert_allclose(holm(p), [0.03, 0.06, 0.06, 0.02])
    np.testing.assert_allclose(benjamini_hochberg(p), [0.02, 0.04, 0.04, 0.02])


def test_deflated_sharpe_penalises_many_trials():
    rng = np.random.default_rng(5)
    x = rng.normal(0.1, 1, 500)
    one = deflated_sharpe(x, n_trials=1, var_sr_trials=0.01)["dsr"]
    many = deflated_sharpe(x, n_trials=10000, var_sr_trials=0.01)["dsr"]
    assert many < one


def test_pbo_is_high_for_pure_noise():
    rng = np.random.default_rng(9)
    s = rng.normal(0, 1, (10, 300))
    out = pbo_cscv(s, np.full_like(s, 100.0), np.full_like(s, 50.0))
    assert 0.3 < out["pbo"] < 0.7


def test_cost_model_matches_broker_calculator():
    # Zerodha charges page (Oct 2026): 1 lot Nifty futures at 22,500 -> Rs 874 excl. slippage.
    m = FuturesCostModel(slippage_points_per_side=0)
    rupees = m.round_trip_bps(22500, 65) * 22500 * 65 / 1e4
    assert rupees == pytest.approx(874, abs=1)
