import time
from collections import deque
import statistics
import numpy as np
from typing import Dict, Any
import logging
from metricsPromet import create_sensor_metrics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MetricsProcessor:
    def __init__(self, window_size: int = 20):
        self.window_size = window_size
        self.sensor_data = {}  # Для хранения истории значений по каждому датчику
        self.last_update_time = {}  # Для хранения времени последнего обновления

    def init_sensor(self, sensor_id: str):
        """Инициализация структур данных для нового датчика"""
        if sensor_id not in self.sensor_data:
            self.sensor_data[sensor_id] = {
                'pm25': deque(maxlen=self.window_size),
                'temperature_c': deque(maxlen=self.window_size),
                'humidity': deque(maxlen=self.window_size),
                'dew_point_c': deque(maxlen=self.window_size),
                'last_values': {}
            }
            self.last_update_time[sensor_id] = time.time()

    def process_metrics(self, sensor_id: str, metrics: Dict[str, Any], new_data: Dict[str, Any]):
        """
        Полная обработка всех метрик с учетом квантилей и стандартных отклонений
        """
        try:
            # Инициализация датчика
            self.init_sensor(sensor_id)
            current_time = time.time()

            # Получаем историю данных для этого датчика
            sensor_history = self.sensor_data[sensor_id]
            last_values = sensor_history['last_values']

            # Обработка PM2.5
            if 'PM25' in new_data:
                pm25 = float(new_data['PM25'])
                sensor_history['pm25'].append(pm25)

                # Базовые метрики
                metrics['pm25'].set(pm25)
                metrics['pm25_alert'].set(1 if pm25 > 0 else 0)

                # Расчет скорости изменения
                if 'pm25' in last_values:
                    time_diff = max(current_time - self.last_update_time[sensor_id], 0.1)
                    metrics['pm25_rate'].set((pm25 - last_values['pm25']) / time_diff)

                # Статистические показатели
                if len(sensor_history['pm25']) >= 2:
                    data = list(sensor_history['pm25'])
                    metrics['pm25_stddev'].set(statistics.stdev(data))

                last_values['pm25'] = pm25

            # Обработка температуры
            if 'TemperatureC' in new_data:
                temp = float(new_data['TemperatureC'])
                sensor_history['temperature_c'].append(temp)
                metrics['temperature_c'].set(temp)

                # Расчет скорости изменения
                if 'temperature_c' in last_values:
                    time_diff = max(current_time - self.last_update_time[sensor_id], 0.1)
                    metrics['temp_rate'].set((temp - last_values['temperature_c']) / time_diff)

                # Полная статистическая обработка
                if len(sensor_history['temperature_c']) >= 10:
                    data = list(sensor_history['temperature_c'])

                    # Стандартное отклонение
                    std = statistics.stdev(data)
                    metrics['temp_stddev'].set(std)

                    # Квантили
                    metrics['temp_upper_quantile'].set(np.percentile(data, 95))
                    metrics['temp_lower_quantile'].set(np.percentile(data, 5))

                    # Границы μ±2σ
                    mean = statistics.mean(data)
                    metrics['temp_upper_stddev'].set(mean + 2 * std)
                    metrics['temp_lower_stddev'].set(mean - 2 * std)

                last_values['temperature_c'] = temp

            # Обработка влажности
            if 'Humidity' in new_data:
                humidity = float(new_data['Humidity'])
                sensor_history['humidity'].append(humidity)
                metrics['humidity'].set(humidity)

                if 'humidity' in last_values:
                    time_diff = max(current_time - self.last_update_time[sensor_id], 0.1)
                    metrics['humidity_rate'].set((humidity - last_values['humidity']) / time_diff)

                if len(sensor_history['humidity']) >= 10:
                    data = list(sensor_history['humidity'])
                    metrics['humidity_upper_quantile'].set(np.percentile(data, 95))
                    metrics['humidity_lower_quantile'].set(np.percentile(data, 5))

                last_values['humidity'] = humidity

            # Обработка точки росы
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

                last_values['dew_point_c'] = dew_point

            # Обновление времени последнего обновления
            self.last_update_time[sensor_id] = current_time

        except Exception as e:
            logger.error(f"Error processing metrics for {sensor_id}: {str(e)}")


# Создаем глобальный экземпляр процессора
metrics_processor = MetricsProcessor()