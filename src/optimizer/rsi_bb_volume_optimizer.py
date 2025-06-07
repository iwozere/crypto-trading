"""
RSI BB Volume Optimizer Module
-----------------------------

This module implements the optimizer for the RsiBollVolumeStrategy. It uses Bayesian optimization to tune parameters for mean-reversion strategies that combine RSI, Bollinger Bands, and Volume with position management. The optimizer supports backtesting, result plotting, and metrics reporting for robust parameter selection.

Main Features:
- Bayesian optimization of strategy parameters
- Backtesting and performance evaluation
- Result visualization and reporting
- Designed for use with RsiBollVolumeStrategy

Classes:
- RsiBBVolumeOptimizer: Optimizer for the RsiBollVolumeStrategy
"""
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from skopt.space import Real, Integer
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
from src.strategy.rsi_bb_volume_strategy import RsiBollVolumeStrategy
import matplotlib.gridspec as gridspec
import backtrader as bt
import pandas as pd
import numpy as np
from datetime import datetime
from src.optimizer.base_optimizer import BaseOptimizer
from typing import Any, Dict, Optional

class RsiBBVolumeOptimizer(BaseOptimizer):
    """
    Optimizer for the RsiBollVolumeStrategy.
    
    This optimizer uses Bayesian optimization to tune parameters for a mean-reversion strategy
    that combines RSI, Bollinger Bands, and Volume with position management. It is suitable for assets
    that exhibit mean-reverting behavior with volume spikes, such as certain crypto pairs or stocks.
    
    Use Case:
        - Markets with mean-reverting tendencies and volume-driven moves
        - Finds optimal parameters for maximizing profit and minimizing drawdown
    """
    def __init__(self, config: dict):
        """
        Initialize the optimizer with a configuration dictionary.
        Args:
            config: Dictionary containing all optimizer parameters.
        """
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
        self.results_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'results')
        self.strategy_name = 'RsiBollVolumeStrategy'
        self.strategy_class = RsiBollVolumeStrategy
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
    
    def plot_results(self, data: Any, trades_df: Any, params: Dict[str, Any], data_file: str) -> Optional[str]:
        """
        Plot the results of the strategy, including price, indicators, trades, and equity curve.
        Args:
            data: DataFrame with OHLCV data
            trades_df: DataFrame with trade records (must include 'entry_time', 'entry_price', 'exit_time', 'exit_price')
            params: Dictionary of strategy parameters
            data_file: Name of the data file (for plot title and saving)
        Returns:
            Path to the saved plot image, or None if plotting fails
        """
        plt.style.use('dark_background')
        fig = plt.figure(figsize=self.plot_size)
        
        # Create subplots
        gs = gridspec.GridSpec(4, 1, height_ratios=[3, 1, 1, 1])
        ax1 = plt.subplot(gs[0])
        ax2 = plt.subplot(gs[1], sharex=ax1)
        ax3 = plt.subplot(gs[2], sharex=ax1)
        ax4 = plt.subplot(gs[3], sharex=ax1)
        
        for ax in [ax1, ax2, ax3, ax4]:
            ax.grid(self.show_grid)
        
        # Calculate indicators using the same implementation as the strategy
        use_talib = params.get('use_talib', False)
        
        if use_talib:
            # TA-Lib indicators
            bb_high = bt.talib.BBANDS(
                data['close'],
                timeperiod=params['boll_period'],
                nbdevup=params['boll_devfactor'],
                nbdevdn=params['boll_devfactor']
            )[0]  # Upper band
            bb_mid = bt.talib.BBANDS(
                data['close'],
                timeperiod=params['boll_period'],
                nbdevup=params['boll_devfactor'],
                nbdevdn=params['boll_devfactor']
            )[1]  # Middle band
            bb_low = bt.talib.BBANDS(
                data['close'],
                timeperiod=params['boll_period'],
                nbdevup=params['boll_devfactor'],
                nbdevdn=params['boll_devfactor']
            )[2]  # Lower band
            rsi = bt.talib.RSI(data['close'], timeperiod=params['rsi_period'])
            vol_ma = bt.talib.SMA(data['volume'], timeperiod=params['vol_ma_period'])
        else:
            # Backtrader built-in indicators
            bb = bt.ind.BollingerBands(
                period=params['boll_period'],
                devfactor=params['boll_devfactor']
            )
            bb_high = bb.lines.top
            bb_mid = bb.lines.mid
            bb_low = bb.lines.bot
            rsi = bt.ind.RSI(period=params['rsi_period'])
            vol_ma = bt.ind.SMA(data['volume'], period=params['vol_ma_period'])
        
        # Plot price and Bollinger Bands
        ax1.plot(data.index, data['close'], label='Price', color='white', linewidth=2)
        ax1.plot(data.index, bb_high, label=f'BB High ({params["boll_period"]}, {params["boll_devfactor"]})', color='red', alpha=0.7, linewidth=1)
        ax1.plot(data.index, bb_mid, label=f'BB Mid ({params["boll_period"]})', color='yellow', alpha=0.7, linewidth=1)
        ax1.plot(data.index, bb_low, label=f'BB Low ({params["boll_period"]}, {params["boll_devfactor"]})', color='green', alpha=0.7, linewidth=1)
        
        # Plot trades
        if not trades_df.empty:
            # Plot entry (buy) points
            ax1.scatter(trades_df['entry_time'], trades_df['entry_price'], color='green', marker='^', s=200, label='Buy')
            # Plot exit (sell) points
            ax1.scatter(trades_df['exit_time'], trades_df['exit_price'], color='red', marker='v', s=200, label='Sell')
        
        # Plot RSI
        ax2.plot(data.index, rsi, label=f'RSI ({params["rsi_period"]})', color='cyan', linewidth=2)
        ax2.axhline(y=params['rsi_overbought'], color='red', linestyle='--', alpha=0.5)
        ax2.axhline(y=params['rsi_oversold'], color='green', linestyle='--', alpha=0.5)
        ax2.fill_between(data.index, params['rsi_overbought'], 100, color='red', alpha=0.1)
        ax2.fill_between(data.index, 0, params['rsi_oversold'], color='green', alpha=0.1)
        
        # Plot volume
        ax3.bar(data.index, data['volume'], label='Volume', color='blue', alpha=0.7)
        ax3.plot(data.index, vol_ma, label=f'Volume MA ({params["vol_ma_period"]})', color='yellow', linewidth=2)
        
        # Calculate and plot equity curve
        if not trades_df.empty:
            # Calculate cumulative returns
            returns = trades_df['pnl_comm'] / trades_df['entry_price']
            cumulative_returns = (1 + returns).cumprod()
            initial_equity = self.initial_capital
            equity_curve = initial_equity * cumulative_returns
            
            # Plot equity curve
            ax4.plot(trades_df['exit_time'], equity_curve, label='Equity Curve', color='green', linewidth=2)
            
            # Add drawdown visualization
            rolling_max = equity_curve.expanding().max()
            drawdown = (equity_curve - rolling_max) / rolling_max * 100
            ax4.fill_between(trades_df['exit_time'], drawdown, 0, color='red', alpha=0.3, label='Drawdown')
            
            # Add horizontal line at initial capital
            ax4.axhline(y=initial_equity, color='white', linestyle='--', alpha=0.5, label='Initial Capital')
        
        # Set titles and labels
        ax1.set_title(f'Trading Results - {data_file}', fontsize=20)
        ax1.set_ylabel('Price', fontsize=16)
        ax2.set_ylabel('RSI', fontsize=16)
        ax3.set_ylabel('Volume', fontsize=16)
        ax4.set_ylabel('Equity', fontsize=16)
        ax4.set_xlabel('Date', fontsize=16)
        
        # Set legend
        for ax in [ax1, ax2, ax3, ax4]:
            ax.legend(loc=self.legend_loc, fontsize=self.font_size)
        
        # Rotate x-axis labels
        plt.xticks(rotation=45)
        
        # Adjust layout
        plt.tight_layout()
        
        # Use base class helper for plot file name
        plot_path = os.path.join(self.results_dir, self.get_result_filename(data_file, suffix='_plot.'+self.plot_format, current_data=data))
        if self.save_plot:
            plt.savefig(plot_path, dpi=self.plot_dpi, bbox_inches='tight', format=self.plot_format)
        if self.show_plot:
            plt.show()
        plt.close()
        return plot_path

if __name__ == "__main__":
    import json
    with open("config/optimizer/rsi_bb_volume_optimizer.json") as f:
        config = json.load(f)
    optimizer = RsiBBVolumeOptimizer(config)
    optimizer.run_optimization()
