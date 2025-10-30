"""Indicator implementations inspired by the Wishing Wealth glossary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Tuple

import numpy as np
import pandas as pd

from .data import PriceHistory
from .models import IndicatorResult


def _ensure_min_length(series: pd.Series, min_length: int, name: str) -> None:
    if len(series) < min_length:
        raise ValueError(f"{name} requires at least {min_length} observations")


def ema(series: pd.Series, span: int) -> pd.Series:
    """Exponential moving average."""

    return series.ewm(span=span, adjust=False).mean()


def sma(series: pd.Series, window: int) -> pd.Series:
    """Simple moving average."""

    return series.rolling(window=window, min_periods=window).mean()


@dataclass(slots=True)
class GreenLineBreakoutResult:
    """Outcome of the green line breakout detection."""

    breakout: bool
    prior_high: float
    last_close: float
    months_since_prior_high: float
    base_months: int


def green_line_breakout(history: PriceHistory, min_base_months: int = 3) -> GreenLineBreakoutResult:
    """Detect a Green Line Breakout (GLB).

    The implementation follows the Wishing Wealth and TraderLion definitions:
    identify the highest prior monthly close (the green line), require at least
    ``min_base_months`` of subsequent monthly closes that stay below that level,
    and confirm that the latest weekly close breaks above the green line.
    """

    monthly_close = history.data["Close"].resample("M").last().dropna()
    _ensure_min_length(monthly_close, min_base_months + 2, "green_line_breakout")

    prior_closes = monthly_close.iloc[:-1]
    if prior_closes.empty:
        last_close = float(monthly_close.iloc[-1])
        return GreenLineBreakoutResult(False, float("nan"), last_close, float("nan"), 0)

    prior_high = float(prior_closes.max())
    last_high_idx = prior_closes[prior_closes == prior_high].index[-1]

    base_mask = (monthly_close.index > last_high_idx) & (monthly_close.index < monthly_close.index[-1])
    base_closes = monthly_close.loc[base_mask]
    base_months = int(base_closes.size)

    last_period = monthly_close.index[-1].to_period("M")
    prior_period = last_high_idx.to_period("M")
    months_since_prior_high = float(last_period.ordinal - prior_period.ordinal)

    weekly_close = history.data["Close"].resample("W-FRI").last().dropna()
    if weekly_close.empty:
        weekly_close = history.data["Close"].iloc[[-1]]

    last_close = float(weekly_close.iloc[-1])
    base_below_prior = bool(base_closes.empty or (base_closes < prior_high).all())
    breakout = bool(
        last_close > prior_high
        and base_months >= min_base_months
        and base_below_prior
    )

    return GreenLineBreakoutResult(
        breakout,
        prior_high,
        last_close,
        months_since_prior_high,
        base_months,
    )


@dataclass(slots=True)
class DarvasBoxResult:
    """Outcome of Darvas Box breakout detection."""

    breakout: bool
    box_high: float
    box_low: float
    breakout_margin: float


def darvas_box_breakout(
    history: PriceHistory,
    lookback_days: int = 65,
    max_volatility: float = 0.25,
    breakout_buffer: float = 0.02,
) -> DarvasBoxResult:
    """Detect a Darvas Box breakout.

    We treat the past ``lookback_days`` as the reference box. The box is valid
    when the price range is relatively tight (``max_volatility`` controls the
    acceptable spread). A breakout happens when the latest close exceeds the
    upper box by ``breakout_buffer``.
    """

    close = history.data["Close"]
    _ensure_min_length(close, lookback_days, "darvas_box_breakout")

    reference = close.iloc[-lookback_days:]
    box_high = float(reference.max())
    box_low = float(reference.min())
    volatility = (box_high - box_low) / box_low if box_low else np.inf
    last_close = float(reference.iloc[-1])
    breakout = volatility <= max_volatility and last_close >= box_high * (1 + breakout_buffer)

    return DarvasBoxResult(breakout, box_high, box_low, last_close / box_high - 1)


@dataclass(slots=True)
class RWBResult:
    """Outcome of evaluating the RWB moving average pattern."""

    rwb: bool
    ribbon_spread: float


def rwb_pattern(history: PriceHistory) -> RWBResult:
    """Check for the RWB (red-white-blue) pattern.

    The RWB pattern, as described by Wishing Wealth, consists of six shorter-term
    (3, 5, 8, 10, 12, 15 day) exponential moving averages stacked above six
    longer-term (30, 35, 40, 45, 50, 60 day) moving averages with price above all.
    """

    close = history.data["Close"]
    short_spans = (3, 5, 8, 10, 12, 15)
    long_spans = (30, 35, 40, 45, 50, 60)
    shortest = ema(close, min(short_spans))
    longest = ema(close, max(long_spans))
    _ensure_min_length(close, max(long_spans) + 5, "rwb_pattern")

    short_emas = pd.DataFrame({span: ema(close, span) for span in short_spans})
    long_emas = pd.DataFrame({span: ema(close, span) for span in long_spans})
    latest_short = short_emas.iloc[-1]
    latest_long = long_emas.iloc[-1]
    latest_price = float(close.iloc[-1])

    rwb = bool((latest_short.min() > latest_long.max()) and latest_price > latest_short.max())
    ribbon_spread = float(latest_short.mean() - latest_long.mean())

    return RWBResult(rwb, ribbon_spread)


@dataclass(slots=True)
class BongoResult:
    """Representation of the Bongo indicator on a timeframe."""

    timeframe: str
    is_on: bool
    macd: float
    signal: float
    slope_positive: bool


def _macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series]:
    fast_ema = ema(series, fast)
    slow_ema = ema(series, slow)
    macd_line = fast_ema - slow_ema
    signal_line = ema(macd_line, signal)
    return macd_line, signal_line


def bongo(history: PriceHistory, timeframe: str = "D") -> BongoResult:
    """Compute a simplified Bongo indicator.

    The Bongo turns "on" when the MACD is above its signal line and the slope
    of the 10-day moving average is positive. For weekly data we resample to
    Friday closes before computing the same logic.
    """

    if timeframe not in {"D", "W"}:
        raise ValueError("timeframe must be 'D' or 'W'")

    close = history.data["Close"]
    if timeframe == "W":
        close = close.resample("W-FRI").last()

    _ensure_min_length(close, 50, "bongo")

    macd_line, signal_line = _macd(close)
    ma10 = sma(close, 10)
    slope = ma10.iloc[-1] - ma10.iloc[-3]
    is_on = bool(macd_line.iloc[-1] > signal_line.iloc[-1] and slope > 0)

    return BongoResult(timeframe, is_on, float(macd_line.iloc[-1]), float(signal_line.iloc[-1]), bool(slope > 0))


@dataclass(slots=True)
class WishStrategyResult:
    """Represents Dr. Wish's GLB checklist outcome."""

    qualifies: bool
    glb: GreenLineBreakoutResult
    rwb: RWBResult
    bongo_daily: BongoResult
    bongo_weekly: BongoResult
    last_volume: float
    average_volume: float
    volume_ratio: float
    volume_requirement: float
    volume_ok: bool


def wish_strategy(
    history: PriceHistory,
    *,
    glb: Optional[GreenLineBreakoutResult] = None,
    rwb: Optional[RWBResult] = None,
    bongo_daily: Optional[BongoResult] = None,
    bongo_weekly: Optional[BongoResult] = None,
    volume_window: int = 50,
    breakout_volume_multiple: float = 1.5,
) -> WishStrategyResult:
    """Evaluate the full Dr. Wish GLB strategy checklist.

    The video walkthroughs emphasise combining the GLB with both Bongo
    timeframes, the RWB ribbon and a breakout on surging volume. We honour that
    playbook by confirming each component before declaring a qualifying setup.
    """

    if glb is None:
        glb = green_line_breakout(history)
    if rwb is None:
        rwb = rwb_pattern(history)
    if bongo_daily is None:
        bongo_daily = bongo(history, timeframe="D")
    if bongo_weekly is None:
        bongo_weekly = bongo(history, timeframe="W")

    volume_series = history.data.get("Volume")
    last_volume = float("nan")
    average_volume = float("nan")
    volume_ratio = float("nan")
    volume_ok = False

    if volume_series is not None:
        volume_series = volume_series.dropna()
        if not volume_series.empty:
            last_volume = float(volume_series.iloc[-1])
            if len(volume_series) >= volume_window:
                average_volume = float(volume_series.rolling(window=volume_window).mean().iloc[-1])
                if average_volume > 0:
                    volume_ratio = last_volume / average_volume
                elif last_volume > 0:
                    volume_ratio = float("inf")
                volume_ok = bool(volume_ratio >= breakout_volume_multiple)

    qualifies = bool(
        glb.breakout
        and rwb.rwb
        and bongo_daily.is_on
        and bongo_weekly.is_on
        and volume_ok
    )

    return WishStrategyResult(
        qualifies=qualifies,
        glb=glb,
        rwb=rwb,
        bongo_daily=bongo_daily,
        bongo_weekly=bongo_weekly,
        last_volume=last_volume,
        average_volume=average_volume,
        volume_ratio=volume_ratio,
        volume_requirement=breakout_volume_multiple,
        volume_ok=volume_ok,
    )


def build_indicator_results(history: PriceHistory) -> Iterable[IndicatorResult]:
    """Evaluate the canonical glossary indicators."""

    glb = green_line_breakout(history)
    darvas = darvas_box_breakout(history)
    rwb = rwb_pattern(history)
    bongo_daily = bongo(history, timeframe="D")
    bongo_weekly = bongo(history, timeframe="W")
    wish = wish_strategy(
        history,
        glb=glb,
        rwb=rwb,
        bongo_daily=bongo_daily,
        bongo_weekly=bongo_weekly,
    )

    return [
        IndicatorResult(
            name="Green Line Breakout",
            passed=glb.breakout,
            details={
                "prior_high": glb.prior_high,
                "last_close": glb.last_close,
                "months_since_prior_high": glb.months_since_prior_high,
                "base_months": glb.base_months,
            },
        ),
        IndicatorResult(
            name="Darvas Box Breakout",
            passed=darvas.breakout,
            details={
                "box_high": darvas.box_high,
                "box_low": darvas.box_low,
                "breakout_margin": darvas.breakout_margin,
            },
        ),
        IndicatorResult(
            name="RWB Pattern",
            passed=rwb.rwb,
            details={"ribbon_spread": rwb.ribbon_spread},
        ),
        IndicatorResult(
            name="Bongo Daily",
            passed=bongo_daily.is_on,
            details={
                "macd": bongo_daily.macd,
                "signal": bongo_daily.signal,
                "slope_positive": bongo_daily.slope_positive,
            },
        ),
        IndicatorResult(
            name="Bongo Weekly",
            passed=bongo_weekly.is_on,
            details={
                "macd": bongo_weekly.macd,
                "signal": bongo_weekly.signal,
                "slope_positive": bongo_weekly.slope_positive,
            },
        ),
        IndicatorResult(
            name="Wish GLB Checklist",
            passed=wish.qualifies,
            details={
                "glb": wish.glb.breakout,
                "rwb": wish.rwb.rwb,
                "bongo_daily": wish.bongo_daily.is_on,
                "bongo_weekly": wish.bongo_weekly.is_on,
                "last_volume": wish.last_volume,
                "average_volume": wish.average_volume,
                "volume_ratio": wish.volume_ratio,
                "volume_requirement": wish.volume_requirement,
                "volume_ok": wish.volume_ok,
            },
        ),
    ]


__all__ = [
    "GreenLineBreakoutResult",
    "DarvasBoxResult",
    "RWBResult",
    "BongoResult",
    "WishStrategyResult",
    "green_line_breakout",
    "darvas_box_breakout",
    "rwb_pattern",
    "bongo",
    "wish_strategy",
    "build_indicator_results",
]
