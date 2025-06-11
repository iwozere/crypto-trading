from src.entry.entry_mixin import EntryLogicMixin
import backtrader as bt

class RSIIchimokuMixin(EntryLogicMixin):
    def init_entry(self, strategy, params):
        self.strategy = strategy
        self.rsi_period = params.get('rsi_period', 14)
        self.rsi_oversold = params.get('rsi_oversold', 30)
        self.tenkan_period = params.get('tenkan_period', 9)
        self.kijun_period = params.get('kijun_period', 26)
        
        self.rsi = bt.indicators.RSI(period=self.rsi_period)
        self.ichimoku = bt.indicators.Ichimoku(
            tenkan_period=self.tenkan_period,
            kijun_period=self.kijun_period
        )

    def should_enter(self):
        if self.strategy.position:
            return False
            
        return (self.rsi[0] < self.rsi_oversold and
                self.ichimoku.tenkan_sen[0] > self.ichimoku.kijun_sen[0] and
                self.strategy.data.close[0] > self.ichimoku.senkou_span_a[0]) 
        