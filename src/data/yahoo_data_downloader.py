import os
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import logging

class YahooDataDownloader:
    """
    A class to download historical data from Yahoo Finance.
    
    This class provides methods to:
    1. Download historical OHLCV data for a given symbol
    2. Save data to CSV files
    3. Load data from CSV files
    4. Update existing data files with new data
    
    Parameters:
    -----------
    data_dir : str
        Directory to store downloaded data files
    interval : str
        Data interval (e.g., '1m', '5m', '15m', '1h', '1d')
    start_date : Optional[datetime]
        Start date for historical data
    end_date : Optional[datetime]
        End date for historical data
    """
    
    def __init__(
        self,
        data_dir: str = 'data',
        interval: str = '1d',
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ):
        self.data_dir = data_dir
        self.interval = interval
        self.start_date = start_date or (datetime.now() - timedelta(days=365))
        self.end_date = end_date or datetime.now()
        
        # Create data directory if it doesn't exist
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Set up logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def download_data(
        self,
        symbol: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        interval: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Download historical data for a given symbol.
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            start_date: Start date for historical data
            end_date: End date for historical data
            interval: Data interval
            
        Returns:
            pd.DataFrame: Historical OHLCV data
        """
        try:
            # Use provided dates or default to instance dates
            start = start_date or self.start_date
            end = end_date or self.end_date
            interval = interval or self.interval
            
            # Download data using yfinance
            ticker = yf.Ticker(symbol)
            df = ticker.history(
                start=start,
                end=end,
                interval=interval
            )
            
            # Rename columns to match standard format
            df = df.rename(columns={
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume'
            })
            
            # Add timestamp column
            df['timestamp'] = df.index
            
            # Reset index to make timestamp a regular column
            df = df.reset_index(drop=True)
            
            # Ensure all required columns are present
            required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
            for col in required_columns:
                if col not in df.columns:
                    raise ValueError(f"Missing required column: {col}")
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error downloading data for {symbol}: {str(e)}")
            raise
    
    def save_data(self, df: pd.DataFrame, symbol: str) -> str:
        """
        Save downloaded data to a CSV file.
        
        Args:
            df: DataFrame containing historical data
            symbol: Stock symbol
            
        Returns:
            str: Path to the saved file
        """
        try:
            # Create filename with symbol and date range
            start_date = df['timestamp'].min().strftime('%Y%m%d')
            end_date = df['timestamp'].max().strftime('%Y%m%d')
            filename = f"{symbol}_{self.interval}_{start_date}_{end_date}.csv"
            filepath = os.path.join(self.data_dir, filename)
            
            # Save to CSV
            df.to_csv(filepath, index=False)
            self.logger.info(f"Saved data to {filepath}")
            
            return filepath
            
        except Exception as e:
            self.logger.error(f"Error saving data for {symbol}: {str(e)}")
            raise
    
    def load_data(self, filepath: str) -> pd.DataFrame:
        """
        Load data from a CSV file.
        
        Args:
            filepath: Path to the CSV file
            
        Returns:
            pd.DataFrame: Loaded data
        """
        try:
            df = pd.read_csv(filepath)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            return df
            
        except Exception as e:
            self.logger.error(f"Error loading data from {filepath}: {str(e)}")
            raise
    
    def update_data(self, symbol: str) -> str:
        """
        Update existing data file with new data.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            str: Path to the updated file
        """
        try:
            # Find existing data file
            existing_files = [f for f in os.listdir(self.data_dir) if f.startswith(f"{symbol}_{self.interval}_")]
            if not existing_files:
                # If no existing file, download new data
                df = self.download_data(symbol)
                return self.save_data(df, symbol)
            
            # Load existing data
            latest_file = max(existing_files)
            filepath = os.path.join(self.data_dir, latest_file)
            existing_df = self.load_data(filepath)
            
            # Get last date in existing data
            last_date = existing_df['timestamp'].max()
            
            # Download new data from last date
            new_df = self.download_data(
                symbol,
                start_date=last_date + timedelta(days=1)
            )
            
            if new_df.empty:
                self.logger.info(f"No new data available for {symbol}")
                return filepath
            
            # Combine existing and new data
            combined_df = pd.concat([existing_df, new_df])
            combined_df = combined_df.drop_duplicates(subset=['timestamp'])
            combined_df = combined_df.sort_values('timestamp')
            
            # Save updated data
            return self.save_data(combined_df, symbol)
            
        except Exception as e:
            self.logger.error(f"Error updating data for {symbol}: {str(e)}")
            raise
    
    def download_multiple_symbols(
        self,
        symbols: List[str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, str]:
        """
        Download data for multiple symbols.
        
        Args:
            symbols: List of stock symbols
            start_date: Start date for historical data
            end_date: End date for historical data
            
        Returns:
            Dict[str, str]: Dictionary mapping symbols to file paths
        """
        results = {}
        for symbol in symbols:
            try:
                df = self.download_data(symbol, start_date, end_date)
                filepath = self.save_data(df, symbol)
                results[symbol] = filepath
            except Exception as e:
                self.logger.error(f"Error processing {symbol}: {str(e)}")
                continue
        return results

if __name__ == "__main__":
    # Example usage
    downloader = YahooDataDownloader(
        data_dir='data',
        interval='1d',
        start_date=datetime(2020, 1, 1),
        end_date=datetime.now()
    )
    
    # Download data for a single symbol
    symbol = 'AAPL'
    df = downloader.download_data(symbol)
    filepath = downloader.save_data(df, symbol)
    print(f"Data saved to {filepath}")
    
    # Download data for multiple symbols
    symbols = ['AAPL', 'MSFT', 'GOOGL']
    results = downloader.download_multiple_symbols(symbols)
    print("Downloaded files:", results) 