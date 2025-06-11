from src.entry.entry_mixin import EntryLogicMixin
import backtrader as bt
from src.indicator.super_trend import SuperTrend

class BBVolumeSuperTrendMixin(EntryLogicMixin):
    def init_entry(self):
        self.bb_period = self.p.get('bb_period', 20)
        self.bb_dev = self.p.get('bb_dev', 2.0)
        self.vol_ma_period = self.p.get('vol_ma_period', 20)
        self.st_period = self.p.get('st_period', 10)
        self.st_multiplier = self.p.get('st_multiplier', 3.0)
        
        self.bb = bt.indicators.BollingerBands(period=self.bb_period, devfactor=self.bb_dev)
        self.vol_ma = bt.indicators.SMA(self.data.volume, period=self.vol_ma_period)
        
        supertrend_params = {
            "period": self.st_period,
            "multiplier": self.st_multiplier,
            "use_talib": self.p.get('use_talib', True)
        }
        self.supertrend = SuperTrend(params=supertrend_params)

    def should_enter(self):
        if self.position:
            return False
            
        return (self.data.close[0] < self.bb.lines.bot[0] and 
                self.data.volume[0] > self.vol_ma[0] and
                self.data.close[0] > self.supertrend.lines.supertrend[0]) 