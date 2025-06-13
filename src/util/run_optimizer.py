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

    data = bt.feeds.PandasData(
        dataname=df,
        datetime="datetime",
        open="open",
        high="high",
        low="low",
        close="close",
        volume="volume",
        openinterest=-1,
    )
    return data


def get_result_filename(data_file, entry_logic_name, exit_logic_name, suffix=""):
    """
    Generate a standardized filename for results and plots based on data_file and current_data.
    """
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
    """Save results to file"""
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


def save_plot(plotter, data_file):
    # Create plot with custom name
    plot_name = get_result_filename(
        data_file,
        entry_logic_name=plotter.strategy.entry_logic["name"],
        exit_logic_name=plotter.strategy.exit_logic["name"],
        suffix="_plot",
    )
    plot_path = os.path.join("results", f"{plot_name}.png")
    
    # Get the plotter from the optimizer and plot
    if plotter:
        plotter.plot(plot_path)
        print(f"Plot saved to: {plot_path}")

def create_plotter(strategy, visualization_settings):
    """Create appropriate plotter based on strategy configuration"""
    entry_name = strategy.entry_logic["name"]
    exit_name = strategy.exit_logic["name"]
    
    # Create base plotter
    plotter = BasePlotter(
        strategy.data,
        strategy.trades,
        strategy,
        visualization_settings
    )
    
    # Add indicator plotters based on entry/exit mixins
    if entry_name == "RSIIchimokuEntryMixin":
        plotter.indicator_plotters.append(RSIPlotter(strategy.data, strategy.entry_mixin.indicators, visualization_settings))
        plotter.indicator_plotters.append(IchimokuPlotter(strategy.data, strategy.entry_mixin.indicators, visualization_settings))
    
    elif entry_name == "RSIBBEntryMixin":
        plotter.indicator_plotters.append(RSIPlotter(strategy.data, strategy.entry_mixin.indicators, visualization_settings))
        plotter.indicator_plotters.append(BollingerBandsPlotter(strategy.data, strategy.entry_mixin.indicators, visualization_settings))
    
    elif entry_name == "RSIBBVolumeEntryMixin":
        plotter.indicator_plotters.append(RSIPlotter(strategy.data, strategy.entry_mixin.indicators, visualization_settings))
        plotter.indicator_plotters.append(BollingerBandsPlotter(strategy.data, strategy.entry_mixin.indicators, visualization_settings))
        plotter.indicator_plotters.append(VolumePlotter(strategy.data, strategy.entry_mixin.indicators, visualization_settings))
    
    elif entry_name == "RSIVolumeSuperTrendEntryMixin":
        plotter.indicator_plotters.append(RSIPlotter(strategy.data, strategy.entry_mixin.indicators, visualization_settings))
        plotter.indicator_plotters.append(VolumePlotter(strategy.data, strategy.entry_mixin.indicators, visualization_settings))
        plotter.indicator_plotters.append(SuperTrendPlotter(strategy.data, strategy.entry_mixin.indicators, visualization_settings))
    
    elif entry_name == "BBVolumeSuperTrendEntryMixin":
        plotter.indicator_plotters.append(BollingerBandsPlotter(strategy.data, strategy.entry_mixin.indicators, visualization_settings))
        plotter.indicator_plotters.append(VolumePlotter(strategy.data, strategy.entry_mixin.indicators, visualization_settings))
        plotter.indicator_plotters.append(SuperTrendPlotter(strategy.data, strategy.entry_mixin.indicators, visualization_settings))
    
    # Add exit strategy indicators if needed
    if exit_name == "ATRExitMixin":
        # ATR is already plotted with SuperTrend if present
        pass
    
    elif exit_name == "MACrossoverExitMixin":
        # Moving averages are typically part of the entry strategy
        pass
    
    return plotter



if __name__ == "__main__":
    """Run all optimizers with their respective configurations."""
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
                optimizer_config = {
                    "data": data,
                    "entry_logic": entry_logic_config,
                    "exit_logic": exit_logic_config,
                    "optimizer_settings": {
                        "initial_capital": 1000.0,
                        "commission": 0.001,
                        "risk_free_rate": 0.01,
                        "use_talib": True,
                    },
                }

                # Create optimizer instance
                optimizer = CustomOptimizer(optimizer_config)

                # Create Optuna study
                study = optuna.create_study(
                    direction="maximize",
                    study_name=f"{data_file}_{entry_logic_name}_{exit_logic_name}",
                )

                # Define objective function
                def objective(trial):
                    _, result = optimizer.run_optimization(trial)
                    return result["total_profit_with_commission"]

                # Run optimization
                study.optimize(objective, n_trials=100, n_jobs=1, show_progress_bar=False)

                # Get best trial and run it again to get detailed results
                if study.best_trial is not None:
                    strategy, best_result = optimizer.run_optimization(study.best_trial)
                    print("\nBest trial results:")
                    print(f"Parameters: {best_result['best_params']}")
                    print(f"Total Profit: {best_result['total_profit']:.2f}")
                    print(f"Total Profit (with commission): {best_result['total_profit_with_commission']:.2f}")


                    #results = {
                    #    "study_name": study.study_name,
                    #    "best_params": study.best_params,
                    #    "best_value": study.best_value,
                    #    "analyzers": best_result["analyzers"],
                    #    "trades": best_result["trades"],
                    #}

                    save_results(best_result, data_file)
                    
                    save_plot(create_plotter(strategy, optimizer_config.get("visualization_settings", {})), data_file)

                else:
                    print("No trials were completed successfully.")

