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

import backtrader as bt
from src.exit.base_exit_mixin import BaseExitMixin


class TimeBasedExitMixin(BaseExitMixin):
    """Exit mixin based on time"""

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """Initialize the mixin with parameters"""
        super().__init__(params)
        self.entry_bar = 0

    def get_required_params(self) -> list:
        """There are no required parameters - all have default values"""
        return []

    def get_default_params(self) -> Dict[str, Any]:
        """Default parameters"""
        return {
            "max_bars": 20,
            "use_time": False,
            "max_minutes": 60,
        }

    def _init_indicators(self):
        """Initialize time-based exit indicators"""
        if not hasattr(self, 'strategy'):
            return

    def should_exit(self) -> bool:
        """Check if we should exit a position"""
        if not self.strategy.position:
            return False

        if self.get_param("use_time", False):
            current_time = self.strategy.data.datetime.datetime(0)
            entry_time = self.strategy.position.dtopen
            time_diff = (current_time - entry_time).total_seconds() / 60
            return time_diff >= self.get_param("max_minutes")
        else:
            bars_held = len(self.strategy.data) - self.strategy.position.dtopen
            return bars_held >= self.get_param("max_bars")
