from src.entry.entry_mixin import EntryLogicMixin
import backtrader as bt

class RSIIchimokuMixin(EntryLogicMixin):
    def init_entry(self, params=None):
        self.rsi_period = self.params.get('rsi_period', 14)
        self.tenkan_period = self.params.get('tenkan_period', 9)
        self.kijun_period = self.params.get('kijun_period', 26)
        self.rsi_oversold = self.params.get('rsi_oversold', 30)
        
        self.rsi = bt.indicators.RSI(period=self.rsi_period)
        self.ichimoku = bt.indicators.Ichimoku(
            tenkan_period=self.tenkan_period,
            kijun_period=self.kijun_period
        )

    def should_enter(self):
        if self.position:
            return False
            
        return (self.rsi[0] < self.rsi_oversold and 
                self.data.close[0] > self.ichimoku.lines.tenkan[0] and
                self.ichimoku.lines.tenkan[0] > self.ichimoku.lines.kijun[0]) 