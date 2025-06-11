from src.entry.entry_mixin import EntryLogicMixin
import backtrader as bt
from src.indicator.super_trend import SuperTrend

class RSIVolumeSuperTrendMixin(EntryLogicMixin):
    def init_entry(self):
        self.rsi_period = self.p.get('rsi_period', 14)
        self.vol_ma_period = self.p.get('vol_ma_period', 20)
        self.st_period = self.parapms.get('st_period', 10)
        self.st_multiplier = self.p.get('st_multiplier', 3.0)
        self.rsi_oversold = self.p.get('rsi_oversold', 30)
        
        self.rsi = bt.indicators.RSI(period=self.rsi_period)
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
            
        return (self.rsi[0] < self.rsi_oversold and 
                self.data.volume[0] > self.vol_ma[0] and
                self.data.close[0] > self.supertrend.lines.supertrend[0]) 