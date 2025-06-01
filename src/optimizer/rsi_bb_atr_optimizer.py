"""
RSI BB ATR Optimizer Module
--------------------------

This module implements the optimizer for the MeanReversionRSBBATRStrategy. It uses Bayesian optimization to tune parameters for mean-reversion strategies that combine Bollinger Bands, RSI, and ATR. The optimizer supports backtesting, result plotting, and metrics reporting for robust parameter selection.

Main Features:
- Bayesian optimization of strategy parameters
- Backtesting and performance evaluation
- Result visualization and reporting
- Designed for use with MeanReversionRSBBATRStrategy

Classes:
- MeanReversionRSBBATROptimizer: Optimizer for the MeanReversionRSBBATRStrategy
"""
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import pandas as pd
from skopt.space import Real, Integer
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
from src.strats.rsi_bb_atr_strategy import MeanReversionRSBBATRStrategy
import matplotlib.gridspec as gridspec
from ta.volatility import BollingerBands
from ta.momentum import RSIIndicator
from src.optimizer.base_optimizer import BaseOptimizer
from typing import Any, Dict, Optional
import datetime
import json

class MeanReversionRSBBATROptimizer(BaseOptimizer):
    """
    Optimizer for the MeanReversionRSBBATRStrategy.
    
    This optimizer uses Bayesian optimization (skopt) to tune parameters for a mean-reversion strategy
    that combines Bollinger Bands, RSI, and ATR. It is designed for ranging or sideways markets (e.g., forex pairs, altcoins)
    and works on timeframes from 5m to 4H. The optimizer seeks to maximize net profit while penalizing high drawdown and low Sharpe ratio.
    
    Use Case:
        - Ranging/sideways markets
        - Finds optimal parameters for the strategy to maximize risk-adjusted returns
    """
    def __init__(self, config: dict):
        """
        Initialize the optimizer with a configuration dictionary.
        Args:
            config: Dictionary containing all optimizer parameters.
        """
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
        self.results_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'results')
        self.strategy_name = 'MeanReversionRSBBATRStrategy'
        self.strategy_class = MeanReversionRSBBATRStrategy
        super().__init__(config)
        os.makedirs(self.results_dir, exist_ok=True)
        
        self.plot_size = config.get('plot_size', [15, 10])
        plt.style.use('dark_background')
        sns.set_theme(style="darkgrid")
        plt.rcParams['figure.figsize'] = self.plot_size
        plt.rcParams['font.size'] = 10
        
        # Read search space from config and convert to skopt space objects
        self.space = super()._build_skopt_space_from_config(config.get('search_space', []))
        
        warnings.filterwarnings('ignore', category=UserWarning, module='skopt')
        warnings.filterwarnings('ignore', category=RuntimeWarning)
    
    def plot_results(self, data_df: Any, trades_df: Any, params: Dict[str, Any], data_file_name: str) -> Optional[str]:
        """
        Plot the results of the strategy, including price, indicators, trades, and equity curve.
        Args:
            data_df: DataFrame with OHLCV data
            trades_df: DataFrame with trade records (must include 'direction', 'entry_time', 'entry_price', 'exit_time', 'exit_price')
            params: Dictionary of strategy parameters
            data_file_name: Name of the data file (for plot title and saving)
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

        # Price and Bollinger Bands
        ax1.plot(data_df.index, data_df['close'], label='Price', color='white', linewidth=2)
        bb_period = params.get('bb_period', 20)
        bb_devfactor = params.get('bb_devfactor', 2.0)
        bb_indicator = BollingerBands(close=data_df['close'], window=bb_period, window_dev=bb_devfactor, fillna=False)
        ax1.plot(data_df.index, bb_indicator.bollinger_hband(), label=f'BB Top ({bb_period},{bb_devfactor})', color='cyan', linestyle='--', alpha=0.7, linewidth=1)
        ax1.plot(data_df.index, bb_indicator.bollinger_lband(), label=f'BB Low ({bb_period},{bb_devfactor})', color='cyan', linestyle='--', alpha=0.7, linewidth=1)
        ax1.plot(data_df.index, bb_indicator.bollinger_mavg(), label=f'BB Mid ({bb_period})', color='blue', linestyle=':', alpha=0.6, linewidth=1)
        ax1.fill_between(data_df.index, bb_indicator.bollinger_lband(), bb_indicator.bollinger_hband(), color='cyan', alpha=0.1)

        # Plot only long trades
        if not trades_df.empty:
            trades_df_plot = trades_df.copy()
            if 'entry_time' in trades_df_plot.columns: trades_df_plot['entry_time'] = pd.to_datetime(trades_df_plot['entry_time'])
            if 'exit_time' in trades_df_plot.columns: trades_df_plot['exit_time'] = pd.to_datetime(trades_df_plot['exit_time'])
            long_trades = trades_df_plot[trades_df_plot['direction'] == 'long']
            if not long_trades.empty:
                ax1.scatter(long_trades['entry_time'], long_trades['entry_price'], color='lime', marker='^', s=200, label='Long Entry', zorder=5)
                valid_exits = long_trades.dropna(subset=['exit_time', 'exit_price'])
                if not valid_exits.empty:
                    ax1.scatter(valid_exits['exit_time'], valid_exits['exit_price'], color='red', marker='v', s=200, label='Long Exit', zorder=5)
        ax1.set_ylabel('Price / BB', fontsize=12)

        # RSI
        rsi_period = params.get('rsi_period', 14)
        rsi_oversold = params.get('rsi_oversold', 30)
        rsi_overbought = params.get('rsi_overbought', 70)
        rsi_mid_level = params.get('rsi_mid_level', 50)
        rsi_indicator = RSIIndicator(close=data_df['close'], window=rsi_period, fillna=False).rsi()
        ax2.plot(data_df.index, rsi_indicator, label=f'RSI ({rsi_period})', color='cyan', linewidth=2)
        ax2.axhline(y=rsi_overbought, color='red', linestyle='--', alpha=0.7, label=f'Overbought ({rsi_overbought})')
        ax2.axhline(y=rsi_mid_level, color='gray', linestyle=':', alpha=0.7, label=f'Mid Level ({rsi_mid_level})')
        ax2.axhline(y=rsi_oversold, color='green', linestyle='--', alpha=0.7, label=f'Oversold ({rsi_oversold})')
        ax2.set_ylabel('RSI', fontsize=12)
        ax2.set_ylim(0, 100)

        # Volume
        vol_ma_period = 10
        ax3.bar(data_df.index, data_df['volume'], label='Volume', color='blue', alpha=0.7)
        vol_ma = data_df['volume'].rolling(window=vol_ma_period).mean()
        ax3.plot(data_df.index, vol_ma, label=f'Volume MA ({vol_ma_period})', color='yellow', linewidth=2)
        ax3.set_ylabel('Volume', fontsize=12)

        # Equity Curve
        if not trades_df.empty and 'pnl_comm' in trades_df.columns and 'exit_time' in trades_df.columns:
            trades_df_sorted = trades_df_plot.dropna(subset=['exit_time']).sort_values(by='exit_time').copy()
            if not trades_df_sorted.empty:
                trades_df_sorted['cumulative_pnl'] = trades_df_sorted['pnl_comm'].cumsum()
                equity_curve = self.initial_capital + trades_df_sorted['cumulative_pnl']
                ax4.plot(trades_df_sorted['exit_time'], equity_curve, label='Equity Curve', color='green', linewidth=2)
                rolling_max_equity = equity_curve.expanding().max()
                ax4.fill_between(trades_df_sorted['exit_time'], equity_curve, rolling_max_equity, where=equity_curve < rolling_max_equity, color='red', alpha=0.3, label='Drawdown')
        ax4.axhline(y=self.initial_capital, color='white', linestyle='--', alpha=0.7, label='Initial Capital')
        ax4.set_ylabel('Equity', fontsize=12)
        ax4.set_xlabel('Date', fontsize=12)

        # Titles and legends
        ax1.set_title(f'Trading Results - {data_file_name} - Params: {params}', fontsize=16)
        for ax in [ax1, ax2, ax3, ax4]: ax.legend(loc='upper left', fontsize=10)
        plt.xticks(rotation=45); plt.tight_layout()
        plot_path = os.path.join(self.results_dir, self.get_result_filename(data_file_name, suffix='_plot.png', current_data=data_df))
        plt.savefig(plot_path, dpi=300, bbox_inches='tight'); plt.close()
        return plot_path

if __name__ == "__main__":
    with open("config/optimizer/rsi_bb_atr_optimizer.json") as f:
        config = json.load(f)
    optimizer = MeanReversionRSBBATROptimizer(config)
    optimizer.run_optimization()
