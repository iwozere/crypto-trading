from src.plotter.indicators.base_indicator_plotter import BaseIndicatorPlotter

class SuperTrendPlotter(BaseIndicatorPlotter):
    @property
    def subplot_type(self):
        return 'price'

    def plot(self, ax):
        """Plot SuperTrend on the price axis"""
        # Plot SuperTrend line
        ax.plot(self.data.datetime.array, self.indicators["supertrend"].array,
                label='SuperTrend', color='purple', alpha=0.7, linewidth=2)
        
        # Plot ATR if available
        if "atr" in self.indicators:
            ax.plot(self.data.datetime.array, self.indicators["atr"].array,
                   label='ATR', color='orange', alpha=0.5, linestyle='--')
        
        # Fill between price and SuperTrend to show trend direction
        ax.fill_between(
            self.data.datetime.array,
            self.data.close.array,
            self.indicators["supertrend"].array,
            where=self.data.close.array > self.indicators["supertrend"].array,
            color='green', alpha=0.1, label='Bullish'
        )
        ax.fill_between(
            self.data.datetime.array,
            self.data.close.array,
            self.indicators["supertrend"].array,
            where=self.data.close.array <= self.indicators["supertrend"].array,
            color='red', alpha=0.1, label='Bearish'
        )
        
        self._apply_style(ax) 