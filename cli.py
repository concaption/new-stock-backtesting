import os
import asyncio
import click
from datetime import datetime, timedelta
import json
import logging

# Import the existing implementation from the previous script
from main import (
    main, 
    PolygonAPI, 
    ExcelHandler, 
    StockAnalyzer, 
    MIN_PREMARKET_VOLUME, 
    MIN_PRICE, 
    MIN_GAP_UP, 
    MIN_MARKET_CAP
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
@click.command()
@click.option('--date', 
              default=None, 
              help='Analysis date (YYYY-MM-DD). Defaults to today.')
@click.option('--tickers', 
              default=None, 
              help='Comma-separated list of tickers to analyze (e.g., AAPL,PTON). Overrides JSON file.')
@click.option('--min-premarket-volume', 
              default=MIN_PREMARKET_VOLUME, 
              help='Minimum premarket volume for stock filtering.')
@click.option('--min-price', 
              default=MIN_PRICE, 
              help='Minimum stock price for filtering.')
@click.option('--min-gap-up', 
              default=MIN_GAP_UP, 
              help='Minimum gap up percentage for filtering.')
@click.option('--min-market-cap', 
              default=MIN_MARKET_CAP, 
              help='Minimum market capitalization for filtering.')
@click.option('--tickers-file', 
              default='ticker_data.json', 
              help='Path to JSON file containing tickers. Ignored if --tickers is specified.')
@click.option('--export/--no-export', 
              default=True, 
              help='Export results to Excel. Defaults to export.')
@click.option('--console-output/--no-console-output', 
              default=True, 
              help='Print results to console. Defaults to console output.')
def analyze_stocks(
    date, 
    tickers, 
    min_premarket_volume, 
    min_price, 
    min_gap_up, 
    min_market_cap, 
    tickers_file, 
    export,
    console_output
):
    """
    Analyze stocks based on specified criteria.
    
    Filters stocks by premarket volume, price, gap up percentage, and market capitalization.
    Optionally exports results to Excel and displays results in console.
    """
    # Use provided date or today's date
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    
    # Temporarily modify global constants for dynamic filtering
    global MIN_PREMARKET_VOLUME, MIN_PRICE, MIN_GAP_UP, MIN_MARKET_CAP
    MIN_PREMARKET_VOLUME = min_premarket_volume
    MIN_PRICE = min_price
    MIN_GAP_UP = min_gap_up
    MIN_MARKET_CAP = min_market_cap
    
    # Determine tickers to analyze
    if tickers:
        test_tickers = tickers.split(',')
    else:
        try:
            with open(tickers_file, 'r') as file:
                json_str = file.read()
            test_tickers = get_tickers_from_json(json_str)
            if not test_tickers:
                click.echo("No tickers found in JSON, using default list")
                test_tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "META"]  # fallback list
        except FileNotFoundError:
            click.echo("JSON file not found, using default list")
            test_tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "META"]  # fallback list
    
    try:
        results = asyncio.run(main(test_tickers, date))
        
        if not results:
            click.echo("\nNo stocks found matching criteria")
            return
        
        click.echo(f"\nFound {len(results)} matching stocks:")
        
        # Export to Excel if enabled
        if export:
            excel_handler = ExcelHandler()
            excel_handler.add_stock_data([result.dict() for result in results], date)
            filename = excel_handler.save(date)
            click.echo(f"\nData saved to {filename}")
        
        # Console output if enabled
        if console_output:
            for result in results:
                click.echo(f"\nResults for {result.ticker} ({result.company_name}):")
                click.echo(f"Premarket Volume: {result.premarket_volume:,.0f}")
                click.echo(f"Gap Up: {result.gap_up:.2f}%")
                click.echo(f"Market Cap: ${result.market_cap:,.2f}")
                click.echo(f"Open to High: {result.open_to_high:.2f}%")
                click.echo(f"Open to Close: {result.open_to_close:.2f}%")
        
    except Exception as e:
        logger.error(f"Script execution failed: {str(e)}")
        click.echo(f"Error: {str(e)}")

if __name__ == "__main__":
    analyze_stocks()
