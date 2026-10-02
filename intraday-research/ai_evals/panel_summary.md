# AI-judge panel results

6 independent judges, same dossier and rubric (scores 1-10, 10 = most favourable to the proposal).

## Verdicts

| Judge | Persona | Verdict | Confidence | P(net profitable, 12m) |
|---|---|---|---|---|
| advocate | Steelman advocate / strategy builder | PILOT_ONLY | 0.72 | 0.18 |
| coach | Retail trading & behavioural coach | NO_GO | 0.80 | 0.07 |
| compliance | SEBI market-structure & compliance specialist | NO_GO | 0.82 | 0.10 |
| macro | Global macro & geopolitical strategist | NO_GO | 0.85 | 0.10 |
| quant | Skeptical quant researcher | NO_GO | 0.85 | 0.12 |
| risk | Prop desk head of risk | NO_GO | 0.80 | 0.08 |

Verdict distribution: NO_GO 5, PILOT_ONLY 1, CONDITIONAL_GO 0, GO 0
Mean P(net profitable over 12 months): 0.11 (range 0.07-0.18)

## Scores by dimension

| Dimension | Mean | SD | Min | Max |
|---|---|---|---|---|
| thesis_fit | 4.0 | 1.1 | 3 | 6 |
| edge_evidence | 2.2 | 0.4 | 2 | 3 |
| cost_feasibility | 2.3 | 0.8 | 2 | 4 |
| method_rigor | 3.5 | 0.6 | 3 | 4 |
| risk_control | 5.2 | 0.4 | 5 | 6 |
| regulatory_operational | 5.7 | 0.8 | 5 | 7 |
| behavioral_sustainability | 2.2 | 0.4 | 2 | 3 |
| nifty_sensex_combination | 2.5 | 0.8 | 2 | 4 |

Overall mean score: 3.44 / 10

Inter-judge agreement on which dimensions are strong vs weak (Kendall's W): 0.94

## Per-judge scores

| Judge | thesis_fit | edge_evidence | cost_feasibility | method_rigor | risk_control | regulatory_operational | behavioral_sustainability | nifty_sensex_combination |
|---|---|---|---|---|---|---|---|---|
| advocate | 6 | 3 | 4 | 4 | 6 | 7 | 3 | 4 |
| coach | 4 | 2 | 2 | 4 | 5 | 6 | 2 | 2 |
| compliance | 3 | 2 | 2 | 3 | 5 | 6 | 2 | 3 |
| macro | 3 | 2 | 2 | 3 | 5 | 5 | 2 | 2 |
| quant | 4 | 2 | 2 | 3 | 5 | 5 | 2 | 2 |
| risk | 4 | 2 | 2 | 4 | 5 | 5 | 2 | 2 |

## Must-have conditions and best variants (verbatim, by judge)

### advocate (Steelman advocate / strategy builder): PILOT_ONLY

Top failure modes: Cost bleed: at 6.9 bps per round trip in futures and ~250 trades a year, even a genuinely positive 3-5 bps gross signal loses 5-10% of notional per year to fees and slippage; the dossier shows every tested strategy flips from gross-positive to net-negative.; False discovery followed by live deployment: an in-sample t of ~3 is indistinguishable from the placebo distribution (95th pct 3.38), and the 61 real 'discoveries' had a median hold-out edge of -5.8 bps; a trader who mines and then trades the top pattern is trading noise with a short-side bias.; Regime and intraday-tail mismatch: the minute data ends Mar 2024 and predates the Nov-2024 F&O changes, the Apr-2026 STT hike and the 2026 war regime; intraday continuation days (2026-03-23), V-reversals, and circuit-breaker halts can hit a leveraged intraday book, and the resulting drawdown typically triggers abandonment or re-mining.

Must-have conditions:
- No open-ended mining for live trading: at most ~10 pre-registered, economically motivated setups (e.g. ORB-30 with stop, down-day trend continuation short, event-day fear-gap rebound), every trial logged, and a setup is live-eligible only if it passes the repo's own gates (DSR >= 0.95 given trials, hold-out t > 2, PBO < 0.05).
- Realised round-trip cost <= 4 bps of delta-notional, demonstrated from actual fills (deep-ITM or ATM weekly options via limit orders, or a verified fee structure); if real fills show > 4 bps, the pilot stops.
- A forward test of at least 60 sessions / 100+ trades at paper or 1-lot size through the broker API before any scaling, with realised net edge > 0 and t > 1.5 on the forward sample alone.
- Hard, automated risk rules: flat by 15:20 every day, daily loss limit of 1% of allocated capital, max 1 lot per Rs 5 lakh of allocated capital, no new entries when India VIX > 25 or within market-wide circuit-breaker events unless the pre-registered setup is specifically for them.
- Keep the long-term equity book (hedged with index puts or collars if the geopolitical fear is the real driver) and cap the intraday sleeve at 10-15% of liquid net worth; the overnight premium is where the historical return is, and the intraday system must not replace it.

Best variant: Address the thesis directly by hedging the existing holdings with index puts or collars instead of liquidating, and run intraday only as a small pre-registered sleeve: 3-5 fixed setups (ORB-30 with stop, weak-open trend-continuation short, large negative fear-gap rebound on event days), executed in deep-ITM or ATM weekly Nifty/Sensex options so statutory cost falls from ~6.9 to ~3 bps of delta-notional, with a 60-session forward-trading gate before any size. An untested but thesis-consistent class worth pre-registering is defined-risk expiry-day premium selling (Tue Nifty / Thu Sensex), since the dossier finds expiry days have slightly lower range and no drift and positions expire the same day.

Would change verdict: A 6-month forward record (>=120 trades) of pre-registered setups at actual fills showing realised net edge > 0 with t > 2 would move me to CONDITIONAL_GO; conversely, if options execution measured at real fills still costs > 5 bps of delta-notional, or post-2024 futures-price minute data shows the gross ORB/continuation edges have shrunk below ~5 bps, I would move to NO_GO.

Disagreements with the dossier:
- Options execution is listed as a limitation but its cost implication is not worked through: the Rs 70 ATM round trip (and ~Rs 60 STT on a deep-ITM option) is roughly a tenth of the Rs 730 futures STT, so the effective cost floor for the proposal 'as written' (futures/options) is nearer 3 bps of delta-notional than 6.9 bps; the pre-Apr-2026 cost column is the relevant one for an options implementation.
- The hold-out test is underpowered and this is not stated: with ~35-100 OOS trades per pattern and ~50 bps per-trade dispersion, it cannot distinguish a +5 bps edge from zero, so '21% stayed profitable' is weaker evidence against the proposal than it reads; the Spearman of 0.52 is the more informative statistic and it supports persistent directional structure.
- The -232% cumulative intraday figure mixes in the untradeable 09:15 opening print (-6.8 / -3.1 bps per day) and describes passive drift, not the opportunity set for a directional system; it argues against being long intraday every day, not against intraday trading as such.
- Slippage is modelled as 1 index point per side with market orders, while SEBI requires limit orders for API trades; a patient limit-order system can have lower realised slippage (with non-fill risk), though STT dominates so this changes little in futures.
- Untested classes that fit the no-overnight thesis are missing: defined-risk expiry-day premium selling on Tue/Thu, Nifty-vs-Sensex relative-value, and a high-VIX regime filter (Gao et al. find intraday momentum concentrated on high-vol/news days; the one low-VIX pattern reported went -13.5 bps OOS, the high-VIX split is not reported). Also, the conditional open-to-close table shows big-down-gap days turned mildly positive (+7.1 bps, n=91) in Apr-2024 to Sep-2026 versus -13.0 in 2015-2020, a hint of a post-2024 regime change that the minute-data study cannot see.

### coach (Retail trading & behavioural coach): NO_GO

Top failure modes: Cost drag exceeds gross edge: ~6.9 bps round trip (up from 3.8 bps before the Apr 2026 STT hike) against 1-4 bps of documented gross edge, so even a 'working' signal bleeds money, and overtrading makes it worse.; Data-mined patterns that do not exist out of sample: with a self-built discovery process the trader will find 'winners' that fail like the 60 of 61 in the hold-out, then keep re-mining after losses (researcher degrees of freedom), and regime shift (2026 war, post-Nov-2024 rules) adds more decay.; Behavioural blow-up: a fear-driven switch from investing to daily bull/bear F&O trading leads to loss chasing, size escalation, expiry-day option gambling and burning through the capital the investing portfolio took years to build, turning a risk-reduction motive into a higher-risk activity.

Must-have conditions:
- At least 6 months and 200 or more trades of forward paper or shadow trading on a frozen, pre-registered rule set (hypothesis count logged, no edits mid-test), using the real broker API with limit-order fills, showing net expectancy of at least +3 bps per trade after 6.9 bps costs with t above 3 (or DSR of at least 0.95).
- Ring-fenced risk capital of no more than 5-10% of net worth, money the family can lose entirely; the long-term portfolio stays untouched or separately hedged; defined-risk instruments only (long options or spreads); no selling naked options or holding positions overnight.
- Hard, automated limits agreed in writing in advance: max trades per day, max daily loss, max monthly drawdown, and a kill-switch; if live net expectancy is negative after the first 60 trades or drawdown hits the preset cap, trading stops and is reviewed for a cooling-off period.
- A cost-aware entry filter, so a trade is only taken when expected move is several times the ~7 bps round-trip cost, with realistic slippage modelled; Nifty only until Sensex is shown to add independent edge.
- Compliance and tax readiness before the first order: SEBI-compliant broker algo set-up (static IP, 2FA), self-use only (no selling signals), a CA engaged for ITR-3 and audit thresholds, and a complete trade journal.

Best variant: Do not replace the investing book with an intraday system. Keep a smaller core, address the macro worry through allocation and cheap hedges (trim equity exposure, add liquid funds/gold, buy index put spreads on Nifty for tail events), and run any systematic idea as a single simple pre-registered Nifty rule in paper trading for 6 months, treating it as an education budget and not an income plan. If real money is ever added, make it one lot, defined-risk options only.

Would change verdict: A pre-registered forward test on 2024-2026 data (post Nov-2024 regime and the 2026 war period) with at least 200 live-fill trades, showing net expectancy of at least +3 bps per trade after full current costs, t above 3 and DSR of at least 0.95, would move this to PILOT_ONLY. Demonstrated defined-risk option or spread execution that cuts all-in cost below ~2 bps with the same edge would also change my view.

Disagreements with the dossier:
- The 'where risk arrives' section is framed as favourable to intraday, but it does not state that the overnight leg also carries almost all of the return (+374% vs -232% intraday). Staying flat overnight removes gap risk and the equity risk premium together; the dossier lacks the honest counterfactual of hedged or reduced investing versus intraday trading.
- The 66%-of-variance-from-gap figure for 2026 and the 18 shock-day sample (9 of 15 rebounded) are small, war-regime-specific samples; they are suggestive, not evidence of a tradable shock-day rebound, and should not support a bull/bear intraday thesis.
- Missing: the trader's existing investing results and tax position. Investment gains are STCG/LTCG, while F&O is business income at slab rates with audit/compliance costs; this tax and compliance drag is a further hurdle on the intraday side. Also missing are capital size versus lot size (Rs 1.67 lakh margin per futures lot, 65-unit lots), risk of ruin for a typical retail account, and screen time and lifestyle costs.
- Options execution is not backtested, yet options are the most likely retail vehicle. The Rs 70 round-trip figure understates the real cost for option buyers (bid-ask spread, IV crush, theta, expiry-day gamma), and the dossier does not flag this asymmetry.
- The hold-out ends Mar 2024 and uses index prices, not futures prices. The 'short-side continuation' structure that survived directionally (Spearman 0.52) may be a 2015-2024 drift artefact; it is a hypothesis to forward-test, not a result to build on.
- The dossier treats Sensex as a combination question, but Sensex derivatives liquidity, BSE spreads and weekly-option depth are likely worse than Nifty's; with no Sensex intraday data, the combined-index claim is untestable and should default to Nifty only.
- The dossier does not note the mismatch between the stated trigger (war, El Nino) and the market's current pricing (VIX 12-15 in late Sep/1 Oct 2026). Moving to intraday on macro fear while implied volatility is calm is a narrative-driven decision, which is a behavioural red flag in its own right.

### compliance (SEBI market-structure & compliance specialist): NO_GO

Top failure modes: Cost bleed with no edge: a 6.9 bps round trip (Rs 874/lot, ~8% of the median daily range) against gross intraday edges of 0-6 bps produces a steady negative drift of about -5 bps per trade out of sample; at 1-2 trades/day on 2 lots this is tens of thousands of rupees a month in charges alone before any market loss.; Deploying noise: mined patterns that look strong in-sample (t up to 3.27) are indistinguishable from luck (Reality Check p 0.97, DSR 0.08) and revert out of sample (median +16.8 to -5.8 bps); the data also ends Mar 2024, before the Nov-2024 F&O curbs, the Tuesday expiry move, the Apr-2026 STT hike, the closing auction and the 2026 war regime, so live behaviour will differ from the backtest.; Leverage plus shock-day whipsaw plus rule drift: ~8.7x notional leverage, short-biased patterns run over on gap-down-then-rebound days (9 of 15 negative-gap event days), V-reversal sessions, API/broker outages mid-position, and SEBI/Budget changes (further STT, lot, expiry-settlement or margin changes) that can erase a thin edge overnight.

Must-have conditions:
- Replace open-ended mining with a pre-registered set of at most ~10 economically motivated hypotheses, tested on Nifty FUTURES prices (not spot) including 2024-2026 data, charged at today's full cost model with realistic slippage, and passing Reality Check/SPA FWER p < 0.05, Deflated Sharpe >= 0.95 and PBO < 0.05 on an untouched hold-out.
- At least 6 months of forward paper trading through the actual broker API (limit orders, real quotes, logged fills and rejects) showing net-positive P&L after all charges with t > 2 versus zero before a single live lot.
- Live only at 1 lot per Rs 10 lakh of allocated capital, allocated capital capped at 10-15% of net worth, hard daily loss limit (~1% of allocated capital), max 2 round trips per day, auto-flat by 15:15, and an automatic kill switch on data/API failure or margin shortfall.
- Full compliance baseline documented before go-live: own/family account only, < 10 orders/sec, whitelisted static IP, daily OAuth+TOTP login, algo tagging as the broker requires, no sharing or selling of signals (else SEBI RA registration), and ITR-3 bookkeeping with turnover tracking for tax-audit thresholds.
- Sensex leg permitted only in instruments with demonstrated liquidity at the intended entry/exit times (spread and depth checks logged; Sensex futures excluded unless spread <= 2 ticks), and only after the strategy has been validated on actual Sensex intraday data; otherwise trade Nifty only.

Best variant: Do not convert the portfolio into a day-trading operation. Keep the long-horizon equity book (where the +374% overnight return has come from) and hedge the geopolitical gap risk directly and cheaply: cut beta to a comfortable level, hold more cash, or buy monthly Nifty puts / a collar sized to the drawdown the trader cannot stomach. If intraday work is still wanted, run it as an unfunded research project: 3-5 pre-registered event-conditioned hypotheses (e.g. behaviour after >= 2% shock gaps) executed in ATM Nifty options to cut statutory cost, forward-tested on paper for 6 months before any capital.

Would change verdict: A pre-registered strategy on Nifty futures prices covering 2024-2026 that stays net-positive after the 6.9 bps base cost with Reality Check FWER p < 0.05 and Deflated Sharpe >= 0.95, confirmed by 6 months of logged live-API paper fills. Alternatively a demonstrated all-in cost (including real option spreads and theta) below ~3 bps per round trip while gross edge stays >= 5 bps.

Disagreements with the dossier:
- Sensex liquidity asymmetry is missing: BSE index-derivative volume is overwhelmingly in Sensex options and concentrated around the Thursday expiry; Sensex futures are thin and off-expiry option spreads are wider than Nifty's. 'Nifty and Sensex combined (index futures/options)' is therefore not a symmetric two-leg system, and the 1-2% diversification figure overstates practical value because the Sensex leg will carry higher slippage than the 1 point/side assumed for Nifty.
- Options execution is the one cost lever the dossier leaves unquantified: STT on options is charged on premium, not notional, so statutory charges per unit of delta exposure are several times lower than futures (the ~Rs 70 figure), but the dossier's 'ATM weekly option round trip ~Rs 70' omits bid-ask spread, theta over a multi-hour hold and gamma on expiry days. The net effect on an intraday directional strategy is untested and should not be assumed in either direction.
- Backtests use index spot prices while the trade is in futures: futures basis moves, roll days, and the fact that futures trade continuously from 09:15 while the spot opening print is a stale-constituent artefact mean opening-window entries and the 15:15 exits will fill differently from the spot series; results near the open should be treated as more uncertain than the dossier implies.
- The closing auction session (live since 3 Aug 2026 per the dossier) and the pending expiry-settlement-methodology change are noted but not analysed; several top mined patterns exit at 15:15 and the whole last-30-minute literature is about pre-CAS microstructure, so late-session behaviour in the backtest may not represent today's market.
- Two regulatory details should be verified before being relied on: SEBI's retail-algo circular (Feb 2025) came into force in 2025 as far as I know, so 'in force for all brokers since 1 Apr 2026' may refer to a later broker-level milestone; and 'limit orders only for API orders' reads like a broker/exchange implementation standard rather than a SEBI-level mandate. Neither changes the verdict, but the operational design (marketable limit orders for time-based exits) should follow the broker's actual rulebook.
- Operational cost items absent from the cost model and risk discussion: peak-margin shortfall penalties, broker auto-square-off charges and RMS cut-off times (~15:20), API/data-feed subscription fees, and intraday MTM calls; individually small, but for a 1-2 lot trader they are the same order of magnitude as the hoped-for edge.

### macro (Global macro & geopolitical strategist): NO_GO

Top failure modes: Cost bleed: gross edges of 1-5 bps against a round trip of about 6.9 bps (8.6 bps under stress), at low 2026 VIX and narrow ranges, wear the capital down steadily, and overtrading speeds this up.; Data-snooped patterns: the trader's own search will surface t > 2 patterns that are noise (61 found vs 17.7 in the placebo; the best is indistinguishable from luck) and that decay to negative out of sample, especially because the backtest data ends before the 2024-2026 regime.; Headline whipsaw with leverage: a system that leans short gets squeezed by intraday ceasefire or peace headlines and V-reversals, limit-only API stops fail to fill in fast markets, and ~9x leverage per minimum lot turns a few bad sessions into a large drawdown. Meanwhile the long-term book, liquidated near a -13% low, misses any recovery.

Must-have conditions:
- A strategy written down before testing and validated on Nifty futures minute data (not spot) from after November 2024, including the 2026 war regime. It must be net positive at the 8.6 bps stress cost with Reality Check/SPA p < 0.05, Deflated Sharpe >= 0.95 and PBO <= 0.05.
- At least 3-6 months of shadow trading through the SEBI-compliant API with logged limit-order fills, showing realised slippage no worse than assumed and positive net P&L, before any real capital is used.
- Ring-fenced risk capital of at most 10% of investable wealth, a maximum of 1 Nifty lot, a daily loss cap of about 1% of the trading sleeve, flat by 15:20, and a hard kill switch at a 15% drawdown of the sleeve, with no averaging down.
- A no-trade calendar (RBI on 7 October, Fed, CPI, OPEC, expiry days, announced ultimatum or ceasefire deadlines), with Nifty only and no Sensex until an edge is proven.
- The long-term portfolio decision (resize or hedge) is made separately, on macro grounds, and is not financed by liquidating holdings for this experiment.

Best variant: Keep a resized core of long-horizon holdings and hedge the geopolitical tail directly. India VIX at 12-15 makes Nifty puts and put spreads cheap. Use a partial short-futures overlay around known event windows and tilt sectors along the oil, rupee and monsoon channels (exporters over oil-sensitive importers). If the trader wants something systematic, run it at a daily or weekly horizon (trend and drawdown-control overlay with VIX and FII-flow filters), where costs are a small fraction of the move.

Would change verdict: This would change if a strategy written down before testing, run on post-2024 Nifty futures minute data that includes the 2026 war regime, cleared stress costs with family-wise significance (RC/SPA p < 0.05, DSR >= 0.95), and then held up in 6 months of live shadow trading with realised slippage. Evidence that cheap tail hedges were unavailable or ineffective for the core book would also strengthen the case for going flat overnight.

Disagreements with the dossier:
- The dossier never tests the trader's premise against simpler ways of managing macro risk: reducing gross exposure, protective puts or collars, a futures hedge overlay, or sector rotation along the oil, rupee and monsoon channels. The proposal mixes up risk reduction with alpha generation.
- It highlights that 66% of 2026 variance came from gaps but does not point out that the 2026 drawdown itself came mostly intraday (overnight -0.8% vs intraday -11.3% cumulative). Being flat overnight would not have protected a long-only holder this year; most of the gap variance was noise that mean-reverted (9 of 15 negative-gap shock days rebounded).
- The overnight/intraday split is computed on the spot index, and the stale 09:15 opening print moves return from the intraday side to the overnight side. The overnight premium (+374%) and the intraday loss (-232%) are therefore overstated in size; a futures-based split is needed.
- Calling the persistent short-side bias 'structure' is too strong without checking whether those patterns beat a naive 'short every day 09:30-15:15' benchmark or are just beta to FII-selling regimes (2015-2020 and 2026). That flow is better captured at a daily horizon.
- It leaves out that Sensex futures on BSE are illiquid compared with Nifty futures (BSE volume is mostly options), so a combined futures plan carries much higher slippage on the Sensex leg; correlation measured from an ETF proxy does not capture this.
- It underplays geopolitical risk during Indian trading hours: Middle East events and ceasefire or ultimatum headlines often arrive during IST hours, so intraday trading does not remove the tail, and a system that leans short has a large upside-squeeze tail.
- It does not say that selling long-term holdings near a -13% YTD low crystallises losses and capital-gains tax effects and gives up the historical post-shock recovery of Indian indices (Balakot, Ukraine 2022 and the 2025 tariff shock all retraced within months).
- The Fed 'hike' to 3.75-4.00% on 16 Sep 2026 is a sharp reversal of the 2025 easing path and a key driver of FII flows and INR at 96. It should be source-checked, because the macro framing depends on it.

### quant (Skeptical quant researcher): NO_GO

Top failure modes: Cost drag: a round-trip cost of ~6.9 bps (mostly STT) exceeds every gross intraday edge measured out of sample (top-50 mined +1.8 bps; best literature rule +4.3 bps), so the system bleeds slowly but almost certainly, and that shows up only after months of noise-dominated P&L.; Data-mining and regime fragility: the patterns found are noise (best t 3.27 is below the noise max-t; 61 discoveries end with a median of -5.8 bps in the hold-out). The persistent 'short continuation' bias is a small, regime-dependent post-09:30 drift that may flip. The trader will keep re-mining after each drawdown, and none of that iterative snooping is counted in any correction.; Execution and behaviour under stress: limit-only API orders miss stops and fills on headline spikes. Then comes the slide into weekly options (theta/VRP, Tue+Thu expiry gamma), more leverage and discretionary overrides, the path behind the 88-93% retail F&O loss rates.

Must-have conditions:
- At most ~5-10 economically motivated hypotheses are pre-registered and frozen before testing, with every trial logged. Each must pass a family-wise test (Romano-Wolf/SPA at 5%), reach a Deflated Sharpe of at least 0.95 on the honest trial count, and show PBO below 0.1.
- Validation on actual Nifty (and Sensex, if used) futures/options 1-minute data from Apr 2024 to Sep 2026, never used in design, at current costs: a net edge with t>2 and gross edge per trade at least 2x round-trip cost (~14 bps or more).
- 3-6 months of shadow/paper trading through the real broker API (limit-only orders, static IP, daily login), measuring realised slippage, fill rate and missed stops, with live per-trade results inside the backtest's confidence band before any capital is committed.
- Hard risk limits enforced in code and at the broker: 1 lot per index at most (or under 0.5% of capital at risk per trade), daily loss stop around 1%, kill switch at about 5% drawdown or if the live mean falls below cost breakeven after a pre-set trade count, flat by 15:15, no option selling, no expiry-day trades at first.
- Risk capital capped at about 10% of investable assets or less, with the core portfolio's geopolitical risk handled separately by de-risking or hedging, not by this system.

Best variant: Address the geopolitical risk where it lives, at the portfolio level. Keep a reduced core long-horizon allocation (the data say returns accrue overnight/long-horizon) and cap gap losses with index put spreads or collars or partial short Nifty futures hedges in high-risk windows, plus diversifiers (gold, short-duration debt). If intraday research continues, limit it to one pre-registered, low-frequency, volatility-conditioned Nifty-futures-only hypothesis, paper-traded on post-2024 data.

Would change verdict: A strategy pre-registered before seeing Apr 2024-Sep 2026 Nifty futures minute data that shows net-of-current-cost t>3 with gross edge at least 2x cost on that data, followed by 6 months of live paper trading with limit-only fills close to the backtest. That would move the verdict to PILOT_ONLY at small size.

Disagreements with the dossier:
- The Reality Check p=0.97 is probably too conservative, so it should not be the headline number. Bootstrap means are studentised with the full-sample SE while resamples are admitted with as few as half the trades, which inflates the null max-t: bootstrap median 3.9 against a placebo max-t p95 of 3.38. The placebo percentile (0.91, i.e. family-wise p of about 0.09 for the best pattern) is the better-calibrated figure. The conclusion is unchanged.
- The DSR (0.08) and MinBTL (16.6 years) use the nominal 24,488 trials. The candidates are highly correlated (nested windows, overlapping conditions, long/short mirrors), so the effective number of trials is far smaller and these figures overstate severity. The hold-out decay is the stronger evidence.
- The Spearman 0.52 IS/OOS persistence is mostly one common factor, the negative post-09:30 intraday drift that favours shorts, not many independent persistent patterns. That drift is ~2-3 bps/day, far below cost, and regime-dependent.
- The overnight +374% vs intraday -232% decomposition is heavily contaminated by the untradeable 09:15 open print (-6.8 bps/day, about -95 log-% over 2015-20 alone), so it overstates the overnight/intraday asymmetry. Also, in 2026 YTD the mean loss came intraday (-11.3%), not overnight (-0.8%), so being flat overnight cuts gap variance but would not have avoided this year's drawdown for a long holder.
- The evidence comes from index prices, not futures, and ends Mar 2024. The live regime (post-Nov-2024 F&O changes, Tuesday expiries, STT hike, the war period) has no intraday test at all. The in-sample includes the 2020 COVID crash, which likely drives the short-continuation patterns (best pattern: 63 trades, kurtosis 4.1), and there is no leave-crash-out robustness check.
- The ~Rs 70 (1.1 point) options round trip understates the true cost of options execution: it leaves out bid-ask spread, adverse selection under limit-only orders, and the theta/variance-risk-premium drag on buyers. Options are untested and should not be read as a way around futures costs.
- The 18 geopolitical event days are picked in hindsight. The 9/15 intraday rebounds after negative gaps contradict the mined short-continuation patterns, and the sample is far too small to trade on.
- Missing: the obvious counterfactual of hedging or de-risking the existing portfolio, the trader's capital, time budget and size relative to lot size, and Sensex derivatives liquidity/spread data.

### risk (Prop desk head of risk): NO_GO

Top failure modes: No net-of-cost edge: gross edges of 0-4 bps per trade cannot clear a 6.9 bps round trip (8.6 bps under stress), so the account bleeds steadily through STT, brokerage and slippage while the trader keeps refitting patterns that are noise (hold-out 1 of 61 survived).; Overfit pattern discovery redeployed into a different regime: parameters mined on 2015-2024 data, then traded in a 2026 war/El Nino regime with a 66% overnight variance share, producing whipsaw losses and drawdown that triggers behavioural overrides (revenge trading, size-up, averaging).; Execution and sizing failures: limit-only API orders that do not fill on stop-throughs or gap-through opens, doubled Nifty plus Sensex exposure on 0.95-correlated signals, and futures leverage with one-lot margin of about Rs 1.67 lakh, so one bad session can breach a retail drawdown limit.

Must-have conditions:
- A single pre-registered hypothesis (or a very small frozen set), tested on genuinely out-of-sample data from Apr 2024 onward with real futures/options bid-ask and post-Apr-2026 costs, showing net expectancy of at least about +3 bps per trade after the 6.9 bps base cost and still positive at 8.6 bps stress, with White RC or SPA p below 0.05 and Deflated Sharpe at least 0.95.
- At least 60 trading sessions of forward paper or minimum-size trading that models limit-only fills (including missed fills and stop-limit failures), with realised slippage no worse than assumed and results inside the backtest confidence band.
- Ring-fenced risk capital of no more than 5-10% of net worth, max loss per day of 0.5-1% of that capital, no overnight positions (auto square-off by about 15:15), defined-risk structures (long options or spreads) preferred over naked futures, and a hard kill-switch at a pre-set weekly and monthly drawdown with no discretionary override.
- Nifty only until Sensex intraday data and BSE liquidity are shown to add value; no doubling of the same signal across both indices.
- Operational readiness confirmed: static IP, daily login automation with alerts, position reconciliation, SEBI retail-algo compliance for self-use only, and ITR-3 or audit set-up for F&O business income.

Best variant: Do not convert the portfolio into a discovery-driven day-trading book; address the macro worry at portfolio level by cutting size and buying defined-risk index puts or put spreads on the existing holdings (low VIX of 12-15 makes protection cheap). If the trader still wants intraday, paper trade one pre-registered Nifty-only rule (e.g. ORB-30 with a stop or short-continuation after a down open), expressed with long options for defined risk, at minimum size for at least three months with explicit kill criteria.

Would change verdict: A frozen rule that shows positive net expectancy of roughly 3+ bps per trade on post-Apr-2024 futures/options data with real spreads and Apr-2026 costs, passes RC/SPA and DSR, and then holds up over about 60 forward sessions with realised fills at or better than modelled would move me to PILOT_ONLY or CONDITIONAL_GO.

Disagreements with the dossier:
- The dossier tests an index-price proxy with fixed-time exits and 1 point of slippage per side; it does not model limit-only fill risk (missed winners, stop-limit failures), which under the SEBI API rules is a real hidden cost and a tail-risk issue, not just a friction.
- The overnight-versus-intraday result (+374% overnight, -232% intraday) is presented as a risk-location fact, but the practical implication is that flat-overnight trading structurally surrenders the index return premium; part of the intraday drag is the untradeable 09:15 print, so the case against intraday long exposure is partly overstated, but the case for any edge is not improved.
- The thesis itself is not tested against simpler alternatives (reduce size, hedge with index puts, hold cash); the dossier evaluates intraday pattern trading on its merits but not whether it answers the stated macro risk better than hedging, which is the first question a risk desk would ask.
- The hold-out (2021-2024) is mostly a bull-market regime and the data end Mar 2024, so the short-side bias that persists (95% of t>2 discoveries are shorts) may behave differently in the 2026 bear/war regime; the dossier flags the limitation but does not say that regime-conditional shorts remain the single open hypothesis worth pre-registering and testing forward.
- The shock-day sample (18 days, 15 negative gaps, 9 rebounds) is too small to support any inference; no risk-of-ruin, drawdown or Monte Carlo sizing analysis is provided for a retail account with one-lot margin of about Rs 1.67 lakh.
- Options-based execution is not backtested, yet it is the most likely retail implementation (cheap charges, defined risk); spread, theta and implied-vs-realised vol costs may exceed the apparent Rs 70 round-trip charge, so the 'about 1.1 option points' cost figure should not be read as evidence of feasibility.
