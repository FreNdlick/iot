import os
from dotenv import load_dotenv
from metricsPromet import create_sensor_metrics
from Request import start_api_client
import threading
from prometheus_client import start_http_server



##инициализация бд + мккти
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
    start_http_server(8000)

    from mongo import init_db
    collection_mq = init_db(MONGO_URL, MONGO_DB)
    collection_api = init_db(MONGO_URL, "api_database")

    sensor_metrics = {
        "000DE0163B57": create_sensor_metrics("000DE0163B57"),
        "000DE0163B59": create_sensor_metrics("000DE0163B59"),
        "000DE0163B58": create_sensor_metrics("000DE0163B58"),
        "000DE0163B56": create_sensor_metrics("000DE0163B56")
    }
    from mqqt import start_mqtt_client

    api_client_thread = threading.Thread(target=start_api_client, args=(BASE_URL, collection_api))
    api_client_thread.daemon = True
    api_client_thread.start()

    start_mqtt_client(MQTT_BROKER_ADDRESS, MQTT_BROKER_PORT, MQTT_TOPICS, collection_mq, sensor_metrics)

if __name__ == "__main__":
    main()