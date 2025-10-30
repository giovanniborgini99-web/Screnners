# Screnners

A lightweight stock screener inspired by the terminology used on the [Wishing Wealth Blog glossary](https://www.wishingwealthblog.com/glossary/).
The Green Line Breakout implementation also reflects the additional color
from TraderLion's [Green Line Breakout primer](https://traderlion.com/technical-analysis/green-line-breakout/),
requiring a base of monthly closes below the prior high before confirming a
weekly close breakout above that level.

The project provides:

* A Python API to compute the canonical glossary indicators such as the Green Line Breakout (GLB), Darvas Box breakout, RWB ribbon and Bongo signals.
* A command line interface for downloading data (via `yfinance`) or loading a cached CSV file and displaying the indicator outcomes.
* Unit tests demonstrating how the indicators behave using synthetic datasets.

## Dr. Wish GLB checklist

The screener follows Dr. Wish's walkthroughs by synthesising the individual
signals into a "Wish GLB Checklist" result. A ticker only passes when:

1. A monthly Green Line Breakout forms after at least three months of closes
   below the prior high.
2. Both the daily and weekly Bongo indicators are on, confirming momentum.
3. The RWB ribbon shows all short-term EMAs stacked above the long-term set.
4. Breakout volume is at least 1.5× the 50-day average, echoing the emphasis on
   surging demand highlighted in the [first walkthrough](https://www.youtube.com/watch?v=m90HHpbHzlw&t=152s)
   and the [companion session](https://www.youtube.com/watch?v=pV4rXBw3cYo&t=26s).

The checklist indicator exposes each contributing signal and the measured volume
ratio so you can quickly see why a candidate did or did not qualify.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Command line usage

Screen a ticker using Yahoo Finance data:

```bash
python -m screnners.cli AAPL MSFT --period 2y --interval 1d
```

Screen using a local CSV to avoid network access:

```bash
python -m screnners.cli --csv path/to/AAPL.csv --json
```

## Python API

```python
from screnners.data import YFinanceDataSource
from screnners.screener import GlossaryScreener

screener = GlossaryScreener(YFinanceDataSource())
result = screener.screen("AAPL")
for indicator in result.indicator_results:
    print(indicator.name, indicator.passed, indicator.details)
```

## Tests

```bash
pytest
```

The synthetic datasets in the tests intentionally emphasise the conditions described by the glossary to keep the behaviours deterministic.
