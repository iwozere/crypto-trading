# ticker_bot/bot.py

import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import FSInputFile
from aiogram.utils import executor

from src.analyzer.telegram.combine import analyze_ticker

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")  # Установи переменную окружения

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)


@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    await message.reply("📊 Отправь тикер (например: AAPL или TSLA), и я пришлю анализ компании.")


@dp.message_handler(lambda message: message.text and message.text.strip().isalnum())
async def handle_ticker(message: types.Message):
    ticker = message.text.strip().upper()
    await message.reply(f"🔍 Анализирую {ticker}...")

    try:
        result = analyze_ticker(ticker)

        # Формируем текст ответа
        text = (
            f"📈 <b>{result.ticker}</b>\n\n"
            f"💵 Цена: ${result.fundamentals.price:.2f}\n"
            f"🏦 P/E: {result.fundamentals.pe_ratio:.2f}, EPS: {result.fundamentals.eps:.2f}\n"
            f"💸 Доходы: ${result.fundamentals.revenue / 1e9:.2f}B, Прибыль: ${result.fundamentals.net_income / 1e9:.2f}B\n"
            f"📉 RSI: {result.technicals.rsi:.2f}, MACD: {result.technicals.macd:.2f}, Signal: {result.technicals.macd_signal:.2f}\n"
            f"📊 MA(50): {result.technicals.ma50:.2f}, MA(200): {result.technicals.ma200:.2f}"
        )

        # Сохраняем график во временный файл
        chart_path = f"/tmp/{ticker}_chart.png"
        with open(chart_path, "wb") as f:
            f.write(result.chart_image)

        await bot.send_photo(chat_id=message.chat.id, photo=FSInputFile(chart_path), caption=text, parse_mode="HTML")

    except Exception as e:
        logging.exception("Ошибка анализа")
        await message.reply(f"⚠️ Ошибка анализа тикера {ticker}: {str(e)}")


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
