import logging
import os
import pandas as pd
from telebot import TeleBot
from dotenv import load_dotenv
from telebot.types import Message
from Anomalies_Detected.anomaly_detection import detect_anomalies  # импортируем функцию для анализа аномалий
from mongo import init_db, fetch_data, fetch_data_for_period  # импортируем функции для получения данных из MongoDB

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
load_dotenv()
logger = logging.getLogger(__name__)

# Токен вашего бота
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

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


# Функция для проверки данных в MongoDB на наличие аномалий
def check_for_alerts(df):
    alerts = []

    # Проверка температуры
    if df['TemperatureC'].max() > thresholds['temperature_c']:
        alerts.append(f"Температура выше порога: {df['TemperatureC'].max()}°C")

    # Проверка влажности
    if df['Humidity'].max() > thresholds['humidity']:
        alerts.append(f"Влажность выше порога: {df['Humidity'].max()}%")

    return alerts


# Функция для отправки уведомлений о найденных аномалиях
def send_anomaly_alert(anomalies):
    for anomaly in anomalies:
        message = f"⚠️ *Anomaly Detected!*\n\nDetails:\n{anomaly}"
        try:
            bot.send_message(chat_id=os.environ.get('TELEGRAM_CHAT_ID'), text=message, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления: {e}")


# Обработчик команды /start
@bot.message_handler(commands=['start'])
def handle_start(message: Message):
    try:
        bot.send_message(message.chat.id,
                         'Привет! Я бот для уведомлений из MongoDB. Используй /alerts для получения текущих алертов.\n'
                         'Другие команды:\n'
                         '/anomalies — для получения уведомлений об аномалиях\n'
                         '/stats — для получения текущей статистики\n'
                         '/history — для получения истории аномалий\n'
                         '/set_threshold — для настройки пороговых значений.')
    except Exception as e:
        logger.error(f"Ошибка при обработке команды /start: {e}")


# Обработчик команды /alerts


# Функция для проверки активных алертов
def check_for_alerts(df):
    alerts = []

    # Проверяем только первую строку данных или конкретную строку (например, последнюю)
    if df.empty:
        return alerts  # Если данных нет, сразу возвращаем пустой список

    # Извлекаем значения для первой строки данных
    try:
        temperature_c = float(df.iloc[0]['TemperatureC'])  # Переводим в float для первой строки
        humidity = float(df.iloc[0]['Humidity'])  # Переводим в float для первой строки
    except ValueError as e:
        logger.error(f"Ошибка при преобразовании данных в float: {e}")
        return []

    # Проверяем на превышение пороговых значений
    if temperature_c > thresholds['temperature_c']:
        alerts.append(f"Температура выше порога: {temperature_c:.2f}°C")
    if humidity > thresholds['humidity']:
        alerts.append(f"Влажность выше порога: {humidity:.2f}%")

    return alerts


# Обработчик команды /alerts
@bot.message_handler(commands=['alerts'])
def handle_alerts(message: Message):
    try:
        # Получаем данные из базы
        df = fetch_data(collection_mq)

        # Проверяем на наличие аномалий
        alerts = check_for_alerts(df)

        if alerts:
            # Собираем все предупреждения в одном сообщении
            alert_message = "⚠️ *Alerts Detected!*\n\n"
            alert_message += "\n".join(alerts)
            bot.send_message(message.chat.id, alert_message, parse_mode='Markdown')
        else:
            bot.send_message(message.chat.id, "Нет активных алертов.")
    except Exception as e:
        logger.error(f"Ошибка при обработке команды /alerts: {e}")


# Обработчик команды /anomalies
@bot.message_handler(commands=['anomalies'])
def handle_anomalies(message: Message):
    try:
        # Получаем данные из базы
        df = fetch_data(collection_mq)

        # Если данные есть, проверяем их на аномалии
        if not df.empty:
            anomalies = detect_anomalies(df)
            if not anomalies.empty:
                # Создаем сообщение с аномалиями
                anomaly_message = "⚠️ *Аномалии обнаружены!*\n\n"

                # Преобразуем все аномалии в строку для отправки
                anomaly_message += anomalies.to_string()  # Преобразуем в строку (или можно кастомизировать вывод)

                # Отправляем уведомление о найденных аномалиях
                send_anomaly_alert(anomalies)  # Отправляем уведомление
                bot.send_message(message.chat.id, anomaly_message, parse_mode='Markdown')
            else:
                bot.send_message(message.chat.id, "Аномалий не обнаружено.")
        else:
            bot.send_message(message.chat.id, "Нет данных для анализа.")
    except Exception as e:
        logger.error(f"Ошибка при обработке команды /anomalies: {e}")


# Обработчик команды /stats
@bot.message_handler(commands=['stats'])
def handle_stats(message: Message):
    try:
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
    except Exception as e:
        logger.error(f"Ошибка при обработке команды /stats: {e}")


# Обработчик команды /history
@bot.message_handler(commands=['history'])
def handle_history(message: Message):
    try:
        # Получаем данные за последний период (например, последние 24 часа)
        df = fetch_data_for_period(collection_mq, period='24h')

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
    except Exception as e:
        logger.error(f"Ошибка при обработке команды /history: {e}")


# Обработчик команды /set_threshold
@bot.message_handler(commands=['set_threshold'])
def handle_set_threshold(message: Message):
    try:
        # Запрашиваем пороговое значение для температуры или влажности
        bot.send_message(message.chat.id, "Введите название параметра (temperature_c, humidity):")
        bot.register_next_step_handler(message, process_threshold_param)
    except Exception as e:
        logger.error(f"Ошибка при обработке команды /set_threshold: {e}")


def process_threshold_param(message: Message):
    try:
        param = message.text.strip().lower()

        if param not in thresholds:
            bot.send_message(message.chat.id, "Неверный параметр. Доступные параметры: temperature_c, humidity.")
            return

        bot.send_message(message.chat.id, f"Введите новое пороговое значение для {param}:")
        bot.register_next_step_handler(message, process_threshold_value, param)
    except Exception as e:
        logger.error(f"Ошибка при обработке порогового параметра: {e}")


def process_threshold_value(message: Message, param):
    try:
        value = float(message.text.strip())
        thresholds[param] = value
        bot.send_message(message.chat.id, f"Пороговое значение для {param} успешно установлено на {value}.")
    except ValueError:
        bot.send_message(message.chat.id, "Введите корректное числовое значение.")
    except Exception as e:
        logger.error(f"Ошибка при установке порогового значения для {param}: {e}")


# Основная функция для запуска бота
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
