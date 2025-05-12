import os
import threading
import time
import subprocess
from pathlib import Path
from dotenv import load_dotenv
from prometheus_client import start_http_server
from metricsPromet import create_sensor_metrics
from Request import start_api_client
from Telgram_bot.bot_app import main_bot  # Импортируем функцию для запуска бота
from Telgram_bot.Bot_telegram import  main_bot

# Инициализация переменных окружения
load_dotenv()
MONGO_URL = os.getenv("MONGO_URL")
MONGO_DB = os.getenv("MONGO_DB")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION")

MQTT_BROKER_ADDRESS = os.getenv("MQTT_BROKER_ADDRESS")
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT"))
MQTT_TOPICS = os.getenv("MQTT_TOPICS").split(',')
BASE_URL = "http://air.krasn.ru/api/2.0/data"


def main():
    try:


        try:
            base = Path(__file__).parent

            # Запуск Prometheus с конфигурационным файлом
            prometheus_path = base / "tools" / "prometheus-2.54.1.windows-amd64" / "prometheus.exe"
            prometheus_config = base / "tools" / "prometheus-2.54.1.windows-amd64" / "prometheus.yml"
            subprocess.Popen([
                str(prometheus_path),
                f"--config.file={prometheus_config}"
            ])

            # Запуск Alertmanager с конфигурационным файлом
            alertmanager_path = base / "tools" / "alertmanager-0.28.0.windows-amd64" / "alertmanager.exe"
            alertmanager_config = base / "tools" / "alertmanager-0.28.0.windows-amd64" / "alertmanager.yml"
            subprocess.Popen([
                str(alertmanager_path),
                f"--config.file={alertmanager_config}"
            ])

            print("Сервисы запущены")
        except Exception as e:
            print(f"Ошибка: {e}")

        # Запуск Prometheus сервера
        print("Prometheus server started on port 8000")
        start_http_server(8000)

        from mongo import init_db, fetch_sensor_data_for_day
        collection_mq = init_db(MONGO_URL, MONGO_DB)
        collection_api = init_db(MONGO_URL, "api_database")

        # Получение данных о сенсорах за день
        result_file = fetch_sensor_data_for_day()
        print(f"Файл сохранен: {result_file}")

        # Инициализация метрик для сенсоров

        sensor_metrics= {
            "000DE0163B57": create_sensor_metrics("000DE0163B57"),
            "000DE0163B59": create_sensor_metrics("000DE0163B59"),
            "000DE0163B58": create_sensor_metrics("000DE0163B58"),
            "000DE0163B56": create_sensor_metrics("000DE0163B56")
        }
        print("Sensor metrics initialized:", sensor_metrics)

        from mqqt import start_mqtt_client

        # Запуск API клиента в отдельном потоке
        #api_client_thread = threading.Thread(target=start_api_client, args=(BASE_URL, collection_api), daemon=True)
        #api_client_thread.start()
        print("API client thread started")

        # Запуск Telegram-бота в отдельном потоке
        def start_bot():
            try:
                main_bot()
            except Exception as e:
                print(f"Ошибка при запуске бота: {e}")

        bot_thread = threading.Thread(target=start_bot, daemon=True).start()
        print("Telegram bot thread started")

        # Запуск MQTT клиента
        try:
            start_mqtt_client(MQTT_BROKER_ADDRESS, MQTT_BROKER_PORT, MQTT_TOPICS, collection_mq, sensor_metrics)
        except Exception as e:
            print(f"Ошибка в запуске prometheus {e}")
        try:
            while True:
                time.sleep(1)  # Небольшая задержка, чтобы не нагружать цп
        except KeyboardInterrupt:
            print("Остановка программы")
    except Exception as e:
        print(f"Ошибка в main: {e}")

if __name__ == "__main__":
    main()
