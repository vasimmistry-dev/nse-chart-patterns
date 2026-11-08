"""Helpers for building small, hand-checked bar series."""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from nse_chart_patterns.data import bars_from_tuples  # noqa: E402


def trend(start, end, n, vol=1000, bearish_bodies=None):
    """``n`` bars whose closes move linearly from ``start`` to ``end``.

    Each bar opens at the previous close, with high/low 0.5 beyond the body,
    so bodies are non-zero (no accidental dojis) when the trend is not flat.
    """
    rows = []
    prev = start
    for k in range(n):
        c = start + (end - start) * (k + 1) / n
        o = prev
        rows.append((o, max(o, c) + 0.5, min(o, c) - 0.5, c, vol))
        prev = c
    return rows


def path(anchors, step_bars, vol=1000):
    """Piecewise-linear close path through ``anchors`` with ``step_bars`` bars per leg.

    Every bar has high = close + 0.5 and low = close - 0.5, so each anchor is a
    unique local extreme and pivot prices are ``anchor +/- 0.5``.
    """
    closes = [float(anchors[0])]
    for a, b in zip(anchors, anchors[1:]):
        for k in range(1, step_bars + 1):
            closes.append(a + (b - a) * k / step_bars)
    rows = []
    prev = closes[0]
    for c in closes:
        o = min(max((prev + c) / 2, c - 0.5), c + 0.5)
        rows.append((o, c + 0.5, c - 0.5, c, vol))
        prev = c
    return rows


@pytest.fixture
def make():
    return bars_from_tuples
