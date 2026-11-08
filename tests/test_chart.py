from conftest import path, trend

from nse_chart_patterns import chart
from nse_chart_patterns.data import bars_from_tuples as mk

FLAT = (100, 101, 99, 100.2, 1000)


def names(signals):
    return [s.pattern for s in signals]


# ------------------------------------------------------------------ 52-week breakout

def test_52w_breakout_default_lookback():
    bars = mk([FLAT] * 252 + [(100.5, 103, 100, 102.5, 1000)])
    sig = chart.detect_52w_breakout(bars)
    assert names(sig) == ["52w_high_breakout"]
    assert sig[0].index == 252 and sig[0].details["prior_high"] == 101


def test_52w_needs_full_lookback():
    assert chart.detect_52w_breakout(mk([FLAT] * 100 + [(100.5, 103, 100, 102.5)])) == []


def test_52w_close_must_clear_prior_high():
    bars = mk([FLAT] * 20 + [(100.5, 103, 100, 100.9)])  # intraday high above, close below
    assert chart.detect_52w_breakout(bars, lookback=20) == []


def test_52w_low_breakdown():
    bars = mk([FLAT] * 20 + [(99, 99.5, 97.5, 98)])
    assert names(chart.detect_52w_breakout(bars, lookback=20)) == ["52w_low_breakdown"]


# ------------------------------------------------------------------ range breakout with volume

BASE = [(100, 102, 98, 100.5, 1000)] * 20


def test_range_breakout_with_volume():
    sig = chart.detect_range_breakout(mk(BASE + [(101, 104, 100.5, 103.5, 2000)]))
    assert names(sig) == ["range_breakout"]
    assert sig[0].details["volume_ratio"] == 2.0
    assert abs(sig[0].strength - 2 / 3) < 1e-9


def test_range_breakout_rejected_on_low_volume():
    assert chart.detect_range_breakout(mk(BASE + [(101, 104, 100.5, 103.5, 1400)])) == []


def test_volume_spike_inside_range_is_not_breakout():
    assert chart.detect_range_breakout(mk(BASE + [(101, 101.8, 100.5, 101.5, 3000)])) == []


def test_range_breakdown():
    sig = chart.detect_range_breakout(mk(BASE + [(99, 99.5, 96.5, 97, 2000)]))
    assert names(sig) == ["range_breakdown"] and sig[0].direction == "bearish"


# ------------------------------------------------------------------ golden / death cross

def _closes(cs):
    return mk([(c, c + 0.5, c - 0.5, c) for c in cs])


def test_ma_cross_small_periods_hand_computed():
    bars = _closes([10, 10, 10, 10, 10, 9, 8, 7, 12, 14])
    sig = chart.detect_ma_cross(bars, fast=3, slow=5)
    assert [(s.pattern, s.index) for s in sig] == [("death_cross", 5), ("golden_cross", 9)]


def test_golden_cross_default_50_200():
    closes = [200 - 100 * k / 149 for k in range(150)] + [100 + 150 * k / 149 for k in range(150)]
    sig = chart.detect_ma_cross(_closes(closes))
    assert names(sig) == ["golden_cross"]


def test_no_cross_in_steady_uptrend():
    assert chart.detect_ma_cross(_closes([100 + k for k in range(260)])) == []


# ------------------------------------------------------------------ pivots / swing points

def test_find_pivots_and_swing_signal_dated_on_confirmation():
    bars = mk(path([100, 110, 100], 5))
    pivots = chart.find_pivots(bars, 5, 5)
    assert [(p.kind, p.index, p.price, p.confirmed_index) for p in pivots] == [("high", 5, 110.5, 10)]
    sig = chart.detect_swing_points(bars)
    assert names(sig) == ["swing_high"]
    assert sig[0].index == 10 and sig[0].details["pivot_date"] == bars[5].date


def test_equal_highs_are_not_pivots():
    bars = mk([(100, 101, 99, 100)] * 11)
    assert chart.find_pivots(bars, 5, 5) == []


# ------------------------------------------------------------------ double top / bottom

def test_double_top_confirmed_on_neckline_break():
    bars = mk(path([100, 110, 100, 109.5, 98], 10))
    sig = chart.detect_double_patterns(bars)
    assert names(sig) == ["double_top"]
    s = sig[0]
    assert s.index == 39  # first close below the 99.5 neckline
    assert s.details["neckline"] == 99.5
    assert s.details["first_peak"] == 110.5 and s.details["second_peak"] == 110.0


def test_double_top_rejected_when_peaks_differ_beyond_tolerance():
    assert chart.detect_double_patterns(mk(path([100, 110, 100, 120, 98], 10))) == []


def test_double_top_tolerance_parameter():
    bars = mk(path([100, 110, 100, 113, 98], 10))  # peaks ~2.6% apart
    assert chart.detect_double_patterns(bars, tolerance=0.02) == []
    assert names(chart.detect_double_patterns(bars, tolerance=0.03)) == ["double_top"]


def test_double_top_needs_neckline_break():
    assert chart.detect_double_patterns(mk(path([100, 110, 100, 109.5, 104], 10))) == []


def test_double_top_needs_depth():
    assert chart.detect_double_patterns(mk(path([100, 110, 108, 109.5, 98], 10))) == []


def test_double_bottom():
    sig = chart.detect_double_patterns(mk(path([110, 100, 110, 100.5, 112], 10)))
    assert names(sig) == ["double_bottom"]
    assert sig[0].direction == "bullish" and sig[0].index == 39


# ------------------------------------------------------------------ support / resistance

def test_support_resistance_clusters_pivots():
    bars = mk(path([100, 110, 100, 109.5, 98], 10))
    levels = chart.support_resistance(bars)
    assert len(levels) == 1
    lv = levels[0]
    assert lv.kind == "resistance" and lv.touches == 2
    assert abs(lv.price - 110.25) < 1e-9


def test_support_level_below_price():
    bars = mk(path([110, 100, 110, 100.5, 112], 10))
    levels = chart.support_resistance(bars)
    assert [(lv.kind, lv.touches) for lv in levels] == [("support", 2)]


def test_levels_min_touches_and_empty():
    bars = mk(path([100, 110, 100, 109.5, 98], 10))
    assert chart.support_resistance(bars, min_touches=3) == []
    assert chart.support_resistance([]) == []


# ------------------------------------------------------------------ Bollinger squeeze

def test_bollinger_squeeze_after_volatility_contracts():
    loud = [100 + (5 if k % 2 else -5) for k in range(60)]
    quiet = [100 + (0.1 if k % 2 else -0.1) for k in range(30)]
    sig = chart.detect_bollinger_squeeze(_closes(loud + quiet), lookback=40)
    assert sig, "expected a squeeze once the quiet regime fills the band window"
    assert all(s.index >= 60 for s in sig)
    assert all(s.pattern == "bollinger_squeeze" for s in sig)


def test_no_squeeze_when_volatility_expands():
    closes = [100 + (-1) ** k * (1 + 0.1 * k) for k in range(120)]
    assert chart.detect_bollinger_squeeze(_closes(closes), lookback=40) == []


def test_trend_helper_has_no_dojis():
    from nse_chart_patterns.candlesticks import detect_doji
    assert detect_doji(mk(trend(100, 120, 20))) == []
