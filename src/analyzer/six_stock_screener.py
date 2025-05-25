import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import pandas as pd
import yfinance as yf
from src.analyzer.stock_screener import StockScreener
from src.analyzer.tickers_list import get_six_tickers
import datetime
from typing import Any, Dict, Optional
"""
Screening criteria:
- P/E < 25 — reasonable valuation
- ROE > 15% — capital efficiency
- Debt/Equity < 100% — moderate debt
- Free Cash Flow > 0
- Price > 50D > 200D — positive momentum
"""


class SixStockScreener(StockScreener):
	def __init__(self):
		super().__init__(stock_data=None)
		
# Main
if __name__ == "__main__":
	print("Loading SIX tickers...")
	tickers = get_six_tickers()
	print(f"Found {len(tickers)} tickers")
	print("Screening by fundamental and technical criteria...")
	screener = SixStockScreener()
	df = screener.screen_stocks(tickers)
	print(f"\n=== Selected {len(df)} stocks ===")
	print(df)
	df.to_csv("six_selected_stocks.csv", index=False)
	print("Results saved to six_selected_stocks.csv")
 