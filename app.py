import os
from dotenv import load_dotenv
from metricsPromet import create_sensor_metrics
from Request import start_api_client
import threading
from prometheus_client import start_http_server
import Telgram_bot.bot_app
from Telgram_bot.bot_app import main_bot   # Импортируем функцию для запуска бота

# Инициализация бд + мккти
load_dotenv()
MONGO_URL = os.getenv("MONGO_URL")
MONGO_DB = os.getenv("MONGO_DB")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION")

MQTT_BROKER_ADDRESS = os.getenv("MQTT_BROKER_ADDRESS")
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT"))
MQTT_TOPICS = os.getenv("MQTT_TOPICS").split(',')
BASE_URL = "http://air.krasn.ru/api/2.0/data"


def main():
    global collection_mq, collection_api
    start_http_server(8000)  # Запуск Prometheus сервер
    from mongo import init_db
    collection_mq = init_db(MONGO_URL, MONGO_DB)
    collection_api = init_db(MONGO_URL, "api_database")

    from mongo import fetch_sensor_data_for_day
    result_file = fetch_sensor_data_for_day()
    print(f"Файл сохранен: {result_file}")

    sensor_metrics = {
        "000DE0163B57": create_sensor_metrics("000DE0163B57"),
        "000DE0163B59": create_sensor_metrics("000DE0163B59"),
        "000DE0163B58": create_sensor_metrics("000DE0163B58"),
        "000DE0163B56": create_sensor_metrics("000DE0163B56")
    }

    from mqqt import start_mqtt_client

    # Запуск API клиента в отдельном потоке
    """"
    api_client_thread = threading.Thread(target=start_api_client, args=(BASE_URL, collection_api))
    api_client_thread.daemon = True
    api_client_thread.start()
    """
    # Запуск MQTT клиента

    # Запуск бота в отдельном потоке
    bot_thread = threading.Thread(target=main_bot)
    bot_thread.daemon = True
    bot_thread.start()
    start_mqtt_client(MQTT_BROKER_ADDRESS, MQTT_BROKER_PORT, MQTT_TOPICS, collection_mq, sensor_metrics)

    # Основной поток продолжает работать с MQTT и API
    try:
        bot_thread.join()  # Это заставит основной поток ожидать завершения работы бота
    except Exception as e:
        print(f"Ошибка при запуске бота: {e}")


if __name__ == "__main__":
    main()
