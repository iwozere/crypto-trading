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