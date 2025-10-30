"""Utilities for loading and normalising price history."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd


@dataclass(slots=True)
class PriceHistory:
    """Wrapper around a pandas DataFrame representing OHLCV data."""

    data: pd.DataFrame

    def __post_init__(self) -> None:
        if not isinstance(self.data.index, pd.DatetimeIndex):
            raise TypeError("Price history must be indexed by DatetimeIndex")
        if not self.data.index.is_monotonic_increasing:
            self.data = self.data.sort_index()

    @property
    def as_of(self) -> datetime:
        return self.data.index[-1].to_pydatetime()


class DataSource:
    """Abstract source able to provide historical data for a ticker."""

    def get_history(
        self,
        ticker: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        period: str = "2y",
        interval: str = "1d",
    ) -> PriceHistory:
        raise NotImplementedError


class YFinanceDataSource(DataSource):
    """Download historical data using :mod:`yfinance`."""

    def __init__(self) -> None:
        try:
            import yfinance as yf  # type: ignore
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("yfinance must be installed to use YFinanceDataSource") from exc
        self._yf = yf

    def get_history(
        self,
        ticker: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        period: str = "2y",
        interval: str = "1d",
    ) -> PriceHistory:
        history = self._yf.download(
            tickers=ticker,
            start=start,
            end=end,
            period=None if start else period,
            interval=interval,
            auto_adjust=False,
            progress=False,
        )
        if history.empty:
            raise ValueError(f"No price history returned for {ticker}")
        history.index = pd.to_datetime(history.index)
        return PriceHistory(history)


def load_csv(path: Path) -> PriceHistory:
    """Load price history from a CSV file exported from Yahoo Finance."""

    df = pd.read_csv(path, parse_dates=[0], index_col=0)
    required_columns = {"Open", "High", "Low", "Close", "Adj Close", "Volume"}
    if not required_columns.issubset(df.columns):
        missing = ", ".join(sorted(required_columns - set(df.columns)))
        raise ValueError(f"CSV file is missing required columns: {missing}")
    return PriceHistory(df)


__all__ = ["PriceHistory", "DataSource", "YFinanceDataSource", "load_csv"]
