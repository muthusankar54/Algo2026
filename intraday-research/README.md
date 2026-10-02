# patternlab: intraday pattern discovery and validation for Nifty

A research harness for answering one question honestly: *does a data-mined intraday pattern on
Nifty/Sensex have an edge that survives today's costs and proper statistics?*

The findings and recommendations are in [REPORT.md](REPORT.md).

## Quick start

```bash
cd intraday-research
pip install -r requirements.txt
./scripts/fetch_data.sh                 # public datasets -> data/ (git-ignored)
python -m pytest -q                     # includes look-ahead tests
python -m patternlab.run_all            # ~30 s: discovery, Reality Check, placebo, PBO, hold-out, regimes
python -m patternlab.charts             # results/chart_*.png
python ai_evals/aggregate.py            # summarise the AI-judge panel
```

## What it does

| Module | Purpose |
|---|---|
| `data.py` | Cleans 1-minute bars into a (days x 375) matrix; column k = bar starting 09:15 + k min |
| `features.py` | ~55 point-in-time "pattern atoms" (gap, prior day, VIX regime, expiry, opening range, gap fill, first candle, range, TWAP, momentum) |
| `discovery.py` | Scores every 1-2 atom conjunction x 11 entry/exit windows x long/short (~24k patterns) in one matrix product; White's Reality Check with bootstrap day weights |
| `stats.py` | Holm, Benjamini-Hochberg, stationary bootstrap, Deflated Sharpe, MinBTL, PBO via CSCV |
| `hypotheses.py` | Pre-registered literature strategies: intraday momentum, opening-range breakout, gap fade/go, expiry days |
| `regime.py` | Daily 2012-2026: overnight vs intraday returns, geopolitical event study, Nifty-Sensex correlation |
| `evals.py` | The eval gates every strategy must pass before live money |
| `costs.py` | Round-trip cost model with 2026 statutory rates (STT 0.05% on futures sells) |

## Testing your own idea

1. Write the rule down **before** looking at data (entry time, exit, condition, direction).
2. Add it to `hypotheses.py` (or as a predicate in `features.py`) and count it as a trial.
3. Run `run_all` and read its scorecard in `results/eval_scorecards.csv`. All gates must pass.
4. If it passes, paper trade it on live data for at least 3 months before risking capital.

To use newer data (2024-2026 minute bars from your broker's historical API), export a CSV with
columns `Date (DD-MM-YYYY), Time (HH:MM:SS), Open, High, Low, Close` and point
`PATTERNLAB_DATA` at its folder, named `nifty50_1min.csv`.

## Data sources

- Nifty 50 1-minute bars, Jan 2015 - Mar 2024: github.com/sandeepkapri/Nifty50-Minute-Data (MIT)
- NSE daily Nifty 50, India VIX, Sensex/Nifty ETFs to Sep 2026: github.com/BennyThadikaran/eod2_data
