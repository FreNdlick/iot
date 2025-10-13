#!/usr/bin/env python3
"""
Тест улучшений для быстрого запуска системы метрик
"""
import time
import numpy as np
from prometheus_client import start_http_server
from Analyz.metrics_process import create_sensor_metrics, metrics_processor

def test_startup_improvements():
    """Тестирует улучшения для быстрого запуска"""
    print("=== Тест улучшений для быстрого запуска ===\n")
    
    # Запускаем Prometheus сервер
    print("Запуск Prometheus сервера на порту 8000...")
    start_http_server(8000)
    print("Prometheus сервер запущен")
    
    # Создаем метрики для тестовых сенсоров
    sensor_ids = ["000DE0163B57", "000DE0163B59", "000DE0163B58", "000DE0163B56"]
    sensor_metrics = {}
    
    print("\nСоздание метрик для сенсоров...")
    for sensor_id in sensor_ids:
        sensor_metrics[sensor_id] = create_sensor_metrics(sensor_id)
        print(f"  Созданы метрики для {sensor_id}")
    
    print("\n=== Тест 1: Инициализация с предзаполнением ===")
    
    # Предзаполняем данные для быстрого старта
    for i, sensor_id in enumerate(sensor_ids):
        initial_data = {
            'temperature_c': 20 + i * 2,
            'humidity': 50 + i * 5,
            'pm25': 10 + i * 2,
            'dew_point_c': 15 + i * 2
        }
        metrics_processor.prefill_sensor_data(sensor_id, initial_data)
        print(f"  Предзаполнены данные для {sensor_id}")
    
    print("\n=== Тест 2: Обработка первого реального сообщения ===")
    
    # Обрабатываем первое реальное сообщение
    for i, sensor_id in enumerate(sensor_ids):
        new_data = {
            'TemperatureC': 22 + i * 1.5,
            'Humidity': 55 + i * 3,
            'PM25': 12 + i * 1.5,
            'DewPointC': 17 + i * 1.5
        }
        
        print(f"  Обработка данных для {sensor_id}: {new_data}")
        metrics_processor.process_metrics(sensor_id, sensor_metrics[sensor_id], new_data)
    
    print("\n=== Результаты после первого сообщения ===")
    
    for sensor_id in sensor_ids:
        metrics = sensor_metrics[sensor_id]
        print(f"\nСенсор {sensor_id}:")
        print(f"  Базовые метрики готовы: {metrics['metrics_ready_basic']._value.get()}")
        print(f"  Статистические метрики готовы: {metrics['metrics_ready_statistical']._value.get()}")
        print(f"  Спектральные метрики готовы: {metrics['metrics_ready_spectral']._value.get()}")
        print(f"  Обнаружение аномалий готово: {metrics['metrics_ready_anomaly']._value.get()}")
        
        print(f"  Температура: {metrics['temperature_c']._value.get():.2f}C")
        print(f"  Влажность: {metrics['humidity']._value.get():.2f}%")
        print(f"  PM2.5: {metrics['pm25']._value.get():.2f} ug/m3")
        
        # Проверяем спектральные метрики
        if metrics['metrics_ready_spectral']._value.get():
            print(f"  Спектральная энергия температуры: {metrics['temp_spectral_energy']._value.get():.4f}")
            print(f"  Спектральный центроид температуры: {metrics['temp_spectral_centroid']._value.get():.4f}")
        else:
            print("  Спектральные метрики еще не готовы")
    
    print("\n=== Тест 3: Прогрессивное накопление данных ===")
    
    # Добавляем еще несколько сообщений для демонстрации прогрессивного вычисления
    for round_num in range(5):
        print(f"\nРаунд {round_num + 1}:")
        
        for i, sensor_id in enumerate(sensor_ids):
            # Генерируем реалистичные данные с небольшими вариациями
            base_temp = 22 + i * 1.5
            base_humidity = 55 + i * 3
            base_pm25 = 12 + i * 1.5
            
            new_data = {
                'TemperatureC': base_temp + np.random.normal(0, 0.5),
                'Humidity': base_humidity + np.random.normal(0, 2),
                'PM25': max(0, base_pm25 + np.random.normal(0, 1)),
                'DewPointC': (base_temp + np.random.normal(0, 0.5)) - 5
            }
            
            metrics_processor.process_metrics(sensor_id, sensor_metrics[sensor_id], new_data)
            
            # Показываем прогресс готовности метрик
            metrics = sensor_metrics[sensor_id]
            ready_count = sum([
                metrics['metrics_ready_basic']._value.get(),
                metrics['metrics_ready_statistical']._value.get(),
                metrics['metrics_ready_spectral']._value.get(),
                metrics['metrics_ready_anomaly']._value.get()
            ])
            print(f"  {sensor_id}: {ready_count}/4 метрик готовы")
        
        time.sleep(0.5)  # Небольшая задержка между раундами
    
    print("\n=== Финальные результаты ===")
    
    for sensor_id in sensor_ids:
        metrics = sensor_metrics[sensor_id]
        print(f"\nСенсор {sensor_id}:")
        print(f"  Базовые метрики: {'OK' if metrics['metrics_ready_basic']._value.get() else 'NO'}")
        print(f"  Статистические метрики: {'OK' if metrics['metrics_ready_statistical']._value.get() else 'NO'}")
        print(f"  Спектральные метрики: {'OK' if metrics['metrics_ready_spectral']._value.get() else 'NO'}")
        print(f"  Обнаружение аномалий: {'OK' if metrics['metrics_ready_anomaly']._value.get() else 'NO'}")
        
        if metrics['metrics_ready_spectral']._value.get():
            print(f"  Спектральная энергия: {metrics['temp_spectral_energy']._value.get():.4f}")
            print(f"  Доминирующая частота: {metrics['temp_dominant_freq']._value.get():.6f} Гц")
            print(f"  Счет аномалий: {metrics['anomaly_score']._value.get():.4f}")
    
    print("\n=== Тест завершен ===")
    print("Проверьте метрики по адресу: http://localhost:8000/metrics")
    print("Обратите внимание на метрики готовности:")
    print("- mqtt_*_metrics_ready_basic")
    print("- mqtt_*_metrics_ready_statistical") 
    print("- mqtt_*_metrics_ready_spectral")
    print("- mqtt_*_metrics_ready_anomaly")
    print("\nНажмите Ctrl+C для остановки")

if __name__ == "__main__":
    try:
        test_startup_improvements()
        
        # Держим сервер запущенным
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nОстановка теста...")
