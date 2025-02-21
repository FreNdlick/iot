import pandas as pd
from tkinter import messagebox

import pymongo

import os

def parse_and_plot_mongodb_data(database_name, collection_name, mac_address):
    client = pymongo.MongoClient(os.getenv("MONGO_URL"))
    db = client[database_name]
    collection = db[collection_name]

    query = {"MacAddress": mac_address}
    results = collection.find(query)
    #
    data = []
    for result in results:
        data.append({
            "MsgTimeStamp": pd.to_datetime(result["MsgTimeStamp"]),
            "Humidity": float(result["Humidity"]),
            "TemperatureC": float(result["TemperatureC"]),
            "TemperatureF": float(result["TemperatureF"]),
            "DewPointC": float(result["DewPointC"]),
            "DewPointF": float(result["DewPointF"]),
        })

    if not data:
        return pd.DataFrame()

    df = pd.DataFrame(data)
    return df