"""
Run Optimizers Script
-------------------

This script runs all optimizer configurations for each strategy with different exit logics.
It processes each strategy's configurations sequentially and saves results in separate directories.
"""

# Add project root to Python path
import os
import sys
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(project_root)

import json
import logging
import datetime
from src.notification.logger import _logger
from src.optimizer.optimizer_registry import OPTIMIZER_CONFIGS




def load_config(config_path):
    """Load configuration from JSON file."""
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except Exception as e:
        _logger.error(f"Error loading config {config_path}: {str(e)}")
        return None


def run_optimizer(strategy_name, optimizer_class, config_path):
    """Run a single optimizer with the given configuration."""
    try:
        _logger.info(f"Running {strategy_name} with config: {config_path}")

        # Load configuration
        config = load_config(config_path)
        if not config:
            return

        # Create optimizer instance
        optimizer = optimizer_class(config)

        # Run optimization
        optimizer.run_optimization()

        _logger.info(f"Completed {strategy_name} with config: {config_path}")

    except Exception as e:
        _logger.error(
            f"Error running {strategy_name} with config {config_path}: {str(e)}"
        )


def run_optimizers():
    """Run all optimizers with their respective configurations."""
    start_time = datetime.datetime.now()
    _logger.info(f"Starting optimization at {start_time}")

    # Get the config directory
    config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "optimizer")

    # Run each optimizer with its configurations
    for strategy_name, optimizer_info in OPTIMIZER_CONFIGS.items():
        _logger.info(f"\nProcessing {strategy_name} strategy...")
        
        optimizer_class = optimizer_info["class"]
        config_files = optimizer_info["configs"]
        
        for config_file in config_files:
            config_path = os.path.join(config_dir, config_file)
            try:
                _logger.info(f"Loading configuration from {config_file}")
                with open(config_path, 'r') as f:
                    config = json.load(f)
                
                _logger.info(f"Initializing {optimizer_class.__name__}")
                optimizer = optimizer_class(config)
                
                _logger.info("Starting optimization...")
                optimizer.run_optimization()
                
            except Exception as e:
                _logger.error(f"Error processing {config_file}: {str(e)}")
                continue

    end_time = datetime.datetime.now()
    duration = end_time - start_time
    _logger.info(f"\nOptimization completed at {end_time}")
    _logger.info(f"Total duration: {duration}")


if __name__ == "__main__":
    run_optimizers()
