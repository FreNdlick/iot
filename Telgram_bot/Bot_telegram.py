import os
import logging
import asyncio
import threading
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext
from dotenv import load_dotenv
from pymongo import MongoClient
from datetime import datetime

# Загрузка переменных окружения
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
MONGO_URL = os.getenv("MONGO_URL")
MONGO_DB = os.getenv("MONGO_DB")

# Подключение к MongoDB
client = MongoClient(MONGO_URL)
db = client[MONGO_DB]
anomalies_collection = db["anomalies"]

# Логирование
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)


# Обработчик команды /count_anomalies
async def count_anomalies(update: Update, context: CallbackContext) -> None:
    count = anomalies_collection.count_documents({})
    await update.message.reply_text(f"📊 Всего аномалий: {count}")


# Обработчик команды /list_anomalies
async def list_anomalies(update: Update, context: CallbackContext) -> None:
    count = anomalies_collection.count_documents({})  # Подсчитываем количество аномалий
    if count == 0:
        await update.message.reply_text("✅ Аномалий не зафиксировано.")
        return

    anomalies = anomalies_collection.find({}).sort("timestamp", -1).limit(10)

    message = "📌 *Последние аномалии:*\n"
    for anomaly in anomalies:
        message += (f"📍 Датчик: `{anomaly['sensor_id']}`\n"
                    f"⏰ Время: `{anomaly['timestamp']}`\n"
                    f"⚠ Данные: `{anomaly['data']}`\n"
                    f"----------------------\n")

    await update.message.reply_text(message, parse_mode="Markdown")


# Функция запуска бота
def main_bot():
    asyncio.set_event_loop(asyncio.new_event_loop())  # Создаем новый event loop

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("count_anomalies", count_anomalies))
    application.add_handler(CommandHandler("list_anomalies", list_anomalies))

    print("✅ Telegram-бот запущен!")
    application.run_polling()


# Запуск бота в отдельном потоке
if __name__ == "__main__":
    bot_thread = threading.Thread(target=main_bot, daemon=True, name="start_bot")
    bot_thread.start()
