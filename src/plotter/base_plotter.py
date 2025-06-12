import matplotlib.pyplot as plt
import pandas as pd
import backtrader as bt
from datetime import datetime

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

    def plot(self, output_path):
        """Create and save the plot"""
        self._create_figure()
        self._plot_price()
        if self.vis_settings.get("show_indicators", True):
            self._plot_indicators()
        self._plot_trades()
        if self.vis_settings.get("show_equity_curve", True):
            self._plot_equity()
        self._save_plot(output_path)

    def _create_figure(self):
        """Create figure with subplots"""
        # Set plot style
        plt.style.use(self.vis_settings.get("plot_style", "default"))
        
        # Create figure with specified size
        plot_size = self.vis_settings.get("plot_size", [15, 10])
        self.fig = plt.figure(figsize=plot_size)
        
        # Create subplots: price+indicators and equity
        n_subplots = 2 if self.vis_settings.get("show_equity_curve", True) else 1
        self.axes = self.fig.subplots(n_subplots, 1, height_ratios=[3, 1] if n_subplots == 2 else [1])
        
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
        """Plot indicators - to be implemented by specific plotters"""
        pass

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
            ax = self.axes[1]
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