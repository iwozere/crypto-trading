import pandas as pd
import yfinance as yf

"""
Screening criteria:
- P/E < 25 — reasonable valuation
- ROE > 15% — capital efficiency
- Debt/Equity < 100% — moderate debt
- Free Cash Flow > 0
- Price > 50D > 200D — positive momentum
"""

# Step 1: Download SIX ticker list
def get_six_tickers():
	url = 'https://www.six-group.com/sheldon/equity_issuers/v1/equity_issuers.csv'
	tables = pd.read_html(url)
	tickers = tables[0]['Symbol'].tolist()
	tickers = [t.replace('.', '-') for t in tickers] # Convert for yfinance    
	return tickers
	
# Step 2: Screening and filtering by metrics
def screen_stocks(tickers):
	results = []
	for ticker in tickers:
		try:
			stock = yf.Ticker(ticker)
			info = stock.info
			pe = info.get("trailingPE", None)
			roe = info.get("returnOnEquity", None)
			debt_equity = info.get("debtToEquity", None)
			fcf = info.get("freeCashflow", 0)
			price = info.get("currentPrice", None)
			fifty_day = info.get("fiftyDayAverage", None)
			two_hundred_day = info.get("twoHundredDayAverage", None)
			if all([pe, roe, debt_equity, price, fifty_day, two_hundred_day]):
				if (
					pe < 25 and
					roe > 0.15 and
					debt_equity < 100 and
					fcf and fcf > 0 and
					price > fifty_day > two_hundred_day
				):
					results.append({
						'Ticker': ticker,
						'P/E': round(pe, 2),
						'ROE %': round(roe * 100, 1),
						'D/E': round(debt_equity, 1),
						'Price': price,
						'50D Avg': round(fifty_day, 2),
						'200D Avg': round(two_hundred_day, 2)
					})
		except Exception as e:
			print(f"{ticker}: {e}")
	return pd.DataFrame(results)
		
# Main
if __name__ == "__main__":
	print("Loading SIX tickers...")
	tickers = get_six_tickers()
	print(f"Found {len(tickers)} tickers")
	print("Screening by fundamental and technical criteria...")
	df = screen_stocks(tickers)
	print(f"\n=== Selected {len(df)} stocks ===")
	print(df)
	df.to_csv("six_selected_stocks.csv", index=False)
	print("Results saved to six_selected_stocks.csv")