from src.plotter.base_plotter import BasePlotter
import matplotlib.pyplot as plt

class RSIIchimokuPlotter(BasePlotter):
    def _plot_indicators(self):
        """Plot RSI and Ichimoku Cloud indicators"""
        ax = self.axes[0]
        
        # Plot Ichimoku Cloud
        entry_mixin = self.strategy.entry_mixin
        indicators = entry_mixin.indicators
        
        # Plot Kumo (Cloud)
        ax.fill_between(
            self.data.datetime.array,
            indicators["senkou_span_a"].array,
            indicators["senkou_span_b"].array,
            where=indicators["senkou_span_a"].array >= indicators["senkou_span_b"].array,
            color='green', alpha=0.1, label='Bullish Cloud'
        )
        ax.fill_between(
            self.data.datetime.array,
            indicators["senkou_span_a"].array,
            indicators["senkou_span_b"].array,
            where=indicators["senkou_span_a"].array < indicators["senkou_span_b"].array,
            color='red', alpha=0.1, label='Bearish Cloud'
        )
        
        # Plot Ichimoku lines
        ax.plot(self.data.datetime.array, indicators["tenkan"].array, 
                label='Tenkan-sen', color='blue', alpha=0.7)
        ax.plot(self.data.datetime.array, indicators["kijun"].array, 
                label='Kijun-sen', color='red', alpha=0.7)
        ax.plot(self.data.datetime.array, indicators["senkou_span_a"].array, 
                label='Senkou Span A', color='green', alpha=0.7)
        ax.plot(self.data.datetime.array, indicators["senkou_span_b"].array, 
                label='Senkou Span B', color='orange', alpha=0.7)
        ax.plot(self.data.datetime.array, indicators["chikou_span"].array, 
                label='Chikou Span', color='purple', alpha=0.7)
        
        # Create a new subplot for RSI
        ax_rsi = self.axes[0].twinx()
        ax_rsi.plot(self.data.datetime.array, indicators["rsi"].array, 
                   label='RSI', color='gray', alpha=0.7)
        ax_rsi.axhline(y=70, color='r', linestyle='--', alpha=0.3)
        ax_rsi.axhline(y=30, color='g', linestyle='--', alpha=0.3)
        ax_rsi.set_ylabel('RSI')
        ax_rsi.set_ylim(0, 100)
        
        # Add legends
        lines1, labels1 = ax.get_legend_handles_labels()
        lines2, labels2 = ax_rsi.get_legend_handles_labels()
        ax.legend(lines1 + lines2, labels1 + labels2, loc='upper left') 