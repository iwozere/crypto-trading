import yfinance as yf


def get_fundamentals(ticker: str) -> dict:
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        return {
            "ticker": ticker.upper(),
            "company_name": info.get("shortName", "Unknown"),
            "current_price": info.get("currentPrice") or info.get("regularMarketPrice"),
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "dividend_yield": info.get("dividendYield"),
            "earnings_per_share": info.get("trailingEps"),
        }
    except Exception as e:
        print(f"[ERROR] Failed to get fundamentals for {ticker}: {e}")
        return {}
