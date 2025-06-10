from src.exit.exit_mixin import ExitLogicMixin

class FixedRatioExitMixin(ExitLogicMixin):
    def init_exit(self, params=None):
        self.entry_price = None
        self.tp_ratio = self.params.take_profit
        self.sl_ratio = self.params.stop_loss

    def should_exit(self):
        if not self.position:
            return False
        if self.entry_price is None:
            self.entry_price = self.data.close[0]
        cp = self.data.close[0]
        return cp >= self.entry_price * (1 + self.tp_ratio) or cp <= self.entry_price * (1 - self.sl_ratio)