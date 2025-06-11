from src.exit.exit_mixin import ExitLogicMixin
import backtrader as bt

class TimeBasedExitMixin(ExitLogicMixin):
    def init_exit(self, strategy, params):
        self.strategy = strategy
        self.time_period = params.get('time_period', 10)
        self.entry_bar = 0

    def should_exit(self):
        if not self.strategy.position:
            return False
            
        # Update entry bar if not set
        if self.entry_bar == 0:
            self.entry_bar = len(self.strategy)
            
        # Exit if time period has elapsed
        return len(self.strategy) - self.entry_bar >= self.time_period 