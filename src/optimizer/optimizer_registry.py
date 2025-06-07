import json
import logging
import os
import sys
from datetime import datetime

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(project_root)

from src.optimizer.bb_volume_supertrend_optimizer import BBSuperTrendVolumeBreakoutOptimizer
from src.optimizer.ichimoku_rsi_volume_optimizer import IchimokuRsiVolumeOptimizer
from src.optimizer.rsi_bb_optimizer import RsiBbOptimizer
from src.optimizer.rsi_bb_volume_optimizer import RsiBollVolumeOptimizer
from src.optimizer.rsi_volume_supertrend_optimizer import RsiVolumeSuperTrendOptimizer

# Define optimizer classes and their corresponding config patterns
OPTIMIZER_CONFIGS = {
    "RSI Bollinger Volume": {
        "class": RsiBollVolumeOptimizer,
        "configs": [
            "rsi_boll_volume_atr_exit_optimizer.json",
            "rsi_boll_volume_fixed_sl_tp_exit_optimizer.json",
            "rsi_boll_volume_ma_crossover_exit_optimizer.json",
            "rsi_boll_volume_time_based_exit_optimizer.json",
            "rsi_boll_volume_trailing_stop_exit_optimizer.json",
        ],
    },
    "BB Volume Supertrend": {
        "class": BBSuperTrendVolumeBreakoutOptimizer,
        "configs": [
            "bb_volume_supertrend_atr_exit_optimizer.json",
            "bb_volume_supertrend_fixed_sl_tp_exit_optimizer.json",
            "bb_volume_supertrend_ma_crossover_exit_optimizer.json",
            "bb_volume_supertrend_time_based_exit_optimizer.json",
            "bb_volume_supertrend_trailing_stop_exit_optimizer.json",
        ],
    },
    "Ichimoku RSI Volume": {
        "class": IchimokuRsiVolumeOptimizer,
        "configs": [
            "ichimoku_rsi_volume_atr_exit_optimizer.json",
            "ichimoku_rsi_volume_fixed_sl_tp_exit_optimizer.json",
            "ichimoku_rsi_volume_ma_crossover_exit_optimizer.json",
            "ichimoku_rsi_volume_time_based_exit_optimizer.json",
            "ichimoku_rsi_volume_trailing_stop_exit_optimizer.json",
        ],
    },
    "RSI BB": {
        "class": RsiBbOptimizer,
        "configs": [
            "rsi_bb_atr_exit_optimizer.json",
            "rsi_bb_fixed_sl_tp_exit_optimizer.json",
            "rsi_bb_ma_crossover_exit_optimizer.json",
            "rsi_bb_time_based_exit_optimizer.json",
            "rsi_bb_trailing_stop_exit_optimizer.json",
        ],
    },
    "RSI Volume Supertrend": {
        "class": RsiVolumeSuperTrendOptimizer,
        "configs": [
            "rsi_volume_supertrend_atr_exit_optimizer.json",
            "rsi_volume_supertrend_fixed_sl_tp_exit_optimizer.json",
            "rsi_volume_supertrend_ma_crossover_exit_optimizer.json",
            "rsi_volume_supertrend_time_based_exit_optimizer.json",
            "rsi_volume_supertrend_trailing_stop_exit_optimizer.json",
        ],
    },
}
