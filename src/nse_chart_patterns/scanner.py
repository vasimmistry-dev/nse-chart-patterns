"""Run every (or a chosen subset of) detector over a bar series."""

from __future__ import annotations

from typing import Callable, Dict, Iterable, List, Optional, Sequence

from . import candlesticks as cs
from . import chart
from .models import Bar, Signal

Detector = Callable[[Sequence[Bar]], List[Signal]]

#: detector name -> function. Some detectors emit more than one pattern name.
DETECTORS: Dict[str, Detector] = {
    "doji": cs.detect_doji,
    "hammer": cs.detect_hammer,
    "shooting_star": cs.detect_shooting_star,
    "engulfing": cs.detect_engulfing,
    "stars": cs.detect_stars,
    "inside_bar": cs.detect_inside_bar,
    "nr7": cs.detect_nr7,
    "52w": chart.detect_52w_breakout,
    "range_breakout": chart.detect_range_breakout,
    "ma_cross": chart.detect_ma_cross,
    "swing": chart.detect_swing_points,
    "double": chart.detect_double_patterns,
    "bollinger_squeeze": chart.detect_bollinger_squeeze,
}

#: every pattern name a detector can emit
PATTERNS = (
    "doji", "hammer", "shooting_star", "bullish_engulfing", "bearish_engulfing",
    "morning_star", "evening_star", "inside_bar", "nr7",
    "52w_high_breakout", "52w_low_breakdown", "range_breakout", "range_breakdown",
    "golden_cross", "death_cross", "swing_high", "swing_low",
    "double_top", "double_bottom", "bollinger_squeeze",
)


def scan(
    bars: Sequence[Bar],
    detectors: Optional[Iterable[str]] = None,
    patterns: Optional[Iterable[str]] = None,
    last: Optional[int] = None,
) -> List[Signal]:
    """Run detectors and return signals sorted by date (then pattern name).

    :param detectors: detector names from :data:`DETECTORS` (default: all).
    :param patterns: keep only these pattern names (see :data:`PATTERNS`).
    :param last: keep only signals dated within the last ``last`` bars.
    """
    names = list(detectors) if detectors is not None else list(DETECTORS)
    unknown = [n for n in names if n not in DETECTORS]
    if unknown:
        raise ValueError("Unknown detector(s): %s. Choose from %s" % (unknown, sorted(DETECTORS)))
    keep = set(patterns) if patterns is not None else None
    if keep is not None:
        bad = keep.difference(PATTERNS)
        if bad:
            raise ValueError("Unknown pattern(s): %s" % sorted(bad))
    signals: List[Signal] = []
    for n in names:
        signals.extend(DETECTORS[n](bars))
    if keep is not None:
        signals = [s for s in signals if s.pattern in keep]
    if last is not None and bars:
        cutoff = len(bars) - last
        signals = [s for s in signals if s.index >= cutoff]
    signals.sort(key=lambda s: (s.index, s.pattern))
    return signals
