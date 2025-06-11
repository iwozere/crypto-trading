import backtrader as bt
from src.entry.entry_mixin_factory import EntryMixinFactory
from src.exit.exit_mixin_factory import ExitMixinFactory

def make_strategy() -> bt.Strategy:
    class CustomStrategy(bt.Strategy):
        params = (
            ('entry_type', None),
            ('exit_type', None),
            ('rsi_period', 14),
            ('bb_period', 20),
            ('bb_dev', 2.0),
            ('rsi_oversold', 30),
            ('atr_period', 14),
            ('tp_multiplier', 2.0),
            ('sl_multiplier', 1.0),
            ('use_talib', True),
            ('ma_period', 20),
            ('time_period', 10),
            ('trail_pct', 0.02),
            ('sl_pct', 0.02),
            ('rr', 2.0),
            ('take_profit', 0.02),
            ('stop_loss', 0.01),
            ('vol_ma_period', 20),
            ('st_period', 10),
            ('st_multiplier', 3.0),
            ('tenkan_period', 9),
            ('kijun_period', 26),
        )

        def __init__(self):
            self.trades = []
            self._open_trade_data = None
            
            # Get entry and exit mixins
            self.entry_mixin = EntryMixinFactory.get_entry_mixin(self.p.entry_type)
            self.exit_mixin = ExitMixinFactory.get_exit_mixin(self.p.exit_type)
            
            # Initialize mixins with strategy parameters
            self.entry_mixin.init_entry(self.p)
            self.exit_mixin.init_exit(self.p)
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