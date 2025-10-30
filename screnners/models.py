"""Data structures used by the screener."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Iterable, Mapping


@dataclass(slots=True)
class IndicatorResult:
    """Represents the outcome of a single indicator evaluation."""

    name: str
    passed: bool
    details: Mapping[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ScreeningResult:
    """Outcome of running the screener for a ticker."""

    ticker: str
    as_of: datetime
    indicator_results: Iterable[IndicatorResult]

    @property
    def passed_indicators(self) -> Dict[str, IndicatorResult]:
        """Return a mapping of the indicators that passed."""

        return {result.name: result for result in self.indicator_results if result.passed}

    @property
    def failed_indicators(self) -> Dict[str, IndicatorResult]:
        """Return a mapping of the indicators that failed."""

        return {result.name: result for result in self.indicator_results if not result.passed}


__all__ = ["IndicatorResult", "ScreeningResult"]
