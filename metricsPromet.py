from prometheus_client import Counter, Gauge, Summary
mqtt_messages_received = Counter('mqtt_messages_received_total', 'Всего полученных данных с Mqtt')
mongodb_insertions = Counter('mongodb_insertions_total', 'Количество вставленных данных в mongodb')
active_mqtt_subscriptions = Gauge('active_mqtt_subscriptions', 'Количество подключенных датчиков')
api_requests = Counter('api_requests_total', 'Количество полученных Api-запросов')
def create_sensor_metrics(sensor_name):
    return {
        'pm25': Gauge(f'mqtt_{sensor_name}_pm25', f'Последняя отправка PM2.5 на датчике {sensor_name}'),
        'humidity': Gauge(f'mqtt_{sensor_name}_humidity', f'Последняя отправка Влажности на датчике {sensor_name}'),
        'temperature_c': Gauge(f'mqtt_{sensor_name}_temperature_c', f'Последняя отправка Температуры в Цельсии на датчике{sensor_name}'),
        'temperature_f': Gauge(f'mqtt_{sensor_name}_temperature_f', f'Последняя отправка Температуры в Фаренгейтахна датчике {sensor_name}'),
        'dew_point_c': Gauge(f'mqtt_{sensor_name}_dew_point_c', f'Последняя отправка Точки россы в Цельсии на датчике{sensor_name}'),
        'dew_point_f': Gauge(f'mqtt_{sensor_name}_dew_point_f', f'Последняя отправка Точки россы в Фаренгейтах на датчике {sensor_name}'),
        'alarm_status': Gauge(f'mqtt_{sensor_name}_alarm_status', f'Последняя отправка Alarm_status на датчике{sensor_name}')
    }
api_successful_requests = Counter('api_successful_requests_total', 'Удачные запросы Api')
api_failed_requests = Counter('api_failed_requests_total', 'Неудачные запросы Api')
api_data_read = Counter('api_data_read_total', 'Количество прочитанных запросов Api ')
api_request_duration = Summary('api_request_duration_seconds', 'Время потраченно для обработки Api')

api_temperature = Gauge('api_temperature', 'Температура с Api')
api_pressure = Gauge('api_pressure', 'Давление с Api')
api_humidity = Gauge('api_humidity', 'Влажность с Api')
api_aqi = Gauge('api_aqi', 'AQI с API')
api_iaqi = Gauge('api_iaqi', 'IAQI с API')
api_pm25 = Gauge('api_pm25', 'PM2.5 с API')
api_pm10 = Gauge('api_pm10', 'PM10 с API')
api_pm25_mcp = Gauge('api_pm25_mcp', 'PM2.5 MCP с API')

anomally_detected = Gauge('anomally_detected', 'Обнаружение аномалии')

test_alert = Gauge("anomaly_test", "Test_Anomaly")