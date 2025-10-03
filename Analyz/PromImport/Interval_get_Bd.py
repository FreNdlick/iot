from pymongo import MongoClient
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime


def remove_outliers(data, threshold=2):
    """
    Функция для удаления аномальных значений.
    """
    mean = np.mean(data)
    std = np.std(data)
    lower_bound = mean - threshold * std
    upper_bound = mean + threshold * std
    return [v for v in data if lower_bound <= v <= upper_bound]


def plot_sensor_data(ax, timestamps, values, sensor_name, value_name):
    """
    Рисует график для одного датчика, включая минимальное и максимальное значение,
    с удалением аномальных значений.
    """
    if len(values) > 0:
        # Удаление аномальных значений
        if sensor_name == '3B56':
            filtered_values = remove_outliers(values)
        else:
            filtered_values = values
        # Определение границ
        if filtered_values:
            min_value = min(filtered_values)
            max_value = max(filtered_values)
        else:
            min_value = None
            max_value = None

        # Построим график по индексам точек
        x_indices = range(len(filtered_values))
        ax.plot(x_indices, filtered_values, 'b-', linewidth=1)

        # Устанавливаем подпись на оси X (первая и последняя точка)
        start_time = timestamps[0].strftime('%Y-%m-%d %H:%M:%S')
        end_time = timestamps[-1].strftime('%Y-%m-%d %H:%M:%S')
        ax.set_xticks([0, len(filtered_values) - 1])
        ax.set_xticklabels([start_time, end_time])

        # Горизонтальные линии Min и Max
        if min_value is not None and max_value is not None:
            ax.axhline(y=min_value, color='r', linestyle='--', label=f'Min: {min_value:.2f}')
            ax.axhline(y=max_value, color='g', linestyle='--', label=f'Max: {max_value:.2f}')
            ax.legend(loc="upper left")

        ax.set_title(f'Датчик {sensor_name}')
        ax.set_ylabel(value_name)
        ax.grid(True)
    else:
        ax.text(0.5, 0.5, f'Нет данных для датчика {sensor_name}', ha='center', va='center')


def main():
    # Настройки
    DB_NAME = "mqtt_database"
    COLLECTION_NAME = "your_collection"
    MAC_FIELD = "MacAddress"
    VALUE_FIELD = "TemperatureC"  # Измените на нужное поле
    TIME_FIELD = "MsgTimeStamp"  # Измените если нужно

    # Подключение к MongoDB
    client = MongoClient('mongodb://localhost:27017/', connectTimeoutMS=30000)
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]

    # Получаем список уникальных датчиков
    unique_macs = collection.distinct(MAC_FIELD)
    print(f"Найдено датчиков: {len(unique_macs)}")

    # Создаем фигуру с 4 subplots (2x2)
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle(f'Показания датчиков ({VALUE_FIELD})', fontsize=16)

    # Для каждого датчика получаем данные и рисуем график
    for i, mac in enumerate(unique_macs[:4]):
        # Получаем данные для конкретного датчика
        query = {MAC_FIELD: mac}
        projection = {VALUE_FIELD: 1, TIME_FIELD: 1, "_id": 0}
        data = list(collection.find(query, projection).limit(100000000000))

        # Подготовка данных
        values = []
        timestamps = []
        for doc in data:
            try:
                val = float(doc.get(VALUE_FIELD))
                values.append(val)
                timestamps.append(datetime.fromisoformat(doc.get(TIME_FIELD)))
            except ValueError:
                continue

        # Выбираем оси для текущего графика
        ax = axes[i // 2, i % 2]
        plot_sensor_data(ax, timestamps, values, mac[-4:], VALUE_FIELD)

    plt.tight_layout()
    plt.show()
    client.close()


if __name__ == "__main__":
    main()