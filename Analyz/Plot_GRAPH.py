from pymongo import MongoClient
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt


def plot_temperature_by_date_range(start_date_str, end_date_str, mac_address="000DE0163B58", db_name="mqtt_database",
                                   collection_name="your_collection", y_min=None, y_max=None):
    """
    Функция для построения графика температуры по заданному диапазону дат.

    Параметры:
    - start_date_str: Начальная дата в формате 'YYYY-MM-DD' или 'YYYY-MM-DDTHH:MM:SS'
    - end_date_str: Конечная дата в формате 'YYYY-MM-DD' или 'YYYY-MM-DDTHH:MM:SS'
    - mac_address: MAC-адрес устройства (по умолчанию "000DE0163B58")
    - db_name: Имя базы данных (по умолчанию "mqtt_database")
    - collection_name: Имя коллекции (по умолчанию "your_collection")
    - y_min: Минимальное значение по оси Y (опционально)
    - y_max: Максимальное значение по оси Y (опционально)
    """
    # Преобразование строк дат в datetime объекты
    try:
        start_date = datetime.fromisoformat(start_date_str)
        end_date = datetime.fromisoformat(end_date_str)
    except ValueError:
        raise ValueError("Даты должны быть в формате ISO: 'YYYY-MM-DD' или 'YYYY-MM-DDTHH:MM:SS'")

    # Если дата указана без времени, скорректируем end_date на конец дня
    if 'T' not in end_date_str:
        end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
    if 'T' not in start_date_str:
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)

    # Подключение к MongoDB
    client = MongoClient("mongodb://localhost:27017/")
    collection = client[db_name][collection_name]

    # Запрос данных за период (предполагая, что MsgTimeStamp - строка в ISO формате)
    query = {
        "MacAddress": mac_address,
        "MsgTimeStamp": {"$gte": start_date.isoformat(), "$lte": end_date.isoformat()}
    }
    data = list(collection.find(query, {"TemperatureC": 1, "MsgTimeStamp": 1, "_id": 0}).sort("MsgTimeStamp", 1))

    if not data:
        print("Нет данных за указанный период.")
        client.close()
        return

    values = []
    timestamps = []
    for doc in data:
        try:
            values.append(float(doc["TemperatureC"]))
            timestamps.append(datetime.fromisoformat(doc["MsgTimeStamp"]))
        except (KeyError, ValueError):
            continue

    if not values:
        print("Нет валидных данных за указанный период.")
        client.close()
        return

    # Построение графика
    plt.figure(figsize=(12, 6))
    plt.plot(timestamps, values, 'b-', linewidth=0.5)  # Уменьшили linewidth для более плотного вида, убрали маркеры
    plt.title(f"Интервал 1: {start_date_str} - {end_date_str} ({len(values)} точек)", fontsize=14)
    plt.xlabel("Время", fontsize=12)
    plt.ylabel("Температура (°C)", fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.xticks(rotation=45)
    if y_min is not None and y_max is not None:
        plt.ylim(y_min, y_max)
    plt.tight_layout()
    plt.show()

    # Закрытие соединения
    client.close()

# Пример использования:
plot_temperature_by_date_range("2025-01-01T12:00", "2025-01-04T12:00", y_min=19.5, y_max=29)