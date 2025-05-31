"""
BB Volume SuperTrend Optimizer Module
------------------------------------

This module implements the optimizer for the BBSuperTrendVolumeBreakoutStrategy. It uses Bayesian optimization to tune parameters for breakout strategies that combine Bollinger Bands, SuperTrend, and Volume. The optimizer supports backtesting, result plotting, and metrics reporting for robust parameter selection.

Main Features:
- Bayesian optimization of strategy parameters
- Backtesting and performance evaluation
- Result visualization and reporting
- Designed for use with BBSuperTrendVolumeBreakoutStrategy

Classes:
- BBSuperTrendVolumeBreakoutOptimizer: Optimizer for the BBSuperTrendVolumeBreakoutStrategy
"""
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import json
import pandas as pd
from skopt.space import Real, Integer
import matplotlib.pyplot as plt
import warnings
from src.strats.bb_volume_supertrend_strategy import BBSuperTrendVolumeBreakoutStrategy
import matplotlib.gridspec as gridspec
from ta.volatility import BollingerBands
from src.optimizer.base_optimizer import BaseOptimizer
from typing import Any, Dict, Optional
import datetime

class BBSuperTrendVolumeBreakoutOptimizer(BaseOptimizer):
    """
    Optimizer for the BBSuperTrendVolumeBreakoutStrategy.
    
    This optimizer uses Bayesian optimization to tune parameters for a breakout strategy that combines
    Bollinger Bands, SuperTrend, and Volume. It is designed for volatile breakout markets (crypto, small-cap stocks)
    and seeks to maximize net profit while controlling drawdown and risk.
    
    Use Case:
        - Volatile breakout markets
        - Finds optimal parameters for capturing large moves early while filtering out fakeouts
    """
    def __init__(self, config: dict):
        """
        Initialize the optimizer with a configuration dictionary.
        Args:
            config: Dictionary containing all optimizer parameters.
        """
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
        self.results_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'results')
        self.strategy_name = 'BBSuperTrendVolumeBreakoutStrategy'
        self.strategy_class = BBSuperTrendVolumeBreakoutStrategy
        super().__init__(config)
        os.makedirs(self.results_dir, exist_ok=True)
        # Read search space from config and convert to skopt space objects
        self.space = self._build_skopt_space_from_config(config.get('search_space', []))
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

    def plot_results(self, data_df: pd.DataFrame, trades_df: pd.DataFrame, params: Dict[str, Any], data_file_name: str) -> Optional[str]:
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
        print(trades_df)
        
        fig = plt.figure(figsize=self.plot_size)
        gs = gridspec.GridSpec(3, 1, height_ratios=[3, 1, 1]) 
        ax1 = plt.subplot(gs[0])
        ax2 = plt.subplot(gs[1], sharex=ax1)
        ax3 = plt.subplot(gs[2], sharex=ax1)
        
        ax1.plot(data_df.index, data_df['close'], label='Price', color='lightgray', linewidth=1.5)
        
        bb_period = params.get('bb_period', 20)
        bb_devfactor = params.get('bb_devfactor', 2.0)
        bb_indicator = BollingerBands(close=data_df['close'], window=bb_period, window_dev=bb_devfactor, fillna=False)
        ax1.plot(data_df.index, bb_indicator.bollinger_hband(), label=f'BB Top ({bb_period},{bb_devfactor})', color='cyan', linestyle='--', alpha=0.7, linewidth=1)
        ax1.plot(data_df.index, bb_indicator.bollinger_lband(), label=f'BB Low ({bb_period},{bb_devfactor})', color='cyan', linestyle='--', alpha=0.7, linewidth=1)
        ax1.plot(data_df.index, bb_indicator.bollinger_mavg(), label=f'BB Mid ({bb_period})', color='blue', linestyle=':', alpha=0.6, linewidth=1)
        ax1.fill_between(data_df.index, bb_indicator.bollinger_lband(), bb_indicator.bollinger_hband(), color='cyan', alpha=0.1)

        st_period = params.get('st_period', 10)
        st_multiplier = params.get('st_multiplier', 3.0)
        supertrend_plot_values = self._calculate_supertrend_for_plot(data_df, st_period, st_multiplier)
        ax1.plot(data_df.index, supertrend_plot_values, label=f'SuperTrend ({st_period},{st_multiplier})', color='orange', linestyle='-', linewidth=1.5, alpha=0.9)
        
        if not trades_df.empty:
            long_trades = trades_df[trades_df['direction'] == 'long']
            short_trades = trades_df[trades_df['direction'] == 'short']
            if not long_trades.empty:
                ax1.scatter(long_trades['entry_time'], long_trades['entry_price'], color='lime', marker='^', s=100, label='Long Entry', zorder=5, edgecolors='black')
                ax1.scatter(long_trades['exit_time'], long_trades['exit_price'], color='red', marker='v', s=100, label='Long Exit', zorder=5, edgecolors='black')
            if not short_trades.empty:
                ax1.scatter(short_trades['entry_time'], short_trades['entry_price'], color='fuchsia', marker='v', s=100, label='Short Entry', zorder=5, edgecolors='black')
                ax1.scatter(short_trades['exit_time'], short_trades['exit_price'], color='aqua', marker='^', s=100, label='Short Exit', zorder=5, edgecolors='black')
        
        vol_ma_period = params.get('vol_ma_period', 20)
        ax2.bar(data_df.index, data_df['volume'], label='Volume', color='lightblue', alpha=0.7)
        vol_ma = data_df['volume'].rolling(window=vol_ma_period).mean()
        ax2.plot(data_df.index, vol_ma, label=f'Volume MA ({vol_ma_period})', color='yellow', linewidth=1.5)
        
        if not trades_df.empty and 'pnl_comm' in trades_df.columns:
            trades_df_sorted = trades_df.sort_values(by='exit_time').copy()
            trades_df_sorted['cumulative_pnl'] = trades_df_sorted['pnl_comm'].cumsum()
            equity_curve = self.initial_capital + trades_df_sorted['cumulative_pnl']
            ax3.plot(trades_df_sorted['exit_time'], equity_curve, label='Equity Curve (PnL based)', color='lightgreen', linewidth=2)
            
            rolling_max_equity = equity_curve.expanding().max()
            drawdown_values = equity_curve - rolling_max_equity
            ax3.fill_between(trades_df_sorted['exit_time'], equity_curve, rolling_max_equity, where=equity_curve < rolling_max_equity, color='red', alpha=0.3, label='Drawdown from Peak')
        ax3.axhline(y=self.initial_capital, color='white', linestyle='--', alpha=0.7, label='Initial Capital')
        
        ax1.set_title(f'Trading Results - {data_file_name} - Params: {json.dumps(params,indent=1)}', fontsize=14)
        ax1.set_ylabel('Price / Indicators', fontsize=12); 
        ax2.set_ylabel('Volume', fontsize=12); 
        ax3.set_ylabel('Equity', fontsize=12)
        ax3.set_xlabel('Date', fontsize=12)
        for ax in [ax1, ax2, ax3]:
            ax.legend(loc=self.legend_loc, fontsize=self.font_size)
            ax.grid(self.show_grid)
        plt.setp(ax1.get_xticklabels(), visible=False)
        plt.setp(ax2.get_xticklabels(), visible=False)
        plt.tight_layout(pad=1.5)
        plot_path = os.path.join(self.results_dir, self.get_result_filename(data_file_name, suffix='_plot.'+self.plot_format, current_data=data_df))
        if self.save_plot:
            plt.savefig(plot_path, dpi=self.plot_dpi, bbox_inches='tight', format=self.plot_format)
        if self.show_plot:
            plt.show()
        plt.close()
        self.log_message(f"Plot saved to {plot_path}")
        return plot_path

if __name__ == "__main__":
    import json
    with open("config/optimizer/bb_volume_supertrend_optimizer.json") as f:
        config = json.load(f)
    optimizer = BBSuperTrendVolumeBreakoutOptimizer(config)
    optimizer.run_optimization()
