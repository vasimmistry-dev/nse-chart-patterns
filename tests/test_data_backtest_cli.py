import datetime as dt
import io
import json
import os

import pytest

from nse_chart_patterns import Signal, bars_from_rows, forward_return, forward_stats, load_csv, scan
from nse_chart_patterns.cli import main
from nse_chart_patterns.data import bars_from_tuples as mk
from nse_chart_patterns.data import parse_date

EXAMPLE = os.path.join(os.path.dirname(__file__), "..", "examples", "synthetic_nse_daily.csv")

NSE_CSV = """SYMBOL, SERIES, DATE1, PREV_CLOSE, OPEN_PRICE, HIGH_PRICE, LOW_PRICE, CLOSE_PRICE, TTL_TRD_QNTY
DEMO,EQ,03-Jan-2024,100.00,"1,001.50","1,010.00",995.00,"1,005.25","12,34,567"
DEMO,BE,02-Jan-2024,99.00,1.00,1.00,1.00,1.00,10
DEMO,EQ,02-Jan-2024,99.00,990.00,1002.00,985.00,1000.00,1000
DEMO,EQ,04-Jan-2024,100.00,-,-,-,-,0
"""


# ------------------------------------------------------------------ loading

def test_load_nse_style_csv_with_padded_headers():
    bars = load_csv(io.StringIO(NSE_CSV), series="EQ")
    assert [b.date for b in bars] == [dt.date(2024, 1, 2), dt.date(2024, 1, 3)]  # sorted, "-" row dropped
    assert bars[1].open == 1001.5 and bars[1].close == 1005.25
    assert bars[1].volume == 1234567  # Indian digit grouping


def test_series_filter_off_keeps_last_duplicate():
    bars = load_csv(io.StringIO(NSE_CSV))
    assert bars[0].close == 1000.0  # EQ row after BE row for same date wins


def test_standard_headers_and_missing_volume():
    rows = [{"Date": "2024-01-02", "Open": "1", "High": "2", "Low": "0.5", "Close": "1.5"}]
    bars = bars_from_rows(rows)
    assert bars[0].volume == 0.0 and bars[0].high == 2.0


def test_missing_required_column():
    with pytest.raises(ValueError, match="close"):
        bars_from_rows([{"Date": "2024-01-02", "Open": 1, "High": 2, "Low": 0}])


@pytest.mark.parametrize("text", ["2024-01-05", "05-Jan-2024", "05-01-2024", "05/01/2024", "20240105"])
def test_parse_date_formats(text):
    assert parse_date(text) == dt.date(2024, 1, 5)


def test_parse_date_rejects_garbage():
    with pytest.raises(ValueError):
        parse_date("yesterday")


def test_bars_from_tuples_skips_weekends():
    bars = mk([(1, 1, 1, 1)] * 3, start=dt.date(2024, 1, 5))  # a Friday
    assert [b.date.weekday() for b in bars] == [4, 0, 1]


def test_example_file_loads():
    bars = load_csv(EXAMPLE)
    assert len(bars) == 320
    assert all(b.low <= min(b.open, b.close) and b.high >= max(b.open, b.close) for b in bars)


# ------------------------------------------------------------------ scanner

def test_scan_filters():
    bars = load_csv(EXAMPLE)
    every = scan(bars)
    recent = scan(bars, last=5)
    assert recent and all(s.index >= len(bars) - 5 for s in recent)
    assert len(recent) < len(every)
    only = scan(bars, patterns=["doji"])
    assert only and {s.pattern for s in only} == {"doji"}
    assert [s.index for s in every] == sorted(s.index for s in every)


def test_scan_rejects_unknown_names():
    with pytest.raises(ValueError):
        scan([], detectors=["nope"])
    with pytest.raises(ValueError):
        scan([], patterns=["nope"])


# ------------------------------------------------------------------ backtest

def test_forward_return_and_stats_hand_computed():
    bars = mk([(c, c, c, c) for c in [100, 110, 121, 100, 90, 99]])
    assert forward_return(bars, 0, 2) == pytest.approx(0.21)
    assert forward_return(bars, 5, 1) is None
    d = bars[0].date
    sigs = [
        Signal(d, "x_up", "bullish", 1, index=0),   # +21%
        Signal(d, "x_up", "bullish", 1, index=2),   # 121 -> 90 = -25.6%
        Signal(d, "x_up", "bullish", 1, index=5),   # no forward data, skipped
        Signal(d, "x_down", "bearish", 1, index=1),  # 110 -> 100 = -9.09% (a "win")
    ]
    stats = {s.pattern: s for s in forward_stats(bars, sigs, horizon=2)}
    up = stats["x_up"]
    assert up.count == 2
    assert up.avg_return == pytest.approx((0.21 + (90 / 121 - 1)) / 2)
    assert up.win_rate == 0.5
    down = stats["x_down"]
    assert down.count == 1 and down.win_rate == 1.0


def test_stats_with_no_forward_data():
    bars = mk([(1, 1, 1, 1)] * 3)
    st = forward_stats(bars, [Signal(bars[2].date, "p", "neutral", 0, index=2)], horizon=5)
    assert st[0].count == 0 and st[0].win_rate is None
    with pytest.raises(ValueError):
        forward_stats(bars, [], horizon=0)


# ------------------------------------------------------------------ CLI

def test_cli_scan_json(capsys):
    assert main(["scan", EXAMPLE, "--last", "5", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert isinstance(data, list) and data
    assert set(data[0]) >= {"date", "pattern", "direction", "strength", "details"}


def test_cli_scan_text_levels_backtest(capsys):
    assert main(["scan", EXAMPLE, "--last", "5"]) == 0
    assert main(["levels", EXAMPLE]) == 0
    assert main(["levels", EXAMPLE, "--json"]) == 0
    assert main(["backtest", EXAMPLE, "--horizon", "5"]) == 0
    out = capsys.readouterr().out
    assert "Last close" in out and "Not a prediction" in out


def test_cli_missing_file(capsys):
    assert main(["scan", "does-not-exist.csv"]) == 2
    assert "error" in capsys.readouterr().err
