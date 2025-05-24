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

class IchimokuRSIATRVolumeOptimizer(BaseOptimizer):
    """
    Optimizer for the IchimokuRSIATRVolumeStrategy.
    Uses Bayesian optimization to tune Ichimoku, RSI, ATR, and volume parameters.
    """
    def __init__(self, initial_capital=1000.0, commission=0.001):
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
        self.results_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'results')
        self.strategy_name = 'IchimokuRSIATRVolumeStrategy'
        self.strategy_class = IchimokuRSIATRVolumeStrategy
        super().__init__(initial_capital, commission)
        os.makedirs(self.results_dir, exist_ok=True)
        self.space = [
            Integer(7, 15, name='tenkan_period'),
            Integer(20, 35, name='kijun_period'),
            Integer(40, 65, name='senkou_span_b_period'),
            Integer(7, 21, name='rsi_period'),
            Real(40, 60, name='rsi_entry'),
            Integer(7, 21, name='atr_period'),
            Real(1.0, 4.0, name='atr_mult'),
            Integer(10, 40, name='vol_ma_period'),
        ]
        warnings.filterwarnings('ignore', category=UserWarning, module='skopt')

    def plot_results(self, data, trades_df, params, data_file):
        plt.style.use('dark_background')
        fig = plt.figure(figsize=(60, 30))
        gs = gridspec.GridSpec(5, 1, height_ratios=[3, 1, 1, 1, 1])
        ax1 = plt.subplot(gs[0])
        ax2 = plt.subplot(gs[1], sharex=ax1)
        ax3 = plt.subplot(gs[2], sharex=ax1)
        ax4 = plt.subplot(gs[3], sharex=ax1)
        ax5 = plt.subplot(gs[4], sharex=ax1)

        # Price and Ichimoku Cloud
        ax1.plot(data.index, data['close'], label='Price', color='white', linewidth=2)
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
        tenkan_sen, kijun_sen, senkou_a, senkou_b, chikou = ichimoku_lines(data, params['tenkan_period'], params['kijun_period'], params['senkou_span_b_period'])
        ax1.plot(data.index, tenkan_sen, label='Tenkan-sen', color='orange', linewidth=1.5)
        ax1.plot(data.index, kijun_sen, label='Kijun-sen', color='blue', linewidth=1.5)
        ax1.plot(data.index, senkou_a, label='Senkou Span A', color='green', linewidth=1.2, alpha=0.7)
        ax1.plot(data.index, senkou_b, label='Senkou Span B', color='red', linewidth=1.2, alpha=0.7)
        ax1.fill_between(data.index, senkou_a, senkou_b, where=senkou_a>=senkou_b, color='green', alpha=0.15)
        ax1.fill_between(data.index, senkou_a, senkou_b, where=senkou_a<senkou_b, color='red', alpha=0.15)
        ax1.plot(data.index, chikou, label='Chikou Span', color='magenta', linewidth=1, alpha=0.5)

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
        rsi = RSIIndicator(close=data['close'], window=params['rsi_period']).rsi()
        ax2.plot(data.index, rsi, label=f'RSI ({params["rsi_period"]})', color='cyan', linewidth=2)
        ax2.axhline(y=params['rsi_entry'], color='yellow', linestyle='--', alpha=0.7, label=f'RSI Entry ({params["rsi_entry"]})')
        ax2.set_ylabel('RSI', fontsize=12)
        ax2.legend(loc='upper left', fontsize=10)

        # ATR (for trailing stop)
        atr = AverageTrueRange(high=data['high'], low=data['low'], close=data['close'], window=params['atr_period']).average_true_range()
        ax3.plot(data.index, atr, label=f'ATR ({params["atr_period"]})', color='orange', linewidth=1.5)
        ax3.set_ylabel('ATR', fontsize=12)
        ax3.legend(loc='upper left', fontsize=10)

        # Volume
        ax4.bar(data.index, data['volume'], label='Volume', color='blue', alpha=0.7)
        vol_ma = data['volume'].rolling(window=params['vol_ma_period']).mean()
        ax4.plot(data.index, vol_ma, label=f'Volume MA ({params["vol_ma_period"]})', color='yellow', linewidth=2)
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
        ax1.set_title(f'Trading Results - {data_file}', fontsize=20)
        for ax in [ax1, ax2, ax3, ax4, ax5]:
            ax.grid(True, linestyle=':', alpha=0.5)
        ax1.legend(loc='upper left', fontsize=12)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plot_path = os.path.join(self.results_dir, f'{data_file}_plot.png')
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        plt.close()
        return plot_path

if __name__ == "__main__":
    optimizer = IchimokuRSIATRVolumeOptimizer(initial_capital=1000.0, commission=0.001)
    optimizer.run_optimization() 