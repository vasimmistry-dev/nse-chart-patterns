# nse-chart-patterns

[![tests](https://github.com/vasimmistry-dev/nse-chart-patterns/actions/workflows/tests.yml/badge.svg)](https://github.com/vasimmistry-dev/nse-chart-patterns/actions/workflows/tests.yml)
![python](https://img.shields.io/badge/python-3.9%2B-blue)
![license](https://img.shields.io/badge/license-MIT-green)

Transparent, rule-based **candlestick and chart pattern detection** for daily OHLCV data, in pure Python with **zero dependencies**.

It reads plain `Date,Open,High,Low,Close,Volume` CSVs and NSE-style files (`DATE1`, `OPEN_PRICE`, `TTL_TRD_QNTY`, ...) directly. The examples use NSE (India) stocks, but the rules work for any market.

This library was extracted from the pattern logic behind features like *Chart patterns* and *Setup lab* on [TickerKhoj](https://tickerkhoj.com), a free Indian stock analysis site. It is released on its own so the rules can be read, tested and improved in the open.

## Why

Most pattern scanners are black boxes: they tell you "bullish engulfing on INFY" but not *which* rule fired or how close the call was. Here:

- **Every rule is written down** below, in the docstrings and in tests that build bar series by hand to show where each pattern fires and where it does not.
- **No look-ahead.** A signal dated on bar *t* uses only bars up to *t*. Swing points are dated on the bar that confirms them, not on the pivot bar.
- **Every signal shows its numbers.** Each one has a `details` dict, e.g. the neckline of a double top or the volume ratio of a breakout.
- **Pure stdlib.** It runs on Python 3.9+ anywhere, with no NumPy or pandas install.

## Install

```bash
pip install git+https://github.com/vasimmistry-dev/nse-chart-patterns.git
# or, from a clone:
pip install -e ".[test]"
```

## CLI

```bash
chart-patterns scan examples/synthetic_nse_daily.csv --last 5
chart-patterns scan data.csv --last 5 --json            # machine-readable
chart-patterns scan data.csv --patterns double_top,double_bottom
chart-patterns levels data.csv                           # support / resistance
chart-patterns backtest data.csv --horizon 10            # historical stats per pattern
```

Output on the bundled **synthetic** sample file (it is generated data, not a real stock):

```
$ chart-patterns scan examples/synthetic_nse_daily.csv --last 5
320 bars, 2025-01-01 to 2026-03-24
date        pattern               dir         str  details
2026-03-18  bearish_engulfing     bearish    1.00  body_ratio=5.3051
2026-03-18  bollinger_squeeze     neutral    0.91  bandwidth=0.0204, lookback=120
2026-03-19  bollinger_squeeze     neutral    0.91  bandwidth=0.0197, lookback=120
2026-03-23  swing_low             neutral    0.28  pivot_date=2026-03-16, pivot_price=768.38

$ chart-patterns levels examples/synthetic_nse_daily.csv
Last close 783.95 on 2026-03-24
resistance     785.86  touches=2  (2026-02-17 .. 2026-03-10)
support        765.71  touches=3  (2025-11-26 .. 2026-03-16)
...
```

If a file holds several series (e.g. `EQ` and `BE`), use `--series EQ` to keep one.

## Python

```python
from nse_chart_patterns import load_csv, scan, support_resistance, forward_stats

bars = load_csv("TATAMOTORS.csv", series="EQ")   # any OHLCV CSV

for s in scan(bars, last=5):
    print(s.date, s.pattern, s.direction, round(s.strength, 2), s.details)

for lv in support_resistance(bars, tolerance=0.015):
    print(lv.kind, round(lv.price, 2), lv.touches)

# Historical statistics, NOT predictions
for st in forward_stats(bars, scan(bars), horizon=10):
    print(st.pattern, st.count, st.win_rate, st.avg_return)
```

You can also build bars without a CSV:

```python
from nse_chart_patterns import Bar, bars_from_rows, bars_from_tuples
from nse_chart_patterns.chart import detect_double_patterns

bars = bars_from_rows([{"Date": "2024-01-02", "Open": 100, "High": 102, "Low": 99, "Close": 101, "Volume": 1e5}, ...])
signals = detect_double_patterns(bars, tolerance=0.02)
```

Each `Signal` has `date`, `pattern`, `direction` (`bullish` / `bearish` / `neutral`), `strength` (0 to 1), `details` (dict) and `index` (the bar position).

> `strength` is a simple heuristic for ranking signals of the **same** pattern against each other. It is not a probability, and it should not be compared across different patterns.

## Input format

Headers are matched case-insensitively, and surrounding spaces are ignored.

| field  | accepted headers |
|--------|------------------|
| date   | `Date`, `DATE1`, `TIMESTAMP`, `TRADE_DATE` |
| open   | `Open`, `OPEN_PRICE` |
| high   | `High`, `HIGH_PRICE` |
| low    | `Low`, `LOW_PRICE` |
| close  | `Close`, `CLOSE_PRICE` |
| volume | `Volume`, `TTL_TRD_QNTY`, `TOTTRDQTY`, `TOTAL_TRADED_QUANTITY` (optional) |

- **Dates:** `2024-01-05`, `05-Jan-2024` (as in NSE archives), `05-01-2024`, `05/01/2024` and `20240105` are all accepted. Day-first is assumed for the `dd-mm-yyyy` formats.
- **Numbers:** comma grouping such as `12,34,567` is accepted.
- **Cleanup:** rows with `-` or blank prices are skipped. Rows are sorted by date, and if a date appears twice the later row wins.
- **Adjustments:** prices are used exactly as given. Adjust for splits and bonuses before scanning, or a split will look like a crash.

## Rules

Notation for one bar: `body = |close - open|`, `range = high - low`, `upper = high - max(open, close)`, `lower = min(open, close) - low`. A 5-bar *prior trend* is `close[i-1] - close[i-6]`.

### Candlesticks

| pattern | direction | rule |
|---|---|---|
| `doji` | neutral | `range > 0` and `body <= 0.1 * range` |
| `hammer` | bullish | `body >= 0.1*range`, `lower >= 2*body`, `upper <= 0.1*range`, **prior trend < 0** |
| `shooting_star` | bearish | `body >= 0.1*range`, `upper >= 2*body`, `lower <= 0.1*range`, **prior trend > 0** |
| `bullish_engulfing` | bullish | previous bar bearish, current bar bullish, `open <= prev.close`, `close >= prev.open`, `body > prev.body` (shadows ignored) |
| `bearish_engulfing` | bearish | mirror of the above |
| `morning_star` | bullish | bar 1 bearish with `body1 >= 0.5*range1`; bar 2 `body2 <= 0.3*body1` and its body top `<= close1`; bar 3 bullish and closes above the midpoint of bar 1's body |
| `evening_star` | bearish | mirror: bar 1 bullish and long; bar 2 small with body bottom `>= close1`; bar 3 bearish and closes below bar 1's body midpoint |
| `inside_bar` | neutral | `high < prev.high` and `low > prev.low` (strict) |
| `nr7` | neutral | today's range is strictly smaller than each of the previous 6 ranges |

### Chart and setup patterns

| pattern | direction | rule (defaults in brackets) |
|---|---|---|
| `52w_high_breakout` | bullish | close > highest **high** of the previous 252 bars |
| `52w_low_breakdown` | bearish | close < lowest **low** of the previous 252 bars |
| `range_breakout` | bullish | close > highest high of the previous N [20] bars **and** volume > 1.5 x the average volume of the previous 20 bars (today excluded) |
| `range_breakdown` | bearish | close < lowest low of the previous N bars with the same volume condition |
| `golden_cross` | bullish | SMA50 was `<=` SMA200 yesterday and is `>` SMA200 today |
| `death_cross` | bearish | SMA50 was `>=` SMA200 yesterday and is `<` SMA200 today |
| `swing_high` / `swing_low` | neutral | the pivot bar's high (low) is **strictly** above (below) the highs (lows) of the 5 bars on each side. The signal is dated on the **confirming** bar (pivot + 5) |
| `double_top` | bearish | two **consecutive** swing highs within `tolerance` [3%] of each other (`|P2-P1| / max(P1,P2)`), 10 to 120 bars apart, with the lowest low between them (the neckline) at least 3% below the lower peak. It fires on the first **close below the neckline** within 20 bars after P2 is confirmed, and is cancelled if price trades above both peaks first |
| `double_bottom` | bullish | mirror: two swing lows, with confirmation on a close above the highest high between them |
| `bollinger_squeeze` | neutral | Bollinger bandwidth `(upper - lower) / middle` (20, 2 sigma, population SD) is strictly below every other bandwidth value of the last 120 bars |

### Support and resistance (`levels`)

1. Collect the swing highs and lows (5/5 pivots) from the last 250 bars.
2. Sort the pivot prices. Walk through them, adding each price to the current cluster if it lies within `tolerance` [1.5%] of the cluster's mean, and otherwise starting a new cluster.
3. Each cluster with at least `min_touches` [2] pivots becomes a level at its mean price. A level is *support* if it is below the last close and *resistance* otherwise. Levels are listed nearest first.

### Indicators (`nse_chart_patterns.indicators`)

`sma`, `ema` (alpha = 2/(n+1), seeded with the SMA), `rsi` (Wilder smoothing, seeded with simple averages), `true_range`, `atr` (Wilder), `bollinger` (population SD), `bandwidth`, `volume_sma`. Each returns a list the same length as its input, with `None` until enough data exists.

### Back-test helper

`forward_stats(bars, signals, horizon)` measures returns from the close of each signal bar to the close `horizon` bars later.

- **win_rate:** the share of signals that moved in the signal's direction (`> 0` for bullish, `< 0` for bearish, `> 0` for neutral).
- **Skipped signals:** signals without `horizon` bars of later data are left out.
- **What it ignores:** costs, slippage, gaps, position sizing and survivorship bias.

These are **historical statistics only, not predictions**. Small counts mean noisy numbers.

## Limitations

- **Simplified rules.** The rules are simple on purpose. Textbook definitions vary, so check that they match yours before relying on a scan. Thresholds can be changed through function parameters, not the CLI.
- **Look-alike shapes.** Hammer and shooting-star shapes depend on the 5-bar trend filter. Hanging man and inverted hammer are not detected separately.
- **Daily bars.** The data is assumed to be daily. Intraday bars would also work, but the "52-week" lookback then means 252 bars rather than 52 weeks.
- **Pure Python speed.** Scanning a few thousand bars takes milliseconds. Scanning the whole market every minute is not the goal.
- **No data download.** You provide the CSV. Respect the terms of whichever data source you use.

## Development

```bash
pip install -e ".[test]"
pytest -q
```

The tests in `tests/` build small bar series by hand (see `tests/conftest.py`). Each pattern has cases that must fire and near misses that must not.

## Disclaimer

This project is for **educational and research purposes only**. It is **not investment advice** and not a recommendation to buy or sell any security. Patterns and historical statistics do not predict future prices. This project is **not affiliated with, endorsed by or connected to the National Stock Exchange of India (NSE)**. "NSE" is used only to describe compatible data formats. Do your own research or consult a SEBI-registered adviser.

## License

MIT © 2026 Vasim Mistry
