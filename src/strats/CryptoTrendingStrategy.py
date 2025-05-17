import pandas as pd
import numpy as np
from typing import Tuple, Dict
from .BaseStrategy import BaseStrategy
import ta
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator
from ta.volatility import AverageTrueRange

class CryptoTrendStrategy(BaseStrategy):
    """
    A cryptocurrency trading strategy that combines multiple technical indicators to identify
    trend following opportunities with risk management. The strategy uses EMAs, SuperTrend,
    RSI, ATR, and volume indicators to generate trading signals.

    Strategy Parameters:
    -------------------
    atr_period (int): Period for ATR calculation (default: 14)
    atr_ma_period (int): Period for ATR moving average (default: 30)
    rsi_period (int): Period for RSI calculation (default: 14)
    rsi_threshold (float): RSI threshold for momentum (default: 50)
    supertrend_period (int): Period for SuperTrend calculation (default: 10)
    supertrend_multiplier (float): Multiplier for SuperTrend bands (default: 3)
    risk_per_trade (float): Maximum risk per trade as percentage of portfolio (default: 0.02)
    take_profit_multiplier (float): Multiplier for take profit calculation (default: 1.5)
    stop_loss_multiplier (float): Multiplier for stop loss calculation (default: 2.5)
    min_volume_multiplier (float): Minimum volume multiplier compared to average (default: 1.5)
    funding_rate_threshold (float): Maximum allowed funding rate for futures (default: 0.0001)
    commission (float): Trading commission as decimal (default: 0.001)

    Entry Criteria:
    --------------
    The strategy requires at least 4 out of 5 conditions to be met:

    1. Trend Conditions (any of the following):
       - Price above slow EMA
       - SuperTrend indicator is bullish (1)
       - Fast EMA above mid EMA

    2. Momentum Conditions (any of the following):
       - RSI above threshold (default: 50)
       - RSI is rising (current > previous)

    3. Volume Conditions:
       - Current volume above volume SMA * multiplier (default: 1.1)

    4. Volatility Conditions:
       - Current ATR above ATR moving average * 0.5

    5. Funding Rate Conditions (for futures):
       - Absolute funding rate below threshold (default: 0.0001)

    Exit Conditions:
    ---------------
    1. Stage 1 Exit (50% of position):
       - Take profit at entry price + (ATR * take_profit_multiplier)

    2. Stage 2 Exit (remaining 50%):
       - Trailing stop using the higher of:
         * SuperTrend stop level
         * Chandelier exit (price - ATR * 3)

    3. Emergency Exit:
       - Stop loss at entry price - (ATR * stop_loss_multiplier)

    Position Sizing:
    --------------
    - Position size is calculated based on risk per trade
    - Risk is defined as the distance between entry price and stop loss
    - Commission is factored into position size calculation

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
    - reason: exit reason ('take_profit_stage1', 'trailing_stop', 'stop_loss')
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
        'atr_period': 14,
        'atr_ma_period': 30,
        'rsi_period': 14,
        'rsi_threshold': 50,
        'supertrend_period': 10,
        'supertrend_multiplier': 3,
        'risk_per_trade': 0.02,
        'take_profit_multiplier': 1.5,
        'stop_loss_multiplier': 2.5,
        'min_volume_multiplier': 1.5,
        'funding_rate_threshold': 0.0001,
        'commission': 0.001
    }
    strategy = CryptoTrendStrategy(config)
    """
    def __init__(self, config: Dict = None):
        """
        Initialize strategy with configuration parameters
        
        Args:
            config: Dictionary containing strategy parameters
                   Example:
                   {
                       'atr_period': 14,
                       'atr_ma_period': 30,  # Period for ATR moving average
                       'rsi_period': 14,
                       'rsi_threshold': 50,  # RSI threshold for momentum
                       'supertrend_period': 10,  # Period for SuperTrend
                       'supertrend_multiplier': 3,  # Multiplier for SuperTrend
                       'risk_per_trade': 0.02,
                       'take_profit_multiplier': 1.5,
                       'stop_loss_multiplier': 2.5,
                       'commission': 0.001  # 0.1% commission per trade
                   }
        """
        super().__init__(config)
        self.active_positions = {}
        self.trade_log = []

    def _get_default_config(self) -> Dict:
        """
        Get default configuration parameters
        
        Returns:
            Dict: Default configuration parameters
        """
        return {
            'atr_period': 14,
            'atr_ma_period': 30,  # Period for ATR moving average
            'rsi_period': 14,
            'rsi_threshold': 50,  # RSI threshold for momentum
            'supertrend_period': 10,  # Period for SuperTrend
            'supertrend_multiplier': 3,  # Multiplier for SuperTrend
            'risk_per_trade': 0.02,
            'take_profit_multiplier': 1.5,
            'stop_loss_multiplier': 2.5,
            'min_volume_multiplier': 1.5,
            'funding_rate_threshold': 0.0001,
            'commission': 0.001  # 0.1% commission per trade
        }

    def check_entry_conditions(self, df: pd.DataFrame, symbol: str) -> bool:
        """
        Check if all entry conditions are met
        
        Args:
            df: DataFrame with precalculated indicators
            symbol: Trading pair symbol (e.g. 'BTCUSDT')
            
        Returns:
            bool: True if all conditions are met
        """
        if len(df) < 2:  # Need at least 2 rows for comparison
            return False
            
        last_row = df.iloc[-1]
        prev_row = df.iloc[-2]
        
        try:
            # Trend conditions - more relaxed
            trend_ok = any([  # Changed from all() to any()
                last_row['close'].item() > last_row['ema_slow'].item(),
                last_row['supertrend'].item() == 1,  # 1 = bullish, -1 = bearish
                last_row['ema_fast'].item() > last_row['ema_mid'].item()
            ])
            
            # Momentum conditions - more relaxed
            momentum_ok = any([  # Changed from all() to any()
                last_row['rsi'].item() > self.config['rsi_threshold'],
                last_row['rsi'].item() > prev_row['rsi'].item()  # Rising RSI
            ])
            
            # Volume conditions - more relaxed
            volume_ok = (
                last_row['volume'].item() > last_row['volume_sma'].item() * 1.1  # Reduced from 1.2
            )
            
            # Volatility condition - more relaxed
            atr_ma = df['atr'].rolling(self.config['atr_ma_period']).mean().iloc[-1].item()
            volatility_ok = last_row['atr'].item() > atr_ma * 0.5  # Reduced from 0.8
            
            # Funding rate check (for futures)
            funding_ok = True
            if 'funding_rate' in last_row:
                funding_ok = abs(last_row['funding_rate'].item()) <= self.config['funding_rate_threshold']
            
            # Require at least 2 conditions to be met
            conditions = [trend_ok, momentum_ok, volume_ok, volatility_ok, funding_ok]
            return sum(conditions) >= 4  # Changed from all() to sum() >= 2
            
        except (KeyError, AttributeError) as e:
            return False

    def calculate_position_size(self, price: float, stop_loss: float, portfolio_value: float) -> float:
        """
        Calculate position size based on risk management rules
        
        Args:
            price: Entry price
            stop_loss: Stop loss price
            portfolio_value: Total portfolio value
            
        Returns:
            float: Position size in quote currency
        """
        if price <= 0 or stop_loss <= 0 or portfolio_value <= 0:
            return 0.0
            
        risk_amount = portfolio_value * self.config['risk_per_trade']
        risk_per_unit = abs(price - stop_loss)
        
        if risk_per_unit == 0:
            return 0.0
            
        position_size = risk_amount / risk_per_unit
        
        # Adjust position size for commission
        commission_cost = position_size * price * self.config['commission']
        position_size = (position_size * price - commission_cost) / price
        
        return position_size

    def generate_signals(self, df: pd.DataFrame, symbol: str, portfolio_value: float) -> Dict:
        """
        Generate trading signals based on strategy rules
        
        Args:
            df: DataFrame with precalculated indicators
            symbol: Trading pair symbol
            portfolio_value: Current portfolio value
            
        Returns:
            Dict: Trading signals with details
        """
        signal = {'signal': None}
        
        # Check for new entry
        if symbol not in self.active_positions:
            if self.check_entry_conditions(df, symbol):
                last_row = df.iloc[-1]
                
                # Calculate stop loss based on ATR
                stop_loss = last_row['close'].item() - (last_row['atr'].item() * self.config['stop_loss_multiplier'])
                
                # Calculate position size
                position_size = self.calculate_position_size(
                    price=last_row['close'].item(),
                    stop_loss=stop_loss,
                    portfolio_value=portfolio_value
                )
                
                # Stage 1 take profit
                take_profit = last_row['close'].item() + (last_row['atr'].item() * self.config['take_profit_multiplier'])
                
                signal = {
                    'signal': 'buy',
                    'price': last_row['close'].item(),
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'size': position_size,
                    'timestamp': last_row.name,  # Assuming index is datetime
                    'stage1_completed': False
                }
                
                # Store active position
                self.active_positions[symbol] = signal.copy()
            
        # Check for exits on active positions
        elif symbol in self.active_positions:
            position = self.active_positions[symbol]
            last_row = df.iloc[-1]
            
            # Stage 1 exit (50% position)
            if not position['stage1_completed'] and last_row['close'].item() >= position['take_profit']:
                signal = {
                    'signal': 'sell',
                    'price': last_row['close'].item(),
                    'size': position['size'] * 0.5,
                    'reason': 'take_profit_stage1',
                    'timestamp': last_row.name
                }
                self.active_positions[symbol]['stage1_completed'] = True
                self.active_positions[symbol]['size'] *= 0.5  # Reduce remaining position
                
            # Stage 2 trailing stop
            elif position['stage1_completed']:
                current_trailing_stop = max(
                    last_row['supertrend_stop'].item(),
                    last_row['close'].item() - (last_row['atr'].item() * 3)  # Chandelier exit
                )
                
                if last_row['close'].item() <= current_trailing_stop:
                    signal = {
                        'signal': 'sell',
                        'price': last_row['close'].item(),
                        'size': self.active_positions[symbol]['size'],
                        'reason': 'trailing_stop',
                        'timestamp': last_row.name
                    }
                    del self.active_positions[symbol]  # Close position
                    
            # Emergency stop loss check
            elif last_row['close'].item() <= position['stop_loss']:
                signal = {
                    'signal': 'sell',
                    'price': last_row['close'].item(),
                    'size': position['size'],
                    'reason': 'stop_loss',
                    'timestamp': last_row.name
                }
                del self.active_positions[symbol]
                
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
        
        # Create a copy of the DataFrame to avoid modifying the original
        df = df.copy()
        
        # Fill NaN values with 0 to avoid comparison issues
        df = df.fillna(0)
        
        for i in range(1, len(df)):
            current_df = df.iloc[:i+1].copy()  # Create a copy of the lookback window
            signal = self.generate_signals(current_df, symbol, portfolio_value)
            
            if signal['signal'] == 'buy':
                # Skip if price or size is invalid
                if signal['price'] <= 0 or signal['size'] <= 0:
                    continue
                    
                # Calculate commission for entry
                commission = signal['size'] * signal['price'] * self.config['commission']
                
                # Execute buy order
                trade = {
                    'timestamp': signal['timestamp'],
                    'symbol': symbol,
                    'signal': 'buy',
                    'price': signal['price'],
                    'size': signal['size'],
                    'commission': commission,
                    'portfolio_value': portfolio_value - commission
                }
                trade_log.append(trade)
                portfolio_value -= commission
                
            elif signal['signal'] == 'sell':
                # Skip if price or size is invalid
                if signal['price'] <= 0 or signal['size'] <= 0:
                    continue
                    
                # Calculate commission for exit
                commission = signal['size'] * signal['price'] * self.config['commission']
                
                # Calculate PnL including commission
                entry_price = trade_log[-1]['price']
                if entry_price <= 0:
                    continue
                    
                entry_commission = trade_log[-1]['commission']
                exit_commission = commission
                
                # Calculate raw PnL
                raw_pnl = (signal['price'] / entry_price - 1) * 100
                
                # Adjust PnL for commissions
                total_commission_pct = ((entry_commission + exit_commission) / (entry_price * signal['size'])) * 100
                adjusted_pnl = raw_pnl - total_commission_pct
                
                # Execute sell order
                trade = {
                    'timestamp': signal['timestamp'],
                    'symbol': symbol,
                    'signal': 'sell',
                    'price': signal['price'],
                    'size': signal['size'],
                    'commission': commission,
                    'reason': signal['reason'],
                    'raw_pnl': raw_pnl,
                    'commission_pct': total_commission_pct,
                    'pnl': adjusted_pnl,
                    'portfolio_value': portfolio_value - commission
                }
                trade_log.append(trade)
                
                # Update portfolio value
                if signal['reason'] == 'stop_loss':
                    portfolio_value -= portfolio_value * self.config['risk_per_trade']
                else:
                    portfolio_value += (signal['price'] - trade_log[-2]['price']) * signal['size'] - commission
        
        self.trade_log = pd.DataFrame(trade_log)
        return self.trade_log

    def get_active_positions(self) -> Dict:
        """Return currently active positions"""
        return self.active_positions

    def get_trade_log(self) -> pd.DataFrame:
        """Return complete trade history"""
        return self.trade_log

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate all required indicators
        
        Args:
            df: DataFrame with price and volume data
            
        Returns:
            pd.DataFrame: DataFrame with calculated indicators
        """
        # Create a copy of the DataFrame to avoid modifying the original
        df = df.copy()
        
        # Replace zeros with small values to avoid division by zero
        df['close'] = df['close'].replace(0, 0.0001)
        df['high'] = df['high'].replace(0, 0.0001)
        df['low'] = df['low'].replace(0, 0.0001)
        df['volume'] = df['volume'].replace(0, 0.0001)
        
        # Calculate EMAs
        ema_slow = EMAIndicator(close=df['close'], window=self.config['ema_slow'])
        ema_mid = EMAIndicator(close=df['close'], window=self.config['ema_mid'])
        ema_fast = EMAIndicator(close=df['close'], window=self.config['ema_fast'])
        df['ema_slow'] = ema_slow.ema_indicator()
        df['ema_mid'] = ema_mid.ema_indicator()
        df['ema_fast'] = ema_fast.ema_indicator()
        
        # Calculate RSI
        rsi = RSIIndicator(close=df['close'], window=self.config['rsi_period'])
        df['rsi'] = rsi.rsi()
        
        # Calculate ATR
        atr = AverageTrueRange(high=df['high'], low=df['low'], close=df['close'], window=self.config['atr_period'])
        df['atr'] = atr.average_true_range()
        
        # Calculate SuperTrend
        df['supertrend'], df['supertrend_stop'] = self.calculate_supertrend(
            df, self.config['supertrend_period'], self.config['supertrend_multiplier']
        )
        
        # Calculate Volume SMA
        df['volume_sma'] = df['volume'].rolling(self.config['volume_sma']).mean()
        
        # Drop rows with any NaN values
        df = df.dropna()
        
        return df

    def calculate_supertrend(self, df: pd.DataFrame, period: int, multiplier: float) -> Tuple[pd.Series, pd.Series]:
        """Calculate SuperTrend indicator"""
        # Convert to numpy arrays for faster computation
        high = df['high'].values
        low = df['low'].values
        close = df['close'].values
        
        # Calculate ATR
        atr_indicator = AverageTrueRange(high=df['high'], low=df['low'], close=df['close'], window=period)
        atr = atr_indicator.average_true_range().values
        
        # Calculate basic upper and lower bands
        hl2 = (high + low) / 2
        upper = hl2 + (multiplier * atr)
        lower = hl2 - (multiplier * atr)
        
        # Initialize arrays
        supertrend = np.ones(len(df))
        supertrend_stop = np.copy(lower)
        
        # Calculate SuperTrend
        for i in range(1, len(df)):
            if close[i] > upper[i-1]:
                supertrend[i] = 1
            elif close[i] < lower[i-1]:
                supertrend[i] = -1
            else:
                supertrend[i] = supertrend[i-1]
                
            if supertrend[i] == 1:
                supertrend_stop[i] = lower[i]
            else:
                supertrend_stop[i] = upper[i]
        
        # Convert back to pandas Series
        supertrend = pd.Series(supertrend, index=df.index)
        supertrend_stop = pd.Series(supertrend_stop, index=df.index)
        
        return supertrend, supertrend_stop