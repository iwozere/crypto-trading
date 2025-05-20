from typing import Dict, Optional
import pandas as pd
import numpy as np

class BaseStrategy:
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize base strategy with configuration parameters
        
        Args:
            config: Dictionary containing strategy parameters
        """
        self.config = self._get_default_config()
        if config:
            self.config.update(config)
            
        self.active_positions = {}
        self.trade_log = []

    def _get_default_config(self) -> Dict:
        """
        Get default configuration parameters
        
        Returns:
            Dict: Default configuration parameters
        """
        return {
            'risk_per_trade': 0.02,
            'take_profit_multiplier': 1.5,
            'stop_loss_multiplier': 2.5
        }

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
        risk_amount = portfolio_value * self.config['risk_per_trade']
        risk_per_unit = price - stop_loss
        position_size = risk_amount / risk_per_unit
        return position_size

    def get_active_positions(self) -> Dict:
        """
        Return currently active positions
        
        Returns:
            Dict: Active positions
        """
        return self.active_positions

    def check_entry_conditions(self, df: pd.DataFrame, symbol: str) -> bool:
        """
        Check if all entry conditions are met. To be implemented by child classes.
        
        Args:
            df: DataFrame with precalculated indicators
            symbol: Trading pair symbol
            
        Returns:
            bool: True if all conditions are met
        """
        raise NotImplementedError("Child classes must implement check_entry_conditions")

    def generate_signals(self, df: pd.DataFrame, symbol: str, portfolio_value: float) -> Dict:
        """
        Generate trading signals based on strategy rules. To be implemented by child classes.
        
        Args:
            df: DataFrame with precalculated indicators
            symbol: Trading pair symbol
            portfolio_value: Current portfolio value
            
        Returns:
            Dict: Trading signals with details
        """
        raise NotImplementedError("Child classes must implement generate_signals")

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate all required indicators. To be implemented by child classes.
        
        Args:
            df: DataFrame with price and volume data
            
        Returns:
            pd.DataFrame: DataFrame with calculated indicators
        """
        raise NotImplementedError("Child classes must implement calculate_indicators")

    def run_backtest(self, df: pd.DataFrame, symbol: str, initial_balance: float = 10000) -> pd.DataFrame:
        """
        Run backtest on historical data. To be implemented by child classes.
        
        Args:
            df: DataFrame with precalculated indicators
            symbol: Trading pair symbol
            initial_balance: Starting portfolio value
            
        Returns:
            pd.DataFrame: Trade log with all executed trades
        """
        raise NotImplementedError("Child classes must implement run_backtest") 
    
    def stop(self):
        pass

    def get_trades(self):
        """Return trade information as a DataFrame"""
        if not self.trades:
            return pd.DataFrame()
        return pd.DataFrame(self.trades)

    def on_error(self, error):
        """Called when an error occurs"""
        if self.notifier:
            self.notifier.send_error_notification(str(error))    
            
