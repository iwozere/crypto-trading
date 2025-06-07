"""
Strategy Registry
-----------------
Central registry for all available trading strategy classes, with metadata.
Allows dynamic lookup and instantiation by name, and provides descriptions and default parameters.
"""

from src.strategy.bb_volume_supertrend_strategy import \
    BBSuperTrendVolumeBreakoutStrategy
from src.strategy.ichimoku_rsi_volume_strategy import IchimokuRsiVolumeStrategy
from src.strategy.liquidity_momentum_strategy import LiquidityMomentumStrategy
from src.strategy.rsi_bb_strategy import MeanReversionRsiBbStrategy
from src.strategy.rsi_bb_volume_strategy import RsiBollVolumeStrategy
from src.strategy.rsi_volume_supertrend_strategy import \
    RsiVolumeSuperTrendStrategy

STRATEGY_REGISTRY = {
    "MeanReversionRsiBbStrategy": {
        "class": MeanReversionRsiBbStrategy,
        "description": "RSI + Bollinger Bands mean reversion strategy for ranging/sideways markets.",
        "default_params": {
            "bb_period": 20,
            "bb_devfactor": 2.0,
            "rsi_period": 14,
            "rsi_oversold": 30,
            "rsi_overbought": 70,
            "rsi_mid_level": 50,
            "atr_period": 14,
            "tp_atr_mult": 1.5,
            "sl_atr_mult": 1.0,
            "trail_atr_mult": 2.0,
            "printlog": False,
            "check_rsi_slope": False,
            "notify": False,
        },
    },
    "RsiBollVolumeStrategy": {
        "class": RsiBollVolumeStrategy,
        "description": "RSI + Bollinger Bands + Volume mean reversion strategy with pluggable exit logic.",
        "default_params": {
            "rsi_period": 14,
            "boll_period": 20,
            "boll_devfactor": 2.0,
            "vol_ma_period": 20,
            "rsi_oversold": 30,
            "rsi_overbought": 70,
            "printlog": False,
            "notify": False,
        },
    },
    "BBSuperTrendVolumeBreakoutStrategy": {
        "class": BBSuperTrendVolumeBreakoutStrategy,
        "description": "Bollinger Bands + SuperTrend + Volume breakout strategy for volatile markets.",
        "default_params": {
            "bb_period": 20,
            "bb_devfactor": 2.0,
            "st_period": 10,
            "st_multiplier": 3.0,
            "vol_ma_period": 20,
            "vol_strength_mult": 1.5,
            "atr_period": 14,
            "tp_atr_mult": 2.0,
            "sl_atr_mult": 1.0,
            "printlog": False,
            "notify": False,
        },
    },
    "RsiVolumeSuperTrendStrategy": {
        "class": RsiVolumeSuperTrendStrategy,
        "description": "SuperTrend + RSI + Volume trend-following strategy with ATR-based exits.",
        "default_params": {
            "rsi_period": 14,
            "rsi_entry_long_level": 40.0,
            "rsi_entry_short_level": 60.0,
            "rsi_exit_long_level": 70.0,
            "rsi_exit_short_level": 30.0,
            "st_period": 10,
            "st_multiplier": 3.0,
            "vol_ma_period": 10,
            "atr_period": 14,
            "tp_atr_mult": 2.0,
            "sl_atr_mult": 1.5,
            "time_based_exit_period": 5,
            "printlog": False,
            "notify": False,
        },
    },
    "IchimokuRsiVolumeStrategy": {
        "class": IchimokuRsiVolumeStrategy,
        "description": "Ichimoku Cloud + RSI + Volume strategy for trend and volume confirmation.",
        "default_params": {
            "tenkan_period": 9,
            "kijun_period": 26,
            "senkou_span_b_period": 52,
            "rsi_period": 14,
            "rsi_entry": 50,
            "atr_period": 14,
            "atr_mult": 2.0,
            "vol_ma_period": 20,
            "printlog": False,
            "notify": False,
        },
    },
    "LiquidityMomentumStrategy": {
        "class": LiquidityMomentumStrategy,
        "description": "Momentum-based strategy using volume profile and liquidity analysis.",
        "default_params": {
            "atr_period": 14,
            "vol_ma_period": 20,
            "volume_threshold": 1.5,
            "printlog": False,
            "notify": False,
        },
    },
    # Add new strategies here as needed
}


def get_strategy_info(name: str):
    """Get strategy info dict (class, description, default_params) by registry name."""
    return STRATEGY_REGISTRY.get(name)
