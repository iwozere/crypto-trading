import os
from datetime import datetime, timedelta
import pandas as pd
from binance.client import Client
from typing import List, Optional

class BinanceDataDownloader:
    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        """Initialize the Binance client."""
        self.client = Client(api_key, api_secret)
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'dataset')
        os.makedirs(self.data_dir, exist_ok=True)

    def download_historical_data(
        self,
        symbol: str,
        interval: str,
        start_date: str,
        end_date: Optional[str] = None,
        save_to_csv: bool = True
    ) -> pd.DataFrame:
        """
        Download historical klines/candlestick data from Binance.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
            interval: Kline interval (e.g., '1h', '4h', '1d')
            start_date: Start date in format 'YYYY-MM-DD'
            end_date: End date in format 'YYYY-MM-DD' (optional)
            save_to_csv: Whether to save the data to a CSV file
            
        Returns:
            DataFrame containing the historical data
        """
        # Convert dates to timestamps
        start_timestamp = int(datetime.strptime(start_date, '%Y-%m-%d').timestamp() * 1000)
        end_timestamp = None
        if end_date:
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
            filename = f"{symbol}_{interval}_{start_date.replace('-', '')}"
            if end_date:
                filename += f"_{end_date.replace('-', '')}"
            filename += ".csv"
            filepath = os.path.join(self.data_dir, filename)
            df.to_csv(filepath, index=False)
            print(f"Data saved to {filepath}")

        return df

    def download_multiple_symbols(
        self,
        symbols: List[str],
        interval: str,
        start_date: str,
        end_date: Optional[str] = None
    ):
        """Download historical data for multiple symbols."""
        for symbol in symbols:
            print(f"Downloading data for {symbol}...")
            self.download_historical_data(symbol, interval, start_date, end_date) 