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
from src.strats.rsi_volume_supertrend_strategy import RsiVolumeSuperTrendStrategy
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
        plt.style.use('default')
        plt.rcParams['figure.figsize'] = self.plot_size
        plt.rcParams['font.size'] = 10
        # Read search space from config and convert to skopt space objects
        self.space = self._build_skopt_space_from_config(config.get('search_space', []))
        warnings.filterwarnings('ignore', category=UserWarning, module='skopt')
        warnings.filterwarnings('ignore', category=RuntimeWarning)
    
    def _build_skopt_space_from_config(self, search_space_config):
        from skopt.space import Real, Integer, Categorical
        skopt_space = []
        for param in search_space_config:
            if param['type'] == 'Integer':
                skopt_space.append(Integer(param['low'], param['high'], name=param['name']))
            elif param['type'] == 'Real':
                skopt_space.append(Real(param['low'], param['high'], name=param['name']))
            elif param['type'] == 'Categorical':
                skopt_space.append(Categorical(param['categories'], name=param['name']))
        return skopt_space

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
        ax2.axhline(y=params['rsi_exit_short_level'], color='red', linestyle='--', alpha=0.5, label=f'RSI Short Exit ({params["rsi_exit_short_level"]})')
        ax2.axhline(y=params['rsi_entry_short_level'], color='lightcoral', linestyle=':', alpha=0.5, label=f'RSI Short Entry ({params["rsi_entry_short_level"]})')
        
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
        
        ax1.set_title(f'Trading Results - {data_file} - Params: {params}', fontsize=16)
        ax1.set_ylabel('Price', fontsize=12); ax2.set_ylabel('RSI', fontsize=12)
        ax3.set_ylabel('Volume', fontsize=12); ax4.set_ylabel('Equity', fontsize=12)
        ax4.set_xlabel('Date', fontsize=12)
        for ax in [ax1, ax2, ax3, ax4]: ax.legend(loc='upper left', fontsize=10)
        plt.xticks(rotation=45); plt.tight_layout()
        plot_path = os.path.join(self.results_dir, self.get_result_filename(data_file, suffix='_plot.png', current_data=data))
        plt.savefig(plot_path, dpi=300, bbox_inches='tight'); plt.close()
        return plot_path

if __name__ == "__main__":
    import json
    with open("optimizer_config.json") as f:
        config = json.load(f)
    optimizer = RsiVolumeSuperTrendOptimizer(config)
    optimizer.run_optimization()
