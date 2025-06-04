"""
RSI Volume SuperTrend Optimizer Module
-------------------------------------

This module implements the optimizer for the RsiVolumeSuperTrendStrategy. It uses Bayesian optimization to tune strategy parameters for trend-following systems that combine SuperTrend, RSI, and Volume. The optimizer supports backtesting, result plotting, and metrics reporting for robust parameter selection.

Main Features:
- Bayesian optimization of strategy parameters
- Backtesting and performance evaluation
- Result visualization and reporting
- Designed for use with RsiVolumeSuperTrendStrategy

Classes:
- RsiVolumeSuperTrendOptimizer: Optimizer for the RsiVolumeSuperTrendStrategy
"""
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from skopt.space import Real, Integer
import matplotlib.pyplot as plt
import warnings
from src.strategy.rsi_volume_supertrend_strategy import RsiVolumeSuperTrendStrategy
import matplotlib.gridspec as gridspec
from ta.momentum import RSIIndicator
from src.optimizer.base_optimizer import BaseOptimizer
from typing import Any, Dict, Optional
import datetime

class RsiVolumeSuperTrendOptimizer(BaseOptimizer):
    """
    Optimizer for the RsiVolumeSuperTrendStrategy.
    """
    def __init__(self, config: dict):
        """
        Initialize the optimizer with a configuration dictionary.
        Args:
            config: Dictionary containing all optimizer parameters.
        """
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
        self.results_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'results')
        self.strategy_name = 'RsiVolumeSuperTrendStrategy'
        self.strategy_class = RsiVolumeSuperTrendStrategy
        super().__init__(config)
        os.makedirs(self.results_dir, exist_ok=True)
        self.plot_size = config.get('plot_size', [15, 10])
        plt.style.use('dark_background')
        self.plot_style = config.get('plot_style', 'default')
        self.font_size = config.get('font_size', 10)
        self.plot_dpi = config.get('plot_dpi', 300)
        self.show_grid = config.get('show_grid', True)
        self.legend_loc = config.get('legend_loc', 'upper left')
        self.save_plot = config.get('save_plot', True)
        self.show_plot = config.get('show_plot', False)
        self.plot_format = config.get('plot_format', 'png')
        self.show_equity_curve = config.get('show_equity_curve', True)
        self.show_indicators = config.get('show_indicators', True)
        self.color_scheme = config.get('color_scheme', {})
        self.report_metrics = config.get('report_metrics', [])
        self.save_trades = config.get('save_trades', True)
        self.trades_csv_path = config.get('trades_csv_path', None)
        self.save_metrics = config.get('save_metrics', True)
        self.metrics_format = config.get('metrics_format', 'json')
        self.print_summary = config.get('print_summary', True)
        self.report_params = config.get('report_params', True)
        self.report_filename_pattern = config.get('report_filename_pattern', None)
        self.include_plots_in_report = config.get('include_plots_in_report', True)
        plt.rcParams['figure.figsize'] = self.plot_size
        plt.rcParams['font.size'] = self.font_size
        # Read search space from config and convert to skopt space objects
        self.space = super()._build_skopt_space_from_config(config.get('search_space', []))
        warnings.filterwarnings('ignore', category=UserWarning, module='skopt')
        warnings.filterwarnings('ignore', category=RuntimeWarning)
    
    def plot_results(self, data: Any, trades_df: Any, params: Dict[str, Any], data_file: str) -> Optional[str]:
        """
        Plot the results of the strategy, including price, indicators, trades, and equity curve.
        Args:
            data: DataFrame with OHLCV data
            trades_df: DataFrame with trade records (must include 'type', 'entry_time', 'entry_price', 'exit_time', 'exit_price')
            params: Dictionary of strategy parameters
            data_file: Name of the data file (for plot title and saving)
        Returns:
            Path to the saved plot image, or None if plotting fails
        """
        plt.style.use('dark_background')
        fig = plt.figure(figsize=self.plot_size)
        gs = gridspec.GridSpec(4, 1, height_ratios=[3, 1, 1, 1])
        ax1 = plt.subplot(gs[0])
        ax2 = plt.subplot(gs[1], sharex=ax1)
        ax3 = plt.subplot(gs[2], sharex=ax1)
        ax4 = plt.subplot(gs[3], sharex=ax1)
        for ax in [ax1, ax2, ax3, ax4]:
            ax.grid(self.show_grid)
        
        ax1.plot(data.index, data['close'], label='Price', color='white', linewidth=2)
        
        # Plot SuperTrend using the helper method
        st_period = params.get('st_period', 10)
        st_multiplier = params.get('st_multiplier', 3.0)
        supertrend_plot_values = self._calculate_supertrend_for_plot(data, st_period, st_multiplier)
        ax1.plot(data.index, supertrend_plot_values, label=f'SuperTrend ({st_period},{st_multiplier})', color='orange', linestyle='--', alpha=0.8)
        
        if not trades_df.empty:
            long_trades = trades_df[trades_df['type'] == 'long']
            short_trades = trades_df[trades_df['type'] == 'short']
            if not long_trades.empty:
                ax1.scatter(long_trades['entry_time'], long_trades['entry_price'], color='lime', marker='^', s=200, label='Long Entry', zorder=5)
                ax1.scatter(long_trades['exit_time'], long_trades['exit_price'], color='red', marker='v', s=200, label='Long Exit', zorder=5)
            if not short_trades.empty:
                ax1.scatter(short_trades['entry_time'], short_trades['entry_price'], color='fuchsia', marker='v', s=200, label='Short Entry', zorder=5)
                ax1.scatter(short_trades['exit_time'], short_trades['exit_price'], color='aqua', marker='^', s=200, label='Short Exit', zorder=5)
        
        rsi_period = params.get('rsi_period', 14)
        rsi = RSIIndicator(close=data['close'], window=rsi_period).rsi()
        ax2.plot(data.index, rsi, label=f'RSI ({rsi_period})', color='cyan', linewidth=2)
        ax2.axhline(y=params['rsi_exit_long_level'], color='lime', linestyle='--', alpha=0.5, label=f'RSI Long Exit ({params["rsi_exit_long_level"]})')
        ax2.axhline(y=params['rsi_entry_long_level'], color='lightgreen', linestyle=':', alpha=0.5, label=f'RSI Long Entry ({params["rsi_entry_long_level"]})')
        
        vol_ma_period = params.get('vol_ma_period', 10)
        ax3.bar(data.index, data['volume'], label='Volume', color='blue', alpha=0.7)
        vol_ma = data['volume'].rolling(window=vol_ma_period).mean()
        ax3.plot(data.index, vol_ma, label=f'Volume MA ({vol_ma_period})', color='yellow', linewidth=2)
        
        if not trades_df.empty:
            trades_df['returns'] = trades_df['pnl'] / 100
            cumulative_returns = (1 + trades_df['returns']).cumprod()
            initial_equity = self.initial_capital
            equity_curve = initial_equity * cumulative_returns
            ax4.plot(trades_df['exit_time'], equity_curve, label='Equity Curve', color='green', linewidth=2)
            rolling_max = equity_curve.expanding().max()
            drawdown_pct = (equity_curve - rolling_max) / rolling_max * 100 # Percentage drawdown
            ax4.fill_between(trades_df['exit_time'], equity_curve, equity_curve + (drawdown_pct/100 * equity_curve) , color='red', alpha=0.3, label='Drawdown From Peak Equity')
            ax4.axhline(y=initial_equity, color='white', linestyle='--', alpha=0.5, label='Initial Capital')
        
        ax1.set_title(f'Trading Results - {data_file} - Params: {params}', fontsize=self.font_size)
        ax1.set_ylabel('Price', fontsize=self.font_size); ax2.set_ylabel('RSI', fontsize=self.font_size)
        ax3.set_ylabel('Volume', fontsize=self.font_size); ax4.set_ylabel('Equity', fontsize=self.font_size)
        ax4.set_xlabel('Date', fontsize=self.font_size)
        for ax in [ax1, ax2, ax3, ax4]:
            ax.legend(loc=self.legend_loc, fontsize=self.font_size)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plot_path = os.path.join(self.results_dir, self.get_result_filename(data_file, suffix='_plot.'+self.plot_format, current_data=data))
        if self.save_plot:
            plt.savefig(plot_path, dpi=self.plot_dpi, bbox_inches='tight', format=self.plot_format)
        if self.show_plot:
            plt.show()
        plt.close()
        return plot_path

if __name__ == "__main__":
    import json
    with open("config/optimizer/rsi_volume_supertrend_optimizer.json") as f:
        config = json.load(f)
    optimizer = RsiVolumeSuperTrendOptimizer(config)
    optimizer.run_optimization()
