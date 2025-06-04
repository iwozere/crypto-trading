"""
Liquidity Momentum Strategy
--------------------------

This strategy combines liquidity ratio and momentum indicators to generate trading signals.
It uses:
1. Liquidity Ratio: Volume / Market Capitalization
2. Momentum: 5-day, 10-day, and 20-day returns
[5, 10, 20] - Short-term momentum (default)
[5, 10, 30] - Short to medium-term
[5, 15, 30] - Short to medium-term with different spacing
[10, 20, 30] - Medium-term momentum
[10, 20, 50] - Medium to long-term
[20, 50, 100] - Long-term momentum
3. Position Score: Average of standardized (z-score) versions of the above factors
4. Buy/Sell signals based on Position Score thresholds
"""

import backtrader as bt
import numpy as np
import pandas as pd
from src.strategy.base_strategy import BaseStrategy
from typing import Any, Dict, Optional
from src.analyzer.tickers_list import get_circulating_supply

class LiquidityMomentumStrategy(BaseStrategy):
    """
    Strategy that combines liquidity and momentum indicators for trading signals.
    
    Parameters:
    - buy_thresh: Threshold for buy signals (default: 0.5)
    - sell_thresh: Threshold for sell signals (default: -0.5)
    - lookback_period: Period for calculating z-scores (default: 252)
    - momentum_periods: List of periods for momentum calculation (default: [5, 10, 20])
    """
    
    def __init__(self, params: dict):
        super().__init__(params)
        
        # Strategy parameters
        self.buy_thresh = self.params.get('buy_thresh', 0.5)
        self.sell_thresh = self.params.get('sell_thresh', -0.5)
        self.lookback_period = self.params.get('lookback_period', 252)
        self.momentum_periods = self.params.get('momentum_periods', [5, 10, 20])
        
        # Initialize indicators
        self.volume = self.data.volume
        self.close = self.data.close
        
        # Calculate market cap (using circulating supply)
        self.supply = get_circulating_supply(self.data._name)
        self.market_cap = self.close * self.supply
        
        # Calculate liquidity ratio
        self.liquidity = bt.indicators.DivByZero(
            self.volume,
            self.market_cap,
            plot=False
        )
        
        # Calculate momentum returns
        self.momentum_returns = {}
        for period in self.momentum_periods:
            self.momentum_returns[period] = bt.indicators.PercentChange(
                self.close,
                period=period,
                plot=False
            )
        
        # Initialize position score
        self.position_score = bt.indicators.SMA(
            period=1,
            plot=False
        )
        
        # Trading state
        self.order = None
        self.entry_price = None
        self.trade_active = False
        
    def compute_position_score(self):
        """Calculate the position score based on z-scores of liquidity and momentum."""
        # Calculate z-scores for liquidity
        liquidity_mean = bt.indicators.SMA(self.liquidity, period=self.lookback_period)
        liquidity_std = bt.indicators.StandardDeviation(self.liquidity, period=self.lookback_period)
        z_liquidity = (self.liquidity - liquidity_mean) / liquidity_std
        
        # Calculate z-scores for momentum returns
        z_momentum = {}
        for period in self.momentum_periods:
            momentum_mean = bt.indicators.SMA(self.momentum_returns[period], period=self.lookback_period)
            momentum_std = bt.indicators.StandardDeviation(self.momentum_returns[period], period=self.lookback_period)
            z_momentum[period] = (self.momentum_returns[period] - momentum_mean) / momentum_std
        
        # Calculate average z-score
        z_scores = [z_liquidity] + list(z_momentum.values())
        self.position_score = bt.indicators.SMA(
            bt.indicators.SumN(z_scores, period=1) / len(z_scores),
            period=1
        )
    
    def next(self):
        """Main strategy logic."""
        # Skip if we have a pending order
        if self.order:
            return
            
        # Compute position score
        self.compute_position_score()
        
        # Check for entry/exit signals
        if not self.trade_active:
            # Entry logic
            if self.position_score[0] > self.buy_thresh:
                self.log(f'BUY CREATE, Price: {self.data.close[0]:.2f}, Score: {self.position_score[0]:.2f}')
                self.order = self.buy()
                self.trade_active = True
                self.entry_price = self.data.close[0]
                
                # Record trade entry
                trade_dict = {
                    'entry_time': self.data.datetime.datetime(),
                    'entry_price': self.entry_price,
                    'position_score': self.position_score[0],
                    'liquidity': self.liquidity[0],
                    'momentum_5d': self.momentum_returns[5][0],
                    'momentum_10d': self.momentum_returns[10][0],
                    'momentum_20d': self.momentum_returns[20][0]
                }
                self.record_trade(trade_dict)
                
        else:
            # Exit logic
            if self.position_score[0] < self.sell_thresh:
                self.log(f'SELL CREATE, Price: {self.data.close[0]:.2f}, Score: {self.position_score[0]:.2f}')
                self.order = self.sell()
                self.trade_active = False
                
                # Record trade exit
                trade_dict = {
                    'exit_time': self.data.datetime.datetime(),
                    'exit_price': self.data.close[0],
                    'pnl': (self.data.close[0] - self.entry_price) / self.entry_price * 100,
                    'position_score': self.position_score[0]
                }
                self.record_trade(trade_dict)
    
    def notify_order(self, order):
        """Handle order notifications."""
        if order.status in [order.Submitted, order.Accepted]:
            return
            
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY EXECUTED, Price: {order.executed.price:.2f}')
            elif order.issell():
                self.log(f'SELL EXECUTED, Price: {order.executed.price:.2f}')
                
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f'Order {order.getstatusname()}')
            
        self.order = None 