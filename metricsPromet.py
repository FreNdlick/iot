from prometheus_client import Counter, Gauge, Summary
mqtt_messages_received = Counter('mqtt_messages_received_total', 'Всего полученных данных с Mqtt')
mongodb_insertions = Counter('mongodb_insertions_total', 'Количество вставленных данных в mongodb')
active_mqtt_subscriptions = Gauge('active_mqtt_subscriptions', 'Количество подключенных датчиков')
api_requests = Counter('api_requests_total', 'Количество полученных Api-запросов')

def create_sensor_metrics(sensor_name):
    return {
        'pm25': Gauge(f'mqtt_{sensor_name}_pm25', f'Последняя отправка PM2.5 на датчике {sensor_name}'),
        'humidity': Gauge(f'mqtt_{sensor_name}_humidity', f'Последняя отправка Влажности на датчике {sensor_name}'),
        'temperature_c': Gauge(f'mqtt_{sensor_name}_temperature_c', f'Последняя отправка Температуры в Цельсиях на датчике {sensor_name}'),
        'temperature_f': Gauge(f'mqtt_{sensor_name}_temperature_f', f'Последняя отправка Температуры в Фаренгейтах на датчике {sensor_name}'),
        'dew_point_c': Gauge(f'mqtt_{sensor_name}_dew_point_c', f'Последняя отправка Точки росы в Цельсиях на датчике {sensor_name}'),
        'dew_point_f': Gauge(f'mqtt_{sensor_name}_dew_point_f', f'Последняя отправка Точки росы в Фаренгейтах на датчике {sensor_name}'),
        'alarm_status': Gauge(f'mqtt_{sensor_name}_alarm_status', f'Последняя отправка Статуса тревоги на датчике {sensor_name}'),
        'pm25_rate': Gauge(f'mqtt_{sensor_name}_pm25_rate', f'Скорость изменения PM2.5 для датчика {sensor_name}'),
        'temp_rate': Gauge(f'mqtt_{sensor_name}_temp_rate', f'Скорость изменения температуры для датчика {sensor_name}'),
        'humidity_rate': Gauge(f'mqtt_{sensor_name}_humidity_rate', f'Скорость изменения влажности для датчика {sensor_name}'),
        'pm25_stddev': Gauge(f'mqtt_{sensor_name}_pm25_stddev', f'Стандартное отклонение PM2.5 для датчика {sensor_name}'),
        'temp_stddev': Gauge(f'mqtt_{sensor_name}_temp_stddev', f'Стандартное отклонение температуры для датчика {sensor_name}'),
        'temp_upper_quantile': Gauge(f'mqtt_{sensor_name}_temp_upper_q', f'Верхняя граница температуры (95% квантиль)'),
        'temp_lower_quantile': Gauge(f'mqtt_{sensor_name}_temp_lower_q', f'Нижняя граница температуры (5% квантиль)'),
        'temp_upper_stddev': Gauge(f'mqtt_{sensor_name}_temp_upper_std', f'Верхняя граница температуры (μ+2σ)'),
        'temp_lower_stddev': Gauge(f'mqtt_{sensor_name}_temp_lower_std', f'Нижняя граница температуры (μ-2σ)'),
        'humidity_upper_quantile': Gauge(f'mqtt_{sensor_name}_humidity_upper_q', f'Верхняя граница влажности (95% квантиль)'),
        'humidity_lower_quantile': Gauge(f'mqtt_{sensor_name}_humidity_lower_q', f'Нижняя граница влажности (5% квантиль)'),
        'dew_point_rate': Gauge(f'mqtt_{sensor_name}_dew_point_rate', f'Скорость изменения точки росы (°C/мин)'),
        'dew_point_upper_quantile': Gauge(f'mqtt_{sensor_name}_dew_point_upper_q', f'Верхняя граница точки росы (95% квантиль)'),
        'dew_point_lower_quantile': Gauge(f'mqtt_{sensor_name}_dew_point_lower_q', f'Нижняя граница точки росы (5% квантиль)'),
        'pm25_alert': Gauge(f'mqtt_{sensor_name}_pm25_alert', 'Предупреждение PM2.5 (1 если > 0)'),
        'temp_trend': Gauge(f'mqtt_{sensor_name}_temp_trend', 'Тренд температуры (°C/мин)'),
        'humidity_trend': Gauge(f'mqtt_{sensor_name}_humidity_trend', 'Тренд влажности (%/мин)'),
        'dew_point_trend': Gauge(f'mqtt_{sensor_name}_dew_point_trend', 'Тренд точки росы (°C/мин)'),
        'temp_humidity_corr': Gauge(f'mqtt_{sensor_name}_temp_humidity_corr', 'Корреляция температуры и влажности'),
        # Новые метрики для БПФ и спектрального анализа
        'temp_spectral_energy': Gauge(f'mqtt_{sensor_name}_temp_spectral_energy', f'Спектральная энергия температуры для {sensor_name}'),
        'temp_spectral_centroid': Gauge(f'mqtt_{sensor_name}_temp_spectral_centroid', f'Спектральный центроид температуры для {sensor_name}'),
        'temp_spectral_bandwidth': Gauge(f'mqtt_{sensor_name}_temp_spectral_bandwidth', f'Спектральная ширина полосы температуры для {sensor_name}'),
        'temp_dominant_freq': Gauge(f'mqtt_{sensor_name}_temp_dominant_freq', f'Доминирующая частота температуры для {sensor_name}'),
        'temp_skewness': Gauge(f'mqtt_{sensor_name}_temp_skewness', f'Асимметрия температуры для {sensor_name}'),
        'temp_kurtosis': Gauge(f'mqtt_{sensor_name}_temp_kurtosis', f'Эксцесс температуры для {sensor_name}'),
        'humidity_spectral_energy': Gauge(f'mqtt_{sensor_name}_humidity_spectral_energy', f'Спектральная энергия влажности для {sensor_name}'),
        'humidity_spectral_centroid': Gauge(f'mqtt_{sensor_name}_humidity_spectral_centroid', f'Спектральный центроид влажности для {sensor_name}'),
        'pm25_spectral_energy': Gauge(f'mqtt_{sensor_name}_pm25_spectral_energy', f'Спектральная энергия PM2.5 для {sensor_name}'),
        'pm25_spectral_centroid': Gauge(f'mqtt_{sensor_name}_pm25_spectral_centroid', f'Спектральный центроид PM2.5 для {sensor_name}'),
        'anomaly_score': Gauge(f'mqtt_{sensor_name}_anomaly_score', f'Счет аномалий для {sensor_name}'),
        # Метрики готовности
        'metrics_ready_basic': Gauge(f'mqtt_{sensor_name}_metrics_ready_basic', f'Статус готовности базовых метрик для {sensor_name}'),
        'metrics_ready_statistical': Gauge(f'mqtt_{sensor_name}_metrics_ready_statistical', f'Статус готовности статистических метрик для {sensor_name}'),
        'metrics_ready_spectral': Gauge(f'mqtt_{sensor_name}_metrics_ready_spectral', f'Статус готовности спектральных метрик для {sensor_name}'),
        'metrics_ready_anomaly': Gauge(f'mqtt_{sensor_name}_metrics_ready_anomaly', f'Статус готовности обнаружения аномалий для {sensor_name}')
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


