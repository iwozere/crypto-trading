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
        self.use_talib = self.optimizer_settings.get("use_talib", True)
        self.output_dir = self.optimizer_settings.get("output_dir", "output")
        os.makedirs(self.output_dir, exist_ok=True)

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
        cerebro.addanalyzer(bt.analyzers.TimeReturn, _name="time_return")
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
        results = cerebro.run()
        strategy = results[0]

        analyzers = {
            "sharpe": strategy.analyzers.sharpe.get_analysis(),
            "drawdown": strategy.analyzers.drawdown.get_analysis(),
            "returns": strategy.analyzers.returns.get_analysis(),
            "trades_summary": strategy.analyzers.trades.get_analysis(),
            "profit_factor": strategy.analyzers.profit_factor.get_analysis(),
            "calmar": strategy.analyzers.calmar.get_analysis(),
            "cagr": strategy.analyzers.cagr.get_analysis(),
            "sortino": strategy.analyzers.sortino.get_analysis(),
            "winrate": strategy.analyzers.winrate.get_analysis(),
            "consecutivewinslosses": strategy.analyzers.consecutivewinslosses.get_analysis(),
            "portfoliovolatility": strategy.analyzers.portfoliovolatility.get_analysis(),
            "sqn": strategy.analyzers.sqn.get_analysis(),
            "time_drawdown": strategy.analyzers.time_drawdown.get_analysis(),
            #"time_return": strategy.analyzers.time_return.get_analysis(), - removed due to datetime objects
            "vwr": strategy.analyzers.vwr.get_analysis(),
        }

        # Collect metrics
        trades_analysis = strategy.analyzers.trades.get_analysis()
        total_profit = trades_analysis.get("pnl", {}).get("net", {}).get("total", 0.0)
        total_commission = trades_analysis.get("pnl", {}).get("comm", {}).get("total", 0.0)
        total_profit_with_comm = total_profit - total_commission

        output = {
            "best_params": strategy_params,
            "total_profit": total_profit,
            "total_profit_with_commission": total_profit_with_comm,
            "analyzers": analyzers,
            "trades": strategy.trades,  # what is collected in notify_trade or in next()
        }

        # Convert to JSON and back to handle datetime serialization
        return strategy, output

