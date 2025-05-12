from collections import defaultdict, deque
import numpy as np
from prometheus_client import Gauge


class SensorMetrics:
    def __init__(self, sensor_name, window_size=60):
        self.sensor_name = sensor_name
        self.window_size = window_size

        # История данных
        self.history = {
            'pm25': deque(maxlen=window_size),
            'temperature_c': deque(maxlen=window_size),
            'humidity': deque(maxlen=window_size),
            'dew_point_c': deque(maxlen=window_size),
            'timestamps': deque(maxlen=window_size)
        }

        # Инициализация Prometheus метрик
        self.metrics = {
            # Базовые метрики
            'pm25': Gauge(f'mqtt_{sensor_name}_pm25', f'PM2.5 value for {sensor_name}'),
            'humidity': Gauge(f'mqtt_{sensor_name}_humidity', f'Humidity for {sensor_name}'),
            'temperature_c': Gauge(f'mqtt_{sensor_name}_temperature_c', f'Temperature (C) for {sensor_name}'),
            'temperature_f': Gauge(f'mqtt_{sensor_name}_temperature_f', f'Temperature (F) for {sensor_name}'),
            'dew_point_c': Gauge(f'mqtt_{sensor_name}_dew_point_c', f'Dew point (C) for {sensor_name}'),
            'dew_point_f': Gauge(f'mqtt_{sensor_name}_dew_point_f', f'Dew point (F) for {sensor_name}'),
            'alarm_status': Gauge(f'mqtt_{sensor_name}_alarm_status', f'Alarm status for {sensor_name}'),

            # Метрики скорости изменений
            'pm25_rate': Gauge(f'mqtt_{sensor_name}_pm25_rate', f'PM2.5 change rate for {sensor_name}'),
            'temp_rate': Gauge(f'mqtt_{sensor_name}_temp_rate', f'Temperature change rate for {sensor_name}'),
            'humidity_rate': Gauge(f'mqtt_{sensor_name}_humidity_rate', f'Humidity change rate for {sensor_name}'),

            # Метрики статистики
            'pm25_stddev': Gauge(f'mqtt_{sensor_name}_pm25_stddev', f'PM2.5 standard deviation for {sensor_name}'),
            'temp_stddev': Gauge(f'mqtt_{sensor_name}_temp_stddev',
                                 f'Temperature standard deviation for {sensor_name}'),

            # High/Low метрики
            'pm25_high': Gauge(f'mqtt_{sensor_name}_pm25_high', f'Highest PM2.5 for {sensor_name}'),
            'pm25_low': Gauge(f'mqtt_{sensor_name}_pm25_low', f'Lowest PM2.5 for {sensor_name}'),
            'temp_high': Gauge(f'mqtt_{sensor_name}_temp_high', f'Highest temperature for {sensor_name}'),
            'temp_low': Gauge(f'mqtt_{sensor_name}_temp_low', f'Lowest temperature for {sensor_name}'),
            'humidity_high': Gauge(f'mqtt_{sensor_name}_humidity_high', f'Highest humidity for {sensor_name}'),
            'humidity_low': Gauge(f'mqtt_{sensor_name}_humidity_low', f'Lowest humidity for {sensor_name}')
        }

    def update(self, sensor_data):
        """Обновление всех метрик на основе новых данных"""
        # Преобразование данных
        pm25 = float(sensor_data.get('PM25', 0))
        temp_c = float(sensor_data.get('TemperatureC', 0))
        humidity = float(sensor_data.get('Humidity', 0))
        dew_point_c = float(sensor_data.get('DewPointC', 0))
        temp_f = float(sensor_data.get('TemperatureF', 0))
        dew_point_f = float(sensor_data.get('DewPointF', 0))
        alarm_status = 1 if sensor_data.get('AlarmStatus', '').lower() == 'on' else 0

        # Обновление истории
        self.history['pm25'].append(pm25)
        self.history['temperature_c'].append(temp_c)
        self.history['humidity'].append(humidity)
        self.history['dew_point_c'].append(dew_point_c)
        self.history['timestamps'].append(sensor_data.get('MsgTimeStamp'))

        # Обновление базовых метрик
        self.metrics['pm25'].set(pm25)
        self.metrics['humidity'].set(humidity)
        self.metrics['temperature_c'].set(temp_c)
        self.metrics['temperature_f'].set(temp_f)
        self.metrics['dew_point_c'].set(dew_point_c)
        self.metrics['dew_point_f'].set(dew_point_f)
        self.metrics['alarm_status'].set(alarm_status)

        # Вычисление скоростей изменений
        self._calculate_rates()

        # Вычисление статистики
        self._calculate_statistics()

        # Обновление high/low значений
        self._update_high_low()

    def _calculate_rates(self):
        """Вычисление скоростей изменений"""
        if len(self.history['pm25']) > 1:
            self.metrics['pm25_rate'].set(self.history['pm25'][-1] - self.history['pm25'][-2])
        if len(self.history['temperature_c']) > 1:
            self.metrics['temp_rate'].set(self.history['temperature_c'][-1] - self.history['temperature_c'][-2])
        if len(self.history['humidity']) > 1:
            self.metrics['humidity_rate'].set(self.history['humidity'][-1] - self.history['humidity'][-2])

    def _calculate_statistics(self):
        """Вычисление стандартных отклонений"""
        if len(self.history['pm25']) > 1:
            self.metrics['pm25_stddev'].set(np.std(list(self.history['pm25'])))
        if len(self.history['temperature_c']) > 1:
            self.metrics['temp_stddev'].set(np.std(list(self.history['temperature_c'])))

    def _update_high_low(self):
        """Обновление high/low значений"""
        if self.history['pm25']:
            self.metrics['pm25_high'].set(max(self.history['pm25']))
            self.metrics['pm25_low'].set(min(self.history['pm25']))
        if self.history['temperature_c']:
            self.metrics['temp_high'].set(max(self.history['temperature_c']))
            self.metrics['temp_low'].set(min(self.history['temperature_c']))
        if self.history['humidity']:
            self.metrics['humidity_high'].set(max(self.history['humidity']))
            self.metrics['humidity_low'].set(min(self.history['humidity']))