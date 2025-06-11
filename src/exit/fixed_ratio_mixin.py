from src.exit.exit_mixin import ExitLogicMixin

class FixedRatioExitMixin(ExitLogicMixin):
    def init_exit(self):
        self.entry_price = None
        self.tp_ratio = self.p.get('take_profit', 0.02)
        self.sl_ratio = self.p.get('stop_loss', 0.01)

    def should_exit(self):
        if not self.position:
            return False
        if self.entry_price is None:
            self.entry_price = self.data.close[0]
        cp = self.data.close[0]
        return cp >= self.entry_price * (1 + self.tp_ratio) or cp <= self.entry_price * (1 - self.sl_ratio)