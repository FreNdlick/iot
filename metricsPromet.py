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
        'alarm_status': Gauge(f'mqtt_{sensor_name}_alarm_status', f'Последняя отправка Alarm_status на датчике{sensor_name}'),

        'pm25_rate': Gauge(f'mqtt_{sensor_name}_pm25_rate', f'PM2.5 change rate for {sensor_name}'),
        'temp_rate': Gauge(f'mqtt_{sensor_name}_temp_rate', f'Temperature change rate for {sensor_name}'),
        'humidity_rate': Gauge(f'mqtt_{sensor_name}_humidity_rate', f'Humidity change rate for {sensor_name}'),
        'pm25_stddev': Gauge(f'mqtt_{sensor_name}_pm25_stddev', f'PM2.5 standard deviation for {sensor_name}'),
        'temp_stddev': Gauge(f'mqtt_{sensor_name}_temp_stddev', f'Temperature standard deviation for {sensor_name}'),

        'temp_upper_quantile': Gauge(f'mqtt_{sensor_name}_temp_upper_q', f'Temperature 95% quantile bound'),
        'temp_lower_quantile': Gauge(f'mqtt_{sensor_name}_temp_lower_q', f'Temperature 5% quantile bound'),
        'temp_upper_stddev': Gauge(f'mqtt_{sensor_name}_temp_upper_std', f'Temperature μ+2σ bound'),
        'temp_lower_stddev': Gauge(f'mqtt_{sensor_name}_temp_lower_std', f'Temperature μ-2σ bound'),

        # Производные метрики для влажности
        'humidity_upper_quantile': Gauge(f'mqtt_{sensor_name}_humidity_upper_q', f'Humidity 95% quantile bound'),
        'humidity_lower_quantile': Gauge(f'mqtt_{sensor_name}_humidity_lower_q', f'Humidity 5% quantile bound'),

        # Производные метрики для точки росы
        'dew_point_rate': Gauge(f'mqtt_{sensor_name}_dew_point_rate', f'Dew point change rate (C/min)'),
        'dew_point_upper_quantile': Gauge(f'mqtt_{sensor_name}_dew_point_upper_q', f'Dew point 95% quantile bound'),
        'dew_point_lower_quantile': Gauge(f'mqtt_{sensor_name}_dew_point_lower_q', f'Dew point 5% quantile bound'),

        # Специальная метрика для PM2.5 (только проверка на 0)
        'pm25_alert': Gauge(f'mqtt_{sensor_name}_pm25_alert', 'PM2.5 non-zero alert (1 if > 0)')

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


