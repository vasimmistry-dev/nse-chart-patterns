"""Chart / setup patterns: breakouts, crosses, swing points, double tops and
bottoms, support/resistance levels and the Bollinger squeeze.

All detectors only use data available *on or before* the bar a signal is
dated, so signals can be back-tested without look-ahead bias. Swing points
are therefore dated on the bar that *confirms* them (``right`` bars after the
pivot), with the pivot itself in ``details``.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from typing import List, Optional, Sequence

from . import indicators as ind
from .models import BEARISH, BULLISH, NEUTRAL, Bar, Signal, clamp01


def _sig(bars: Sequence[Bar], i: int, pattern: str, direction: str, strength: float, **details) -> Signal:
    return Signal(bars[i].date, pattern, direction, clamp01(strength), details, index=i)


# --------------------------------------------------------------------------- breakouts


def detect_52w_breakout(bars: Sequence[Bar], lookback: int = 252) -> List[Signal]:
    """Close above the highest high (or below the lowest low) of the previous ``lookback`` bars."""
    out = []
    for i in range(lookback, len(bars)):
        window = bars[i - lookback : i]
        hi = max(b.high for b in window)
        lo = min(b.low for b in window)
        c = bars[i].close
        if c > hi:
            pct = c / hi - 1
            out.append(_sig(bars, i, "52w_high_breakout", BULLISH, 0.5 + 0.5 * clamp01(pct / 0.05),
                            prior_high=hi, pct_above=pct))
        elif c < lo:
            pct = 1 - c / lo
            out.append(_sig(bars, i, "52w_low_breakdown", BEARISH, 0.5 + 0.5 * clamp01(pct / 0.05),
                            prior_low=lo, pct_below=pct))
    return out


def detect_range_breakout(
    bars: Sequence[Bar], period: int = 20, volume_period: int = 20, volume_mult: float = 1.5
) -> List[Signal]:
    """Close beyond the prior ``period``-bar high/low with volume > ``volume_mult`` x average.

    The volume average covers the ``volume_period`` bars *before* the signal bar.
    """
    out = []
    start = max(period, volume_period)
    for i in range(start, len(bars)):
        b = bars[i]
        avg_vol = sum(x.volume for x in bars[i - volume_period : i]) / volume_period
        if avg_vol <= 0 or b.volume <= volume_mult * avg_vol:
            continue
        window = bars[i - period : i]
        hi = max(x.high for x in window)
        lo = min(x.low for x in window)
        ratio = b.volume / avg_vol
        if b.close > hi:
            out.append(_sig(bars, i, "range_breakout", BULLISH, ratio / 3,
                            period=period, range_high=hi, volume_ratio=ratio))
        elif b.close < lo:
            out.append(_sig(bars, i, "range_breakdown", BEARISH, ratio / 3,
                            period=period, range_low=lo, volume_ratio=ratio))
    return out


# --------------------------------------------------------------------------- moving averages


def detect_ma_cross(bars: Sequence[Bar], fast: int = 50, slow: int = 200) -> List[Signal]:
    """Golden cross (fast SMA crosses above slow SMA) and death cross (crosses below)."""
    closes = ind.closes(bars)
    f, s = ind.sma(closes, fast), ind.sma(closes, slow)
    out = []
    for i in range(1, len(bars)):
        if None in (f[i - 1], s[i - 1], f[i], s[i]):
            continue
        gap = (f[i] - s[i]) / s[i]  # type: ignore[operator]
        if f[i - 1] <= s[i - 1] and f[i] > s[i]:  # type: ignore[operator]
            out.append(_sig(bars, i, "golden_cross", BULLISH, 0.5 + 0.5 * clamp01(gap / 0.01),
                            fast=fast, slow=slow, fast_sma=f[i], slow_sma=s[i]))
        elif f[i - 1] >= s[i - 1] and f[i] < s[i]:  # type: ignore[operator]
            out.append(_sig(bars, i, "death_cross", BEARISH, 0.5 + 0.5 * clamp01(-gap / 0.01),
                            fast=fast, slow=slow, fast_sma=f[i], slow_sma=s[i]))
    return out


# --------------------------------------------------------------------------- pivots


@dataclass(frozen=True)
class Pivot:
    index: int
    date: _dt.date
    price: float
    kind: str  # "high" or "low"
    confirmed_index: int


def find_pivots(bars: Sequence[Bar], left: int = 5, right: int = 5) -> List[Pivot]:
    """Swing highs/lows.

    Bar ``i`` is a swing high if its high is *strictly* greater than the highs
    of the ``left`` bars before it and the ``right`` bars after it (swing lows
    mirror this with lows). A pivot is only known ``right`` bars later.
    """
    pivots: List[Pivot] = []
    for i in range(left, len(bars) - right):
        h, l = bars[i].high, bars[i].low
        neighbours = list(bars[i - left : i]) + list(bars[i + 1 : i + 1 + right])
        if all(h > b.high for b in neighbours):
            pivots.append(Pivot(i, bars[i].date, h, "high", i + right))
        if all(l < b.low for b in neighbours):
            pivots.append(Pivot(i, bars[i].date, l, "low", i + right))
    return pivots


def detect_swing_points(bars: Sequence[Bar], left: int = 5, right: int = 5) -> List[Signal]:
    """Emit ``swing_high`` / ``swing_low`` on the bar that confirms each pivot."""
    out = []
    for p in find_pivots(bars, left, right):
        c = p.confirmed_index
        move = abs(bars[c].close - p.price) / p.price
        out.append(_sig(bars, c, "swing_" + p.kind, NEUTRAL, clamp01(move / 0.05),
                        pivot_date=p.date, pivot_price=p.price))
    return out


# --------------------------------------------------------------------------- double top / bottom


def detect_double_patterns(
    bars: Sequence[Bar],
    tolerance: float = 0.03,
    left: int = 5,
    right: int = 5,
    min_separation: int = 10,
    max_separation: int = 120,
    min_depth: float = 0.03,
    confirm_within: int = 20,
) -> List[Signal]:
    """Double top / double bottom, confirmed by a close through the neckline.

    Double top: two *consecutive* swing highs P1, P2 with
    ``|P2 - P1| / max(P1, P2) <= tolerance``, ``min_separation`` to
    ``max_separation`` bars apart, and the lowest low between them (the
    neckline) at least ``min_depth`` below the lower peak. The signal fires on
    the first close below the neckline within ``confirm_within`` bars after P2
    is confirmed, unless price trades above both peaks first. Double bottom is
    the mirror image.
    """
    pivots = find_pivots(bars, left, right)
    out: List[Signal] = []
    for kind in ("high", "low"):
        pts = [p for p in pivots if p.kind == kind]
        for p1, p2 in zip(pts, pts[1:]):
            sep = p2.index - p1.index
            if not (min_separation <= sep <= max_separation):
                continue
            diff = abs(p2.price - p1.price) / max(p1.price, p2.price)
            if diff > tolerance:
                continue
            between = bars[p1.index + 1 : p2.index]
            if not between:
                continue
            if kind == "high":
                neck = min(b.low for b in between)
                ref = min(p1.price, p2.price)
                depth = (ref - neck) / ref
                extreme = max(p1.price, p2.price)
            else:
                neck = max(b.high for b in between)
                ref = max(p1.price, p2.price)
                depth = (neck - ref) / ref
                extreme = min(p1.price, p2.price)
            if depth < min_depth:
                continue
            start = p2.confirmed_index
            for j in range(start, min(len(bars), start + confirm_within + 1)):
                b = bars[j]
                if kind == "high":
                    if b.high > extreme:
                        break
                    if b.close < neck:
                        strength = 0.5 * clamp01(1 - diff / tolerance) + 0.5 * clamp01(depth / 0.15)
                        out.append(_sig(bars, j, "double_top", BEARISH, strength,
                                        first_peak_date=p1.date, second_peak_date=p2.date,
                                        first_peak=p1.price, second_peak=p2.price,
                                        neckline=neck, depth=depth))
                        break
                else:
                    if b.low < extreme:
                        break
                    if b.close > neck:
                        strength = 0.5 * clamp01(1 - diff / tolerance) + 0.5 * clamp01(depth / 0.15)
                        out.append(_sig(bars, j, "double_bottom", BULLISH, strength,
                                        first_trough_date=p1.date, second_trough_date=p2.date,
                                        first_trough=p1.price, second_trough=p2.price,
                                        neckline=neck, depth=depth))
                        break
    out.sort(key=lambda s: s.index)
    return out


# --------------------------------------------------------------------------- support / resistance


@dataclass
class Level:
    price: float
    kind: str  # "support" or "resistance"
    touches: int
    first_date: _dt.date
    last_date: _dt.date

    def to_dict(self) -> dict:
        return {
            "price": round(self.price, 4),
            "kind": self.kind,
            "touches": self.touches,
            "first_date": self.first_date.isoformat(),
            "last_date": self.last_date.isoformat(),
        }


def support_resistance(
    bars: Sequence[Bar],
    left: int = 5,
    right: int = 5,
    tolerance: float = 0.015,
    min_touches: int = 2,
    lookback: Optional[int] = 250,
) -> List[Level]:
    """Cluster swing highs and lows into horizontal price levels.

    Pivot prices from the last ``lookback`` bars are sorted and grouped
    greedily: a price joins the current cluster if it lies within
    ``tolerance`` (fractional) of the cluster's mean. Clusters with at least
    ``min_touches`` pivots become levels at their mean price. A level below the
    last close is support, otherwise resistance. Levels are returned nearest
    to the last close first.
    """
    if not bars:
        return []
    start = 0 if lookback is None else max(0, len(bars) - lookback)
    pivots = sorted((p for p in find_pivots(bars, left, right) if p.index >= start), key=lambda p: p.price)
    clusters: List[List[Pivot]] = []
    for p in pivots:
        if clusters:
            cur = clusters[-1]
            mean = sum(x.price for x in cur) / len(cur)
            if abs(p.price - mean) / mean <= tolerance:
                cur.append(p)
                continue
        clusters.append([p])
    last = bars[-1].close
    levels = []
    for cl in clusters:
        if len(cl) < min_touches:
            continue
        price = sum(x.price for x in cl) / len(cl)
        dates = sorted(x.date for x in cl)
        levels.append(Level(price, "support" if price < last else "resistance", len(cl), dates[0], dates[-1]))
    levels.sort(key=lambda lv: abs(lv.price - last))
    return levels


# --------------------------------------------------------------------------- volatility


def detect_bollinger_squeeze(
    bars: Sequence[Bar], period: int = 20, k: float = 2.0, lookback: int = 120
) -> List[Signal]:
    """Bollinger bandwidth strictly below every other bandwidth value of the last ``lookback`` bars.

    Ties do not count, so a perfectly constant bandwidth never signals.
    """
    if lookback < 2:
        raise ValueError("lookback must be >= 2")
    bw = ind.bandwidth(ind.closes(bars), period, k)
    out = []
    for i in range(len(bars)):
        if i - lookback + 1 < 0:
            continue
        window = bw[i - lookback + 1 : i + 1]
        if any(x is None for x in window):
            continue
        if bw[i] < min(window[:-1]):  # type: ignore[operator, type-var]
            widest = max(window)  # type: ignore[type-var]
            strength = 1 - bw[i] / widest if widest else 1.0  # type: ignore[operator]
            out.append(_sig(bars, i, "bollinger_squeeze", NEUTRAL, strength,
                            bandwidth=bw[i], lookback=lookback))
    return out
