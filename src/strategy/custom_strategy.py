import backtrader as bt
from src.entry.entry_mixin_factory import EntryMixinFactory
from src.exit.exit_mixin_factory import ExitMixinFactory
from src.entry.entry_mixin import EntryLogicMixin
from src.exit.exit_mixin import ExitLogicMixin

# Caller is sending preinitialized mixins
def make_strategy() -> bt.Strategy:
    class CustomStrategy(bt.Strategy):
        params = (
            ('entry_logic', None),
            ('exit_logic', None),
        )

        def __init__(self):
            self.trades = []
            self._open_trade_data = None
            
            # Get entry and exit mixins
            self.entry_mixin = EntryMixinFactory.get_entry_mixin(self.p.entry_logic['name'])
            self.exit_mixin = ExitMixinFactory.get_exit_mixin(self.p.exit_logic['name'])
            
            # Initialize mixins with their respective parameters
            self.entry_mixin.init_entry(strategy=self, params=self.p.entry_logic['params'])
            self.exit_mixin.init_exit(strategy=self, params=self.p.exit_logic['params'])
            
            super().__init__()

        def next(self):
            if not self.position and self.entry_mixin.should_enter():
                self.buy()
                self._open_trade_data = {
                    'entry_date': self.data.datetime.date(0).isoformat(),
                    'entry_price': self.data.close[0],
                    'entry_indicators': self.collect_entry_indicators()
                }
            elif self.position and self.exit_mixin.should_exit():
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