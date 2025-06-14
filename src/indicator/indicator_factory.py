"""
Indicator Factory Module

This module provides a factory for creating and managing indicators, supporting both
Backtrader native indicators and TA-Lib indicators. It ensures proper data handling
and indicator lifecycle management.
"""

from typing import Any, Dict, Optional
import backtrader as bt
from src.notification.logger import setup_logger

# Import TA-Lib indicators
from src.indicator.talib_rsi import TALibRSI
from src.indicator.talib_bb import TALibBB
from src.indicator.talib_atr import TALibATR
from src.indicator.talib_sma import TALibSMA

# Import Backtrader indicators
from backtrader.indicators import RSI, BollingerBands, ATR, SMA

logger = setup_logger(__name__)

class IndicatorFactory:
    """Factory for creating and managing indicators"""

    def __init__(self, data: bt.DataBase, use_talib: bool = False):
        """
        Initialize the indicator factory
        
        Args:
            data: Backtrader data feed
            use_talib: Whether to use TA-Lib indicators
        """
        self.data = data
        self.use_talib = use_talib
        self.indicators = {}
        logger.debug(f"IndicatorFactory initialized with use_talib={use_talib}")

    def create_rsi(self, name: str, period: int = 14) -> Any:
        """Create RSI indicator"""
        if name in self.indicators:
            return self.indicators[name]

        logger.debug(f"Creating {'TA-Lib' if self.use_talib else 'Backtrader'} RSI indicator")
        if self.use_talib:
            indicator = TALibRSI(self.data, period=period)
        else:
            indicator = RSI(self.data, period=period)
        
        self.indicators[name] = indicator
        return indicator

    def create_bollinger_bands(self, name: str, period: int = 20, devfactor: float = 2.0) -> Any:
        """Create Bollinger Bands indicator"""
        if name in self.indicators:
            return self.indicators[name]

        logger.debug(f"Creating {'TA-Lib' if self.use_talib else 'Backtrader'} Bollinger Bands indicator")
        if self.use_talib:
            indicator = TALibBB(self.data, period=period, devfactor=devfactor)
        else:
            indicator = BollingerBands(self.data, period=period, devfactor=devfactor)
        
        self.indicators[name] = indicator
        return indicator

    def create_atr(self, name: str, period: int = 14) -> Any:
        """Create ATR indicator"""
        if name in self.indicators:
            return self.indicators[name]

        logger.debug(f"Creating {'TA-Lib' if self.use_talib else 'Backtrader'} ATR indicator")
        if self.use_talib:
            indicator = TALibATR(self.data, period=period)
        else:
            indicator = ATR(self.data, period=period)
        
        self.indicators[name] = indicator
        return indicator

    def create_sma(self, name: str, period: int = 20) -> Any:
        """Create SMA indicator"""
        if name in self.indicators:
            return self.indicators[name]

        logger.debug(f"Creating {'TA-Lib' if self.use_talib else 'Backtrader'} SMA indicator")
        if self.use_talib:
            indicator = TALibSMA(self.data, period=period)
        else:
            indicator = SMA(self.data, period=period)
        
        self.indicators[name] = indicator
        return indicator

    def get_indicator(self, name: str) -> Optional[Any]:
        """Get an indicator by name"""
        return self.indicators.get(name)

    def has_indicator(self, name: str) -> bool:
        """Check if an indicator exists"""
        return name in self.indicators 