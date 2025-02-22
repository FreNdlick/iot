import numpy as np
import pandas as pd
import os
from sklearn.ensemble import IsolationForest
from metricsPromet import  anomally_detected
import telegram
from dotenv import load_dotenv



# Инициализация бота Telegram
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
bot = telegram.Bot(token=TELEGRAM_TOKEN)




def detect_anomalies(dataframe):
    """
    Детекция аномалий с использованием Isolation Forest
    """
    if dataframe.empty:
        return []

    # Используем только числовые данные для анализа аномалий
    numeric_data = dataframe[['Humidity', 'TemperatureC', 'DewPointC']]

    # Применяем Isolation Forest
    model = IsolationForest(contamination=0.05)
    model.fit(numeric_data)

    # Прогноз аномалий
    predictions = model.predict(numeric_data)

    # Сигналы аномалии: -1 значит аномалия
    anomalies = dataframe[predictions == -1]

    if not anomalies.empty:
        message = f"Anomalies detected:\n{anomalies.to_string()}"
        bot.send_message(chat_id=CHAT_ID, text=message)
        anomally_detected.inc()  # Увеличиваем метрику о найденной аномалии

    return anomalies

