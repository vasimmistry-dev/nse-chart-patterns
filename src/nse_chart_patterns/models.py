"""Core data types: a daily OHLCV bar and a detected signal."""

from __future__ import annotations

import datetime as _dt
from dataclasses import asdict, dataclass, field
from typing import Any, Dict

BULLISH = "bullish"
BEARISH = "bearish"
NEUTRAL = "neutral"


@dataclass(frozen=True)
class Bar:
    """One daily OHLCV bar."""

    date: _dt.date
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0

    @property
    def body(self) -> float:
        return abs(self.close - self.open)

    @property
    def range(self) -> float:
        return self.high - self.low

    @property
    def upper_shadow(self) -> float:
        return self.high - max(self.open, self.close)

    @property
    def lower_shadow(self) -> float:
        return min(self.open, self.close) - self.low

    @property
    def is_bullish(self) -> bool:
        return self.close > self.open

    @property
    def is_bearish(self) -> bool:
        return self.close < self.open


@dataclass
class Signal:
    """A pattern detected on a specific bar.

    ``strength`` is a 0-1 heuristic intended only for ranking signals of the
    same pattern against each other. It is *not* a probability.
    """

    date: _dt.date
    pattern: str
    direction: str
    strength: float
    details: Dict[str, Any] = field(default_factory=dict)
    index: int = -1

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["date"] = self.date.isoformat()
        d["strength"] = round(self.strength, 3)
        d["details"] = {
            k: (v.isoformat() if isinstance(v, _dt.date) else (round(v, 4) if isinstance(v, float) else v))
            for k, v in self.details.items()
        }
        return d


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))
