import time
from collections import deque
import statistics
import numpy as np
import pandas as pd
from typing import Dict, Any
import logging
from prometheus_client import Gauge

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_sensor_metrics(sensor_name: str) -> Dict[str, Gauge]:
    return {
        'pm25': Gauge(f'mqtt_{sensor_name}_pm25', f'PM2.5 value for {sensor_name}'),
        'humidity': Gauge(f'mqtt_{sensor_name}_humidity', f'Humidity for {sensor_name}'),
        'temperature_c': Gauge(f'mqtt_{sensor_name}_temperature_c', f'Temperature (C) for {sensor_name}'),
        'temperature_f': Gauge(f'mqtt_{sensor_name}_temperature_f', f'Temperature (F) for {sensor_name}'),
        'dew_point_c': Gauge(f'mqtt_{sensor_name}_dew_point_c', f'Dew point (C) for {sensor_name}'),
        'dew_point_f': Gauge(f'mqtt_{sensor_name}_dew_point_f', f'Dew point (F) for {sensor_name}'),
        'alarm_status': Gauge(f'mqtt_{sensor_name}_alarm_status', f'Alarm status for {sensor_name}'),
        'pm25_rate': Gauge(f'mqtt_{sensor_name}_pm25_rate', f'PM2.5 change rate for {sensor_name}'),
        'temp_rate': Gauge(f'mqtt_{sensor_name}_temp_rate', f'Temperature change rate for {sensor_name}'),
        'humidity_rate': Gauge(f'mqtt_{sensor_name}_humidity_rate', f'Humidity change rate for {sensor_name}'),
        'dew_point_rate': Gauge(f'mqtt_{sensor_name}_dew_point_rate', f'Dew point change rate for {sensor_name}'),
        'pm25_stddev': Gauge(f'mqtt_{sensor_name}_pm25_stddev', f'PM2.5 standard deviation for {sensor_name}'),
        'temp_stddev': Gauge(f'mqtt_{sensor_name}_temp_stddev', f'Temperature standard deviation for {sensor_name}'),
        'temp_upper_quantile': Gauge(f'mqtt_{sensor_name}_temp_upper_quantile', f'Temperature upper quantile for {sensor_name}'),
        'temp_lower_quantile': Gauge(f'mqtt_{sensor_name}_temp_lower_quantile', f'Temperature lower quantile for {sensor_name}'),
        'temp_upper_stddev': Gauge(f'mqtt_{sensor_name}_temp_upper_stddev', f'Temperature upper stddev for {sensor_name}'),
        'temp_lower_stddev': Gauge(f'mqtt_{sensor_name}_temp_lower_stddev', f'Temperature lower stddev for {sensor_name}'),
        'humidity_upper_quantile': Gauge(f'mqtt_{sensor_name}_humidity_upper_quantile', f'Humidity upper quantile for {sensor_name}'),
        'humidity_lower_quantile': Gauge(f'mqtt_{sensor_name}_humidity_lower_quantile', f'Humidity lower quantile for {sensor_name}'),
        'dew_point_upper_quantile': Gauge(f'mqtt_{sensor_name}_dew_point_upper_quantile', f'Dew point upper quantile for {sensor_name}'),
        'dew_point_lower_quantile': Gauge(f'mqtt_{sensor_name}_dew_point_lower_quantile', f'Dew point lower quantile for {sensor_name}'),
        'temp_trend': Gauge(f'mqtt_{sensor_name}_temp_trend', f'Temperature trend for {sensor_name}'),
        'humidity_trend': Gauge(f'mqtt_{sensor_name}_humidity_trend', f'Humidity trend for {sensor_name}'),
        'dew_point_trend': Gauge(f'mqtt_{sensor_name}_dew_point_trend', f'Dew point trend for {sensor_name}'),
        'temp_humidity_corr': Gauge(f'mqtt_{sensor_name}_temp_humidity_corr', f'Temperature-humidity correlation for {sensor_name}'),
        'pm25_alert': Gauge(f'mqtt_{sensor_name}_pm25_alert', f'PM2.5 alert status for {sensor_name}')
    }

class MetricsProcessor:
    def __init__(self, window_size: int = 100, trend_window: int = 100):
        self.window_size = window_size
        self.trend_window = trend_window
        self.sensor_data = {}
        self.last_update_time = {}
        self.trend_coefficients = {}
        self.correlation_cache = {}

    def init_sensor(self, sensor_id: str):
        if sensor_id not in self.sensor_data:
            self.sensor_data[sensor_id] = {
                'pm25': deque(maxlen=self.window_size),
                'temperature_c': deque(maxlen=self.window_size),
                'humidity': deque(maxlen=self.window_size),
                'dew_point_c': deque(maxlen=self.window_size),
                'timestamps': deque(maxlen=self.window_size),
                'last_values': {}
            }
            self.trend_coefficients[sensor_id] = {
                'temp_trend': 0,
                'humidity_trend': 0,
                'dew_point_trend': 0
            }
            self.last_update_time[sensor_id] = time.time()

    def calculate_correlations(self, sensor_id):
        data = self.sensor_data[sensor_id]
        df = pd.DataFrame({
            'temp': list(data['temperature_c']),
            'humidity': list(data['humidity']),
            'pm25': list(data['pm25'])
        })
        corr = df.corr()
        self.correlation_cache[sensor_id] = corr
        return corr

    def get_correlation_metric(self, sensor_id, metric1, metric2):
        corr = self.correlation_cache.get(sensor_id, None)
        if corr is not None:
            return corr.at[metric1, metric2]
        return 0

    def calculate_trend(self, values: deque, timestamps: deque) -> float:
        if len(values) < 2:
            return 0.0
        x = np.array(timestamps)
        y = np.array(values)
        slope, _ = np.polyfit(x, y, 1)
        return slope * 60

    def process_metrics(self, sensor_id: str, metrics: Dict[str, Any], new_data: Dict[str, Any]):
        try:
            self.init_sensor(sensor_id)
            current_time = time.time()
            sensor_history = self.sensor_data[sensor_id]
            last_values = sensor_history['last_values']
            if 'PM25' in new_data:
                pm25 = float(new_data['PM25'])
                sensor_history['pm25'].append(pm25)
                metrics['pm25'].set(pm25)
                metrics['pm25_alert'].set(1 if pm25 > 0 else 0)
                if 'pm25' in last_values:
                    time_diff = max(current_time - self.last_update_time[sensor_id], 0.1)
                    metrics['pm25_rate'].set((pm25 - last_values['pm25']) / time_diff)
                if len(sensor_history['pm25']) >= 2:
                    data = list(sensor_history['pm25'])
                    metrics['pm25_stddev'].set(statistics.stdev(data))
                last_values['pm25'] = pm25

            if 'TemperatureC' in new_data:
                temp = float(new_data['TemperatureC'])
                sensor_history['temperature_c'].append(temp)
                metrics['temperature_c'].set(temp)
                if 'temperature_c' in last_values:
                    time_diff = max(current_time - self.last_update_time[sensor_id], 0.1)
                    metrics['temp_rate'].set((temp - last_values['temperature_c']) / time_diff)
                if len(sensor_history['temperature_c']) >= 10:
                    data = list(sensor_history['temperature_c'])
                    std = statistics.stdev(data)
                    metrics['temp_stddev'].set(std)
                    metrics['temp_upper_quantile'].set(np.percentile(data, 95))
                    metrics['temp_lower_quantile'].set(np.percentile(data, 5))
                    mean = statistics.mean(data)
                    metrics['temp_upper_stddev'].set(mean + 2 * std)
                    metrics['temp_lower_stddev'].set(mean - 2 * std)
                if len(sensor_history['temperature_c']) >= self.trend_window:
                    metrics['temp_trend'].set(
                        self.calculate_trend(
                            sensor_history['temperature_c'],
                            sensor_history['timestamps']
                        )
                    )
                if len(sensor_history['temperature_c']) >= self.window_size:
                    self.calculate_correlations(sensor_id)
                    metrics['temp_humidity_corr'].set(
                        self.get_correlation_metric(sensor_id, 'temp', 'humidity')
                    )
                last_values['temperature_c'] = temp

            if 'Humidity' in new_data:
                humidity = float(new_data['Humidity'])
                sensor_history['humidity'].append(humidity)
                metrics['humidity'].set(humidity)
                if 'humidity' in last_values:
                    time_diff = max(current_time - self.last_update_time[sensor_id], 0.1)
                    metrics['humidity_rate'].set((humidity - last_values['humidity']) / time_diff)
                if len(sensor_history['humidity']) >= 15:
                    data = list(sensor_history['humidity'])
                    metrics['humidity_upper_quantile'].set(np.percentile(data, 95))
                    metrics['humidity_lower_quantile'].set(np.percentile(data, 5))
                if len(sensor_history['humidity']) >= self.trend_window:
                    metrics['humidity_trend'].set(
                        self.calculate_trend(
                            sensor_history['humidity'],
                            sensor_history['timestamps']
                        )
                    )
                last_values['humidity'] = humidity

            if 'DewPointC' in new_data:
                dew_point = float(new_data['DewPointC'])
                sensor_history['dew_point_c'].append(dew_point)
                metrics['dew_point_c'].set(dew_point)
                if 'dew_point_c' in last_values:
                    time_diff = max(current_time - self.last_update_time[sensor_id], 0.1)
                    metrics['dew_point_rate'].set((dew_point - last_values['dew_point_c']) / time_diff)
                if len(sensor_history['dew_point_c']) >= 10:
                    data = list(sensor_history['dew_point_c'])
                    metrics['dew_point_upper_quantile'].set(np.percentile(data, 95))
                    metrics['dew_point_lower_quantile'].set(np.percentile(data, 5))
                if len(sensor_history['dew_point_c']) >= self.trend_window:
                    metrics['dew_point_trend'].set(
                        self.calculate_trend(
                            sensor_history['dew_point_c'],
                            sensor_history['timestamps']
                        )
                    )
                last_values['dew_point_c'] = dew_point

            self.last_update_time[sensor_id] = current_time

        except Exception as e:
            logger.error(f"Error processing metrics for {sensor_id}: {str(e)}")

metrics_processor = MetricsProcessor()