import os
import json
import numpy as np
import pandas as pd
from datetime import datetime
from src.notification.logger import _logger

class BaseOptimizer:
    def __init__(self, initial_capital=1000.0, commission=0.001):
        self.initial_capital = initial_capital
        self.commission = commission

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

    def log_message(self, message, level="info"):
        """
        Log a message using the configured logger.
        - level: "info" (default) for normal messages, "error" for errors.
        """
        if level == "error":
            _logger.error(message)
        else:
            _logger.info(message)

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

    def save_results(self, data_file, best_params, metrics, trades_df, optimization_result=None, plot_path=None, strategy_name=None):
        """
        Unified method to save optimization results. Handles serialization, extra metrics, and logging.
        """
        try:
            self.log_message(f"\nSaving results for {data_file}...", level='info')
            os.makedirs(self.results_dir, exist_ok=True)
            # Calculate extra metrics if possible
            sqn_pct = None
            cagr = None
            final_value = metrics.get('final_value') or metrics.get('portfolio_value')
            if trades_df is not None and not trades_df.empty and final_value is not None:
                try:
                    sqn_pct = self.calculate_sqn_pct(trades_df)
                    if 'entry_dt' in trades_df.columns and 'exit_dt' in trades_df.columns:
                        trades_df = trades_df.dropna(subset=['entry_dt', 'exit_dt'])
                        if not trades_df.empty:
                            cagr = self.calculate_cagr(self.initial_capital, final_value, trades_df['entry_dt'].iloc[0], trades_df['exit_dt'].iloc[-1])
                except Exception as e:
                    self.log_message(f"Error calculating sqn_pct/cagr: {e}", level='error')
            # Prepare trades log
            trades_records = []
            if trades_df is not None and not trades_df.empty:
                for _, trade_row in trades_df.iterrows():
                    trade_dict = {}
                    for col in trades_df.columns:
                        value = trade_row[col]
                        if pd.isna(value): trade_dict[col] = None
                        elif isinstance(value, (pd.Timestamp, datetime)): trade_dict[col] = value.isoformat()
                        elif isinstance(value, (np.integer, np.floating, int, float)): trade_dict[col] = float(value)
                        else: trade_dict[col] = str(value)
                    trades_records.append(trade_dict)
            # Prepare optimization history
            optimization_history = []
            if optimization_result is not None and hasattr(optimization_result, 'x_iters'):
                for x_iter, score_iter in zip(optimization_result.x_iters, optimization_result.func_vals):
                    try:
                        param_dict_iter = self.params_to_dict(x_iter)
                        optimization_history.append({'params': param_dict_iter, 'score': float(score_iter)})
                    except Exception as e:
                        self.log_message(f"Warning: Could not process optimization history entry: {e}", level='warning')
                        continue
            # Compose results dict
            results_dict = {
                'timestamp': datetime.now().isoformat(),
                'data_file': data_file,
                'strategy_name': strategy_name,
                'best_params': best_params,
                'metrics': metrics,
                'sqn_pct': sqn_pct,
                'cagr': cagr,
                'trades_log': trades_records,
                'optimization_history': optimization_history,
                'plot_path': plot_path
            }
            filename_base = f"{data_file}_optimization_results"
            results_path = os.path.join(self.results_dir, f'{filename_base}.json')
            self.log_message(f"Saving results to: {results_path}", level='info')
            try:
                json_str = json.dumps(results_dict, indent=4, cls=BaseOptimizer.DateTimeEncoder)
                with open(results_path, 'w') as f: f.write(json_str)
            except Exception as e:
                self.log_message(f"Error during JSON serialization: {e}. Trying to save simplified.", level='error')
                simplified_dict = {k: v for k, v in results_dict.items() if k not in ['trades_log', 'optimization_history']}
                simplified_dict['error_in_serialization'] = str(e)
                json_str = json.dumps(simplified_dict, indent=4, cls=BaseOptimizer.DateTimeEncoder)
                with open(results_path, 'w') as f: f.write(json_str)
                self.log_message("Saved simplified results due to serialization error.", level='error')
            self.log_message(f"Results saved to {results_path}", level='info')
            return results_dict
        except Exception as e:
            self.log_message(f"Error in save_results: {str(e)}", level='error')
            import traceback
            self.log_message(f"Full traceback: {traceback.format_exc()}", level='error')
            return None 