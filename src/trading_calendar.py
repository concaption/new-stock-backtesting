"""
path: src/trading_calendar.py
author: @concaption
date: 2025-01-15

This module provides a TradingCalendar class that manages trading calendar information, including holidays and trading days. It loads holidays from a CSV file and provides methods to check if a given date is a trading day and to get the last trading day before a given date.

"""

from datetime import datetime
from typing import Set
import logging
import csv
from datetime import date, timedelta


logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - file: %(filename)s - func: %(funcName)s - line: %(lineno)d - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)



def validate_holidays_csv():
    """
    Validate that the holidays.csv file exists and has the correct format
    
    Returns:
        bool: True if the file is valid, False otherwise
    """
    try:
        with open('data/holidays.csv', 'r') as f:
            reader = csv.DictReader(f)
            required_fields = {'Date', 'Market Status'}
            if not required_fields.issubset(reader.fieldnames):
                logger.error("holidays.csv is missing required fields: Date, Market Status")
                return False
            
            # Validate few rows
            for row in reader:
                try:
                    datetime.strptime(row['Date'], '%Y-%m-%d')
                    if row['Market Status'] not in ['Closed', 'Early Close']:
                        logger.error(f"Invalid market status in holidays.csv: {row['Market Status']}")
                        return False
                except ValueError:
                    logger.error(f"Invalid date format in holidays.csv: {row['Date']}")
                    return False
        return True
    except FileNotFoundError:
        logger.error("holidays.csv file not found")
        return False
    except Exception as e:
        logger.error(f"Error validating holidays.csv: {e}")
        return False


class TradingCalendar:
    """
    Manages trading calendar information including holidays and trading days
    """
    def __init__(self):
        self.holidays: Set[date] = set()
        self.early_closing_days: Set[date] = set()
        self.load_holidays()
        
    def load_holidays(self):
        """Load holidays from CSV file"""
        try:
            with open('data/holidays.csv', 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    date_obj = datetime.strptime(row['Date'], '%Y-%m-%d').date()
                    if row['Market Status'] == 'Closed':
                        self.holidays.add(date_obj)
                    elif row['Market Status'] == 'Early Close':
                        self.early_closing_days.add(date_obj)
            logger.info(f"Loaded {len(self.holidays)} holidays and {len(self.early_closing_days)} early closing days")
        except Exception as e:
            logger.error(f"Error loading holidays: {e}")
            self.holidays = set()
            self.early_closing_days = set()

    def is_trading_day(self, date_to_check: date) -> bool:
        """
        Check if a given date is a trading day
        
        Args:
            date_to_check: date object to check
            
        Returns:
            bool: True if it's a trading day, False otherwise
        """
        # Convert datetime to date if necessary
        if isinstance(date_to_check, datetime):
            date_to_check = date_to_check.date()
            
        # Check if it's a weekend (5 = Saturday, 6 = Sunday)
        if date_to_check.weekday() >= 5:
            return False
            
        # Check if it's a holiday
        if date_to_check in self.holidays:
            return False
            
        return True

    def get_last_trading_day(self, current_date: date) -> date:
        """
        Get the last trading day before the given date
        
        Args:
            current_date: date to start from
            
        Returns:
            date: The last trading day
        """
        if isinstance(current_date, datetime):
            current_date = current_date.date()
            
        last_day = current_date - timedelta(days=1)
        while not self.is_trading_day(last_day):
            last_day = last_day - timedelta(days=1)
        return last_day