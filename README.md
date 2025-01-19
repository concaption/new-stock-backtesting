# Stock Analysis Tool

A powerful stock analysis tool that combines market data from Polygon.io with Google Trends search data to identify potential trading opportunities. This tool analyzes pre-market activity, gap-up percentages, and search trend changes to help identify stocks with significant movement potential.

## Features

- Combined analysis using both market data and search trends
- Pre-market volume analysis
- Gap-up percentage calculation
- Market capitalization filtering
- Google Trends hourly analysis (4-6 AM PST)
- Customizable filtering criteria
- Excel report generation with conditional formatting
- Colored console logging
- Concurrent processing with rate limiting
- Trading calendar aware (handles holidays and market closures)

## Prerequisites

- Python 3.8+
- Polygon.io API key
- SERP API key (for Google Trends data)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/concaption/new-stock-backtesting.git
cd new-stock-backtesting
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
```

Edit the `.env` file and add your API keys:
```
POLYGON_API_KEY=your_polygon_api_key
SERPAPI_KEY=your_serp_api_key
```

4. Create required directories:
```bash
mkdir -p data output logs
```

5. Add the holidays.csv file to the data directory with required fields:
- Date (YYYY-MM-DD format)
- Market Status (Closed/Early Close)

## Usage

### Basic Analysis

Analyze a single stock:
```bash
python main.py analyze --ticker AAPL
```

Analyze multiple stocks from a JSON file:
```bash
python main.py analyze --ticker-file tickers.json
```

### Analysis Options

- `--date`: Analysis date (YYYY-MM-DD). Defaults to today
- `--min-trends-change`: Minimum Google Trends change percentage (default: 50.0)
- `--min-premarket-volume`: Minimum premarket volume (default: 50000)
- `--min-price`: Minimum stock price (default: 3.0)
- `--min-gap-up`: Minimum gap up percentage (default: 2.0)
- `--min-market-cap`: Minimum market cap (can use B/M suffix, e.g., 100M)
- `--trends-only`: Only perform Google Trends analysis
- `--polygon-only`: Only perform Polygon analysis
- `--batch-size`: Number of concurrent requests (default: 5)
- `--verbose`: Increase verbosity level (-v or -vv)

Example with custom parameters:
```bash
python main.py analyze --ticker AAPL --min-trends-change 75 --min-gap-up 3 --min-market-cap 1B -v
```

## Output

The tool generates:
1. Excel files with analysis results in the `output` directory
2. Detailed logs in the `logs` directory
3. Console output with color-coded status messages

### Excel Output Format

The Excel output includes:
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

Positive and negative percentage values are highlighted in green and red respectively.

## Project Structure

```
├── src/
│   ├── combined_analyzer.py   # Main analysis logic
│   ├── excel_handler.py       # Excel file generation
│   ├── google_trends.py       # Google Trends analysis
│   ├── logger_config.py       # Logging configuration
│   ├── polygon.py            # Polygon.io API interface
│   └── trading_calendar.py   # Market calendar management
├── data/
│   └── holidays.csv          # Market holidays data
├── logs/                     # Log files directory
├── output/                   # Analysis results
├── main.py                   # CLI interface
├── requirements.txt          # Dependencies
└── README.md                 # This file
```

## Limitations

- SERP API rate limits apply to Google Trends analysis
- Polygon.io API rate limits apply to market data retrieval
- Historical data availability depends on your Polygon.io subscription level
- Pre-market data might be limited for some stocks

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Polygon.io for market data
- SERP API for Google Trends data
- Click for CLI interface
- OpenPyXL for Excel handling

## Author

@concaption - January 2025