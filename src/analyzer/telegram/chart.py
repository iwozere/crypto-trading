# ticker_bot/analyzer/chart.py

import yfinance as yf
import matplotlib.pyplot as plt
import io
import matplotlib.dates as mdates

def generate_price_chart(ticker: str) -> bytes:
    try:
        df = yf.download(ticker, period="6mo", interval="1d")
        df.dropna(inplace=True)

        df["SMA_50"] = df["Close"].rolling(window=50).mean()
        df["SMA_200"] = df["Close"].rolling(window=200).mean()

        plt.style.use("seaborn-v0_8-darkgrid")
        fig, ax = plt.subplots(figsize=(10, 5))

        ax.plot(df.index, df["Close"], label="Close Price", linewidth=2)
        ax.plot(df.index, df["SMA_50"], label="SMA 50", linestyle="--")
        ax.plot(df.index, df["SMA_200"], label="SMA 200", linestyle="--")

        ax.set_title(f"{ticker} Price Chart with SMA")
        ax.set_xlabel("Date")
        ax.set_ylabel("Price")
        ax.legend()
        ax.grid(True)

        # Формат даты на оси X
        ax.xaxis.set_major_locator(mdates.MonthLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
        fig.autofmt_xdate()

        # Сохраняем в байты
        buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format="png")
        plt.close(fig)
        buf.seek(0)

        return buf.read()

    except Exception as e:
        print(f"[ERROR] Failed to generate chart for {ticker}: {e}")
        return buf.read()
