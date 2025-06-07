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


class BaseOptimizer:
    """
    Base class for all optimizers.
    Provides common functionality for parameter optimization, backtesting, and result visualization.
    """

    def __init__(self, config: dict):
        """
        Initialize the optimizer with a configuration dictionary.
        Args:
            config: Dictionary containing all optimizer parameters.
        """
        self.data_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data"
        )
        self.results_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "results"
        )
        self.strategy_name = config.get("strategy_name", "")
        self.strategy_class = config.get("strategy_class", None)
        self.initial_capital = config.get("initial_capital", 10000.0)
        self.commission = config.get("commission", 0.001)
        self.plot_size = config.get("plot_size", [15, 10])
        plt.style.use("dark_background")
        self.plot_style = config.get("plot_style", "default")
        self.font_size = config.get("font_size", 10)
        self.plot_dpi = config.get("plot_dpi", 300)
        self.show_grid = config.get("show_grid", True)
        self.legend_loc = config.get("legend_loc", "upper left")
        self.save_plot = config.get("save_plot", True)
        self.show_plot = config.get("show_plot", False)
        self.plot_format = config.get("plot_format", "png")
        self.show_equity_curve = config.get("show_equity_curve", True)
        self.show_indicators = config.get("show_indicators", True)
        self.color_scheme = config.get("color_scheme", {})
        self.report_metrics = config.get("report_metrics", [])
        self.save_trades = config.get("save_trades", True)
        self.trades_csv_path = config.get("trades_csv_path", None)
        self.save_metrics = config.get("save_metrics", True)
        self.metrics_format = config.get("metrics_format", "json")
        self.print_summary = config.get("print_summary", True)
        self.report_params = config.get("report_params", True)
        self.report_filename_pattern = config.get("report_filename_pattern", None)
        self.include_plots_in_report = config.get("include_plots_in_report", True)
        warnings.filterwarnings("ignore", category=UserWarning, module="skopt")
        warnings.filterwarnings("ignore", category=RuntimeWarning)
        self.config = config  # Store config for later use
        self.initial_capital = config.get("initial_capital", 1000.0)
        self.notify = config.get("notify", False)
        self.risk_free_rate = config.get("risk_free_rate", 0.0)
        self.omega_threshold = config.get("omega_threshold", 0.0)
        self.current_metrics = {}
        self.current_data = None
        self.current_symbol = None
        self.raw_data = {}
        self.best_metrics = float("-inf")
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
        start_date: Union[str, datetime],
        end_date: Union[str, datetime],
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
        log_dir = os.path.join("logs", "log")
        os.makedirs(log_dir, exist_ok=True)

        if level == "error":
            _logger.error(message)
        elif level == "warning":
            _logger.warning(message)
        else:
            _logger.info(message)

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
        - param_types: dict of {param_name: type}, e.g. {'rsi_period': int, ...}
        If not provided, will use int for names containing 'period', else float.
        """
        if not hasattr(self, "space"):
            raise AttributeError(
                "Optimizer must have a 'space' attribute with parameter names."
            )
        param_names = [p.name for p in self.space]
        param_dict = dict(zip(param_names, params))
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
        import datetime

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

    def save_results(self, study: optuna.Study, data_file: str) -> None:
        """
        Save optimization results to a JSON file.
        Args:
            study: Optuna study object containing optimization results
            data_file: Name of the data file used for optimization
        """
        try:
            # Get best trial
            best_trial = study.best_trial

            # Get exit logic configuration
            exit_logic_config = self.config.get("exit_logic", {})
            exit_logic_name = exit_logic_config.get("name", "atr_exit")
            exit_params_config = exit_logic_config.get("params", {})

            # Separate strategy, exit logic, and other parameters
            strategy_params = {}
            exit_params = {}
            other_params = {}

            for param_name, param_value in best_trial.params.items():
                if param_name in exit_params_config:
                    exit_params[param_name] = param_value
                elif param_name == "notify":
                    other_params[param_name] = param_value
                else:
                    strategy_params[param_name] = param_value

            # Create results dictionary
            results_dict = {
                "version": "1.0.0",
                "timestamp": datetime.now().isoformat(),
                "data_file": data_file,
                "best_params": {
                    "strategy": {
                        "strategy_name": self.strategy_name,
                        **strategy_params,
                    },
                    "exit_logic": {"exit_logic_name": exit_logic_name, **exit_params},
                    **other_params,
                },
                "best_value": best_trial.value,
                "optimization_time": self.optimization_time,
                "n_trials": len(study.trials),
                "optimization_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }

            # Save to file
            result_file = os.path.join(
                self.results_dir, self.get_result_filename(data_file)
            )
            with open(result_file, "w") as f:
                json.dump(results_dict, f, indent=4)

            self.log_message(f"Results saved to {result_file}")

        except Exception as e:
            self.log_message(f"Error saving results: {str(e)}", level="ERROR")

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
        exit_logic_name = exit_logic_config.get("name", "atr_exit")
        exit_params_config = exit_logic_config.get("params", {})

        def objective(trial):
            # --- Suggest strategy parameters (add as needed) ---
            strategy_params = {}
            # Suggest all strategy params that are not exit logic params
            for pname, pinfo in self.param_ranges.items():
                if pname == "exit_logic_name" or pname in EXIT_PARAM_MAP:
                    continue
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

            # --- Exit logic parameters ---
            exit_params = {}
            for param, pinfo in exit_params_config.items():
                if pinfo["type"] == "Real":
                    exit_params[param] = trial.suggest_float(
                        param, pinfo["low"], pinfo["high"]
                    )
                elif pinfo["type"] == "Integer":
                    exit_params[param] = trial.suggest_int(
                        param, pinfo["low"], pinfo["high"]
                    )
                elif pinfo["type"] == "Categorical":
                    exit_params[param] = trial.suggest_categorical(
                        param, pinfo["categories"]
                    )

            strategy_params["exit_logic_name"] = exit_logic_name
            strategy_params["exit_params"] = exit_params

            # --- Run backtest ---
            results = self.run_backtest(self.current_data.copy(), strategy_params)
            net_profit = (
                results.get("trades", {})
                .get("pnl", {})
                .get("net", {})
                .get("total", 0.0)
                if results
                else 0.0
            )
            return -net_profit

        return objective

    def optimize_single_file(self, data_file):
        """
        Generalized optimization routine for a single data file.
        Subclasses must set self.strategy_name and implement self.plot_results.
        """
        self.log_message(
            f"\nOptimizing {data_file} for {getattr(self, 'strategy_name', 'UnknownStrategy')}...",
            level="info",
        )
        self.current_symbol = data_file.split("_")[0]
        if data_file not in self.raw_data:
            self.log_message(f"Error: No data for {data_file}.", level="error")
            return None
        self.current_data = self.raw_data[data_file].copy()
        if len(self.current_data) < 100:
            self.log_message(
                f"Warning: Insufficient data points in {data_file}. Skipping...",
                level="info",
            )
            return None
        if self.current_data.isnull().any().any():
            self.log_message(
                f"Warning: Found missing values in {data_file}. Cleaning data...",
                level="info",
            )
            self.current_data = self.current_data.fillna(method="ffill").fillna(
                method="bfill"
            )
        self.current_metrics = {}
        try:
            # Get optimization method from config
            opt_method = self.config.get(
                "optimization_method", "skopt"
            )  # Default to skopt for backward compatibility
            n_trials = self.config.get("n_trials", 100)
            n_random_starts = self.config.get("n_random_starts", 42)
            if opt_method == "skopt":
                noise = self.config.get("noise", 0.01)
                n_jobs = self.config.get("n_jobs", -1)
                verbose = self.config.get("verbose", False)
                result = self.optimize_with_skopt(
                    n_trials=n_trials,
                    n_random_starts=n_random_starts,
                    noise=noise,
                    n_jobs=n_jobs,
                    verbose=verbose,
                )
                best_params = self.params_to_dict(result.x)
                best_score = result.fun
            elif opt_method == "optuna":
                study = optuna.create_study(direction="minimize")
                study.optimize(self.get_optuna_objective(), n_trials=n_trials)
                best_params = study.best_params
                best_score = study.best_value
                result = study
            else:
                raise ValueError(f"Unknown optimization method: {opt_method}")
            self.log_message(f"\nOptimization completed for {data_file}", level="info")
            self.log_message(
                f"Best params for {data_file}: {best_params}", level="info"
            )
            self.log_message(
                f"Best score: {best_score:.2f}. Metrics: {self.current_metrics}",
                level="info",
            )
            final_backtest_run = self.run_backtest(
                self.current_data.copy(), best_params
            )
            trades_df = pd.DataFrame()
            if final_backtest_run and hasattr(
                final_backtest_run.get("strategy", None), "trades"
            ):
                trades_list = final_backtest_run["strategy"].trades
                if trades_list:
                    trades_df = pd.DataFrame(trades_list)
                    # Calculate metrics from trades
                    self.current_metrics = self.calculate_metrics(trades_df)
                    # Add trade-specific metrics
                    self.current_metrics["total_trades"] = len(trades_list)
                    winning_trades = [
                        t for t in trades_list if t.get("pnl_comm", 0) > 0
                    ]
                    self.current_metrics["win_rate"] = (
                        len(winning_trades) / len(trades_list) * 100
                        if trades_list
                        else 0
                    )
                    losing_trades_sum = sum(
                        t.get("pnl_comm", 0)
                        for t in trades_list
                        if t.get("pnl_comm", 0) <= 0
                    )
                    if losing_trades_sum == 0:
                        self.current_metrics["profit_factor"] = (
                            float("inf") if winning_trades else 0
                        )
                    else:
                        self.current_metrics["profit_factor"] = abs(
                            sum(t.get("pnl_comm", 0) for t in winning_trades)
                            / losing_trades_sum
                        )
                    self.current_metrics["net_profit"] = sum(
                        t.get("pnl_comm", 0) for t in trades_list
                    )
                    self.current_metrics["portfolio_growth_pct"] = (
                        (self.current_metrics["net_profit"] / self.initial_capital)
                        * 100
                        if self.initial_capital > 0
                        else 0
                    )
                    self.current_metrics["final_value"] = (
                        self.initial_capital + self.current_metrics["net_profit"]
                    )
            plot_path = None
            if hasattr(self, "plot_results") and callable(self.plot_results):
                plot_path = self.plot_results(
                    self.current_data.copy(), trades_df, best_params, data_file
                )
            return self.save_results(study=result, data_file=data_file)
        except Exception as e:
            self.log_message(
                f"Error during optimization for {data_file}: {str(e)}", level="error"
            )
            self.log_message(traceback.format_exc(), level="error")
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
                    all_results.append(result)
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
            "timestamp": datetime.now().isoformat(),
            "optimizer_class": self.__class__.__name__,
            "strategy_name": getattr(self, "strategy_name", "UnknownStrategy"),
            "results": all_results,
        }
        combined_path = os.path.join(
            self.results_dir,
            f'combined_optimization_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json',
        )
        try:
            with open(combined_path, "w") as f:
                json.dump(
                    combined_results, f, indent=4, cls=BaseOptimizer.DateTimeEncoder
                )
            self.log_message(
                f"\nCombined results saved to {combined_path}", level="info"
            )
        except Exception as e:
            self.log_message(f"Error saving combined JSON: {e}", level="error")

    def run_backtest(self, data, params):
        """
        Generic Backtrader backtest runner. Uses self.strategy_class for the strategy.
        Subclasses can override customize_cerebro(self, cerebro) for custom analyzers or broker setup.
        """
        cerebro = bt.Cerebro()
        if not isinstance(data.index, pd.DatetimeIndex):
            self.log_message("Error: Data for backtest must have a DatetimeIndex.")
            return None
        expected_cols = ["open", "high", "low", "close", "volume"]
        if not all(col in data.columns for col in expected_cols):
            self.log_message(
                f"Error: Data missing one of required columns: {expected_cols}"
            )
            return None

        data_feed = bt.feeds.PandasData(
            dataname=data,
            datetime=None,
            open="open",
            high="high",
            low="low",
            close="close",
            volume="volume",
            openinterest=-1,
        )
        cerebro.adddata(data_feed)
        cerebro.broker.setcash(self.initial_capital)
        cerebro.broker.setcommission(commission=self.commission)
        cerebro.broker.set_checksubmit(False)

        params["notify"] = self.notify
        # Extract ticker from data file name if not already present
        if "ticker" not in params and hasattr(self, "current_data_file"):
            params["ticker"] = self.current_data_file.split("_")[0]
        cerebro.addstrategy(self.strategy_class, params=params)

        # Only add essential analyzers for optimization
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")

        # Allow subclass customization
        if hasattr(self, "customize_cerebro") and callable(self.customize_cerebro):
            self.customize_cerebro(cerebro)

        try:
            results = cerebro.run()
            if not results:
                self.log_message(
                    f"Backtest with params {params} did not yield valid results object."
                )
                return None
            strategy = results[0]
            drawdown = strategy.analyzers.drawdown.get_analysis()
            trades = strategy.analyzers.trades.get_analysis()
            return {"strategy": strategy, "drawdown": drawdown, "trades": trades}
        except Exception as e:
            self.log_message(f"Error during backtest run for params {params}: {str(e)}")
            self.log_message(traceback.format_exc(), level="error")
            return None

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
        Objective function for optimization. Runs backtest and returns negative net profit.
        """
        param_dict = self.params_to_dict(params)
        param_key = str(param_dict)  # Use string representation as cache key

        # Check cache first
        if param_key in self.metrics_cache:
            return -self.metrics_cache[param_key]["net_profit"]

        backtest_results = self.run_backtest(self.current_data, param_dict)
        if backtest_results is None:
            return float("inf")

        trades = backtest_results["strategy"].get_trades()
        if not trades:
            return float("inf")

        trades_df = pd.DataFrame(trades)

        # Calculate only essential metrics for optimization
        metrics = {
            "net_profit": trades_df["pnl_comm"].sum(),
            "total_trades": len(trades_df),
            "win_rate": (
                len(trades_df[trades_df["pnl_comm"] > 0]) / len(trades_df) * 100
                if len(trades_df) > 0
                else 0
            ),
            "max_drawdown": backtest_results["drawdown"]
            .get("max", {})
            .get("drawdown", 0),
        }

        # Cache the results
        self.metrics_cache[param_key] = metrics

        # Only save results if they're better than previous best
        if metrics["net_profit"] > self.best_metrics:
            self.best_metrics = metrics["net_profit"]
            # Calculate additional metrics only for saving results
            full_metrics = self.calculate_metrics(trades_df)
            self.save_results(
                study=self.optimization_result, data_file=self.current_data_file
            )

        return -metrics["net_profit"]

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
