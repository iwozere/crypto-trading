"""
Downloads historical OHLCV data from Binance and saves it as CSV for backtesting and analysis.

This module provides BinanceDataDownloader, a utility for fetching and storing historical market data for multiple symbols and intervals.
"""
import os
from datetime import datetime, timedelta
import pandas as pd
from binance.client import Client
from typing import List, Optional
from .base_data_downloader import BaseDataDownloader

class BinanceDataDownloader(BaseDataDownloader):
    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None, data_dir: Optional[str] = None, interval: Optional[str] = None):
        super().__init__(data_dir=data_dir, interval=interval)
        self.client = Client(api_key, api_secret)

    def download_historical_data(
        self,
        symbol: str,
        interval: str,
        start_date: str,
        end_date: str,
        save_to_csv: bool = True
    ) -> pd.DataFrame:
        """
        Download historical klines/candlestick data from Binance.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
            interval: Kline interval (e.g., '1h', '4h', '1d')
            start_date: Start date in format 'YYYY-MM-DD'
            end_date: End date in format 'YYYY-MM-DD'
            save_to_csv: Whether to save the data to a CSV file
            
        Returns:
            DataFrame containing the historical data
        """
        # Convert dates to timestamps
        start_timestamp = int(datetime.strptime(start_date, '%Y-%m-%d').timestamp() * 1000)
        end_timestamp = int(datetime.strptime(end_date, '%Y-%m-%d').timestamp() * 1000)

        # Get klines data
        klines = self.client.get_historical_klines(
            symbol,
            interval,
            start_timestamp,
            end_timestamp
        )

        # Convert to DataFrame
        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
        ])

        # Convert timestamp to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        # Convert string values to float
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)

        # Save to CSV if requested
        if save_to_csv:
            self.save_data(df, symbol, start_date, end_date)

        return df

    def download_multiple_symbols(
        self,
        symbols: List[str],
        interval: str,
        start_date: str,
        end_date: str
    ):
        """Download historical data for multiple symbols."""
        def download_func(symbol, interval, start_date, end_date):
            return self.download_historical_data(symbol, interval, start_date, end_date, save_to_csv=False)
        return super().download_multiple_symbols(symbols, download_func, interval, start_date, end_date)

    def save_data(self, df: pd.DataFrame, symbol: str, start_date: str = None, end_date: str = None) -> str:
        return super().save_data(df, symbol, start_date, end_date) 