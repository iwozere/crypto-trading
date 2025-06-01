"""
RSI Bollinger Bands Volume Trading Bot Module
--------------------------------------------

This module implements a trading bot based on the RSI, Bollinger Bands, and volume indicators. The bot is designed for use with the Binance exchange and can be run in both backtesting and live trading modes. It inherits from BaseTradingBot and integrates a specific strategy implementation.

Main Features:
- Automated trading using RSI, Bollinger Bands, and volume signals
- Position management and trade execution
- Trade history and performance tracking
- Designed for extension and integration with other trading infrastructure

Classes:
- RsiBbVolumeBot: Main bot class for this strategy
"""

import time
import backtrader as bt
from datetime import datetime
from binance.client import Client
from binance.exceptions import BinanceAPIException
from config.donotshare.donotshare import BINANCE_PAPER_KEY, BINANCE_PAPER_SECRET
from src.trading.base_trading_bot import BaseTradingBot
from typing import Any, Dict
from src.data.binance_live_feed import BinanceLiveFeed
from src.strats.bb_volume_supertrend_strategy import BBSuperTrendVolumeBreakoutStrategy
from src.broker.binance_paper_broker import BinancePaperBroker
from src.notification.logger import _logger


class RsiBbVolumeBot(BaseTradingBot):
    """
    Trading bot for RSI, Bollinger Bands, and Volume strategies. Accepts any strategy class and parameters, and instantiates via Backtrader Cerebro.
    """
    def __init__(self, config: Dict[str, Any], strategy_class: Any, parameters: Dict[str, Any], broker: Any = None) -> None:
        super().__init__(config, strategy_class, parameters, broker)

    def run(self) -> None:
        """Main bot loop using Backtrader Cerebro."""
        symbol = self.config.get('trading_pair', 'BTCUSDT')
        interval = self.config.get('interval', '1m')
        window = self.config.get('window', 200)
        client = Client(BINANCE_PAPER_KEY, BINANCE_PAPER_SECRET)
        data_feed = BinanceLiveFeed.from_binance(client, symbol=symbol, interval=interval, window=window)
        self.run_backtrader_engine(data_feed)

    def execute_trade(self, trade_type, price, size):
        """Execute a trade and record it"""
        timestamp = datetime.now()
        
        if trade_type == 'buy':
            self.active_positions[self.trading_pair] = {
                'entry_price': price,
                'size': size,
                'entry_time': timestamp
            }
        else:  # sell
            if self.trading_pair in self.active_positions:
                position = self.active_positions[self.trading_pair]
                pnl = ((price - position['entry_price']) / position['entry_price']) * 100
                
                self.trade_history.append({
                    'bot_id': id(self),
                    'pair': self.trading_pair,
                    'type': 'long',
                    'entry_price': position['entry_price'],
                    'exit_price': price,
                    'size': position['size'],
                    'pl': pnl,
                    'time': timestamp.isoformat()
                })
                
                self.current_balance *= (1 + pnl/100)
                self.total_pnl += pnl
                del self.active_positions[self.trading_pair]
    
    def update_positions(self):
        """Update open positions"""
        for pair, position in list(self.active_positions.items()):
            # Check stop loss and take profit
            current_price = self.strategy.get_current_price(pair)
            entry_price = position['entry_price']
            
            # Calculate P/L
            pnl = ((current_price - entry_price) / entry_price) * 100
            
            # Check stop loss
            if pnl <= -self.strategy.sl_atr_mult * 100:
                self.execute_trade('sell', current_price, position['size'])
            
            # Check take profit
            elif pnl >= self.strategy.tp_atr_mult * 100:
                self.execute_trade('sell', current_price, position['size'])
    
    def stop(self):
        """Stop the bot"""
        self.is_running = False
        _logger.info(f"Stopping bot for {self.trading_pair}")
        # Optionally handle graceful shutdown

if __name__ == "__main__":
    # Example config for standalone run
    config = {
        'trading_pair': 'BTCUSDT',
        'initial_balance': 1000.0,
        'rsi_period': 14,
        'boll_period': 20,
        'boll_devfactor': 2.0,
        'atr_period': 14,
        'vol_ma_period': 20,
        'tp_atr_mult': 2.0,
        'sl_atr_mult': 1.0,
        'rsi_oversold': 30,
        'rsi_overbought': 70
    }
    bot = RsiBbVolumeBot(config)
    bot.run() 
    
    cerebro = bt.Cerebro()
    client = Client(BINANCE_PAPER_KEY, BINANCE_PAPER_SECRET)
    data = BinanceLiveFeed(symbol='LTCUSDC', timeframe='1m', client=client)
    cerebro.adddata(data)
    cerebro.addstrategy(BBSuperTrendVolumeBreakoutStrategy)
    cerebro.setbroker(BinancePaperBroker(BINANCE_PAPER_KEY, BINANCE_PAPER_SECRET, cash=1000.0))
    cerebro.run()
    