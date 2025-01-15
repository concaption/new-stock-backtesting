# Stock Analysis Tool Documentation

## Overview

This tool combines market data from Polygon.io and search trends from Google Trends to analyze stocks and identify potential trading opportunities. It supports both real-time analysis and historical backtesting.

## Table of Contents
- [Installation](#installation)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)

## Installation

### Prerequisites
- Python 3.7 or higher
- Polygon.io API key
- SERP API key (for Google Trends)

### Setup

1. Clone the repository:
```bash
git clone https://github.com/concaption/new-stock-backtesting.git
cd stock-analysis-tool
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
# Create .env file
cp .env.example .env

# Edit .env file with your API keys
POLYGON_API_KEY=your_polygon_api_key
SERPAPI_KEY=your_serp_api_key
```

4. Create required directories:
```bash
mkdir -p data logs output
```

### Project Structure
```
stock-analysis-tool/
├── src/
│   ├── __init__.py
│   ├── trading_calendar.py
│   ├── polygon.py
│   ├── google_trends.py
│   ├── excel_handler.py
│   └── combined_analyzer.py
├── data/
│   └── holidays.csv
├── logs/
├── output/
├── main.py
├── requirements.txt
└── README.md
```

## Configuration

### holidays.csv Format
```csv
Date,Market Status,Description
2024-01-01,Closed,New Year's Day
2024-01-15,Closed,Martin Luther King Jr. Day
2024-02-19,Closed,Presidents Day
```

### Analysis Parameters
- `MIN_PREMARKET_VOLUME`: Minimum premarket trading volume (default: 50,000)
- `MIN_PRICE`: Minimum stock price (default: $3)
- `MIN_GAP_UP`: Minimum gap up percentage (default: 2%)
- `MIN_MARKET_CAP`: Minimum market capitalization (default: $100M)

## Usage

### Command Line Interface

1. Single Stock Analysis
```bash
# Basic analysis
python main.py analyze --ticker AAPL

# Custom parameters
python main.py analyze --ticker AAPL \
    --min-trends-change 75 \
    --min-market-cap 1B \
    --min-gap-up 3
```

2. Multiple Stock Analysis
```bash
# Using JSON file
python main.py analyze --ticker-file tickers.json

# Custom output directory
python main.py analyze --ticker-file tickers.json --output-dir ./results
```

3. Backtesting
```bash
# Basic backtest
python main.py backtest \
    --ticker AAPL \
    --start-date 2024-01-01 \
    --end-date 2024-01-15

# Advanced backtest
python main.py backtest \
    --ticker AAPL \
    --start-date 2024-01-01 \
    --end-date 2024-01-15 \
    --min-trends-change 75 \
    --min-gap-up 3 \
    --batch-size 10
```

4. Analysis Modes
```bash
# Only Google Trends analysis
python main.py analyze --ticker AAPL --trends-only

# Only market data analysis
python main.py analyze --ticker AAPL --polygon-only
```

### Common Options
- `--date`: Analysis date (YYYY-MM-DD)
- `--min-trends-change`: Minimum Google Trends change percentage
- `--min-premarket-volume`: Minimum premarket volume
- `--min-price`: Minimum stock price
- `--min-gap-up`: Minimum gap up percentage
- `--min-market-cap`: Minimum market cap (supports M/B notation)
- `--output-dir`: Directory for output files
- `--batch-size`: Number of concurrent requests
- `-v/--verbose`: Increase verbosity level

## API Documentation

### TradingCalendar
```python
from src.trading_calendar import TradingCalendar

calendar = TradingCalendar()
is_trading = calendar.is_trading_day(date)
last_day = calendar.get_last_trading_day(current_date)
```

### GoogleTrendsAnalyzer
```python
from src.google_trends import GoogleTrendsAnalyzer

analyzer = GoogleTrendsAnalyzer(trading_calendar)
results = await analyzer.analyze_trends(session, ticker, date)
```

### PolygonAPI
```python
from src.polygon import PolygonAPI

api = PolygonAPI(api_key)
data = await api.get_daily_open_close(session, ticker, date)
```

### CombinedAnalyzer
```python
from src.combined_analyzer import CombinedAnalyzer

analyzer = CombinedAnalyzer(polygon_analyzer, trends_analyzer)
results = await analyzer.analyze_stocks(tickers, date)
```

## Examples

### 1. Basic Stock Analysis
```python
import asyncio
from src.combined_analyzer import CombinedAnalyzer

async def analyze_stock():
    results = await analyzer.analyze_stocks(
        tickers=["AAPL"],
        date=datetime.now(),
        min_trends_change=50.0
    )
    return results

results = asyncio.run(analyze_stock())
```

### 2. Custom Analysis Parameters
```python
params = {
    "min_trends_change": 75.0,
    "min_premarket_volume": 100000,
    "min_gap_up": 3.0,
    "min_market_cap": 1_000_000_000
}

results = await analyzer.analyze_stocks(tickers, date, **params)
```

### 3. Backtesting Example
```python
backtest_results = await analyzer.backtest(
    tickers=["AAPL"],
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 1, 15)
)
```

## Output Formats

### 1. Excel Output
The tool generates Excel files with the following columns:
- Date
- Ticker
- Company Name
- Pre-market Volume
- Gap Up %
- Market Cap
- Open Price
- High Price
- Close Price
- Open to High %
- Open to Close %
- Trends Change %
- 4-5 AM Change %
- 5-6 AM Change %

### 2. Console Output
```
Google Trends Results:
AAPL:
  Total Change: 75.50%
  4-5 AM Change: 25.30%
  5-6 AM Change: 15.20%

Market Data Results:
AAPL (Apple Inc.):
  Premarket Volume: 1,234,567
  Gap Up: 2.50%
  Market Cap: $3,000,000,000,000
```

## Troubleshooting

### Common Issues

1. API Key Issues
```
Error: POLYGON_API_KEY environment variable not set
Solution: Ensure API key is set in .env file
```

2. Holiday Data Issues
```
Error: Invalid or missing holidays.csv file
Solution: Verify holidays.csv exists and has correct format
```

3. Rate Limiting
```
Error: API request failed: Rate limit exceeded
Solution: Adjust batch_size parameter or add delay between requests
```

### Logging

- Default log location: `logs/stock_analyzer_YYYYMMDD_HHMMSS.log`
- Verbosity levels:
  - Normal: Warnings and errors
  - `-v`: Info level (adds progress updates)
  - `-vv`: Debug level (adds detailed API interactions)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Submit a pull request