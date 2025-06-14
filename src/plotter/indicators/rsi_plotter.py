from src.plotter.indicators.base_indicator_plotter import BaseIndicatorPlotter

class RSIPlotter(BaseIndicatorPlotter):
    def plot(self, ax):
        """Plot RSI indicator"""
        try:
            # Try to plot entry RSI first
            if 'rsi' in self.indicators:
                rsi = self.indicators['rsi']
                if hasattr(rsi, 'array'):
                    rsi_data = rsi.array
                elif hasattr(rsi, 'lines'):
                    rsi_data = rsi.lines[0].array
                else:
                    self.logger.warning("RSI indicator has invalid data structure")
                    return
                    
                dates = [self.data.datetime.datetime(i) for i in range(len(self.data))]
                ax.plot(dates, rsi_data, label='RSI (Entry)', color='blue', alpha=0.7)
            
            # Then try to plot exit RSI if it exists
            if 'exit_rsi' in self.indicators:
                rsi = self.indicators['exit_rsi']
                if hasattr(rsi, 'array'):
                    rsi_data = rsi.array
                elif hasattr(rsi, 'lines'):
                    rsi_data = rsi.lines[0].array
                else:
                    self.logger.warning("Exit RSI indicator has invalid data structure")
                    return
                    
                dates = [self.data.datetime.datetime(i) for i in range(len(self.data))]
                ax.plot(dates, rsi_data, label='RSI (Exit)', color='red', alpha=0.7)
            
            # Add overbought/oversold lines
            ax.axhline(y=70, color='r', linestyle='--', alpha=0.3)
            ax.axhline(y=30, color='g', linestyle='--', alpha=0.3)
            
            ax.set_ylabel('RSI')
            self._apply_style(ax)
        except Exception as e:
            self.logger.error(f"Error plotting RSI: {str(e)}")

    @property
    def subplot_type(self):
        return 'separate' 