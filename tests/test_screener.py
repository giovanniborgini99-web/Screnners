from __future__ import annotations

from datetime import datetime

import pandas as pd

from screnners.data import DataSource, PriceHistory
from screnners.screener import GlossaryScreener


class StubDataSource(DataSource):
    def __init__(self, history: PriceHistory) -> None:
        self._history = history

    def get_history(self, ticker: str, **_: object) -> PriceHistory:  # type: ignore[override]
        return self._history


def test_screener_returns_indicator_results() -> None:
    dates = pd.date_range(start="2022-01-03", periods=200, freq="B")
    close = [i * 0.1 + 20 for i in range(len(dates))]
    df = pd.DataFrame({
        "Open": close,
        "High": close,
        "Low": close,
        "Close": close,
        "Adj Close": close,
        "Volume": 1000,
    }, index=dates)
    history = PriceHistory(df)

    screener = GlossaryScreener(StubDataSource(history))
    result = screener.screen("TEST")

    assert result.ticker == "TEST"
    assert result.indicator_results
    assert any(indicator.passed for indicator in result.indicator_results)
    assert "Wish GLB Checklist" in {indicator.name for indicator in result.indicator_results}
