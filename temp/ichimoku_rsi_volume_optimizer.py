"""
Ichimoku RSI ATR Volume Optimizer Module
---------------------------------------

This module implements the optimizer for the IchimokuRsiVolumeStrategy. It uses Bayesian optimization to tune parameters for strategies that combine Ichimoku Cloud, RSI, and Volume. The optimizer supports backtesting, result plotting, and metrics reporting for robust parameter selection.

Main Features:
- Bayesian optimization of strategy parameters
- Backtesting and performance evaluation
- Result visualization and reporting
- Designed for use with IchimokuRsiVolumeStrategy

Classes:
- IchimokuRSIATRVolumeOptimizer: Optimizer for the IchimokuRsiVolumeStrategy
"""

import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import datetime
import json
import traceback
import warnings
from typing import Any, Dict, Optional

import backtrader as bt
import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import talib
from skopt.space import Integer, Real
from src.optimizer.base_optimizer import BaseOptimizer
from src.strategy.ichimoku_rsi_volume_strategy import IchimokuRsiVolumeStrategy


class IchimokuRsiVolumeOptimizer(BaseOptimizer):
    """
    Optimizer for the IchimokuRsiVolumeStrategy.
    Uses Bayesian optimization to tune Ichimoku, RSI, ATR, and volume parameters.
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
        self.strategy_name = "IchimokuRsiVolumeStrategy"
        self.strategy_class = IchimokuRsiVolumeStrategy
        super().__init__(config)
        os.makedirs(self.results_dir, exist_ok=True)
        self.plot_size = self.visualization_settings.get("plot_size", [15, 10])
        plt.style.use("dark_background")
        self.plot_style = self.visualization_settings.get("plot_style", "default")
        self.font_size = self.visualization_settings.get("font_size", 10)
        self.plot_dpi = self.visualization_settings.get("plot_dpi", 300)
        self.show_grid = self.visualization_settings.get("show_grid", True)
        self.legend_loc = self.visualization_settings.get("legend_loc", "upper left")
        self.save_plot = self.visualization_settings.get("save_plot", True)
        self.show_plot = self.visualization_settings.get("show_plot", False)
        self.plot_format = self.visualization_settings.get("plot_format", "png")
        self.show_equity_curve = self.visualization_settings.get(
            "show_equity_curve", True
        )
        self.show_indicators = self.visualization_settings.get("show_indicators", True)
        self.color_scheme = self.visualization_settings.get("color_scheme", {})
        self.report_metrics = self.visualization_settings.get("report_metrics", [])
        self.save_trades = self.visualization_settings.get("save_trades", True)
        self.trades_csv_path = self.visualization_settings.get("trades_csv_path", None)
        self.save_metrics = self.visualization_settings.get("save_metrics", True)
        self.metrics_format = self.visualization_settings.get("metrics_format", "json")
        self.print_summary = self.visualization_settings.get("print_summary", True)
        self.report_params = self.visualization_settings.get("report_params", True)
        self.report_filename_pattern = self.visualization_settings.get(
            "report_filename_pattern", None
        )
        self.include_plots_in_report = self.visualization_settings.get(
            "include_plots_in_report", True
        )
        plt.rcParams["figure.figsize"] = self.plot_size
        plt.rcParams["font.size"] = self.font_size
        # Read search space from config and convert to skopt space objects
        self.space = super()._build_skopt_space_from_config(
            config.get("search_space", [])
        )
        warnings.filterwarnings("ignore", category=UserWarning, module="skopt")
        warnings.filterwarnings("ignore", category=RuntimeWarning)

    def plot_results(
        self, data_df: Any, trades_df: Any, params: Dict[str, Any], data_file_name: str
    ) -> Optional[str]:
        """
        Plot the results of the strategy, including price, indicators, trades, and equity curve.
        Args:
            data_df: DataFrame with OHLCV data
            trades_df: DataFrame with trade records (must include 'entry_time', 'entry_price', 'exit_time', 'exit_price')
            params: Dictionary of strategy parameters
            data_file_name: Name of the data file (for plot title and saving)
        Returns:
            Path to the saved plot image, or None if plotting fails
        """
        try:
            plt.style.use("dark_background")
            fig = plt.figure(figsize=self.plot_size)

            # Create subplots
            gs = gridspec.GridSpec(4, 1, height_ratios=[3, 1, 1, 1])
            ax1 = plt.subplot(gs[0])
            ax2 = plt.subplot(gs[1], sharex=ax1)
            ax3 = plt.subplot(gs[2], sharex=ax1)
            ax4 = plt.subplot(gs[3], sharex=ax1)

            for ax in [ax1, ax2, ax3, ax4]:
                ax.grid(self.show_grid)

            # Calculate indicators using pandas/TA-Lib
            use_talib = params.get("use_talib", False)

            if use_talib:
                # TA-Lib indicators
                # RSI
                rsi = talib.RSI(
                    data_df["close"].values, timeperiod=params["rsi_period"]
                )

                # Volume MA
                vol_ma = talib.SMA(
                    data_df["volume"].values, timeperiod=params["vol_ma_period"]
                )
            else:
                # Pandas calculations
                # RSI
                delta = data_df["close"].diff()
                gain = (
                    (delta.where(delta > 0, 0))
                    .rolling(window=params["rsi_period"])
                    .mean()
                )
                loss = (
                    (-delta.where(delta < 0, 0))
                    .rolling(window=params["rsi_period"])
                    .mean()
                )
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs))

                # Volume MA
                vol_ma = (
                    data_df["volume"].rolling(window=params["vol_ma_period"]).mean()
                )

            # Calculate Ichimoku Cloud components
            # Conversion Line (Tenkan-sen)
            period9_high = data_df["high"].rolling(window=9).max()
            period9_low = data_df["low"].rolling(window=9).min()
            tenkan_sen = (period9_high + period9_low) / 2

            # Base Line (Kijun-sen)
            period26_high = data_df["high"].rolling(window=26).max()
            period26_low = data_df["low"].rolling(window=26).min()
            kijun_sen = (period26_high + period26_low) / 2

            # Leading Span A (Senkou Span A)
            senkou_span_a = ((tenkan_sen + kijun_sen) / 2).shift(26)

            # Leading Span B (Senkou Span B)
            period52_high = data_df["high"].rolling(window=52).max()
            period52_low = data_df["low"].rolling(window=52).min()
            senkou_span_b = ((period52_high + period52_low) / 2).shift(26)

            # Plot price and Ichimoku Cloud
            ax1.plot(
                data_df.index,
                data_df["close"],
                label="Price",
                color="white",
                linewidth=2,
            )
            ax1.plot(
                data_df.index,
                tenkan_sen,
                label="Tenkan-sen (9)",
                color="yellow",
                alpha=0.7,
            )
            ax1.plot(
                data_df.index, kijun_sen, label="Kijun-sen (26)", color="red", alpha=0.7
            )
            ax1.plot(
                data_df.index,
                senkou_span_a,
                label="Senkou Span A",
                color="green",
                alpha=0.7,
            )
            ax1.plot(
                data_df.index,
                senkou_span_b,
                label="Senkou Span B",
                color="red",
                alpha=0.7,
            )

            # Fill the cloud
            ax1.fill_between(
                data_df.index,
                senkou_span_a,
                senkou_span_b,
                where=senkou_span_a >= senkou_span_b,
                color="green",
                alpha=0.3,
            )
            ax1.fill_between(
                data_df.index,
                senkou_span_a,
                senkou_span_b,
                where=senkou_span_a < senkou_span_b,
                color="red",
                alpha=0.3,
            )

            # Plot trades
            if not trades_df.empty:
                # Plot entry (buy) points
                ax1.scatter(
                    trades_df["entry_time"],
                    trades_df["entry_price"],
                    color="green",
                    marker="^",
                    s=200,
                    label="Buy",
                )
                # Plot exit (sell) points
                ax1.scatter(
                    trades_df["exit_time"],
                    trades_df["exit_price"],
                    color="red",
                    marker="v",
                    s=200,
                    label="Sell",
                )

            # Plot RSI
            ax2.plot(
                data_df.index,
                rsi,
                label=f'RSI ({params["rsi_period"]})',
                color="cyan",
                linewidth=2,
            )
            ax2.axhline(
                y=params["rsi_overbought"], color="red", linestyle="--", alpha=0.5
            )
            ax2.axhline(
                y=params["rsi_oversold"], color="green", linestyle="--", alpha=0.5
            )
            ax2.fill_between(
                data_df.index, params["rsi_overbought"], 100, color="red", alpha=0.1
            )
            ax2.fill_between(
                data_df.index, 0, params["rsi_oversold"], color="green", alpha=0.1
            )

            # Plot volume
            ax3.bar(
                data_df.index,
                data_df["volume"],
                label="Volume",
                color="blue",
                alpha=0.7,
            )
            ax3.plot(
                data_df.index,
                vol_ma,
                label=f'Volume MA ({params["vol_ma_period"]})',
                color="yellow",
                linewidth=2,
            )

            # Calculate and plot equity curve
            if not trades_df.empty:
                # Calculate cumulative returns
                returns = trades_df["pnl_comm"] / trades_df["entry_price"]
                cumulative_returns = (1 + returns).cumprod()
                initial_equity = self.initial_capital
                equity_curve = initial_equity * cumulative_returns

                # Plot equity curve
                ax4.plot(
                    trades_df["exit_time"],
                    equity_curve,
                    label="Equity Curve",
                    color="green",
                    linewidth=2,
                )

                # Add drawdown visualization
                rolling_max = equity_curve.expanding().max()
                drawdown = (equity_curve - rolling_max) / rolling_max * 100
                ax4.fill_between(
                    trades_df["exit_time"],
                    drawdown,
                    0,
                    color="red",
                    alpha=0.3,
                    label="Drawdown",
                )

                # Add horizontal line at initial capital
                ax4.axhline(
                    y=initial_equity,
                    color="white",
                    linestyle="--",
                    alpha=0.5,
                    label="Initial Capital",
                )

            # Set titles and labels
            ax1.set_title(f"Trading Results - {data_file_name}", fontsize=20)
            ax1.set_ylabel("Price", fontsize=16)
            ax2.set_ylabel("RSI", fontsize=16)
            ax3.set_ylabel("Volume", fontsize=16)
            ax4.set_ylabel("Equity", fontsize=16)
            ax4.set_xlabel("Date", fontsize=16)

            # Set legend
            for ax in [ax1, ax2, ax3, ax4]:
                ax.legend(loc=self.legend_loc, fontsize=self.font_size)

            # Rotate x-axis labels
            plt.xticks(rotation=45)

            # Adjust layout
            plt.tight_layout()

            # Use base class helper for plot file name
            plot_path = os.path.join(
                self.results_dir,
                self.get_result_filename(
                    data_file_name, suffix="_plot." + self.plot_format
                ),
            )
            if self.save_plot:
                plt.savefig(
                    plot_path,
                    dpi=self.plot_dpi,
                    bbox_inches="tight",
                    format=self.plot_format,
                )
            if self.show_plot:
                plt.show()
            plt.close()
            return plot_path
        except Exception as e:
            self.log_message(f"Error plotting results: {str(e)}", level="error")
            self.log_message(traceback.format_exc(), level="error")
            return None


if __name__ == "__main__":
    import json

    with open("config/optimizer/ichimoku_rsi_volume_optimizer.json") as f:
        config = json.load(f)
    optimizer = IchimokuRsiVolumeOptimizer(config)
    optimizer.run_optimization()
