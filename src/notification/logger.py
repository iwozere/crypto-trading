"""
Provides logging utilities for the trading system, including console and file logging.

This module sets up application-wide logging configuration and exposes a logger for use throughout the project.
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import logging.config
from datetime import datetime as dt

# Ensure log directory exists
log_dir = os.path.join("logs", "log")
os.makedirs(log_dir, exist_ok=True)


####################################################################
# Simple logger, which logs to console
####################################################################
def print_log(msg: str):
    # Get current timestamp
    current_time = dt.now()
    time = current_time.strftime("%Y-%m-%d %H:%M:%S")

    # Print the timestamp in a human-readable format
    print(f"{time} {msg}")


####################################################################
# This is the logger that will be used in the application.
# Example usage:
# from _logging_config import _logger
####################################################################
LOG_CONFIG = {
    "version": 1,
    "formatters": {
        "detailed": {
            "format": "%(asctime)s - %(levelname)s - %(filename)s - %(funcName)s - %(lineno)d - %(message)s"
        },
        "standard": {"format": "%(asctime)s - %(levelname)s - %(message)s"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "detailed",
        },
        "file": {
            "class": "logging.FileHandler",
            "filename": "logs/log/app.log",
            "level": "DEBUG",
            "formatter": "detailed",
        },
        "trade_file": {
            "class": "logging.FileHandler",
            "filename": "logs/log/trades.log",
            "level": "DEBUG",
            "formatter": "detailed",
        },
        "error_file": {
            "class": "logging.FileHandler",
            "filename": "logs/log/app_errors.log",
            "level": "ERROR",
            "formatter": "detailed",
        },
    },
    "loggers": {
        "matplotlib": {
            "level": "WARNING",  # Logging level for matplotlib matplotlib to WARNING
            "handlers": ["console"],
            "propagate": False,  # Switch off the log propagation to the root logger
        },
        "live_trader": {
            "handlers": ["console", "file"],
            "level": "DEBUG",
            "propagate": False,
        },
        "telegram_bot": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
        "default": {"handlers": ["console", "file"], "level": "DEBUG"},
        "root": {"handlers": ["console", "file"], "level": "DEBUG"},
    },
}

logging.config.dictConfig(LOG_CONFIG)
_logger = logging.getLogger()


#
# Set up the logger for the application
# Usage: setup_logger('live_trader')
def setup_logger():
    """Set up the logger with file and console handlers."""
    logger = logging.getLogger("trading_bot")
    logger.setLevel(logging.INFO)

    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)

    # Create file handler
    current_time = dt.now()
    log_file = os.path.join("logs", f"app_{current_time.strftime('%Y%m%d_%H%M%S')}.log")
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
