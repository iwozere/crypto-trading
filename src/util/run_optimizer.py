"""
Run Optimizer Module

This module provides functionality to run optimizations for trading strategies.
It handles:
1. Loading and preparing data
2. Running optimizations for different entry/exit strategy combinations
3. Saving results and plots
4. Managing visualization settings
"""

import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import json
from datetime import datetime as dt

import backtrader as bt
import optuna
import pandas as pd
from src.entry.entry_mixin_factory import (ENTRY_MIXIN_REGISTRY)
from src.exit.exit_mixin_factory import (EXIT_MIXIN_REGISTRY)
from src.notification.logger import _logger
from src.optimizer.custom_optimizer import CustomOptimizer
from src.util.date_time_encoder import DateTimeEncoder
from src.plotter.indicators.rsi_plotter import RSIPlotter
from src.plotter.indicators.ichimoku_plotter import IchimokuPlotter
from src.plotter.indicators.bollinger_bands_plotter import BollingerBandsPlotter
from src.plotter.indicators.volume_plotter import VolumePlotter
from src.plotter.indicators.supertrend_plotter import SuperTrendPlotter
from src.plotter.base_plotter import BasePlotter


def prepare_data(data_file):
    """Load and prepare data from CSV file"""
    # Load and prepare data
    df = pd.read_csv(os.path.join("data", data_file))
    print("Available columns:", df.columns.tolist())

    # Find datetime column
    datetime_col = None
    for col in ["datetime", "date", "time", "timestamp"]:
        if col in df.columns:
            datetime_col = col
            break

    if datetime_col:
        df["datetime"] = pd.to_datetime(df[datetime_col])
    else:
        # If no datetime column found, create one from index
        df["datetime"] = pd.date_range(start="2020-01-01", periods=len(df), freq="1min")

    # Ensure all required columns exist
    required_columns = ["open", "high", "low", "close", "volume"]
    for col in required_columns:
        if col not in df.columns:
            raise ValueError(f"Required column '{col}' not found in data file")

    # Set datetime as index
    df.set_index("datetime", inplace=True)
    
    # Create Backtrader data feed
    data = bt.feeds.PandasData(
        dataname=df,
        open="open",
        high="high",
        low="low",
        close="close",
        volume="volume",
        openinterest=-1,
    )
    return data


def get_result_filename(data_file, entry_logic_name, exit_logic_name, suffix=""):
    """Generate a standardized filename for results and plots"""
    # Extract symbol, interval, and dates from data_file
    symbol = "SYMBOL"
    interval = "INTERVAL"
    start_date = "STARTDATE"
    end_date = "ENDDATE"

    if "_" in data_file:
        parts = data_file.replace(".csv", "").split("_")
        if len(parts) >= 4:  # We expect at least symbol_interval_startdate_enddate
            symbol = parts[0]
            interval = parts[1]
            start_date = parts[2]
            end_date = parts[3]

    timestamp = dt.now().strftime("%Y%m%d_%H%M%S")
    return f"{symbol}_{interval}_{start_date}_{end_date}_{entry_logic_name}_{exit_logic_name}_{timestamp}{suffix}"


def save_results(results, data_file):
    """Save optimization results to JSON file"""
    output_file_name = get_result_filename(
        data_file,
        entry_logic_name=results["best_params"]["entry_logic"]["name"],
        exit_logic_name=results["best_params"]["exit_logic"]["name"],
        suffix="",
    )
    output_file = os.path.join("results", f"{output_file_name}.json")
    os.makedirs("results", exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(results, f, indent=4, cls=DateTimeEncoder)
    print(f"Results saved to {output_file}")


def save_plot(strategy, data_file, optimizer_config):
    """Save plot to file"""
    # Create plot with custom name
    plot_name = get_result_filename(
        data_file,
        entry_logic_name=strategy.entry_logic["name"],
        exit_logic_name=strategy.exit_logic["name"],
        suffix="_plot",
    )
    plot_path = os.path.join("results", f"{plot_name}.png")
    
    # Get the plotter from the optimizer and plot
    plotter = create_plotter(strategy, optimizer_config.get("visualization_settings", {}))
    if plotter:
        plotter.plot(plot_path)
        print(f"Plot saved to: {plot_path}")


def create_plotter(strategy, visualization_settings):
    """Create appropriate plotter based on strategy configuration"""
    entry_name = strategy.entry_logic["name"]
    exit_name = strategy.exit_logic["name"]
    
    # Create base plotter
    plotter = BasePlotter(
        data=strategy.data,
        trades=strategy.trades,
        strategy=strategy,
        vis_settings=visualization_settings
    )
    
    # Create indicators dictionary from strategy attributes
    indicators = {}
    
    # Add entry mixin indicators
    if hasattr(strategy, 'rsi'):
        indicators['rsi'] = strategy.rsi
    if hasattr(strategy, 'bb'):
        indicators['bb'] = strategy.bb
    if hasattr(strategy, 'volume'):
        indicators['volume'] = strategy.volume
    if hasattr(strategy, 'supertrend'):
        indicators['supertrend'] = strategy.supertrend
    if hasattr(strategy, 'ichimoku'):
        indicators['ichimoku'] = strategy.ichimoku
        
    # Add exit mixin indicators
    if hasattr(strategy, 'exit_rsi'):
        indicators['exit_rsi'] = strategy.exit_rsi
    if hasattr(strategy, 'exit_bb'):
        indicators['exit_bb'] = strategy.exit_bb
    
    # Add indicator plotters based on entry/exit mixins
    if entry_name == "RSIIchimokuEntryMixin":
        if hasattr(strategy, 'rsi'):
            plotter.indicator_plotters.append(RSIPlotter(strategy.data, indicators, visualization_settings))
        if hasattr(strategy, 'ichimoku'):
            plotter.indicator_plotters.append(IchimokuPlotter(strategy.data, indicators, visualization_settings))
    
    elif entry_name == "RSIBBEntryMixin":
        if hasattr(strategy, 'rsi'):
            plotter.indicator_plotters.append(RSIPlotter(strategy.data, indicators, visualization_settings))
        if hasattr(strategy, 'bb'):
            plotter.indicator_plotters.append(BollingerBandsPlotter(strategy.data, indicators, visualization_settings))
    
    elif entry_name == "RSIBBVolumeEntryMixin":
        if hasattr(strategy, 'rsi'):
            plotter.indicator_plotters.append(RSIPlotter(strategy.data, indicators, visualization_settings))
        if hasattr(strategy, 'bb'):
            plotter.indicator_plotters.append(BollingerBandsPlotter(strategy.data, indicators, visualization_settings))
        if hasattr(strategy, 'volume'):
            plotter.indicator_plotters.append(VolumePlotter(strategy.data, indicators, visualization_settings))
    
    elif entry_name == "RSIVolumeSuperTrendEntryMixin":
        if hasattr(strategy, 'rsi'):
            plotter.indicator_plotters.append(RSIPlotter(strategy.data, indicators, visualization_settings))
        if hasattr(strategy, 'volume'):
            plotter.indicator_plotters.append(VolumePlotter(strategy.data, indicators, visualization_settings))
        if hasattr(strategy, 'supertrend'):
            plotter.indicator_plotters.append(SuperTrendPlotter(strategy.data, indicators, visualization_settings))
    
    elif entry_name == "BBVolumeSuperTrendEntryMixin":
        if hasattr(strategy, 'bb'):
            plotter.indicator_plotters.append(BollingerBandsPlotter(strategy.data, indicators, visualization_settings))
        if hasattr(strategy, 'volume'):
            plotter.indicator_plotters.append(VolumePlotter(strategy.data, indicators, visualization_settings))
        if hasattr(strategy, 'supertrend'):
            plotter.indicator_plotters.append(SuperTrendPlotter(strategy.data, indicators, visualization_settings))
    
    # Add exit strategy indicators if needed
    if exit_name == "RSIBBExitMixin":
        if hasattr(strategy, 'exit_rsi'):
            plotter.indicator_plotters.append(RSIPlotter(strategy.data, indicators, visualization_settings))
        if hasattr(strategy, 'exit_bb'):
            plotter.indicator_plotters.append(BollingerBandsPlotter(strategy.data, indicators, visualization_settings))
    
    elif exit_name == "ATRExitMixin":
        # ATR is already plotted with SuperTrend if present
        pass
    
    elif exit_name == "MACrossoverExitMixin":
        # Moving averages are typically part of the entry strategy
        pass
    
    return plotter


if __name__ == "__main__":
    """Run all optimizers with their respective configurations."""
    
    with open(os.path.join("config", "optimizer", "optimizer.json"), "r", ) as f:
        optimizer_config = json.load(f)

    start_time = dt.now()
    _logger.info(f"Starting optimization at {start_time}")

    # Get the data files
    data_files = [f for f in os.listdir("data/") if f.endswith(".csv") and not f.startswith(".")]

    for data_file in data_files:
        _logger.info(f"Running optimization for {data_file}")

        data = prepare_data(data_file)
        for entry_logic_name in ENTRY_MIXIN_REGISTRY.keys():
            # Load entry logic configuration
            with open(os.path.join("config", "optimizer", "entry", f"{entry_logic_name}.json"), "r", ) as f:
                entry_logic_config = json.load(f)

            for exit_logic_name in EXIT_MIXIN_REGISTRY.keys():
                # Load exit logic configuration
                with open(os.path.join("config", "optimizer", "exit", f"{exit_logic_name}.json"), "r", ) as f:
                    exit_logic_config = json.load(f)

                print(f"Running optimization for {entry_logic_name} and {exit_logic_name}")

                # Create optimizer configuration
                _optimizer_config = {
                    "data": data,
                    "entry_logic": entry_logic_config,
                    "exit_logic": exit_logic_config,
                    "optimizer_settings": optimizer_config.get("optimizer_settings", {}),
                    "visualization_settings": optimizer_config.get("visualization_settings", {})
                }

                # Create optimizer instance
                optimizer = CustomOptimizer(_optimizer_config)

                def objective(trial):
                    """Objective function for optimization"""
                    _, result = optimizer.run_optimization(trial)
                    return result["total_profit_with_commission"]

                # Create study
                study = optuna.create_study(direction="maximize")

                # Run optimization
                study.optimize(
                    objective,
                    n_trials=optimizer_config.get("optimizer_settings", {}).get("n_trials", 100),
                    n_jobs=optimizer_config.get("optimizer_settings", {}).get("n_jobs", 1),
                )

                # Get best result
                best_trial = study.best_trial
                strategy, best_result = optimizer.run_optimization(best_trial)

                # Save results
                save_results(best_result, data_file)

                # Create and save plot
                if optimizer_config.get("optimizer_settings", {}).get("plot", True):
                    save_plot(strategy, data_file, optimizer_config)

