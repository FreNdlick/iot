import time
from collections import deque
import statistics
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, Tuple, List
import logging
from prometheus_client import Gauge
from scipy.fft import fft, fftfreq
from scipy.signal import welch, find_peaks
from scipy.stats import skew, kurtosis
import json
import os
import sys

# Добавляем путь к корневой директории проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FFTProcessor:
    """Класс для обработки БПФ и спектрального анализа"""
    
    def __init__(self, window_size: int = None, sample_rate: float = None):
        self.window_size = window_size or config.FFT_WINDOW_SIZE
        self.sample_rate = sample_rate or config.FFT_SAMPLE_RATE
        self.fft_cache = {}
        self.spectral_cache = {}
        self.fft_config = config.get_fft_config()
        
    def compute_fft(self, data: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Вычисляет БПФ и возвращает частоты и амплитуды"""
        if len(data) < 10:
            return np.array([]), np.array([])
            
        # Убираем среднее значение для лучшего БПФ
        data_centered = data - np.mean(data)
        
        # Вычисляем БПФ
        fft_result = fft(data_centered)
        freqs = fftfreq(len(data_centered), 1/self.sample_rate)
        
        # Берем только положительные частоты
        positive_freqs = freqs[:len(freqs)//2]
        amplitudes = 2.0 / len(data_centered) * np.abs(fft_result[:len(fft_result)//2])
        
        return positive_freqs, amplitudes
    
    def compute_spectral_density(self, data: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Вычисляет спектральную плотность мощности методом Уэлча"""
        if len(data) < config.MIN_DATA_FOR_FFT:
            return np.array([]), np.array([])
            
        nperseg = min(self.fft_config['nperseg'], len(data)//4)
        noverlap = min(self.fft_config['noverlap'], nperseg//2)
        freqs, psd = welch(data, fs=self.sample_rate, nperseg=nperseg, noverlap=noverlap)
        return freqs, psd
    
    def find_dominant_frequencies(self, freqs: np.ndarray, amplitudes: np.ndarray, 
                                 num_peaks: int = 5) -> List[Tuple[float, float]]:
        """Находит доминирующие частоты в спектре"""
        if len(amplitudes) < 10:
            return []
            
        anomaly_config = config.get_anomaly_config()
        # Находим пики в спектре
        peaks, properties = find_peaks(
            amplitudes, 
            height=np.max(amplitudes) * anomaly_config['peak_height_ratio'], 
            distance=anomaly_config['peak_distance']
        )
        
        # Сортируем по амплитуде
        peak_amplitudes = amplitudes[peaks]
        peak_freqs = freqs[peaks]
        
        # Берем топ N пиков
        sorted_indices = np.argsort(peak_amplitudes)[::-1][:num_peaks]
        
        return [(peak_freqs[i], peak_amplitudes[i]) for i in sorted_indices]
    
    def compute_spectral_energy(self, amplitudes: np.ndarray) -> float:
        """Вычисляет общую энергию спектра"""
        return np.sum(amplitudes**2)
    
    def compute_spectral_centroid(self, freqs: np.ndarray, amplitudes: np.ndarray) -> float:
        """Вычисляет спектральный центроид"""
        if np.sum(amplitudes) == 0:
            return 0.0
        return np.sum(freqs * amplitudes) / np.sum(amplitudes)
    
    def compute_spectral_bandwidth(self, freqs: np.ndarray, amplitudes: np.ndarray) -> float:
        """Вычисляет спектральную ширину полосы"""
        centroid = self.compute_spectral_centroid(freqs, amplitudes)
        if np.sum(amplitudes) == 0:
            return 0.0
        return np.sqrt(np.sum(((freqs - centroid)**2) * amplitudes) / np.sum(amplitudes))

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
        'pm25_alert': Gauge(f'mqtt_{sensor_name}_pm25_alert', f'PM2.5 alert status for {sensor_name}'),
        # Новые метрики для БПФ и спектрального анализа
        'temp_spectral_energy': Gauge(f'mqtt_{sensor_name}_temp_spectral_energy', f'Temperature spectral energy for {sensor_name}'),
        'temp_spectral_centroid': Gauge(f'mqtt_{sensor_name}_temp_spectral_centroid', f'Temperature spectral centroid for {sensor_name}'),
        'temp_spectral_bandwidth': Gauge(f'mqtt_{sensor_name}_temp_spectral_bandwidth', f'Temperature spectral bandwidth for {sensor_name}'),
        'temp_dominant_freq': Gauge(f'mqtt_{sensor_name}_temp_dominant_freq', f'Temperature dominant frequency for {sensor_name}'),
        'temp_skewness': Gauge(f'mqtt_{sensor_name}_temp_skewness', f'Temperature skewness for {sensor_name}'),
        'temp_kurtosis': Gauge(f'mqtt_{sensor_name}_temp_kurtosis', f'Temperature kurtosis for {sensor_name}'),
        'humidity_spectral_energy': Gauge(f'mqtt_{sensor_name}_humidity_spectral_energy', f'Humidity spectral energy for {sensor_name}'),
        'humidity_spectral_centroid': Gauge(f'mqtt_{sensor_name}_humidity_spectral_centroid', f'Humidity spectral centroid for {sensor_name}'),
        'pm25_spectral_energy': Gauge(f'mqtt_{sensor_name}_pm25_spectral_energy', f'PM2.5 spectral energy for {sensor_name}'),
        'pm25_spectral_centroid': Gauge(f'mqtt_{sensor_name}_pm25_spectral_centroid', f'PM2.5 spectral centroid for {sensor_name}'),
        'anomaly_score': Gauge(f'mqtt_{sensor_name}_anomaly_score', f'Anomaly detection score for {sensor_name}'),
        # Метрики готовности
        'metrics_ready_basic': Gauge(f'mqtt_{sensor_name}_metrics_ready_basic', f'Basic metrics ready status for {sensor_name}'),
        'metrics_ready_statistical': Gauge(f'mqtt_{sensor_name}_metrics_ready_statistical', f'Statistical metrics ready status for {sensor_name}'),
        'metrics_ready_spectral': Gauge(f'mqtt_{sensor_name}_metrics_ready_spectral', f'Spectral metrics ready status for {sensor_name}'),
        'metrics_ready_anomaly': Gauge(f'mqtt_{sensor_name}_metrics_ready_anomaly', f'Anomaly detection ready status for {sensor_name}')
    }

class MetricsProcessor:
    def __init__(self, window_size: int = None, trend_window: int = None, fft_window_size: int = None):
        self.window_size = window_size or config.WINDOW_SIZE
        self.trend_window = trend_window or config.TREND_WINDOW_SIZE
        self.fft_window_size = fft_window_size or config.FFT_WINDOW_SIZE
        self.sensor_data = {}
        self.last_update_time = {}
        self.trend_coefficients = {}
        self.correlation_cache = {}
        self.fft_processor = FFTProcessor(window_size=self.fft_window_size)
        self.anomaly_thresholds = {}
        self.metrics_ready = {}
        
        # Конфигурация для оптимизации памяти
        memory_config = config.get_memory_config()
        self.max_cached_fft = memory_config['max_cached_fft']
        self.enable_fft_caching = memory_config['enable_fft_caching']
        self.fft_cache_size = {}

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
            self.fft_cache_size[sensor_id] = 0
            self.anomaly_thresholds[sensor_id] = {
                'temp_spectral_energy': {'mean': 0, 'std': 1},
                'temp_spectral_centroid': {'mean': 0, 'std': 1},
                'pm25_spectral_energy': {'mean': 0, 'std': 1}
            }
            # Инициализируем метрики готовности
            self.metrics_ready[sensor_id] = {
                'basic_metrics': False,
                'statistical_metrics': False,
                'spectral_metrics': False,
                'anomaly_detection': False
            }

    def initialize_metrics_with_defaults(self, sensor_id: str, metrics: Dict[str, Gauge]):
        """Инициализирует метрики с разумными значениями по умолчанию"""
        try:
            # Базовые метрики - устанавливаем в 0 или NaN для индикации отсутствия данных
            metrics['pm25'].set(0)
            metrics['humidity'].set(0)
            metrics['temperature_c'].set(0)
            metrics['dew_point_c'].set(0)
            metrics['alarm_status'].set(0)
            
            # Скорости изменения - 0
            metrics['pm25_rate'].set(0)
            metrics['temp_rate'].set(0)
            metrics['humidity_rate'].set(0)
            metrics['dew_point_rate'].set(0)
            
            # Статистические метрики - 0
            metrics['pm25_stddev'].set(0)
            metrics['temp_stddev'].set(0)
            metrics['temp_upper_quantile'].set(0)
            metrics['temp_lower_quantile'].set(0)
            metrics['temp_upper_stddev'].set(0)
            metrics['temp_lower_stddev'].set(0)
            metrics['humidity_upper_quantile'].set(0)
            metrics['humidity_lower_quantile'].set(0)
            metrics['dew_point_upper_quantile'].set(0)
            metrics['dew_point_lower_quantile'].set(0)
            
            # Тренды - 0
            metrics['temp_trend'].set(0)
            metrics['humidity_trend'].set(0)
            metrics['dew_point_trend'].set(0)
            metrics['temp_humidity_corr'].set(0)
            metrics['pm25_alert'].set(0)
            
            # Спектральные метрики - 0
            metrics['temp_spectral_energy'].set(0)
            metrics['temp_spectral_centroid'].set(0)
            metrics['temp_spectral_bandwidth'].set(0)
            metrics['temp_dominant_freq'].set(0)
            metrics['temp_skewness'].set(0)
            metrics['temp_kurtosis'].set(0)
            metrics['humidity_spectral_energy'].set(0)
            metrics['humidity_spectral_centroid'].set(0)
            metrics['pm25_spectral_energy'].set(0)
            metrics['pm25_spectral_centroid'].set(0)
            metrics['anomaly_score'].set(0)
            
            # Метрики готовности - 0 (не готовы)
            metrics['metrics_ready_basic'].set(0)
            metrics['metrics_ready_statistical'].set(0)
            metrics['metrics_ready_spectral'].set(0)
            metrics['metrics_ready_anomaly'].set(0)
            
            logger.info(f"Initialized default metrics for sensor {sensor_id}")
            
        except Exception as e:
            logger.error(f"Error initializing default metrics for {sensor_id}: {str(e)}")

    def get_adaptive_thresholds(self, data_length: int) -> Dict[str, int]:
        """Возвращает адаптивные пороги для вычислений в зависимости от доступных данных"""
        thresholds = {
            'min_for_basic': max(1, min(5, data_length)),
            'min_for_stddev': max(2, min(config.MIN_DATA_FOR_STDDEV, data_length)),
            'min_for_quantiles': max(3, min(config.MIN_DATA_FOR_QUANTILES, data_length)),
            'min_for_trend': max(5, min(config.MIN_DATA_FOR_TREND, data_length)),
            'min_for_fft': max(10, min(config.MIN_DATA_FOR_FFT, data_length)),
            'min_for_correlation': max(10, min(config.MIN_DATA_FOR_CORRELATION, data_length))
        }
        return thresholds

    def update_metrics_readiness(self, sensor_id: str, metrics: Dict[str, Gauge]):
        """Обновляет статус готовности метрик"""
        try:
            if sensor_id not in self.metrics_ready:
                return
                
            readiness = self.metrics_ready[sensor_id]
            sensor_data = self.sensor_data[sensor_id]
            
            # Базовые метрики готовы, если есть хотя бы одно значение
            basic_ready = (len(sensor_data['temperature_c']) > 0 or 
                          len(sensor_data['humidity']) > 0 or 
                          len(sensor_data['pm25']) > 0)
            
            # Статистические метрики готовы, если есть достаточно данных для STD
            thresholds = self.get_adaptive_thresholds(len(sensor_data['temperature_c']))
            statistical_ready = (len(sensor_data['temperature_c']) >= thresholds['min_for_stddev'] or
                               len(sensor_data['humidity']) >= thresholds['min_for_stddev'] or
                               len(sensor_data['pm25']) >= thresholds['min_for_stddev'])
            
            # Спектральные метрики готовы, если есть достаточно данных для БПФ
            spectral_ready = (len(sensor_data['temperature_c']) >= thresholds['min_for_fft'] or
                            len(sensor_data['humidity']) >= thresholds['min_for_fft'] or
                            len(sensor_data['pm25']) >= thresholds['min_for_fft'])
            
            # Обнаружение аномалий готово, если спектральные метрики готовы
            anomaly_ready = spectral_ready
            
            # Обновляем статусы
            readiness['basic_metrics'] = basic_ready
            readiness['statistical_metrics'] = statistical_ready
            readiness['spectral_metrics'] = spectral_ready
            readiness['anomaly_detection'] = anomaly_ready
            
            # Обновляем метрики готовности
            metrics['metrics_ready_basic'].set(1 if basic_ready else 0)
            metrics['metrics_ready_statistical'].set(1 if statistical_ready else 0)
            metrics['metrics_ready_spectral'].set(1 if spectral_ready else 0)
            metrics['metrics_ready_anomaly'].set(1 if anomaly_ready else 0)
            
        except Exception as e:
            logger.error(f"Error updating metrics readiness for {sensor_id}: {str(e)}")

    def compute_progressive_metrics(self, sensor_id: str, data_type: str, data: np.ndarray, metrics: Dict[str, Gauge]):
        """Вычисляет метрики прогрессивно в зависимости от доступных данных"""
        try:
            data_length = len(data)
            thresholds = self.get_adaptive_thresholds(data_length)
            
            if data_length < thresholds['min_for_basic']:
                return
                
            # Базовые статистики (минимальные данные)
            if data_length >= thresholds['min_for_stddev']:
                if data_type == 'temperature_c':
                    std = np.std(data)
                    mean = np.mean(data)
                    metrics['temp_stddev'].set(std)
                    metrics['temp_upper_stddev'].set(mean + 2 * std)
                    metrics['temp_lower_stddev'].set(mean - 2 * std)
                    
                    # Простые квантили для малых выборок
                    if data_length >= 5:
                        metrics['temp_upper_quantile'].set(np.percentile(data, 90))
                        metrics['temp_lower_quantile'].set(np.percentile(data, 10))
                
                elif data_type == 'humidity':
                    if data_length >= 5:
                        metrics['humidity_upper_quantile'].set(np.percentile(data, 90))
                        metrics['humidity_lower_quantile'].set(np.percentile(data, 10))
                
                elif data_type == 'pm25':
                    std = np.std(data)
                    metrics['pm25_stddev'].set(std)
            
            # Простые спектральные метрики (меньше данных)
            if data_length >= max(10, thresholds['min_for_fft'] // 2):
                try:
                    # Упрощенный БПФ для малых выборок
                    if data_length < 50:
                        # Используем только основные частоты
                        freqs, amplitudes = self.fft_processor.compute_fft(data)
                        if len(freqs) > 0:
                            spectral_energy = np.sum(amplitudes[:min(10, len(amplitudes))]**2)
                            spectral_centroid = np.sum(freqs[:min(10, len(freqs))] * amplitudes[:min(10, len(amplitudes))]) / np.sum(amplitudes[:min(10, len(amplitudes))])
                            
                            if data_type == 'temperature_c':
                                metrics['temp_spectral_energy'].set(spectral_energy)
                                metrics['temp_spectral_centroid'].set(spectral_centroid)
                            elif data_type == 'humidity':
                                metrics['humidity_spectral_energy'].set(spectral_energy)
                                metrics['humidity_spectral_centroid'].set(spectral_centroid)
                            elif data_type == 'pm25':
                                metrics['pm25_spectral_energy'].set(spectral_energy)
                                metrics['pm25_spectral_centroid'].set(spectral_energy)
                except Exception as e:
                    logger.debug(f"Progressive spectral computation failed for {sensor_id}: {str(e)}")
            
            # Полные спектральные метрики (достаточно данных)
            if data_length >= thresholds['min_for_fft']:
                self.compute_spectral_metrics(sensor_id, data_type, data, metrics)
            
        except Exception as e:
            logger.error(f"Error in progressive metrics computation for {sensor_id}: {str(e)}")

    def prefill_sensor_data(self, sensor_id: str, initial_data: Dict[str, Any]):
        """Предварительно заполняет данные сенсора для быстрого старта"""
        try:
            if sensor_id not in self.sensor_data:
                self.init_sensor(sensor_id)
            
            sensor_history = self.sensor_data[sensor_id]
            
            # Заполняем данными по умолчанию для быстрого старта
            default_temp = initial_data.get('temperature_c', 20.0)
            default_humidity = initial_data.get('humidity', 50.0)
            default_pm25 = initial_data.get('pm25', 10.0)
            default_dew_point = initial_data.get('dew_point_c', default_temp - 5)
            
            # Создаем небольшой массив данных для быстрого старта
            current_time = time.time()
            for i in range(min(10, config.MIN_DATA_FOR_FFT // 10)):
                timestamp = current_time - (10 - i) * 60  # 1 минута между измерениями
                
                # Добавляем небольшой шум для реалистичности
                temp = default_temp + np.random.normal(0, 0.5)
                humidity = default_humidity + np.random.normal(0, 2)
                pm25 = max(0, default_pm25 + np.random.normal(0, 1))
                dew_point = temp - 5 + np.random.normal(0, 0.3)
                
                sensor_history['temperature_c'].append(temp)
                sensor_history['humidity'].append(humidity)
                sensor_history['pm25'].append(pm25)
                sensor_history['dew_point_c'].append(dew_point)
                sensor_history['timestamps'].append(timestamp)
            
            logger.info(f"Prefilled {len(sensor_history['temperature_c'])} data points for sensor {sensor_id}")
            
        except Exception as e:
            logger.error(f"Error prefill data for {sensor_id}: {str(e)}")

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

    def compute_spectral_metrics(self, sensor_id: str, data_type: str, data: np.ndarray, metrics: Dict[str, Gauge]):
        """Вычисляет спектральные метрики для данных"""
        if len(data) < 10:
            return
            
        try:
            # БПФ анализ
            freqs, amplitudes = self.fft_processor.compute_fft(data)
            if len(freqs) == 0:
                return
                
            # Спектральная плотность
            psd_freqs, psd = self.fft_processor.compute_spectral_density(data)
            
            # Основные спектральные метрики
            spectral_energy = self.fft_processor.compute_spectral_energy(amplitudes)
            spectral_centroid = self.fft_processor.compute_spectral_centroid(freqs, amplitudes)
            spectral_bandwidth = self.fft_processor.compute_spectral_bandwidth(freqs, amplitudes)
            
            # Доминирующие частоты
            dominant_freqs = self.fft_processor.find_dominant_frequencies(freqs, amplitudes, num_peaks=1)
            dominant_freq = dominant_freqs[0][0] if dominant_freqs else 0.0
            
            # Статистические метрики
            data_skewness = skew(data)
            data_kurtosis = kurtosis(data)
            
            # Обновляем метрики
            if data_type == 'temperature_c':
                metrics['temp_spectral_energy'].set(spectral_energy)
                metrics['temp_spectral_centroid'].set(spectral_centroid)
                metrics['temp_spectral_bandwidth'].set(spectral_bandwidth)
                metrics['temp_dominant_freq'].set(dominant_freq)
                metrics['temp_skewness'].set(data_skewness)
                metrics['temp_kurtosis'].set(data_kurtosis)
            elif data_type == 'humidity':
                metrics['humidity_spectral_energy'].set(spectral_energy)
                metrics['humidity_spectral_centroid'].set(spectral_centroid)
            elif data_type == 'pm25':
                metrics['pm25_spectral_energy'].set(spectral_energy)
                metrics['pm25_spectral_centroid'].set(spectral_centroid)
                
            # Обнаружение аномалий на основе спектральных характеристик
            self.detect_spectral_anomalies(sensor_id, data_type, spectral_energy, spectral_centroid, metrics)
            
        except Exception as e:
            logger.error(f"Error computing spectral metrics for {sensor_id} {data_type}: {str(e)}")

    def detect_spectral_anomalies(self, sensor_id: str, data_type: str, spectral_energy: float, 
                                 spectral_centroid: float, metrics: Dict[str, Gauge]):
        """Обнаружение аномалий на основе спектральных характеристик"""
        try:
            thresholds = self.anomaly_thresholds[sensor_id]
            
            # Простое обнаружение аномалий на основе Z-score
            anomaly_score = 0.0
            
            if data_type == 'temperature_c':
                energy_key = 'temp_spectral_energy'
                centroid_key = 'temp_spectral_centroid'
            elif data_type == 'pm25':
                energy_key = 'pm25_spectral_energy'
                centroid_key = 'pm25_spectral_centroid'
            else:
                return
                
            anomaly_config = config.get_anomaly_config()
            
            # Обновляем пороги (скользящее среднее)
            if thresholds[energy_key]['mean'] == 0:
                thresholds[energy_key]['mean'] = spectral_energy
                thresholds[energy_key]['std'] = 1.0
            else:
                # Экспоненциальное сглаживание
                alpha = anomaly_config['alpha']
                thresholds[energy_key]['mean'] = alpha * spectral_energy + (1 - alpha) * thresholds[energy_key]['mean']
                thresholds[energy_key]['std'] = alpha * abs(spectral_energy - thresholds[energy_key]['mean']) + (1 - alpha) * thresholds[energy_key]['std']
            
            # Вычисляем Z-score
            if thresholds[energy_key]['std'] > 0:
                energy_z_score = abs(spectral_energy - thresholds[energy_key]['mean']) / thresholds[energy_key]['std']
                anomaly_score += energy_z_score
                
            # Нормализуем аномальный счет
            anomaly_score = min(anomaly_score, anomaly_config['max_score'])
            
            metrics['anomaly_score'].set(anomaly_score)
            
        except Exception as e:
            logger.error(f"Error in anomaly detection for {sensor_id}: {str(e)}")

    def process_metrics(self, sensor_id: str, metrics: Dict[str, Any], new_data: Dict[str, Any]):
        try:
            self.init_sensor(sensor_id)
            
            # Инициализируем метрики с значениями по умолчанию при первом запуске
            if not self.metrics_ready[sensor_id]['basic_metrics']:
                self.initialize_metrics_with_defaults(sensor_id, metrics)
            
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
                
                # Прогрессивный спектральный анализ для PM2.5
                if len(sensor_history['pm25']) >= 2:
                    pm25_data = np.array(list(sensor_history['pm25']))
                    self.compute_progressive_metrics(sensor_id, 'pm25', pm25_data, metrics)

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
                
                # Прогрессивный спектральный анализ для температуры
                if len(sensor_history['temperature_c']) >= 2:
                    temp_data = np.array(list(sensor_history['temperature_c']))
                    self.compute_progressive_metrics(sensor_id, 'temperature_c', temp_data, metrics)

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
                
                # Прогрессивный спектральный анализ для влажности
                if len(sensor_history['humidity']) >= 2:
                    humidity_data = np.array(list(sensor_history['humidity']))
                    self.compute_progressive_metrics(sensor_id, 'humidity', humidity_data, metrics)

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
            
            # Обновляем статус готовности метрик
            self.update_metrics_readiness(sensor_id, metrics)

        except Exception as e:
            logger.error(f"Error processing metrics for {sensor_id}: {str(e)}")

# Создаем глобальный экземпляр с конфигурацией из config.py
metrics_processor = MetricsProcessor()