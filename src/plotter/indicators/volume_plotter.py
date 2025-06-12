from src.plotter.indicators.base_indicator_plotter import BaseIndicatorPlotter
import numpy as np

class VolumePlotter(BaseIndicatorPlotter):
    @property
    def subplot_type(self):
        return 'separate'

    def plot(self, ax):
        """Plot Volume on a separate axis"""
        # Plot volume bars
        volume = self.indicators["volume"].array
        dates = self.data.datetime.array
        
        # Color bars based on price movement
        colors = np.where(
            self.data.close.array > self.data.open.array,
            'green',  # Up day
            'red'     # Down day
        )
        
        ax.bar(dates, volume, color=colors, alpha=0.7, label='Volume')
        
        # Plot volume MA if available
        if "vol_ma" in self.indicators:
            ax.plot(dates, self.indicators["vol_ma"].array,
                   label='Volume MA', color='blue', alpha=0.7)
        
        ax.set_ylabel('Volume')
        ax.set_ylim(bottom=0)  # Start y-axis from 0
        
        self._apply_style(ax) 