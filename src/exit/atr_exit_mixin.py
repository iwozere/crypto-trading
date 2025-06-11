from src.exit.exit_mixin import BaseExitMixin
import backtrader as bt

class ATRExitMixin(BaseExitMixin):
    def init_exit(self, strategy, params):
        self.strategy = strategy
        self.atr_period = params.get('atr_period', 14)
        self.tp_multiplier = params.get('tp_multiplier', 2.0)
        self.sl_multiplier = params.get('sl_multiplier', 1.0)
        
        self.atr = bt.indicators.ATR(period=self.atr_period)

    def should_exit(self):
        if not self.strategy.position:
            return False
            
        price = self.strategy.data.close[0]
        entry_price = self.strategy.position.price
        
        # Calculate take profit and stop loss levels
        tp_level = entry_price + (self.atr[0] * self.tp_multiplier)
        sl_level = entry_price - (self.atr[0] * self.sl_multiplier)
        
        # Exit if take profit or stop loss is hit
        return price >= tp_level or price <= sl_level 