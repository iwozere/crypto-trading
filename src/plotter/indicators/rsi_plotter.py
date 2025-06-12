from src.plotter.indicators.base_indicator_plotter import BaseIndicatorPlotter

class RSIPlotter(BaseIndicatorPlotter):
    @property
    def subplot_type(self):
        return 'separate'

    def plot(self, ax):
        """Plot RSI on a separate axis"""
        ax.plot(self.data.datetime.array, self.indicators["rsi"].array, 
               label='RSI', color='gray', alpha=0.7)
        ax.axhline(y=70, color='r', linestyle='--', alpha=0.3)
        ax.axhline(y=30, color='g', linestyle='--', alpha=0.3)
        ax.set_ylabel('RSI')
        ax.set_ylim(0, 100)
        
        self._apply_style(ax) 