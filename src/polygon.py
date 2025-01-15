"""
path: src/polygon.py
author: @concaption
date: 2025-01-15

This script is a part of a stock analysis tool that uses the Polygon.io API to analyze stock data and identify potential trading opportunities. The script fetches minute-by-minute stock data, calculates pre-market volume, gap up percentage, and other metrics to determine if a stock meets the analysis criteria.
"""
import os
import asyncio
from datetime import datetime
import aiohttp
from pydantic import BaseModel, Field, field_validator
from dotenv import load_dotenv
import logging
import json
from typing import List, Optional
from .trading_calendar import TradingCalendar, validate_holidays_csv
from .excel_handler import ExcelHandler
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import os
import aiohttp

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - file: %(filename)s - func: %(funcName)s - line: %(lineno)d - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")

# Constants for stock filtering criteria
MIN_PREMARKET_VOLUME = 50000
MIN_PRICE = 3
MIN_GAP_UP = 2
MIN_MARKET_CAP = 100_000_000  # 100M


# Pydantic Models
class TickerDetails(BaseModel):
    """Model for storing ticker details from Polygon API"""
    market_cap: float = Field(default=0)
    weighted_shares_outstanding: int = Field(default=0)
    name: str = Field(default="")
    primary_exchange: str = Field(default="")

class StockAggregate(BaseModel):
    """Model for minute-by-minute stock data"""
    o: float = Field(description="Open price")
    h: float = Field(description="High price")
    l: float = Field(description="Low price")
    c: float = Field(description="Close price")
    v: float = Field(description="Volume")
    t: int = Field(description="Timestamp in milliseconds")
    vw: float = Field(description="Volume weighted average price")

class DailyOpenClose(BaseModel):
    """Model for daily open/close data from Polygon API"""
    afterHours: Optional[float] = None
    close: float
    high: float
    low: float
    open: float
    preMarket: Optional[float] = None
    status: str
    symbol: str
    volume: Optional[float] = None
    from_: str = Field(alias='from')

class PremarketData(BaseModel):
    """Model for storing analyzed stock data"""
    ticker: str
    company_name: str = ""
    premarket_volume: float
    gap_up: float
    market_cap: float
    open_price: float
    high_price: float
    close_price: float
    open_to_high: float
    open_to_close: float

    @field_validator('premarket_volume', 'market_cap', 'open_price')
    def validate_positive(cls, v):
        """Ensure values are positive"""
        if v < 0:
            raise ValueError("Value must be positive")
        return v

class PolygonAPI:
    """Handles all interactions with the Polygon.io API"""
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.polygon.io"

    async def _make_request(self, session: aiohttp.ClientSession, endpoint: str) -> Optional[dict]:
        """Make an authenticated request to the Polygon.io API"""
        url = f"{self.base_url}{endpoint}"
        if '?' in endpoint:
            url = f"{url}&apiKey={self.api_key}"
        else:
            url = f"{url}?apiKey={self.api_key}"
        
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                logger.error(f"Error {response.status} for {url}: {await response.text()}")
                return None
        except Exception as e:
            logger.error(f"Exception during request to {url}: {str(e)}")
            return None

    async def get_ticker_details(self, session: aiohttp.ClientSession, ticker: str) -> Optional[TickerDetails]:
        """Fetch details for a specific ticker"""
        endpoint = f"/v3/reference/tickers/{ticker}"
        response = await self._make_request(session, endpoint)
        
        if response and response.get("status") == "OK" and response.get("results"):
            return TickerDetails(**response["results"])
        return None

    async def get_aggregates(
        self,
        session: aiohttp.ClientSession,
        ticker: str,
        from_date: str,
        to_date: str,
        multiplier: int = 1,
        timespan: str = "minute"
    ) -> List[StockAggregate]:
        """Fetch aggregate stock data for a given time period"""
        endpoint = f"/v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/{from_date}/{to_date}?adjusted=true&sort=asc"
        response = await self._make_request(session, endpoint)
        
        if response and response.get("status") == "OK" and response.get("results"):
            return [StockAggregate(**agg) for agg in response["results"]]
        return []
    
    async def get_daily_open_close(
        self,
        session: aiohttp.ClientSession,
        ticker: str,
        date_str: str,
        adjusted: bool = True
    ) -> Optional[DailyOpenClose]:
        """Fetch daily open/close data for a stock"""
        endpoint = f"/v1/open-close/{ticker}/{date_str}?adjusted={str(adjusted).lower()}"
        response = await self._make_request(session, endpoint)
        
        if response and response.get("status") == "OK":
            return DailyOpenClose(**response)
        return None

class StockAnalyzer:
    """Analyzes stock data to identify potential trading opportunities"""
    def __init__(self, api: PolygonAPI, calendar: TradingCalendar):
        self.api = api
        self.calendar = calendar

    def calculate_premarket_volume(self, aggregates: List[StockAggregate]) -> float:
        """Calculate total pre-market volume from minute-by-minute data"""
        premarket_volume = 0
        for agg in aggregates:
            timestamp = datetime.fromtimestamp(agg.t / 1000)
            hour = timestamp.hour
            minute = timestamp.minute
            if (4 <= hour < 9) or (hour == 9 and minute < 30):
                premarket_volume += agg.v
        return premarket_volume

    def calculate_gap_up(self, prev_close: float, current_open: float) -> float:
        """Calculate percentage gap up between previous close and current open"""
        if prev_close == 0:
            return 0
        return ((current_open - prev_close) / prev_close) * 100

    async def analyze_stock(
        self,
        session: aiohttp.ClientSession,
        ticker: str,
        date_str: str
    ) -> Optional[PremarketData]:
        """Perform comprehensive analysis of a stock for a given date"""
        try:
            logger.info(f"Analyzing {ticker} for {date_str}")
            
            current_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            if not self.calendar.is_trading_day(current_date):
                logger.warning(f"{date_str} is not a trading day for {ticker}")
                return None
            
            # Get ticker details
            details = await self.api.get_ticker_details(session, ticker)
            if not details:
                logger.warning(f"No ticker details found for {ticker}")
                return None

            # Get previous trading day's data
            prev_trading_date = self.calendar.get_last_trading_day(current_date)
            previous_daily_data = await self.api.get_daily_open_close(
                session, ticker, prev_trading_date.strftime("%Y-%m-%d")
            )
            if not previous_daily_data:
                logger.warning(f"No previous day data found for {ticker}")
                return None

            # Get current day's data
            current_daily_data = await self.api.get_daily_open_close(session, ticker, date_str)
            if not current_daily_data:
                logger.warning(f"No current day data found for {ticker}")
                return None

            # Get minute data for premarket volume
            current_aggregates = await self.api.get_aggregates(
                session, ticker, date_str, date_str, 1, "minute"
            )

            # Calculate all metrics
            premarket_volume = self.calculate_premarket_volume(current_aggregates)
            gap_up = self.calculate_gap_up(previous_daily_data.close, current_daily_data.open)
            market_cap = details.weighted_shares_outstanding * current_daily_data.open
            open_to_high = ((current_daily_data.high - current_daily_data.open) / current_daily_data.open) * 100
            open_to_close = ((current_daily_data.close - current_daily_data.open) / current_daily_data.open) * 100

            # Check if stock meets criteria
            if (premarket_volume >= MIN_PREMARKET_VOLUME and
                current_daily_data.open >= MIN_PRICE and
                gap_up >= MIN_GAP_UP and
                market_cap >= MIN_MARKET_CAP):
                logger.info(f"{ticker} meets criteria")
                logger.debug(f"Premarket Volume: {premarket_volume}")
                logger.debug(f"Gap Up: {gap_up}")
                logger.debug(f"Market Cap: {market_cap}")
                logger.debug(f"Open to High: {open_to_high}")
                logger.debug(f"Open to Close: {open_to_close}")
                logger.debug(f"Details: {details}")
                return PremarketData(
                    ticker=ticker,
                    company_name=details.name,
                    premarket_volume=premarket_volume,
                    gap_up=gap_up,
                    market_cap=market_cap,
                    open_price=current_daily_data.open,
                    high_price=current_daily_data.high,
                    close_price=current_daily_data.close,
                    open_to_high=open_to_high,
                    open_to_close=open_to_close
                )
            
            logger.info(f"{ticker} did not meet criteria")
            return None

        except Exception as e:
            logger.error(f"Error analyzing {ticker} for {date_str}: {str(e)}")
            return None

async def main(tickers: List[str], date_str: str) -> List[PremarketData]:
    """
    Main function to analyze multiple stocks concurrently
    
    Args:
        tickers: List of stock ticker symbols to analyze
        date_str: Date to analyze stocks for (YYYY-MM-DD)
        
    Returns:
        List[PremarketData]: List of stocks that meet the analysis criteria
    """
    logger.info(f"Starting analysis for {len(tickers)} tickers on {date_str}")
    
    # Initialize API and calendar
    api = PolygonAPI(POLYGON_API_KEY)
    calendar = TradingCalendar()
    analyzer = StockAnalyzer(api, calendar)
    
    # Check if date is a trading day
    analysis_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    if not calendar.is_trading_day(analysis_date):
        logger.warning(f"{date_str} is not a trading day. Please select a valid trading day.")
        return []
    
    async with aiohttp.ClientSession() as session:
        # Create tasks for concurrent analysis of all tickers
        tasks = [analyzer.analyze_stock(session, ticker, date_str) for ticker in tickers]
        results = await asyncio.gather(*tasks)
        
        # Filter out None results and sort by gap up percentage
        filtered_results = [r for r in results if r is not None]
        sorted_results = sorted(filtered_results, key=lambda x: x.gap_up, reverse=True)
        
        logger.info(f"Analysis complete. Found {len(filtered_results)} matching stocks")
        return sorted_results

def get_tickers_from_json(json_data: str) -> List[str]:
    """
    Extract ticker symbols from JSON data
    
    Args:
        json_data: JSON string containing ticker data
        
    Returns:
        List[str]: List of ticker symbols
    """
    try:
        data = json.loads(json_data)
        if isinstance(data, list) and len(data) > 0:
            json_data = data[0].get('json', {})
            tickers_data = json_data.get('tickers', [])
            return [ticker['ticker'] for ticker in tickers_data if 'ticker' in ticker]
        return []
    except Exception as e:
        logger.error(f"Error extracting tickers: {e}")
        return []


if __name__ == "__main__":
    print("Stock Analysis Starting...")
    
    # Validate environment and files
    if not POLYGON_API_KEY:
        logger.error("POLYGON_API_KEY not found in environment variables")
        exit(1)
        
    if not validate_holidays_csv():
        logger.error("Invalid or missing holidays.csv file")
        exit(1)
    
    print(f"API Key present: {bool(POLYGON_API_KEY)}")
    
    # Load tickers from JSON file
    try:
        with open('ticker_data.json', 'r') as file:
            json_str = file.read()
        test_tickers = get_tickers_from_json(json_str)
        if not test_tickers:
            logger.warning("No tickers found in JSON, using default list")
            test_tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "META"]  # fallback list
    except FileNotFoundError:
        logger.warning("JSON file not found, using default list")
        test_tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "META"]  # fallback list
    
    # Use current date for analysis
    # test_date = datetime.now().strftime("%Y-%m-%d")
    test_date = "2024-01-04"
    
    try:
        # Run the analysis
        results = asyncio.run(main(test_tickers, test_date))
        
        if not results:
            print("\nNo stocks found matching criteria")
        else:
            print(f"\nFound {len(results)} matching stocks:")
            
            # Initialize Excel handler and save results
            excel_handler = ExcelHandler()
            excel_handler.add_stock_data([result.model_dump() for result in results], test_date)
            filename = excel_handler.save(test_date)
            print(f"\nData saved to {filename}")
            
            # Print detailed results to console
            for result in results:
                print(f"\nResults for {result.ticker} ({result.company_name}):")
                print(f"Premarket Volume: {result.premarket_volume:,.0f}")
                print(f"Gap Up: {result.gap_up:.2f}%")
                print(f"Market Cap: ${result.market_cap:,.2f}")
                print(f"Open to High: {result.open_to_high:.2f}%")
                print(f"Open to Close: {result.open_to_close:.2f}%")
                
    except Exception as e:
        logger.error(f"Script execution failed: {str(e)}")
        raise