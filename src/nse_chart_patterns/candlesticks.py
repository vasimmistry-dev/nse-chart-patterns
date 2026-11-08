"""Single- and multi-bar candlestick patterns.

Notation used below (for one bar): ``body = |close - open|``,
``range = high - low``, ``upper = high - max(open, close)``,
``lower = min(open, close) - low``. The exact rules are repeated in README.md.
"""

from __future__ import annotations

from typing import List, Optional, Sequence

from .models import BEARISH, BULLISH, NEUTRAL, Bar, Signal, clamp01

#: body <= DOJI_BODY_RATIO * range  ->  doji
DOJI_BODY_RATIO = 0.1
#: bars used to judge the trend before a hammer / shooting star
TREND_LOOKBACK = 5


def _sig(bars: Sequence[Bar], i: int, pattern: str, direction: str, strength: float, **details) -> Signal:
    return Signal(bars[i].date, pattern, direction, clamp01(strength), details, index=i)


def prior_trend(bars: Sequence[Bar], i: int, lookback: int = TREND_LOOKBACK) -> Optional[float]:
    """Close of bar ``i-1`` minus close of bar ``i-1-lookback`` (None if not enough history)."""
    j = i - 1 - lookback
    if j < 0:
        return None
    return bars[i - 1].close - bars[j].close


def detect_doji(bars: Sequence[Bar]) -> List[Signal]:
    """Doji: range > 0 and body <= 10% of range."""
    out = []
    for i, b in enumerate(bars):
        if b.range > 0 and b.body <= DOJI_BODY_RATIO * b.range:
            strength = 1.0 - b.body / (DOJI_BODY_RATIO * b.range)
            out.append(_sig(bars, i, "doji", NEUTRAL, strength, body_pct_of_range=b.body / b.range))
    return out


def _is_hammer_shape(b: Bar) -> bool:
    return (
        b.range > 0
        and b.body >= DOJI_BODY_RATIO * b.range
        and b.lower_shadow >= 2 * b.body
        and b.upper_shadow <= DOJI_BODY_RATIO * b.range
    )


def _is_shooting_star_shape(b: Bar) -> bool:
    return (
        b.range > 0
        and b.body >= DOJI_BODY_RATIO * b.range
        and b.upper_shadow >= 2 * b.body
        and b.lower_shadow <= DOJI_BODY_RATIO * b.range
    )


def detect_hammer(bars: Sequence[Bar]) -> List[Signal]:
    """Hammer: long lower shadow (>= 2x body), tiny upper shadow, after a 5-bar decline."""
    out = []
    for i, b in enumerate(bars):
        trend = prior_trend(bars, i)
        if trend is not None and trend < 0 and _is_hammer_shape(b):
            out.append(
                _sig(bars, i, "hammer", BULLISH, b.lower_shadow / b.range,
                     lower_shadow_to_body=b.lower_shadow / b.body, prior_change=trend)
            )
    return out


def detect_shooting_star(bars: Sequence[Bar]) -> List[Signal]:
    """Shooting star: long upper shadow (>= 2x body), tiny lower shadow, after a 5-bar advance."""
    out = []
    for i, b in enumerate(bars):
        trend = prior_trend(bars, i)
        if trend is not None and trend > 0 and _is_shooting_star_shape(b):
            out.append(
                _sig(bars, i, "shooting_star", BEARISH, b.upper_shadow / b.range,
                     upper_shadow_to_body=b.upper_shadow / b.body, prior_change=trend)
            )
    return out


def detect_engulfing(bars: Sequence[Bar]) -> List[Signal]:
    """Bullish / bearish engulfing (real bodies only, shadows ignored)."""
    out = []
    for i in range(1, len(bars)):
        p, c = bars[i - 1], bars[i]
        if p.body == 0 or c.body <= p.body:
            continue
        ratio = c.body / p.body
        strength = 0.5 + 0.5 * clamp01((ratio - 1) / 2)
        if p.is_bearish and c.is_bullish and c.open <= p.close and c.close >= p.open:
            out.append(_sig(bars, i, "bullish_engulfing", BULLISH, strength, body_ratio=ratio))
        elif p.is_bullish and c.is_bearish and c.open >= p.close and c.close <= p.open:
            out.append(_sig(bars, i, "bearish_engulfing", BEARISH, strength, body_ratio=ratio))
    return out


def detect_stars(bars: Sequence[Bar]) -> List[Signal]:
    """Morning star (bullish) and evening star (bearish) three-bar reversals."""
    out = []
    for i in range(2, len(bars)):
        b1, b2, b3 = bars[i - 2], bars[i - 1], bars[i]
        if b1.range == 0 or b1.body < 0.5 * b1.range or b2.body > 0.3 * b1.body:
            continue
        mid1 = (b1.open + b1.close) / 2
        half = b1.body / 2
        if b1.is_bearish and max(b2.open, b2.close) <= b1.close and b3.is_bullish and b3.close > mid1:
            pen = (b3.close - mid1) / half
            out.append(_sig(bars, i, "morning_star", BULLISH, 0.5 + 0.5 * clamp01(pen),
                            first_bar_midpoint=mid1))
        elif b1.is_bullish and min(b2.open, b2.close) >= b1.close and b3.is_bearish and b3.close < mid1:
            pen = (mid1 - b3.close) / half
            out.append(_sig(bars, i, "evening_star", BEARISH, 0.5 + 0.5 * clamp01(pen),
                            first_bar_midpoint=mid1))
    return out


def detect_inside_bar(bars: Sequence[Bar]) -> List[Signal]:
    """Inside bar: high < previous high and low > previous low (strict)."""
    out = []
    for i in range(1, len(bars)):
        p, c = bars[i - 1], bars[i]
        if c.high < p.high and c.low > p.low and p.range > 0:
            out.append(_sig(bars, i, "inside_bar", NEUTRAL, 1 - c.range / p.range,
                            mother_high=p.high, mother_low=p.low))
    return out


def detect_nr7(bars: Sequence[Bar]) -> List[Signal]:
    """NR7: today's range is strictly the narrowest of the last 7 bars (today included)."""
    out = []
    for i in range(6, len(bars)):
        r = bars[i].range
        prev = [bars[j].range for j in range(i - 6, i)]
        if all(r < x for x in prev):
            widest = max(prev)
            out.append(_sig(bars, i, "nr7", NEUTRAL, 1 - r / widest if widest else 0.0,
                            range=r, widest_prior_range=widest))
    return out
