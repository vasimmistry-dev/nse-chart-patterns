from conftest import trend

from nse_chart_patterns import candlesticks as cs
from nse_chart_patterns.data import bars_from_tuples as mk


def names(signals):
    return [s.pattern for s in signals]


# ------------------------------------------------------------------ doji

def test_doji_fires_on_tiny_body():
    sig = cs.detect_doji(mk([(100, 102, 98, 100.1)]))
    assert names(sig) == ["doji"]
    assert sig[0].direction == "neutral"
    assert 0 < sig[0].strength <= 1


def test_doji_not_on_normal_body_or_zero_range():
    assert cs.detect_doji(mk([(100, 102, 98, 101)])) == []  # body 25% of range
    assert cs.detect_doji(mk([(100, 100, 100, 100)])) == []  # no range at all


# ------------------------------------------------------------------ hammer / shooting star

HAMMER = (99.0, 99.6, 97.0, 99.5)        # body .5, lower 2.0, upper .1, range 2.6
SHOOTING = (100.5, 102.5, 99.9, 100.0)   # body .5, upper 2.0, lower .1, range 2.6


def test_hammer_after_downtrend():
    bars = mk(trend(110, 100, 6) + [HAMMER])
    sig = cs.detect_hammer(bars)
    assert names(sig) == ["hammer"]
    assert sig[0].index == 6 and sig[0].direction == "bullish"


def test_hammer_shape_after_uptrend_is_not_a_hammer():
    assert cs.detect_hammer(mk(trend(90, 100, 6) + [HAMMER])) == []


def test_hammer_needs_small_upper_shadow():
    bad = (99.0, 100.5, 97.0, 99.5)  # upper shadow 1.0 > 10% of range
    assert cs.detect_hammer(mk(trend(110, 100, 6) + [bad])) == []


def test_hammer_needs_trend_history():
    assert cs.detect_hammer(mk(trend(110, 100, 3) + [HAMMER])) == []


def test_shooting_star_after_uptrend():
    sig = cs.detect_shooting_star(mk(trend(90, 100, 6) + [SHOOTING]))
    assert names(sig) == ["shooting_star"] and sig[0].direction == "bearish"


def test_shooting_star_not_after_downtrend():
    assert cs.detect_shooting_star(mk(trend(110, 100, 6) + [SHOOTING])) == []


# ------------------------------------------------------------------ engulfing

def test_bullish_engulfing():
    sig = cs.detect_engulfing(mk([(102, 102.5, 99.5, 100), (99.5, 103.5, 99, 103)]))
    assert names(sig) == ["bullish_engulfing"]
    assert sig[0].details["body_ratio"] == 3.5 / 2


def test_bullish_engulfing_rejected_when_close_inside_prior_body():
    assert cs.detect_engulfing(mk([(102, 102.5, 99.5, 100), (99.5, 103.5, 99, 101.5)])) == []


def test_bearish_engulfing():
    sig = cs.detect_engulfing(mk([(100, 102.5, 99.5, 102), (102.5, 103, 99, 99.5)]))
    assert names(sig) == ["bearish_engulfing"]


def test_same_colour_bars_do_not_engulf():
    assert cs.detect_engulfing(mk([(100, 102.5, 99.5, 102), (99, 104, 98.5, 103.5)])) == []


# ------------------------------------------------------------------ morning / evening star

def test_morning_star():
    bars = mk([(110, 110.5, 99.5, 100), (99, 99.5, 97.5, 98.5), (99, 107, 98.5, 106)])
    sig = cs.detect_stars(bars)
    assert names(sig) == ["morning_star"]
    assert sig[0].details["first_bar_midpoint"] == 105


def test_morning_star_needs_close_above_midpoint():
    bars = mk([(110, 110.5, 99.5, 100), (99, 99.5, 97.5, 98.5), (99, 105, 98.5, 104)])
    assert cs.detect_stars(bars) == []


def test_morning_star_needs_small_middle_body():
    bars = mk([(110, 110.5, 99.5, 100), (99, 99.5, 94.5, 95), (95, 107, 94.5, 106)])
    assert cs.detect_stars(bars) == []


def test_evening_star():
    bars = mk([(100, 110.5, 99.5, 110), (111, 112.5, 110.5, 111.5), (111, 111.5, 103, 104)])
    assert names(cs.detect_stars(bars)) == ["evening_star"]


# ------------------------------------------------------------------ inside bar / NR7

def test_inside_bar():
    sig = cs.detect_inside_bar(mk([(100, 110, 90, 105), (102, 108, 95, 104)]))
    assert names(sig) == ["inside_bar"]
    assert sig[0].strength == 1 - 13 / 20


def test_inside_bar_requires_strictly_inside():
    assert cs.detect_inside_bar(mk([(100, 110, 90, 105), (102, 110, 95, 104)])) == []


def _ranges(rs):
    return mk([(100, 100 + r / 2, 100 - r / 2, 100 + r / 4) for r in rs])


def test_nr7():
    sig = cs.detect_nr7(_ranges([10, 9, 8, 7, 6, 5, 3]))
    assert names(sig) == ["nr7"] and sig[0].index == 6


def test_nr7_tie_does_not_count():
    assert cs.detect_nr7(_ranges([10, 9, 8, 7, 6, 5, 5])) == []


def test_nr7_needs_seven_bars():
    assert cs.detect_nr7(_ranges([9, 8, 7, 6, 5, 3])) == []
