import backtrader as bt
from src.entry.entry_mixin import EntryLogicMixin
from src.exit.exit_mixin import ExitLogicMixin

def make_strategy(entry_mixin : EntryLogicMixin, exit_mixin : ExitLogicMixin):
    class CustomStrategy(bt.Strategy, entry_mixin, exit_mixin):
        def __init__(self, params: dict):
            self.trades = []
            self._open_trade_data = None
            self.init_entry(params)
            self.init_exit(params)
            super().__init__(params)


        def next(self):
            if not self.position and self.should_enter():
                self.buy()
                self._open_trade_data = {
                    'entry_date': self.data.datetime.date(0).isoformat(),
                    'entry_price': self.data.close[0],
                    'entry_indicators': self.collect_entry_indicators()
                }
            elif self.position and self.should_exit():
                self.close()
                trade_data = self._open_trade_data or {}
                trade_data.update({
                    'exit_date': self.data.datetime.date(0).isoformat(),
                    'exit_price': self.data.close[0],
                    'pnl': self.data.close[0] - trade_data.get('entry_price', 0),
                    'exit_indicators': self.collect_exit_indicators()
                })
                self.trades.append(trade_data)
                self._open_trade_data = None

        def notify_trade(self, trade):
            if trade.isclosed:
                self.trades.append({
                    'date': self.data.datetime.date(0).isoformat(),
                    'price_entry': trade.price,
                    'price_exit': trade.close_price,
                    'pnl': trade.pnl,
                    'pnl_pct': trade.pnlcomm / trade.price if trade.price != 0 else None,
                    'bar_executed': trade.baropen,
                    'bar_closed': trade.barclose
                })
                
    return CustomStrategy