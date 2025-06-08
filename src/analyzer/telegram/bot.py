# ticker_bot/bot.py
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

import logging
import tempfile
import asyncio

from aiogram import Bot, Dispatcher, types
from aiogram.types import FSInputFile
from aiogram.filters import Command
from aiogram.types import Message
from src.analyzer.telegram.combine import analyze_ticker
from config.donotshare.donotshare import TELEGRAM_BOT_TOKEN

logging.basicConfig(level=logging.INFO)

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable is not set")

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start", "help"))
async def send_welcome(message: Message):
    await message.reply(
        "📊 Send a ticker symbol (e.g., AAPL, TSLA, BTC-USD), and I'll analyze it for you.\n\n"
        "Available commands:\n"
        "/start or /help - Show this message"
    )

@dp.message(lambda message: message.text and message.text.strip().isalnum())
async def handle_ticker(message: Message):
    ticker = message.text.strip().upper()
    await message.reply(f"🔍 Analyzing {ticker}...")

    try:
        result = analyze_ticker(ticker)

        # Format response text
        text = (
            f"📈 <b>{result.ticker}</b> - {result.fundamentals.company_name or 'Unknown'}\n\n"
            f"💵 Price: ${result.fundamentals.current_price or 0.0:.2f}\n"
            f"🏦 P/E: {result.fundamentals.pe_ratio or 0.0:.2f}, Forward P/E: {result.fundamentals.forward_pe or 0.0:.2f}\n"
            f"💸 Market Cap: ${(result.fundamentals.market_cap or 0.0)/1e9:.2f}B\n"
            f"📊 EPS: ${result.fundamentals.earnings_per_share or 0.0:.2f}, Div Yield: {(result.fundamentals.dividend_yield or 0.0)*100:.2f}%\n\n"
            f"📉 Technical Analysis:\n"
            f"RSI: {result.technicals.rsi:.2f}\n"
            f"MA(50): ${result.technicals.sma_50:.2f}\n"
            f"MA(200): ${result.technicals.sma_200:.2f}\n"
            f"MACD Signal: {result.technicals.macd_signal:.2f}\n"
            f"Trend: {result.technicals.trend}\n\n"
            f"📊 Bollinger Bands:\n"
            f"Upper: ${result.technicals.bb_upper:.2f}\n"
            f"Middle: ${result.technicals.bb_middle:.2f}\n"
            f"Lower: ${result.technicals.bb_lower:.2f}\n"
            f"Width: {result.technicals.bb_width:.4f}\n\n"
            f"🎯 Recommendation: {result.recommendation}"
        )

        # Save chart to temporary file
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
            temp_file.write(result.chart_image)
            temp_file.flush()
            
            await bot.send_photo(
                chat_id=message.chat.id,
                photo=FSInputFile(temp_file.name),
                caption=text,
                parse_mode="HTML"
            )
            
        # Clean up the temporary file
        os.unlink(temp_file.name)

    except Exception as e:
        logging.exception("Analysis error")
        await message.reply(
            f"⚠️ Error analyzing {ticker}:\n"
            f"Please check if the ticker symbol is correct and try again."
        )

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
