#!/usr/bin/env python3
"""
Тест интеграции с основным приложением
"""
import time
import threading
from prometheus_client import start_http_server
from Analyz.metrics_process import create_sensor_metrics, metrics_processor

def test_app_integration():
    """Тестирует интеграцию с основным приложением"""
    print("=== Тест интеграции с основным приложением ===\n")
    
    # Запускаем Prometheus сервер
    print("Запуск Prometheus сервера на порту 8000...")
    start_http_server(8000)
    print("Prometheus сервер запущен")
    
    # Создаем метрики для тестовых сенсоров
    sensor_metrics = {
        "000DE0163B57": create_sensor_metrics("000DE0163B57"),
        "000DE0163B59": create_sensor_metrics("000DE0163B59"),
        "000DE0163B58": create_sensor_metrics("000DE0163B58"),
        "000DE0163B56": create_sensor_metrics("000DE0163B56")
    }
    
    print("Метрики сенсоров созданы")
    
    # Симулируем получение данных от MQTT
    print("\nСимуляция получения данных от MQTT...")
    
    import random
    import numpy as np
    
    for i in range(100):
        for sensor_id in sensor_metrics.keys():
            # Генерируем тестовые данные
            temp = 20 + random.uniform(-5, 5) + 2 * np.sin(i * 0.1)
            humidity = 60 + random.uniform(-10, 10) + 3 * np.cos(i * 0.05)
            pm25 = 10 + random.uniform(-5, 15) + 5 * np.sin(i * 0.02)
            
            new_data = {
                'TemperatureC': temp,
                'Humidity': humidity,
                'PM25': pm25,
                'DewPointC': temp - 5
            }
            
            # Обрабатываем метрики
            metrics_processor.process_metrics(sensor_id, sensor_metrics[sensor_id], new_data)
        
        if (i + 1) % 20 == 0:
            print(f"Обработано {i + 1} циклов данных")
        
        time.sleep(0.1)  # Небольшая задержка
    
    print("\nОбработка данных завершена")
    
    # Проверяем, что метрики обновились
    print("\n=== Проверка метрик ===")
    
    for sensor_id, metrics in sensor_metrics.items():
        print(f"\nСенсор {sensor_id}:")
        print(f"  Температура: {metrics['temperature_c']._value.get():.2f}C")
        print(f"  Влажность: {metrics['humidity']._value.get():.2f}%")
        print(f"  PM2.5: {metrics['pm25']._value.get():.2f} ug/m3")
        
        # Проверяем новые спектральные метрики
        if metrics['temp_spectral_energy']._value.get() > 0:
            print(f"  Спектральная энергия температуры: {metrics['temp_spectral_energy']._value.get():.4f}")
            print(f"  Спектральный центроид температуры: {metrics['temp_spectral_centroid']._value.get():.4f}")
            print(f"  Доминирующая частота температуры: {metrics['temp_dominant_freq']._value.get():.6f} Гц")
            print(f"  Счет аномалий: {metrics['anomaly_score']._value.get():.4f}")
        else:
            print("  Спектральные метрики еще не вычислены (недостаточно данных)")
    
    print("\n=== Тест завершен ===")
    print("Проверьте метрики по адресу: http://localhost:8000/metrics")
    print("Нажмите Ctrl+C для остановки")

if __name__ == "__main__":
    try:
        test_app_integration()
        
        # Держим сервер запущенным
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nОстановка теста...")
