"""Load daily OHLCV data from CSV files or plain Python rows.

Accepted column names (case-insensitive, surrounding whitespace ignored):

=========  ==========================================================
field      accepted headers
=========  ==========================================================
date       Date, DATE1, TIMESTAMP, TRADE_DATE
open       Open, OPEN_PRICE
high       High, HIGH_PRICE
low        Low, LOW_PRICE
close      Close, CLOSE_PRICE   ("Adj Close" is ignored)
volume     Volume, TTL_TRD_QNTY, TOTTRDQTY, TOTAL_TRADED_QUANTITY
=========  ==========================================================

NSE security-wise archive files use ``DATE1``, ``OPEN_PRICE`` ... and often
have padded headers such as ``" OPEN_PRICE"``; those are handled.
"""

from __future__ import annotations

import csv
import datetime as _dt
import io
import os
from typing import Any, Dict, Iterable, List, Mapping, Optional, TextIO, Union

from .models import Bar

ALIASES = {
    "date": ("date", "date1", "timestamp", "trade_date"),
    "open": ("open", "open_price"),
    "high": ("high", "high_price"),
    "low": ("low", "low_price"),
    "close": ("close", "close_price"),
    "volume": ("volume", "ttl_trd_qnty", "tottrdqty", "total_traded_quantity"),
}

DATE_FORMATS = (
    "%Y-%m-%d",
    "%d-%b-%Y",  # 01-Jan-2024 (NSE archives)
    "%d-%B-%Y",
    "%d-%m-%Y",
    "%d/%m/%Y",
    "%Y/%m/%d",
    "%d %b %Y",
    "%Y%m%d",
)


def parse_date(value: Any) -> _dt.date:
    if isinstance(value, _dt.datetime):
        return value.date()
    if isinstance(value, _dt.date):
        return value
    text = str(value).strip()
    for fmt in DATE_FORMATS:
        try:
            return _dt.datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    # ISO timestamps such as 2024-01-02T00:00:00
    try:
        return _dt.datetime.fromisoformat(text).date()
    except ValueError:
        raise ValueError("Unrecognised date: %r" % value) from None


def _parse_number(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "")
    if text in ("", "-", "NA", "N/A", "nan", "null"):
        return None
    return float(text)


def _resolve_columns(headers: Iterable[str]) -> Dict[str, str]:
    normalised = {h.strip().lower().replace(" ", "_"): h for h in headers if h is not None}
    mapping: Dict[str, str] = {}
    for field_name, names in ALIASES.items():
        for name in names:
            if name in normalised:
                mapping[field_name] = normalised[name]
                break
    missing = [f for f in ("date", "open", "high", "low", "close") if f not in mapping]
    if missing:
        raise ValueError(
            "Missing required column(s) %s. Found headers: %s" % (", ".join(missing), list(headers))
        )
    return mapping


def bars_from_rows(rows: Iterable[Mapping[str, Any]], series: Optional[str] = None) -> List[Bar]:
    """Convert dict-like rows into a sorted, de-duplicated list of :class:`Bar`.

    Rows with a missing price are skipped. If ``series`` is given (e.g. ``"EQ"``)
    and a ``SERIES`` column exists, only rows of that series are kept.
    """
    rows = list(rows)
    if not rows:
        return []
    headers = list(rows[0].keys())
    cols = _resolve_columns(headers)
    series_col = next((h for h in headers if h and h.strip().lower() == "series"), None)

    by_date: Dict[_dt.date, Bar] = {}
    for row in rows:
        if series and series_col and str(row.get(series_col, "")).strip().upper() != series.upper():
            continue
        raw_date = row.get(cols["date"])
        if raw_date is None or str(raw_date).strip() == "":
            continue
        o, h, l, c = (_parse_number(row.get(cols[k])) for k in ("open", "high", "low", "close"))
        if None in (o, h, l, c):
            continue
        v = _parse_number(row.get(cols["volume"])) if "volume" in cols else None
        d = parse_date(raw_date)
        by_date[d] = Bar(d, o, h, l, c, v or 0.0)  # later duplicates win
    return [by_date[d] for d in sorted(by_date)]


def load_csv(source: Union[str, os.PathLike, TextIO], series: Optional[str] = None) -> List[Bar]:
    """Load bars from a CSV path or an open text file."""
    if hasattr(source, "read"):
        text = source.read()  # type: ignore[union-attr]
    else:
        with open(source, newline="", encoding="utf-8-sig") as fh:
            text = fh.read()
    reader = csv.DictReader(io.StringIO(text))
    return bars_from_rows(reader, series=series)


def bars_from_tuples(rows: Iterable[tuple], start: Optional[_dt.date] = None) -> List[Bar]:
    """Build bars from ``(open, high, low, close[, volume])`` tuples on consecutive weekdays.

    Handy for tests and notebooks.
    """
    day = start or _dt.date(2024, 1, 1)
    out: List[Bar] = []
    for row in rows:
        while day.weekday() >= 5:
            day += _dt.timedelta(days=1)
        o, h, l, c = (float(x) for x in row[:4])
        v = float(row[4]) if len(row) > 4 else 0.0
        out.append(Bar(day, o, h, l, c, v))
        day += _dt.timedelta(days=1)
    return out
