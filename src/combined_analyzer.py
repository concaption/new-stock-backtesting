"""
path: src/combined_analyzer.py
author: @concaption
date: 2025-01-15

This module combines the functionality of Polygon.io and Google Trends analysis.
It provides a unified interface to analyze stocks using both market data and search trends,
with options to run analyses independently or combined.
"""

from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Union
import logging
import aiohttp
import asyncio

from src.polygon import StockAnalyzer, PremarketData
from src.google_trends import GoogleTrendsAnalyzer
from src.trading_calendar import TradingCalendar

# Initialize logger
logger = logging.getLogger(__name__)

class CombinedAnalyzer:
    """
    Combines Polygon and Google Trends analysis
    
    Attributes:
        polygon: StockAnalyzer instance for market data
        trends: GoogleTrendsAnalyzer instance for search trends
        trading_calendar: Calendar instance shared between analyzers
    """
    def __init__(self, polygon_analyzer: StockAnalyzer, trends_analyzer: GoogleTrendsAnalyzer):
        """
        Initialize the combined analyzer
        
        Args:
            polygon_analyzer: StockAnalyzer instance for market data
            trends_analyzer: GoogleTrendsAnalyzer instance for search trends
        """
        self.polygon = polygon_analyzer
        self.trends = trends_analyzer
        self.trading_calendar = trends_analyzer.trading_calendar

    def _convert_to_datetime(self, date_param: Union[datetime, date]) -> datetime:
        """Convert date to datetime if needed"""
        if isinstance(date_param, date) and not isinstance(date_param, datetime):
            return datetime.combine(date_param, datetime.min.time())
        return date_param

    def _convert_to_date(self, date_param: Union[datetime, date]) -> date:
        """Convert datetime to date if needed"""
        return date_param.date() if isinstance(date_param, datetime) else date_param

    async def analyze_stocks(
        self,
        tickers: List[str],
        date_param: Union[datetime, date],
        min_trends_change: float = 50.0,
        min_premarket_volume: float = 50000,
        min_price: float = 3,
        min_gap_up: float = 2,
        min_market_cap: float = 100_000_000,
        trends_only: bool = False,
        polygon_only: bool = False,
        batch_size: int = 5
    ) -> Dict:
        """
        Perform combined analysis using both services
        
        Args:
            tickers: List of tickers to analyze
            date_param: Date to analyze
            min_trends_change: Minimum Google Trends change percentage
            min_premarket_volume: Minimum premarket volume
            min_price: Minimum stock price
            min_gap_up: Minimum gap up percentage
            min_market_cap: Minimum market capitalization
            trends_only: Only perform Google Trends analysis
            polygon_only: Only perform Polygon analysis
            batch_size: Number of concurrent requests for trends analysis
            
        Returns:
            Dict containing trends_results, polygon_results, and combined_results
        """
        results = {
            "trends_results": [],
            "polygon_results": [],
            "combined_results": []
        }

        try:
            date_obj = self._convert_to_datetime(date_param)
            
            if not self.trading_calendar.is_trading_day(date_obj.date()):
                logger.warning(f"{date_obj.date()} is not a trading day")
                return results

            async with aiohttp.ClientSession() as session:
                # Step 1: Google Trends Analysis
                if not polygon_only:
                    logger.info("Starting Google Trends analysis...")
                    trends_results = await self.trends.analyze_multiple_tickers(
                        tickers,
                        date_obj,
                        min_trends_change,
                        batch_size
                    )
                    results["trends_results"] = trends_results

                    if trends_results:
                        logger.info(f"Found {len(trends_results)} tickers with significant trends changes")
                        trending_tickers = [result["ticker"] for result in trends_results]
                        tickers = trending_tickers if not trends_only else []
                    else:
                        logger.info("No tickers met the trends criteria")
                        return results

                # Step 2: Polygon Market Data Analysis
                if not trends_only and tickers:
                    logger.info("Starting Polygon market data analysis...")
                    polygon_results = []
                    
                    for ticker in tickers:
                        try:
                            result = await self.polygon.analyze_stock(
                                session,
                                ticker,
                                date_obj.strftime("%Y-%m-%d")
                            )
                            if result:
                                polygon_results.append(result)
                        except Exception as e:
                            logger.error(f"Error analyzing {ticker} with Polygon: {str(e)}")
                            continue

                    results["polygon_results"] = polygon_results
                    logger.info(f"Found {len(polygon_results)} tickers meeting market criteria")

                    # Step 3: Combine Results if both analyses were performed
                    if not polygon_only and trends_results:
                        for p_result in polygon_results:
                            t_result = next(
                                (r for r in trends_results if r["ticker"] == p_result.ticker),
                                None
                            )
                            if t_result:
                                combined_result = {
                                    "ticker": p_result.ticker,
                                    "company_name": p_result.company_name,
                                    "date": date_obj.strftime("%Y-%m-%d"),
                                    # Market data
                                    "premarket_volume": p_result.premarket_volume,
                                    "gap_up": p_result.gap_up,
                                    "market_cap": p_result.market_cap,
                                    "open_price": p_result.open_price,
                                    "high_price": p_result.high_price,
                                    "close_price": p_result.close_price,
                                    "open_to_high": p_result.open_to_high,
                                    "open_to_close": p_result.open_to_close,
                                    # Trends data
                                    "trends_change": t_result["total_change"],
                                    "trends_4_to_5": t_result["hour_4_to_5_change"],
                                    "trends_5_to_6": t_result["hour_5_to_6_change"]
                                }
                                results["combined_results"].append(combined_result)

                        logger.info(f"Found {len(results['combined_results'])} tickers meeting all criteria")

        except Exception as e:
            logger.error(f"Error in combined analysis: {str(e)}")
            raise

        return results

    async def backtest(
        self,
        tickers: List[str],
        start_date: Union[datetime, date],
        end_date: Union[datetime, date],
        min_trends_change: float = 50.0,
        min_premarket_volume: float = 50000,
        min_price: float = 3,
        min_gap_up: float = 2,
        min_market_cap: float = 100_000_000,
        batch_size: int = 5
    ) -> List[Dict]:
        """
        Perform backtesting using both data sources
        
        Args:
            tickers: List of tickers to analyze
            start_date: Start date for backtesting
            end_date: End date for backtesting
            min_trends_change: Minimum trends change percentage
            min_premarket_volume: Minimum premarket volume
            min_price: Minimum stock price
            min_gap_up: Minimum gap up percentage
            min_market_cap: Minimum market capitalization
            batch_size: Number of concurrent requests for trends analysis
            
        Returns:
            List[Dict]: Backtesting results for each day
        """
        all_results = []
        current_date = self._convert_to_datetime(start_date)
        end_date_obj = self._convert_to_datetime(end_date)
        
        total_days = (end_date_obj - current_date).days + 1
        processed_days = 0
        
        while current_date <= end_date_obj:
            try:
                processed_days += 1
                logger.info(f"Processing day {processed_days}/{total_days}: {current_date.date()}")
                
                if self.trading_calendar.is_trading_day(current_date.date()):
                    results = await self.analyze_stocks(
                        tickers,
                        current_date,
                        min_trends_change,
                        min_premarket_volume,
                        min_price,
                        min_gap_up,
                        min_market_cap,
                        batch_size=batch_size
                    )
                    
                    if results["combined_results"]:
                        all_results.extend(results["combined_results"])
                        logger.info(f"Found {len(results['combined_results'])} matching stocks")
                    else:
                        logger.info("No matching stocks found for this date")
                else:
                    logger.info(f"{current_date.date()} is not a trading day, skipping")
                        
            except Exception as e:
                logger.error(f"Error analyzing {current_date.date()}: {str(e)}")
                
            # Add delay between days to avoid rate limits
            if current_date < end_date_obj:
                await asyncio.sleep(1)
                
            current_date += timedelta(days=1)
            
        logger.info(f"Backtest complete. Analyzed {total_days} days, found {len(all_results)} matching results")
        return all_results