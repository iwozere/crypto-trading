from src.entry.entry_mixin import EntryLogicMixin
import backtrader as bt

class BBVolumeSuperTrendMixin(EntryLogicMixin):
    def init_entry(self, strategy, params):
        self.strategy = strategy
        self.bb_period = params.get('bb_period', 20)
        self.bb_dev = params.get('bb_dev', 2.0)
        self.vol_ma_period = params.get('vol_ma_period', 20)
        self.st_period = params.get('st_period', 10)
        self.st_multiplier = params.get('st_multiplier', 3.0)
        
        self.bb = bt.indicators.BollingerBands(period=self.bb_period, devfactor=self.bb_dev)
        self.vol_ma = bt.indicators.SMA(self.strategy.data.volume, period=self.vol_ma_period)
        self.supertrend = bt.indicators.SuperTrend(period=self.st_period, multiplier=self.st_multiplier)

    def should_enter(self):
        if self.strategy.position:
            return False
            
        return (self.strategy.data.close[0] < self.bb.lines.bot[0] and
                self.strategy.data.volume[0] > self.vol_ma[0] and
                self.supertrend[0] < self.strategy.data.close[0]) 