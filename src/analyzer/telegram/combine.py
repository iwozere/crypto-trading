from dataclasses import dataclass
from src.analyzer.telegram.fundamentals import get_fundamentals
from src.analyzer.telegram.technicals import calculate_technicals
from src.analyzer.telegram.chart import generate_price_chart

@dataclass
class TickerAnalysis:
    ticker: str
    fundamentals: dict
    technicals: dict
    chart_image: bytes  # PNG-image as bytes

def analyze_ticker(ticker: str) -> TickerAnalysis:
    fundamentals = get_fundamentals(ticker)
    technicals = calculate_technicals(ticker)
    chart_image = generate_price_chart(ticker)

    return TickerAnalysis(
        ticker=ticker.upper(),
        fundamentals=fundamentals,
        technicals=technicals,
        chart_image=chart_image
    )
