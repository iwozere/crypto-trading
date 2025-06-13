from src.plotter.indicators.base_indicator_plotter import BaseIndicatorPlotter

class RSIPlotter(BaseIndicatorPlotter):
    def plot(self, ax):
        """Plot RSI indicator"""
        try:
            rsi = self.indicators['rsi']
            dates = [self.data.datetime.datetime(i) for i in range(len(self.data))]
            ax.plot(dates, rsi, label='RSI', color='blue', alpha=0.7)
            ax.set_ylabel('RSI')
            ax.axhline(y=70, color='r', linestyle='--', alpha=0.3)
            ax.axhline(y=30, color='g', linestyle='--', alpha=0.3)
            self._apply_style(ax)
        except Exception as e:
            self.logger.error(f"Error plotting RSI: {str(e)}")

    @property
    def subplot_type(self):
        return 'separate' 