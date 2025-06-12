from src.plotter.indicators.base_indicator_plotter import BaseIndicatorPlotter

class IchimokuPlotter(BaseIndicatorPlotter):
    @property
    def subplot_type(self):
        return 'price'

    def plot(self, ax):
        """Plot Ichimoku Cloud on the price axis"""
        # Plot Kumo (Cloud)
        ax.fill_between(
            self.data.datetime.array,
            self.indicators["senkou_span_a"].array,
            self.indicators["senkou_span_b"].array,
            where=self.indicators["senkou_span_a"].array >= self.indicators["senkou_span_b"].array,
            color='green', alpha=0.1, label='Bullish Cloud'
        )
        ax.fill_between(
            self.data.datetime.array,
            self.indicators["senkou_span_a"].array,
            self.indicators["senkou_span_b"].array,
            where=self.indicators["senkou_span_a"].array < self.indicators["senkou_span_b"].array,
            color='red', alpha=0.1, label='Bearish Cloud'
        )
        
        # Plot Ichimoku lines
        ax.plot(self.data.datetime.array, self.indicators["tenkan"].array, 
                label='Tenkan-sen', color='blue', alpha=0.7)
        ax.plot(self.data.datetime.array, self.indicators["kijun"].array, 
                label='Kijun-sen', color='red', alpha=0.7)
        ax.plot(self.data.datetime.array, self.indicators["senkou_span_a"].array, 
                label='Senkou Span A', color='green', alpha=0.7)
        ax.plot(self.data.datetime.array, self.indicators["senkou_span_b"].array, 
                label='Senkou Span B', color='orange', alpha=0.7)
        ax.plot(self.data.datetime.array, self.indicators["chikou_span"].array, 
                label='Chikou Span', color='purple', alpha=0.7)
        
        self._apply_style(ax) 