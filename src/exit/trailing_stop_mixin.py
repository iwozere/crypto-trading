from src.exit.exit_mixin import ExitLogicMixin

class TrailingStopExitMixin(ExitLogicMixin):
    def init_exit(self):
        self.trailing_stop_pct = self.p.get('trailing_stop', 0.02)
        self.highest_price = None

    def should_exit(self):
        if not self.position:
            self.highest_price = None
            return False

        cp = self.data.close[0]
        self.highest_price = max(self.highest_price or cp, cp)
        stop_price = self.highest_price * (1 - self.trailing_stop_pct)
        return cp <= stop_price