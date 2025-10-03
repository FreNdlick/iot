import os
import logging
import asyncio
import threading
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext, MessageHandler, filters
from dotenv import load_dotenv
from pymongo import MongoClient
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import io
import requests
import re
from prometheus_client import Gauge
from Anomalies_Detected.anomaly_detector import process_sensor_data, toggle_analysis

load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://localhost:9090")
PUSHGATEWAY_URL = os.getenv("PUSHGATEWAY_URL", "http://localhost:9091")
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


def query_prometheus(metric_name, start_time, end_time, step="2m"):
    try:
        query = f'{metric_name}'
        params = {
            "query": query,
            "start": start_time.timestamp(),
            "end": end_time.timestamp(),
            "step": step
        }
        response = requests.get(f"{PROMETHEUS_URL}/api/v1/query_range", params=params)
        response.raise_for_status()
        result = response.json()
        if result["status"] == "success" and result["data"]["result"]:
            values = result["data"]["result"][0]["values"]
            return [(float(timestamp), float(value)) for timestamp, value in values]
        return []
    except Exception as e:
        logging.error(f"Ошибка при запросе Prometheus: {e}")
        return []


def send_test_timeseries(metric_name, values, timestamps):
    try:
        data = ""
        for ts, value in zip(timestamps, values):
            data += f'{metric_name} {value} {int(ts.timestamp() * 1000)}\n'
        response = requests.post(f"{PUSHGATEWAY_URL}/metrics/job/test_job", data=data)
        response.raise_for_status()
        logging.info(f"Тестовый временной ряд для {metric_name} отправлен")
    except Exception as e:
        logging.error(f"Ошибка при отправке временного ряда в Pushgateway: {e}")


async def send_test_alert_graph(chat_id):
    end_time = datetime.now()
    start_time = end_time - timedelta(minutes=10)

    test_data = query_prometheus('anomaly_test', start_time, end_time)

    if not test_data:
        await application.bot.send_message(chat_id=chat_id,
                                           text="⚠ Нет данных для anomaly_test за последние 10 минут в Prometheus.")
        return

    timestamps = [datetime.fromtimestamp(ts) for ts, _ in test_data]
    values = [value for _, value in test_data]

    plt.figure(figsize=(8, 4))
    plt.plot(timestamps, values, label="anomaly_test", color="blue", marker="o")
    plt.axhline(y=1.0, color="red", linestyle="--", label="Порог алерта")
    if values:
        plt.plot(timestamps[-1], values[-1], 'bo', markersize=10, label="Последняя точка")
    plt.title("Тестовый алерт (anomaly_test) за последние 10 минут")
    plt.xlabel("Время")
    plt.ylabel("Значение")
    plt.legend()

    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    plt.close()

    await application.bot.send_photo(chat_id=chat_id, photo=buf, caption="График тестового алерта (anomaly_test)")


# тест построения графика в интервал
async def send_anomaly_graph(chat_id, sensor_id):
    end_time = datetime.now()
    start_time = end_time - timedelta(minutes=30)

    temp_data = query_prometheus(f'mqtt_{sensor_id}_temperature_c', start_time, end_time)
    humidity_data = query_prometheus(f'mqtt_{sensor_id}_humidity', start_time, end_time)
    dewpoint_data = query_prometheus(f'mqtt_{sensor_id}_dew_point_c', start_time, end_time)

    temp_upper = query_prometheus(f'mqtt_{sensor_id}_temp_upper_q', start_time, end_time)[-1][1] if query_prometheus(
        f'mqtt_{sensor_id}_temp_upper_q', start_time, end_time) else 30.0
    temp_lower = query_prometheus(f'mqtt_{sensor_id}_temp_lower_q', start_time, end_time)[-1][1] if query_prometheus(
        f'mqtt_{sensor_id}_temp_lower_q', start_time, end_time) else 10.0
    humidity_upper = query_prometheus(f'mqtt_{sensor_id}_humidity_upper_q', start_time, end_time)[-1][
        1] if query_prometheus(f'mqtt_{sensor_id}_humidity_upper_q', start_time, end_time) else 80.0
    humidity_lower = query_prometheus(f'mqtt_{sensor_id}_humidity_lower_q', start_time, end_time)[-1][
        1] if query_prometheus(f'mqtt_{sensor_id}_humidity_lower_q', start_time, end_time) else 20.0
    dewpoint_upper = query_prometheus(f'mqtt_{sensor_id}_dew_point_upper_q', start_time, end_time)[-1][
        1] if query_prometheus(f'mqtt_{sensor_id}_dew_point_upper_q', start_time, end_time) else 20.0
    dewpoint_lower = query_prometheus(f'mqtt_{sensor_id}_dew_point_lower_q', start_time, end_time)[-1][
        1] if query_prometheus(f'mqtt_{sensor_id}_dew_point_lower_q', start_time, end_time) else 0.0

    if not temp_data or not humidity_data or not dewpoint_data:
        await application.bot.send_message(chat_id=chat_id,
                                           text=f"⚠ Нет данных для датчика {sensor_id} за последние 30 минут в Prometheus.")
        return

    timestamps = [datetime.fromtimestamp(ts) for ts, _ in temp_data]
    temperature = [value for _, value in temp_data]
    humidity = [value for _, value in humidity_data]
    dewpoint = [value for _, value in dewpoint_data]

    plt.figure(figsize=(10, 8))

    plt.subplot(3, 1, 1)
    plt.plot(timestamps, temperature, label="Температура (°C)", color="red", marker="o")
    plt.axhline(y=temp_upper, color="orange", linestyle="--", label="Верхняя граница (95%)")
    plt.axhline(y=temp_lower, color="purple", linestyle="--", label="Нижняя граница (5%)")
    if temperature:
        plt.plot(timestamps[-1], temperature[-1], 'ro', markersize=10, label="Аномалия")
    plt.title(f"Датчик {sensor_id} - Температура (последние 30 минут)")
    plt.xlabel("Время")
    plt.ylabel("Температура (°C)")
    plt.legend()

    plt.subplot(3, 1, 2)
    plt.plot(timestamps, humidity, label="Влажность (%)", color="blue", marker="o")
    plt.axhline(y=humidity_upper, color="orange", linestyle="--", label="Верхняя граница (95%)")
    plt.axhline(y=humidity_lower, color="purple", linestyle="--", label="Нижняя граница (5%)")
    if humidity:
        plt.plot(timestamps[-1], humidity[-1], 'bo', markersize=10, label="Аномалия")
    plt.title(f"Датчик {sensor_id} - Влажность")
    plt.xlabel("Время")
    plt.ylabel("Влажность (%)")
    plt.legend()

    plt.subplot(3, 1, 3)
    plt.plot(timestamps, dewpoint, label="Точка росы (°C)", color="green", marker="o")
    plt.axhline(y=dewpoint_upper, color="purple", linestyle="--", label="Верхняя граница (95%)")
    plt.axhline(y=dewpoint_lower, color="orange", linestyle="--", label="Нижняя граница (5%)")
    if dewpoint:
        plt.plot(timestamps[-1], dewpoint[-1], 'go', markersize=10, label="Аномалия")
    plt.title(f"Датчик {sensor_id} - Точка росы")
    plt.xlabel("Время")
    plt.ylabel("Точка росы (°C)")
    plt.legend()

    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    plt.close()

    await application.bot.send_photo(chat_id=chat_id, photo=buf,
                                     caption=f"График аномалии для {sensor_id} за последние 30 минут")


# Middleware для перехвата сообщений
async def message_interceptor(update: Update, context: CallbackContext) -> None:
    if update.message and update.message.text:
        message_text = update.message.text
        if "🚨" in message_text or "⚠️" in message_text:
            match = re.search(r"Датчик: ([^\s]+)", message_text)
            if match:
                sensor_id = match.group(1)
                if sensor_id in SENSOR_IDS:
                    await send_anomaly_graph(update.message.chat_id, sensor_id)
        elif "Тестовый алерт" in message_text:
            await send_test_alert_graph(update.message.chat_id)


# /test_alert запуск
async def test_alert(update: Update, context: CallbackContext) -> None:
    end_time = datetime.now()
    start_time = end_time - timedelta(minutes=10)
    num_points = 5
    timestamps = [start_time + timedelta(minutes=i * 10 / (num_points - 1)) for i in range(num_points)]
    test_values = [0.0] * (num_points - 1) + [1.0]
    send_test_timeseries("anomaly_test", test_values, timestamps)
    test_alert.set(1.0)
    await update.message.reply_text(
        f"✅ Тестовый временной ряд для anomaly_test отправлен. Ожидайте алерт и график через ~5 минут.",
        parse_mode="HTML"
    )

# geter из prometheus
def query_prometheus(metric_name, start_time, end_time, step="2m"):
    try:
        query = f'{metric_name}'
        params = {
            "query": query,
            "start": start_time.timestamp(),
            "end": end_time.timestamp(),
            "step": step
        }
        response = requests.get(f"{PROMETHEUS_URL}/api/v1/query_range", params=params)
        response.raise_for_status()
        result = response.json()
        if result["status"] == "success" and result["data"]["result"]:
            values = result["data"]["result"][0]["values"]
            return [(float(timestamp), float(value)) for timestamp, value in values]
        return []
    except Exception as e:
        logging.error(f"Ошибка при запросе Prometheus: {e}")
        return []


## это для создания job в прометеус
def send_test_timeseries(metric_name, values, timestamps):
    try:
        data = ""
        for ts, value in zip(timestamps, values):
            data += f'{metric_name} {value} {int(ts.timestamp() * 1000)}\n'
        response = requests.post(f"{PUSHGATEWAY_URL}/metrics/job/test_job", data=data)
        response.raise_for_status()
        logging.info(f"Тестовый временной ряд для {metric_name} отправлен")
    except Exception as e:
        logging.error(f"Ошибка при отправке временного ряда в Pushgateway: {e}")

#тестовы для алерта с рядом
async def send_test_alert_graph(chat_id):
    end_time = datetime.now()
    start_time = end_time - timedelta(minutes=10)

    test_data = query_prometheus('anomaly_test', start_time, end_time)

    if not test_data:
        await application.bot.send_message(chat_id=chat_id,
                                           text="⚠ Нет данных для anomaly_test за последние 10 минут в Prometheus.")
        return

    timestamps = [datetime.fromtimestamp(ts) for ts, _ in test_data]
    values = [value for _, value in test_data]

    plt.figure(figsize=(8, 4))
    plt.plot(timestamps, values, label="anomaly_test", color="blue", marker="o")
    plt.axhline(y=1.0, color="red", linestyle="--", label="Порог алерта")
    if values:
        plt.plot(timestamps[-1], values[-1], 'bo', markersize=10, label="Последняя точка")
    plt.title("Тестовый алерт (anomaly_test) за последние 10 минут")
    plt.xlabel("Время")
    plt.ylabel("Значение")
    plt.legend()
    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    plt.close()

    await application.bot.send_photo(chat_id=chat_id, photo=buf, caption="График тестового алерта (anomaly_test)")


# test отправки графика. Смотреть middleware
async def send_anomaly_graph(chat_id, sensor_id):
    end_time = datetime.now()
    start_time_30 = end_time - timedelta(minutes=30)
    start_time_10 = end_time - timedelta(minutes=10)

    temp_data = query_prometheus(f'mqtt_{sensor_id}_temperature_c', start_time_30, end_time)
    humidity_data = query_prometheus(f'mqtt_{sensor_id}_humidity', start_time_30, end_time)
    dewpoint_data = query_prometheus(f'mqtt_{sensor_id}_dew_point_c', start_time_30, end_time)

    interval = 30
    if not any([temp_data, humidity_data, dewpoint_data]):
        interval = 10
        temp_data = query_prometheus(f'mqtt_{sensor_id}_temperature_c', start_time_10, end_time)
        humidity_data = query_prometheus(f'mqtt_{sensor_id}_humidity', start_time_10, end_time)
        dewpoint_data = query_prometheus(f'mqtt_{sensor_id}_dew_point_c', start_time_10, end_time)

    if not any([temp_data, humidity_data, dewpoint_data]):
        logging.warning(f"Нет данных для датчика {sensor_id} за {interval} минут")
        await application.bot.send_message(chat_id=chat_id,
                                           text=f"⚠ Нет данных для датчика {sensor_id} за последние {interval} минут в Prometheus.")
        return

    temp_upper = query_prometheus(f'mqtt_{sensor_id}_temp_upper_q', start_time_30, end_time)[-1][1] if query_prometheus(
        f'mqtt_{sensor_id}_temp_upper_q', start_time_30, end_time) else 30.0
    temp_lower = query_prometheus(f'mqtt_{sensor_id}_temp_lower_q', start_time_30, end_time)[-1][1] if query_prometheus(
        f'mqtt_{sensor_id}_temp_lower_q', start_time_30, end_time) else 10.0
    humidity_upper = query_prometheus(f'mqtt_{sensor_id}_humidity_upper_q', start_time_30, end_time)[-1][
        1] if query_prometheus(f'mqtt_{sensor_id}_humidity_upper_q', start_time_30, end_time) else 80.0
    humidity_lower = query_prometheus(f'mqtt_{sensor_id}_humidity_lower_q', start_time_30, end_time)[-1][
        1] if query_prometheus(f'mqtt_{sensor_id}_humidity_lower_q', start_time_30, end_time) else 20.0
    dewpoint_upper = query_prometheus(f'mqtt_{sensor_id}_dew_point_upper_q', start_time_30, end_time)[-1][
        1] if query_prometheus(f'mqtt_{sensor_id}_dew_point_upper_q', start_time_30, end_time) else 20.0
    dewpoint_lower = query_prometheus(f'mqtt_{sensor_id}_dew_point_lower_q', start_time_30, end_time)[-1][
        1] if query_prometheus(f'mqtt_{sensor_id}_dew_point_lower_q', start_time_30, end_time) else 0.0
    plt.figure(figsize=(10, 8))
    plot_count = 0

    if temp_data:
        plot_count += 1
        timestamps = [datetime.fromtimestamp(ts) for ts, _ in temp_data]
        temperature = [value for _, value in temp_data]
        plt.subplot(3, 1, plot_count)
        plt.plot(timestamps, temperature, label="Температура (°C)", color="red", marker="o")
        plt.axhline(y=temp_upper, color="orange", linestyle="--", label="Верхняя граница (95%)")
        plt.axhline(y=temp_lower, color="purple", linestyle="--", label="Нижняя граница (5%)")
        plt.plot(timestamps[-1], temperature[-1], 'ro', markersize=10, label="Последняя точка")
        plt.title(f"Датчик {sensor_id} - Температура (последние {interval} минут)")
        plt.xlabel("Время")
        plt.ylabel("Температура (°C)")
        plt.legend()

    if humidity_data:
        plot_count += 1
        timestamps = [datetime.fromtimestamp(ts) for ts, _ in humidity_data]
        humidity = [value for _, value in humidity_data]
        plt.subplot(3, 1, plot_count)
        plt.plot(timestamps, humidity, label="Влажность (%)", color="blue", marker="o")
        plt.axhline(y=humidity_upper, color="orange", linestyle="--", label="Верхняя граница (95%)")
        plt.axhline(y=humidity_lower, color="purple", linestyle="--", label="Нижняя граница (5%)")
        plt.plot(timestamps[-1], humidity[-1], 'bo', markersize=10, label="Последняя точка")
        plt.title(f"Датчик {sensor_id} - Влажность (последние {interval} минут)")
        plt.xlabel("Время")
        plt.ylabel("Влажность (%)")
        plt.legend()

    if dewpoint_data:
        plot_count += 1
        timestamps = [datetime.fromtimestamp(ts) for ts, _ in dewpoint_data]
        dewpoint = [value for _, value in dewpoint_data]
        plt.subplot(3, 1, plot_count)
        plt.plot(timestamps, dewpoint, label="Точка росы (°C)", color="green", marker="o")
        plt.axhline(y=dewpoint_upper, color="orange", linestyle="--", label="Верхняя граница (95%)")
        plt.axhline(y=dewpoint_lower, color="purple", linestyle="--", label="Нижняя граница (5%)")
        plt.plot(timestamps[-1], dewpoint[-1], 'go', markersize=10, label="Последняя точка")
        plt.title(f"Датчик {sensor_id} - Точка росы (последние {interval} минут)")
        plt.xlabel("Время")
        plt.ylabel("Точка росы (°C)")
        plt.legend()

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    plt.close()

    await application.bot.send_photo(chat_id=chat_id, photo=buf,
                                     caption=f"График аномалии для {sensor_id} за последние {interval} минут")


async def message_interceptor(update: Update, context: CallbackContext) -> None:
    if update.message and update.message.text:
        message_text = update.message.text
        logging.debug(f"Получено сообщение: {message_text}")
        if "🚨" in message_text or "⚠️" in message_text:
            match = re.search(r"Датчик: ([^\s]+)", message_text)
            if match:
                sensor_id = match.group(1)
                # Исправляем возможную опечатку
                if sensor_id.startswith("000DE0163B5") and sensor_id not in SENSOR_IDS:
                    for valid_id in SENSOR_IDS:
                        if valid_id.startswith(sensor_id[:10]):
                            sensor_id = valid_id
                            logging.info(f"Исправлен ID датчика: {match.group(1)} -> {sensor_id}")
                            break
                if sensor_id in SENSOR_IDS:
                    logging.info(f"Обрабатываем аномалию для датчика {sensor_id}")
                    await send_anomaly_graph(update.message.chat_id, sensor_id)
                else:
                    logging.warning(f"Датчик {sensor_id} не найден в SENSOR_IDS")
                    await application.bot.send_message(chat_id=update.message.chat_id,
                                                       text=f"⚠ Датчик {sensor_id} не найден.")
        elif "Тестовый алерт" in message_text:
            logging.info("Обрабатываем тестовый алерт")
            await send_test_alert_graph(update.message.chat_id)


# /test_alert
async def test_alert(update: Update, context: CallbackContext) -> None:
    end_time = datetime.now()
    start_time = end_time - timedelta(minutes=10)
    num_points = 5
    timestamps = [start_time + timedelta(minutes=i * 10 / (num_points - 1)) for i in range(num_points)]
    test_values = [0.0] * (num_points - 1) + [1.0]

    send_test_timeseries("anomaly_test", test_values, timestamps)
    test_alert.set(1.0)

    await update.message.reply_text(
        f"✅ Тестовый временной ряд для anomaly_test отправлен. Ожидайте алерт",
        parse_mode="HTML"
    )
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
    keyboard = [[sensor_id] for sensor_id in SENSOR_IDS]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    await update.message.reply_text("Выберите датчик для просмотра предыдущих 24 часов:", reply_markup=reply_markup)


#/info_previous выбор
async def handle_sensor_selection_previous(update: Update, context: CallbackContext) -> None:
    sensor_id = update.message.text
    if sensor_id not in SENSOR_IDS:
        await update.message.reply_text("⚠ Неверный выбор датчика.")
        return
    latest_data = sensors_collection.find_one(
        {"MacAddress": sensor_id},
        sort=[("MsgTimeStamp", -1)]
    )
    if not latest_data:
        await update.message.reply_text(f"⚠ Нет данных для датчика {sensor_id}.")
        return
    latest_timestamp = datetime.strptime(latest_data["MsgTimeStamp"], "%Y-%m-%d %H:%M:%S")
    time_24_hours_before_latest = latest_timestamp - timedelta(hours=24)
    sensor_data = list(sensors_collection.find(
        {
            "MacAddress": sensor_id,
            "MsgTimeStamp": {
                "$gte": time_24_hours_before_latest.strftime("%Y-%m-%d %H:%M:%S"),
                "$lt": latest_data["MsgTimeStamp"]
            }
        }
    ).sort("MsgTimeStamp", 1))
    if not sensor_data:
        await update.message.reply_text(f"⚠ Нет данных для датчика {sensor_id} за предыдущие 24 часа.")
        return
    timestamps = [datetime.strptime(data["MsgTimeStamp"], "%Y-%m-%d %H:%M:%S") for data in sensor_data]
    temperature = [float(data["TemperatureC"]) for data in sensor_data]
    humidity = [float(data["Humidity"]) for data in sensor_data]
    dewpoint = [float(data["DewPointC"]) for data in sensor_data]
    start_time = timestamps[0].strftime("%Y-%m-%d %H:%M:%S")
    end_time = timestamps[-1].strftime("%Y-%m-%d %H:%M:%S")
    plt.figure(figsize=(10, 8))
    plt.subplot(3, 1, 1)

    plt.plot(timestamps, temperature, label="Temperature (°C)", color="red")
    plt.title(f"Датчик {sensor_id} - Температура")
    plt.xlabel("Время")
    plt.ylabel("Температура (°C)")
    plt.legend()
    plt.subplot(3, 1, 2)
    plt.plot(timestamps, humidity, label="Humidity (%)", color="blue")
    plt.title(f"Датчик {sensor_id} - Влажность")
    plt.xlabel("Время")
    plt.ylabel("Влажность (%)")
    plt.legend()
    plt.subplot(3, 1, 3)
    plt.plot(timestamps, dewpoint, label="Dew Point (°C)", color="green")
    plt.title(f"Датчик {sensor_id} - Точка росы")
    plt.xlabel("Время")
    plt.ylabel("Точка росы (°C)")
    plt.legend()
    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    plt.close()
    await update.message.reply_photo(photo=buf, caption=f"Графики для датчика {sensor_id}")
    await update.message.reply_text(f"📊 Графики построены за период: {start_time} — {end_time}")

##Вывод аномалий
async def list_anomalies(update: Update, context: CallbackContext) -> None:
    count = anomalies_collection.count_documents({})
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
    keyboard = [[sensor_id] for sensor_id in SENSOR_IDS]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    await update.message.reply_text("Выберите датчик:", reply_markup=reply_markup)



async def handle_sensor_selection(update: Update, context: CallbackContext) -> None:
    sensor_id = update.message.text
    if sensor_id not in SENSOR_IDS:
        await update.message.reply_text("⚠ Неверный выбор датчика.")
        return
    time_24_hours_ago = datetime.now() - timedelta(hours=24)

    sensor_data = list(sensors_collection.find(
        {"MacAddress": sensor_id, "MsgTimeStamp": {"$gte": time_24_hours_ago.strftime("%Y-%m-%d %H:%M:%S")}}
    ).sort("MsgTimeStamp", 1))

    if not sensor_data:
        await update.message.reply_text("⚠ Нет данных для выбранного датчика за последние 24 часа.")
        return
    timestamps = [datetime.strptime(data["MsgTimeStamp"], "%Y-%m-%d %H:%M:%S") for data in sensor_data]
    temperature = [float(data["TemperatureC"]) for data in sensor_data]
    humidity = [float(data["Humidity"]) for data in sensor_data]
    dewpoint = [float(data["DewPointC"]) for data in sensor_data]

    start_time = timestamps[0].strftime("%Y-%m-%d %H:%M:%S")
    end_time = timestamps[-1].strftime("%Y-%m-%d %H:%M:%S")
    plt.figure(figsize=(10, 8))

    plt.subplot(3, 1, 1)
    plt.plot(timestamps, temperature, label="Temperature (°C)", color="red")
    plt.title(f"Датчик {sensor_id} - Температура")
    plt.xlabel("Время")
    plt.ylabel("Температура (°C)")
    plt.legend()

    plt.subplot(3, 1, 2)
    plt.plot(timestamps, humidity, label="Humidity (%)", color="blue")
    plt.title(f"Датчик {sensor_id} - Влажность")
    plt.xlabel("Время")
    plt.ylabel("Влажность (%)")
    plt.legend()

    plt.subplot(3, 1, 3)
    plt.plot(timestamps, dewpoint, label="Dew Point (°C)", color="green")
    plt.title(f"Датчик {sensor_id} - Точка росы")
    plt.xlabel("Время")
    plt.ylabel("Точка росы (°C)")
    plt.legend()

    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    plt.close()

    await update.message.reply_photo(photo=buf, caption=f"Графики для датчика {sensor_id}")

    await update.message.reply_text(f"📊 Графики за период:\n {start_time} — {end_time}")

    last_data = sensor_data[-1]
    message = (
        f"📊 Последние данные для датчика {sensor_id}:\n"
        f"🌫️ PM2.5: {last_data['PM25']}\n"
        f"🚨 Статус тревоги: {last_data['AlarmStatus']}"
    )
    await update.message.reply_text(message)


##Проверка на наличие аномалий (Коммент)
async def check_for_anomalies():
    while True:
        print("Начался анализ данных на поиск аномалий")
        if analysis_enabled:
            latest_data = list(sensors_collection.find().sort("MsgTimeStamp", -1).limit(1))
            if not latest_data:
                print("⚠ Нет данных для анализа.")
                await asyncio.sleep(10)
                continue
            data = latest_data[0]
            required_keys = ["MacAddress", "TemperatureC", "PM25", "AlarmStatus"]
            if not all(key in data for key in required_keys):
                print("⚠ Документ содержит неполные данные.")
                await asyncio.sleep(10)
                continue

            sensor_id = data["MacAddress"]
            value = float(data["TemperatureC"])
            pm25 = data["PM25"]
            alarm_status = data["AlarmStatus"]

            is_anomaly = process_sensor_data(sensor_id, value, pm25, alarm_status)
            if is_anomaly:
                message = (f"⚠ *Обнаружена аномалия!*\n"
                           f"📍 Датчик: `{sensor_id}`\n"
                           f"⏰ Время: `{data['MsgTimeStamp']}`\n"
                           f"📊 Температура: `{value}°C`\n"
                           f"🌫️ PM2.5: `{pm25}`\n"
                           f"🚨 Статус тревоги: `{alarm_status}`")
                await application.bot.send_message(chat_id=update.message.chat_id, text=message, parse_mode="Markdown")

        await asyncio.sleep(60)

def main_bot():
    global application
    asyncio.set_event_loop(asyncio.new_event_loop())
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("test_alert", test_alert))
    application.add_handler(CommandHandler("info_previous", info_previous))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_sensor_selection_previous))
    application.add_handler(CommandHandler("count_anomalies", count_anomalies))
    application.add_handler(CommandHandler("list_anomalies", list_anomalies))
    application.add_handler(CommandHandler("toggle_analysis", toggle_analysis_command))
    application.add_handler(CommandHandler("info", info))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_sensor_selection))
    application.add_handler(MessageHandler(filters.TEXT & filters.UpdateType.MESSAGE, message_interceptor), group=1)

    #asyncio.get_event_loop().create_task(check_for_anomalies())
    print("✅ Telegram-бот запущен!")
    application.run_polling()

if __name__ == "__main__":
    bot_thread = threading.Thread(target=main_bot, daemon=True, name="start_bot")
    bot_thread.start()