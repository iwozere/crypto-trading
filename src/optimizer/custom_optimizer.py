"""
Custom Optimizer Module

This module implements a custom optimization framework for trading strategies using Backtrader
and Optuna. It provides functionality to:
1. Run backtests with fixed parameters
2. Optimize strategy parameters using Optuna
3. Collect and analyze various performance metrics
4. Support multiple entry and exit strategies

The optimizer supports:
- Multiple entry and exit strategy combinations
- Parameter optimization with different types (int, float, categorical)
- Comprehensive performance analysis with multiple metrics
- Custom analyzers for detailed strategy evaluation

Parameters:
    config (dict): Configuration dictionary containing:
        - data: pandas DataFrame with OHLCV data
        - entry_logic: Entry logic configuration
        - exit_logic: Exit logic configuration
        - optimizer_settings: Optimization settings
"""

import os
import sys
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import json
import backtrader as bt
from src.analyzer.bt_analyzers import (CAGR, CalmarRatio,
                                       ConsecutiveWinsLosses,
                                       PortfolioVolatility, ProfitFactor,
                                       SortinoRatio, WinRate)
from src.notification.logger import _logger
from src.strategy.custom_strategy import CustomStrategy


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
        self.data = config.get("data")
        self.entry_logic = config.get("entry_logic")
        self.exit_logic = config.get("exit_logic")
        self.optimizer_settings = config.get("optimizer_settings", {})
        self.visualization_settings = config.get("visualization_settings", {})

        # Initialize settings
        self.initial_capital = self.optimizer_settings.get("initial_capital", 1000.0)
        self.commission = self.optimizer_settings.get("commission", 0.001)
        self.risk_free_rate = self.optimizer_settings.get("risk_free_rate", 0.01)
        self.use_talib = self.optimizer_settings.get("use_talib", False)
        self.output_dir = self.optimizer_settings.get("output_dir", "output")
        os.makedirs(self.output_dir, exist_ok=True)

    def to_dict(self, obj):
        if isinstance(obj, dict):
            return {k: self.to_dict(v) for k, v in obj.items()}
        elif hasattr(obj, 'items'):
            return {k: self.to_dict(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self.to_dict(v) for v in obj]
        else:
            return obj

    def run_optimization(self, trial=None):
        """
        Run optimization for a single trial or backtest with fixed parameters

        Args:
            trial: Optuna trial object (optional)

        Returns:
            dict: Dictionary containing metrics and trades
        """
        # Create cerebro instance
        cerebro = bt.Cerebro()

        # Add data
        cerebro.adddata(self.data)

        # Add entry logic parameters
        entry_logic_params = {}
        for param_name, param_config in self.entry_logic["params"].items():
            if trial:
                if param_config["type"] == "int":
                    entry_logic_params[param_name] = trial.suggest_int(
                        param_name, param_config["low"], param_config["high"]
                    )
                elif param_config["type"] == "float":
                    entry_logic_params[param_name] = trial.suggest_float(
                        param_name, param_config["low"], param_config["high"]
                    )
                elif param_config["type"] == "categorical":
                    entry_logic_params[param_name] = trial.suggest_categorical(
                        param_name, param_config["choices"]
                    )
            else:
                entry_logic_params[param_name] = param_config["default"]

        # Add exit logic parameters
        exit_logic_params = {}
        for param_name, param_config in self.exit_logic["params"].items():
            if trial:
                if param_config["type"] == "int":
                    exit_logic_params[param_name] = trial.suggest_int(
                        param_name, param_config["low"], param_config["high"]
                    )
                elif param_config["type"] == "float":
                    exit_logic_params[param_name] = trial.suggest_float(
                        param_name, param_config["low"], param_config["high"]
                    )
                elif param_config["type"] == "categorical":
                    exit_logic_params[param_name] = trial.suggest_categorical(
                        param_name, param_config["choices"]
                    )
            else:
                exit_logic_params[param_name] = param_config["default"]

        # Prepare strategy parameters
        strategy_params = {
            "entry_logic": {
                "name": self.entry_logic["name"],
                "params": entry_logic_params,
            },
            "exit_logic": {
                "name": self.exit_logic["name"],
                "params": exit_logic_params,
            },
            "use_talib": self.use_talib,
            "position_size": self.optimizer_settings.get("position_size", 0.10),
        }

        # Add strategy with parameters
        cerebro.addstrategy(CustomStrategy, strategy_config=strategy_params)

        # Set broker parameters
        cerebro.broker.setcash(self.initial_capital)
        cerebro.broker.setcommission(commission=self.commission)

        # Add analyzers
        cerebro.addanalyzer(bt.analyzers.Returns, _name="returns")
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
        cerebro.addanalyzer(bt.analyzers.SQN, _name="sqn")
        cerebro.addanalyzer(bt.analyzers.TimeDrawDown, _name="time_drawdown")
        #cerebro.addanalyzer(bt.analyzers.TimeReturn, _name="time_return")
        cerebro.addanalyzer(bt.analyzers.VWR, _name="vwr")
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe", riskfreerate=self.risk_free_rate)

        # Add custom analyzers
        cerebro.addanalyzer(ProfitFactor, _name="profit_factor")
        cerebro.addanalyzer(WinRate, _name="winrate")
        cerebro.addanalyzer(CalmarRatio, _name="calmar", riskfreerate=self.risk_free_rate)
        cerebro.addanalyzer(CAGR, _name="cagr", timeframe=bt.TimeFrame.Years)
        cerebro.addanalyzer(SortinoRatio, _name="sortino", riskfreerate=self.risk_free_rate)
        cerebro.addanalyzer(ConsecutiveWinsLosses, _name="consecutivewinslosses")
        cerebro.addanalyzer(PortfolioVolatility, _name="portfoliovolatility")

        # Run backtest
        _logger.debug("Running backtest")
        results = cerebro.run(runonce=True, preload=True)
        strategy = results[0]
        _logger.debug("Backtest completed")

        analyzers = {}
        for name in strategy.analyzers._names:
            analyzer = getattr(strategy.analyzers, name)
            analysis = analyzer.get_analysis()
            analyzers[name] = self.to_dict(analysis)

        # Get trade analysis
        trades_analysis = analyzers.get('trades', {})
        
        # Calculate metrics
        total_profit = trades_analysis.get("pnl", {}).get("net", {}).get("total", 0.0)
        total_commission = trades_analysis.get("pnl", {}).get("comm", {}).get("total", 0.0)
        total_profit_with_comm = total_profit - total_commission

        output = {
            "best_params": strategy_params,
            "total_profit": float(total_profit),
            "total_profit_with_commission": float(total_profit_with_comm),
            "analyzers": analyzers,
            "trades": strategy.trades
        }

        return strategy, cerebro, output

