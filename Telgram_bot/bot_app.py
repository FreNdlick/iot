import logging
import os
import requests
import pandas as pd
from telebot import TeleBot
from dotenv import load_dotenv
from telebot.types import Message
from Anomalies_Detected.anomaly_detection import detect_anomalies  # импортируем функцию для анализа аномалий
from mongo import init_db, fetch_data, fetch_data_for_period  # импортируем функции для получения данных из MongoDB
from prometheus_client import Gauge

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
load_dotenv()
logger = logging.getLogger(__name__)

# Токен вашего ботаa
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# URL Prometheus API
PROMETHEUS_URL = os.environ.get('PROMETHEUS_URL')

# Создание экземпляра бота
bot = TeleBot(TELEGRAM_TOKEN)

# Словарь для хранения порогов аномалий
thresholds = {
    'temperature_c': 25.0,
    'humidity': 60.0
}

# Инициализация коллекции MongoDB
MONGO_URL = os.getenv("MONGO_URL")
MONGO_DB = os.getenv("MONGO_DB")
collection_mq = init_db(MONGO_URL, MONGO_DB)  # Инициализируем коллекцию MongoDB

# Функция для получения данных из Prometheus
def get_prometheus_alert():
    query = 'ALERTS{alertstate="firing"}'
    try:
        response = requests.get(PROMETHEUS_URL, params={'query': query})
        logger.debug(f"Ответ от Prometheus: {response.status_code}")
    except requests.exceptions.RequestException as e:
        logger.error(f'Ошибка при получении данных от Prometheus: {e}')
        return None

    if response.status_code == 200:
        data = response.json()
        if data['data']['result']:
            return data['data']['result']

    logger.warning(f'Prometheus вернул статус-код {response.status_code}. Данные могут быть неверными.')
    return None


# Функция для отправки уведомлений о найденных аномалиях
def send_anomaly_alert(anomalies):
    for anomaly in anomalies:
        message = f"⚠️ *Anomaly Detected!*\n\nDetails:\n{anomaly.to_string()}"
        bot.send_message(chat_id=os.environ.get('TELEGRAM_CHAT_ID'), text=message, parse_mode='Markdown')


# Обработчик команды /start
@bot.message_handler(commands=['start'])
def handle_start(message: Message):
    bot.send_message(message.chat.id,
                     'Привет! Я бот для уведомлений из Prometheus. Используй /alerts для получения текущих алертов.\n'
                     'Другие команды:\n'
                     '/anomalies — для получения уведомлений об аномалиях\n'
                     '/stats — для получения текущей статистики\n'
                     '/history — для получения истории аномалий\n'
                     '/set_threshold — для настройки пороговых значений.')


# Обработчик команды /alerts
@bot.message_handler(commands=['alerts'])
def handle_alerts(message: Message):
    alerts = get_prometheus_alert()
    if alerts:
        for alert in alerts:
            alert_name = alert['metric'].get('alertname')
            alert_state = alert['metric'].get('alertstate')
            alert_message = f'*Alert:* `{alert_name}`\n*State:* `{alert_state}`'
            bot.send_message(message.chat.id, alert_message, parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id, "Нет активных алертов.")


# Обработчик команды /anomalies
@bot.message_handler(commands=['anomalies'])
def handle_anomalies(message: Message):
    # Получаем данные из базы
    df = fetch_data(collection_mq)

    # Если данные есть, проверяем их на аномалии
    if not df.empty:
        anomalies = detect_anomalies(df)
        if not anomalies.empty:
            send_anomaly_alert(anomalies)  # Отправляем уведомление
            bot.send_message(message.chat.id, "Аномалии были найдены и отправлены.")
        else:
            bot.send_message(message.chat.id, "Аномалий не обнаружено.")
    else:
        bot.send_message(message.chat.id, "Нет данных для анализа.")


# Обработчик команды /stats
@bot.message_handler(commands=['stats'])
def handle_stats(message: Message):
    # Получаем текущие метрики или статистику
    df = fetch_data(collection_mq)

    if not df.empty:
        stats_message = f"Текущая статистика:\n"
        stats_message += f"Общее количество записей: {len(df)}\n"
        stats_message += f"Средняя температура: {df['TemperatureC'].mean():.2f}°C\n"
        stats_message += f"Средняя влажность: {df['Humidity'].mean():.2f}%"
        bot.send_message(message.chat.id, stats_message)
    else:
        bot.send_message(message.chat.id, "Нет данных для статистики.")


# Обработчик команды /history
@bot.message_handler(commands=['history'])
def handle_history(message: Message):
    # Получаем данные за последний период (например, последние 24 часа)
    df = fetch_data_for_period(collection_mq, period='24h')  # Теперь используем функцию из mongo.py

    if not df.empty:
        history_message = f"История аномалий за последние 24 часа:\n"
        anomalies = detect_anomalies(df)
        if not anomalies.empty:
            history_message += anomalies.to_string()
            send_anomaly_alert(anomalies)  # Отправляем уведомление
        else:
            history_message += "Аномалий за этот период не найдено."
        bot.send_message(message.chat.id, history_message)
    else:
        bot.send_message(message.chat.id, "Нет данных за указанный период.")


# Обработчик команды /set_threshold
@bot.message_handler(commands=['set_threshold'])
def handle_set_threshold(message: Message):
    # Запрашиваем пороговое значение для температуры или влажности
    bot.send_message(message.chat.id, "Введите название параметра (temperature_c, humidity):")
    bot.register_next_step_handler(message, process_threshold_param)


def process_threshold_param(message: Message):
    param = message.text.strip().lower()

    if param not in thresholds:
        bot.send_message(message.chat.id, "Неверный параметр. Доступные параметры: temperature_c, humidity.")
        return

    bot.send_message(message.chat.id, f"Введите новое пороговое значение для {param}:")
    bot.register_next_step_handler(message, process_threshold_value, param)


def process_threshold_value(message: Message, param):
    try:
        value = float(message.text.strip())
        thresholds[param] = value
        bot.send_message(message.chat.id, f"Пороговое значение для {param} успешно установлено на {value}.")
    except ValueError:
        bot.send_message(message.chat.id, "Введите корректное числовое значение.")


# Основная функция для запуска бота
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main_bot():
    try:
        logger.info("Бот запускается...")
        bot.polling(none_stop=True)
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        # Дополнительные логи для отладки
        logger.debug("Попытка перезапуска бота...")

if __name__ == "__main__":
    main_bot()


