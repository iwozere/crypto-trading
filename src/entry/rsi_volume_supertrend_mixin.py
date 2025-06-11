from src.entry.entry_mixin import EntryLogicMixin
import backtrader as bt

class RSIVolumeSuperTrendMixin(EntryLogicMixin):
    def init_entry(self, strategy, params):
        self.strategy = strategy
        self.rsi_period = params.get('rsi_period', 14)
        self.rsi_oversold = params.get('rsi_oversold', 30)
        self.vol_ma_period = params.get('vol_ma_period', 20)
        self.st_period = params.get('st_period', 10)
        self.st_multiplier = params.get('st_multiplier', 3.0)
        
        self.rsi = bt.indicators.RSI(period=self.rsi_period)
        self.vol_ma = bt.indicators.SMA(self.strategy.data.volume, period=self.vol_ma_period)
        self.supertrend = bt.indicators.SuperTrend(period=self.st_period, multiplier=self.st_multiplier)

    def should_enter(self):
        if self.strategy.position:
            return False
            
        return (self.rsi[0] < self.rsi_oversold and
                self.strategy.data.volume[0] > self.vol_ma[0] and
                self.supertrend[0] < self.strategy.data.close[0]) 