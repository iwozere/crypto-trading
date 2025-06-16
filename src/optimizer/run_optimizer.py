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
from src.notification.logger import setup_logger
from src.optimizer.custom_optimizer import CustomOptimizer
from src.plotter.base_plotter import BasePlotter

_logger = setup_logger(__name__)


def prepare_data(data_file):
    """Load and prepare data from CSV file"""
    # Load and prepare data
    df = pd.read_csv(os.path.join("data", data_file))
    print("Available columns:", df.columns.tolist())

    # Find datetime column
    df["datetime"] = pd.to_datetime(df["timestamp"], utc=True)    
    df = df.sort_values("datetime", ascending=True)
    df.set_index("datetime", inplace=True)

    df = df[["open", "high", "low", "close", "volume"]]

    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df.ffill(inplace=True)
    df.bfill(inplace=True)

    # Create Backtrader data feed
    data = bt.feeds.PandasData(
        dataname=df,
        datetime=None,
        open=df.columns.get_loc("open"),
        high=df.columns.get_loc("high"),
        low=df.columns.get_loc("low"),
        close=df.columns.get_loc("close"),
        volume=df.columns.get_loc("volume"),
        openinterest=None
    )
    return data


def get_result_filename(data_file, entry_logic_name=None, exit_logic_name=None, suffix=""):
    """Generate a standardized filename for results"""
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
    
    # Include strategy names in filename if provided
    strategy_part = ""
    if entry_logic_name and exit_logic_name:
        strategy_part = f"_{entry_logic_name}_{exit_logic_name}"
    
    return f"{symbol}_{interval}_{start_date}_{end_date}{strategy_part}_{timestamp}{suffix}"


def save_results(result, data_file):
    """Save optimization results to a JSON file"""
    try:
        # Create results directory if it doesn't exist
        os.makedirs("results", exist_ok=True)
        
        # Generate filename based on data file
        filename = get_result_filename(
            data_file,
            entry_logic_name=result.get("best_params", {}).get("entry_logic", {}).get("name", ""),
            exit_logic_name=result.get("best_params", {}).get("exit_logic", {}).get("name", ""),
            suffix=""
        )
        
        # Convert trade records to serializable format
        trades = []
        for trade in result.get("trades", []):
            try:
                # Ensure we have all required fields
                if not all(k in trade for k in ['entry_time', 'exit_time', 'entry_price', 'exit_price']):
                    _logger.warning(f"Skipping trade with missing required fields: {trade}")
                    continue
                    
                # Convert datetime objects to ISO format strings
                entry_time = trade['entry_time']
                exit_time = trade['exit_time']
                
                if isinstance(entry_time, pd.Timestamp):
                    entry_time = entry_time.isoformat()
                elif isinstance(entry_time, dt):
                    entry_time = entry_time.isoformat()
                    
                if isinstance(exit_time, pd.Timestamp):
                    exit_time = exit_time.isoformat()
                elif isinstance(exit_time, dt):
                    exit_time = exit_time.isoformat()
                
                # Create serializable trade record
                serializable_trade = {
                    'entry_time': entry_time,
                    'exit_time': exit_time,
                    'entry_price': float(trade['entry_price']),
                    'exit_price': float(trade['exit_price']),
                    'size': float(trade['size']),
                    'symbol': str(trade['symbol']),
                    'trade_type': str(trade['trade_type']),
                    'commission': float(trade['commission']),
                    'gross_pnl': float(trade['gross_pnl']),
                    'net_pnl': float(trade['net_pnl']),
                    'pnl_percentage': float(trade['pnl_percentage']),
                    'exit_reason': str(trade['exit_reason']),
                    'status': str(trade['status'])
                }
                trades.append(serializable_trade)
                
                # Log trade details for debugging
                _logger.debug(f"Processed trade: Entry={serializable_trade['entry_price']} @ {serializable_trade['entry_time']}, "
                            f"Exit={serializable_trade['exit_price']} @ {serializable_trade['exit_time']}")
            except Exception as e:
                _logger.error(f"Error processing trade: {str(e)}")
                continue
        
        # Process analyzer results
        analyzers = {}
        for name, analyzer in result.get("analyzers", {}).items():
            try:
                # Handle different analyzer types
                if isinstance(analyzer, dict):
                    # Already a dictionary, just convert values
                    processed_analysis = {}
                    for k, v in analyzer.items():
                        if isinstance(v, (int, float)):
                            processed_analysis[str(k)] = float(v)
                        elif isinstance(v, dt):
                            processed_analysis[str(k)] = v.isoformat()
                        else:
                            processed_analysis[str(k)] = str(v)
                    analyzers[name] = processed_analysis
                elif hasattr(analyzer, 'get_analysis'):
                    # Get analysis using get_analysis method
                    analysis = analyzer.get_analysis()
                    if isinstance(analysis, dict):
                        processed_analysis = {}
                        for k, v in analysis.items():
                            if isinstance(v, (int, float)):
                                processed_analysis[str(k)] = float(v)
                            elif isinstance(v, dt):
                                processed_analysis[str(k)] = v.isoformat()
                            else:
                                processed_analysis[str(k)] = str(v)
                        analyzers[name] = processed_analysis
                    elif isinstance(analysis, (int, float)):
                        analyzers[name] = float(analysis)
                    else:
                        analyzers[name] = str(analysis)
                else:
                    # Direct value or other type
                    if isinstance(analyzer, (int, float)):
                        analyzers[name] = float(analyzer)
                    else:
                        analyzers[name] = str(analyzer)
            except Exception as e:
                _logger.warning(f"Could not process analyzer {name}: {str(e)}")
                # Store the raw analyzer value if processing fails
                analyzers[name] = str(analyzer)
        
        # Create the final result dictionary
        result_dict = {
            "data_file": str(data_file),
            "total_trades": len(trades),
            "total_profit": float(result.get("total_profit", 0)),
            "total_profit_with_commission": float(result.get("total_profit_with_commission", 0)),
            "best_params": result.get("best_params", {}),
            "analyzers": analyzers,
            "trades": trades
        }
        
        # Save to JSON file
        json_file = os.path.join("results", f"{filename}.json")
        with open(json_file, "w") as f:
            json.dump(result_dict, f, indent=4)
            
        _logger.info(f"Results saved to {json_file}")
        
    except Exception as e:
        _logger.error(f"Error saving results: {str(e)}")
        raise


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
    _logger.info(f"Creating plotter for strategy: {strategy}")
    
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
    if hasattr(strategy, 'entry_mixin'):
        if hasattr(strategy.entry_mixin, 'indicators'):
            indicators.update(strategy.entry_mixin.indicators)
        else:
            # Add individual indicators if not in indicators dict
            if hasattr(strategy, 'entry_rsi'):
                indicators['entry_rsi'] = strategy.entry_rsi
            if hasattr(strategy, 'entry_bb'):
                indicators['entry_bb'] = strategy.entry_bb
            if hasattr(strategy, 'entry_volume_ma'):
                indicators['entry_volume_ma'] = strategy.entry_volume_ma
            if hasattr(strategy, 'entry_supertrend'):
                indicators['entry_supertrend'] = strategy.entry_supertrend
            if hasattr(strategy, 'entry_ichimoku'):
                indicators['entry_ichimoku'] = strategy.entry_ichimoku
    
    # Add exit mixin indicators
    if hasattr(strategy, 'exit_mixin'):
        if hasattr(strategy.exit_mixin, 'indicators'):
            indicators.update(strategy.exit_mixin.indicators)
        else:
            # Add individual indicators if not in indicators dict
            if hasattr(strategy, 'exit_rsi'):
                indicators['exit_rsi'] = strategy.exit_rsi
            if hasattr(strategy, 'exit_bb'):
                indicators['exit_bb'] = strategy.exit_bb
    
    # Update strategy's indicators dictionary
    #if hasattr(strategy, 'entry_mixin'):
    #    strategy.entry_mixin.indicators = indicators
    
    # Log available indicators for debugging
    _logger.info(f"Available indicators: {list(indicators.keys())}")
    for name, indicator in indicators.items():
        if hasattr(indicator, 'array'):
            _logger.info(f"Indicator {name} has array of length {len(indicator.array)}")
        elif hasattr(indicator, 'lines'):
            _logger.info(f"Indicator {name} has {len(indicator.lines)} lines")
        else:
            _logger.warning(f"Indicator {name} has no array or lines attribute")
    
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

                def objective(trial):
                    """Objective function for optimization"""
                    # Create optimizer instance
                    optimizer = CustomOptimizer(_optimizer_config)
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
                best_optimizer = CustomOptimizer(_optimizer_config)
                
                # Run full backtest with best parameters
                _logger.info("Running full backtest with best parameters")
                strategy, best_result = best_optimizer.run_optimization(best_trial)
                
                # Save results
                save_results(best_result, data_file)

                # Create and save plot
                if optimizer_config.get("optimizer_settings", {}).get("plot", True):
                    save_plot(strategy, data_file, optimizer_config)

