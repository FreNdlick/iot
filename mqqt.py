import paho.mqtt.client as mqtt
import json
import logging
from metricsPromet import mqtt_messages_received, active_mqtt_subscriptions, mongodb_insertions

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
    logger.info(f"Received message on topic {msg.topic}: {msg.payload.decode()}")
    mqtt_messages_received.inc()
    try:
        data = json.loads(msg.payload.decode())
        logger.info(f"Data received: {data}")

        mac_address = data.get('MacAddress', '')
        logger.info("Processing data for sensor"+ "\033[32m{}".format({mac_address}) +"\033[0m ")


        # Обновление метрик датчика
        if mac_address in userdata["sensor_metrics"]:
            metrics = userdata["sensor_metrics"][mac_address]
            metrics['pm25'].set(float(data.get('PM25', 0)))
            metrics['humidity'].set(float(data.get('Humidity', 0)))
            metrics['temperature_c'].set(float(data.get('TemperatureC', 0)))
            metrics['temperature_f'].set(float(data.get('TemperatureF', 0)))
            metrics['dew_point_c'].set(float(data.get('DewPointC', 0)))
            metrics['dew_point_f'].set(float(data.get('DewPointF', 0)))
            metrics['alarm_status'].set(1 if data.get('AlarmStatus', '') == 'On' else 0)
        else:
            logger.warning(f"Unknown MAC address: {mac_address}")

        # Вставка  MongoDB
        from mongo import insert_data
        insert_data(userdata["collection"], data)
    except json.JSONDecodeError:
        logger.error(f"Failed to decode JSON from topic {msg.topic}: {msg.payload.decode()}")
    except Exception as e:
        logger.error(f"An error occurred: {e}")


def start_mqtt_client(broker_address, broker_port, topics, collection, sensor_metrics):
    mqtt_client = mqtt.Client(userdata={"topics": topics, "collection": collection, "sensor_metrics": sensor_metrics})
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message

    try:
        mqtt_client.connect(broker_address, broker_port, 60)
        logger.info(f"Attempting to connect to MQTT Broker... {topics}")
        mqtt_client.loop_forever()
    except Exception as e:
        logger.error(f"Failed to connect to MQTT Broker: {e}")