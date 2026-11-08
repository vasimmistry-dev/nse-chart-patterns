"""Pure-Python technical indicators.

Every function returns a list aligned with its input: element ``i`` is the
indicator value on bar ``i``, or ``None`` while there is not yet enough data.
"""

from __future__ import annotations

import math
from typing import List, Optional, Sequence, Tuple

from .models import Bar

Series = List[Optional[float]]


def sma(values: Sequence[float], period: int) -> Series:
    """Simple moving average."""
    if period < 1:
        raise ValueError("period must be >= 1")
    out: Series = [None] * len(values)
    total = 0.0
    for i, v in enumerate(values):
        total += v
        if i >= period:
            total -= values[i - period]
        if i >= period - 1:
            out[i] = total / period
    return out


def ema(values: Sequence[float], period: int) -> Series:
    """Exponential moving average, alpha = 2 / (period + 1), seeded with the SMA of the first ``period`` values."""
    if period < 1:
        raise ValueError("period must be >= 1")
    out: Series = [None] * len(values)
    if len(values) < period:
        return out
    alpha = 2.0 / (period + 1)
    prev = sum(values[:period]) / period
    out[period - 1] = prev
    for i in range(period, len(values)):
        prev = alpha * values[i] + (1 - alpha) * prev
        out[i] = prev
    return out


def rsi(closes: Sequence[float], period: int = 14) -> Series:
    """Relative Strength Index using Wilder's smoothing.

    The first value appears at index ``period`` and is seeded with simple
    averages of the first ``period`` gains/losses.
    """
    out: Series = [None] * len(closes)
    if len(closes) <= period:
        return out
    gains = losses = 0.0
    for i in range(1, period + 1):
        ch = closes[i] - closes[i - 1]
        gains += max(ch, 0.0)
        losses += max(-ch, 0.0)
    avg_g, avg_l = gains / period, losses / period

    def _value(g: float, l: float) -> float:
        if l == 0:
            return 100.0 if g > 0 else 50.0
        return 100.0 - 100.0 / (1.0 + g / l)

    out[period] = _value(avg_g, avg_l)
    for i in range(period + 1, len(closes)):
        ch = closes[i] - closes[i - 1]
        avg_g = (avg_g * (period - 1) + max(ch, 0.0)) / period
        avg_l = (avg_l * (period - 1) + max(-ch, 0.0)) / period
        out[i] = _value(avg_g, avg_l)
    return out


def true_range(bars: Sequence[Bar]) -> List[float]:
    out: List[float] = []
    for i, b in enumerate(bars):
        if i == 0:
            out.append(b.high - b.low)
        else:
            pc = bars[i - 1].close
            out.append(max(b.high - b.low, abs(b.high - pc), abs(b.low - pc)))
    return out


def atr(bars: Sequence[Bar], period: int = 14) -> Series:
    """Average True Range with Wilder's smoothing (first value = SMA of the first ``period`` true ranges)."""
    tr = true_range(bars)
    out: Series = [None] * len(tr)
    if len(tr) < period:
        return out
    prev = sum(tr[:period]) / period
    out[period - 1] = prev
    for i in range(period, len(tr)):
        prev = (prev * (period - 1) + tr[i]) / period
        out[i] = prev
    return out


def bollinger(
    closes: Sequence[float], period: int = 20, k: float = 2.0
) -> Tuple[Series, Series, Series]:
    """Bollinger Bands ``(middle, upper, lower)`` using the population standard deviation."""
    mid = sma(closes, period)
    upper: Series = [None] * len(closes)
    lower: Series = [None] * len(closes)
    for i in range(period - 1, len(closes)):
        m = mid[i]
        assert m is not None
        window = closes[i - period + 1 : i + 1]
        sd = math.sqrt(sum((x - m) ** 2 for x in window) / period)
        upper[i] = m + k * sd
        lower[i] = m - k * sd
    return mid, upper, lower


def bandwidth(closes: Sequence[float], period: int = 20, k: float = 2.0) -> Series:
    """Bollinger bandwidth: (upper - lower) / middle."""
    mid, up, lo = bollinger(closes, period, k)
    out: Series = [None] * len(closes)
    for i, m in enumerate(mid):
        if m is not None and m != 0 and up[i] is not None and lo[i] is not None:
            out[i] = (up[i] - lo[i]) / m  # type: ignore[operator]
    return out


def volume_sma(bars: Sequence[Bar], period: int = 20) -> Series:
    return sma([b.volume for b in bars], period)


def closes(bars: Sequence[Bar]) -> List[float]:
    return [b.close for b in bars]
