"""
Base exit logic class for trading strategies. All custom exit logics should inherit from this base class.

Exit Reason Values:
    - "TP": Take Profit - Price reached the take profit level
    - "SL": Stop Loss - Price reached the stop loss level
    - "TS": Trailing Stop - Price fell below the trailing stop level
    - "TB": Time Based - Maximum time period elapsed
    - "MA": Moving Average - Price crossed below the moving average
"""

from src.strategy.base_strategy import BaseStrategy


class BaseExitLogic:
    def __init__(self, strategy : BaseStrategy, params=None):
        self.params = params or {}
        self.entry_price = None

    def initialize(self, entry_price, **kwargs):
        """
        Initialize the exit logic with entry price and any additional parameters.

        Args:
            entry_price (float): The entry price for the trade
            **kwargs: Additional parameters needed by specific exit logic implementations
        """
        self.entry_price = entry_price

    def check_exit(self, current_price):
        """
        Check if an exit condition is met.

        Args:
            current_price (float): Current price

        Returns:
            tuple: (bool, str) - (should_exit, exit_reason)
                - should_exit (bool): True if exit condition is met, False otherwise
                - exit_reason (str): Reason for exit, one of:
                    - "TP": Take Profit
                    - "SL": Stop Loss
                    - "TS": Trailing Stop
                    - "TB": Time Based
                    - "MA": Moving Average
        """
        raise NotImplementedError

    def next(self, **kwargs):
        """
        Called on each new bar to update exit logic state.
        This method should be overridden by exit logic implementations that need to update their state
        on each bar (e.g., updating ATR values, moving averages, etc.).
        
        It should be called on each new bar after check_exit is called.

        Args:
            **kwargs: Additional data needed by specific exit logic implementations.
                     For example:
                     - atr_value: Current ATR value for ATR-based exits
                     - ma_value: Current moving average value for MA-based exits
                     - time_elapsed: Time elapsed since entry for time-based exits
        """
        pass

