#!/usr/bin/env python3
"""
Тестовый скрипт для демонстрации модернизированной системы метрик
"""
import numpy as np
import time
import random
from Analyz.metrics_process import metrics_processor, create_sensor_metrics
from config import config

def generate_synthetic_data(num_points=1000, base_temp=20.0, noise_level=0.5):
    """Генерирует синтетические данные для тестирования"""
    timestamps = np.arange(num_points)
    
    # Температура с трендом и шумом
    temp_trend = 0.001 * timestamps
    temp_noise = np.random.normal(0, noise_level, num_points)
    temp_sine = 2 * np.sin(0.01 * timestamps)  # Низкочастотная компонента
    temperature = base_temp + temp_trend + temp_sine + temp_noise
    
    # Влажность с обратной корреляцией с температурой
    humidity = 80 - 0.5 * (temperature - base_temp) + np.random.normal(0, 2, num_points)
    humidity = np.clip(humidity, 0, 100)
    
    # PM2.5 с периодическими всплесками
    pm25_base = 10 + 5 * np.sin(0.005 * timestamps)
    pm25_spikes = np.random.poisson(0.1, num_points) * 50
    pm25 = pm25_base + pm25_spikes + np.random.normal(0, 2, num_points)
    pm25 = np.clip(pm25, 0, 200)
    
    return timestamps, temperature, humidity, pm25

def test_metrics_processing():
    """Тестирует обработку метрик с синтетическими данными"""
    print("=== Тестирование модернизированной системы метрик ===\n")
    
    # Создаем метрики для тестового сенсора
    sensor_id = "test_sensor_001"
    sensor_metrics = create_sensor_metrics(sensor_id)
    
    print(f"Конфигурация:")
    print(f"  Размер окна: {config.WINDOW_SIZE}")
    print(f"  Размер окна для тренда: {config.TREND_WINDOW_SIZE}")
    print(f"  Размер окна для БПФ: {config.FFT_WINDOW_SIZE}")
    print(f"  Минимум данных для БПФ: {config.MIN_DATA_FOR_FFT}")
    print()
    
    # Генерируем тестовые данные
    print("Генерация синтетических данных...")
    timestamps, temperatures, humidities, pm25_values = generate_synthetic_data(2000)
    
    print(f"Сгенерировано {len(temperatures)} точек данных")
    print(f"Температура: {np.mean(temperatures):.2f}C ± {np.std(temperatures):.2f}")
    print(f"Влажность: {np.mean(humidities):.2f}% ± {np.std(humidities):.2f}")
    print(f"PM2.5: {np.mean(pm25_values):.2f} ug/m3 ± {np.std(pm25_values):.2f}")
    print()
    
    # Обрабатываем данные по частям
    print("Обработка данных...")
    start_time = time.time()
    
    for i in range(len(temperatures)):
        new_data = {
            'TemperatureC': temperatures[i],
            'Humidity': humidities[i],
            'PM25': pm25_values[i],
            'DewPointC': temperatures[i] - 5  # Простое приближение
        }
        
        metrics_processor.process_metrics(sensor_id, sensor_metrics, new_data)
        
        # Показываем прогресс каждые 200 точек
        if (i + 1) % 200 == 0:
            print(f"Обработано {i + 1}/{len(temperatures)} точек")
    
    processing_time = time.time() - start_time
    print(f"Обработка завершена за {processing_time:.2f} секунд")
    print()
    
    # Выводим результаты
    print("=== Результаты обработки ===")
    
    # Базовые метрики
    print("\nБазовые метрики:")
    print(f"  Температура: {sensor_metrics['temperature_c']._value.get():.2f}C")
    print(f"  Влажность: {sensor_metrics['humidity']._value.get():.2f}%")
    print(f"  PM2.5: {sensor_metrics['pm25']._value.get():.2f} ug/m3")
    
    # Статистические метрики
    print("\nСтатистические метрики:")
    print(f"  STD температуры: {sensor_metrics['temp_stddev']._value.get():.2f}")
    print(f"  Верхний квантиль температуры: {sensor_metrics['temp_upper_quantile']._value.get():.2f}")
    print(f"  Нижний квантиль температуры: {sensor_metrics['temp_lower_quantile']._value.get():.2f}")
    
    # Тренды
    print("\nТренды:")
    print(f"  Тренд температуры: {sensor_metrics['temp_trend']._value.get():.4f}C/мин")
    print(f"  Тренд влажности: {sensor_metrics['humidity_trend']._value.get():.4f}%/мин")
    
    # Корреляции
    print("\nКорреляции:")
    print(f"  Корреляция температура-влажность: {sensor_metrics['temp_humidity_corr']._value.get():.4f}")
    
    # Новые спектральные метрики
    print("\nСпектральные метрики:")
    print(f"  Спектральная энергия температуры: {sensor_metrics['temp_spectral_energy']._value.get():.4f}")
    print(f"  Спектральный центроид температуры: {sensor_metrics['temp_spectral_centroid']._value.get():.4f}")
    print(f"  Спектральная ширина полосы температуры: {sensor_metrics['temp_spectral_bandwidth']._value.get():.4f}")
    print(f"  Доминирующая частота температуры: {sensor_metrics['temp_dominant_freq']._value.get():.6f} Гц")
    
    # Статистические характеристики
    print("\nСтатистические характеристики:")
    print(f"  Асимметрия температуры: {sensor_metrics['temp_skewness']._value.get():.4f}")
    print(f"  Эксцесс температуры: {sensor_metrics['temp_kurtosis']._value.get():.4f}")
    
    # Метрики влажности
    print("\nСпектральные метрики влажности:")
    print(f"  Спектральная энергия влажности: {sensor_metrics['humidity_spectral_energy']._value.get():.4f}")
    print(f"  Спектральный центроид влажности: {sensor_metrics['humidity_spectral_centroid']._value.get():.4f}")
    
    # Метрики PM2.5
    print("\nСпектральные метрики PM2.5:")
    print(f"  Спектральная энергия PM2.5: {sensor_metrics['pm25_spectral_energy']._value.get():.4f}")
    print(f"  Спектральный центроид PM2.5: {sensor_metrics['pm25_spectral_centroid']._value.get():.4f}")
    
    # Обнаружение аномалий
    print("\nОбнаружение аномалий:")
    print(f"  Счет аномалий: {sensor_metrics['anomaly_score']._value.get():.4f}")
    
    print("\n=== Тест завершен успешно ===")

def test_configuration():
    """Тестирует систему конфигурации"""
    print("\n=== Тестирование конфигурации ===")
    
    print(f"Текущая конфигурация:")
    print(f"  WINDOW_SIZE: {config.WINDOW_SIZE}")
    print(f"  TREND_WINDOW_SIZE: {config.TREND_WINDOW_SIZE}")
    print(f"  FFT_WINDOW_SIZE: {config.FFT_WINDOW_SIZE}")
    print(f"  MIN_DATA_FOR_FFT: {config.MIN_DATA_FOR_FFT}")
    print(f"  FFT_SAMPLE_RATE: {config.FFT_SAMPLE_RATE}")
    print(f"  ANOMALY_ALPHA: {config.ANOMALY_ALPHA}")
    print(f"  ANOMALY_MAX_SCORE: {config.ANOMALY_MAX_SCORE}")
    
    # Тестируем валидацию конфигурации
    try:
        config.validate_config()
        print("OK Конфигурация валидна")
    except ValueError as e:
        print(f"ERROR Ошибка конфигурации: {e}")
    
    print()

if __name__ == "__main__":
    # Тестируем конфигурацию
    test_configuration()
    
    # Тестируем обработку метрик
    test_metrics_processing()
    
    print("\nДля просмотра метрик в Prometheus:")
    print("http://localhost:8000/metrics")
    print("\nДля просмотра в Grafana:")
    print("Используйте новые метрики с префиксами:")
    print("- mqtt_test_sensor_001_temp_spectral_*")
    print("- mqtt_test_sensor_001_humidity_spectral_*")
    print("- mqtt_test_sensor_001_pm25_spectral_*")
    print("- mqtt_test_sensor_001_anomaly_score")
