from src.exit.exit_mixin import ExitLogicMixin
import backtrader as bt

class MACrossoverExitMixin(ExitLogicMixin):
    def init_exit(self, params=None):
        self.ma_period = self.params.get('ma_period', 20)
        self.ma = bt.indicators.SMA(self.data.close, period=self.ma_period)

    def should_exit(self):
        if not self.position:
            return False
        
        # Exit when price crosses below MA
 