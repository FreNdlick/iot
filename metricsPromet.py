from prometheus_client import Counter, Gauge, Summary

mqtt_messages_received = Counter('mqtt_messages_received_total', 'Total MQTT messages received')
mongodb_insertions = Counter('mongodb_insertions_total', 'Total MongoDB insertions')
active_mqtt_subscriptions = Gauge('active_mqtt_subscriptions', 'Number of active MQTT subscriptions')
api_requests = Counter('api_requests_total', 'Total API requests')

def create_sensor_metrics(sensor_name):
    return {
        'pm25': Gauge(f'mqtt_{sensor_name}_pm25', f'Last received PM2.5 value for {sensor_name}'),
        'humidity': Gauge(f'mqtt_{sensor_name}_humidity', f'Last received humidity value for {sensor_name}'),
        'temperature_c': Gauge(f'mqtt_{sensor_name}_temperature_c', f'Last received temperature in Celsius value for {sensor_name}'),
        'temperature_f': Gauge(f'mqtt_{sensor_name}_temperature_f', f'Last received temperature in Fahrenheit value for {sensor_name}'),
        'dew_point_c': Gauge(f'mqtt_{sensor_name}_dew_point_c', f'Last received dew point in Celsius value for {sensor_name}'),
        'dew_point_f': Gauge(f'mqtt_{sensor_name}_dew_point_f', f'Last received dew point in Fahrenheit value for {sensor_name}'),
        'alarm_status': Gauge(f'mqtt_{sensor_name}_alarm_status', f'Last received alarm status for {sensor_name}')
    }
api_successful_requests = Counter('api_successful_requests_total', 'Total successful API requests')
api_failed_requests = Counter('api_failed_requests_total', 'Total failed API requests')
api_data_read = Counter('api_data_read_total', 'Total amount of data read from API')
api_request_duration = Summary('api_request_duration_seconds', 'Time spent processing API request')

api_temperature = Gauge('api_temperature', 'Temperature from API')
api_pressure = Gauge('api_pressure', 'Pressure from API')
api_humidity = Gauge('api_humidity', 'Humidity from API')
api_aqi = Gauge('api_aqi', 'AQI from API')
api_iaqi = Gauge('api_iaqi', 'IAQI from API')
api_pm25 = Gauge('api_pm25', 'PM2.5 from API')
api_pm10 = Gauge('api_pm10', 'PM10 from API')
api_pm25_mcp = Gauge('api_pm25_mcp', 'PM2.5 MCP from API')