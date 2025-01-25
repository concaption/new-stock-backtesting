"""
path: main.py
author: @concaption
date: 2025-01-15

This is the main CLI script that combines Polygon.io and Google Trends analysis.
It provides a command-line interface to analyze stocks using both market data and search trends,
with support for parallel processing of date ranges.
"""

import os
import asyncio
import click
from datetime import datetime, timedelta, date
import json
import logging
from typing import List, Optional
from pathlib import Path

# Import components
from src.trading_calendar import TradingCalendar, validate_holidays_csv
from src.polygon import PolygonAPI, StockAnalyzer, MIN_PREMARKET_VOLUME, MIN_PRICE, MIN_GAP_UP, MIN_MARKET_CAP
from src.google_trends import GoogleTrendsAnalyzer
from src.excel_handler import ExcelHandler
from src.combined_analyzer import CombinedAnalyzer
from src.logger_config import setup_logging

# Initialize logger
logger = logging.getLogger(__name__)

def initialize_logging(verbose: int, output_dir: str = "logs"):
    """Initialize logging based on verbosity level"""
    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Map verbose count to log levels
    levels = {
        0: logging.WARNING,  # Default
        1: logging.INFO,     # -v
        2: logging.DEBUG     # -vv
    }
    console_level = levels.get(verbose, logging.DEBUG)

    setup_logging(
        console_level=console_level,
        file_level=logging.DEBUG,
        log_dir=output_dir,
        app_name="stock_analyzer"
    )

def validate_date(ctx, param, value):
    """Validate date format and check if it's a trading day"""
    if value is None:
        return None
    try:
        date_obj = datetime.strptime(value, "%Y-%m-%d")
        calendar = TradingCalendar()
        if not calendar.is_trading_day(date_obj.date()):
            raise click.BadParameter(f"{value} is not a trading day")
        return date_obj
    except ValueError:
        raise click.BadParameter("Date must be in YYYY-MM-DD format")

def validate_market_cap(ctx, param, value):
    """Validate and convert market cap notation"""
    try:
        if isinstance(value, str):
            value = value.upper()
            if value.endswith('M'):
                value = float(value[:-1]) * 1_000_000
            elif value.endswith('B'):
                value = float(value[:-1]) * 1_000_000_000
            else:
                value = float(value)
        if value <= 0:
            raise ValueError
        return value
    except ValueError:
        raise click.BadParameter("Invalid market cap format")

def validate_percentage(ctx, param, value):
    """Validate percentage values"""
    try:
        value = float(value)
        if value < 0:
            raise ValueError("Percentage cannot be negative")
        return value
    except ValueError as e:
        raise click.BadParameter(str(e))

def validate_volume(ctx, param, value):
    """Validate volume values"""
    try:
        value = int(value)
        if value < 0:
            raise ValueError("Volume cannot be negative")
        return value
    except ValueError:
        raise click.BadParameter("Volume must be a positive integer")

def ensure_output_dir(output_dir: str):
    """Ensure output directory exists"""
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path

@click.group()
def cli():
    """Stock Analysis Tool combining Polygon.io and Google Trends data"""
    pass

@cli.command()
@click.option('--date', 
              callback=validate_date,
              help='Analysis date (YYYY-MM-DD)')
@click.option('--start-date', callback=validate_date,
              help='Start date for range analysis (YYYY-MM-DD)')
@click.option('--end-date', callback=validate_date,
              help='End date for range analysis (YYYY-MM-DD)')
@click.option('--max-parallel', default=5, type=int,
              help='Maximum number of parallel date analyses')
@click.option('--ticker', 
              help='Stock ticker to analyze.')
@click.option('--ticker-file',
              type=click.Path(exists=True),
              help='Path to JSON file containing tickers.')
@click.option('--min-trends-change',
              default=50.0,
              callback=validate_percentage,
              help='Minimum Google Trends change percentage.')
@click.option('--min-premarket-volume',
              default=MIN_PREMARKET_VOLUME,
              callback=validate_volume,
              help='Minimum premarket volume.')
@click.option('--min-price',
              default=MIN_PRICE,
              type=float,
              help='Minimum stock price.')
@click.option('--min-gap-up',
              default=MIN_GAP_UP,
              callback=validate_percentage,
              help='Minimum gap up percentage.')
@click.option('--min-market-cap',
              default=str(MIN_MARKET_CAP),
              callback=validate_market_cap,
              help='Minimum market cap')
@click.option('--trends-only', 
              is_flag=True,
              help='Only perform Google Trends analysis.')
@click.option('--polygon-only',
              is_flag=True,
              help='Only perform Polygon analysis.')
@click.option('--output-dir',
              type=click.Path(),
              default='output',
              help='Directory for output files.')
@click.option('--batch-size',
              default=5,
              type=int,
              help='Number of concurrent requests for trends analysis.')
@click.option('--verbose', '-v',
              count=True,
              help='Increase verbosity level.')
def analyze(
    date: Optional[datetime],
    start_date: Optional[datetime],
    end_date: Optional[datetime],
    max_parallel: int,
    ticker: str,
    ticker_file: str,
    min_trends_change: float,
    min_premarket_volume: float,
    min_price: float,
    min_gap_up: float,
    min_market_cap: float,
    trends_only: bool,
    polygon_only: bool,
    output_dir: str,
    batch_size: int,
    verbose: int
):
    """Analyze stocks using both Polygon.io and Google Trends data"""
    try:
        # Initialize logging and validate environment
        initialize_logging(verbose, output_dir)
        logger.debug("Starting analysis with parameters: %s", locals())
        
        # Validate date inputs
        if date and (start_date or end_date):
            raise click.UsageError("Cannot specify both single date and date range")
        if (start_date and not end_date) or (end_date and not start_date):
            raise click.UsageError("Must specify both start-date and end-date for range analysis")
        if start_date and end_date and start_date > end_date:
            raise click.UsageError("start-date must be before end-date")
        # Validate environment
        if not trends_only and not os.getenv("POLYGON_API_KEY"):
            raise click.UsageError("POLYGON_API_KEY environment variable not set")
        if not polygon_only and not os.getenv("SERPAPI_KEY"):
            raise click.UsageError("SERPAPI_KEY environment variable not set")
        if not validate_holidays_csv():
            raise click.UsageError("Invalid or missing holidays.csv file")

        # Get ticker(s)
        tickers = []
        if ticker:
            tickers = [ticker.upper()]
        elif ticker_file:
            try:
                with open(ticker_file, 'r') as f:
                    data = json.load(f)[0].get('json', {}).get('tickers', [])
                    if not data:
                        raise click.UsageError("No tickers found in file")
                    tickers = [t['ticker'] for t in data if 'ticker' in t]
            except Exception as e:
                logger.error(f"Error reading ticker file: {e}")
                raise click.UsageError(f"Error reading ticker file: {e}")
        else:
            raise click.UsageError("Either --ticker or --ticker-file must be provided")

        # Ensure output directory exists
        output_path = ensure_output_dir(output_dir)

        # Initialize components
        trading_calendar = TradingCalendar()
        polygon_api = PolygonAPI(os.getenv("POLYGON_API_KEY"))
        polygon_analyzer = StockAnalyzer(polygon_api, trading_calendar)
        trends_analyzer = GoogleTrendsAnalyzer(trading_calendar)
        combined_analyzer = CombinedAnalyzer(polygon_analyzer, trends_analyzer)

        # Generate dates to analyze
        dates_to_analyze = []
        if start_date and end_date:
            current = start_date
            while current <= end_date:
                if trading_calendar.is_trading_day(current.date()):
                    dates_to_analyze.append(current)
                current += timedelta(days=1)
        elif date:
            dates_to_analyze = [date]
        else:
            dates_to_analyze = [datetime.now()]

        click.echo(f"Analyzing {len(dates_to_analyze)} trading days...")

        async def analyze_single_date(date_param: datetime, semaphore: asyncio.Semaphore):
            try:
                async with semaphore:
                    logger.info(f"Analyzing date: {date_param.strftime('%Y-%m-%d')}")
                    results = await combined_analyzer.analyze_stocks(
                        tickers=tickers,
                        date_param=date_param,
                        min_trends_change=min_trends_change,
                        min_premarket_volume=min_premarket_volume,
                        min_price=min_price,
                        min_gap_up=min_gap_up,
                        min_market_cap=min_market_cap,
                        trends_only=trends_only,
                        polygon_only=polygon_only,
                        batch_size=batch_size
                    )
                    return date_param, results
            except Exception as e:
                logger.error(f"Error analyzing {date_param.strftime('%Y-%m-%d')}: {str(e)}")
                return date_param, None

        async def run_parallel_analysis():
            semaphore = asyncio.Semaphore(max_parallel)
            tasks = [analyze_single_date(d, semaphore) for d in dates_to_analyze]
            return await asyncio.gather(*tasks)

        # Run parallel analysis
        all_results = asyncio.run(run_parallel_analysis())

        # Process results
        total_combined = 0
        total_polygon = 0
        total_trends = 0

        for date_param, results in all_results:
            if not results:
                continue

            date_str = date_param.strftime("%Y-%m-%d")
            
            # Save combined results
            if results["combined_results"]:
                total_combined += len(results["combined_results"])
                excel_handler = ExcelHandler()
                excel_handler.add_stock_data(results["combined_results"], date_str)
                filename = output_path / f"analysis_{date_str}"
                excel_handler.save(str(filename))
                click.echo(f"Results for {date_str} saved to {filename}")

            # Print market data results
            if results["polygon_results"]:
                total_polygon += len(results["polygon_results"])
                click.echo(f"\nMarket Data Results for {date_str}:")
                for result in results["polygon_results"]:
                    click.echo(f"\n{result.ticker} ({result.company_name}):")
                    click.echo(f"  Premarket Volume: {result.premarket_volume:,.0f}")
                    click.echo(f"  Gap Up: {result.gap_up:.2f}%")
                    click.echo(f"  Market Cap: ${result.market_cap:,.2f}")
                    click.echo(f"  Open to High: {result.open_to_high:.2f}%")
                    click.echo(f"  Open to Close: {result.open_to_close:.2f}%")

            # Print trends results
            if results["trends_results"]:
                total_trends += len(results["trends_results"])
                click.echo(f"\nGoogle Trends Results for {date_str}:")
                for result in results["trends_results"]:
                    click.echo(f"\n{result['ticker']}:")
                    click.echo(f"  Total Change: {result['total_change']:.2f}%")
                    if result['hour_4_to_5_change']:
                        click.echo(f"  4-5 AM Change: {result['hour_4_to_5_change']:.2f}%")
                    if result['hour_5_to_6_change']:
                        click.echo(f"  5-6 AM Change: {result['hour_5_to_6_change']:.2f}%")

        # Print summary
        click.echo("\nAnalysis Summary:")
        click.echo(f"Total days analyzed: {len(dates_to_analyze)}")
        click.echo(f"Combined results found: {total_combined}")
        click.echo(f"Market data results found: {total_polygon}")
        click.echo(f"Trends results found: {total_trends}")

    except Exception as e:
        logger.error(f"Analysis failed: {str(e)}", exc_info=verbose > 1)
        raise click.ClickException(str(e))

# @cli.command()
# @click.option('--start-date',
#               required=True,
#               callback=validate_date,
#               help='Start date for backtesting (YYYY-MM-DD)')
# @click.option('--end-date',
#               required=True,
#               callback=validate_date,
#               help='End date for backtesting (YYYY-MM-DD)')
# @click.option('--ticker',
#               required=True,
#               help='Stock ticker to analyze')
# @click.option('--min-trends-change',
#               default=50.0,
#               callback=validate_percentage,
#               help='Minimum Google Trends change percentage')
# @click.option('--min-premarket-volume',
#               default=MIN_PREMARKET_VOLUME,
#               callback=validate_volume,
#               help='Minimum premarket volume')
# @click.option('--min-price',
#               default=MIN_PRICE,
#               type=float,
#               help='Minimum stock price')
# @click.option('--min-gap-up',
#               default=MIN_GAP_UP,
#               callback=validate_percentage,
#               help='Minimum gap up percentage')
# @click.option('--min-market-cap',
#               default=str(MIN_MARKET_CAP),
#               callback=validate_market_cap,
#               help='Minimum market cap (can use B/M suffix, e.g., 100M)')
# @click.option('--output-dir',
#               type=click.Path(),
#               default='output',
#               help='Directory for output files')
# @click.option('--batch-size',
#               default=5,
#               type=int,
#               help='Number of concurrent requests')
# @click.option('--verbose', '-v',
#               count=True,
#               help='Increase verbosity')
# def backtest(
#     start_date: datetime,
#     end_date: datetime,
#     ticker: str,
#     min_trends_change: float,
#     min_premarket_volume: float,
#     min_price: float,
#     min_gap_up: float,
#     min_market_cap: float,
#     output_dir: str,
#     batch_size: int,
#     verbose: int
# ):
#     """Perform backtesting analysis over a date range"""
#     try:
#         # Initialize logging
#         initialize_logging(verbose, output_dir)
#         logger.debug("Starting backtest with parameters: %s", locals())

#         # Validate environment and files
#         if not os.getenv("POLYGON_API_KEY"):
#             raise click.UsageError("POLYGON_API_KEY environment variable not set")
#         if not os.getenv("SERPAPI_KEY"):
#             raise click.UsageError("SERPAPI_KEY environment variable not set")
#         if not validate_holidays_csv():
#             raise click.UsageError("Invalid or missing holidays.csv file")

#         # Ensure output directory exists
#         output_path = ensure_output_dir(output_dir)

#         # Initialize components
#         trading_calendar = TradingCalendar()
#         polygon_api = PolygonAPI(os.getenv("POLYGON_API_KEY"))
#         polygon_analyzer = StockAnalyzer(polygon_api, trading_calendar)
#         trends_analyzer = GoogleTrendsAnalyzer(trading_calendar)
#         combined_analyzer = CombinedAnalyzer(polygon_analyzer, trends_analyzer)

#         # Run backtesting
#         click.echo(f"\nStarting backtesting for {ticker} from {start_date.date()} to {end_date.date()}")
#         results = asyncio.run(combined_analyzer.backtest(
#             tickers=[ticker.upper()],
#             start_date=start_date,
#             end_date=end_date,
#             min_trends_change=min_trends_change,
#             min_premarket_volume=min_premarket_volume,
#             min_price=min_price,
#             min_gap_up=min_gap_up,
#             min_market_cap=min_market_cap,
#             batch_size=batch_size
#         ))

#         if not results:
#             click.echo("No matching results found during the backtest period")
#             return

#         # Save results
#         excel_handler = ExcelHandler()
#         filename = output_path / f"backtest_{ticker}_{start_date.date()}_{end_date.date()}.xlsx"
        
#         for result in results:
#             excel_handler.add_stock_data([result], result['date'])
        
#         excel_handler.save(str(filename))
#         click.echo(f"\nBacktest results saved to {filename}")

#         # Print summary statistics
#         click.echo("\nBacktest Summary:")
#         total_days = (end_date - start_date).days + 1
#         click.echo(f"Total days analyzed: {total_days}")
#         click.echo(f"Days with matching criteria: {len(results)}")
        
#         if results:
#             # Calculate statistics
#             total_gap_up = sum(r['gap_up'] for r in results)
#             avg_gap_up = total_gap_up / len(results)
#             total_trends_change = sum(r['trends_change'] for r in results)
#             avg_trends_change = total_trends_change / len(results)
#             avg_volume = sum(r['premarket_volume'] for r in results) / len(results)
            
#             # Calculate success rates
#             profitable_trades = sum(1 for r in results if r['open_to_close'] > 0)
#             success_rate = (profitable_trades / len(results)) * 100
            
#             # Print statistics
#             click.echo(f"\nAverage Statistics:")
#             click.echo(f"  Gap Up: {avg_gap_up:.2f}%")
#             click.echo(f"  Trends Change: {avg_trends_change:.2f}%")
#             click.echo(f"  Premarket Volume: {avg_volume:,.0f}")
#             click.echo(f"  Success Rate: {success_rate:.1f}%")
            
#             # Print best performing day
#             best_day = max(results, key=lambda x: x['open_to_close'])
#             click.echo(f"\nBest Performing Day:")
#             click.echo(f"  Date: {best_day['date']}")
#             click.echo(f"  Open to Close: {best_day['open_to_close']:.2f}%")
#             click.echo(f"  Gap Up: {best_day['gap_up']:.2f}%")
#             click.echo(f"  Trends Change: {best_day['trends_change']:.2f}%")

#     except Exception as e:
#         logger.error(f"Backtesting failed: {str(e)}", exc_info=verbose > 1)
#         raise click.ClickException(str(e))

if __name__ == "__main__":
    cli()