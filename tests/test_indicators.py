from __future__ import annotations

from datetime import datetime

import pandas as pd

from screnners.data import PriceHistory
from screnners.indicators import (
    GreenLineBreakoutResult,
    WishStrategyResult,
    bongo,
    darvas_box_breakout,
    green_line_breakout,
    rwb_pattern,
    wish_strategy,
)


def build_history(close: list[float], start: str = "2023-01-02", volume: list[float] | None = None) -> PriceHistory:
    dates = pd.date_range(start=start, periods=len(close), freq="B")
    volume = volume or [1_000.0] * len(close)
    df = pd.DataFrame({
        "Open": close,
        "High": close,
        "Low": close,
        "Close": close,
        "Adj Close": close,
        "Volume": volume,
    }, index=dates)
    return PriceHistory(df)


def test_green_line_breakout_detects_breakout() -> None:
    # Build monthly closes where February sets the green line, followed by
    # four months of closes below that level and a July breakout.
    month_values = {
        "2022-01": 20.0,
        "2022-02": 30.0,
        "2022-03": 28.0,
        "2022-04": 27.0,
        "2022-05": 29.0,
        "2022-06": 29.5,
        "2022-07": 31.0,
    }
    dates = pd.bdate_range("2022-01-03", "2022-07-29")
    prices = [month_values[date.strftime("%Y-%m")] for date in dates]
    history = build_history(prices, start="2022-01-03")
    result = green_line_breakout(history, min_base_months=3)
    assert isinstance(result, GreenLineBreakoutResult)
    assert result.breakout is True
    assert result.last_close > result.prior_high
    assert result.months_since_prior_high >= 4
    assert result.base_months == 4


def test_green_line_breakout_requires_base_below_high() -> None:
    # A would-be breakout fails because one of the base months closes back at
    # the green line, violating the consolidation requirement.
    month_values = {
        "2022-01": 20.0,
        "2022-02": 30.0,
        "2022-03": 30.0,
        "2022-04": 29.0,
        "2022-05": 29.5,
        "2022-06": 31.0,
    }
    dates = pd.bdate_range("2022-01-03", "2022-06-30")
    prices = [month_values[date.strftime("%Y-%m")] for date in dates]
    history = build_history(prices, start="2022-01-03")
    result = green_line_breakout(history, min_base_months=3)
    assert result.breakout is False
    assert result.base_months == 3


def test_darvas_box_breakout_requires_consolidation() -> None:
    prices = [10.0] * 60 + [12.0, 12.2, 12.4, 12.8, 13.0]
    history = build_history(prices)
    result = darvas_box_breakout(history, lookback_days=55, breakout_buffer=0.01)
    assert result.breakout is True
    assert result.box_high < result.box_low * 1.3


def test_rwb_pattern_detects_stack() -> None:
    # Create an up-trending price series to satisfy the RWB pattern
    prices = [i * 0.2 + 20 for i in range(120)]
    history = build_history(prices)
    result = rwb_pattern(history)
    assert result.rwb is True
    assert result.ribbon_spread > 0


def test_bongo_daily_turns_on_with_rising_trend() -> None:
    prices = [i * 0.1 + 30 for i in range(200)]
    history = build_history(prices)
    result = bongo(history, timeframe="D")
    assert result.is_on is True
    assert result.slope_positive is True


def test_bongo_weekly_turns_on_with_rising_trend() -> None:
    prices = [i * 0.2 + 30 for i in range(200)]
    history = build_history(prices)
    result = bongo(history, timeframe="W")
    assert result.is_on is True


def test_wish_strategy_requires_all_components() -> None:
    dates = pd.bdate_range("2022-01-03", periods=220)
    prices: list[float] = []
    for idx, _ in enumerate(dates):
        if idx < 60:
            prices.append(40.0 + 0.2 * idx)
        elif idx < 160:
            prices.append(51.0 - 0.02 * (idx - 60))
        else:
            prices.append(51.0 + 0.5 * (idx - 160))

    # Boost the final day's volume to exceed the 50 day average by > 1.5x.
    volumes = [1_000.0] * len(prices)
    volumes[-1] = 2_000.0

    history = build_history(prices, start="2022-01-03", volume=volumes)
    result = wish_strategy(history)
    assert isinstance(result, WishStrategyResult)
    assert result.qualifies is True
    assert result.volume_ok is True
    assert result.volume_ratio >= result.volume_requirement


def test_wish_strategy_fails_without_volume_confirmation() -> None:
    dates = pd.bdate_range("2022-01-03", periods=220)
    prices: list[float] = []
    for idx, _ in enumerate(dates):
        if idx < 60:
            prices.append(40.0 + 0.2 * idx)
        elif idx < 160:
            prices.append(51.0 - 0.02 * (idx - 60))
        else:
            prices.append(51.0 + 0.5 * (idx - 160))

    volumes = [1_000.0] * len(prices)
    volumes[-1] = 1_200.0  # insufficient volume surge

    history = build_history(prices, start="2022-01-03", volume=volumes)
    result = wish_strategy(history)
    assert result.qualifies is False
    assert result.volume_ok is False
