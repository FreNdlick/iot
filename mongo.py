from pymongo import MongoClient
from metricsPromet import mongodb_insertions
import pandas as pd
import json
from datetime import datetime, timedelta
import os
import numpy as np

def save_sensor_data(collection, sensor_data, metrics):
    """Сохранение данных сенсора и метрик в MongoDB"""
    doc = {
        'sensor_id': sensor_data.get('MacAddress'),
        'timestamp': sensor_data.get('MsgTimeStamp'),
        'data': {
            'pm25': sensor_data.get('PM25'),
            'temperature_c': sensor_data.get('TemperatureC'),
            'humidity': sensor_data.get('Humidity')
        },
        'metrics': {
            'current': {
                'pm25': metrics['pm25'][-1] if metrics['pm25'] else None,
                'temperature_c': metrics['temperature_c'][-1] if metrics['temperature_c'] else None
            },
            'stats': {
                'pm25_high': max(metrics['pm25']) if metrics['pm25'] else None,
                'pm25_low': min(metrics['pm25']) if metrics['pm25'] else None,
                'pm25_stddev': np.std(list(metrics['pm25'])) if len(metrics['pm25']) > 1 else None
            }
        }
    }
    collection.insert_one(doc)


def init_db(mongo_url, db_name):
    client = MongoClient(mongo_url)
    db = client[db_name]
    if not db.list_collection_names():
        db.create_collection("your_collection")
    collection = db["your_collection"]
    print(f"Initialized DB: {db_name}")
    return collection


def insert_data(collection, data):
    try:
        collection.insert_one(data)
        mongodb_insertions.inc()
        print(f"Data inserted successfully into Collection: {collection.name}")
    except Exception as e:
        print(f"Failed to insert data: {e}")


def fetch_data(collection, field_name="MsgTimeStamp", date_format="%Y-%m-%d %H:%M:%S"):
    try:
        data = list(collection.find({}, {field_name: 1, 'Humidity': 1, 'TemperatureC': 1, 'TemperatureF': 1, 'DewPointC': 1, 'DewPointF': 1, 'AlarmStatus': 1, '_id': 0}))

        if not data:
            raise ValueError("Коллекция пуста.")

        df = pd.DataFrame(data)

        if field_name not in df.columns:
            raise KeyError(f"Поле '{field_name}' не найдено.")

        try:
            df[field_name] = pd.to_datetime(df[field_name], format=date_format)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Ошибка преобразования даты: {e}")

        return df
    except Exception as e:
        print(f"Ошибка при получении данных: {e}")
        return pd.DataFrame()

def fetch_sensor_data_for_day():
    db_name = "mqtt_database"
    collection_name = "your_collection"
    mac_address = "000DE0163B56"
    output_folder = "json_import"
    target_date = "2024-11-23"
    client = MongoClient('mongodb://localhost:27017/')
    db = client[db_name]
    collection = db[collection_name]

    regex_pattern = f"^{target_date} .*"
    query = {
        "MacAddress": mac_address,
        "MsgTimeStamp": {
            "$regex": regex_pattern
        }
    }

    data = list(collection.find(query, {"_id": 0}))
    client.close()

    if not data:
        print(f"Данные для датчика {mac_address} за {target_date} не найдены.")
        return None

    json_data = json.dumps(data, indent=4)

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    filename = f"sensor_data_{mac_address}_{target_date}.json"
    file_path = os.path.join(output_folder, filename)

    # Сохраняем JSON в файл
    with open(file_path, "w", encoding="utf-8") as file:
        file.write(json_data)

    print(f"Данные сохранены в файл: {file_path}")
    return file_path
def fetch_data_for_period(collection, period='24h'):
    """
    Функция для получения данных за определенный период.
    :param collection: коллекция MongoDB
    :param period: строка с периодом ('24h', '7d', '30d', и т.д.)
    :return: DataFrame с данными за указанный период
    """
    try:
        # Получаем текущее время
        current_time = datetime.now()

        # Определяем временные рамки в зависимости от периода
        if period == '24h':
            start_time = current_time - timedelta(hours=24)
        elif period == '7d':
            start_time = current_time - timedelta(days=7)
        elif period == '30d':
            start_time = current_time - timedelta(days=30)
        else:
            raise ValueError(f"Неизвестный период: {period}")

        # Формируем запрос для MongoDB
        query = {
            'MsgTimeStamp': {
                '$gte': start_time
            }
        }

        # Получаем данные из коллекции
        data = list(collection.find(query))

        # Преобразуем данные в DataFrame
        df = pd.DataFrame(data)

        # Если данных нет, возвращаем пустой DataFrame
        if df.empty:
            raise ValueError(f"Нет данных за период {period}.")

        return df

    except Exception as e:
        print(f"Ошибка при получении данных за период {period}: {e}")
        return pd.DataFrame()

