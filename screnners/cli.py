"""Command line interface for the screener."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable, Sequence

from .data import DataSource, PriceHistory, YFinanceDataSource, load_csv
from .models import ScreeningResult
from .screener import GlossaryScreener

try:  # pragma: no cover - optional dependency for nicer output
    from rich.console import Console
    from rich.table import Table
except ImportError:  # pragma: no cover - fallback path
    Console = None
    Table = None


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Wishing Wealth glossary screener")
    parser.add_argument("tickers", nargs="*", help="Tickers to screen")
    parser.add_argument("--csv", type=Path, help="Optional path to a Yahoo-style CSV to avoid network access")
    parser.add_argument("--period", default="2y", help="History period when downloading from Yahoo Finance")
    parser.add_argument("--interval", default="1d", help="Price interval when downloading from Yahoo Finance")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a table")
    return parser.parse_args(argv)


def _serialise_result(result: ScreeningResult) -> dict:
    return {
        "ticker": result.ticker,
        "as_of": result.as_of.isoformat(),
        "indicators": [
            {"name": ir.name, "passed": ir.passed, "details": dict(ir.details)} for ir in result.indicator_results
        ],
    }


def _print_table(results: Iterable[ScreeningResult]) -> None:
    if Console is None or Table is None:
        for result in results:
            print(result.ticker, result.as_of.isoformat())
            for indicator in result.indicator_results:
                status = "PASS" if indicator.passed else "FAIL"
                print(f"  - {indicator.name:>22}: {status}")
        return

    table = Table(title="Glossary Screener Results")
    table.add_column("Ticker")
    table.add_column("As of")
    table.add_column("Indicator")
    table.add_column("Status")
    table.add_column("Details")

    for result in results:
        for indicator in result.indicator_results:
            status = "✅" if indicator.passed else "❌"
            details = ", ".join(f"{k}={v:.2f}" if isinstance(v, float) else f"{k}={v}" for k, v in indicator.details.items())
            table.add_row(result.ticker, result.as_of.strftime("%Y-%m-%d"), indicator.name, status, details)

    Console().print(table)


def _load_history_from_args(args: argparse.Namespace) -> tuple[DataSource, list[str]]:
    if args.csv:
        history = load_csv(args.csv)

        class StaticDataSource(DataSource):
            def get_history(self, ticker: str, **_: object) -> PriceHistory:  # type: ignore[override]
                return history

        return StaticDataSource(), args.tickers or [args.csv.stem]

    return YFinanceDataSource(), list(args.tickers)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    if not args.tickers and not args.csv:
        raise SystemExit("Provide at least one ticker or a --csv path")

    data_source, tickers = _load_history_from_args(args)
    screener = GlossaryScreener(data_source)

    results = [
        screener.screen(ticker, period=args.period, interval=args.interval)
        for ticker in tickers
    ]

    if args.json:
        print(json.dumps([_serialise_result(result) for result in results], indent=2))
    else:
        _print_table(results)

    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
