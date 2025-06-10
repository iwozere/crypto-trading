import os
import sys
import json
import pandas as pd
import backtrader as bt
import optuna
from datetime import datetime
from src.entry.entry_mixin_factory import EntryMixinFactory
from src.exit.exit_mixin_factory import ExitMixinFactory
from src.analyzer.bt_analyzers import CalmarRatio, CAGR, SortinoRatio, ProfitFactor, WinRate, ConsecutiveWinsLosses, PortfolioVolatility
from src.strategy.custom_strategy import make_strategy
from src.notification.logger import _logger

class CustomOptimizer:
    def __init__(self, config: dict):
        """
        Initialize optimizer with configuration
        
        Args:
            config (dict): Configuration dictionary containing:
                - data: pandas DataFrame with OHLCV data
                - entry_logic: Entry logic configuration
                - exit_logic: Exit logic configuration
                - optimizer_settings: Optimization settings
        """
        self.config = config
        self.data = config.get('data')
        self.entry_logic = config.get('entry_logic')
        self.exit_logic = config.get('exit_logic')
        self.optimizer_settings = config.get('optimizer_settings', {})
        
        # Initialize settings
        self.initial_capital = self.optimizer_settings.get('initial_capital', 1000.0)
        self.commission = self.optimizer_settings.get('commission', 0.001)
        self.risk_free_rate = self.optimizer_settings.get('risk_free_rate', 0.01)
        self.use_talib = self.optimizer_settings.get('use_talib', True)

    def run_optimization(self, trial=None):
        """
        Run optimization for a single trial or backtest with fixed parameters
        
        Args:
            trial: Optuna trial object (optional)
            
        Returns:
            dict: Dictionary containing metrics and trades
        """
        # Get entry and exit mixins
        entry_mixin = EntryMixinFactory.get_entry_mixin(self.entry_logic['name'])
        exit_mixin = ExitMixinFactory.get_exit_mixin(self.exit_logic['name'])
        StrategyClass = make_strategy(entry_mixin, exit_mixin)

        # Create cerebro instance
        cerebro = bt.Cerebro()
        
        # Add data
        data = bt.feeds.PandasData(dataname=self.data)
        cerebro.adddata(data)
        
        # Prepare strategy parameters
        strategy_params = {}
        
        # Add entry logic parameters
        for param_name, param_config in self.entry_logic['params'].items():
            if trial:
                if param_config['type'] == 'int':
                    strategy_params[param_name] = trial.suggest_int(
                        param_name, 
                        param_config['low'], 
                        param_config['high']
                    )
                elif param_config['type'] == 'float':
                    strategy_params[param_name] = trial.suggest_float(
                        param_name, 
                        param_config['low'], 
                        param_config['high']
                    )
                elif param_config['type'] == 'categorical':
                    strategy_params[param_name] = trial.suggest_categorical(
                        param_name, 
                        param_config['choices']
                    )
            else:
                strategy_params[param_name] = param_config['default']
        
        # Add exit logic parameters
        for param_name, param_config in self.exit_logic['params'].items():
            if trial:
                if param_config['type'] == 'int':
                    strategy_params[param_name] = trial.suggest_int(
                        param_name, 
                        param_config['low'], 
                        param_config['high']
                    )
                elif param_config['type'] == 'float':
                    strategy_params[param_name] = trial.suggest_float(
                        param_name, 
                        param_config['low'], 
                        param_config['high']
                    )
                elif param_config['type'] == 'categorical':
                    strategy_params[param_name] = trial.suggest_categorical(
                        param_name, 
                        param_config['choices']
                    )
            else:
                strategy_params[param_name] = param_config['default']
        
        # Add strategy with parameters
        cerebro.addstrategy(StrategyClass, **strategy_params)
        
        # Set broker parameters
        cerebro.broker.setcash(self.initial_capital)
        cerebro.broker.setcommission(commission=self.commission)
        
        # Add analyzers
        cerebro.addanalyzer(bt.analyzers.Returns, _name="returns")
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe", riskfreerate=self.risk_free_rate)
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades", _openinterest=False)
        cerebro.addanalyzer(bt.analyzers.SQN, _name="sqn")
        cerebro.addanalyzer(bt.analyzers.TimeDrawDown, _name="time_drawdown")
        cerebro.addanalyzer(bt.analyzers.TimeReturn, _name="time_return")
        cerebro.addanalyzer(bt.analyzers.VWR, _name="vwr")
        
        # Add custom analyzers
        cerebro.addanalyzer(CalmarRatio, riskfreerate=self.risk_free_rate)
        cerebro.addanalyzer(CAGR, timeframe=bt.TimeFrame.Years)
        cerebro.addanalyzer(SortinoRatio, riskfreerate=self.risk_free_rate)
        cerebro.addanalyzer(ProfitFactor)
        cerebro.addanalyzer(WinRate)
        cerebro.addanalyzer(ConsecutiveWinsLosses, _openinterest=False)
        cerebro.addanalyzer(PortfolioVolatility, _openinterest=False)
        
        # Run backtest
        results = cerebro.run()
        strategy = results[0]
        
        analyzers = {
            'sharpe': strategy.analyzers.sharpe.get_analysis(),
            'drawdown': strategy.analyzers.drawdown.get_analysis(),
            'returns': strategy.analyzers.returns.get_analysis(),
            'trades_summary': strategy.analyzers.trades.get_analysis(),
            'profit_factor': strategy.analyzers.pf.get_analysis(),
            'calmar': strategy.analyzers.calmar.get_analysis(),
            'cagr': strategy.analyzers.cagr.get_analysis(),
            'sortino': strategy.analyzers.sortino.get_analysis(),
            'winrate': strategy.analyzers.winrate.get_analysis(),
            'consecutivewinslosses': strategy.analyzers.consecutivewinslosses.get_analysis(),
            'portfoliovolatility': strategy.analyzers.portfoliovolatility.get_analysis(),
            'sqn': strategy.analyzers.sqn.get_analysis(),
            'time_drawdown': strategy.analyzers.time_drawdown.get_analysis(),
            'time_return': strategy.analyzers.time_return.get_analysis(),
            'vwr': strategy.analyzers.vwr.get_analysis()
        }        
        
        # Collect metrics
        output = {
            'best_params': study.best_trial.params if study else strategy_params,
            'analyzers': analyzers,
            'trades': strategy.trades  # то, что ты собираешь в notify_trade или в next()
        }        
        return output





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
        
        # Load data
        data = bt.feeds.GenericCSV(dataname=os.path.join("data", data_file))
        
        for entry_logic_name in EntryMixinFactory.ENTRY_LOGIC_REGISTRY.keys():
            # Load entry logic configuration
            with open(os.path.join("config", "optimizer", "entry", f"{entry_logic_name}.json"), "r") as f:
                entry_logic_config = json.load(f)
                    
            for exit_logic_name in ExitMixinFactory.EXIT_LOGIC_REGISTRY.keys():
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
                output_file = os.path.join(
                    "studies",
                    f"{data_file}_{entry_logic_name}_{exit_logic_name}.json"
                )
                os.makedirs("studies", exist_ok=True)
                
                with open(output_file, 'w') as f:
                    json.dump(results, f, indent=4)
                
                print(f"Best parameters: {study.best_params}")
                print(f"Best Sharpe ratio: {study.best_value}")
                print(f"Results saved to {output_file}")



