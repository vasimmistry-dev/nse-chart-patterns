"""Command-line interface: ``chart-patterns scan|levels|backtest``."""

from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

from . import __version__
from .backtest import forward_stats
from .chart import support_resistance
from .data import load_csv
from .scanner import DETECTORS, PATTERNS, scan

DISCLAIMER = "Educational use only. Not investment advice."


def _csv_list(value: Optional[str]) -> Optional[List[str]]:
    if not value:
        return None
    return [x.strip() for x in value.split(",") if x.strip()]


def _load(args):
    bars = load_csv(args.file, series=args.series)
    if not bars:
        raise SystemExit("No usable rows found in %s" % args.file)
    return bars


def cmd_scan(args) -> int:
    bars = _load(args)
    signals = scan(bars, detectors=_csv_list(args.detectors), patterns=_csv_list(args.patterns), last=args.last)
    if args.json:
        print(json.dumps([s.to_dict() for s in signals], indent=2))
        return 0
    print("%d bars, %s to %s" % (len(bars), bars[0].date, bars[-1].date))
    if not signals:
        print("No signals%s." % (" in the last %d bars" % args.last if args.last else ""))
        return 0
    print("%-10s  %-20s  %-8s  %5s  %s" % ("date", "pattern", "dir", "str", "details"))
    for s in signals:
        d = s.to_dict()["details"]
        detail = ", ".join("%s=%s" % kv for kv in list(d.items())[:3])
        print("%-10s  %-20s  %-8s  %5.2f  %s" % (s.date, s.pattern, s.direction, s.strength, detail))
    return 0


def cmd_levels(args) -> int:
    bars = _load(args)
    levels = support_resistance(bars, tolerance=args.tolerance, min_touches=args.min_touches,
                                lookback=args.lookback)
    if args.json:
        print(json.dumps({"last_close": bars[-1].close, "levels": [lv.to_dict() for lv in levels]}, indent=2))
        return 0
    print("Last close %.2f on %s" % (bars[-1].close, bars[-1].date))
    if not levels:
        print("No levels with >= %d touches." % args.min_touches)
    for lv in levels:
        print("%-10s %10.2f  touches=%d  (%s .. %s)" % (lv.kind, lv.price, lv.touches, lv.first_date, lv.last_date))
    return 0


def cmd_backtest(args) -> int:
    bars = _load(args)
    signals = scan(bars, detectors=_csv_list(args.detectors), patterns=_csv_list(args.patterns))
    stats = forward_stats(bars, signals, horizon=args.horizon)
    if args.json:
        print(json.dumps({"note": "Historical statistics only, not predictions.",
                          "stats": [s.to_dict() for s in stats]}, indent=2))
        return 0
    print("Historical %d-bar forward returns (close to close, no costs). Not a prediction." % args.horizon)
    print("%-20s  %-8s  %5s  %8s  %8s  %6s" % ("pattern", "dir", "n", "avg", "median", "win%"))
    for s in stats:
        if s.count == 0:
            print("%-20s  %-8s  %5d  %8s  %8s  %6s" % (s.pattern, s.direction, 0, "-", "-", "-"))
        else:
            print("%-20s  %-8s  %5d  %7.2f%%  %7.2f%%  %5.1f%%" % (
                s.pattern, s.direction, s.count, 100 * s.avg_return, 100 * s.median_return, 100 * s.win_rate))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="chart-patterns",
        description="Detect candlestick and chart patterns in daily OHLCV CSV data. " + DISCLAIMER,
    )
    p.add_argument("--version", action="version", version="%(prog)s " + __version__)
    sub = p.add_subparsers(dest="command", required=True)

    def common(sp):
        sp.add_argument("file", help="CSV with Date,Open,High,Low,Close[,Volume] or NSE-style headers")
        sp.add_argument("--series", help="keep only this SERIES value (e.g. EQ) if the column exists")
        sp.add_argument("--json", action="store_true", help="machine-readable JSON output")

    s = sub.add_parser("scan", help="list detected signals")
    common(s)
    s.add_argument("--last", type=int, help="only signals from the last N bars")
    s.add_argument("--patterns", help="comma-separated pattern names: " + ",".join(PATTERNS))
    s.add_argument("--detectors", help="comma-separated detectors: " + ",".join(DETECTORS))
    s.set_defaults(func=cmd_scan)

    lv = sub.add_parser("levels", help="support / resistance levels from clustered swing points")
    common(lv)
    lv.add_argument("--tolerance", type=float, default=0.015, help="cluster width as a fraction (default 0.015)")
    lv.add_argument("--min-touches", type=int, default=2)
    lv.add_argument("--lookback", type=int, default=250, help="bars to look back (default 250)")
    lv.set_defaults(func=cmd_levels)

    b = sub.add_parser("backtest", help="historical forward-return stats per pattern")
    common(b)
    b.add_argument("--horizon", type=int, default=10, help="forward bars (default 10)")
    b.add_argument("--patterns", help="comma-separated pattern names")
    b.add_argument("--detectors", help="comma-separated detectors")
    b.set_defaults(func=cmd_backtest)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (OSError, ValueError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
