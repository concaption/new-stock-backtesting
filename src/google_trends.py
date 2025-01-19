"""
path: src/google_trends.py
author: @concaption
date: 2025-01-15

This module analyzes Google Trends data for stock tickers using the SERP API.
It fetches historical search data for a given keyword and calculates hourly changes in interest over time.
The `GoogleTrendsAnalyzer` class provides methods to fetch trends data, extract daily values,
and calculate hourly changes for a specific ticker on a given date.
"""

import os
from datetime import datetime, timedelta, timezone, date
from typing import Dict, Optional, Set, List, Union
import asyncio
import aiohttp
import logging
from dotenv import load_dotenv

load_dotenv()
SERP_API_KEY = os.getenv("SERPAPI_KEY")

# Initialize logger
logger = logging.getLogger(__name__)

class GoogleTrendsAnalyzer:
    """
    Analyzes Google Trends data for stock tickers using SERP API
    
    Attributes:
        api_key: SERP API key for authentication
        trading_calendar: Calendar instance for market day validation
        pst_tz: Pacific timezone for time calculations
    """
    def __init__(self, trading_calendar):
        if not SERP_API_KEY:
            raise ValueError("SERPAPI_KEY not found in environment variables")
        
        self.api_key = SERP_API_KEY
        self.trading_calendar = trading_calendar
        self.pst_tz = timezone(timedelta(hours=-8))  # PST timezone

    def _convert_to_date(self, date_param: Union[datetime, date]) -> date:
        """
        Convert datetime or date to date object
        
        Args:
            date_param: Input date/datetime
            
        Returns:
            date: Converted date object
        """
        return date_param.date() if isinstance(date_param, datetime) else date_param

    def _convert_to_datetime(self, date_param: Union[datetime, date]) -> datetime:
        """
        Convert date to datetime if needed
        
        Args:
            date_param: Input date/datetime
            
        Returns:
            datetime: Converted datetime object
        """
        if isinstance(date_param, date) and not isinstance(date_param, datetime):
            return datetime.combine(date_param, datetime.min.time())
        return date_param

    def get_date_range(self, target_date: Union[datetime, date]) -> str:
        """
        Get the date range string for the API request with hour precision.
        Uses hour-based format required for hourly data.
        
        Args:
            target_date: The target date to analyze
            
        Returns:
            str: Formatted date range string in yyyy-mm-ddThh format
        """
        end_date = self._convert_to_datetime(target_date)
        # Get 7 days before
        start_date = end_date - timedelta(days=6)
        
        # Format with hours for hourly data
        # End at 23:00 of target date to get full day data
        end_str = end_date.replace(hour=23).strftime('%Y-%m-%dT%H')
        # Start at 00:00 of start date
        start_str = start_date.replace(hour=0).strftime('%Y-%m-%dT%H')
        
        return f"{start_str} {end_str}"

    async def fetch_trends_data(
        self,
        session: aiohttp.ClientSession,
        keyword: str,
        current_date: Union[datetime, date]
    ) -> Optional[Dict]:
        """
        Fetch Google Trends data for a keyword
        
        Args:
            session: aiohttp client session
            keyword: Search term to analyze
            current_date: Date to analyze
            
        Returns:
            Optional[Dict]: Structured trends data if successful
        """
        try:
            date_range = self.get_date_range(current_date)
            
            params = {
                "engine": "google_trends",
                "q": keyword,
                "data_type": "TIMESERIES",
                "date": date_range,
                "api_key": self.api_key,
                "tz": "480",  # PST (UTC-8)
                "granular": "hourly"
            }

            logger.debug(f"Fetching trends data for {keyword} with params: {params}")
            async with session.get("https://serpapi.com/search", params=params) as response:
                if response.status != 200:
                    logger.error(f"Failed to fetch trends for {keyword}: Status {response.status}")
                    return None

                result = await response.json()

                logger.debug(f"Response for {keyword}: {result}")
                
                if "error" in result:
                    logger.error(f"API error for {keyword}: {result['error']}")
                    return None
                logger.debug(f"Raw data for {keyword}: {result}")
                if "interest_over_time" not in result:
                    logger.warning(f"No time series data found for {keyword}")
                    return None

                # Process timeline data
                timeline_data = {}
                for point in result["interest_over_time"]["timeline_data"]:
                    try:
                        time_obj = datetime.fromtimestamp(int(point["timestamp"]))
                        time_obj = time_obj.replace(tzinfo=timezone.utc).astimezone(self.pst_tz)
                        
                        value = point["values"][0].get("extracted_value")
                        if value is not None:
                            timeline_data[time_obj] = value
                            
                    except (KeyError, IndexError, ValueError) as e:
                        logger.warning(f"Error processing data point for {keyword}: {e}")
                        continue

                current_date_obj = self._convert_to_date(current_date)
                last_trading_day = self.trading_calendar.get_last_trading_day(current_date_obj)
                logger.debug(f"Last trading day for {current_date_obj}: {last_trading_day}")
                logger.debug(f"Timeline data for {keyword}: {timeline_data}")
                return {
                    "keyword": keyword,
                    "timeline_data": timeline_data,
                    "last_trading_day": last_trading_day
                }

        except Exception as e:
            logger.error(f"Exception fetching trends for {keyword}: {str(e)}")
            return None

    def extract_daily_values(
        self,
        time_data: Dict[datetime, int],
        target_date: Union[datetime, date],
        hours_to_check: Set[int]
    ) -> Dict[int, int]:
        """
        Extract values for specific hours in a day
        
        Args:
            time_data: Dictionary of datetime to values
            target_date: Date to extract values for
            hours_to_check: Set of hours to extract
        
        Returns:
            Dict[int, int]: Hour to value mapping
        """
        daily_values = {}
        target_date_obj = self._convert_to_date(target_date)
        
        for time_obj, value in time_data.items():
            if (time_obj.date() == target_date_obj and 
                time_obj.hour in hours_to_check):
                daily_values[time_obj.hour] = value
        logger.debug(f"Extracted values for {target_date_obj}: {daily_values}")
        
        return daily_values

    def calculate_hourly_changes(
        self,
        current_day_values: Dict[int, int],
        previous_day_values: Dict[int, int],
        hours_to_check: Set[int]
    ) -> Dict[str, Optional[float]]:
        """
        Calculate percentage changes between hours
        
        Args:
            current_day_values: Current day hourly values
            previous_day_values: Previous day hourly values
            hours_to_check: Hours to analyze
            
        Returns:
            Dict[str, Optional[float]]: Dictionary of calculated changes
        """
        matching_hours = set(previous_day_values.keys()) & set(current_day_values.keys())
        logger.debug(f"Matching hours: {matching_hours}")
        if not matching_hours:
            logger.warning("No matching hours found between current and previous day")
            return {
                "total_change": 0,
                "hour_4_to_5": None,
                "hour_5_to_6": None
            }

        # Calculate total change
        previous_total = sum(previous_day_values[h] for h in matching_hours)
        current_total = sum(current_day_values[h] for h in matching_hours)

        total_change = ((current_total - previous_total) / previous_total * 100) if previous_total != 0 else float('inf')

        # Calculate hour-to-hour changes
        hour_4_to_5 = None
        if 4 in current_day_values and 5 in current_day_values and current_day_values[4] != 0:
            hour_4_to_5 = ((current_day_values[5] - current_day_values[4]) / current_day_values[4] * 100)

        hour_5_to_6 = None
        if 5 in current_day_values and 6 in current_day_values and current_day_values[5] != 0:
            hour_5_to_6 = ((current_day_values[6] - current_day_values[5]) / current_day_values[5] * 100)
        logger.debug(f"Changes: {total_change}, 4-5: {hour_4_to_5}, 5-6: {hour_5_to_6}")
        return {
            "total_change": total_change,
            "hour_4_to_5": hour_4_to_5,
            "hour_5_to_6": hour_5_to_6
        }

    async def analyze_trends(
        self,
        session: aiohttp.ClientSession,
        ticker: str,
        date_param: Union[datetime, date],
        hours_to_check: Set[int] = {4, 5, 6}
    ) -> Optional[Dict]:
        """
        Analyze Google Trends data for a specific ticker
        
        Args:
            session: HTTP session for making requests
            ticker: Stock ticker symbol
            date_param: Date to analyze
            hours_to_check: Hours to analyze (default: 4, 5, 6 AM PST)
            
        Returns:
            Optional[Dict]: Analysis results if successful
        """
        try:
            date_obj = self._convert_to_date(date_param)
            
            if not self.trading_calendar.is_trading_day(date_obj):
                logger.warning(f"{date_obj} is not a trading day")
                return None

            # Fetch trends data
            trends_data = await self.fetch_trends_data(session, ticker +" "+ "Stock", date_param)
            if not trends_data:
                return None

            # Extract values for current and previous trading days
            current_day_values = self.extract_daily_values(
                trends_data["timeline_data"],
                date_param,
                hours_to_check
            )
            
            previous_day_values = self.extract_daily_values(
                trends_data["timeline_data"],
                trends_data["last_trading_day"],
                hours_to_check
            )

            # Calculate changes
            changes = self.calculate_hourly_changes(
                current_day_values, 
                previous_day_values, 
                hours_to_check
            )

            return {
                "ticker": ticker,
                "date": date_obj.strftime("%Y-%m-%d"),
                "total_change": changes["total_change"],
                "hour_4_to_5_change": changes["hour_4_to_5"],
                "hour_5_to_6_change": changes["hour_5_to_6"],
                "current_day_values": current_day_values,
                "previous_day_values": previous_day_values,
                "raw_timeline_data": trends_data["timeline_data"]
            }

        except Exception as e:
            logger.error(f"Error analyzing {ticker} for {date_param}: {str(e)}")
            return None

    async def analyze_multiple_tickers(
        self,
        tickers: List[str],
        date_param: Union[datetime, date],
        min_change_threshold: float = 50.0,
        batch_size: int = 5
    ) -> List[Dict]:
        """
        Analyze multiple tickers concurrently with batching
        
        Args:
            tickers: List of tickers to analyze
            date_param: Date to analyze
            min_change_threshold: Minimum change percentage to include
            batch_size: Number of concurrent requests
            
        Returns:
            List[Dict]: Analysis results meeting the threshold
        """
        results = []
        date_obj = self._convert_to_datetime(date_param)
        
        try:
            async with aiohttp.ClientSession() as session:
                # Process tickers in batches to avoid rate limits
                for i in range(0, len(tickers), batch_size):
                    batch = tickers[i:i + batch_size]
                    logger.info(f"Processing batch of {len(batch)} tickers")
                    
                    tasks = [self.analyze_trends(session, ticker, date_obj) 
                            for ticker in batch]
                    
                    batch_results = await asyncio.gather(*tasks)
                    filtered_results = [
                        result for result in batch_results 
                        if result and result["total_change"] >= min_change_threshold
                    ]
                    results.extend(filtered_results)
                    
                    # Rate limiting delay
                    if i + batch_size < len(tickers):
                        await asyncio.sleep(1)

                # Sort by total change percentage
                results.sort(key=lambda x: x["total_change"], reverse=True)
                logger.info(f"Analyzed {len(tickers)} tickers, found {len(results)} meeting criteria")
                return results
                
        except Exception as e:
            logger.error(f"Error in analyze_multiple_tickers: {str(e)}")
            return []