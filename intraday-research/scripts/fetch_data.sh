#!/usr/bin/env bash
# Downloads the public datasets used by patternlab into intraday-research/data/.
#   1. Nifty 50 1-minute bars, 2015-01-09 .. 2024-03-27 (MIT licence)
#      https://github.com/sandeepkapri/Nifty50-Minute-Data
#   2. NSE end-of-day data (Nifty 50, India VIX, Sensex ETF ...), updated weekly
#      https://github.com/BennyThadikaran/eod2_data
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DATA="$ROOT/data"
CACHE="$DATA/.cache"
mkdir -p "$CACHE"

if [ ! -d "$CACHE/nifty_min" ]; then
  git clone --depth 1 https://github.com/sandeepkapri/Nifty50-Minute-Data "$CACHE/nifty_min"
fi
cp "$CACHE/nifty_min/nifty50_candlestick_data.csv" "$DATA/nifty50_1min.csv"

if [ ! -d "$CACHE/eod2" ]; then
  git clone --depth 1 --filter=blob:none --no-checkout https://github.com/BennyThadikaran/eod2_data "$CACHE/eod2"
fi
(
  cd "$CACHE/eod2"
  git fetch --depth 1 origin main
  git checkout origin/main -- "daily/nifty 50.csv" "daily/india vix.csv" "daily/nifty bank.csv" \
    "daily/sensexietf.csv" "daily/niftybees.csv"
)
for f in "nifty 50" "india vix" "nifty bank" "sensexietf" "niftybees"; do
  cp "$CACHE/eod2/daily/$f.csv" "$DATA/$(echo "$f" | tr ' ' '_')_daily.csv"
done

echo "Data ready in $DATA"
ls -la "$DATA"
