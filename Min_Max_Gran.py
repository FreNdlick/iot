from pymongo import MongoClient
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime

def plot_sensor_data(ax, timestamps, values, sensor_name, value_name):
    if len(values) > 0:
        min_val = min(values)
        max_val = max(values)
        x_indices = range(len(values))
        ax.plot(x_indices, values, 'b-', linewidth=1)
        ax.axhline(y=min_val, color='r', linestyle='--', label=f'{min_val:.2f}')
        ax.axhline(y=max_val, color='g', linestyle='--', label=f'{max_val:.2f}')
        mean_value = np.mean(values)
        ax.axhline(y=mean_value, color='m', linestyle=':', label=f'{mean_value:.2f}')
        start_time = timestamps[0].strftime('%H:%M:%S')
        end_time = timestamps[-1].strftime('%H:%M:%S')
        ax.set_xticks([0, len(values)-1])
        ax.set_xticklabels([start_time, end_time])
        ax.legend(loc="upper left")
        ax.set_title(sensor_name)
        ax.set_ylabel(value_name)
        ax.grid(True)
    else:
        ax.text(0.5, 0.5, f'Нет данных для датчика {sensor_name}', ha='center', va='center')

def main():
    DB_NAME = "mqtt_database"
    COLLECTION_NAME = "your_collection"
    MAC_FIELD = "MacAddress"
    VALUE_FIELD = "Humidity"
    TIME_FIELD = "MsgTimeStamp"

    client = MongoClient('mongodb://localhost:27017/', connectTimeoutMS=30000)
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]

    mac_addresses = collection.distinct(MAC_FIELD)

    if not mac_addresses:
        print("В базе данных не найдено ни одного датчика.")
        return

    selected_macs = mac_addresses[:4]

    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    fig.suptitle('Данные датчиков температуры', fontsize=16)

    for i, mac in enumerate(selected_macs):
        row = i // 2
        col = i % 2
        ax = axes[row][col]
        query = {MAC_FIELD: mac}
        projection = {VALUE_FIELD: 1, TIME_FIELD: 1, "_id": 0}
        cursor = collection.find(query, projection).sort(TIME_FIELD, 1).limit(10000000)

        values = []
        timestamps = []
        for doc in cursor:
            try:
                val = float(doc[VALUE_FIELD])
                ts = datetime.fromisoformat(doc[TIME_FIELD])
                values.append(val)
                timestamps.append(ts)
            except (ValueError, KeyError, TypeError):
                continue

        plot_sensor_data(ax, timestamps, values, mac[-4:], VALUE_FIELD)

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.show()
    client.close()

if __name__ == "__main__":
    main()