"""
Ichimoku RSI ATR Volume Optimizer Module
---------------------------------------

This module implements the optimizer for the IchimokuRSIATRVolumeStrategy. It uses Bayesian optimization to tune parameters for strategies that combine Ichimoku Cloud, RSI, ATR, and Volume. The optimizer supports backtesting, result plotting, and metrics reporting for robust parameter selection.

Main Features:
- Bayesian optimization of strategy parameters
- Backtesting and performance evaluation
- Result visualization and reporting
- Designed for use with IchimokuRSIATRVolumeStrategy

Classes:
- IchimokuRSIATRVolumeOptimizer: Optimizer for the IchimokuRSIATRVolumeStrategy
"""
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from skopt.space import Real, Integer
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
from src.strats.ichimoku_rsi_atr_volume_strategy import IchimokuRSIATRVolumeStrategy
import matplotlib.gridspec as gridspec
from ta.momentum import RSIIndicator
from ta.volatility import AverageTrueRange
from src.optimizer.base_optimizer import BaseOptimizer
import backtrader as bt
import pandas as pd
from typing import Any, Dict, Optional

class IchimokuRSIATRVolumeOptimizer(BaseOptimizer):
    """
    Optimizer for the IchimokuRSIATRVolumeStrategy.
    Uses Bayesian optimization to tune Ichimoku, RSI, ATR, and volume parameters.
    """
    def __init__(self, initial_capital: float = 1000.0, commission: float = 0.001) -> None:
        """
        Initialize the optimizer with initial capital and commission.
        Args:
            initial_capital: Starting capital for backtests
            commission: Commission rate per trade
        """
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
        self.results_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'results')
        self.strategy_name = 'IchimokuRSIATRVolumeStrategy'
        self.strategy_class = IchimokuRSIATRVolumeStrategy
        super().__init__(initial_capital, commission)
        os.makedirs(self.results_dir, exist_ok=True)
        plt.style.use('default')
        sns.set_theme(style="darkgrid")
        plt.rcParams['figure.figsize'] = (15, 10)
        plt.rcParams['font.size'] = 10
        self.space = [
            Integer(7, 30, name='rsi_period'),
            Real(20.0, 40.0, name='rsi_oversold'),
            Real(60.0, 80.0, name='rsi_overbought'),
            Integer(7, 30, name='atr_period'),
            Real(1.0, 3.0, name='tp_atr_mult'),
            Real(0.5, 2.0, name='sl_atr_mult'),
            Integer(5, 30, name='ichimoku_tenkan'),
            Integer(20, 60, name='ichimoku_kijun'),
            Integer(40, 120, name='ichimoku_senkou'),
            Integer(0, 1, name='check_rsi_slope')
        ]
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
        fig = plt.figure(figsize=(60, 30))
        gs = gridspec.GridSpec(5, 1, height_ratios=[3, 1, 1, 1, 1])
        ax1 = plt.subplot(gs[0])
        ax2 = plt.subplot(gs[1], sharex=ax1)
        ax3 = plt.subplot(gs[2], sharex=ax1)
        ax4 = plt.subplot(gs[3], sharex=ax1)
        ax5 = plt.subplot(gs[4], sharex=ax1)

        # Price and Ichimoku Cloud
        ax1.plot(data_df.index, data_df['close'], label='Price', color='white', linewidth=2)
        # Ichimoku lines
        # For plotting, recalc Ichimoku lines manually for pandas
        def ichimoku_lines(df, tenkan, kijun, senkou):
            high = df['high']
            low = df['low']
            tenkan_sen = (high.rolling(tenkan).max() + low.rolling(tenkan).min()) / 2
            kijun_sen = (high.rolling(kijun).max() + low.rolling(kijun).min()) / 2
            senkou_span_a = ((tenkan_sen + kijun_sen) / 2).shift(kijun)
            senkou_span_b = ((high.rolling(senkou).max() + low.rolling(senkou).min()) / 2).shift(kijun)
            chikou_span = df['close'].shift(-kijun)
            return tenkan_sen, kijun_sen, senkou_span_a, senkou_span_b, chikou_span
        tenkan_sen, kijun_sen, senkou_a, senkou_b, chikou = ichimoku_lines(data_df, params['ichimoku_tenkan'], params['ichimoku_kijun'], params['ichimoku_senkou'])
        ax1.plot(data_df.index, tenkan_sen, label='Tenkan-sen', color='orange', linewidth=1.5)
        ax1.plot(data_df.index, kijun_sen, label='Kijun-sen', color='blue', linewidth=1.5)
        ax1.plot(data_df.index, senkou_a, label='Senkou Span A', color='green', linewidth=1.2, alpha=0.7)
        ax1.plot(data_df.index, senkou_b, label='Senkou Span B', color='red', linewidth=1.2, alpha=0.7)
        ax1.fill_between(data_df.index, senkou_a, senkou_b, where=senkou_a>=senkou_b, color='green', alpha=0.15)
        ax1.fill_between(data_df.index, senkou_a, senkou_b, where=senkou_a<senkou_b, color='red', alpha=0.15)
        ax1.plot(data_df.index, chikou, label='Chikou Span', color='magenta', linewidth=1, alpha=0.5)

        # Plot trades
        if not trades_df.empty:
            long_trades = trades_df[trades_df['type'] == 'long']
            short_trades = trades_df[trades_df['type'] == 'short']
            if not long_trades.empty:
                ax1.scatter(long_trades['entry_time'], long_trades['entry_price'], color='lime', marker='^', s=200, label='Long Entry', zorder=5)
                ax1.scatter(long_trades['exit_time'], long_trades['exit_price'], color='red', marker='v', s=200, label='Long Exit', zorder=5)
            if not short_trades.empty:
                ax1.scatter(short_trades['entry_time'], short_trades['entry_price'], color='fuchsia', marker='v', s=200, label='Short Entry', zorder=5)
                ax1.scatter(short_trades['exit_time'], short_trades['exit_price'], color='aqua', marker='^', s=200, label='Short Exit', zorder=5)

        # RSI
        rsi = RSIIndicator(close=data_df['close'], window=params['rsi_period']).rsi()
        ax2.plot(data_df.index, rsi, label=f'RSI ({params["rsi_period"]})', color='cyan', linewidth=2)
        ax2.axhline(y=params['rsi_oversold'], color='yellow', linestyle='--', alpha=0.7, label=f'RSI Oversold ({params["rsi_oversold"]})')
        ax2.axhline(y=params['rsi_overbought'], color='red', linestyle='--', alpha=0.7, label=f'RSI Overbought ({params["rsi_overbought"]})')
        ax2.set_ylabel('RSI', fontsize=12)
        ax2.legend(loc='upper left', fontsize=10)

        # ATR (for trailing stop)
        atr = AverageTrueRange(high=data_df['high'], low=data_df['low'], close=data_df['close'], window=params['atr_period']).average_true_range()
        ax3.plot(data_df.index, atr, label=f'ATR ({params["atr_period"]})', color='orange', linewidth=1.5)
        ax3.set_ylabel('ATR', fontsize=12)
        ax3.legend(loc='upper left', fontsize=10)

        # Volume
        ax4.bar(data_df.index, data_df['volume'], label='Volume', color='blue', alpha=0.7)
        vol_ma = data_df['volume'].rolling(window=params['ichimoku_senkou']).mean()
        ax4.plot(data_df.index, vol_ma, label=f'Volume MA ({params["ichimoku_senkou"]})', color='yellow', linewidth=2)
        ax4.set_ylabel('Volume', fontsize=12)
        ax4.legend(loc='upper left', fontsize=10)

        # Equity Curve
        if not trades_df.empty:
            trades_df = trades_df.sort_values(by='exit_time').copy()
            trades_df['returns'] = trades_df['pnl'] / 100
            initial_equity = self.initial_capital
            equity_curve = initial_equity * (1 + trades_df['returns']).cumprod()
            ax5.plot(trades_df['exit_time'], equity_curve, label='Equity Curve', color='green', linewidth=2)
            rolling_max = equity_curve.expanding().max()
            drawdown = (equity_curve - rolling_max) / rolling_max * 100
            ax5.fill_between(trades_df['exit_time'], drawdown, 0, color='red', alpha=0.3, label='Drawdown')
            ax5.axhline(y=initial_equity, color='white', linestyle='--', alpha=0.5, label='Initial Capital')
        ax5.set_ylabel('Equity', fontsize=12)
        ax5.set_xlabel('Date', fontsize=12)
        ax5.legend(loc='upper left', fontsize=10)

        # Titles and layout
        ax1.set_title(f'Trading Results - {data_file_name}', fontsize=20)
        for ax in [ax1, ax2, ax3, ax4, ax5]:
            ax.grid(True, linestyle=':', alpha=0.5)
        ax1.legend(loc='upper left', fontsize=12)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plot_path = os.path.join(self.results_dir, f'{data_file_name}_plot.png')
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        plt.close()
        return plot_path

if __name__ == "__main__":
    optimizer = IchimokuRSIATRVolumeOptimizer(initial_capital=1000.0, commission=0.001)
    optimizer.run_optimization() 