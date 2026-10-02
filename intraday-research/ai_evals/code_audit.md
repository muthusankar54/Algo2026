# Independent code audit: `patternlab` (intraday-research)

*Auditor: independent AI agent, 2 Oct 2026. Scope: every module in `patternlab/`, `tests/`, the
numbers in `results/summary.json`, and the claims in `ai_evals/dossier.md` / `REPORT.md` that
those numbers support.*

## Bottom line

- **No critical bugs.** I found no look-ahead, no IS/OOS leakage, no off-by-one error in any
  backtest, and no wrong statistics formula. Every core routine matches an independent
  brute-force or reference implementation to floating-point precision.
- **The headline survives:** at today's ~6.9 bps round trip, no mined pattern and no
  pre-registered strategy shows a positive net edge. None of the 18 findings overturns it.
- **One place has a thin margin:** the 30-min opening-range breakout with a stop. Its gross edge
  is real and replicated: 5.2 bps, t = 3.9 over 2015-2024, and it holds under harsher stop-fill
  assumptions. Its net loss at 6.87 bps is **not** statistically significant (net t = -1.3; the
  95% CI of the gross edge reaches 7.7 bps). So "every gross edge is smaller than one round trip"
  is true for the point estimates, not with statistical confidence.
- **The daily-data regime numbers are distorted by the 09:15 opening print.** Measured from the
  09:16 price, the 2015-2024 intraday loss is -58%, not -183%. The REPORT's 2026 claim
  ("overnight -0.8% vs intraday -11.3%, the decline happened during market hours") is not robust.
  This does not touch the "nothing survives costs" headline.
- **Several reported statistics lean pessimistic:** RC p = 0.97, DSR = 0.08, and the 0.52
  Spearman (which is mostly a cost artefact). One leans optimistic: PBO = 0.21. Corrected values
  still fail every gate.

**Count of findings:** 0 critical · 3 major · 9 minor · 6 nit.

### Snapshot audited
I audited the tree as of commit `6b91b0c` plus working files at 19:47 UTC. During the audit,
commit `eeee7d8` added `discovery.spa_check` (Hansen SPA), switched the best-pattern FWER gate to
SPA, and added `REPORT.md`. I reviewed that diff as well:
- `spa_check` matches my independent SPA_c implementation: p = 0.876 (theirs, 500 resamples) vs
  0.880 (mine, 300).
- The current code passes all 12 tests.
- The fast run (`--boot 50 --placebo 5`) reproduces the discovery, PBO and hold-out numbers
  exactly.

Line numbers below refer to the current files. All experiments ran on copies in the session
scratchpad; nothing under `/home/user/Algo2026` was modified except this file.

---

## Findings

| ID | Severity | Where | One-line summary | Could change headline? |
|---|---|---|---|---|
| A1 | major | `regime.py:39-41` (+ REPORT §1, dossier l.105) | 09:15 opening-print drift (-5.5 bps/day) is booked as "intraday"; inflates the intraday loss about 3x; 2026 split not robust | No (headline); **maybe** for the REPORT's 2026 "decline was intraday" claim |
| A2 | major | `run_all.py:136`, dossier l.93 | Spearman(IS t, OOS t) = 0.52 is mostly mechanical cost drag; gross-signal persistence is 0.14-0.19 | No |
| A3 | major (interpretation) | `hypotheses.py`, REPORT §4 | ORB-with-stop has a significant, replicated **gross** edge; its net loss is not significant; margin to breakeven is about 1.3 SE | Maybe (thin margin); no on point estimates |
| B1 | minor | `discovery.py:114-139`, dossier l.80 | RC p = 0.97 is a least-favourable bound; "no-predictability" nulls give p = 0.07-0.17 | No |
| B2 | minor | `run_all.py:151` | DSR's V mixes deterministic cost/σ offsets and long/short mirror rows; DSR 0.08 becomes 0.41-0.60 | No (still < 0.95) |
| B3 | minor | `run_all.py:116-118` | PBO on net SR is flattered by cost-driven rank persistence: 0.21 net vs 0.39 gross | No (optimistic direction) |
| B4 | minor | `regime.py:89-107` | Gap-by-era fade table measured from the official open; up-gap "fade" profits are the open-print artefact | No |
| B5 | minor | `data.py:82-87`, `features.py:54` | eod2 daily file is missing at least 11 sessions in 2015-16 and 2020-02-01; stale prev_close on 6 eligible days; 10 contaminated "overnight" rows | No |
| B6 | minor | `regime.py:53` | `var(o)/var(o+i)` is not a share when corr(o,i) < 0; 2026 "66%" is 57% under an additive split | No |
| B7 | minor | `discovery.py:34-40`, `hypotheses.py:63` | Entry fills at the close of the bar that completes the signal; a 1-min delay costs about 1 bps and 10 of 61 "discoveries" | No (optimistic direction) |
| B8 | minor | `costs.py:22` | 1 pt/side slippage is conservative for 1-lot Nifty futures; statutory-only cost is 5.98 bps | No |
| B9 | minor | `run_all.py:127-137` | Per-pattern hold-out tests are underpowered; the hold-out shows gross decay to about 0, not a reversal | No |
| C1 | nit | `features.py:122-126` | `or15` at 09:30 and `or30` at 09:45 are degenerate (always "inside"); 239 duplicate day-sets | No |
| C2 | nit | `hypotheses.py:42-44` | H1 charges a full round trip on a zero-signal day (1 day) | No |
| C3 | nit | `regime.py:17,19` | Event dates: Soleimani strike was before the 3 Jan 2020 open; Galwan news broke intraday | No |
| C4 | nit | docstrings, REPORT l.234 | Stale or inaccurate documentation (see below) | No |
| C5 | nit | `tests/` | Cost test is self-referential; no tests for RC/SPA/PBO/block_stats/hypotheses/regime | No |
| C6 | nit | REPORT §3-§5 | Several REPORT robustness numbers are not produced by committed code (I reproduced all of them) | No |

### A1 (major): the opening print contaminates the overnight/intraday decomposition
**Where:** `regime.decompose` (`regime.py:39-41`) uses the official daily `Open`. In the minute
data that is exactly the 09:15 bar's open: the median |difference| is 0.0 bps. Quoted in the
dossier (l.105) and the REPORT (§1, ll.11-12, 39-46).

**Evidence.** The open print → 09:16 move averages -6.8 bps/day in 2015-20 and -3.1 in 2021-24
(`results/time_of_day_drift.csv`). By year it is: -8.1, -6.2, -5.3, -4.7, -7.1, -9.6, -5.2,
**+1.9 (2022)**, -6.2, -1.6 (2024 Q1). Recomputing the decomposition on the 2,251 minute-data
days:

| Open used | Cum. overnight 2015-24 | Cum. intraday 2015-24 | Mean intraday | Overnight var share |
|---|---|---|---|---|
| Official 09:15 print (as coded) | +278.6% | **-183.1%** | -8.13 bps/day | 0.375 |
| 09:16 price (close of 09:15 bar) | +153.7% | **-58.2%** | -2.59 bps/day | 0.425 |
| 09:20 price | +173.5% | -78.0% | -3.47 bps/day | 0.408 |

About two thirds of the measured intraday loss is the untradeable first minute. The *sign* of
"all return came overnight" survives, and the variance-share conclusion gets stronger (0.375 →
0.425). The magnitudes in "+374% vs -232%" do not.

**2026 claim.** The REPORT's "2026 YTD: overnight -0.8% vs intraday -11.3%" (182 days) cannot be
corrected, because no minute data exists for 2026. It is fragile:

| Assumed first-minute drift in 2026 | Intraday | Overnight |
|---|---|---|
| -1 bps/day | -9.5% | -2.6% |
| -3.1 bps/day (2021-24 average) | -5.7% | -6.5% |
| -5.5 bps/day (2015-24 average) | -1.3% | -10.8% |

**Could change headline?** No for "nothing survives costs". **Maybe** for the REPORT's argument
that "in 2026 the decline happened during market hours". That statement should be qualified or
removed until 2026 minute or futures data is checked.

### A2 (major): the 0.52 IS/OOS rank correlation is mostly cost arithmetic
**Where:** `run_all.py:136` correlates **net** t-stats. Net t = gross t − cost·√n/σ. The cost
term depends only on n and σ, which persist across periods.

**Evidence** (all candidates with ≥ 20 hold-out trades):
- Spearman of net t, as reported: **0.516**.
- Spearman of the IS cost drag alone (−cost/se) against OOS net t: **0.596**. This is higher
  than the reported statistic.
- Spearman of gross t, IS vs OOS: **0.189**. Within each direction: **0.142**. Gross bps: 0.111.

The dossier's reading (l.93: "directional structure, mainly short-side bias, persists") overstates
what persists. Weak gross structure does carry over (consistent with the placebo excess, B1), but
at ρ ≈ 0.14-0.19, not 0.52.

**Fix:** report the gross-t correlation, or partial out cost/se.

**Could change headline?** No. If anything it strengthens "no edge".

### A3 (major, interpretation): ORB with a stop has a real gross edge; its net loss is within noise
**Where:** `hypotheses.opening_range_breakout`, REPORT §4 and §8B.3. The code is correct: it
matches an independent bar-by-bar implementation exactly for all three variants. The issue is
how the numbers are framed.

**Evidence: gross bps per trade (t-stat)**

| Strategy | 2015-20 | 2021-24 | All 2015-24 | 95% CI upper bound, all |
|---|---|---|---|---|
| ORB-30 + stop | 5.63 (3.21) | 4.31 (2.28) | **5.16 (3.93)** | **7.73** |
| ORB-15 + stop | 4.40 (2.52) | 3.35 (1.76) | 4.02 (3.07) | 6.58 |

**Robustness of ORB-30 to execution assumptions.** It stays at 4.6-5.2 bps gross under every
variant I tried:

| Variant | ORB-30 gross, all 2015-24 |
|---|---|
| Stop on a 1-min close, exit at that close | 4.98 |
| Same, but exit one bar later | 4.88 |
| Intrabar stop with 2 extra points of slippage on the stop | 4.59 |
| Gap-through stop fills | 5.62 / 4.31 IS/OOS (no change) |
| Entry at next bar's open | 5.62 / 4.26 IS/OOS |

The no-stop variant earns only about 1 bps. So the edge comes from the stop logic, and that
logic survives realistic fills.

**Net at 6.87 bps:** -1.7 ± 1.3 bps (t ≈ -1.3). Net losses in both periods are point estimates
that are not statistically significant.

The headline still holds on economics. Today's statutory charges alone are 5.98 bps (zero
slippage, `costs.py`), which is above the 5.16 bps point estimate. Breakeven needs about 1.3 SE
of luck in the edge, or a cheaper instrument such as the options route in REPORT §8B.
Recommended wording: "gross edge ≈ 75% of today's cost (95% CI 2.6-7.7 bps); cannot be shown
profitable, and cannot be ruled out as breakeven".

**Could change headline?** Maybe, at the margin. It is the one result where "nothing survives"
rests on a point estimate about 1 SE from breakeven.

### B1 (minor): Reality Check p = 0.97 answers a least-favourable null
**Where:** `discovery.reality_check` (`discovery.py:114-139`) recentres every candidate to zero
*net* mean. With costs, almost every long/short pair has strongly negative net means, and a
pattern's long and short legs cannot both sit at zero net.

The implementation is otherwise correct:
- Weights equal an explicit resample.
- The bootstrap SD of studentised t\* is 0.99 (well calibrated).
- `abs()` covers both directions.

**Evidence: p-value of the best pattern (t = 3.27) under different nulls**

| Null | Bootstrap max-t median / p95 | p for the best pattern |
|---|---|---|
| RC, LFC (as coded) | 3.93 / 5.01 | 0.970 |
| Hansen SPA_c (mine; matches the new `spa_check`) | 3.78 / 4.94 | 0.880 |
| "No predictability" (gross mean 0, so net = −cost) | 2.65 / 3.90 | **0.173** |
| Permutation placebo (100 runs) | — | 0.09 |
| Circular-shift placebo (keeps time clustering, 40 runs) | max-t p95 3.43 | 0.07 |

SPA stays high because many small-n candidates have net t above −2 and so are still recentred.
The REPORT now quotes "p = 0.09 to 0.97", which is fair. The dossier's p = 0.97 alone overstates
how far the best pattern is from significance.

**Could change headline?** No. Nothing reaches 0.05 under any null.

### B2 (minor): DSR uses an inflated trial variance
**Where:** `run_all.py:151`, `var_sr = var(net_bps/sd_bps)` over all 24,488 rows. Net SR =
gross SR − cost/σ. The cost/σ term has a median of 0.17 (5th-95th percentile 0.07-0.36) across rows and is
deterministic and negative, so it cannot produce a large maximum. It also mixes long and short
mirror rows.

The DSR formula itself (`stats.py:59-85`) matches Bailey & López de Prado (2014), including
non-excess kurtosis, and so do `expected_max_sharpe` and MinBTL.

**Evidence** (best pattern, SR 0.412, n = 63):

| Choice of V | V | SR0 | DSR |
|---|---|---|---|
| As coded | 0.0212 | 0.593 | **0.079** |
| Distinct day-sets only (N = 12,005) | 0.0212 | 0.569 | 0.111 |
| Variance of gross SR | 0.0118 | 0.443 | **0.407** |
| Pure sampling noise, mean(1/n) | 0.0087 | 0.381 | **0.598** |

The dossier's "expected max SR from noise (0.59) exceeds observed 0.41" depends on this choice.

**Could change headline?** No. Every variant is below 0.95.

### B3 (minor, optimistic direction): PBO is flattered by costs
**Where:** `run_all.py:116-118`. `pbo_cscv` is correct: an independent implementation using
`scipy.stats.rankdata` reproduces PBO = 0.2063 and median logit 1.770. But on net SR, the
persistent cost/σ ranking keeps the IS-best near the top OOS.

**Evidence:**

| Rows | Net of cost | Gross (zero cost) |
|---|---|---|
| All rows | 0.206 | **0.393** |
| Long rows only | 0.325 | 0.460 |

The "near pass" (0.21 vs the 0.20 gate) is a cost artefact.

**Could change headline?** No. It makes mining look better, not worse.

### B4 (minor): `gap_conditional_open_to_close` is contaminated by the open print
**Where:** `regime.py:89-107` and `results/gap_open_to_close_by_era.csv`. Fades are measured from
the official open. The first-minute drift is -5.4 bps on up-gap days and -5.8 bps on down-gap
days, so it adds about 5-6 bps to up-gap fades and subtracts it from down-gap fades.

**Evidence: up-gap fade, net bps**

| Era | As coded | Entry at 09:20 instead |
|---|---|---|
| 2015-20 | **+6.4** | -0.8 |
| 2021-24 | **+3.7** | -0.9 |

The table is not cited in the dossier, but a reader could take it as an edge.

**Could change headline?** No.

### B5 (minor): the daily file is missing sessions, so t-1 features are stale on some days
**Where:** `load_daily` (`data.py:82-87`) feeding `daily_context` (`features.py:54`, `shift(1)`
is row-based) and `regime.decompose`.

**Missing sessions.** `nifty_50_daily.csv` lacks 2015-02-02, 02-28, 03-12, 03-13, 05-19, 07-08,
09-04, 10-16, 12-01, 2016-06-20 and 2020-02-01 (Budget Saturday). It also lacks 2013-10-09,
2014-03-19, 2014-12-15 and 2016-10-30; `niftybees` has those dates.

**Consequences:**
1. Those minute-data days are silently ineligible.
2. On 6 eligible IS days (2015-05-20, 07-09, 10-19, 12-02, 2016-06-21, 2020-02-03), prev_close,
   gap and all t-1 features refer to two sessions back. For example, 2020-02-03's gap is
   computed as -280 bps instead of -14 bps versus the Saturday close, so the day is mislabelled
   `gap=big_down`.
3. Ten `decompose` rows book a whole session as "overnight" (e.g. 2020-02-03 at -2.84%).
   2015-09-07 is in the top-50 tail set. Tail attribution barely moves (median gap share 0.400 →
   0.395; same-sign share 88% unchanged).

**Fix:** derive prev_close from a complete calendar, or from the minute panel, and flag days
whose predecessor session is missing.

**Could change headline?** No (6 of 1,417 IS days).

### B6 (minor): the "overnight variance share" is not an additive share
**Where:** `regime.py:53`, `var(o)/var(o+i)`. This exceeds a decomposition share when
corr(o, i) < 0.

**Evidence:**

| Year | As coded | `var(o)/(var(o)+var(i))` | corr(o, i) |
|---|---|---|---|
| 2026 | 0.655 | **0.566** | -0.14 |
| 2025 | 0.491 | 0.433 | — |

The 2012-25 median is unchanged (0.292). The REPORT and dossier headline "66% in 2026" would be
57% under an additive split.

**Could change headline?** No.

### B7 (minor, optimistic direction): same-bar execution
**Where:** `price_col` (`discovery.py:34-36`). Entry is at the close of bar k−1, which is the
same price the predicates see last. ORB (`hypotheses.py:63`) also enters at the close of the
breakout bar. This is not look-ahead, but it assumes zero latency, and 1-minute index data has
stale-price autocorrelation.

**Evidence: delaying entry**

| Entry delay | IS mean of the 61 t > 2 patterns | How many keep t > 2 | Re-mined max t |
|---|---|---|---|
| None (as coded) | 17.9 bps | 61 | 3.27 |
| 1 minute | 16.9 bps | 50 | 3.12 |
| 5 minutes | — | — | 2.94 |

ORB moves by 0.05 bps or less.

**Could change headline?** No. The bias favours the strategies.

### B8 (minor, pessimistic direction): conservative slippage
**Where:** `costs.py:22`. One index point per side (0.44 bps/side) is generous relative to the
near-month Nifty futures spread for a 1-lot order.

The statutory arithmetic is correct: ₹874.3 per round trip = 5.98 bps. STT of 0.05% on the sell
side from 1 Apr 2026 is confirmed by web search (Budget 2026: futures 0.02% → 0.05%, options
0.10% → 0.15%).

**Effect of the slippage assumption:**
- With 0.25 pt/side the cost is 6.20 bps.
- The largest gross edge found (ORB-30, 5.16 bps) is below even the statutory-only 5.98 bps.
- The top-50 mined patterns earn +1.8 bps gross in the hold-out.

Costs are charged **exactly once per round trip** everywhere: `score`, `trades`/`evaluate_on`,
`block_stats` (algebra verified), all hypotheses, the stress adjustment
`o_s − (stress − cost)`, and the top-10 portfolio. Nothing is double-charged and no sign is
flipped.

**Could change headline?** No.

### B9 (minor): hold-out power and how to read it
**Where:** `run_all.py:127-137`. Mined patterns have 26-91 hold-out trades and per-trade sd of
about 50-100 bps, so OOS se ≈ 8-15 bps. Single-pattern OOS tests cannot separate +5 from -5 bps.

**Evidence: the 61 t > 2 patterns in the hold-out**
- Gross: mean **+1.7 bps**, median +1.1, 56% positive.
- Net: 21% positive, median -5.8 bps.

So the hold-out shows the gross edge decaying to about zero, not reversing. The pooled result in
REPORT §3 (3,270 trades at -5.6 bps; I reproduced it exactly) is the right summary.

**Could change headline?** No.

### Nits
- **C1. Degenerate atoms.** In `features.py:122-126`, at k = n the range uses bar n−1, whose
  high/low brackets its close. So `or15` at 09:30 and `or30` at 09:45 are always `inside`, and
  `above`/`below` are never true. This makes 239 exact duplicate day-sets (12,244 → 12,005
  distinct patterns). It slightly inflates n_trials for Holm/BH/DSR/MinBTL, in the conservative
  direction. RC and placebo are unaffected.
- **C2. H1 zero signal.** `hypotheses.py:42-44`: if `sign(...) == 0` the day is charged
  −cost with no trade (1 day in the sample).
- **C3. Event dates.**
  - The Soleimani strike was about 03:30 IST on 3 Jan 2020, so the first session after the news
    is 2020-01-03, not 01-06. Swapping the date leaves the "15 negative gaps / 9 rebounds"
    count unchanged.
  - The Galwan news (2020-06-16) broke during market hours: the +2.03% gap is unrelated and the
    -1.01% session move is the reaction. It is not an "overnight shock" example.
  - The 2026 entries could not be verified independently.
- **C4. Documentation.**
  - `features.py:6` cites `tests/test_no_lookahead.py`, which does not exist; the test is in
    `tests/test_patternlab.py`.
  - The `discovery.py` docstring says "~40k candidates".
  - "24,488 candidate patterns" are 12,244 patterns × 2 directions.
  - `reality_check` takes unused `table` and `cost_bps` arguments.
  - `expiry_flags` keeps flagging Thursdays after the Sep 2025 move to Tuesday. This is harmless
    because the flags are only used on 2015-24 data.
  - REPORT l.234 says SPA "p **rose** from 0.97 to 0.88"; it fell.
- **C5. Tests.**
  - `test_cost_model_matches_broker_calculator` asserts the model's own output (₹874), so it is
    self-referential.
  - There are no unit tests for `reality_check`, `spa_check`, `fwer_pvalues`, `block_stats`,
    `pbo_cscv`, hypotheses or regime.
  - The look-ahead test uses synthetic data only and does not perturb future *days*. I covered
    both gaps; see below.
- **C6. Reproducibility.** Several REPORT numbers are not produced by any committed code:
  - the 2015-2019-only discovery (47 / 29.8% / +13.9 → -5.4 / 74% short);
  - "short every day 09:30-15:15" (+3.8 / +2.4 gross);
  - top-50 pooled (3,270 trades, -5.6 bps);
  - ORB-30 by year (0.8-12.8 bps).

  I reproduced every one of them exactly. They should be added to `run_all.py`.

---

## Checked and found correct

**Look-ahead and leakage**
- **Truncation test.** I deleted all post-2020 minute, daily and VIX data, rebuilt context and
  IS combos, and got byte-identical predicate masks, outcomes and names (1,417 days).
- **Daily context.** I perturbed every daily and VIX row from day t onward (5% noise, VIX × 3)
  at 4 dates. `daily_context` up to and including t was unchanged, so all features use data
  through t−1 only. Manual checks:
  - `prev_close`, `sigma20` (20-day std ending t−1);
  - `vix_pct` (250-day rank ending t−1), matched `rankdata` at 3 dates.
- **Intraday predicates.** On the real panel, for all 11 decision minutes, scrambling bars ≥ k
  leaves masks unchanged. Multiplying all *future days* by 1.3 leaves masks for earlier days
  unchanged, which covers the cross-day 60-day `range_so_far` median (`shift(1)`) and the
  `last30` guard (k ≥ 31, so no wrap to column −1).
- **Expiry flags.**
  - Weekly expiries start 2019-02-14; there are 53 in 2020 (53 Thursdays).
  - Holiday shifts are correct (Wednesdays): 2019-03-20, 2019-08-14, 2020-04-01, 2021-03-10,
    2021-05-12, 2021-08-18, 2022-04-13, 2023-01-25, 2023-03-29, 2023-06-28, 2024-04-10,
    2024-08-14.
  - Monthly last-Thursday logic is correct.
  - The flags use the exchange holiday calendar, which is published in advance, so this is not
    look-ahead.
- **IS/OOS separation.** Selection, placebo, RC/SPA, PBO and DSR all use IS combos only.
  `evaluate_on` uses separately prepared OOS combos. Predicate names are identical across
  `c_is`, `c_oos` and `c_all`.

**Time indexing**
- `price_col`/`outcome_bps`: entry 09:30 → column 14 with decision k = 15; 15:15 → column 359;
  15:30 → column 374. All 11 windows were checked.
- ORB matches an independent loop exactly:
  - range from bars 0..n−1;
  - breakouts on closes from bar n to 358;
  - stop checked on bars k+1..359;
  - exit at the close of bar 359.
- H1 matches Gao et al. (2018): previous close → first 30 min (09:45) sign, trade the last 30
  min (15:00 → 15:29 close). Gross edge 0.2 / 1.0 bps; regression R² 0.06% / 0.15%.
- Gap trade: sign, |gap_z| > 0.5, 09:20 → 15:15.
- Bar labelling: the minute timestamps are bar-start labels (the 09:15 bar open equals the
  official open).

**Statistics** (brute force or independent reference)
- `score()` vs explicit per-trade computation on 300 random rows: n, net, sd, t and win rate
  agree to 1e-13.
- `evaluate_on` and `block_stats`:
  - net sum = s·S − c·C;
  - sum of squares = Q − 2cs·S + c²·C;
  - both agree to 1e-9.
- Stationary bootstrap (Politis-Romano, wrap-around), and bootstrap weights equal to an
  explicit resample.
- Studentisation calibration: bootstrap SD of t\* is 0.99.
- `fwer_pvalues` with (1 + #≥) / (1 + B).
- Holm and BH step-down/step-up.
- DSR / expected max SR / MinBTL formulas match the papers.
- PBO / CSCV: 252 splits, mid-rank, logit.
- New `spa_check`: Hansen g_c with threshold √(2 ln ln n).
- Placebo: the same permutation for all combos keeps cross-window dependence. A circular-shift
  placebo, which keeps time clustering, gives a similar result (mean 15.4 patterns with t > 2;
  max-t p95 3.43), so the "61 vs ~15-18" excess is not an artefact of clustered predicates.
- The top patterns are not COVID-only: excluding 15 Feb – 30 Apr 2020, the top 5 keep
  t = 2.4-3.1.

**Data cleaning** (`data.py`)
- Timestamp flooring:
  - 10,693 rows (100 days in Jun-Nov 2015) carry :01-:59 seconds;
  - flooring creates only 4 collisions, all with identical closes, and `keep="first"` is benign.
- Dropped days: 12 (<370 bars or no 09:15 bar), including the 2021-02-24 NSE outage and a
  partial last day.
- Filled minutes: 29 across 18 days (flat bars).
- Out-of-session bars exist only on Muhurat days and 2021-02-24.
- Bar sanity: no OHLC-inconsistent bars. The largest 1-min moves fall on the 13 Mar and
  23 Mar 2020 circuit-breaker days (real events).
- Official close vs the 15:29 bar close: median 4.9 bps apart. This is expected, because the
  official close is a 30-min VWAP.

**Reproduction**
- Tests: 12 pass.
- Fast run: reproduces discovery (24,488 rows / 61 / 4 / max t 3.274), PBO 0.2063, the hold-out
  block and the top-10 portfolio (+21.2% / −2.6%).
- Costs: ₹874.3 per round trip; 6.87 / 3.84 / 8.64 bps scenarios.

## Recommendations (none change the conclusion)
1. Add a "09:16-open" version of `decompose`. Report both, and drop or qualify the 2026 "decline
   was intraday" sentence (A1).
2. Report the gross-t Spearman (A2), and confidence intervals on the gross and net edge of each
   pre-registered strategy (A3).
3. Report SPA, the no-predictability bootstrap and placebo p-values together (B1). Compute DSR
   with V from gross SR, or from sampling noise (B2). Report PBO at zero cost as well (B3).
4. Fix the daily calendar gaps (B5), the degenerate ORB atoms (C1) and the docstrings (C4). Add
   unit tests for RC, SPA, PBO, block_stats, hypotheses and regime (C5). Move the REPORT's ad-hoc
   robustness checks into `run_all.py` (C6).
