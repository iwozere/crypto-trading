from src.exit.exit_mixin import ExitLogicMixin

class TimeBasedExitMixin(ExitLogicMixin):
    def init_exit(self):
        self.entry_time = None
        self.max_bars = self.p.get('max_bars', 10)
        self.bar_count = 0

    def should_exit(self):
        if not self.position:
            return False
        if self.entry_time is None:
            self.entry_time = self.data.datetime.datetime(0)
            self.bar_count = 0
        
        self.bar_count += 1
        return self.bar_count >= self.max_bars 