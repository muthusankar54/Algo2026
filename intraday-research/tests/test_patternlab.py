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


def test_cost_model_matches_hand_calculation():
    # 1 lot Nifty futures at 22,500 (lot 65, notional Rs 14,62,500), rates from 1 Apr 2026,
    # worked by hand: STT 0.05% sell 731.25; NSE txn 0.00183% x2 53.53; SEBI Rs10/cr x2 2.93;
    # stamp 0.002% buy 29.25; brokerage 2 x 20; GST 18% on (40 + 53.53 + 2.93) 17.36.
    expected = 731.25 + 53.53 + 2.93 + 29.25 + 40 + 17.36  # = 874.32, matches Zerodha's calculator
    m = FuturesCostModel(slippage_points_per_side=0)
    rupees = m.round_trip_bps(22500, 65) * 22500 * 65 / 1e4
    assert rupees == pytest.approx(expected, abs=0.05)


def test_predicates_ignore_future_days():
    panel, daily, vix = _synthetic()
    ctx = daily_context(daily, vix)
    k = minute_index("10:15")
    before = build_predicates(panel, ctx, k).mask[:, :200]
    rng = np.random.default_rng(2)
    noisy = IntradayPanel(panel.dates, panel.open.copy(), panel.high.copy(), panel.low.copy(), panel.close.copy())
    for m in (noisy.open, noisy.high, noisy.low, noisy.close):
        m[200:] *= np.exp(rng.normal(0, 0.02, m[200:].shape))
    daily2 = daily.copy()
    daily2.iloc[200:] *= 1.07
    after = build_predicates(noisy, daily_context(daily2, vix), k).mask[:, :200]
    assert np.array_equal(before, after)


def _noise_combos(n_days=300, n_pred=8, seed=4):
    rng = np.random.default_rng(seed)
    mask = (rng.random((n_pred, n_days)) < 0.5).astype(float)
    I, J = np.triu_indices(n_pred)
    return [ComboData("09:45", "15:15", [f"p{i}=x" for i in range(n_pred)], mask, rng.normal(0, 50, n_days), I, J)]


def test_spa_null_never_exceeds_reality_check_null():
    from patternlab.discovery import reality_check, spa_check
    combos = _noise_combos()
    rc = reality_check(combos, min_trades=30, n_boot=60, seed=1)
    spa = spa_check(combos, cost_bps=5.0, min_trades=30, n_boot=60, seed=1)
    assert np.all(spa <= rc + 1e-9)


def test_fwer_pvalues_are_valid_on_noise():
    from patternlab.discovery import fwer_pvalues, reality_check, score
    combos = _noise_combos()
    table = score(combos, cost_bps=0.0, min_trades=30)
    p = fwer_pvalues(table.t.to_numpy(), reality_check(combos, min_trades=30, n_boot=100, seed=3))
    assert ((p > 0) & (p <= 1)).all()
    assert p.min() > 0.05  # nothing is significant in pure noise


def test_block_stats_match_brute_force():
    from patternlab.discovery import block_stats, score, trades
    combos = _noise_combos()
    table = score(combos, cost_bps=4.0, min_trades=30)
    s, q, n = block_stats(combos, table, cost_bps=4.0, n_blocks=5)
    row = table.iloc[7]
    x = trades(combos, row, 4.0)
    assert s[:, 7].sum() == pytest.approx(x.sum())
    assert q[:, 7].sum() == pytest.approx((x ** 2).sum())
    assert n[:, 7].sum() == len(x)


def test_opening_range_breakout_long_and_stop():
    from patternlab.hypotheses import opening_range_breakout
    dates = pd.bdate_range("2020-01-01", periods=2)
    base = np.full((2, 375), 100.0)
    up = base.copy()
    up[0, 30:] = np.linspace(100.5, 103, 345)  # breaks above the 100 range and trends up
    up[1, 30:] = 100.5  # breaks out...
    up[1, 40:] = 99.0  # ...then falls through the stop at the range low (100)
    hi, lo = up + 0.01, up - 0.01
    hi[:, :30], lo[:, :30] = 100.0, 100.0
    panel = IntradayPanel(dates, up.copy(), hi, lo, up)
    net = opening_range_breakout(panel, 30, cost_bps=0.0, use_stop=True)
    assert net[0] > 0
    assert net[1] == pytest.approx(1e4 * np.log(100.0 / 100.5))


def test_overnight_variance_share_is_additive():
    from patternlab.regime import decompose, yearly_profile
    _, daily, vix = _synthetic()
    yp = yearly_profile(decompose(daily), vix, cost_bps=5.0)
    assert ((yp.overnight_var_share >= 0) & (yp.overnight_var_share <= 1)).all()
