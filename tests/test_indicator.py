import unittest
import numpy as np
import backtrader as bt
from src.indicator.rsi import RSI

class TestRSIIndicator(unittest.TestCase):
    def setUp(self):
        # Create synthetic close price data
        self.data = [100 + np.sin(i/5)*10 for i in range(100)]
        self.bt_data = bt.feeds.PandasData(dataname=self._to_pandas())

    def _to_pandas(self):
        import pandas as pd
        idx = pd.date_range("2020-01-01", periods=len(self.data), freq="D")
        return pd.DataFrame({
            'close': self.data
        }, index=idx)

    def test_rsi_all_types(self):
        indicator_types = ['bt', 'bt-talib', 'pandas-ta', 'talib']
        for ind_type in indicator_types:
            cerebro = bt.Cerebro()
            data = bt.feeds.PandasData(dataname=self._to_pandas())
            cerebro.adddata(data)
            rsi = RSI(data, period=14, indicator_type=ind_type)
            cerebro.addindicator(RSI, period=14, indicator_type=ind_type)
            # Run for a few bars to ensure no exceptions
            try:
                cerebro.run(runonce=False, stdstats=False)
            except Exception as e:
                self.fail(f"RSI indicator_type '{ind_type}' raised an exception: {e}")

if __name__ == "__main__":
    unittest.main() 