"""High level orchestration of the glossary indicators."""

from __future__ import annotations

from datetime import datetime
from typing import Iterable

from .data import DataSource, PriceHistory
from .indicators import build_indicator_results
from .models import IndicatorResult, ScreeningResult


class GlossaryScreener:
    """Run the canonical indicators defined in :mod:`screnners.indicators`."""

    def __init__(self, data_source: DataSource) -> None:
        self._data_source = data_source

    def screen(
        self,
        ticker: str,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
        period: str = "2y",
        interval: str = "1d",
    ) -> ScreeningResult:
        history = self._data_source.get_history(ticker, start=start, end=end, period=period, interval=interval)
        indicator_results: Iterable[IndicatorResult] = build_indicator_results(history)
        return ScreeningResult(ticker=ticker, as_of=history.as_of, indicator_results=list(indicator_results))


__all__ = ["GlossaryScreener"]
