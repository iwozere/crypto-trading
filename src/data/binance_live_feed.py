"""
Provides a Backtrader-compatible live data feed using Binance API and Pandas.

This module defines BinanceLiveFeed, a custom Backtrader data feed that fetches and updates live market data from Binance for algorithmic trading.
"""
import pandas as pd
import time
import backtrader as bt

class BinanceLiveFeed(bt.feeds.PandasData):
    def __init__(self, client, symbol='BTCUSDT', interval='1m', window=200):
        self.client = client
        self.symbol = symbol
        self.interval = interval
        self.window = window
        self.df = self.fetch()
        super().__init__(dataname=self.df)

    def fetch(self):
        bars = self.client.get_klines(symbol=self.symbol, interval=self.interval, limit=self.window)
        df = pd.DataFrame(bars, columns=[
            'datetime', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
        ])
        df['datetime'] = pd.to_datetime(df['datetime'], unit='ms')
        df.set_index('datetime', inplace=True)
        df = df.astype(float)
        return df

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
