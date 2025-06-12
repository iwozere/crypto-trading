import matplotlib.pyplot as plt
import pandas as pd
import backtrader as bt
from datetime import datetime
from src.plotter.indicators.ichimoku_plotter import IchimokuPlotter
from src.plotter.indicators.rsi_plotter import RSIPlotter
from src.plotter.indicators.bollinger_bands_plotter import BollingerBandsPlotter
from src.plotter.indicators.volume_plotter import VolumePlotter
from src.plotter.indicators.supertrend_plotter import SuperTrendPlotter

class BasePlotter:
    def __init__(self, data, trades, strategy, vis_settings):
        """
        Initialize the plotter
        
        Args:
            data: Backtrader data feed
            trades: List of trade dictionaries
            strategy: Strategy instance containing indicators
            vis_settings: Visualization settings from optimizer config
        """
        self.data = data
        self.trades = trades
        self.strategy = strategy
        self.vis_settings = vis_settings
        self.fig = None
        self.axes = None
        
        # Initialize indicator plotters
        self.indicator_plotters = self._create_indicator_plotters()

    def _create_indicator_plotters(self):
        """Create appropriate indicator plotters based on strategy"""
        plotters = []
        entry_mixin = self.strategy.entry_mixin
        
        # Add plotters based on available indicators
        if hasattr(entry_mixin, 'indicators'):
            indicators = entry_mixin.indicators
            
            # RSI
            if 'rsi' in indicators:
                plotters.append(RSIPlotter(self.data, indicators, self.vis_settings))
            
            # Ichimoku
            if all(k in indicators for k in ['tenkan', 'kijun', 'senkou_span_a', 'senkou_span_b']):
                plotters.append(IchimokuPlotter(self.data, indicators, self.vis_settings))
            
            # Bollinger Bands
            if all(k in indicators for k in ['bb_upper', 'bb_middle', 'bb_lower']):
                plotters.append(BollingerBandsPlotter(self.data, indicators, self.vis_settings))
            
            # Volume
            if 'volume' in indicators:
                plotters.append(VolumePlotter(self.data, indicators, self.vis_settings))
            
            # SuperTrend
            if 'supertrend' in indicators:
                plotters.append(SuperTrendPlotter(self.data, indicators, self.vis_settings))
        
        return plotters

    def plot(self, output_path):
        """Create and save the plot"""
        self._create_figure()
        self._plot_price()
        self._plot_indicators()
        self._plot_trades()
        if self.vis_settings.get("show_equity_curve", True):
            self._plot_equity()
        self._save_plot(output_path)

    def _create_figure(self):
        """Create figure with subplots"""
        # Set plot style
        plt.style.use(self.vis_settings.get("plot_style", "default"))
        
        # Calculate number of subplots needed
        n_subplots = 1  # Price subplot
        for plotter in self.indicator_plotters:
            if plotter.subplot_type == 'separate':
                n_subplots += 1
        if self.vis_settings.get("show_equity_curve", True):
            n_subplots += 1
        
        # Create figure with appropriate size
        plot_size = self.vis_settings.get("plot_size", [15, 10])
        self.fig = plt.figure(figsize=plot_size)
        
        # Create subplots with appropriate ratios
        ratios = [3] + [1] * (n_subplots - 1)  # Price plot is larger
        self.axes = self.fig.subplots(n_subplots, 1, height_ratios=ratios)
        if n_subplots == 1:
            self.axes = [self.axes]
        
        # Set title with timestamp
        self.fig.suptitle(
            f'Strategy Backtest Results - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
            fontsize=self.vis_settings.get("font_size", 10)
        )

    def _plot_price(self):
        """Plot price data"""
        ax = self.axes[0]
        ax.plot(self.data.datetime.array, self.data.close.array, label='Price', color='black', alpha=0.7)
        ax.set_ylabel('Price')
        
        # Configure grid
        if self.vis_settings.get("show_grid", True):
            ax.grid(True, alpha=0.3)
        
        # Configure legend
        ax.legend(loc=self.vis_settings.get("legend_loc", "upper left"))
        
        # Set font size
        ax.tick_params(axis='both', which='major', 
                      labelsize=self.vis_settings.get("font_size", 10))

    def _plot_indicators(self):
        """Plot all indicators using their respective plotters"""
        current_ax = 0
        for plotter in self.indicator_plotters:
            if plotter.subplot_type == 'price':
                plotter.plot(self.axes[0])
            else:
                current_ax += 1
                plotter.plot(self.axes[current_ax])

    def _plot_trades(self):
        """Plot trade markers"""
        ax = self.axes[0]
        for trade in self.trades:
            # Plot entry
            if 'entry_date' in trade:
                entry_date = pd.to_datetime(trade['entry_date'])
                ax.scatter(entry_date, trade['entry_price'], 
                          marker='^', color='green', s=100, 
                          label='Buy' if trade == self.trades[0] else "")
            
            # Plot exit
            if 'exit_date' in trade:
                exit_date = pd.to_datetime(trade['exit_date'])
                ax.scatter(exit_date, trade['exit_price'], 
                          marker='v', color='red', s=100, 
                          label='Sell' if trade == self.trades[0] else "")

    def _plot_equity(self):
        """Plot equity curve"""
        if len(self.axes) > 1:  # Only plot if we have a second subplot
            ax = self.axes[-1]  # Always last subplot
            equity = self.strategy.broker.getvalue()
            ax.plot(self.data.datetime.array, equity, label='Equity', color='blue')
            ax.set_ylabel('Equity')
            
            # Configure grid
            if self.vis_settings.get("show_grid", True):
                ax.grid(True, alpha=0.3)
            
            # Configure legend
            ax.legend(loc=self.vis_settings.get("legend_loc", "upper left"))
            
            # Set font size
            ax.tick_params(axis='both', which='major', 
                          labelsize=self.vis_settings.get("font_size", 10))

    def _save_plot(self, output_path):
        """Save the plot to file"""
        plt.tight_layout()
        
        # Save plot with specified DPI
        plt.savefig(
            output_path,
            dpi=self.vis_settings.get("plot_dpi", 300),
            format=self.vis_settings.get("plot_format", "png")
        )
        
        # Show plot if configured
        if self.vis_settings.get("show_plot", False):
            plt.show()
        
        plt.close() 