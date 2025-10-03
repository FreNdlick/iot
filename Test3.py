import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.fft import fft, fftfreq
from pymongo import MongoClient
import json
from datetime import datetime
import os
import glob


def save_intervals_to_json():
    """Функция для выбора интервалов и сохранения в JSON"""
    # Подключение к MongoDB и загрузка данных
    client = MongoClient("mongodb://localhost:27017/")
    collection = client["mqtt_database"]["your_collection"]
    data = list(collection.find(
        {"MacAddress": "000DE0163B56"},
        {"TemperatureC": 1, "MsgTimeStamp": 1, "_id": 0}).limit(1000000))

    # Преобразование в DataFrame и конвертация типов
    df = pd.DataFrame(data)
    df['TemperatureC'] = pd.to_numeric(df['TemperatureC'], errors='coerce')
    df = df.dropna(subset=['TemperatureC'])
    df['MsgTimeStamp'] = pd.to_datetime(df['MsgTimeStamp'])

    values = df['TemperatureC'].values
    timestamps = df['MsgTimeStamp'].values

    # Визуализация всех данных
    plt.figure(figsize=(14, 5))
    plt.plot(timestamps, values, 'b-')
    plt.title('Полный временной ряд температуры')
    plt.xlabel('Время')
    plt.ylabel('Температура (°C)')
    plt.grid()
    plt.show()

    # Выбор интервалов
    intervals = []
    while True:
        plt.figure(figsize=(14, 5))
        plt.plot(timestamps, values, 'b-')
        for i, interval in enumerate(intervals, 1):
            plt.axvspan(pd.to_datetime(interval['start']), pd.to_datetime(interval['end']),
                        color='g', alpha=0.3)
            plt.text(pd.to_datetime(interval['start']), np.max(values), f'Инт.{i}',
                     ha='left', va='bottom', fontsize=10)
        plt.title('Текущие интервалы (зеленые)')
        plt.grid()
        plt.show()

        action = input("Добавить интервал (a), удалить последний (d), завершить (q): ").lower()

        if action == 'q':
            break
        elif action == 'd':
            if intervals:
                intervals.pop()
            continue

        try:
            start_str = input("Начало интервала (YYYY-MM-DD HH:MM): ")
            end_str = input("Конец интервала (YYYY-MM-DD HH:MM): ")

            start_str = start_str if ':' in start_str[-3:] else start_str + ':00'
            end_str = end_str if ':' in end_str[-3:] else end_str + ':00'

            start = np.datetime64(start_str)
            end = np.datetime64(end_str)

            if start >= end:
                print("Ошибка: начало должно быть раньше конца")
                continue

            mask = (timestamps >= start) & (timestamps <= end)
            if np.sum(mask) == 0:
                print("Ошибка: нет данных в этом интервале")
                continue

            intervals.append({
                'start': str(start),
                'end': str(end),
                'indices': np.where(mask)[0].tolist(),
                'values': values[mask].tolist(),
                'timestamps': timestamps[mask].astype(str).tolist()
            })
            print(f"Добавлен интервал: {start} - {end} ({np.sum(mask)} точек)")

        except Exception as e:
            print(f"Ошибка: {e}")

    if not intervals:
        print("Не выбрано ни одного интервала!")
        return

    # Сохранение в JSON
    output_dir = "selected_intervals"
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{output_dir}/intervals_{timestamp}.json"

    with open(filename, 'w') as f:
        json.dump({
            'metadata': {
                'created_at': timestamp,
                'total_intervals': len(intervals),
                'total_points': sum(len(i['values']) for i in intervals)
            },
            'intervals': intervals
        }, f, indent=2)

    print(f"\nСохранено {len(intervals)} интервалов в {filename}")


def analyze_anomaly_data():
    """Функция для анализа сохраненных хороших и плохих данных"""
    # Поиск файлов в папке temperature_data
    json_files = glob.glob(r"C:\PycharmProjects\NaychkProjectv0.001\tools\prometheus-2.54.1.windows-amd64\temperature_data/*.json")
    if not json_files:
        print("Не найдено JSON файлов в папке temperature_data")
        return

    # Группируем файлы по типу (good/bad)
    data_types = {}
    for file in json_files:
        try:
            with open(file, 'r') as f:
                data = json.load(f)
                data_type = data['metadata']['type']
                if data_type not in data_types:
                    data_types[data_type] = []
                data_types[data_type].append((file, data))
        except Exception as e:
            print(f"Ошибка при чтении файла {file}: {e}")

    if not data_types:
        print("Нет данных для анализа")
        return

    # Выводим доступные типы данных
    print("\nДоступные типы данных:")
    for i, (data_type, files) in enumerate(data_types.items(), 1):
        print(f"{i}. {data_type} (всего {len(files)} файлов)")

    try:
        selected_type = int(input("Выберите тип данных для анализа (номер): ")) - 1
        selected_type = list(data_types.keys())[selected_type]
    except:
        print("Некорректный выбор")
        return

    # Загружаем все данные выбранного типа
    all_data = []
    all_timestamps = []
    for file, data in data_types[selected_type]:
        all_data.extend(data['data']['values'])
        if 'timestamps' in data['data']:
            all_timestamps.extend(data['data']['timestamps'])

    if not all_data:
        print("Нет данных для анализа")
        return

    # Преобразуем в numpy массивы
    values = np.array(all_data, dtype=float)
    if all_timestamps:
        timestamps = pd.to_datetime(all_timestamps)
    else:
        timestamps = pd.date_range(start='2023-01-01', periods=len(values), freq='T')

    # Анализ данных
    plt.figure(figsize=(14, 10))

    # 1. Временной ряд
    plt.subplot(2, 2, 1)
    plt.plot(timestamps, values, 'b-')
    plt.title(f'Временной ряд ({selected_type} данные)')
    plt.xlabel('Время')
    plt.ylabel('Температура (°C)')
    plt.grid()

    # 2. Гистограмма
    plt.subplot(2, 2, 2)
    plt.hist(values, bins=50, density=True, alpha=0.6, color='g')
    plt.title(f'Распределение ({selected_type} данные)')
    plt.xlabel('Температура (°C)')
    plt.ylabel('Плотность')
    plt.grid()

    # 3. БПФ анализ
    plt.subplot(2, 2, 3)
    if len(values) > 1:
        yf = fft(values - np.mean(values))
        xf = fftfreq(len(values), 60)[:len(values) // 2]
        plt.plot(xf, 2.0 / len(values) * np.abs(yf[0:len(values) // 2]))
        plt.title(f'БПФ анализ ({selected_type} данные)')
        plt.xlim(0, 0.002)
        plt.ylim(0, 0.2)
        plt.xlabel('Частота (Гц)')
        plt.ylabel('Амплитуда')
        plt.grid()

    # 4. Скользящее среднее и STD
    plt.subplot(2, 2, 4)
    if len(values) > 100:
        df = pd.DataFrame({'values': values}, index=timestamps)
        rolling_mean = df['values'].rolling(window=100).mean()
        rolling_std = df['values'].rolling(window=100).std()

        plt.plot(rolling_mean, 'r-', label='Скользящее среднее')
        plt.plot(rolling_std, 'g-', label='Скользящее STD')
        plt.title(f'Скользящая статистика ({selected_type} данные)')
        plt.xlabel('Время')
        plt.ylabel('Температура (°C)')
        plt.legend()
        plt.grid()

    plt.tight_layout()
    plt.show()

    # Выводим статистику
    print(f"\n=== Статистика {selected_type} данных ===")
    print(f"Всего точек: {len(values)}")
    print(f"Среднее: {np.mean(values):.2f} °C")
    print(f"Стандартное отклонение: {np.std(values):.2f} °C")
    print(f"Минимум: {np.min(values):.2f} °C")
    print(f"Максимум: {np.max(values):.2f} °C")


def analyze_from_json():
    """Функция для анализа интервалов из JSON файла"""
    # Поиск доступных JSON файлов
    json_files = glob.glob("selected_intervals/*.json")
    if not json_files:
        print("Не найдено JSON файлов в папке selected_intervals")
        return

    print("\nДоступные файлы интервалов:")
    for i, file in enumerate(json_files, 1):
        print(f"{i}. {os.path.basename(file)}")

    try:
        selected = int(input("Выберите номер файла для анализа: ")) - 1
        if selected < 0 or selected >= len(json_files):
            raise ValueError
    except:
        print("Некорректный выбор")
        return

    with open(json_files[selected], 'r') as f:
        data = json.load(f)

    intervals = data['intervals']
    print(f"\nЗагружено {len(intervals)} интервалов из {json_files[selected]}")

    # 1. Графики временных рядов для каждого интервала
    plt.figure(figsize=(14, 5 * len(intervals)))
    for i, interval in enumerate(intervals, 1):
        plt.subplot(len(intervals), 1, i)
        plt.plot(pd.to_datetime(interval['timestamps']), interval['values'], 'b-')
        plt.title(f"Интервал {i}: {interval['start']} - {interval['end']} ({len(interval['values'])} точек)")
        plt.xlabel('Время')
        plt.ylabel('Температура (°C)')
        plt.grid()
    plt.tight_layout()
    plt.show()

    # 2. Сравнение БПФ
    plt.figure(figsize=(14, 8))
    for i, interval in enumerate(intervals, 1):
        y = np.array(interval['values'], dtype=float)
        n = len(y)

        if n < 2:
            print(f"Интервал {i} содержит слишком мало точек ({n}) для анализа БПФ")
            continue

        yf = fft(y - np.mean(y))
        xf = fftfreq(n, 60)[:n // 2]

        plt.subplot(2, 2, i)
        plt.plot(xf, 2.0 / n * np.abs(yf[0:n // 2]))
        plt.title(f"БПФ интервала {i}\n{interval['start']} - {interval['end']}")
        plt.xlim(0, 0.0007)
        plt.ylim(0, 0.2)
        plt.xlabel('Частота ')
        plt.ylabel('Амплитуда')
        plt.grid()
    plt.tight_layout()
    plt.show()

    # 3. Сравнение спектральных характеристик
    dominant_freqs = []
    for interval in intervals:
        y = np.array(interval['values'], dtype=float)
        n = len(y)

        if n >= 2:
            yf = fft(y - np.mean(y))
            xf = fftfreq(n, 60)[:n // 2]
            amplitudes = 2.0 / n * np.abs(yf[0:n // 2])

            if len(amplitudes) > 0:
                dominant_freq = xf[np.argmax(amplitudes)]
                dominant_freqs.append(dominant_freq)

    if dominant_freqs:
        plt.figure(figsize=(10, 5))
        plt.bar(range(len(dominant_freqs)), dominant_freqs)
        plt.title('Доминирующие частоты интервалов')
        plt.xlabel('Номер интервала')
        plt.ylabel('Частота (Гц)')
        plt.grid()
        plt.show()


# Главное меню
while True:
    print("\n=== Меню анализа температурных данных ===")
    print("1. Выбрать новые интервалы и сохранить в JSON")
    print("2. Проанализировать интервалы из JSON файла")
    print("3. Проанализировать сохраненные хорошие/плохие данные")
    print("4. Выход")

    choice = input("Выберите действие (1-4): ")

    if choice == '1':
        save_intervals_to_json()
    elif choice == '2':
        analyze_from_json()
    elif choice == '3':
        analyze_anomaly_data()
    elif choice == '4':
        break
    else:
        print("Некорректный выбор, попробуйте еще раз")