import time
from collections import deque
import statistics
from typing import Dict, Any
import logging
from metricsPromet import create_sensor_metrics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MetricsProcessor:
    def __init__(self, window_size: int = 5):
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
                'last_values': {}
            }
            self.last_update_time[sensor_id] = time.time()

    def process_metrics(self, sensor_id: str, metrics: Dict[str, Any], new_data: Dict[str, Any]):
        """
        Обработка новых данных и обновление производных метрик.

        :param sensor_id: ID датчика
        :param metrics: словарь с метриками датчика
        :param new_data: новые данные от датчика
        """
        try:
            # Инициализация датчика, если он еще не был инициализирован
            self.init_sensor(sensor_id)

            current_time = time.time()
            last_time = self.last_update_time.get(sensor_id, current_time)
            time_diff = current_time - last_time

            if time_diff <= 0:
                time_diff = 1  # избегаем деления на ноль

            # Получаем предыдущие значения
            last_values = self.sensor_data[sensor_id]['last_values']

            # Обработка PM2.5
            if 'PM25' in new_data:
                pm25 = float(new_data['PM25'])
                self.sensor_data[sensor_id]['pm25'].append(pm25)

                # Расчет скорости изменения
                if 'pm25' in last_values:
                    rate = (pm25 - last_values['pm25']) / time_diff
                    metrics['pm25_rate'].set(rate)

                # Расчет стандартного отклонения
                if len(self.sensor_data[sensor_id]['pm25']) >= 2:
                    stddev = statistics.stdev(self.sensor_data[sensor_id]['pm25'])
                    metrics['pm25_stddev'].set(stddev)

                last_values['pm25'] = pm25

            # Обработка температуры
            if 'TemperatureC' in new_data:
                temp = float(new_data['TemperatureC'])
                self.sensor_data[sensor_id]['temperature_c'].append(temp)

                # Расчет скорости изменения
                if 'temperature_c' in last_values:
                    rate = (temp - last_values['temperature_c']) / time_diff
                    metrics['temp_rate'].set(rate)

                # Расчет стандартного отклонения
                if len(self.sensor_data[sensor_id]['temperature_c']) >= 2:
                    stddev = statistics.stdev(self.sensor_data[sensor_id]['temperature_c'])
                    metrics['temp_stddev'].set(stddev)

                last_values['temperature_c'] = temp

            # Обработка влажности
            if 'Humidity' in new_data:
                humidity = float(new_data['Humidity'])
                self.sensor_data[sensor_id]['humidity'].append(humidity)

                # Расчет скорости изменения
                if 'humidity' in last_values:
                    rate = (humidity - last_values['humidity']) / time_diff
                    metrics['humidity_rate'].set(rate)

                last_values['humidity'] = humidity

            # Обновляем время последнего обновления
            self.last_update_time[sensor_id] = current_time

        except Exception as e:
            logger.error(f"Error processing metrics for sensor {sensor_id}: {e}")


# Создаем глобальный экземпляр процессора
metrics_processor = MetricsProcessor()