from src.entry.entry_mixin import EntryLogicMixin
import backtrader as bt

class RSIBBVolumeMixin(EntryLogicMixin):
    def init_entry(self, strategy, params):
        self.strategy = strategy
        self.rsi_period = params.get('rsi_period', 14)
        self.rsi_oversold = params.get('rsi_oversold', 30)
        self.bb_period = params.get('bb_period', 20)
        self.bb_dev = params.get('bb_dev', 2.0)
        self.vol_ma_period = params.get('vol_ma_period', 20)
        
        self.rsi = bt.indicators.RSI(period=self.rsi_period)
        self.bb = bt.indicators.BollingerBands(period=self.bb_period, devfactor=self.bb_dev)
        self.vol_ma = bt.indicators.SMA(self.strategy.data.volume, period=self.vol_ma_period)

    def should_enter(self):
        if self.strategy.position:
            return False
            
        return (self.rsi[0] < self.rsi_oversold and
                self.strategy.data.close[0] < self.bb.lines.bot[0] and
                self.strategy.data.volume[0] > self.vol_ma[0]) 