from src.exit.exit_mixin import ExitLogicMixin
import backtrader as bt

class MACrossoverExitMixin(ExitLogicMixin):
    def init_exit(self, strategy, params):
        self.strategy = strategy
        self.ma_period = params.get('ma_period', 20)
        
        self.ma = bt.indicators.SMA(self.strategy.data.close, period=self.ma_period)

    def should_exit(self):
        if not self.strategy.position:
            return False
            
        return self.strategy.data.close[0] < self.ma[0]
 