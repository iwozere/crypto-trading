"""
Run Optimizers Script
-------------------

This script runs all optimizer configurations for each strategy with different exit logics.
It processes each strategy's configurations sequentially and saves results in separate directories.
"""

import json
import logging
import os
import sys
from datetime import datetime

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(project_root)

from src.optimizer.bb_volume_supertrend_optimizer import \
    BBSuperTrendVolumeBreakoutOptimizer
from src.optimizer.ichimoku_rsi_volume_optimizer import \
    IchimokuRsiVolumeOptimizer
from src.optimizer.rsi_bb_optimizer import RsiBbOptimizer
from src.optimizer.rsi_bb_volume_optimizer import RsiBBVolumeOptimizer
from src.optimizer.rsi_volume_supertrend_optimizer import \
    RsiVolumeSuperTrendOptimizer

# Configure logging
log_dir = os.path.join("logs", "log")
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(
            os.path.join(
                log_dir, f'optimization_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
            )
        ),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# Define optimizer classes and their corresponding config patterns
OPTIMIZER_CONFIGS = {
    "RSI BB Volume": {
        "class": RsiBBVolumeOptimizer,
        "configs": [
            "rsi_bb_volume_atr_exit_optimizer.json",
            "rsi_bb_volume_fixed_sl_tp_exit_optimizer.json",
            "rsi_bb_volume_ma_crossover_exit_optimizer.json",
            "rsi_bb_volume_time_based_exit_optimizer.json",
            "rsi_bb_volume_trailing_stop_exit_optimizer.json",
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
            "rsi_bb_exit_optimizer.json",
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


def load_config(config_path):
    """Load configuration from JSON file."""
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading config {config_path}: {str(e)}")
        return None


def run_optimizer(strategy_name, optimizer_class, config_path):
    """Run a single optimizer with the given configuration."""
    try:
        logger.info(f"Running {strategy_name} with config: {config_path}")

        # Load configuration
        config = load_config(config_path)
        if not config:
            return

        # Create optimizer instance
        optimizer = optimizer_class(config)

        # Run optimization
        optimizer.run_optimization()

        logger.info(f"Completed {strategy_name} with config: {config_path}")

    except Exception as e:
        logger.error(
            f"Error running {strategy_name} with config {config_path}: {str(e)}"
        )


def main():
    """Main function to run all optimizers."""
    logger.info("Starting optimization runs")

    for strategy_name, strategy_info in OPTIMIZER_CONFIGS.items():
        logger.info(f"\nProcessing strategy: {strategy_name}")

        for config_file in strategy_info["configs"]:
            config_path = os.path.join("config", "optimizer", config_file)
            run_optimizer(strategy_name, strategy_info["class"], config_path)

    logger.info("Completed all optimization runs")


if __name__ == "__main__":
    main()
