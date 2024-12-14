from pymongo import MongoClient
from metricsPromet import mongodb_insertions
import pandas as pd

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