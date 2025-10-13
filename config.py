import os
from typing import Dict, Any

class MetricsConfig:
    
    def __init__(self):
        self.WINDOW_SIZE = int(os.getenv('METRICS_WINDOW_SIZE', '3000'))
        self.TREND_WINDOW_SIZE = int(os.getenv('METRICS_TREND_WINDOW_SIZE', '300'))
        self.FFT_WINDOW_SIZE = int(os.getenv('METRICS_FFT_WINDOW_SIZE', '300'))

        self.MIN_DATA_FOR_STDDEV = int(os.getenv('MIN_DATA_FOR_STDDEV', '10'))
        self.MIN_DATA_FOR_QUANTILES = int(os.getenv('MIN_DATA_FOR_QUANTILES', '15'))
        self.MIN_DATA_FOR_TREND = int(os.getenv('MIN_DATA_FOR_TREND', '100'))
        self.MIN_DATA_FOR_FFT = int(os.getenv('MIN_DATA_FOR_FFT', '100'))
        self.MIN_DATA_FOR_CORRELATION = int(os.getenv('MIN_DATA_FOR_CORRELATION', '100'))

        self.FFT_SAMPLE_RATE = float(os.getenv('FFT_SAMPLE_RATE', '1.0'))
        self.FFT_NPERSEG = int(os.getenv('FFT_NPERSEG', '256'))
        self.FFT_NOVERLAP = int(os.getenv('FFT_NOVERLAP', '128'))

        self.ANOMALY_ALPHA = float(os.getenv('ANOMALY_ALPHA', '0.1'))
        self.ANOMALY_MAX_SCORE = float(os.getenv('ANOMALY_MAX_SCORE', '10.0'))
        self.ANOMALY_PEAK_HEIGHT_RATIO = float(os.getenv('ANOMALY_PEAK_HEIGHT_RATIO', '0.1'))
        self.ANOMALY_PEAK_DISTANCE = int(os.getenv('ANOMALY_PEAK_DISTANCE', '5'))

        self.MAX_CACHED_FFT = int(os.getenv('MAX_CACHED_FFT', '10'))
        self.ENABLE_FFT_CACHING = os.getenv('ENABLE_FFT_CACHING', 'true').lower() == 'true'

        self.LOG_LEVEL = os.getenv('METRICS_LOG_LEVEL', 'INFO')
        self.LOG_SPECTRAL_METRICS = os.getenv('LOG_SPECTRAL_METRICS', 'false').lower() == 'true'

        self.EXPORT_FFT_DATA = os.getenv('EXPORT_FFT_DATA', 'false').lower() == 'true'
        self.EXPORT_DIRECTORY = os.getenv('EXPORT_DIRECTORY', './exports')
        
    def get_fft_config(self) -> Dict[str, Any]:
        return {
            'window_size': self.FFT_WINDOW_SIZE,
            'sample_rate': self.FFT_SAMPLE_RATE,
            'nperseg': self.FFT_NPERSEG,
            'noverlap': self.FFT_NOVERLAP
        }
    
    def get_anomaly_config(self) -> Dict[str, Any]:
        return {
            'alpha': self.ANOMALY_ALPHA,
            'max_score': self.ANOMALY_MAX_SCORE,
            'peak_height_ratio': self.ANOMALY_PEAK_HEIGHT_RATIO,
            'peak_distance': self.ANOMALY_PEAK_DISTANCE
        }
    
    def get_memory_config(self) -> Dict[str, Any]:
        return {
            'max_cached_fft': self.MAX_CACHED_FFT,
            'enable_fft_caching': self.ENABLE_FFT_CACHING
        }
    
    def validate_config(self) -> bool:
        if self.WINDOW_SIZE < 10:
            raise ValueError("WINDOW_SIZE должен быть >= 10")
        if self.TREND_WINDOW_SIZE < 10:
            raise ValueError("TREND_WINDOW_SIZE должен быть >= 10")
        if self.FFT_WINDOW_SIZE < 10:
            raise ValueError("FFT_WINDOW_SIZE должен быть >= 10")
        if self.ANOMALY_ALPHA <= 0 or self.ANOMALY_ALPHA >= 1:
            raise ValueError("ANOMALY_ALPHA должен быть в диапазоне (0, 1)")
        if self.FFT_SAMPLE_RATE <= 0:
            raise ValueError("FFT_SAMPLE_RATE должен быть > 0")
        return True

config = MetricsConfig()

try:
    config.validate_config()
except ValueError as e:
    print(f"Ошибка конфигурации: {e}")
    config = MetricsConfig()
    config.WINDOW_SIZE = 3000
    config.TREND_WINDOW_SIZE = 3000
    config.FFT_WINDOW_SIZE = 3000
