import os
import logging
import asyncio
import threading
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext, MessageHandler, filters
from dotenv import load_dotenv
from pymongo import MongoClient
from datetime import datetime, timedelta
from datetime import datetime
import matplotlib.pyplot as plt
import io


from Anomalies_Detected.anomaly_detector import process_sensor_data, toggle_analysis

load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
MONGO_URL = os.getenv("MONGO_URL")
MONGO_DB = os.getenv("MONGO_DB")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION")
ANOMALY_COLLECTION = os.getenv("ANOMALY_COLLECTION")

client = MongoClient(MONGO_URL)
db = client[MONGO_DB]
sensors_collection = db[MONGO_COLLECTION]
anomalies_collection = db[ANOMALY_COLLECTION]

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

analysis_enabled = True

SENSOR_IDS = ["000DE0163B57", "000DE0163B59", "000DE0163B58", "000DE0163B56"]

# /start
async def start(update: Update, context: CallbackContext) -> None:
    commands = (
        "<b>🤖 Доступные команды:</b>\n\n"
        "/start - Показать список команд\n"
        "/test_alert - тестовый алерт от prometheus\n"
        "/count_anomalies - Показать количество аномалий\n"
        "/list_anomalies - Показать последние аномалии\n"
        "/toggle_analysis - Включить/выключить анализ данных\n"
        "/info - Получить графики и значения\n"
        "/info_previous  последние 24х часовых записей\n"
        "\n"
        "<b>📝 Описание:</b>\n"
        "Этот бот анализирует данные с датчиков и уведомляет об аномалиях. "
        "Вы можете управлять анализом данных и просматривать статистику."
    )
    await update.message.reply_text(commands, parse_mode="HTML")

# /count_anomalies
async def count_anomalies(update: Update, context: CallbackContext) -> None:
    count = anomalies_collection.count_documents({})
    await update.message.reply_text(f"📊 Всего аномалий: {count}")

# /list_anomalies
async def info_previous(update: Update, context: CallbackContext) -> None:
    # Создаем кнопки для выбора датчика
    keyboard = [[sensor_id] for sensor_id in SENSOR_IDS]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    await update.message.reply_text("Выберите датчик для просмотра предыдущих 24 часов:", reply_markup=reply_markup)


# Обработчик выбора датчика для /info_previous
async def handle_sensor_selection_previous(update: Update, context: CallbackContext) -> None:
    sensor_id = update.message.text
    if sensor_id not in SENSOR_IDS:
        await update.message.reply_text("⚠ Неверный выбор датчика.")
        return

    # Находим последнюю запись для датчика
    latest_data = sensors_collection.find_one(
        {"MacAddress": sensor_id},
        sort=[("MsgTimeStamp", -1)]
    )

    if not latest_data:
        await update.message.reply_text(f"⚠ Нет данных для датчика {sensor_id}.")
        return

    # Преобразуем время последней записи в объект datetime
    latest_timestamp = datetime.strptime(latest_data["MsgTimeStamp"], "%Y-%m-%d %H:%M:%S")
    time_24_hours_before_latest = latest_timestamp - timedelta(hours=24)

    # Фильтруем данные за предыдущие 24 часа перед последней записью
    sensor_data = list(sensors_collection.find(
        {
            "MacAddress": sensor_id,
            "MsgTimeStamp": {
                "$gte": time_24_hours_before_latest.strftime("%Y-%m-%d %H:%M:%S"),
                "$lt": latest_data["MsgTimeStamp"]
            }
        }
    ).sort("MsgTimeStamp", 1))  # Сортируем по возрастанию времени

    if not sensor_data:
        await update.message.reply_text(f"⚠ Нет данных для датчика {sensor_id} за предыдущие 24 часа.")
        return

    # Извлекаем данные для графиков
    timestamps = [datetime.strptime(data["MsgTimeStamp"], "%Y-%m-%d %H:%M:%S") for data in sensor_data]
    temperature = [float(data["TemperatureC"]) for data in sensor_data]
    humidity = [float(data["Humidity"]) for data in sensor_data]
    dewpoint = [float(data["DewPointC"]) for data in sensor_data]

    # Определяем временной интервал
    start_time = timestamps[0].strftime("%Y-%m-%d %H:%M:%S")
    end_time = timestamps[-1].strftime("%Y-%m-%d %H:%M:%S")

    # Строим графики
    plt.figure(figsize=(10, 8))

    # График температуры
    plt.subplot(3, 1, 1)
    plt.plot(timestamps, temperature, label="Temperature (°C)", color="red")
    plt.title(f"Датчик {sensor_id} - Температура")
    plt.xlabel("Время")
    plt.ylabel("Температура (°C)")
    plt.legend()

    # График влажности
    plt.subplot(3, 1, 2)
    plt.plot(timestamps, humidity, label="Humidity (%)", color="blue")
    plt.title(f"Датчик {sensor_id} - Влажность")
    plt.xlabel("Время")
    plt.ylabel("Влажность (%)")
    plt.legend()

    # График точки росы
    plt.subplot(3, 1, 3)
    plt.plot(timestamps, dewpoint, label="Dew Point (°C)", color="green")
    plt.title(f"Датчик {sensor_id} - Точка росы")
    plt.xlabel("Время")
    plt.ylabel("Точка росы (°C)")
    plt.legend()

    # Сохраняем график в буфер
    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    plt.close()

    # Отправляем график
    await update.message.reply_photo(photo=buf, caption=f"Графики для датчика {sensor_id}")

    # Отправляем информацию об интервале
    await update.message.reply_text(f"📊 Графики построены за период: {start_time} — {end_time}")
async def list_anomalies(update: Update, context: CallbackContext) -> None:
    count = anomalies_collection.count_documents({})  # Подсчитываем количество аномалий
    if count == 0:
        await update.message.reply_text("✅ Аномалий не зафиксировано.")
        return

    anomalies = anomalies_collection.find({}).sort("MsgTimeStamp", -1).limit(10)

    message = "📌 *Последние аномалии:*\n"
    for anomaly in anomalies:
        message += (f"📍 Датчик: `{anomaly['sensor_id']}`\n"
                    f"⏰ Время: `{anomaly['MsgTimeStamp']}`\n"
                    f"⚠ Данные: `{anomaly['data']}`\n"
                    f"----------------------\n")

    await update.message.reply_text(message, parse_mode="Markdown")

# /toggle_analysis
async def toggle_analysis_command(update: Update, context: CallbackContext) -> None:
    global analysis_enabled
    analysis_enabled = not analysis_enabled
    status = "включен" if analysis_enabled else "выключен"
    await update.message.reply_text(f"Анализ данных {status}.")

# /info
async def info(update: Update, context: CallbackContext) -> None:
    # Создаем кнопки для выбора датчика
    keyboard = [[sensor_id] for sensor_id in SENSOR_IDS]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)

    await update.message.reply_text("Выберите датчик:", reply_markup=reply_markup)


#/ test_alert
async def test_alert(update: Update, context: CallbackContext) -> None:
    from metricsPromet import test_alert
    test_alert= 1;
    commands = (
        "Тестовый алерт сейчас будет отправлен\n"
        "Через prometheus_alertmanager"
    )

    await update.message.reply_text(commands, parse_mode="HTML")

async def handle_sensor_selection(update: Update, context: CallbackContext) -> None:
    sensor_id = update.message.text
    if sensor_id not in SENSOR_IDS:
        await update.message.reply_text("⚠ Неверный выбор датчика.")
        return

    # Вычисляем время 24 часа назад
    time_24_hours_ago = datetime.now() - timedelta(hours=24)

    # Фильтруем данные за последние 24 часа
    sensor_data = list(sensors_collection.find(
        {"MacAddress": sensor_id, "MsgTimeStamp": {"$gte": time_24_hours_ago.strftime("%Y-%m-%d %H:%M:%S")}}
    ).sort("MsgTimeStamp", 1))  # Сортируем по возрастанию времени

    if not sensor_data:
        await update.message.reply_text("⚠ Нет данных для выбранного датчика за последние 24 часа.")
        return

    # Извлекаем данные для графиков
    timestamps = [datetime.strptime(data["MsgTimeStamp"], "%Y-%m-%d %H:%M:%S") for data in sensor_data]
    temperature = [float(data["TemperatureC"]) for data in sensor_data]
    humidity = [float(data["Humidity"]) for data in sensor_data]
    dewpoint = [float(data["DewPointC"]) for data in sensor_data]

    # Определяем временной интервал
    start_time = timestamps[0].strftime("%Y-%m-%d %H:%M:%S")
    end_time = timestamps[-1].strftime("%Y-%m-%d %H:%M:%S")

    # Строим графики
    plt.figure(figsize=(10, 8))

    # График температуры
    plt.subplot(3, 1, 1)
    plt.plot(timestamps, temperature, label="Temperature (°C)", color="red")
    plt.title(f"Датчик {sensor_id} - Температура")
    plt.xlabel("Время")
    plt.ylabel("Температура (°C)")
    plt.legend()

    # График влажности
    plt.subplot(3, 1, 2)
    plt.plot(timestamps, humidity, label="Humidity (%)", color="blue")
    plt.title(f"Датчик {sensor_id} - Влажность")
    plt.xlabel("Время")
    plt.ylabel("Влажность (%)")
    plt.legend()

    # График точки росы
    plt.subplot(3, 1, 3)
    plt.plot(timestamps, dewpoint, label="Dew Point (°C)", color="green")
    plt.title(f"Датчик {sensor_id} - Точка росы")
    plt.xlabel("Время")
    plt.ylabel("Точка росы (°C)")
    plt.legend()

    # Сохраняем график в буфер
    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    plt.close()

    # Отправляем график
    await update.message.reply_photo(photo=buf, caption=f"Графики для датчика {sensor_id}")

    # Отправляем информацию об интервале
    await update.message.reply_text(f"📊 Графики построены за период: {start_time} — {end_time}")

    # Отправляем значения PM25 и AlarmStatus
    last_data = sensor_data[-1]  # Последняя запись
    message = (
        f"📊 Последние данные для датчика {sensor_id}:\n"
        f"🌫️ PM2.5: {last_data['PM25']}\n"
        f"🚨 Статус тревоги: {last_data['AlarmStatus']}"
    )
    await update.message.reply_text(message)
# Функция для проверки данных и отправки уведомлений
async def check_for_anomalies():
    while True:
        print("Начался анализ данных на поиск аномалий")
        if analysis_enabled:
            # Получаем последние данные из коллекции sensors
            latest_data = list(sensors_collection.find().sort("MsgTimeStamp", -1).limit(1))

            # Проверяем, есть ли данные
            if not latest_data:
                print("⚠ Нет данных для анализа.")
                await asyncio.sleep(10)  # Ждем перед следующей проверкой
                continue

            data = latest_data[0]  # Безопасный доступ к первому элементу

            # Проверяем наличие обязательных ключей в документе
            required_keys = ["MacAddress", "TemperatureC", "PM25", "AlarmStatus"]
            if not all(key in data for key in required_keys):
                print("⚠ Документ содержит неполные данные.")
                await asyncio.sleep(10)  # Ждем перед следующей проверкой
                continue

            # Извлекаем данные
            sensor_id = data["MacAddress"]
            value = float(data["TemperatureC"])  # Преобразуем в число
            pm25 = data["PM25"]
            alarm_status = data["AlarmStatus"]

            # Проверяем на аномалии
            is_anomaly = process_sensor_data(sensor_id, value, pm25, alarm_status)
            if is_anomaly:
                # Отправляем уведомление в Telegram
                message = (f"⚠ *Обнаружена аномалия!*\n"
                           f"📍 Датчик: `{sensor_id}`\n"
                           f"⏰ Время: `{data['MsgTimeStamp']}`\n"
                           f"📊 Температура: `{value}°C`\n"
                           f"🌫️ PM2.5: `{pm25}`\n"
                           f"🚨 Статус тревоги: `{alarm_status}`")
                await application.bot.send_message(chat_id=update.message.chat_id, text=message, parse_mode="Markdown")

        # Ждем 10 секунд перед следующей проверкой
        await asyncio.sleep(60)

# Функция запуска бота
def main_bot():
    global application
    asyncio.set_event_loop(asyncio.new_event_loop())  # Создаем новый event loop

    application = Application.builder().token(BOT_TOKEN).build()

    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("test_alert", test_alert))
    application.add_handler(CommandHandler("info_previous", info_previous))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_sensor_selection_previous))
    application.add_handler(CommandHandler("count_anomalies", count_anomalies))
    application.add_handler(CommandHandler("list_anomalies", list_anomalies))
    application.add_handler(CommandHandler("toggle_analysis", toggle_analysis_command))
    application.add_handler(CommandHandler("info", info))

    # Регистрируем обработчик выбора датчика
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_sensor_selection))

    # Запускаем фоновую задачу для проверки аномалий
    asyncio.get_event_loop().create_task(check_for_anomalies())

    print("✅ Telegram-бот запущен!")
    application.run_polling()

if __name__ == "__main__":
    bot_thread = threading.Thread(target=main_bot, daemon=True, name="start_bot")
    bot_thread.start()