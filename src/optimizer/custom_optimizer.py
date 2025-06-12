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
from src.util.date_time_encoder import DateTimeEncoder
from src.plotter.rsi_ichimoku_plotter import RSIIchimokuPlotter
from src.plotter.indicators.rsi_plotter import RSIPlotter
from src.plotter.indicators.ichimoku_plotter import IchimokuPlotter
from src.plotter.indicators.bollinger_bands_plotter import BollingerBandsPlotter
from src.plotter.indicators.volume_plotter import VolumePlotter
from src.plotter.indicators.supertrend_plotter import SuperTrendPlotter
from src.plotter.base_plotter import BasePlotter


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

        # Create plot
        plotter = self._create_plotter(strategy)
        if plotter:
            plot_path = os.path.join(
                self.output_dir,
                f"backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            )
            plotter.plot(plot_path)

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
        return json.loads(json.dumps(output, cls=DateTimeEncoder))

    def _create_plotter(self, strategy):
        """Create appropriate plotter based on strategy configuration"""
        entry_name = self.entry_logic["name"]
        exit_name = self.exit_logic["name"]
        
        # Create base plotter
        plotter = BasePlotter(
            self.data,
            strategy.trades,
            strategy,
            self.visualization_settings
        )
        
        # Add indicator plotters based on entry/exit mixins
        if entry_name == "RSIIchimokuEntryMixin":
            plotter.add_indicator_plotter(RSIPlotter(self.data, strategy.entry_mixin.indicators, self.visualization_settings))
            plotter.add_indicator_plotter(IchimokuPlotter(self.data, strategy.entry_mixin.indicators, self.visualization_settings))
        
        elif entry_name == "RSIBBEntryMixin":
            plotter.add_indicator_plotter(RSIPlotter(self.data, strategy.entry_mixin.indicators, self.visualization_settings))
            plotter.add_indicator_plotter(BollingerBandsPlotter(self.data, strategy.entry_mixin.indicators, self.visualization_settings))
        
        elif entry_name == "RSIBBVolumeEntryMixin":
            plotter.add_indicator_plotter(RSIPlotter(self.data, strategy.entry_mixin.indicators, self.visualization_settings))
            plotter.add_indicator_plotter(BollingerBandsPlotter(self.data, strategy.entry_mixin.indicators, self.visualization_settings))
            plotter.add_indicator_plotter(VolumePlotter(self.data, strategy.entry_mixin.indicators, self.visualization_settings))
        
        elif entry_name == "RSIVolumeSuperTrendEntryMixin":
            plotter.add_indicator_plotter(RSIPlotter(self.data, strategy.entry_mixin.indicators, self.visualization_settings))
            plotter.add_indicator_plotter(VolumePlotter(self.data, strategy.entry_mixin.indicators, self.visualization_settings))
            plotter.add_indicator_plotter(SuperTrendPlotter(self.data, strategy.entry_mixin.indicators, self.visualization_settings))
        
        elif entry_name == "BBVolumeSuperTrendEntryMixin":
            plotter.add_indicator_plotter(BollingerBandsPlotter(self.data, strategy.entry_mixin.indicators, self.visualization_settings))
            plotter.add_indicator_plotter(VolumePlotter(self.data, strategy.entry_mixin.indicators, self.visualization_settings))
            plotter.add_indicator_plotter(SuperTrendPlotter(self.data, strategy.entry_mixin.indicators, self.visualization_settings))
        
        # Add exit strategy indicators if needed
        if exit_name == "ATRExitMixin":
            # ATR is already plotted with SuperTrend if present
            pass
        
        elif exit_name == "MACrossoverExitMixin":
            # Moving averages are typically part of the entry strategy
            pass
        
        return plotter
