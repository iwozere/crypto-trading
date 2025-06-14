"""
Ichimoku Cloud Indicator

This module provides a Backtrader-compatible wrapper for the Ichimoku Cloud indicator.
It implements the Ichimoku Kinko Hyo system, which consists of:
1. Tenkan-sen (Conversion Line)
2. Kijun-sen (Base Line)
3. Senkou Span A (Leading Span A)
4. Senkou Span B (Leading Span B)
5. Chikou Span (Lagging Span)

The indicator helps identify:
- Trend direction
- Support and resistance levels
- Potential reversal points
- Momentum
"""

import backtrader as bt


class Ichimoku(bt.Indicator):
    """
    Ichimoku Cloud indicator for Backtrader.
    
    This indicator implements the Ichimoku Kinko Hyo system, which provides
    a comprehensive view of price action, trend direction, and potential
    support/resistance levels.
    
    Parameters:
    -----------
    tenkan : int
        Period for Tenkan-sen (Conversion Line) calculation (default: 9)
    kijun : int
        Period for Kijun-sen (Base Line) calculation (default: 26)
    senkou_span_b : int
        Period for Senkou Span B calculation (default: 52)
    """
    
    lines = ('tenkan_sen', 'kijun_sen', 'senkou_span_a', 'senkou_span_b', 'chikou_span',)
    params = (
        ('tenkan', 9),
        ('kijun', 26),
        ('senkou_span_b', 52),
    )
    
    def __init__(self):
        super(Ichimoku, self).__init__()
        
        # Initialize the native Backtrader Ichimoku indicator
        self.ichimoku = bt.indicators.Ichimoku(
            self.data,
            tenkan=self.p.tenkan,
            kijun=self.p.kijun,
            senkou_span_b=self.p.senkou_span_b
        )
        
        # Map the lines from the native indicator to our lines
        self.lines.tenkan_sen = self.ichimoku.tenkan_sen
        self.lines.kijun_sen = self.ichimoku.kijun_sen
        self.lines.senkou_span_a = self.ichimoku.senkou_span_a
        self.lines.senkou_span_b = self.ichimoku.senkou_span_b
        self.lines.chikou_span = self.ichimoku.chikou_span 