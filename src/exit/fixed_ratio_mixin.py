from src.exit.exit_mixin import BaseExitMixin

class FixedRatioExitMixin(BaseExitMixin):
    def init_exit(self, strategy, params):
        self.strategy = strategy
        self.take_profit = params.get('take_profit', 0.02)
        self.stop_loss = params.get('stop_loss', 0.01)

    def should_exit(self):
        if not self.strategy.position:
            return False
            
        price = self.strategy.data.close[0]
        entry_price = self.strategy.position.price
        
        # Calculate profit/loss percentage
        pnl_pct = (price - entry_price) / entry_price
        
        # Exit if take profit or stop loss is hit
        return pnl_pct >= self.take_profit or pnl_pct <= -self.stop_loss