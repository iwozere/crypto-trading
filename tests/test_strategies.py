import pytest
import pandas as pd
import numpy as np
import backtrader as bt
from src.strats.rsi_volume_supertrend_strategy import RsiVolumeSuperTrendStrategy
from src.strats.ichimoku_rsi_atr_volume_strategy import IchimokuRSIATRVolumeStrategy
from src.strats.rsi_bb_volume_strategy import RSIBollVolumeATRStrategy
from src.strats.rsi_bb_atr_strategy import MeanReversionRSBBATRStrategy
from src.strats.bb_volume_supertrend_strategy import BBSuperTrendVolumeBreakoutStrategy

"""
Unit tests for all trading strategies in src/strats.

These tests ensure that each strategy can be instantiated, run on dummy data, and that it logs trades (or at least has a 'trades' attribute).
The tests use pytest and Backtrader with randomly generated dummy data.
"""

def make_dummy_data(length=100):
    """
    Generate a dummy pandas DataFrame with OHLCV columns for testing strategies.
    """
    idx = pd.date_range('2023-01-01', periods=length, freq='H')
    df = pd.DataFrame({
        'open': np.random.rand(length) * 10 + 100,
        'high': np.random.rand(length) * 12 + 102,
        'low': np.random.rand(length) * 8 + 98,
        'close': np.random.rand(length) * 10 + 100,
        'volume': np.random.rand(length) * 1000 + 100
    }, index=idx)
    df['high'] = np.maximum(df['high'], df['open'])
    df['high'] = np.maximum(df['high'], df['close'])
    df['low'] = np.minimum(df['low'], df['open'])
    df['low'] = np.minimum(df['low'], df['close'])
    return df

@pytest.mark.parametrize('strategy_cls', [
    RsiVolumeSuperTrendStrategy,
    IchimokuRSIATRVolumeStrategy,
    RSIBollVolumeATRStrategy,
    MeanReversionRSBBATRStrategy,
    BBSuperTrendVolumeBreakoutStrategy
])
def test_strategy_runs_and_logs_trades(strategy_cls):
    """
    Test that a strategy can run on dummy data and has a 'trades' attribute (list).
    The test passes if no error is raised and the attribute exists.
    """
    cerebro = bt.Cerebro()
    cerebro.addstrategy(strategy_cls)
    df = make_dummy_data(120)
    data_feed = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(data_feed)
    cerebro.broker.setcash(10000.0)
    cerebro.broker.setcommission(commission=0.001)
    results = cerebro.run()
    strategy = results[0]
    assert hasattr(strategy, 'trades')
    assert isinstance(strategy.trades, list)
    # Should not raise, and trades can be empty if no signals, but type must be list 