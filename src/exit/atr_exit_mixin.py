from src.exit.exit_mixin import ExitLogicMixin
import backtrader as bt

class ATRExitMixin(ExitLogicMixin):
    def init_exit(self, params=None):
        self.entry_price = None
        self.atr_period = self.params.get('atr_period', 14)
        self.tp_multiplier = self.params.get('tp_multiplier', 2.0)
        self.sl_multiplier = self.params.get('sl_multiplier', 1.0)
        self.atr = bt.indicators.ATR(self.data, period=self.atr_period)

    def should_exit(self):
        if not self.position:
            return False
        if self.entry_price is None:
            self.entry_price = self.data.close[0]
        
        current_price = self.data.close[0]
        atr_value = self.atr[0]
        
        # Calculate take profit and stop loss levels
        tp_level = self.entry_price + (atr_value * self.tp_multiplier)
        sl_level = self.entry_price - (atr_value * self.sl_multiplier)
        
        return current_price >= tp_level or current_price <= sl_level 