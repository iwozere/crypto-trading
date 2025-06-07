# ticker_bot/analyzer/models.py

from dataclasses import dataclass
from typing import Optional


@dataclass
class TickerAnalysis:
    ticker: str
    company_name: str
    current_price: float

    # Fundamental
    market_cap: Optional[str]
    pe_ratio: Optional[float]
    forward_pe: Optional[float]
    dividend_yield: Optional[float]
    earnings_per_share: Optional[float]

    # Technical
    rsi: Optional[float]
    sma_50: Optional[float]
    sma_200: Optional[float]
    macd_signal: Optional[float]
    trend: Optional[str]

    # Resume
    recommendation: Optional[str]
