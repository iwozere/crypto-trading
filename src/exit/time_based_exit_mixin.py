"""
Time-based Exit Mixin

This module implements an exit strategy based on time duration. The strategy exits a position
after a specified number of bars or calendar days have elapsed since entry.

Parameters:
    time_period (int): Number of bars to hold position (default: 10)
    use_calendar_days (bool): Whether to use calendar days instead of bars (default: False)

This strategy is useful for:
1. Limiting exposure time in the market
2. Implementing time-based profit taking
3. Preventing positions from being held too long in ranging markets
4. Managing overnight risk by closing positions before market close

Note: When use_calendar_days is True, the strategy will need to be adapted to handle
calendar day calculations based on the data feed's timeframe.
"""

from typing import Any, Dict, Optional

from src.exit.base_exit_mixin import BaseExitMixin
from src.notification.logger import setup_logger

logger = setup_logger(__name__)


class TimeBasedExitMixin(BaseExitMixin):
    """Exit mixin based on time"""

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """Initialize the mixin with parameters"""
        super().__init__(params)
        self.entry_bar = None
        self.entry_time = None

    def get_required_params(self) -> list:
        """There are no required parameters - all have default values"""
        return []

    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        """Default parameters"""
        return {
            "x_max_bars": 20,
            "x_use_time": False,
            "x_max_minutes": 60,
        }

    def _init_indicators(self):
        """Initialize time-based exit indicators"""
        if not hasattr(self, "strategy"):
            return

    def should_exit(self) -> bool:
        """Check if we should exit a position"""
        if not self.strategy.position:
            return False

        current_time = self.strategy.data.datetime.datetime(0)
        entry_time = self.strategy.current_trade.get("entry_time")
        if self.get_param("x_use_time", False):
            time_diff = (current_time - entry_time).total_seconds() / 60
            return_value = time_diff >= self.get_param("x_max_minutes")
        else:
            bars_held = len(self.strategy.data) - self.strategy.trade.dtopen
            return_value = bars_held >= self.get_param("x_max_bars")

        if return_value:
            if self.get_param("x_use_time", False):
                logger.debug(
                    f"EXIT: Price: {self.strategy.data.close[0]}, "
                    f"Time held: {time_diff:.2f} minutes, "
                    f"Max time: {self.get_param('x_max_minutes')} minutes"
                )
                self.strategy.current_exit_reason = "time_limit_minutes"
                self.entry_time = current_time
            else:
                logger.debug(
                    f"EXIT: Price: {self.strategy.data.close[0]}, "
                    f"Bars held: {bars_held}, "
                    f"Max bars: {self.get_param('x_max_bars')}"
                )
                self.strategy.current_exit_reason = "time_limit_bars"
                self.entry_bar = 0
        return return_value

    def next(self):
        """Called for each new bar"""
        super().next()
        if self.get_param("x_use_time", False) == False and self.entry_bar is not None:
            self.entry_bar += 1

    def notify_trade(self, trade):
        if trade.isclosed:
            self.entry_bar = None
        else:
            self.entry_bar = 0
