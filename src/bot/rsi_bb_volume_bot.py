import os
import time
import json
import logging
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from binance.client import Client
from binance.exceptions import BinanceAPIException
from src.strats.rsi_bb_volume_strategy import RSIBollVolumeATRStrategy
from config.donotshare.donotshare import BINANCE_KEY, BINANCE_SECRET
from src.bot.base_trading_bot import BaseTradingBot

class RsiBbVolumeBot(BaseTradingBot):
    def __init__(self, config):
        strategy = RSIBollVolumeATRStrategy(
            rsi_period=config.get('rsi_period', 14),
            boll_period=config.get('boll_period', 20),
            boll_devfactor=config.get('boll_devfactor', 2.0),
            atr_period=config.get('atr_period', 14),
            vol_ma_period=config.get('vol_ma_period', 20),
            tp_atr_mult=config.get('tp_atr_mult', 2.0),
            sl_atr_mult=config.get('sl_atr_mult', 1.0),
            rsi_oversold=config.get('rsi_oversold', 30),
            rsi_overbought=config.get('rsi_overbought', 70)
        )
        super().__init__(config, strategy)

    def run(self):
        """Main bot loop"""
        self.is_running = True
        print(f"Starting bot for {self.trading_pair}")
        
        while self.is_running:
            try:
                # Get trading signals
                signals = self.strategy.get_signals(self.trading_pair)
                
                # Process signals
                for signal in signals:
                    if signal['type'] == 'buy' and self.trading_pair not in self.active_positions:
                        self.execute_trade('buy', signal['price'], signal['size'])
                    elif signal['type'] == 'sell' and self.trading_pair in self.active_positions:
                        self.execute_trade('sell', signal['price'], signal['size'])
                
                # Update positions
                self.update_positions()
                
                # Sleep to prevent excessive API calls
                time.sleep(1)
                
            except Exception as e:
                print(f"Error in bot loop: {str(e)}")
                time.sleep(5)
    
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
        print(f"Stopping bot for {self.trading_pair}")
        
        # Close all open positions
        for pair in list(self.active_positions.keys()):
            current_price = self.strategy.get_current_price(pair)
            self.execute_trade('sell', current_price, self.active_positions[pair]['size'])

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