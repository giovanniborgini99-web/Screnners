"""Core package for Wishing Wealth inspired stock screener."""

from importlib import metadata

from .data import DataSource, PriceHistory, YFinanceDataSource, load_csv
from .indicators import (
    BongoResult,
    DarvasBoxResult,
    GreenLineBreakoutResult,
    RWBResult,
    bongo,
    darvas_box_breakout,
    green_line_breakout,
    rwb_pattern,
    wish_strategy,
    WishStrategyResult,
)
from .models import IndicatorResult, ScreeningResult
from .screener import GlossaryScreener


def get_version() -> str:
    """Return the installed package version."""

    try:
        return metadata.version("screnners")
    except metadata.PackageNotFoundError:  # pragma: no cover - used during development
        return "0.0.0"


__all__ = [
    "DataSource",
    "PriceHistory",
    "YFinanceDataSource",
    "load_csv",
    "BongoResult",
    "DarvasBoxResult",
    "GreenLineBreakoutResult",
    "RWBResult",
    "WishStrategyResult",
    "bongo",
    "darvas_box_breakout",
    "green_line_breakout",
    "rwb_pattern",
    "wish_strategy",
    "IndicatorResult",
    "ScreeningResult",
    "GlossaryScreener",
    "get_version",
]
