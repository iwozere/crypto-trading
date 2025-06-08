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
import sys
import warnings

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import datetime
import json
import traceback
import warnings
from functools import lru_cache
from typing import Any, Dict, List, Optional, Union

import backtrader as bt
import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import numpy as np
import optuna
import pandas as pd
import seaborn as sns
import talib
from skopt import gp_minimize
from skopt.space import Categorical, Integer, Real
from src.exit.exit_registry import EXIT_PARAM_MAP
from src.notification.logger import _logger
from src.strategy.strategy_registry import get_strategy_info


class BaseOptimizer:
    """
    Base class for all optimizers.
    Provides common functionality for parameter optimization, backtesting, and result visualization.
    """

    def _load_config(self, config_path: str) -> dict:
        """
        Load configuration from a JSON file.
        
        Args:
            config_path (str): Path to the configuration file
            
        Returns:
            dict: Configuration dictionary
        """
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            return config
        except Exception as e:
            raise ValueError(f"Failed to load configuration from {config_path}: {e}")

    def _get_strategy_class(self):
        """Get the strategy class based on the strategy name in config."""
        strategy_name = self.config.get("strategy_name")
        if not strategy_name:
            raise ValueError("Strategy name not specified in config")
            
        strategy_info = get_strategy_info(strategy_name)
        if not strategy_info:
            raise ValueError(f"Unknown strategy: {strategy_name}")
            
        return strategy_info["class"]

    def __init__(self, config_path: Union[str, dict]):
        """Initialize the optimizer with configuration."""
        if isinstance(config_path, str):
            self.config = self._load_config(config_path)
        else:
            self.config = config_path
            
        self.strategy_class = self._get_strategy_class()
        self.data_dir = self.config["data_dir"]
        self.results_dir = self.config["results_dir"]
        self.symbol = self.config["symbol"]
        self.interval = self.config["interval"]
        self.start_date = self.config["start_date"]
        self.end_date = self.config["end_date"]
        self.initial_capital = self.config["initial_capital"]
        self.commission = self.config["commission"]
        self.risk_free_rate = self.config["risk_free_rate"]
        self.omega_threshold = self.config["omega_threshold"]
        self.use_talib = self.config["use_talib"]
        
        # Get optimization settings from nested structure
        self.optimization_settings = self.config["optimization_settings"]
        self.optimization_method = self.optimization_settings["optimization_method"]
        self.n_trials = self.optimization_settings["n_trials"]
        self.n_jobs = self.optimization_settings["n_jobs"]
        self.random_state = self.optimization_settings["random_state"]
        
        self.exit_logic = self.config["exit_logic"]
        self.parameters = self.config.get("parameters", {})  # Initialize parameters
        self.search_space = self.config["search_space"]
        self.default_params = self.config["default_params"]
        
        # Get visualization settings from nested structure
        self.visualization_settings = self.config["visualization_settings"]
        self.plot = self.visualization_settings["plot"]
        self.save_trades = self.visualization_settings["save_trades"]
        self.plot_size = self.visualization_settings["plot_size"]
        
        # Create a single notifier instance if notifications are enabled
        self.notifier = None
        if self.config.get("notify", False):
            from src.notification.telegram_notifier import create_notifier
            self.notifier = create_notifier()

        self.strategy_name = self.config.get("strategy_name", "")
        self.plot_style = self.visualization_settings.get("plot_style", "default")
        self.font_size = self.visualization_settings.get("font_size", 10)
        self.plot_dpi = self.visualization_settings.get("plot_dpi", 300)
        self.show_grid = self.visualization_settings.get("show_grid", True)
        self.legend_loc = self.visualization_settings.get("legend_loc", "upper left")
        self.save_plot = self.visualization_settings.get("save_plot", True)
        self.show_plot = self.visualization_settings.get("show_plot", False)
        self.plot_format = self.visualization_settings.get("plot_format", "png")
        self.show_equity_curve = self.visualization_settings.get("show_equity_curve", True)
        self.show_indicators = self.visualization_settings.get("show_indicators", True)
        self.color_scheme = self.visualization_settings.get("color_scheme", {})
        self.report_metrics = self.visualization_settings.get("report_metrics", [])
        self.trades_csv_path = self.visualization_settings.get("trades_csv_path", None)
        self.save_metrics = self.visualization_settings.get("save_metrics", True)
        self.metrics_format = self.visualization_settings.get("metrics_format", "json")
        self.print_summary = self.visualization_settings.get("print_summary", True)
        self.report_params = self.visualization_settings.get("report_params", True)
        self.report_filename_pattern = self.visualization_settings.get("report_filename_pattern", None)
        self.include_plots_in_report = self.visualization_settings.get("include_plots_in_report", True)
        warnings.filterwarnings("ignore", category=UserWarning, module="skopt")
        warnings.filterwarnings("ignore", category=RuntimeWarning)
        self.current_metrics = {}
        self.current_data = None
        self.current_symbol = None
        self.raw_data = {}
        self.best_metrics = float("-inf")
        self.metrics_cache = {}
        self.load_all_data()

    class DateTimeEncoder(json.JSONEncoder):
        def default(self, obj: Any) -> Any:
            if isinstance(obj, (pd.Timestamp, datetime.datetime)):
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
        trades_df = trades_df.dropna(subset=["entry_price", "pnl_comm"])
        if trades_df.empty:
            return None
        trades_df["pct_return"] = trades_df["pnl_comm"] / trades_df["entry_price"] * 100
        returns = trades_df["pct_return"].values
        n = len(returns)
        if n > 1 and np.std(returns) > 0:
            return float(np.mean(returns) / np.std(returns) * np.sqrt(n))
        return None

    @staticmethod
    def calculate_cagr(
        initial_value: float,
        final_value: float,
        start_date: Union[str, datetime.datetime],
        end_date: Union[str, datetime.datetime],
    ) -> Optional[float]:
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
                cagr = (final_value / initial_value) ** (1 / years) - 1
                return float(cagr)
        except Exception:
            pass
        return None

    @staticmethod
    def calculate_sortino(
        returns: Union[List[float], np.ndarray], risk_free_rate: float = 0.0
    ) -> Optional[float]:
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
    def calculate_calmar(
        returns: Union[List[float], np.ndarray], max_drawdown: float
    ) -> Optional[float]:
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
    def calculate_omega(
        returns: Union[List[float], np.ndarray], threshold: float = 0.0
    ) -> Optional[float]:
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
    def calculate_rolling_sharpe(
        returns: Union[List[float], pd.Series], window: int = 30
    ) -> pd.Series:
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
        rolling_sharpe = pd.Series(index=returns.index, dtype="float64")
        mask = rolling_std != 0
        rolling_sharpe[mask] = rolling_mean[mask] / rolling_std[mask]

        return rolling_sharpe

    def _calculate_supertrend_for_plot(
        self, data_df: pd.DataFrame, period: int, multiplier: float
    ) -> pd.Series:
        """
        Helper to calculate SuperTrend for plotting, using TA-Lib for ATR.
        Args:
            data_df: DataFrame with OHLC data
            period: ATR/SuperTrend period
            multiplier: SuperTrend multiplier
        Returns:
            Series of SuperTrend values
        """
        if not all(col in data_df.columns for col in ["high", "low", "close"]):
            self.log_message(
                "Warning: Dataframe for SuperTrend calculation must contain 'high', 'low', 'close' columns."
            )
            return pd.Series(index=data_df.index, dtype="float64")

        # Calculate ATR using TA-Lib
        atr = talib.ATR(
            data_df["high"].values,
            data_df["low"].values,
            data_df["close"].values,
            timeperiod=period,
        )

        if atr is None or len(atr) == 0 or np.isnan(atr).all():
            self.log_message(
                f"ATR calculation failed or all NaN for ST plot. Period: {period}"
            )
            return pd.Series(index=data_df.index, dtype="float64")

        # Convert to pandas Series for easier manipulation
        atr = pd.Series(atr, index=data_df.index)

        # Calculate SuperTrend
        hl2 = (data_df["high"] + data_df["low"]) / 2
        upperband = hl2 + (multiplier * atr)
        lowerband = hl2 - (multiplier * atr)

        supertrend = pd.Series(index=data_df.index, dtype="float64")
        direction = pd.Series(index=data_df.index, dtype="float64")

        for i in range(1, len(data_df)):
            if data_df["close"][i] > upperband[i - 1]:
                direction[i] = 1
            elif data_df["close"][i] < lowerband[i - 1]:
                direction[i] = -1
            else:
                direction[i] = direction[i - 1]

            if direction[i] == 1:
                supertrend[i] = lowerband[i]
            else:
                supertrend[i] = upperband[i]

        return supertrend

    def log_message(self, message: str, level: str = "info") -> None:
        """
        Log a message using the configured logger.
        Args:
            message: Message to log
            level: Log level (info, warning, error)
        """
        import logging
        logger = logging.getLogger(__name__)

        if level == "error":
            logger.error(message)
        elif level == "warning":
            logger.warning(message)
        else:
            logger.info(message)

    def load_all_data(
        self,
        data_dir=None,
        required_columns=None,
        parse_dates=True,
        sort_index=True,
        fillna=True,
        log=True,
    ):
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
            required_columns = ["open", "high", "low", "close", "volume"]
        self.raw_data = {}
        data_files = [f for f in os.listdir(data_dir) if f.endswith(".csv")]
        for data_file in data_files:
            try:
                df = pd.read_csv(os.path.join(data_dir, data_file))
                if parse_dates and "timestamp" in df.columns:
                    df["timestamp"] = pd.to_datetime(df["timestamp"])
                    df.set_index("timestamp", inplace=True)
                for col in required_columns:
                    if col not in df.columns:
                        if col == "volume":
                            self.log_message(
                                f"Warning: 'volume' column missing in {data_file}. Creating dummy 'volume' column with zeros."
                            )
                            df["volume"] = 0
                        else:
                            raise ValueError(
                                f"Missing required column: {col} in {data_file}"
                            )
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                if sort_index:
                    df.sort_index(inplace=True)
                if fillna:
                    if df.isnull().any().any():
                        self.log_message(
                            f"Warning: NaN values found in {data_file}. Forward-filling and back-filling."
                        )
                        df.ffill(inplace=True)
                        df.bfill(inplace=True)
                    if df.isnull().any().any():
                        self.log_message(
                            f"Error: NaN values persist in {data_file} after fill. Skipping."
                        )
                        continue
                self.raw_data[data_file] = df
                if log:
                    self.log_message(
                        f"Loaded data for {data_file}, shape: {df.shape}, date range: {df.index.min()} to {df.index.max()}"
                    )
            except Exception as e:
                self.log_message(f"Error loading {data_file}: {str(e)}")

    def params_to_dict(self, params, param_types=None):
        """
        Convert parameter list to dictionary with proper types.
        
        Args:
            params: List of parameter values
            param_types: dict of {param_name: type}, e.g. {'rsi_period': int, ...}
                        If not provided, will use int for names containing 'period', else float.
        
        Returns:
            Dictionary of parameters with proper types
        """
        # Get parameter names from search space
        param_names = [p["name"] for p in self.search_space]
        
        # Create dictionary from names and values
        param_dict = dict(zip(param_names, params))
        
        # Convert types
        typed_param_dict = {}
        for name, value in param_dict.items():
            if param_types and name in param_types:
                typed_param_dict[name] = param_types[name](value)
            elif (
                "period" in name
                or "window" in name
                or "fast" in name
                or "slow" in name
                or "mid" in name
            ):
                typed_param_dict[name] = int(value)
            elif isinstance(value, bool):
                typed_param_dict[name] = bool(value)
            else:
                typed_param_dict[name] = float(value)
        
        return typed_param_dict

    def get_result_filename(
        self, data_file, suffix="", current_data=None, strategy_name=None
    ):
        """
        Generate a standardized filename for results and plots based on data_file and current_data.
        """
        # Extract strategy name
        if not strategy_name:
            strategy_name = getattr(self, "strategy_name", "Strategy")
        # Extract symbol, interval, and dates from data_file
        symbol = getattr(self, "current_symbol", "SYMBOL")
        interval = "INTERVAL"
        start_date = "STARTDATE"
        end_date = "ENDDATE"

        if "_" in data_file:
            parts = data_file.replace(".csv", "").split("_")
            if len(parts) >= 4:  # We expect at least symbol_interval_startdate_enddate
                symbol = parts[0]
                interval = parts[1]
                start_date = parts[2]
                end_date = parts[3]

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{strategy_name}_{symbol}_{interval}_{start_date}_{end_date}_{timestamp}{suffix}"

    def save_results(self, study, data_file, current_data):
        """
        Save optimization results to JSON and generate plots.
        """
        try:
            # Get the result filename
            result_filename = self.get_result_filename(data_file, current_data)
            if not result_filename:
                self.log_message("Failed to generate result filename", level="error")
                return

            # Extract strategy name from data file
            strategy_name = self._extract_strategy_name(data_file)
            if not strategy_name:
                self.log_message("Failed to extract strategy name", level="error")
                return

            # Create results dictionary
            results_dict = {
                "version": "1.0.0",
                "timestamp": datetime.datetime.now().isoformat(),
                "optimization_date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "strategy_name": strategy_name,
                "data_file": data_file,
                "best_params": study.best_params,
                "best_value": study.best_value,
                "n_trials": len(study.trials),
                "best_trial": {
                    "number": study.best_trial.number,
                    "params": study.best_trial.params,
                    "value": study.best_trial.value,
                    "datetime_start": study.best_trial.datetime_start.isoformat() if study.best_trial.datetime_start else None,
                    "datetime_complete": study.best_trial.datetime_complete.isoformat() if study.best_trial.datetime_complete else None,
                } if study.best_trial else None
            }

            # Save results to JSON
            json_path = os.path.join(self.results_dir, f"{result_filename}.json")
            with open(json_path, "w") as f:
                json.dump(results_dict, f, indent=4)
            self.log_message(f"Results saved to {json_path}", level="info")

            # Generate and save plot
            plot_path = os.path.join(self.results_dir, f"{result_filename}_plot.png")
            try:
                fig = optuna.visualization.plot_optimization_history(study)
                fig.write_image(plot_path)
                self.log_message(f"Plot saved to {plot_path}", level="info")
            except Exception as e:
                self.log_message(f"Error generating plot: {str(e)}", level="error")

        except Exception as e:
            self.log_message(f"Error saving results: {str(e)}", level="error")
            self.log_message(traceback.format_exc(), level="error")

    def _extract_strategy_name(self, data_file):
        """
        Extract strategy name from data file name.
        Example: RSIBollVolumeATRStrategy_ETHUSDT_4h_20240501_20250501.csv -> RSIBollVolumeATRStrategy
        """
        try:
            # Split by underscore and take the first part
            return data_file.split('_')[0]
        except Exception as e:
            self.log_message(f"Error extracting strategy name: {str(e)}", level="error")
            return None

    def optimize_with_skopt(
        self, n_trials=100, n_random_starts=42, noise=0.01, n_jobs=-1, verbose=False
    ):
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
            verbose=verbose,
        )
        return result

    def get_optuna_objective(self):
        self.param_ranges = {p["name"]: p for p in self.config.get("search_space", [])}
        exit_logic_config = self.config.get("exit_logic", {})
        if isinstance(exit_logic_config, dict):
            exit_logic_name = exit_logic_config.get("name", "atr_exit")
            exit_params_config = exit_logic_config.get("params", {})
        else:
            exit_logic_name = "atr_exit"
            exit_params_config = {}

        def objective(trial):
            # --- Suggest strategy parameters ---
            strategy_params = {}
            
            # Get all parameters that need to be optimized
            all_params = {**self.param_ranges, **exit_params_config}
            
            # Suggest values for all parameters
            for pname, pinfo in all_params.items():
                if pinfo["type"] == "Real":
                    strategy_params[pname] = trial.suggest_float(
                        pname, pinfo["low"], pinfo["high"]
                    )
                elif pinfo["type"] == "Integer":
                    strategy_params[pname] = trial.suggest_int(
                        pname, pinfo["low"], pinfo["high"]
                    )
                elif pinfo["type"] == "Categorical":
                    strategy_params[pname] = trial.suggest_categorical(
                        pname, pinfo["categories"]
                    )

            # Add exit logic name
            strategy_params["exit_logic_name"] = exit_logic_name

            try:
                # --- Run backtest ---
                results = self.run_backtest(strategy_params)
                
                # Get net profit from analyzers
                analysis = results.analyzers.trades.get_analysis()
                
                # Handle nested dictionary structure
                try:
                    pnl = analysis.get('pnl', {})
                    net_profit = float(pnl.get('net', 0.0))
                except (KeyError, AttributeError, TypeError):
                    net_profit = 0.0
                
                # Return negative net profit (since we want to maximize)
                return -net_profit
                
            except Exception as e:
                import traceback
                error_msg = f"Error in objective function: {str(e)}\n{traceback.format_exc()}"
                self.log_message(error_msg, level="error")
                return float('inf')  # Return worst possible value if anything fails

        return objective

    def optimize_single_file(self, file_path, n_trials=100, final_backtest_run=True):
        """Run optimization for a single file."""
        try:
            self.log_message(f"Starting optimization for {file_path}")
            
            # Load data if not already loaded
            if not hasattr(self, 'raw_data') or self.raw_data is None:
                self.load_all_data()
            
            # Set current file and data
            self.current_file = file_path
            self.current_data = self.raw_data[file_path].copy()
            
            if self.current_data.empty:
                self.log_message(f"No data found for {file_path}. Skipping.", level="error")
                return None
                
            # Fill any missing values using recommended methods
            self.current_data = self.current_data.ffill().bfill()

            # Create study
            study = optuna.create_study(
                direction="minimize",
                sampler=optuna.samplers.TPESampler(seed=42),
            )

            # Run optimization
            study.optimize(self.get_optuna_objective(), n_trials=n_trials)

            # Get best parameters
            best_params = study.best_params
            self.log_message(f"Best parameters: {best_params}")

            # Run final backtest with best parameters if requested
            try:
                if final_backtest_run:
                    final_results = self.run_backtest(best_params)
                    if hasattr(final_results, 'analyzers') and hasattr(final_results.analyzers, 'trades'):
                        final_analysis = final_results.analyzers.trades.get_analysis()
                        self.log_message(f"Final backtest results: {final_analysis}")
            except Exception as e:
                self.log_message(f"Error in final backtest: {str(e)}", level="error")

            return study

        except Exception as e:
            self.log_message(f"Error in optimize_single_file: {str(e)}", level="error")
            return None

    def run_optimization(self):
        """
        Generalized optimization routine for all data files in self.data_dir.
        Calls optimize_single_file for each .csv file, collects results, and saves a combined results JSON.
        Subclasses can override for extra summary fields or dynamic loading.
        """
        self.log_message(
            f"Starting {self.__class__.__name__} optimization process...", level="info"
        )
        data_files = [
            f
            for f in os.listdir(self.data_dir)
            if f.endswith(".csv") and not f.startswith(".")
        ]
        if not data_files:
            self.log_message("No data files found. Exiting.", level="error")
            return

        all_results = []
        for data_file in data_files:
            try:
                if data_file not in self.raw_data:
                    self.log_message(
                        f"Data for {data_file} not pre-loaded. Skipping.",
                        level="warning",
                    )
                    continue
                result = self.optimize_single_file(data_file)
                if result is not None:
                    # Extract serializable data from the study
                    study_data = {
                        "best_params": result.best_params,
                        "best_value": result.best_value,
                        "n_trials": len(result.trials),
                        "best_trial": {
                            "number": result.best_trial.number,
                            "params": result.best_trial.params,
                            "value": result.best_trial.value,
                            "datetime_start": result.best_trial.datetime_start.isoformat() if result.best_trial.datetime_start else None,
                            "datetime_complete": result.best_trial.datetime_complete.isoformat() if result.best_trial.datetime_complete else None,
                        } if result.best_trial else None
                    }
                    all_results.append(study_data)
            except Exception as e:
                self.log_message(
                    f"Error processing {data_file}: {str(e)}", level="error"
                )
                self.log_message(traceback.format_exc(), level="error")

        if not all_results:
            self.log_message("No optimization results generated.", level="error")
            return

        combined_results = {
            "version": "1.0.0",
            "timestamp": datetime.datetime.now().isoformat(),
            "optimizer_class": self.__class__.__name__,
            "strategy_name": getattr(self, "strategy_name", "UnknownStrategy"),
            "results": all_results,
        }
        combined_path = os.path.join(
            self.results_dir,
            f'combined_optimization_results_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.json',
        )
        try:
            with open(combined_path, "w") as f:
                json.dump(combined_results, f, indent=4)
            self.log_message(
                f"\nCombined results saved to {combined_path}", level="info"
            )
        except Exception as e:
            self.log_message(f"Error saving combined JSON: {e}", level="error")

    def _prepare_strategy_params(self, params):
        """
        Prepare strategy parameters including exit logic parameters.
        
        Args:
            params: Dictionary of strategy parameters
            
        Returns:
            Dictionary of prepared parameters for the strategy
        """
        # Start with the base parameters
        strategy_params = params.copy()
        
        # Get exit logic configuration
        exit_logic_config = self.config.get("exit_logic", {})
        exit_logic_name = exit_logic_config.get("name", "atr_exit")
        
        # Extract exit logic parameters from the optimized params
        exit_params = {}
        for param_name, param_value in params.items():
            if param_name in EXIT_PARAM_MAP.get(exit_logic_name, {}):
                exit_params[param_name] = param_value
        
        # Add exit logic name and params
        strategy_params["exit_logic_name"] = exit_logic_name
        strategy_params["exit_params"] = exit_params
        
        return strategy_params

    def run_backtest(self, params, data=None):
        """
        Run a single backtest with the given parameters.
        
        Args:
            params: Dictionary of strategy parameters
            data: Optional data to use for backtest. If None, will use self.current_data.
        """
        cerebro = bt.Cerebro()

        # Add data
        if data is None:
            if self.current_data is None:
                raise ValueError("No data available for backtest. Call load_all_data() first.")
            data = self.current_data
            
        # Convert DataFrame to Backtrader data feed
        if isinstance(data, pd.DataFrame):
            data = bt.feeds.PandasData(
                dataname=data,
                datetime=None,  # Use index as datetime
                open='open',
                high='high',
                low='low',
                close='close',
                volume='volume',
                openinterest=-1
            )
        cerebro.adddata(data)

        # Add strategy with parameters
        strategy_params = self._prepare_strategy_params(params)
        if self.notifier:
            strategy_params["notify"] = True
        cerebro.addstrategy(self.strategy_class, params=strategy_params)

        # Add analyzers
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe")
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
        cerebro.addanalyzer(bt.analyzers.Returns, _name="returns")
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")

        # Set broker parameters
        cerebro.broker.setcash(self.initial_capital)
        cerebro.broker.setcommission(commission=self.commission)

        # Run backtest
        results = cerebro.run()
        return results[0]

    @staticmethod
    def calculate_metrics(
        trades_df: pd.DataFrame, equity_curve: pd.Series = None
    ) -> Dict[str, Any]:
        """
        Calculate performance metrics from trades DataFrame.
        Args:
            trades_df: DataFrame containing trade records
            equity_curve: Optional Series containing equity curve values
        Returns:
            Dictionary of calculated metrics
        """
        if trades_df is None or trades_df.empty:
            return {}

        try:
            # Calculate basic metrics
            total_trades = len(trades_df)
            winning_trades = len(trades_df[trades_df["pnl_comm"] > 0])
            losing_trades = len(trades_df[trades_df["pnl_comm"] <= 0])

            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

            # Calculate profit metrics
            gross_profit = trades_df[trades_df["pnl_comm"] > 0]["pnl_comm"].sum()
            gross_loss = abs(trades_df[trades_df["pnl_comm"] <= 0]["pnl_comm"].sum())
            net_profit = trades_df["pnl_comm"].sum()

            # Calculate risk metrics
            profit_factor = (
                abs(gross_profit / gross_loss) if gross_loss != 0 else float("inf")
            )

            # Calculate drawdown
            if "equity" in trades_df.columns:
                equity_curve = trades_df["equity"]
            elif equity_curve is not None:
                equity_curve = equity_curve
            else:
                equity_curve = (1 + trades_df["pnl_comm"]).cumprod()

            rolling_max = equity_curve.expanding().max()
            drawdown = (equity_curve - rolling_max) / rolling_max * 100
            max_drawdown = abs(drawdown.min())

            # Calculate return metrics
            if "entry_time" in trades_df.columns and "exit_time" in trades_df.columns:
                start_date = trades_df["entry_time"].min()
                end_date = trades_df["exit_time"].max()
                days = (end_date - start_date).days
                if days > 0:
                    cagr = ((1 + net_profit) ** (365 / days)) - 1
                else:
                    cagr = 0
            else:
                cagr = 0

            # Calculate risk-adjusted return metrics
            returns = trades_df["pnl_comm"]
            if len(returns) > 1:
                sharpe_ratio = (
                    returns.mean() / returns.std() * np.sqrt(252)
                    if returns.std() != 0
                    else 0
                )
                sortino_ratio = (
                    returns.mean() / returns[returns < 0].std() * np.sqrt(252)
                    if len(returns[returns < 0]) > 0
                    else 0
                )
                calmar_ratio = cagr / max_drawdown if max_drawdown != 0 else 0
            else:
                sharpe_ratio = sortino_ratio = calmar_ratio = 0

            return {
                "total_trades": total_trades,
                "winning_trades": winning_trades,
                "losing_trades": losing_trades,
                "win_rate": win_rate,
                "gross_profit": gross_profit,
                "gross_loss": gross_loss,
                "net_profit": net_profit,
                "profit_factor": profit_factor,
                "max_drawdown": max_drawdown,
                "cagr": cagr,
                "sharpe_ratio": sharpe_ratio,
                "sortino_ratio": sortino_ratio,
                "calmar_ratio": calmar_ratio,
            }

        except Exception as e:
            print(f"Error calculating metrics: {str(e)}")
            return {}

    def objective(self, params):
        """
        Objective function for optimization.
        Converts parameters to dictionary and runs backtest.
        """
        try:
            # Convert parameters to dictionary
            param_dict = self.params_to_dict(params)
            
            # Run backtest with parameters
            backtest_results = self.run_backtest(param_dict)
            
            # Extract metrics from analyzers
            sharpe_ratio = backtest_results.analyzers.sharpe.get_analysis().get('sharperatio', 0.0)
            drawdown = backtest_results.analyzers.drawdown.get_analysis().get('max', {}).get('drawdown', 0.0)
            returns = backtest_results.analyzers.returns.get_analysis().get('rtot', 0.0)
            trades = backtest_results.analyzers.trades.get_analysis()
            
            # Calculate objective value (e.g., Sharpe ratio)
            objective_value = sharpe_ratio if sharpe_ratio is not None else 0.0
            
            # Log results
            self.log_message(
                f"Parameters: {param_dict}, Objective: {objective_value:.4f}",
                level="debug"
            )
            
            return -objective_value  # Negative because we want to maximize
            
        except Exception as e:
            self.log_message(f"Error in objective function: {str(e)}", level="error")
            return 0.0  # Return worst possible value on error

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
            if param["type"] == "Integer":
                skopt_space.append(
                    Integer(param["low"], param["high"], name=param["name"])
                )
            elif param["type"] == "Real":
                skopt_space.append(
                    Real(param["low"], param["high"], name=param["name"])
                )
            elif param["type"] == "Categorical":
                skopt_space.append(Categorical(param["categories"], name=param["name"]))
        return skopt_space

    def optimize(self):
        """Run the optimization process."""
        try:
            opt_method = self.optimization_settings.get("optimization_method", "skopt")
            if opt_method == "skopt":
                self._run_bayesian_optimization()
            elif opt_method == "optuna":
                self._run_optuna_optimization()
            else:
                raise ValueError(f"Unknown optimization method: {opt_method}")
        except Exception as e:
            _logger.error(f"Optimization failed: {e}")
            if self.notifier:
                self.notifier.send_message(f"Optimization failed: {e}")
            raise

    def _run_bayesian_optimization(self):
        """Run Bayesian optimization using scikit-optimize."""
        try:
            # Convert search space to skopt format
            dimensions = []
            for param in self.search_space:
                if param["type"] == "Integer":
                    dimensions.append(Integer(param["low"], param["high"], name=param["name"]))
                elif param["type"] == "Real":
                    dimensions.append(Real(param["low"], param["high"], name=param["name"]))
                elif param["type"] == "Categorical":
                    dimensions.append(Categorical(param["values"], name=param["name"]))

            # Run optimization
            result = gp_minimize(
                func=self._objective,
                dimensions=dimensions,
                n_calls=self.n_trials,
                n_random_starts=self.random_state,  # Use random_state from config
                random_state=self.random_state,
                n_jobs=self.n_jobs,
                verbose=True
            )

            # Store results
            self.optimization_result = result
            self.best_params = dict(zip([d.name for d in dimensions], result.x))
            self.best_score = -result.fun  # Convert back to maximization

            # Save results
            self._save_optimization_results()

        except Exception as e:
            _logger.error(f"Bayesian optimization failed: {e}")
            if self.notifier:
                self.notifier.send_message(f"Bayesian optimization failed: {e}")
            raise
