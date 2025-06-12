from src.plotter.indicators.base_indicator_plotter import BaseIndicatorPlotter

class BollingerBandsPlotter(BaseIndicatorPlotter):
    @property
    def subplot_type(self):
        return 'price'

    def plot(self, ax):
        """Plot Bollinger Bands on the price axis"""
        # Plot bands
        ax.plot(self.data.datetime.array, self.indicators["bb_upper"].array, 
                label='BB Upper', color='red', alpha=0.7, linestyle='--')
        ax.plot(self.data.datetime.array, self.indicators["bb_middle"].array, 
                label='BB Middle', color='blue', alpha=0.7)
        ax.plot(self.data.datetime.array, self.indicators["bb_lower"].array, 
                label='BB Lower', color='red', alpha=0.7, linestyle='--')
        
        # Fill between bands
        ax.fill_between(
            self.data.datetime.array,
            self.indicators["bb_upper"].array,
            self.indicators["bb_lower"].array,
            color='gray', alpha=0.1, label='BB Range'
        )
        
        self._apply_style(ax) 