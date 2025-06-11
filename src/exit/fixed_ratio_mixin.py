"""
Fixed Ratio Exit Mixin

This module implements a simple exit strategy based on fixed percentage take profit and
stop loss levels. The strategy exits when:
1. Price reaches the take profit level (entry_price * (1 + take_profit))
2. Price reaches the stop loss level (entry_price * (1 - stop_loss))

Parameters:
    take_profit (float): Take profit percentage (default: 0.02)
    stop_loss (float): Stop loss percentage (default: 0.01)

This strategy is particularly effective for:
1. Short-term trading
2. Ranging markets
3. When you want predictable risk/reward ratios
4. When you need simple and clear exit rules

The strategy is simple but can be powerful when combined with proper position sizing
and risk management. It's often used as a baseline exit strategy that can be enhanced
with more sophisticated exit rules.
"""

from typing import Dict, Any
from src.exit.exit_mixin import BaseExitMixin

class FixedRatioExitMixin(BaseExitMixin):
    """Exit mixin на основе фиксированного соотношения прибыли/убытка"""
    
    def get_required_params(self) -> list:
        """There are no required parameters - all have default values"""
        return []
    
    def get_default_params(self) -> Dict[str, Any]:
        """Default parameters"""
        return {
            'take_profit': 0.02,  # 2% take profit
            'stop_loss': 0.01     # 1% stop loss
        }
    
    def _init_indicators(self):
        """No indicators needed for fixed ratio exit"""
        pass
    
    def should_exit(self, strategy) -> bool:
        """
        Exit logic: Exit when price reaches take profit or stop loss levels
        based on fixed percentage ratios
        """
        if not strategy.position:
            return False
            
        price = strategy.data.close[0]
        entry_price = strategy.position.price
        
        # Calculate profit/loss percentage
        pnl_pct = (price - entry_price) / entry_price
        
        # Exit if take profit or stop loss is hit
        return pnl_pct >= self.get_param('take_profit') or pnl_pct <= -self.get_param('stop_loss')