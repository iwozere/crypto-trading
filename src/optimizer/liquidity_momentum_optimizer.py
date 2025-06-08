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

import pandas as pd
from src.notification.logger import _logger
from src.optimizer.base_optimizer import BaseOptimizer
from src.strategy.liquidity_momentum_strategy import LiquidityMomentumStrategy
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
import matplotlib.gridspec as gridspec


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
        self.plot_size = config.get("plot_size", [15, 10])
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

        # Results settings
        self.report_metrics = config.get("report_metrics", [])
        self.save_trades = config.get("save_trades", True)
        self.trades_csv_path = config.get("trades_csv_path", None)
        self.save_metrics = config.get("save_metrics", True)
        self.metrics_format = config.get("metrics_format", "json")
        self.print_summary = config.get("print_summary", True)

    def plot_results(
        self, data_df: pd.DataFrame, trades_df: pd.DataFrame, params: dict, data_file_name: str
    ) -> str:
        """
        Plot optimization results with strategy-specific visualizations.
        Args:
            data_df: Price data DataFrame
            trades_df: Trades DataFrame
            params: Strategy parameters
            data_file_name: Name of the data file
        Returns:
            Path to the saved plot file
        """
        try:
            plt.style.use("dark_background")
            fig = plt.figure(figsize=self.plot_size)

            # Create subplots
            gs = gridspec.GridSpec(3, 1, height_ratios=[3, 1, 1])
            ax1 = plt.subplot(gs[0])
            ax2 = plt.subplot(gs[1], sharex=ax1)
            ax3 = plt.subplot(gs[2], sharex=ax1)

            # Plot price and trades
            ax1.plot(data_df.index, data_df["close"], label="Price", color="white", linewidth=2)
            if not trades_df.empty:
                ax1.scatter(
                    trades_df["entry_time"],
                    trades_df["entry_price"],
                    color="green",
                    marker="^",
                    s=200,
                    label="Buy",
                )
                ax1.scatter(
                    trades_df["exit_time"],
                    trades_df["exit_price"],
                    color="red",
                    marker="v",
                    s=200,
                    label="Sell",
                )

            # Calculate and plot liquidity ratio
            liquidity_ratio = data_df["volume"] / data_df["close"]
            ax2.plot(data_df.index, liquidity_ratio, label="Liquidity Ratio", color="cyan")

            # Plot momentum indicators
            momentum_periods = [5, 10, 20]  # Example periods
            for period in momentum_periods:
                returns = data_df["close"].pct_change(period)
                ax3.plot(
                    data_df.index, returns, label=f"{period}-period Returns", alpha=0.7
                )

            # Customize plots
            ax1.set_title(f"Liquidity Momentum Strategy - {data_file_name}")
            ax1.set_ylabel("Price")
            ax1.legend()
            ax1.grid(self.show_grid)

            ax2.set_ylabel("Liquidity Ratio")
            ax2.legend()
            ax2.grid(self.show_grid)

            ax3.set_ylabel("Returns")
            ax3.legend()
            ax3.grid(self.show_grid)

            # Format x-axis
            for ax in [ax1, ax2, ax3]:
                ax.xaxis.set_major_formatter(DateFormatter("%Y-%m-%d"))
                plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

            plt.tight_layout()

            # Save plot
            plot_path = os.path.join(
                self.results_dir,
                f"{self.get_result_filename(data_file_name)}_plot.{self.plot_format}",
            )
            plt.savefig(plot_path, dpi=self.plot_dpi)
            if self.show_plot:
                plt.show()
            plt.close()

            return plot_path

        except Exception as e:
            _logger.error(f"Error plotting results: {str(e)}")
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
