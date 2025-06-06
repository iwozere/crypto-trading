import os
import sys
import json
import logging
from datetime import datetime

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(project_root)

from src.optimizer.rsi_bb_volume_optimizer import RsiBBVolumeOptimizer
from src.optimizer.bb_volume_supertrend_optimizer import BBSuperTrendVolumeBreakoutOptimizer
from src.optimizer.ichimoku_rsi_atr_volume_optimizer import IchimokuRSIATRVolumeOptimizer
from src.optimizer.rsi_bb_atr_optimizer import MeanReversionRSBBATROptimizer
from src.optimizer.rsi_volume_supertrend_optimizer import RsiVolumeSuperTrendOptimizer


# Define optimizer classes and their corresponding config patterns
OPTIMIZER_CONFIGS = {
    'RSI BB Volume': {
        'class': RsiBBVolumeOptimizer,
        'configs': [
            'rsi_bb_volume_atr_exit_optimizer.json',
            'rsi_bb_volume_fixed_sl_tp_exit_optimizer.json',
            'rsi_bb_volume_ma_crossover_exit_optimizer.json',
            'rsi_bb_volume_time_based_exit_optimizer.json',
            'rsi_bb_volume_trailing_stop_exit_optimizer.json'
        ]
    },
    'BB Volume Supertrend': {
        'class': BBSuperTrendVolumeBreakoutOptimizer,
        'configs': [
            'bb_volume_supertrend_atr_exit_optimizer.json',
            'bb_volume_supertrend_fixed_sl_tp_exit_optimizer.json',
            'bb_volume_supertrend_ma_crossover_exit_optimizer.json',
            'bb_volume_supertrend_time_based_exit_optimizer.json',
            'bb_volume_supertrend_trailing_stop_exit_optimizer.json'
        ]
    },
    'Ichimoku RSI ATR Volume': {
        'class': IchimokuRSIATRVolumeOptimizer,
        'configs': [
            'ichimoku_rsi_atr_volume_atr_exit_optimizer.json',
            'ichimoku_rsi_atr_volume_fixed_sl_tp_exit_optimizer.json',
            'ichimoku_rsi_atr_volume_ma_crossover_exit_optimizer.json',
            'ichimoku_rsi_atr_volume_time_based_exit_optimizer.json',
            'ichimoku_rsi_atr_volume_trailing_stop_exit_optimizer.json'
        ]
    },
    'RSI BB ATR': {
        'class': MeanReversionRSBBATROptimizer,
        'configs': [
            'rsi_bb_atr_atr_exit_optimizer.json',
            'rsi_bb_atr_fixed_sl_tp_exit_optimizer.json',
            'rsi_bb_atr_ma_crossover_exit_optimizer.json',
            'rsi_bb_atr_time_based_exit_optimizer.json',
            'rsi_bb_atr_trailing_stop_exit_optimizer.json'
        ]
    },
    'RSI Volume Supertrend': {
        'class': RsiVolumeSuperTrendOptimizer,
        'configs': [
            'rsi_volume_supertrend_atr_exit_optimizer.json',
            'rsi_volume_supertrend_fixed_sl_tp_exit_optimizer.json',
            'rsi_volume_supertrend_ma_crossover_exit_optimizer.json',
            'rsi_volume_supertrend_time_based_exit_optimizer.json',
            'rsi_volume_supertrend_trailing_stop_exit_optimizer.json'
        ]
    }
}
