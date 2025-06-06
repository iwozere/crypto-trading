"""
Base Optimizer Module
--------------------

This module defines the BaseOptimizer class, which provides a flexible and extensible foundation for implementing trading strategy optimizers. It is designed to work with Backtrader strategies and supports Bayesian optimization, backtesting, metrics calculation, and result management. Subclasses can define parameter spaces, plotting, and custom scoring logic for specific strategies.

Main Features:
- Unified interface for optimizing Backtrader strategies
- Bayesian optimization using scikit-optimize (skopt)
- Backtest runner with metrics extraction (Sharpe, Drawdown, SQN, etc.)
- Result saving, plotting, and reporting utilities
- Extensible for custom strategies and parameter spaces

Classes:
- BaseOptimizer: Abstract base class for trading strategy optimizers
"""
import os
import json
import numpy as np
import pandas as pd
import traceback
import backtrader as bt
from datetime import datetime
from ta.volatility import AverageTrueRange
from src.notification.logger import _logger
from skopt import gp_minimize
from typing import Any, Dict, List, Optional, Union
from skopt.space import Real, Integer, Categorical
import optuna
from src.exit.exit_registry import EXIT_PARAM_MAP
from functools import lru_cache

class BaseOptimizer:
    def __init__(self, config: dict):
        """
        Initialize the base optimizer with a configuration dictionary.
        Args:
            config: Dictionary containing all optimizer parameters.
        """
        self.config = config  # Store config for later use
        self.initial_capital = config.get('initial_capital', 1000.0)
        self.commission = config.get('commission', 0.001)
        self.notify = config.get('notify', False)
        self.risk_free_rate = config.get('risk_free_rate', 0.0)
        self.omega_threshold = config.get('omega_threshold', 0.0)
        self.current_metrics = {}
        self.current_data = None
        self.current_symbol = None
        self.raw_data = {}
        self.best_metrics = float('-inf')
        self.metrics_cache = {}
        self.load_all_data()

    class DateTimeEncoder(json.JSONEncoder):
        def default(self, obj: Any) -> Any:
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
    def calculate_sqn_pct(trades_df: pd.DataFrame) -> Optional[float]:
        """
        Calculate SQN on percent returns per trade (pnl_comm / entry_price * 100).
        Args:
            trades_df: DataFrame of trades
        Returns:
            SQN value or None if not enough trades
        """
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
    def calculate_cagr(initial_value: float, final_value: float, start_date: Union[str, datetime], end_date: Union[str, datetime]) -> Optional[float]:
        """
        Calculate CAGR given initial/final value and start/end date (datetime or str).
        Args:
            initial_value: Initial portfolio value
            final_value: Final portfolio value
            start_date: Start date (str or datetime)
            end_date: End date (str or datetime)
        Returns:
            CAGR value or None if calculation fails
        """
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

    @staticmethod
    def calculate_sortino(returns: Union[List[float], np.ndarray], risk_free_rate: float = 0.0) -> Optional[float]:
        """
        Calculate the Sortino ratio for a series of returns.
        Args:
            returns: List or array of returns
            risk_free_rate: Risk-free rate (default 0.0)
        Returns:
            Sortino ratio or None if not computable
        """
        returns = np.array(returns)
        downside = returns[returns < risk_free_rate]
        expected_return = np.mean(returns) - risk_free_rate
        downside_std = np.std(downside) if len(downside) > 0 else 0
        if downside_std > 0:
            return float(expected_return / downside_std)
        return None

    @staticmethod
    def calculate_calmar(returns: Union[List[float], np.ndarray], max_drawdown: float) -> Optional[float]:
        """
        Calculate the Calmar ratio: annualized return / max drawdown.
        Args:
            returns: List or array of returns
            max_drawdown: Maximum drawdown value
        Returns:
            Calmar ratio or None if not computable
        """
        ann_return = np.mean(returns) * 252  # Assuming daily returns
        if max_drawdown != 0:
            return float(ann_return / abs(max_drawdown))
        return None

    @staticmethod
    def calculate_omega(returns: Union[List[float], np.ndarray], threshold: float = 0.0) -> Optional[float]:
        """
        Calculate the Omega ratio for a series of returns.
        Args:
            returns: List or array of returns
            threshold: Threshold value (default 0.0)
        Returns:
            Omega ratio or None if not computable
        """
        returns = np.array(returns)
        gains = returns[returns > threshold] - threshold
        losses = threshold - returns[returns < threshold]
        if losses.sum() > 0:
            return float(gains.sum() / losses.sum())
        return None

    @staticmethod
    def calculate_rolling_sharpe(returns: Union[List[float], pd.Series], window: int = 30) -> pd.Series:
        """
        Calculate rolling Sharpe ratio using the basic formula:
        Sharpe Ratio = (Portfolio Return - Risk-free Rate) / Portfolio Standard Deviation
        
        Args:
            returns: List or Series of returns
            window: Rolling window size
        Returns:
            Series of rolling Sharpe ratios
        """
        if not isinstance(returns, pd.Series):
            returns = pd.Series(returns)
        
        # Calculate rolling mean and std
        rolling = returns.rolling(window)
        rolling_mean = rolling.mean()
        rolling_std = rolling.std()
        
        # Calculate Sharpe ratio with proper handling of zero std
        rolling_sharpe = pd.Series(index=returns.index, dtype='float64')
        mask = rolling_std != 0
        rolling_sharpe[mask] = rolling_mean[mask] / rolling_std[mask]
        
        return rolling_sharpe

    def _calculate_supertrend_for_plot(self, data_df: pd.DataFrame, period: int, multiplier: float) -> pd.Series:
        """
        Helper to calculate SuperTrend for plotting, using ta library for ATR.
        Args:
            data_df: DataFrame with OHLC data
            period: ATR/SuperTrend period
            multiplier: SuperTrend multiplier
        Returns:
            Series of SuperTrend values
        """
        if not all(col in data_df.columns for col in ['high', 'low', 'close']):
            self.log_message("Warning: Dataframe for SuperTrend calculation must contain 'high', 'low', 'close' columns.")
            return pd.Series(index=data_df.index, dtype='float64')

        atr_calculator = AverageTrueRange(high=data_df['high'], low=data_df['low'], close=data_df['close'], window=period, fillna=False)
        atr = atr_calculator.average_true_range()

        if atr is None or atr.empty or atr.isnull().all():
            self.log_message(f"ATR calculation failed or all NaN for ST plot. Period: {period}")
            return pd.Series(index=data_df.index, dtype='float64')
        atr = atr.reindex(data_df.index)

        hl2 = (data_df['high'] + data_df['low']) / 2
        basic_upperband = hl2 + multiplier * atr
        basic_lowerband = hl2 - multiplier * atr

        final_upperband = pd.Series(index=data_df.index, dtype='float64')
        final_lowerband = pd.Series(index=data_df.index, dtype='float64')
        supertrend = pd.Series(index=data_df.index, dtype='float64')

        final_upperband.iloc[0] = basic_upperband.iloc[0] if not pd.isna(basic_upperband.iloc[0]) else np.nan
        final_lowerband.iloc[0] = basic_lowerband.iloc[0] if not pd.isna(basic_lowerband.iloc[0]) else np.nan
        trend = 0

        first_valid_idx = atr.first_valid_index()
        if first_valid_idx is None:
            self.log_message("No valid ATR values to start SuperTrend calculation for plot.")
            return supertrend
        start_loc = data_df.index.get_loc(first_valid_idx)

        if data_df['close'].iloc[start_loc] > basic_upperband.iloc[start_loc]:
            trend = 1
            supertrend.iloc[start_loc] = basic_lowerband.iloc[start_loc]
        elif data_df['close'].iloc[start_loc] < basic_lowerband.iloc[start_loc]:
            trend = -1
            supertrend.iloc[start_loc] = basic_upperband.iloc[start_loc]
        else:
            supertrend.iloc[start_loc] = np.nan
            trend = 0 
        final_upperband.iloc[start_loc] = basic_upperband.iloc[start_loc]
        final_lowerband.iloc[start_loc] = basic_lowerband.iloc[start_loc]

        for i in range(start_loc + 1, len(data_df)):
            if pd.isna(atr.iloc[i]):
                final_upperband.iloc[i] = final_upperband.iloc[i-1]
                final_lowerband.iloc[i] = final_lowerband.iloc[i-1]
                supertrend.iloc[i] = supertrend.iloc[i-1]
                continue
            close = data_df['close'].iloc[i]
            prev_close = data_df['close'].iloc[i-1]
            if basic_upperband.iloc[i] < final_upperband.iloc[i-1] or prev_close > final_upperband.iloc[i-1]:
                final_upperband.iloc[i] = basic_upperband.iloc[i]
            else:
                final_upperband.iloc[i] = final_upperband.iloc[i-1]
            if basic_lowerband.iloc[i] > final_lowerband.iloc[i-1] or prev_close < final_lowerband.iloc[i-1]:
                final_lowerband.iloc[i] = basic_lowerband.iloc[i]
            else:
                final_lowerband.iloc[i] = final_lowerband.iloc[i-1]
            if trend == 1 and close < final_lowerband.iloc[i]:
                trend = -1
            elif trend == -1 and close > final_upperband.iloc[i]:
                trend = 1
            elif trend == 0:
                if close > basic_upperband.iloc[i]:
                    trend = 1
                elif close < basic_lowerband.iloc[i]:
                    trend = -1
            if trend == 1:
                supertrend.iloc[i] = final_lowerband.iloc[i]
            elif trend == -1:
                supertrend.iloc[i] = final_upperband.iloc[i]
            else:
                supertrend.iloc[i] = np.nan
        return supertrend

    def log_message(self, message: str, level: str = "info") -> None:
        """
        Log a message using the configured logger.
        Args:
            message: Message string
            level: "info" (default) for normal messages, "error" for errors.
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

    def get_result_filename(self, data_file, suffix='', current_data=None, strategy_name=None):
        """
        Generate a standardized filename for results and plots based on data_file and current_data.
        """
        import datetime
        # Extract strategy name
        if not strategy_name:
            strategy_name = getattr(self, 'strategy_name', 'Strategy')
        # Extract symbol, interval, and dates from data_file
        symbol = getattr(self, 'current_symbol', 'SYMBOL')
        interval = 'INTERVAL'
        start_date = 'STARTDATE'
        end_date = 'ENDDATE'
        
        if '_' in data_file:
            parts = data_file.replace('.csv','').split('_')
            if len(parts) >= 4:  # We expect at least symbol_interval_startdate_enddate
                symbol = parts[0]
                interval = parts[1]
                start_date = parts[2]
                end_date = parts[3]
        
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"{strategy_name}_{symbol}_{interval}_{start_date}_{end_date}_{timestamp}{suffix}"

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
                    if 'entry_time' in trades_df.columns and 'exit_time' in trades_df.columns:
                        trades_df = trades_df.dropna(subset=['entry_time', 'exit_time'])
                        if not trades_df.empty:
                            cagr = self.calculate_cagr(self.initial_capital, final_value, trades_df['entry_time'].iloc[0], trades_df['exit_time'].iloc[-1])
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
            # Ensure all metrics are present and not None, and move all to metrics dict
            metrics['sqn_pct'] = sqn_pct if sqn_pct is not None else 0.0
            metrics['cagr'] = cagr if cagr is not None else 0.0
            metrics['sortino_ratio'] = metrics.get('sortino_ratio', 0.0) or 0.0
            metrics['calmar_ratio'] = metrics.get('calmar_ratio', 0.0) or 0.0
            metrics['omega_ratio'] = metrics.get('omega_ratio', 0.0) or 0.0
            metrics['rolling_sharpe'] = metrics.get('rolling_sharpe', []) or []
            # Compose results dict
            results_dict = {
                'version': '1.0.0',
                'timestamp': datetime.now().isoformat(),
                'strategy_name': strategy_name,
                'data_file': data_file,
                'best_params': best_params,
                'metrics': metrics,
                'plot_path': plot_path,
                'trades': trades_records,
                'optimization_history': optimization_history
            }
            # Extract symbol, interval, start and end date
            symbol = getattr(self, 'current_symbol', 'SYMBOL')
            interval = 'INTERVAL'
            if '_' in data_file:
                parts = data_file.replace('.csv','').split('_')
                if len(parts) >= 2:
                    symbol = parts[0]
                    interval = parts[1]
            if hasattr(self, 'current_data') and self.current_data is not None and not self.current_data.empty:
                start_date = str(self.current_data.index.min())[:10]
                end_date = str(self.current_data.index.max())[:10]
            else:
                start_date = 'STARTDATE'
                end_date = 'ENDDATE'
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename_base = self.get_result_filename(data_file)
            results_path = os.path.join(self.results_dir, f'{filename_base}.json')
            self.log_message(f"Saving results to: {results_path}", level='info')
            try:
                json_str = json.dumps(results_dict, indent=4, cls=BaseOptimizer.DateTimeEncoder)
                with open(results_path, 'w') as f: f.write(json_str)
            except Exception as e:
                self.log_message(f"Error during JSON serialization: {e}. Trying to save simplified.", level='error')
                simplified_dict = {k: v for k, v in results_dict.items() if k not in ['trades', 'optimization_history']}
                simplified_dict['error_in_serialization'] = str(e)
                json_str = json.dumps(simplified_dict, indent=4, cls=BaseOptimizer.DateTimeEncoder)
                with open(results_path, 'w') as f: f.write(json_str)
                self.log_message("Saved simplified results due to serialization error.", level='error')
            self.log_message(f"Results saved to {results_path}", level='info')
            return results_dict
        except Exception as e:
            self.log_message(f"Error in save_results: {str(e)}", level='error')
            self.log_message(f"Full traceback: {traceback.format_exc()}", level='error')
            return None 

    def optimize_with_skopt(self, n_trials=100, n_random_starts=42, noise=0.01, n_jobs=-1, verbose=False):
        """
        Run optimization using scikit-optimize's gp_minimize.
        """
        result = gp_minimize(
            func=self.objective, 
            dimensions=self.space,
            n_calls=n_trials,  # Use n_trials for consistency
            n_random_starts=n_random_starts, 
            noise=noise, 
            n_jobs=n_jobs, 
            verbose=verbose
        )
        return result

    def get_optuna_objective(self):
        self.param_ranges = {p['name']: p for p in self.config.get('search_space', [])}
        exit_logic_config = self.config.get('exit_logic', {})
        exit_logic_name = exit_logic_config.get('name', 'atr_exit')
        exit_params_config = exit_logic_config.get('params', {})
        
        def objective(trial):
            # --- Suggest strategy parameters (add as needed) ---
            strategy_params = {}
            # Suggest all strategy params that are not exit logic params
            for pname, pinfo in self.param_ranges.items():
                if pname == 'exit_logic_name' or pname in EXIT_PARAM_MAP:
                    continue
                if pinfo['type'] == 'Real':
                    strategy_params[pname] = trial.suggest_float(pname, pinfo['low'], pinfo['high'])
                elif pinfo['type'] == 'Integer':
                    strategy_params[pname] = trial.suggest_int(pname, pinfo['low'], pinfo['high'])
                elif pinfo['type'] == 'Categorical':
                    strategy_params[pname] = trial.suggest_categorical(pname, pinfo['categories'])

            # --- Exit logic parameters ---
            exit_params = {}
            for param, pinfo in exit_params_config.items():
                if pinfo['type'] == 'Real':
                    exit_params[param] = trial.suggest_float(param, pinfo['low'], pinfo['high'])
                elif pinfo['type'] == 'Integer':
                    exit_params[param] = trial.suggest_int(param, pinfo['low'], pinfo['high'])
                elif pinfo['type'] == 'Categorical':
                    exit_params[param] = trial.suggest_categorical(param, pinfo['categories'])

            strategy_params['exit_logic_name'] = exit_logic_name
            strategy_params['exit_params'] = exit_params

            # --- Run backtest ---
            results = self.run_backtest(self.current_data.copy(), strategy_params)
            net_profit = results.get('trades', {}).get('pnl', {}).get('net', {}).get('total', 0.0) if results else 0.0
            return -net_profit
        return objective

    def optimize_single_file(self, data_file):
        """
        Generalized optimization routine for a single data file.
        Subclasses must set self.strategy_name and implement self.plot_results.
        """
        self.log_message(f"\nOptimizing {data_file} for {getattr(self, 'strategy_name', 'UnknownStrategy')}...", level='info')
        self.current_symbol = data_file.split('_')[0]
        if data_file not in self.raw_data:
            self.log_message(f"Error: No data for {data_file}.", level='error')
            return None
        self.current_data = self.raw_data[data_file].copy()
        if len(self.current_data) < 100:
            self.log_message(f"Warning: Insufficient data points in {data_file}. Skipping...", level='info')
            return None
        if self.current_data.isnull().any().any():
            self.log_message(f"Warning: Found missing values in {data_file}. Cleaning data...", level='info')
            self.current_data = self.current_data.fillna(method='ffill').fillna(method='bfill')
        self.current_metrics = {}
        try:
            # Get optimization method from config
            opt_method = self.config.get('optimization_method', 'skopt')  # Default to skopt for backward compatibility
            n_trials = self.config.get('n_trials', 100)
            n_random_starts = self.config.get('n_random_starts', 42)
            if opt_method == 'skopt':
                noise = self.config.get('noise', 0.01)
                n_jobs = self.config.get('n_jobs', -1)
                verbose = self.config.get('verbose', False)
                result = self.optimize_with_skopt(
                    n_trials=n_trials,
                    n_random_starts=n_random_starts,
                    noise=noise,
                    n_jobs=n_jobs,
                    verbose=verbose
                )
                best_params = self.params_to_dict(result.x)
                best_score = result.fun
            elif opt_method == 'optuna':
                study = optuna.create_study(direction='minimize')
                study.optimize(self.get_optuna_objective(), n_trials=n_trials)
                best_params = study.best_params
                best_score = study.best_value
                result = study
            else:
                raise ValueError(f"Unknown optimization method: {opt_method}")
            self.log_message(f"\nOptimization completed for {data_file}", level='info')
            self.log_message(f"Best params for {data_file}: {best_params}", level='info')
            self.log_message(f"Best score: {best_score:.2f}. Metrics: {self.current_metrics}", level='info')
            final_backtest_run = self.run_backtest(self.current_data.copy(), best_params)
            trades_df = pd.DataFrame()
            if final_backtest_run and hasattr(final_backtest_run.get('strategy', None), 'trades'):
                trades_list = final_backtest_run['strategy'].trades
                if trades_list:
                    trades_df = pd.DataFrame(trades_list)
                    # Calculate metrics from trades
                    self.current_metrics = self.calculate_metrics(trades_df)
                    # Add trade-specific metrics
                    self.current_metrics['total_trades'] = len(trades_list)
                    winning_trades = [t for t in trades_list if t.get('pnl_comm', 0) > 0]
                    self.current_metrics['win_rate'] = len(winning_trades) / len(trades_list) * 100 if trades_list else 0
                    losing_trades_sum = sum(t.get('pnl_comm', 0) for t in trades_list if t.get('pnl_comm', 0) <= 0)
                    if losing_trades_sum == 0:
                        self.current_metrics['profit_factor'] = float('inf') if winning_trades else 0
                    else:
                        self.current_metrics['profit_factor'] = abs(sum(t.get('pnl_comm', 0) for t in winning_trades) / losing_trades_sum)
                    self.current_metrics['net_profit'] = sum(t.get('pnl_comm', 0) for t in trades_list)
                    self.current_metrics['portfolio_growth_pct'] = (self.current_metrics['net_profit'] / self.initial_capital) * 100 if self.initial_capital > 0 else 0
                    self.current_metrics['final_value'] = self.initial_capital + self.current_metrics['net_profit']
            plot_path = None
            if hasattr(self, 'plot_results') and callable(self.plot_results):
                plot_path = self.plot_results(self.current_data.copy(), trades_df, best_params, data_file)
            return self.save_results(
                data_file=data_file,
                best_params=best_params,
                metrics=self.current_metrics,
                trades_df=trades_df,
                optimization_result=result,
                plot_path=plot_path,
                strategy_name=getattr(self, 'strategy_name', 'UnknownStrategy')
            )
        except Exception as e:
            self.log_message(f"Error during optimization for {data_file}: {str(e)}", level='error')
            self.log_message(traceback.format_exc(), level='error')
            return None

    def run_optimization(self):
        """
        Generalized optimization routine for all data files in self.data_dir.
        Calls optimize_single_file for each .csv file, collects results, and saves a combined results JSON.
        Subclasses can override for extra summary fields or dynamic loading.
        """
        self.log_message(f"Starting {self.__class__.__name__} optimization process...", level='info')
        data_files = [f for f in os.listdir(self.data_dir) if f.endswith('.csv') and not f.startswith('.')]
        if not data_files:
            self.log_message("No data files found. Exiting.", level='error')
            return

        all_results = []
        for data_file in data_files:
            try:
                if data_file not in self.raw_data:
                    self.log_message(f"Data for {data_file} not pre-loaded. Skipping.", level='warning')
                    continue
                result = self.optimize_single_file(data_file)
                if result is not None:
                    all_results.append(result)
            except Exception as e:
                self.log_message(f"Error processing {data_file}: {str(e)}", level='error')
                self.log_message(traceback.format_exc(), level='error')

        if not all_results:
            self.log_message("No optimization results generated.", level='error')
            return

        combined_results = {
            'version': '1.0.0',
            'timestamp': datetime.now().isoformat(),
            'optimizer_class': self.__class__.__name__,
            'strategy_name': getattr(self, 'strategy_name', 'UnknownStrategy'),
            'results': all_results
        }
        combined_path = os.path.join(self.results_dir, f'combined_optimization_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
        try:
            with open(combined_path, 'w') as f:
                json.dump(combined_results, f, indent=4, cls=BaseOptimizer.DateTimeEncoder)
            self.log_message(f"\nCombined results saved to {combined_path}", level='info')
        except Exception as e:
            self.log_message(f"Error saving combined JSON: {e}", level='error') 

    def run_backtest(self, data, params):
        """
        Generic Backtrader backtest runner. Uses self.strategy_class for the strategy.
        Subclasses can override customize_cerebro(self, cerebro) for custom analyzers or broker setup.
        """
        cerebro = bt.Cerebro()
        if not isinstance(data.index, pd.DatetimeIndex):
            self.log_message("Error: Data for backtest must have a DatetimeIndex.")
            return None
        expected_cols = ['open', 'high', 'low', 'close', 'volume']
        if not all(col in data.columns for col in expected_cols):
            self.log_message(f"Error: Data missing one of required columns: {expected_cols}")
            return None

        data_feed = bt.feeds.PandasData(
            dataname=data,
            datetime=None, open='open', high='high', low='low', close='close', volume='volume',
            openinterest=-1
        )
        cerebro.adddata(data_feed)
        cerebro.broker.setcash(self.initial_capital)
        cerebro.broker.setcommission(commission=self.commission)
        cerebro.broker.set_checksubmit(False)
        
        params['notify'] = self.notify
        # Extract ticker from data file name if not already present
        if 'ticker' not in params and hasattr(self, 'current_data_file'):
            params['ticker'] = self.current_data_file.split('_')[0]
        cerebro.addstrategy(self.strategy_class, params=params)
        
        # Only add essential analyzers for optimization
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        
        # Allow subclass customization
        if hasattr(self, 'customize_cerebro') and callable(self.customize_cerebro):
            self.customize_cerebro(cerebro)
            
        try:
            results = cerebro.run()
            if not results:
                self.log_message(f"Backtest with params {params} did not yield valid results object.")
                return None
            strategy = results[0]
            drawdown = strategy.analyzers.drawdown.get_analysis()
            trades = strategy.analyzers.trades.get_analysis()
            return {
                'strategy': strategy,
                'drawdown': drawdown,
                'trades': trades
            }
        except Exception as e:
            self.log_message(f"Error during backtest run for params {params}: {str(e)}")
            self.log_message(traceback.format_exc(), level='error')
            return None

    @lru_cache(maxsize=128)
    def calculate_metrics(self, trades_df: pd.DataFrame, equity_curve: pd.Series = None) -> Dict[str, Any]:
        """
        Calculate and return all relevant metrics, including sortino_ratio, calmar_ratio, omega_ratio, etc.
        Args:
            trades_df: DataFrame of trades
            equity_curve: Series of equity values (optional)
        Returns:
            Dictionary of metrics
        """
        metrics = {}
        if trades_df is not None and not trades_df.empty:
            # Calculate returns from trades
            returns = trades_df['pnl_comm'] / trades_df['entry_price']
            
            # Calculate max drawdown from equity curve if available
            if equity_curve is not None and not equity_curve.empty:
                max_drawdown = (equity_curve / equity_curve.cummax() - 1).min()
            else:
                max_drawdown = 0
                
            # Calculate essential metrics only
            metrics['max_drawdown'] = max_drawdown
            metrics['total_trades'] = len(trades_df)
            metrics['win_rate'] = len(trades_df[trades_df['pnl_comm'] > 0]) / len(trades_df) * 100 if len(trades_df) > 0 else 0
            metrics['net_profit'] = trades_df['pnl_comm'].sum()
            metrics['profit_factor'] = abs(trades_df[trades_df['pnl_comm'] > 0]['pnl_comm'].sum() / trades_df[trades_df['pnl_comm'] < 0]['pnl_comm'].sum()) if len(trades_df[trades_df['pnl_comm'] < 0]) > 0 else float('inf')
        else:
            metrics['max_drawdown'] = 0
            metrics['total_trades'] = 0
            metrics['win_rate'] = 0
            metrics['net_profit'] = 0
            metrics['profit_factor'] = 0
            
        return metrics

    def objective(self, params):
        """
        Objective function for optimization. Runs backtest and returns negative net profit.
        """
        param_dict = self.params_to_dict(params)
        param_key = str(param_dict)  # Use string representation as cache key
        
        # Check cache first
        if param_key in self.metrics_cache:
            return -self.metrics_cache[param_key]['net_profit']
            
        backtest_results = self.run_backtest(self.current_data, param_dict)
        if backtest_results is None:
            return float('inf')
            
        trades = backtest_results['strategy'].get_trades()
        if not trades:
            return float('inf')
            
        trades_df = pd.DataFrame(trades)
        
        # Calculate only essential metrics for optimization
        metrics = {
            'net_profit': trades_df['pnl_comm'].sum(),
            'total_trades': len(trades_df),
            'win_rate': len(trades_df[trades_df['pnl_comm'] > 0]) / len(trades_df) * 100 if len(trades_df) > 0 else 0,
            'max_drawdown': backtest_results['drawdown'].get('max', {}).get('drawdown', 0)
        }
        
        # Cache the results
        self.metrics_cache[param_key] = metrics
        
        # Only save results if they're better than previous best
        if metrics['net_profit'] > self.best_metrics:
            self.best_metrics = metrics['net_profit']
            # Calculate additional metrics only for saving results
            full_metrics = self.calculate_metrics(trades_df)
            self.save_results(
                data_file=self.current_data_file,
                best_params=param_dict,
                metrics=full_metrics,
                trades_df=trades_df,
                optimization_result=self.optimization_result,
                plot_path=self.plot_path,
                strategy_name=self.strategy_name
            )
            
        return -metrics['net_profit']

    def _build_skopt_space_from_config(self, search_space_config):
        """
        Build a skopt search space from a config list of parameter dicts.
        Args:
            search_space_config: List of parameter dicts with keys 'type', 'name', and bounds/categories.
        Returns:
            List of skopt.space.Dimension objects (Integer, Real, Categorical)
        """
        skopt_space = []
        for param in search_space_config:
            if param['type'] == 'Integer':
                skopt_space.append(Integer(param['low'], param['high'], name=param['name']))
            elif param['type'] == 'Real':
                skopt_space.append(Real(param['low'], param['high'], name=param['name']))
            elif param['type'] == 'Categorical':
                skopt_space.append(Categorical(param['categories'], name=param['name']))
        return skopt_space 