import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import json
import pandas as pd
import backtrader as bt
import optuna
from src.notification.logger import _logger
from datetime import datetime
from src.entry.entry_mixin_factory import ENTRY_MIXIN_REGISTRY, get_entry_mixin_from_config
from src.exit.exit_mixin_factory import EXIT_MIXIN_REGISTRY, get_exit_mixin_from_config
from src.optimizer.custom_optimizer import CustomOptimizer


def prepare_data(data_file):
    # Load and prepare data
    df = pd.read_csv(os.path.join("data", data_file))
    print("Available columns:", df.columns.tolist())
    
    # Find datetime column
    datetime_col = None
    for col in ['datetime', 'date', 'time', 'timestamp']:
        if col in df.columns:
            datetime_col = col
            break
    
    if datetime_col:
        df['datetime'] = pd.to_datetime(df[datetime_col])
    else:
        # If no datetime column found, create one from index
        df['datetime'] = pd.date_range(start='2020-01-01', periods=len(df), freq='1min')
    
    data = bt.feeds.PandasData(
        dataname=df,
        datetime='datetime',
        open='open',
        high='high',
        low='low',
        close='close',
        volume='volume',
        openinterest=-1
    )
    return data


def get_result_filename(data_file, entry_logic_name, exit_logic_name, suffix=""):
    """
    Generate a standardized filename for results and plots based on data_file and current_data.
    """
    # Extract symbol, interval, and dates from data_file
    symbol = getattr("current_symbol", "SYMBOL")
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

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{entry_logic_name}_{exit_logic_name}_{symbol}_{interval}_{start_date}_{end_date}_{timestamp}{suffix}"





if __name__ == "__main__":
    """Run all optimizers with their respective configurations."""
    start_time = datetime.now()
    _logger.info(f"Starting optimization at {start_time}")

    # Get the data files
    data_files = [
        f
        for f in os.listdir("data/")
        if f.endswith(".csv") and not f.startswith(".")
    ]

    for data_file in data_files:
        _logger.info(f"Running optimization for {data_file}")
        
        data = prepare_data(data_file)
        for entry_logic_name in ENTRY_MIXIN_REGISTRY.keys():
            # Load entry logic configuration
            with open(os.path.join("config", "optimizer", "entry", f"{entry_logic_name}.json"), "r") as f:
                entry_logic_config = json.load(f)
                    
            for exit_logic_name in EXIT_MIXIN_REGISTRY.keys():
                # Load exit logic configuration
                with open(os.path.join("config", "optimizer", "exit", f"{exit_logic_name}.json"), "r") as f:
                    exit_logic_config = json.load(f)
                
                print(f"Running optimization for {entry_logic_name} and {exit_logic_name}")
                
                # Create optimizer configuration
                optimizer_config = {
                    'data': data,
                    'entry_logic': entry_logic_config,
                    'exit_logic': exit_logic_config,
                    'optimizer_settings': {
                        'initial_capital': 1000.0,
                        'commission': 0.001,
                        'risk_free_rate': 0.01,
                        'use_talib': True
                    }
                }
                
                # Create optimizer instance
                optimizer = CustomOptimizer(optimizer_config)
                
                # Create Optuna study
                study = optuna.create_study(
                    direction="maximize",
                    study_name=f"{data_file}_{entry_logic_name}_{exit_logic_name}"
                )
                
                # Define objective function
                def objective(trial):
                    result = optimizer.run_optimization(trial)
                    # Use Sharpe ratio as the optimization metric
                    return result['analyzers']['sharpe'].get('sharperatio', 0.0)
                
                # Run optimization
                study.optimize(
                    objective,
                    n_trials=100,
                    show_progress_bar=True
                )
                
                # Get best results
                best_result = optimizer.run_optimization(study.best_trial)
                
                # Save results
                results = {
                    'study_name': study.study_name,
                    'best_params': study.best_params,
                    'best_value': study.best_value,
                    'analyzers': best_result['analyzers'],
                    'trades': best_result['trades']
                }
                
                # Save to file
                output_file_name = get_result_filename(data_file, entry_logic_name=entry_logic_name, exit_logic_name=exit_logic_name, suffix="")
                output_file = os.path.join(
                    "results",
                    f"{output_file_name}.json"
                )
                os.makedirs("results", exist_ok=True)
                
                with open(output_file, 'w') as f:
                    json.dump(results, f, indent=4)
                
                print(f"Best parameters: {study.best_params}")
                print(f"Best Sharpe ratio: {study.best_value}")
                print(f"Results saved to {output_file}")



