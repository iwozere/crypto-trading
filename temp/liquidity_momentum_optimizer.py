"""
Liquidity Momentum Optimizer
---------------------------
Optimizer for the LiquidityMomentumStrategy that combines liquidity ratio and momentum indicators.
Uses the same optimization framework as other strategies but with specific parameter handling.
"""

import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import json
import traceback
from typing import Optional

import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import pandas as pd
import talib
from matplotlib.dates import DateFormatter
from src.notification.logger import _logger
from src.optimizer.base_optimizer import BaseOptimizer
from src.strategy.liquidity_momentum_strategy import LiquidityMomentumStrategy


class LiquidityMomentumOptimizer(BaseOptimizer):
    def __init__(self, config: dict):
        """
        Initialize the LiquidityMomentumOptimizer.
        Args:
            config: Dictionary containing all optimizer parameters.
        """
        self.data_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data"
        )
        self.results_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "results"
        )
        self.strategy_name = "LiquidityMomentumStrategy"
        self.strategy_class = LiquidityMomentumStrategy
        super().__init__(config)

        # Create results directory if it doesn't exist
        os.makedirs(self.results_dir, exist_ok=True)

        # Set up search space from config
        self.space = self._build_skopt_space_from_config(config.get("search_space", []))

        # Set default parameters
        self.default_params = config.get("default_params", {})

        # Plot settings
        self.plot_size = self.visualization_settings.get("plot_size", [15, 10])
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

        # Results settings
        self.report_metrics = config.get("report_metrics", [])
        self.save_trades = config.get("save_trades", True)
        self.trades_csv_path = config.get("trades_csv_path", None)
        self.save_metrics = config.get("save_metrics", True)
        self.metrics_format = config.get("metrics_format", "json")
        self.print_summary = config.get("print_summary", True)

    def plot_results(
        self,
        data_df: pd.DataFrame,
        trades_df: pd.DataFrame,
        params: dict,
        data_file_name: str,
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
                # Calculate liquidity ratio
                typical_price = (
                    data_df["high"] + data_df["low"] + data_df["close"]
                ) / 3
                liquidity_ratio = talib.SMA(
                    (data_df["volume"] * typical_price).values,
                    timeperiod=params["liquidity_period"],
                )

                # Calculate momentum indicators
                momentum_5 = talib.ROC(data_df["close"].values, timeperiod=5)
                momentum_10 = talib.ROC(data_df["close"].values, timeperiod=10)
                momentum_20 = talib.ROC(data_df["close"].values, timeperiod=20)

                # Calculate volume MA
                vol_ma = talib.SMA(
                    data_df["volume"].values, timeperiod=params["vol_ma_period"]
                )
            else:
                # Pandas calculations
                # Calculate liquidity ratio
                typical_price = (
                    data_df["high"] + data_df["low"] + data_df["close"]
                ) / 3
                liquidity_ratio = (
                    (data_df["volume"] * typical_price)
                    .rolling(window=params["liquidity_period"])
                    .mean()
                )

                # Calculate momentum indicators
                momentum_5 = data_df["close"].pct_change(periods=5) * 100
                momentum_10 = data_df["close"].pct_change(periods=10) * 100
                momentum_20 = data_df["close"].pct_change(periods=20) * 100

                # Calculate volume MA
                vol_ma = (
                    data_df["volume"].rolling(window=params["vol_ma_period"]).mean()
                )

            # Plot price
            ax1.plot(
                data_df.index,
                data_df["close"],
                label="Price",
                color="white",
                linewidth=2,
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

            # Plot liquidity ratio
            ax2.plot(
                data_df.index,
                liquidity_ratio,
                label=f'Liquidity Ratio ({params["liquidity_period"]})',
                color="cyan",
                linewidth=2,
            )
            ax2.axhline(
                y=params["liquidity_threshold"],
                color="red",
                linestyle="--",
                alpha=0.5,
                label="Threshold",
            )

            # Plot momentum indicators
            ax3.plot(
                data_df.index,
                momentum_5,
                label="Momentum (5)",
                color="yellow",
                linewidth=1,
            )
            ax3.plot(
                data_df.index,
                momentum_10,
                label="Momentum (10)",
                color="orange",
                linewidth=1,
            )
            ax3.plot(
                data_df.index,
                momentum_20,
                label="Momentum (20)",
                color="red",
                linewidth=1,
            )
            ax3.axhline(y=0, color="white", linestyle="--", alpha=0.5)

            # Plot volume
            ax4.bar(
                data_df.index,
                data_df["volume"],
                label="Volume",
                color="blue",
                alpha=0.7,
            )
            ax4.plot(
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
            ax2.set_ylabel("Liquidity Ratio", fontsize=16)
            ax3.set_ylabel("Momentum", fontsize=16)
            ax4.set_ylabel("Volume", fontsize=16)
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

    def NOT_USED_score_objective(self, metrics: dict) -> float:
        """
        Custom scoring function for the liquidity momentum strategy.
        Combines multiple metrics to evaluate strategy performance.
        Args:
            metrics: Dictionary of strategy metrics
        Returns:
            Score to minimize (negative for maximization)
        """
        # Extract key metrics
        sharpe = metrics.get("sharpe_ratio", 0)
        sortino = metrics.get("sortino_ratio", 0)
        calmar = metrics.get("calmar_ratio", 0)
        win_rate = metrics.get("win_rate", 0)
        profit_factor = metrics.get("profit_factor", 0)
        max_drawdown = metrics.get("max_drawdown_pct", 0)
        total_trades = metrics.get("total_trades", 0)

        # Penalize if not enough trades
        if total_trades < 10:
            return 1000.0

        # Calculate composite score
        # Higher weights for risk-adjusted returns and win rate
        score = (
            -0.3 * sharpe  # Risk-adjusted return
            + -0.2 * sortino  # Downside risk-adjusted return
            + -0.2 * calmar  # Drawdown-adjusted return
            + -0.15 * (win_rate / 100)  # Win rate (normalized)
            + -0.1 * profit_factor  # Profit factor
            + 0.05 * (max_drawdown / 100)  # Drawdown penalty (normalized)
        )

        return score


if __name__ == "__main__":
    import json

    with open("config/optimizer/liquidity_momentum_optimizer.json") as f:
        config = json.load(f)
    optimizer = LiquidityMomentumOptimizer(config)
    optimizer.run_optimization()
