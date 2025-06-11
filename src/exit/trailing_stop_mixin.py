from src.exit.exit_mixin import BaseExitMixin

class TrailingStopExitMixin(BaseExitMixin):
    def init_exit(self, params, strategy):
        self.strategy = strategy
        self.trail_pct = params.get('trail_pct', 0.02)
        self.highest_price = 0.0

    def should_exit(self):
        if not self.strategy.position:
            return False
            
        price = self.strategy.data.close[0]
        
        # Update highest price if current price is higher
        if price > self.highest_price:
            self.highest_price = price
            
        # Calculate trailing stop level
        stop_level = self.highest_price * (1 - self.trail_pct)
        
        # Exit if price falls below trailing stop
        return price < stop_level