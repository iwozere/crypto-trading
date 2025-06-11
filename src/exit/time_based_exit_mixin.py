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

from typing import Any, Dict

from src.exit.exit_mixin import BaseExitMixin


class TimeBasedExitMixin(BaseExitMixin):
    """Exit mixin based on time period"""

    # Define default values as class constants
    DEFAULT_TIME_PERIOD = 10
    DEFAULT_USE_CALENDAR_DAYS = False

    def __init__(self, params: Dict[str, Any]):
        super().__init__(params)
        self.time_period = params.get("time_period", self.DEFAULT_TIME_PERIOD)
        self.use_calendar_days = params.get("use_calendar_days", self.DEFAULT_USE_CALENDAR_DAYS)

    def get_required_params(self) -> list:
        """There are no required parameters - all have default values"""
        return []

    def get_default_params(self) -> Dict[str, Any]:
        """Default parameters"""
        return {
            "time_period": self.DEFAULT_TIME_PERIOD,
            "use_calendar_days": self.DEFAULT_USE_CALENDAR_DAYS,
        }

    def _init_indicators(self):
        """No indicators needed for time-based exit"""
        self.entry_bar = 0

    def should_exit(self, strategy) -> bool:
        """
        Exit logic: Exit after specified number of bars or calendar days
        """
        if not strategy.position:
            return False

        # Update entry bar if not set
        if self.entry_bar == 0:
            self.entry_bar = len(strategy)

        # Calculate elapsed time
        if self.use_calendar_days:
            # TODO: Implement calendar days calculation if needed
            elapsed = len(strategy) - self.entry_bar
        else:
            elapsed = len(strategy) - self.entry_bar

        # Exit if time period has elapsed
        return elapsed >= self.time_period
