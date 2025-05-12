import paho.mqtt.client as mqtt
import json
import logging
from metricsPromet import mqtt_messages_received, active_mqtt_subscriptions, mongodb_insertions

from Analyz.metrics_process import metrics_processor
from prometheus_client import Gauge
test_gauge = Gauge('test_metric', 'Test metric')
test_gauge.set(10)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("Connected to MQTT Broker!")
        for topic in userdata["topics"]:
            client.subscribe(topic)
            active_mqtt_subscriptions.inc()
            logger.info(f"Subscribed to topic: {topic}")
    else:
        logger.error(f"Failed to connect, return code {rc}")


def on_message(client, userdata, msg):
    print(f"RAW MQTT message: {msg.payload}")
    try:
        data = json.loads(msg.payload.decode())
        logger.info(f"Received message on topic {msg.topic}: {data}")

        mac_address = data.get('MacAddress')
        if not mac_address:
            logger.error("Missing MacAddress in message")
            return

        logger.info(f"Processing data for sensor {mac_address}")

        # Проверяем, есть ли метрики для этого датчика
        if mac_address not in userdata["sensor_metrics"]:
            logger.warning(f"No metrics configured for sensor {mac_address}")
            return

        metrics = userdata["sensor_metrics"][mac_address]

        try:
            # Обновляем метрики
            metrics['pm25'].set(float(data.get('PM25', 0)))
            metrics['humidity'].set(float(data.get('Humidity', 0)))
            metrics['temperature_c'].set(float(data.get('TemperatureC', 0)))
            metrics['temperature_f'].set(float(data.get('TemperatureF', 0)))
            metrics['dew_point_c'].set(float(data.get('DewPointC', 0)))
            metrics['dew_point_f'].set(float(data.get('DewPointF', 0)))
            metrics['alarm_status'].set(1 if data.get('AlarmStatus', '').lower() == 'on' else 0)

            metrics_processor.process_metrics(mac_address, metrics, data)

            # Вставка в MongoDB
            if "collection" in userdata:
                from mongo import insert_data
                insert_data(userdata["collection"], data)
                logger.info(f"Data inserted for sensor {mac_address}")

        except (ValueError, TypeError) as e:
            logger.error(f"Data conversion error for sensor {mac_address}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error processing sensor {mac_address}: {e}")

    except json.JSONDecodeError:
        logger.error(f"Failed to decode JSON: {msg.payload.decode()}")
    except Exception as e:
        logger.error(f"Critical error in message handler: {e}")

def start_mqtt_client(broker_address, broker_port, topics, collection, sensor_metrics):
    mqtt_client = mqtt.Client(userdata={"topics": topics, "collection": collection, "sensor_metrics": sensor_metrics})
    mqtt_client.on_connect = on_connect
    from file_1 import start_mqtt_client_file
    start_mqtt_client_file(broker_address, broker_port, topics, collection, sensor_metrics,mqtt_client)
    mqtt_client.on_message = on_message

    try:
        mqtt_client.connect(broker_address, broker_port, 60)
        logger.info(f"Attempting to connect to MQTT Broker... {topics}")
        mqtt_client.loop_forever()
    except Exception as e:
        logger.error(f"Failed to connect to MQTT Broker: {e}")




