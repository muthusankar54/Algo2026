# Evaluation dossier: intraday pattern-based Nifty + Sensex system (as of 2 Oct 2026)

This dossier is the single input given to every AI judge. It states the proposal and the
evidence gathered, without a recommendation. Judges score it independently.

## 1. The proposal (trader's own words, paraphrased)

An Indian retail trader currently holds equities for weeks/months. Because of global
conditions (El Niño / "super El Niño", US-Iran war and Iran vs other countries, Russia-Ukraine
war, India-China tension) they plan to stop holding positions and instead build an
**intraday, pattern-based system** using a **pattern-discovery approach**, taking either
**bull or bear** trades, applied to **Nifty and Sensex combined** (index futures/options),
using a system they build themselves.

## 2. Market backdrop, Oct 2026 (from web research; sources dated Sep-Oct 2026)

- Nifty ~22,420 on 1 Oct 2026, about -13% YTD; Sensex ~71,900, about -15% YTD. September 2026
  was Nifty's worst September since 2018. FIIs sold ~Rs 4.03 lakh cr in 2026; DIIs absorbing.
- US/Israel-Iran war began 28 Feb 2026; ceasefire 7-8 Apr with repeated breakdowns; US naval
  blockade of Iranian ports continues; Hormuz traffic still a fraction of normal. Brent: ~$72
  pre-war, $126 peak (30 Apr), ~$100-108 late Sep.
- India VIX: 13.7 (27 Feb) -> 26.7 (23 Mar peak); 12-15 in late Sep / 1 Oct 2026.
- NOAA (10 Sep 2026): El Niño advisory, >90% chance of a very strong event; Indian monsoon
  2026 ended at 87% of LPA (4th lowest since 2001); Aug CPI 4.82%, food 5.95%. RBI repo 5.25%,
  next decision 7 Oct. Fed hiked to 3.75-4.00% on 16 Sep. INR ~96/USD.
- Russia-Ukraine ongoing (talks being revived). US tariff threats over India's Russian oil.
- India-China: thaw in 2026 (Xi visited Delhi 12 Sep); no 2026 border flare-up found.

## 3. Regulation and costs, Oct 2026 (official circulars / broker calculators)

- **STT raised from 1 Apr 2026** (Finance Act 2026): futures 0.05% sell side (was 0.02%),
  options 0.15% of premium sell side (was 0.1%).
- Round trip, 1 lot Nifty futures (lot 65, ~Rs 14.6 lakh notional) = **Rs 874 in charges**
  (~13.5 Nifty points, ~6.0 bps); with 1 point slippage per side **~6.9 bps**. Before Apr 2026
  the same trade cost ~3.8 bps. ATM weekly option round trip ~Rs 70 (~1.1 option points).
- Margin ~Rs 1.67 lakh per Nifty futures lot; no extra intraday leverage (peak-margin rules).
- Expiries: Nifty weekly Tuesday (NSE), Sensex weekly Thursday (BSE). Closing auction session
  live since 3 Aug 2026; SEBI consulting (to 3 Oct) on expiry settlement price methodology.
- SEBI retail-algo framework in force for all brokers since 1 Apr 2026: <10 orders/sec without
  exchange registration, static IP, daily OAuth+2FA login, **limit orders only for API orders**,
  self/family use only; selling signals/black-box needs SEBI RA registration.
- SEBI studies: 93% of individual F&O traders lost money FY22-24 (Rs 1.8 lakh cr); 91% in FY25;
  87.7% in FY26 (Rs 91,685 cr losses, Rs ~25,000 cr paid in costs). 70%+ of intraday cash
  traders lose (FY23). Prop/FPI profits are ~96-99% from algorithmic firms. SEBI's Jane Street
  order (Jul 2025) alleged index manipulation around expiries.
- F&O income is non-speculative business income (ITR-3, audit thresholds apply).

## 4. Academic evidence (summarised)

- Intraday momentum (Gao et al. 2018, SPY): first half-hour predicts last half-hour; ~2.6 bps
  gross per trade; stronger on high-vol/news days; Baltussen et al. 2021: only on negative-gamma
  days and may not survive costs. Opening-range breakout claims (Zarattini & Aziz) mostly
  practitioner papers; independent replications ~zero after spreads.
- Technical-rule literature: best rules lose significance after data-snooping corrections
  (Sullivan-Timmermann-White 1999; Bajgrowicz-Scaillet 2012). India: MA rules unexploitable
  after costs (Mitra 2011).
- False-discovery tools: White's Reality Check, Hansen SPA, Romano-Wolf, t > 3 (Harvey-Liu-Zhu),
  Deflated Sharpe >= 0.95, PBO (authors suggest rejecting > 0.05), minimum backtest length.
- Day-trader outcomes: <1% of Taiwanese day traders predictably profitable (Barber et al.);
  97% of persistent Brazilian day traders lost money (Chague et al.).
- ML for intraday index direction: credible OOS accuracy ~50-54%; leakage is endemic.

## 5. Empirical tests run for this evaluation (code: intraday-research/patternlab)

Data: Nifty 50 1-minute bars Jan 2015 - Mar 2024 (2,213 usable days, public MIT dataset);
NSE daily Nifty 50 & India VIX to 25 Sep 2026. No Sensex intraday data was available; Sensex
is proxied by a Sensex ETF for correlation only. Costs charged at today's rates (6.87 bps
base; 3.84 pre-Apr-2026; 8.64 stress). All features are point-in-time (unit-tested by
scrambling future bars). Discovery period Mar 2015 - Dec 2020 (1,417 days); untouched hold-out
Jan 2021 - Mar 2024 (796 days).

### 5a. Exhaustive pattern discovery
- Grammar: 1-2 condition conjunctions of ~55 point-in-time "atoms" (gap size, previous-day
  return/close location/NR7/inside day, trend, 5-day return, VIX regime, day of week, expiry
  day, open-to-now move, opening-range position, gap-fill state, first-15-min candle,
  range-so-far, price vs TWAP, last-30-min move) x 11 entry/exit windows x long/short.
- **24,488 candidate patterns** with >= 50 trades. At base cost: 61 with t > 2, 4 with t > 3,
  max t = 3.27, **0** significant after Holm or Benjamini-Hochberg.
- **White's Reality Check** (500 stationary-bootstrap resamples, all 24,488 patterns): best
  pattern's family-wise p = 0.97; 0 patterns with FWER p < 0.05. Bootstrap null max-t median 3.9.
- **Placebo** (same pipeline, outcomes shuffled across days, 100 runs): mean 17.7 patterns
  with t > 2 (95th pct 42) vs 61 in real data; placebo best-t 95th pct 3.38 vs real 3.27.
  i.e. real data has *more weak structure than noise*, but the best pattern is not
  distinguishable from luck.
- 95% of the t > 2 "discoveries" are SHORT patterns (e.g. "short 09:30->15:15 if previous day
  down and today's open-to-now move is big down"), consistent with continuation on down days.
- **Deflated Sharpe** of the best pattern = 0.08 (needs >= 0.95); expected max per-trade SR from
  noise (0.59) exceeds the observed 0.41. **PBO (CSCV, 10 blocks)** = 0.21. Minimum backtest
  length for 24,488 trials at annual SR 1 = 16.6 years (we had ~6).
- **Hold-out (2021-2024)**: of the 61 t > 2 discoveries, 21% stayed profitable; median edge
  went from +16.8 bps/trade in-sample to -5.8 bps out of sample; 1 of 61 had hold-out t > 2.
  Top-10 equal-weight portfolio: +21% cumulative in-sample -> about -2.5% over the hold-out.
  Spearman(in-sample t, hold-out t) across all candidates = 0.52 (directional structure, mainly
  short-side bias, persists; magnitudes do not survive costs).
- Cost sensitivity, top-50 patterns' hold-out mean: +1.8 bps at zero cost (80% positive),
  -1.9 bps at pre-2026 cost, -5.0 bps at today's cost, -6.7 bps at stress cost.

### 5b. Pre-registered literature strategies (Nifty, 2015-2024)
Gross edge per trade, in-sample / hold-out: intraday momentum +0.2 / +1.0 bps; ORB-15 with stop
+4.4 / +3.3; ORB-30 with stop +5.6 / +4.3; ORB-15 no stop +1.1 / +2.0; gap fade -2.5 / -4.0;
gap-and-go +2.5 / +4.0. **All are negative after today's 6.9 bps cost** in both periods.
Weekly-expiry days (2019-2024): no directional drift; range slightly lower than other days.

### 5c. Where does risk arrive? (daily data 2012 - Sep 2026)
- Cumulative log return 2012-2026: overnight (close->open) +374%, intraday (open->close) -232%.
  Part of the intraday loss is the 09:15 index opening print (-6.8 bps/day in 2015-20, -3.1 in
  2021-24, untradeable); after 09:30 intraday drift is small and negative (~-2 to -3 bps/day).
- Share of daily variance from the overnight gap: median 29% (2012-2025); **66% in 2026**.
- 50 largest daily moves since 2012: gap had the same sign in 88%; median gap share 40%.
- 18 geopolitical/macro shock days 2019-2026: 15 opened with negative gaps; on 9 of those the
  session then rebounded (e.g. 2026-03-02 gap -2.1%, session +0.8%; 2026-03-09 gap -2.4%,
  session +0.7%); 2022-02-24 (Ukraine) and 2026-03-23 (Hormuz ultimatum) continued down.
- Late Sep 2026: gaps small, intraday moves larger (trend days and V-reversals).
- Median daily Nifty range 2023-2026: ~73-86 bps; today's round-trip cost = ~8% of it.

### 5d. Nifty + Sensex combined
- Daily correlation Nifty vs Sensex ETF 2021-2026 = 0.93 (Nifty vs a Nifty ETF = 0.98, so the
  true index correlation is ~0.95+). Running the same signal on both gives a diversification
  gain of ~1-2% in Sharpe; it mostly doubles position size. Different weekly expiry days
  (Tue vs Thu) are the main structural difference.

### 5e. Limitations
- Minute data ends Mar 2024; it predates the Nov 2024 SEBI F&O changes, the Sep 2025 expiry-day
  move, the Apr 2026 STT hike and the 2026 war regime. Index prices, not futures prices.
- Pattern grammar is broad but finite (1-2 conditions, fixed time exits; no stops/targets
  except in the ORB tests). Options-based execution not backtested.
