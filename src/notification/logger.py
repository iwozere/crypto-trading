"""
Provides logging utilities for the trading system, including console and file logging.

This module sets up application-wide logging configuration and exposes a logger for use throughout the project.
"""
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import logging.config
from datetime import datetime



####################################################################
# Simple logger, which logs to console
####################################################################
def print_log(msg : str):
    # Get current timestamp
    current_time = datetime.now()
    time = current_time.strftime("%Y-%m-%d %H:%M:%S")

    # Print the timestamp in a human-readable format
    print(f'{time} {msg}')



####################################################################
# This is the logger that will be used in the application.
# Example usage:
# from _logging_config import _logger
####################################################################
LOG_CONFIG = {
    "version": 1,
    "formatters": {
        "detailed" : {"format": "%(asctime)s - %(levelname)s - %(filename)s - %(funcName)s - %(lineno)d - %(message)s"},
        "standard": {"format": "%(asctime)s - %(levelname)s - %(message)s"}
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
        }
    },
    'loggers': {
        'matplotlib': {
            'level': 'WARNING',  # Logging level for matplotlib matplotlib to WARNING
            'handlers': ['console'],
            'propagate': False,  # Switch off the log propagation to the root logger
        },
        "live_trader": {
            "handlers": ["console", "file"],
            "level": "DEBUG",
            "propagate": False
        },
        "telegram_bot": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False
        },
        "default": {
            "handlers": ["console"],
            "level": "WARNING"
        },
        "root": {
            "handlers": ["console"],
            "level": "WARNING"
        }
    }
}

logging.config.dictConfig(LOG_CONFIG)
_logger = logging.getLogger()

#
# Set up the logger for the application
# Usage: setup_logger('live_trader')
def setup_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)