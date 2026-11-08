"""Historical forward-return statistics for detected signals.

These numbers describe what happened *in the data you supplied*. They are
not predictions, ignore costs, slippage and gaps, and small sample sizes are
common. Treat them as a sanity check on a rule, nothing more.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence

from .models import BEARISH, BULLISH, Bar, Signal


@dataclass
class PatternStats:
    pattern: str
    direction: str
    horizon: int
    count: int
    avg_return: Optional[float]
    median_return: Optional[float]
    win_rate: Optional[float]
    """Share of signals whose forward return moved in the signal's direction
    (> 0 for bullish, < 0 for bearish). For neutral patterns: share > 0."""

    def to_dict(self) -> dict:
        r = lambda x: None if x is None else round(x, 4)  # noqa: E731
        return {
            "pattern": self.pattern,
            "direction": self.direction,
            "horizon": self.horizon,
            "count": self.count,
            "avg_return": r(self.avg_return),
            "median_return": r(self.median_return),
            "win_rate": r(self.win_rate),
        }


def forward_return(bars: Sequence[Bar], index: int, horizon: int) -> Optional[float]:
    """Close-to-close return from bar ``index`` to bar ``index + horizon`` (None if out of range)."""
    j = index + horizon
    if index < 0 or j >= len(bars) or bars[index].close == 0:
        return None
    return bars[j].close / bars[index].close - 1


def forward_stats(bars: Sequence[Bar], signals: Sequence[Signal], horizon: int = 10) -> List[PatternStats]:
    """Group signals by pattern and summarise their ``horizon``-bar forward returns.

    Entry is the close of the signal bar; exit is the close ``horizon`` bars
    later. Signals without enough following bars are skipped.
    """
    if horizon < 1:
        raise ValueError("horizon must be >= 1")
    groups: Dict[str, List[float]] = {}
    directions: Dict[str, str] = {}
    for s in signals:
        r = forward_return(bars, s.index, horizon)
        directions[s.pattern] = s.direction
        groups.setdefault(s.pattern, [])
        if r is not None:
            groups[s.pattern].append(r)
    out = []
    for pattern in sorted(groups):
        rets = groups[pattern]
        d = directions[pattern]
        if rets:
            if d == BEARISH:
                wins = sum(1 for x in rets if x < 0)
            else:
                wins = sum(1 for x in rets if x > 0)
            out.append(PatternStats(pattern, d, horizon, len(rets), statistics.mean(rets),
                                    statistics.median(rets), wins / len(rets)))
        else:
            out.append(PatternStats(pattern, d, horizon, 0, None, None, None))
    return out


__all__ = ["PatternStats", "forward_return", "forward_stats", "BULLISH", "BEARISH"]
