from pymongo import MongoClient
from datetime import datetime
from dotenv import load_dotenv
import os
import numpy as np

# Подключение к MongoDB
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
MONGO_URL = os.getenv("MONGO_URL")
MONGO_DB = os.getenv("MONGO_DB")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION")
client = MongoClient(MONGO_URL)
db = client[MONGO_DB]
anomalies_collection = db["anomalies"]

sensors_collection = db[MONGO_COLLECTION]

# ID датчиков
SENSOR_IDS = ["000DE0163B57", "000DE0163B59", "000DE0163B58", "000DE0163B56"]

# Глобальный словарь для отслеживания состояний аномалий
anomaly_states = {sensor_id: False for sensor_id in SENSOR_IDS}


# Функция вычисления динамических границ
def calculate_dynamic_bounds(sensor_id):
    data = list(sensors_collection.find({"sensor_id": sensor_id}).sort("timestamp", -1).limit(100))

    if not data:
        return None, None  # Нет данных

    values = [entry["value"] for entry in data if "value" in entry]

    if len(values) < 10:
        return None, None  # Недостаточно данных

    q1, q3 = np.percentile(values, [25, 75])
    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr  # Оптимальная граница
    upper_bound = q3 + 1.5 * iqr  # Экстремальная граница

    return lower_bound, upper_bound


# Функция проверки данных на аномалии
def check_anomaly(sensor_id, value, pm25, alarm_status):
    lower_bound, upper_bound = calculate_dynamic_bounds(sensor_id)
    is_anomaly = False

    if lower_bound is not None and upper_bound is not None:
        if value < lower_bound or value > upper_bound:
            is_anomaly = True  # Выход за границы

    if alarm_status == "On" or pm25 != "0":
        is_anomaly = True  # Условия аномалии

    return is_anomaly


# Функция обработки новых данных
def process_sensor_data(sensor_id, value, pm25, alarm_status):
    global anomaly_states

    is_anomaly = check_anomaly(sensor_id, value, pm25, alarm_status)

    if is_anomaly and not anomaly_states[sensor_id]:
        # Фиксируем начало аномалии
        anomaly_states[sensor_id] = True
        anomaly_record = {
            "sensor_id": sensor_id,
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            "data": {"value": value, "PM25": pm25, "AlarmStatus": alarm_status}
        }
        anomalies_collection.insert_one(anomaly_record)
        print(f"⚠ Аномалия зафиксирована: {anomaly_record}")

    elif not is_anomaly and anomaly_states[sensor_id]:
        # Завершаем аномалию
        anomaly_states[sensor_id] = False
        print(f"✅ Аномалия на датчике {sensor_id} закончилась.")

