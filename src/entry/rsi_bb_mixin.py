from src.entry.entry_mixin import EntryLogicMixin
import backtrader as bt

class RSIBBMixin(EntryLogicMixin):
    def init_entry(self, params=None):
        self.rsi_period = self.p.rsi_period
        self.bb_period = self.p.bb_period
        self.bb_dev = self.p.bb_dev
        self.rsi_oversold = self.p.rsi_oversold
        
        self.rsi = bt.indicators.RSI(period=self.rsi_period)
        self.bb = bt.indicators.BollingerBands(period=self.bb_period, devfactor=self.bb_dev)

    def should_enter(self):
        if self.position:
            return False
            
        return (self.rsi[0] < self.rsi_oversold and 
                self.data.close[0] < self.bb.lines.bot[0]) 