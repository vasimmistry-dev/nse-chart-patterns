"""nse-chart-patterns: transparent, rule-based candlestick and chart pattern detection.

Quick start::

    from nse_chart_patterns import load_csv, scan
    bars = load_csv("RELIANCE.csv")
    for s in scan(bars, last=5):
        print(s.date, s.pattern, s.direction, round(s.strength, 2))
"""

__version__ = "0.1.0"

from .backtest import PatternStats, forward_return, forward_stats  # noqa: E402
from .chart import Level, Pivot, find_pivots, support_resistance  # noqa: E402
from .data import bars_from_rows, bars_from_tuples, load_csv  # noqa: E402
from .models import BEARISH, BULLISH, NEUTRAL, Bar, Signal  # noqa: E402
from .scanner import DETECTORS, PATTERNS, scan  # noqa: E402

__all__ = [
    "Bar", "Signal", "Level", "Pivot", "PatternStats",
    "BULLISH", "BEARISH", "NEUTRAL",
    "load_csv", "bars_from_rows", "bars_from_tuples",
    "scan", "DETECTORS", "PATTERNS",
    "find_pivots", "support_resistance",
    "forward_return", "forward_stats",
    "__version__",
]
