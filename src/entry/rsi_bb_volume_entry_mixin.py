"""
RSI, Bollinger Bands, and Volume Entry Mixin

This module implements an entry strategy based on the combination of:
1. RSI (Relative Strength Index)
2. Bollinger Bands
3. Volume analysis

The strategy enters a position when:
1. RSI is oversold
2. Price is below the lower Bollinger Band
3. Volume is above its moving average

Parameters:
    rsi_period (int): Period for RSI calculation (default: 14)
    rsi_oversold (float): Oversold threshold for RSI (default: 30)
    bb_period (int): Period for Bollinger Bands calculation (default: 20)
    bb_stddev (float): Standard deviation multiplier for Bollinger Bands (default: 2.0)
    volume_ma_period (int): Period for volume moving average (default: 20)
    use_bb_touch (bool): Whether to use Bollinger Band touch for entry (default: True)

This strategy combines mean reversion (RSI and BB) with volume confirmation
to identify potential reversal points with strong momentum.
"""

from typing import Any, Dict, Optional

import backtrader as bt
from src.entry.base_entry_mixin import BaseEntryMixin
from src.indicator.talib_bb import TALibBB
from src.indicator.talib_rsi import TALibRSI
from src.indicator.talib_sma import TALibSMA
from src.notification.logger import setup_logger

logger = setup_logger(__name__)

class RSIBBVolumeEntryMixin(BaseEntryMixin):
    """Entry mixin based on RSI, Bollinger Bands, and Volume"""

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """Initialize the mixin with parameters"""
        super().__init__(params)
        self.rsi_name = 'entry_rsi'
        self.bb_name = 'entry_bb'
        self.vol_ma_name = 'entry_volume_ma'

    def get_required_params(self) -> list:
        """There are no required parameters - all have default values"""
        return []

    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        """Default parameters"""
        return {
            "rsi_period": 14,
            "rsi_oversold": 30,
            "bb_period": 20,
            "bb_stddev": 2.0,
            "volume_ma_period": 20,
            "use_bb_touch": True,
        }

    def _init_indicators(self):
        """Initialize indicators"""
        logger.debug("RSIBBVolumeEntryMixin._init_indicators called")
        if not hasattr(self, 'strategy'):
            logger.error("No strategy available in _init_indicators")
            return

        try:
            data = self.strategy.data
            use_talib = self.strategy.use_talib
            logger.debug(f"Initializing indicators with use_talib={use_talib}")

            # Calculate required data length based on indicator periods
            required_length = max(
                self.get_param("rsi_period"),
                self.get_param("bb_period"),
                self.get_param("volume_ma_period")
            )
            logger.debug(f"Required data length: {required_length}, Current data length: {len(data)}")

            # Ensure we have enough data
            if len(data) <= required_length:
                logger.debug(f"Not enough data yet. Need {required_length} bars, have {len(data)}")
                return

            if use_talib:
                # Use TA-Lib for RSI
                logger.debug("Creating TA-Lib RSI indicator")
                rsi = TALibRSI(
                    data,
                    period=self.get_param("rsi_period")
                )
                logger.debug("Registering TA-Lib RSI indicator")
                self.register_indicator(self.rsi_name, rsi)

                # Use TA-Lib for Bollinger Bands
                logger.debug("Creating TA-Lib BB indicator")
                bb = TALibBB(
                    data,
                    period=self.get_param("bb_period"),
                    devfactor=self.get_param("bb_stddev")
                )
                logger.debug("Registering TA-Lib BB indicator")
                self.register_indicator(self.bb_name, bb)

                # Use TA-Lib for Volume MA
                logger.debug("Creating TA-Lib Volume MA indicator")
                vol_ma = TALibSMA(
                    data.volume,
                    period=self.get_param("volume_ma_period")
                )
                logger.debug("Registering TA-Lib Volume MA indicator")
                self.register_indicator(self.vol_ma_name, vol_ma)
            else:
                # Use Backtrader's native RSI
                logger.debug("Creating Backtrader RSI indicator")
                rsi = bt.indicators.RSI(
                    data,
                    period=self.get_param("rsi_period")
                )
                logger.debug("Registering Backtrader RSI indicator")
                self.register_indicator(self.rsi_name, rsi)

                # Use Backtrader's native Bollinger Bands
                logger.debug("Creating Backtrader BB indicator")
                bb = bt.indicators.BollingerBands(
                    data,
                    period=self.get_param("bb_period"),
                    devfactor=self.get_param("bb_stddev")
                )
                logger.debug("Registering Backtrader BB indicator")
                self.register_indicator(self.bb_name, bb)

                # Use Backtrader's native SMA for Volume
                logger.debug("Creating Backtrader Volume MA indicator")
                vol_ma = bt.indicators.SMA(
                    data.volume,
                    period=self.get_param("volume_ma_period")
                )
                logger.debug("Registering Backtrader Volume MA indicator")
                self.register_indicator(self.vol_ma_name, vol_ma)
        except Exception as e:
            logger.error(f"Error initializing indicators: {e}")
            raise

    def should_enter(self) -> bool:
        """
        Entry logic: RSI oversold, Bollinger Bands conditions, and Volume confirmation
        """
        if not all(hasattr(self.strategy, name) for name in [self.rsi_name, self.bb_name, self.vol_ma_name]):
            return False

        current_price = self.strategy.data.close[0]
        current_volume = self.strategy.data.volume[0]
        
        rsi = getattr(self.strategy, self.rsi_name)
        bb = getattr(self.strategy, self.bb_name)
        vol_ma = getattr(self.strategy, self.vol_ma_name)

        # Check RSI
        rsi_condition = rsi[0] <= self.get_param("rsi_oversold")

        # Check Bollinger Bands
        bb_condition = not self.get_param("use_bb_touch") or current_price <= bb.bb_lower[0] * 1.01  # Small tolerance

        # Check volume
        volume_condition = current_volume > vol_ma[0]

        return_value = rsi_condition and bb_condition and volume_condition
        if return_value:
            logger.debug(f"ENTRY: Price: {current_price}, RSI: {rsi[0]}, BB Lower: {bb.bb_lower[0]}, Volume: {current_volume}, Volume MA: {vol_ma[0]}")
        return return_value
