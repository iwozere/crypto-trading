import os
import json
import numpy as np
import pandas as pd
from datetime import datetime

class BaseOptimizer:
    class DateTimeEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, (pd.Timestamp, datetime)):
                return obj.isoformat()
            if isinstance(obj, np.integer):
                return int(obj)
            if isinstance(obj, np.floating):
                return float(obj)
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            return super().default(obj)

    @staticmethod
    def calculate_sqn_pct(trades_df):
        """Calculate SQN on percent returns per trade (pnl_comm / entry_price * 100)."""
        if trades_df is None or len(trades_df) < 2:
            return None
        trades_df = trades_df.dropna(subset=['entry_price', 'pnl_comm'])
        if trades_df.empty:
            return None
        trades_df['pct_return'] = trades_df['pnl_comm'] / trades_df['entry_price'] * 100
        returns = trades_df['pct_return'].values
        n = len(returns)
        if n > 1 and np.std(returns) > 0:
            return float(np.mean(returns) / np.std(returns) * np.sqrt(n))
        return None

    @staticmethod
    def calculate_cagr(initial_value, final_value, start_date, end_date):
        """Calculate CAGR given initial/final value and start/end date (datetime or str)."""
        try:
            if isinstance(start_date, str):
                start_date = pd.to_datetime(start_date)
            if isinstance(end_date, str):
                end_date = pd.to_datetime(end_date)
            years = (end_date - start_date).days / 365.25
            if years > 0:
                cagr = (final_value / initial_value) ** (1/years) - 1
                return float(cagr)
        except Exception:
            pass
        return None

    def log_message(self, message):
        print(f"[{datetime.now().isoformat()}] {message}")

    def load_all_data(self, data_dir=None, required_columns=None, parse_dates=True, sort_index=True, fillna=True, log=True):
        """
        Load all CSV files in data_dir into self.raw_data.
        - required_columns: list of columns to ensure exist (e.g. ['open','high','low','close','volume'])
        - parse_dates: whether to parse 'timestamp' as datetime
        - sort_index: whether to sort index after loading
        - fillna: whether to ffill/bfill NaNs
        - log: whether to print/log messages
        """
        if data_dir is None:
            data_dir = self.data_dir
        if required_columns is None:
            required_columns = ['open', 'high', 'low', 'close', 'volume']
        self.raw_data = {}
        data_files = [f for f in os.listdir(data_dir) if f.endswith('.csv')]
        for data_file in data_files:
            try:
                df = pd.read_csv(os.path.join(data_dir, data_file))
                if parse_dates and 'timestamp' in df.columns:
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    df.set_index('timestamp', inplace=True)
                for col in required_columns:
                    if col not in df.columns:
                        if col == 'volume':
                            self.log_message(f"Warning: 'volume' column missing in {data_file}. Creating dummy 'volume' column with zeros.")
                            df['volume'] = 0
                        else:
                            raise ValueError(f"Missing required column: {col} in {data_file}")
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                if sort_index:
                    df.sort_index(inplace=True)
                if fillna:
                    if df.isnull().any().any():
                        self.log_message(f"Warning: NaN values found in {data_file}. Forward-filling and back-filling.")
                        df.ffill(inplace=True)
                        df.bfill(inplace=True)
                    if df.isnull().any().any():
                        self.log_message(f"Error: NaN values persist in {data_file} after fill. Skipping.")
                        continue
                self.raw_data[data_file] = df
                if log:
                    self.log_message(f"Loaded data for {data_file}, shape: {df.shape}, date range: {df.index.min()} to {df.index.max()}")
            except Exception as e:
                self.log_message(f"Error loading {data_file}: {str(e)}")

    def params_to_dict(self, params, param_types=None):
        """
        Convert parameter list to dictionary with proper types.
        - param_types: dict of {param_name: type}, e.g. {'rsi_period': int, ...}
        If not provided, will use int for names containing 'period', else float.
        """
        if not hasattr(self, 'space'):
            raise AttributeError("Optimizer must have a 'space' attribute with parameter names.")
        param_names = [p.name for p in self.space]
        param_dict = dict(zip(param_names, params))
        typed_param_dict = {}
        for name, value in param_dict.items():
            if param_types and name in param_types:
                typed_param_dict[name] = param_types[name](value)
            elif 'period' in name or 'window' in name or 'fast' in name or 'slow' in name or 'mid' in name:
                typed_param_dict[name] = int(value)
            elif isinstance(value, bool):
                typed_param_dict[name] = bool(value)
            else:
                typed_param_dict[name] = float(value)
        return typed_param_dict 