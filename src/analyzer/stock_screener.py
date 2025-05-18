import yfinance as yf
import pandas as pd

class StockScreener:
    def __init__(self, stock_data):
        self.stock_data = stock_data

    def filter_by_price(self, min_price, max_price):
        return [stock for stock in self.stock_data if min_price <= stock['price'] <= max_price]

    def filter_by_volume(self, min_volume):
        return [stock for stock in self.stock_data if stock['volume'] >= min_volume]

    def filter_by_market_cap(self, min_market_cap):
        return [stock for stock in self.stock_data if stock['market_cap'] >= min_market_cap]

    def screen_stocks(self, tickers):
        results = []
        for ticker in tickers:
            try:
                symbol = f'{ticker}.SW'
                stock = yf.Ticker(symbol)
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

    def get_fcf_growth(ticker):
        try:
            t = yf.Ticker(ticker)
            cf = t.cashflow
            if cf.empty or 'Total Cash From Operating Activities' not in cf.index or 'Capital Expenditures' not in cf.index:
                return None

            ocf = cf.loc['Total Cash From Operating Activities']
            capex = cf.loc['Capital Expenditures']
            fcf = ocf + capex

            fcf = fcf.dropna().astype(float)
            fcf = fcf[::-1]  # from old to new

            is_positive = (fcf > 0).all()
            is_growing = all(earlier <= later for earlier, later in zip(fcf, fcf[1:]))

            return {
                "Ticker": ticker,
                "FCF Positive": is_positive,
                "FCF Growing": is_growing,
                "FCF (oldest → newest)": list(fcf)
            }

        except Exception as e:
            return {"Ticker": ticker, "Error": str(e)}
