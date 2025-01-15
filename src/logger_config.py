"""
path: src/logger_config.py
author: @concaption
date: 2025-01-15

This module provides centralized logging configuration with colored output.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

# ANSI color codes
COLORS = {
    'DEBUG': '\033[36m',     # Cyan
    'INFO': '\033[32m',      # Green
    'WARNING': '\033[33m',   # Yellow
    'ERROR': '\033[31m',     # Red
    'CRITICAL': '\033[41m',  # Red background
    'RESET': '\033[0m'       # Reset color
}

class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors"""
    
    def format(self, record):
        # Add color to level name
        if record.levelname in COLORS:
            record.levelname = f"{COLORS[record.levelname]}{record.levelname}{COLORS['RESET']}"
        
        # Add color to entire message for errors and criticals
        if record.levelno >= logging.ERROR:
            record.msg = f"{COLORS['ERROR']}{record.msg}{COLORS['RESET']}"
            
        return super().format(record)

def setup_logging(
    console_level: int = logging.INFO,
    file_level: int = logging.DEBUG,
    log_dir: str = "logs",
    app_name: str = "stock_analyzer"
) -> None:
    """
    Set up logging configuration with both console and file handlers
    
    Args:
        console_level: Logging level for console output
        file_level: Logging level for file output
        log_dir: Directory for log files
        app_name: Name of the application for log files
    """
    # Create logs directory if it doesn't exist
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Create formatters
    console_formatter = ColoredFormatter(
        '%(levelname)s - %(message)s'
    )
    
    file_formatter = logging.Formatter(
        '%(asctime)s - file: %(filename)s - func: %(funcName)s - line: %(lineno)d - %(levelname)s - %(message)s'
    )

    # Create console handler with colored output
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(console_formatter)

    # Create file handler
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_handler = logging.FileHandler(
        log_path / f"{app_name}_{current_time}.log",
        encoding='utf-8'
    )
    file_handler.setLevel(file_level)
    file_handler.setFormatter(file_formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(min(console_level, file_level))
    
    # Remove any existing handlers
    root_logger.handlers = []
    
    # Add the handlers
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Log the startup message
    root_logger.info("Logging system initialized")