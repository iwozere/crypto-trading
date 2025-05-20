import os
import json
import pandas as pd
import numpy as np
from skopt import gp_minimize
from skopt.space import Real, Integer
from skopt.utils import use_named_args
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
from src.strats.rsi_bb_volume_strategy import RSIBollVolumeATRStrategy
import backtrader as bt
import matplotlib.gridspec as gridspec
from ta.volatility import BollingerBands
from ta.momentum import RSIIndicator
from datetime import datetime
from src.optimizer.base_optimizer import BaseOptimizer

class RsiBBVolumeOptimizer(BaseOptimizer):
    """
    Optimizer for the RSIBollVolumeATRStrategy.
    
    This optimizer uses Bayesian optimization to tune parameters for a mean-reversion strategy
    that combines RSI, Bollinger Bands, and Volume with ATR-based position management. It is suitable for assets
    that exhibit mean-reverting behavior with volume spikes, such as certain crypto pairs or stocks.
    
    Use Case:
        - Markets with mean-reverting tendencies and volume-driven moves
        - Finds optimal parameters for maximizing profit and minimizing drawdown
    """
    def __init__(self, initial_capital=1000.0, commission=0.001):
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
        self.results_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'results')
        self.strategy_name = 'RSIBollVolumeATRStrategy'
        self.strategy_class = RSIBollVolumeATRStrategy
        super().__init__(initial_capital, commission)
        os.makedirs(self.results_dir, exist_ok=True)
        
        # Set up plotting style
        plt.style.use('default')
        sns.set_theme(style="darkgrid")
        plt.rcParams['figure.figsize'] = (15, 10)
        plt.rcParams['font.size'] = 10
        
        # Define parameter space for optimization
        self.space = [
            Integer(7, 21, name='rsi_period'),
            Integer(15, 40, name='boll_period'),
            Real(1.5, 3.5, name='boll_devfactor'),
            Integer(10, 25, name='atr_period'),
            Integer(15, 40, name='vol_ma_period'),
            Real(1.5, 4.0, name='tp_atr_mult'),
            Real(0.8, 2.5, name='sl_atr_mult'),
            Real(25, 35, name='rsi_oversold'),
            Real(65, 75, name='rsi_overbought')
        ]
        warnings.filterwarnings('ignore', category=UserWarning, module='skopt')
    
    def plot_results(self, data, trades_df, params, data_file):
        """Plot the results of the optimization"""
        plt.style.use('dark_background')
        fig = plt.figure(figsize=(60, 30))
        
        # Create subplots
        gs = gridspec.GridSpec(4, 1, height_ratios=[3, 1, 1, 1])
        ax1 = plt.subplot(gs[0])
        ax2 = plt.subplot(gs[1], sharex=ax1)
        ax3 = plt.subplot(gs[2], sharex=ax1)
        ax4 = plt.subplot(gs[3], sharex=ax1)
        
        # Calculate Bollinger Bands
        bb = BollingerBands(close=data['close'], window=params['boll_period'], window_dev=params['boll_devfactor'])
        bb_high = bb.bollinger_hband()
        bb_mid = bb.bollinger_mavg()
        bb_low = bb.bollinger_lband()
        
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
        rsi = RSIIndicator(close=data['close'], window=params['rsi_period']).rsi()
        ax2.plot(data.index, rsi, label=f'RSI ({params["rsi_period"]})', color='cyan', linewidth=2)
        ax2.axhline(y=params['rsi_overbought'], color='red', linestyle='--', alpha=0.5)
        ax2.axhline(y=params['rsi_oversold'], color='green', linestyle='--', alpha=0.5)
        ax2.fill_between(data.index, params['rsi_overbought'], 100, color='red', alpha=0.1)
        ax2.fill_between(data.index, 0, params['rsi_oversold'], color='green', alpha=0.1)
        
        # Plot volume
        ax3.bar(data.index, data['volume'], label='Volume', color='blue', alpha=0.7)
        vol_ma = data['volume'].rolling(window=params['vol_ma_period']).mean()
        ax3.plot(data.index, vol_ma, label=f'Volume MA ({params["vol_ma_period"]})', color='yellow', linewidth=2)
        
        # Calculate and plot equity curve
        if not trades_df.empty:
            # Calculate cumulative returns
            trades_df['returns'] = trades_df['pnl'] / 100  # Convert percentage to decimal
            cumulative_returns = (1 + trades_df['returns']).cumprod()
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
        ax1.legend(loc='upper left', fontsize=12)
        ax2.legend(loc='upper left', fontsize=12)
        ax3.legend(loc='upper left', fontsize=12)
        ax4.legend(loc='upper left', fontsize=12)
        
        # Rotate x-axis labels
        plt.xticks(rotation=45)
        
        # Adjust layout
        plt.tight_layout()
        
        # Save plot
        plot_path = os.path.join(self.results_dir, f'{data_file}_plot.png')
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return plot_path

if __name__ == "__main__":
    optimizer = RsiBBVolumeOptimizer(initial_capital=1000.0, commission=0.001)
    optimizer.run_optimization()
