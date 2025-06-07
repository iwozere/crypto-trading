import yfinance as yf


def calculate_technicals(ticker: str) -> dict:
    try:
        df = yf.download(ticker, period="6mo", interval="1d")
        df.dropna(inplace=True)

        # SMA
        df["SMA_50"] = df["Close"].rolling(window=50).mean()
        df["SMA_200"] = df["Close"].rolling(window=200).mean()

        # RSI (14)
        delta = df["Close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df["RSI"] = 100 - (100 / (1 + rs))

        # MACD
        exp1 = df["Close"].ewm(span=12, adjust=False).mean()
        exp2 = df["Close"].ewm(span=26, adjust=False).mean()
        df["MACD"] = exp1 - exp2
        df["Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()

        # Определение тренда
        last_close = df["Close"].iloc[-1]
        sma50 = df["SMA_50"].iloc[-1]
        sma200 = df["SMA_200"].iloc[-1]
        rsi = df["RSI"].iloc[-1]
        macd_signal = df["Signal"].iloc[-1]

        trend = (
            "Uptrend"
            if sma50 > sma200 and last_close > sma50
            else "Downtrend" if sma50 < sma200 and last_close < sma50 else "Sideways"
        )

        return {
            "rsi": round(rsi, 2),
            "sma_50": round(sma50, 2),
            "sma_200": round(sma200, 2),
            "macd_signal": round(macd_signal, 2),
            "trend": trend,
        }

    except Exception as e:
        print(f"[ERROR] Technical analysis failed for {ticker}: {e}")
        return {}
