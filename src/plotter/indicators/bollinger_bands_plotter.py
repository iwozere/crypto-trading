from src.plotter.indicators.base_indicator_plotter import BaseIndicatorPlotter

class BollingerBandsPlotter(BaseIndicatorPlotter):
    def plot(self, ax):
        """Plot Bollinger Bands indicator"""
        try:
            if 'bb' not in self.indicators:
                self.logger.warning("Bollinger Bands indicator not found")
                return
                
            bb = self.indicators['bb']
            dates = [self.data.datetime.datetime(i) for i in range(len(self.data))]
            
            # Plot the bands
            ax.plot(dates, bb.lines[0], label='Upper Band', color='red', alpha=0.5)
            ax.plot(dates, bb.lines[1], label='Middle Band', color='blue', alpha=0.5)
            ax.plot(dates, bb.lines[2], label='Lower Band', color='green', alpha=0.5)
            
            self._apply_style(ax)
        except Exception as e:
            self.logger.error(f"Error plotting Bollinger Bands: {str(e)}")

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