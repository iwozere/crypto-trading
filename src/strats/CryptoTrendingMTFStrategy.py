import pandas as pd
import numpy as np
import talib as ta
from typing import Dict, List
from .BaseStrategy import BaseStrategy

class MultiTimeframeTrendStrategy(BaseStrategy):
    def _get_default_config(self) -> Dict:
        """
        Get default configuration parameters
        
        Returns:
            Dict: Default configuration parameters
        """
        return {
            # Core 4H Parameters
            'ema_slow': 200,
            'ema_fast': 20,
            'ema_mid': 50,
            'supertrend_period': 10,
            'supertrend_multiplier': 3,
            'atr_period': 14,
            'rsi_period': 14,
            'volume_sma_period': 20,
            
            # Multi-Timeframe Confirmation
            'use_1h_confirmation': True,
            '1h_ema_fast': 12,  # Faster EMA for 1H
            
            # Risk Management
            'risk_per_trade': 0.02,
            'initial_sl_multiplier': 2.8,
            'tp_stage1_multiplier': 1.8,
            'trailing_sl_multiplier': 3,
            
            # Time Filters
            'trade_hours': (4, 20),  # 04:00-20:00 UTC
            'reduce_weekend_size': True
        }

    def calculate_indicators(self, df_4h: pd.DataFrame, df_1h: pd.DataFrame = None) -> pd.DataFrame:
        """Precompute all required indicators"""
        # 4H Indicators
        df_4h['ema_slow'] = ta.EMA(df_4h['close'], self.config['ema_slow'])
        df_4h['ema_fast'] = ta.EMA(df_4h['close'], self.config['ema_fast'])
        df_4h['ema_mid'] = ta.EMA(df_4h['close'], self.config['ema_mid'])
        df_4h['atr'] = ta.ATR(df_4h['high'], df_4h['low'], df_4h['close'], self.config['atr_period'])
        df_4h['rsi'] = ta.RSI(df_4h['close'], self.config['rsi_period'])
        df_4h['volume_sma'] = df_4h['volume'].rolling(self.config['volume_sma_period']).mean()
        
        # SuperTrend Implementation
        df_4h['supertrend'] = self._calculate_supertrend(df_4h)
        
        # 1H Confirmation Indicators (if enabled)
        if self.config['use_1h_confirmation'] and df_1h is not None:
            df_1h['ema_fast'] = ta.EMA(df_1h['close'], self.config['1h_ema_fast'])
            df_4h['1h_confirmation'] = self._align_1h_confirmation(df_4h, df_1h)
        
        return df_4h

    def _calculate_supertrend(self, df: pd.DataFrame) -> pd.Series:
        """Calculate SuperTrend indicator"""
        hl2 = (df['high'] + df['low']) / 2
        atr = ta.ATR(df['high'], df['low'], df['close'], self.config['supertrend_period'])
        
        upper = hl2 + (self.config['supertrend_multiplier'] * atr)
        lower = hl2 - (self.config['supertrend_multiplier'] * atr)
        
        supertrend = pd.Series(np.nan, index=df.index)
        direction = pd.Series(1, index=df.index)
        
        for i in range(1, len(df)):
            if df['close'].iloc[i] > upper.iloc[i-1]:
                direction.iloc[i] = 1
            elif df['close'].iloc[i] < lower.iloc[i-1]:
                direction.iloc[i] = -1
            else:
                direction.iloc[i] = direction.iloc[i-1]
                
            if direction.iloc[i] == 1:
                supertrend.iloc[i] = lower.iloc[i]
            else:
                supertrend.iloc[i] = upper.iloc[i]
                
        return supertrend

    def _align_1h_confirmation(self, df_4h: pd.DataFrame, df_1h: pd.DataFrame) -> pd.Series:
        """Generate 1H confirmation signals aligned to 4H candles"""
        confirmation = pd.Series(False, index=df_4h.index)
        
        for i in range(len(df_4h)):
            # Get all 1H candles within the current 4H candle
            start_time = df_4h.index[i]
            end_time = start_time + pd.Timedelta(hours=4)
            mask = (df_1h.index >= start_time) & (df_1h.index < end_time)
            hourly_candles = df_1h[mask]
            
            # Require at least 3/4 1H candles to confirm
            if len(hourly_candles) >= 3:
                confirmed = sum(hourly_candles['close'] > hourly_candles['ema_fast']) >= 3
                confirmation.iloc[i] = confirmed
                
        return confirmation

    def check_entry_conditions(self, df: pd.DataFrame, symbol: str) -> bool:
        """Check all 4H entry conditions"""
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        # Trend Conditions
        trend_ok = (last['close'] > last['ema_slow']) and \
                   (last['ema_fast'] > last['ema_mid']) and \
                   (last['ema_fast'] > prev['ema_fast'])
        
        # Momentum Conditions
        mom_ok = (last['rsi'] > 52) and \
                 (last['rsi'] > prev['rsi'])
        
        # Volume & Volatility
        vol_ok = (last['volume'] > last['volume_sma'] * 1.7)
        atr_ok = (last['atr'] > df['atr'].rolling(30).mean().iloc[-1] * 1.2)
        
        # Time Filters
        hour = last.name.hour  # Assuming index is datetime
        time_ok = self.config['trade_hours'][0] <= hour <= self.config['trade_hours'][1]
        
        # Weekend Sizing
        weekend_adjust = True
        if self.config['reduce_weekend_size'] and last.name.weekday() >= 4:
            weekend_adjust = 0.5  # Reduce size on weekends
            
        # 1H Confirmation (if enabled)
        mtf_ok = True
        if self.config['use_1h_confirmation']:
            mtf_ok = last.get('1h_confirmation', False)
            
        return all([trend_ok, mom_ok, vol_ok, atr_ok, time_ok, mtf_ok]) * weekend_adjust

    def generate_signals(self, df: pd.DataFrame, symbol: str, portfolio_value: float) -> Dict:
        """Generate trading signal with multi-timeframe confirmation"""
        signal = {'signal': None}
        
        if self.check_entry_conditions(df, symbol):
            last = df.iloc[-1]
            atr = last['atr']
            
            # Position Sizing
            stop_loss = last['close'] - (atr * self.config['initial_sl_multiplier'])
            stop_loss = max(stop_loss, df['low'].rolling(5).min().iloc[-1])  # Protect against swing lows
            
            position_size = self.calculate_position_size(
                last['close'], 
                stop_loss, 
                portfolio_value
            )
            
            # Apply weekend reduction if needed
            if last.name.weekday() >= 4 and self.config['reduce_weekend_size']:
                position_size *= 0.5
                
            signal = {
                'symbol': symbol,
                'signal': 'buy',
                'price': last['close'],
                'size': position_size,
                'stop_loss': stop_loss,
                'take_profit': last['close'] + (atr * self.config['tp_stage1_multiplier']),
                'timestamp': last.name,
                'atr': atr,
                'supertrend': last['supertrend']
            }
            
        return signal

    def run_backtest(self, df: pd.DataFrame, symbol: str, initial_balance: float = 10000) -> pd.DataFrame:
        """
        Run backtest on historical data
        
        Args:
            df: DataFrame with precalculated indicators
            symbol: Trading pair symbol
            initial_balance: Starting portfolio value
            
        Returns:
            pd.DataFrame: Trade log with all executed trades
        """
        portfolio_value = initial_balance
        trade_log = []
        
        for i in range(1, len(df)):
            current_df = df.iloc[:i+1]  # Lookback window
            signal = self.generate_signals(current_df, symbol, portfolio_value)
            
            if signal['signal'] == 'buy':
                # Execute buy order
                trade = {
                    'timestamp': signal['timestamp'],
                    'symbol': symbol,
                    'action': 'buy',
                    'price': signal['price'],
                    'size': signal['size'],
                    'portfolio_value': portfolio_value
                }
                trade_log.append(trade)
                
            elif signal['signal'] == 'sell':
                # Execute sell order
                trade = {
                    'timestamp': signal['timestamp'],
                    'symbol': symbol,
                    'action': 'sell',
                    'price': signal['price'],
                    'size': signal['size'],
                    'reason': signal.get('reason', 'take_profit'),
                    'pnl': (signal['price'] / trade_log[-1]['price'] - 1) * 100,
                    'portfolio_value': portfolio_value
                }
                trade_log.append(trade)
                
                # Update portfolio value
                if signal.get('reason') == 'stop_loss':
                    portfolio_value -= portfolio_value * self.config['risk_per_trade']
                else:
                    portfolio_value += (signal['price'] - trade_log[-2]['price']) * signal['size']
        
        self.trade_log = pd.DataFrame(trade_log)
        return self.trade_log

# Example Usage
if __name__ == "__main__":
    # Load your 4H and 1H data (example)
    df_4h = pd.read_csv('btc_4h.csv', parse_dates=['timestamp'], index_col='timestamp')
    df_1h = pd.read_csv('btc_1h.csv', parse_dates=['timestamp'], index_col='timestamp')
    
    strategy = MultiTimeframeTrendStrategy({
        'risk_per_trade': 0.02,
        'use_1h_confirmation': True
    })
    
    # Precompute indicators
    df_4h = strategy.calculate_indicators(df_4h, df_1h)
    
    # Generate signal
    signal = strategy.generate_signals(df_4h, 'BTCUSDT', 10000)
    print(signal)