    def _init_indicators(self):
        """Initialize indicators for fixed ratio exit"""
        if self.strategy is None:
            raise ValueError("Strategy must be set before initializing indicators")

        if self.strategy.p.use_talib:
            import talib
            self.indicators["sma"] = bt.indicators.TALibIndicator(
                self.strategy.data.close,
                talib.SMA,
                timeperiod=self.get_param("ma_period")
            )
        else:
            self.indicators["sma"] = bt.indicators.SMA(
                self.strategy.data.close,
                period=self.get_param("ma_period")
            ) 