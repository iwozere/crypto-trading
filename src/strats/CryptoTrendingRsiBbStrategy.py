import pandas as pd
import numpy as np
from typing import Tuple, Dict
from .BaseStrategy import BaseStrategy
import ta
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands, AverageTrueRange
from ta.volume import VolumeWeightedAveragePrice, OnBalanceVolumeIndicator

class CryptoTrendingRsiBbStrategy(BaseStrategy):
    """
    A cryptocurrency trading strategy that combines RSI, Bollinger Bands, and volume indicators
    to identify trading opportunities. The strategy uses RSI for momentum, Bollinger Bands for
    volatility and trend, and volume for confirmation. It uses only 1 position at a time. 
    Position cannot be sold until there is a bought position.
    It uses a fixed risk per trade of 1% of portfolio.
    

    Strategy Parameters:
    -------------------
    rsi_period (int): Period for RSI calculation (default: 14)
    rsi_oversold (float): RSI threshold for oversold condition (default: 30)
    rsi_overbought (float): RSI threshold for overbought condition (default: 70)
    bb_period (int): Period for Bollinger Bands calculation (default: 20)
    bb_std (float): Standard deviation multiplier for Bollinger Bands (default: 2.0)
    volume_period (int): Period for volume moving average (default: 20)
    volume_threshold (float): Minimum volume multiplier compared to average (default: 1.5)
    risk_per_trade (float): Maximum risk per trade as percentage of portfolio (default: 0.02)
    atr_period (int): ATR period for adaptive take profit and stop loss (default: 14)
    atr_tp_multiplier (float): Take profit multiplier for ATR (default: 2.0)
    atr_sl_multiplier (float): Stop loss multiplier for ATR (default: 1.0)
    commission (float): Trading commission as decimal (default: 0.001)

    Entry Criteria:
    --------------
    The strategy requires all of the following conditions to be met:

    1. RSI Conditions:
       - RSI below oversold threshold (default: 30)
       - RSI starting to rise (current > previous)

    2. Bollinger Bands Conditions:
       - Price below lower Bollinger Band
       - Bollinger Band width expanding

    3. Volume Conditions:
       - Current volume above volume SMA * threshold

    Exit Conditions:
    ---------------
    1. Take Profit:
       - Price reaches middle Bollinger Band
       - RSI reaches overbought threshold (default: 70)

    2. Stop Loss:
       - Price drops below lower Bollinger Band
       - RSI drops below previous low

    Position Sizing:
    --------------
    - Position size is calculated based on risk per trade
    - Risk is defined as the distance between entry price and stop loss
    - Commission is factored into position size calculation
    - Risk per trade is 1% of portfolio

    Trade Object Structure:
    ---------------------
    Each trade in the trade log contains the following fields:
    - timestamp: datetime of the trade
    - symbol: trading pair (e.g., 'BTCUSDT')
    - signal: 'buy' or 'sell'
    - price: absolute price at execution
    - size: absolute position size in quote currency
    - commission: absolute commission amount in quote currency
    - portfolio_value: absolute portfolio value after trade
    - reason: exit reason ('take_profit', 'stop_loss')
    - raw_pnl: percentage return before commissions
    - commission_pct: percentage commission cost
    - pnl: percentage return after commissions

    Metrics Structure:
    ----------------
    The strategy tracks the following metrics:
    - total_profit: absolute profit/loss in quote currency
    - num_trades: absolute number of completed trades
    - win_rate: percentage of profitable trades (0-100%)
    - sharpe_ratio: risk-adjusted return metric (absolute value)
    - max_drawdown: maximum percentage drawdown from peak
    - min_time_between_trades: minimum hours between trades
    - max_time_between_trades: maximum hours between trades
    - avg_time_between_trades: average hours between trades

    Example Usage:
    -------------
    config = {
        'rsi_period': 14,
        'rsi_oversold': 30,
        'rsi_overbought': 70,
        'bb_period': 20,
        'bb_std': 2.0,
        'volume_period': 20,
        'volume_threshold': 1.5,
        'risk_per_trade': 0.02,
        'atr_period': 14,
        'atr_tp_multiplier': 2.0,
        'atr_sl_multiplier': 1.0,
        'commission': 0.001
    }
    strategy = CryptoTrendingRsiBbStrategy(config)
    """
    def __init__(self, config: Dict = None):
        """
        Initialize strategy with configuration parameters
        
        Args:
            config: Dictionary containing strategy parameters
                   Example:
                   {
                       'rsi_period': 14,
                       'rsi_oversold': 30,
                       'rsi_overbought': 70,
                       'bb_period': 20,
                       'bb_std': 2.0,
                       'volume_period': 20,
                       'volume_threshold': 1.5,
                       'risk_per_trade': 0.02,
                       'atr_period': 14,
                       'atr_tp_multiplier': 2.0,
                       'atr_sl_multiplier': 1.0,
                       'commission': 0.001  # 0.1% commission per trade
                   }
        """
        super().__init__(config)
        self.active_positions = {}  # Dictionary to track multiple active positions
        self.trade_log = []

    def _get_default_config(self) -> Dict:
        """
        Get default configuration parameters
        
        Returns:
            Dict: Default configuration parameters
        """
        return {
            'rsi_period': 14,
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'bb_period': 20,
            'bb_std': 2.0,
            'volume_period': 20,
            'volume_threshold': 1.5,
            'risk_per_trade': 0.02,
            'atr_period': 14,
            'atr_tp_multiplier': 2.0,
            'atr_sl_multiplier': 1.0,
            'commission': 0.001  # 0.1% commission per trade
        }

    def check_entry_conditions(self, df: pd.DataFrame) -> bool:
        """
        Check if entry conditions are met
        
        Args:
            df: DataFrame with precalculated indicators
            
        Returns:
            bool: True if entry conditions are met, False otherwise
        """
        if len(df) < 2:  # Need at least 2 rows for comparison
            return False
            
        current_row = df.iloc[-1]
        previous_row = df.iloc[-2]
        
        # RSI condition: RSI is below oversold threshold or starting to rise from oversold
        rsi_ok = (current_row['rsi'] < self.config['rsi_oversold'] and current_row['rsi'] > previous_row['rsi'])
        
        # Bollinger Bands condition: Price is below 
        bb_ok = current_row['close'] < current_row['bb_low']
        
        # Volume condition: Current volume is above threshold or increasing
        volume_ok = (current_row['volume'] > current_row['volume_ma'] * 1.1 or
                    current_row['volume'] > previous_row['volume'] * 1.2)
        
        # Require at least 2 conditions to be met
        conditions = [rsi_ok, bb_ok, volume_ok]
        return sum(conditions) >= 2

    def calculate_position_size(self, price: float, portfolio_value: float) -> float:
        """
        Calculate position size based on risk management rules
        
        Args:
            price: Current price of the asset
            portfolio_value: Current portfolio value
            
        Returns:
            float: Position size in base currency
        """
        # Calculate risk amount (1% of portfolio)
        risk_amount = portfolio_value * 0.01
        
        # Calculate position size based on risk amount
        position_size = risk_amount / price
        
        return position_size

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate all required indicators
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            pd.DataFrame: DataFrame with added indicators
        """
        # Create a copy of the DataFrame to avoid modifying the original
        df = df.copy()
        
        # Calculate RSI
        rsi = RSIIndicator(
            close=df['close'],
            window=self.config['rsi_period']
        )
        df['rsi'] = rsi.rsi()
        
        # Calculate Bollinger Bands
        bb = BollingerBands(
            close=df['close'],
            window=self.config['bb_period'],
            window_dev=self.config['bb_std']
        )
        df['bb_high'] = bb.bollinger_hband()
        df['bb_mid'] = bb.bollinger_mavg()
        df['bb_low'] = bb.bollinger_lband()
        
        # Calculate ATR
        atr = AverageTrueRange(
            high=df['high'],
            low=df['low'],
            close=df['close'],
            window=self.config['atr_period']
        )
        df['atr'] = atr.average_true_range()
        
        # Calculate Volume indicators
        df['volume_ma'] = df['volume'].rolling(self.config['volume_period']).mean()
        
        # Calculate On-Balance Volume (OBV)
        obv = OnBalanceVolumeIndicator(
            close=df['close'],
            volume=df['volume']
        )
        df['obv'] = obv.on_balance_volume()
        
        # Fill NaN values with 0
        df = df.fillna(0)
        
        return df

    def generate_signals(self, df: pd.DataFrame, symbol: str, portfolio_value: float) -> dict:
        """
        Generate trading signals based on indicators
        
        Args:
            df: DataFrame with precalculated indicators
            symbol: Trading pair symbol
            portfolio_value: Current portfolio value
            
        Returns:
            dict: Signal information including timestamp, signal type, price, and size
        """
        if len(df) < 2:  # Need at least 2 rows for comparison
            return {'signal': None}
            
        current_row = df.iloc[-1]
        previous_row = df.iloc[-2]
        
        # Check entry conditions for new positions
        # Only generate buy signal if there's no active position for this symbol
        if symbol not in self.active_positions and self.check_entry_conditions(df):
            # Calculate position size
            size = self.calculate_position_size(current_row['close'], portfolio_value)
            
            # Calculate take profit and stop loss levels based on ATR
            atr = current_row['atr']
            entry_price = current_row['close']
            take_profit = entry_price + (self.config['atr_tp_multiplier'] * atr)
            stop_loss = entry_price - (self.config['atr_sl_multiplier'] * atr)
            
            return {
                'signal': 'buy',
                'price': entry_price,
                'size': size,
                'timestamp': df.index[-1],
                'take_profit': take_profit,
                'stop_loss': stop_loss
            }
            
        # Check exit conditions for existing positions
        elif symbol in self.active_positions:
            position = self.active_positions[symbol]
            current_price = current_row['close']
            atr = current_row['atr']
            
            # Update sliding stop loss if price moves in our favor
            if current_price > position['entry_price']:
                new_stop_loss = current_price - (self.config['atr_sl_multiplier'] * atr)
                if new_stop_loss > position['stop_loss']:
                    position['stop_loss'] = new_stop_loss
            
            # Check if stop loss is hit
            if current_price <= position['stop_loss']:
                return {
                    'signal': 'sell',
                    'price': current_price,
                    'size': position['size'],
                    'reason': 'stop_loss',
                    'timestamp': df.index[-1]
                }
            
            # Check if take profit is hit
            if current_price >= position['take_profit']:
                return {
                    'signal': 'sell',
                    'price': current_price,
                    'size': position['size'],
                    'reason': 'take_profit',
                    'timestamp': df.index[-1]
                }
                
        return {'signal': None}

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
        
        # Create a copy of the DataFrame to avoid modifying the original
        df = df.copy()
        
        # Fill NaN values with 0 to avoid comparison issues
        df = df.fillna(0)
        
        # Process each row
        for i in range(len(df)):
            current_data = df.iloc[:i+1]
            if len(current_data) < 2:  # Need at least 2 rows for comparison
                continue
                
            # Generate signals
            signal = self.generate_signals(current_data, symbol, portfolio_value)
            
            if signal['signal'] is not None:
                current_timestamp = current_data.index[-1]
                
                # Execute trade
                if signal['signal'] == 'buy':
                    # Calculate commission
                    commission = signal['price'] * signal['size'] * self.config['commission']
                    
                    # Update portfolio value
                    portfolio_value -= (signal['price'] * signal['size'] + commission)
                    
                    # Store active position with take profit and stop loss levels
                    self.active_positions[symbol] = {
                        'price': signal['price'],
                        'size': signal['size'],
                        'timestamp': current_timestamp,
                        'entry_price': signal['price'],
                        'take_profit': signal['take_profit'],
                        'stop_loss': signal['stop_loss']
                    }
                    
                    # Log trade
                    trade_log.append({
                        'timestamp': current_timestamp,
                        'symbol': symbol,
                        'signal': 'buy',
                        'price': signal['price'],
                        'size': signal['size'],
                        'commission': commission,
                        'portfolio_value': portfolio_value,
                        'raw_pnl': 0.0,
                        'commission_pct': (commission / (signal['price'] * signal['size'])) * 100,
                        'pnl': -((commission / (signal['price'] * signal['size'])) * 100)  # Initial PnL is negative due to commission
                    })
                    
                elif signal['signal'] == 'sell':
                    # Calculate commission
                    commission = signal['price'] * signal['size'] * self.config['commission']
                    
                    # Calculate PnL
                    entry_price = self.active_positions[symbol]['price']
                    raw_pnl = ((signal['price'] - entry_price) / entry_price) * 100
                    commission_pct = (commission / (signal['price'] * signal['size'])) * 100
                    pnl = raw_pnl - commission_pct
                    
                    # Update portfolio value
                    portfolio_value += (signal['price'] * signal['size'] - commission)
                    
                    # Log trade
                    trade_log.append({
                        'timestamp': current_timestamp,
                        'symbol': symbol,
                        'signal': 'sell',
                        'price': signal['price'],
                        'size': signal['size'],
                        'commission': commission,
                        'raw_pnl': raw_pnl,
                        'commission_pct': commission_pct,
                        'pnl': pnl,
                        'reason': signal.get('reason', ''),
                        'portfolio_value': portfolio_value
                    })
                    
                    # Remove active position
                    del self.active_positions[symbol]
        
        # Convert trade log to DataFrame
        trade_log_df = pd.DataFrame(trade_log)
        if not trade_log_df.empty:
            # Ensure timestamp is properly formatted but keep it as a regular column
            trade_log_df['timestamp'] = pd.to_datetime(trade_log_df['timestamp'])
            
        return trade_log_df

    def get_active_positions(self) -> Dict:
        """Get currently active positions"""
        return self.active_positions

    def get_trade_log(self) -> pd.DataFrame:
        """Get trade log as DataFrame"""
        return pd.DataFrame(self.trade_log)