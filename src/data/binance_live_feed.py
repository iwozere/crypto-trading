"""
Binance Live Feed Module
-----------------------

This module provides a Backtrader-compatible live data feed using the Binance API and Pandas. It enables real-time market data streaming for algorithmic trading strategies by integrating Binance's websocket or REST endpoints with the Backtrader framework.

Main Features:
- Fetch and update live OHLCV data from Binance
- Integrate with Backtrader as a custom data feed
- Support for periodic data refresh and event-driven updates

Classes:
- BinanceLiveFeed: Custom Backtrader data feed for live Binance market data
"""
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import pandas as pd
import time
import backtrader as bt

class BinanceLiveFeed(bt.feeds.PandasData):
    @classmethod
    def from_binance(cls, client, symbol='BTCUSDT', interval='1m', window=200, **kwargs):
        bars = client.get_klines(symbol=symbol, interval=interval, limit=window)
        df = pd.DataFrame(bars, columns=[
            'datetime', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
        ])
        df['datetime'] = pd.to_datetime(df['datetime'], unit='ms')
        df.set_index('datetime', inplace=True)
        df = df.astype(float)
        return cls(dataname=df, **kwargs)

    def _load(self):
        time.sleep(60)
        new_df = self.fetch()
        if not new_df.equals(self.df):
            self.df = new_df
            latest = self.df.iloc[-1]
            self.lines.datetime[0] = bt.date2num(self.df.index[-1])
            self.lines.open[0] = latest['open']
            self.lines.high[0] = latest['high']
            self.lines.low[0] = latest['low']
            self.lines.close[0] = latest['close']
            self.lines.volume[0] = latest['volume']
            self.lines.openinterest[0] = 0
            return True
        return None
