import os
import sys
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(project_root)

import optuna
import backtrader as bt
from datetime import datetime
from src.entry.entry_mixin_factory import EntryMixinFactory
from src.exit.exit_mixin_factory import ExitMixinFactory
from src.analyzer.bt_analyzers import CalmarRatio, CAGR, SortinoRatio, ProfitFactor, WinRate, ConsecutiveWinsLosses, PortfolioVolatility
from src.strategy.custom_strategy import make_strategy
from src.notification.logger import _logger


def objective(trial):
    ma_fast = trial.suggest_int("ma_fast", 5, 20)
    ma_slow = trial.suggest_int("ma_slow", ma_fast + 5, 50)
    entry_type = trial.suggest_categorical("entry_type", ["ma_cross", "rsi_bb", "rsi_bb_volume", "bb_volume_supertrend", "rsi_volume_supertrend", "rsi_ichimoku"])
    exit_type = trial.suggest_categorical("exit_type", ["fixed", "trailing"])

    # Строим стратегию
    entry_mixin = EntryMixinFactory.get_entry_mixin(entry_type)
    exit_mixin = ExitMixinFactory.get_exit_mixin(exit_type)
    StrategyClass = make_strategy(entry_mixin, exit_mixin)

    cerebro = bt.Cerebro()
    data = bt.feeds.YahooFinanceData(dataname='AAPL',
                                     fromdate=datetime(2020,1,1),
                                     todate=datetime(2023,1,1))
    cerebro.adddata(data)
    cerebro.addstrategy(StrategyClass,
                        ma_fast=ma_fast,
                        ma_slow=ma_slow,
                        take_profit=trial.suggest_float("take_profit", 0.03, 0.1),
                        stop_loss=trial.suggest_float("stop_loss", 0.01, 0.05),
                        trailing_stop=trial.suggest_float("trailing_stop", 0.01, 0.05),
                       )
    cerebro.broker.setcash(1000)
    
    # Add all analyzers - standard first, custom next
    cerebro.addanalyzer(bt.analyzers.Returns, _name="returns")
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe", riskfreerate=0.02)
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades", _openinterest=False)
    cerebro.addanalyzer(bt.analyzers.SQN, _name="sqn")
    cerebro.addanalyzer(bt.analyzers.TimeDrawDown, _name="time_drawdown")
    cerebro.addanalyzer(bt.analyzers.TimeReturn, _name="time_return")
    cerebro.addanalyzer(bt.analyzers.VWR, _name="vwr")
    
    # Add custom analyzers
    cerebro.addanalyzer(CalmarRatio, riskfreerate=0.02)
    cerebro.addanalyzer(CAGR, timeframe=bt.TimeFrame.Years)
    cerebro.addanalyzer(SortinoRatio, riskfreerate=0.02)
    cerebro.addanalyzer(ProfitFactor)
    cerebro.addanalyzer(WinRate)
    cerebro.addanalyzer(ConsecutiveWinsLosses, _openinterest=False)
    cerebro.addanalyzer(PortfolioVolatility, _openinterest=False)
    
    cerebro.run()
    return cerebro.broker.getvalue()

if __name__ == "__main__":
    """Run all optimizers with their respective configurations."""
    start_time = datetime.datetime.now()
    _logger.info(f"Starting optimization at {start_time}")

    # Get the data files
    data_files = [
        f
        for f in os.listdir("data/")
        if f.endswith(".csv") and not f.startswith(".")
    ]

    for data_file in data_files:
        _logger.info(f"Running optimization for {data_file}")
        for entry_logic_name in EntryMixinFactory.ENTRY_LOGIC_REGISTRY.keys():
            for exit_logic_name in ExitMixinFactory.EXIT_LOGIC_REGISTRY.keys():
                print(f"Running optimization for {entry_logic_name} and {exit_logic_name}")
                study = optuna.create_study(direction="maximize", study_name=f"{entry_logic_name}_{exit_logic_name}")
                study.optimize(objective, n_trials=100)
                print(study.best_trial)
                print(study.best_params)
                print(study.best_value)


