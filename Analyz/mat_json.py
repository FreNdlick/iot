import os
import matplotlib.pyplot as plt
from datetime import datetime
from pymongo import MongoClient
import numpy as np
from scipy.stats import pearsonr
from multiprocessing import Process


def load_all_data_from_mongodb(connection_string, database_name, collection_name, query={}):
    try:
        client = MongoClient(connection_string)
        db = client[database_name]
        collection = db[collection_name]
        data = list(collection.find(query))
        client.close()
        print(f"Загружено {len(data)} записей из MongoDB.")
        return data
    except Exception as e:
        print(f"Ошибка при загрузке данных из MongoDB: {e}")
        return []


def plot_correlation_between_sensors(sensor1_data, sensor2_data, sensor1_mac, sensor2_mac, parameter="TemperatureC", save_dir="sensor_plots", show_plots=True, save_plots=True):
    """
    Строит график корреляции между двумя датчиками по заданному параметру (температура или влажность).
    """
    try:
        # Проверка наличия данных
        if not sensor1_data or not sensor2_data:
            print(f"Нет данных для одного из датчиков: {sensor1_mac} или {sensor2_mac}.")
            return

        # Проверка наличия параметра в данных
        if parameter not in sensor1_data[0] or parameter not in sensor2_data[0]:
            print(f"Параметр '{parameter}' отсутствует в данных.")
            return

        # Извлечение данных для первого датчика
        sensor1_values = [float(entry[parameter]) for entry in sensor1_data]
        sensor1_timestamps = [round_to_minute(datetime.strptime(entry["MsgTimeStamp"], "%Y-%m-%d %H:%M:%S")) for entry in sensor1_data]

        # Извлечение данных для второго датчика
        sensor2_values = [float(entry[parameter]) for entry in sensor2_data]
        sensor2_timestamps = [round_to_minute(datetime.strptime(entry["MsgTimeStamp"], "%Y-%m-%d %H:%M:%S")) for entry in sensor2_data]

        # Сопоставление данных по временным меткам (округленным до минут)
        common_timestamps = list(set(sensor1_timestamps).intersection(set(sensor2_timestamps)))
        common_timestamps.sort()

        # Отладочный вывод
        print(f"Общие временные метки для {sensor1_mac} и {sensor2_mac}: {len(common_timestamps)}")

        if not common_timestamps:
            print(f"Нет общих временных меток для {sensor1_mac} и {sensor2_mac}.")
            return

        sensor1_aligned = []
        sensor2_aligned = []
        for timestamp in common_timestamps:
            idx1 = sensor1_timestamps.index(timestamp)
            idx2 = sensor2_timestamps.index(timestamp)
            sensor1_aligned.append(sensor1_values[idx1])
            sensor2_aligned.append(sensor2_values[idx2])

        # Построение графика корреляции
        plt.figure(figsize=(10, 6))
        plt.scatter(
            sensor1_aligned,
            sensor2_aligned,
            label=f"{parameter} ({sensor1_mac} vs {sensor2_mac})",
            color="blue",
            marker='o',
            edgecolor='black'
        )

        # Линия тренда
        trend = np.polyfit(sensor1_aligned, sensor2_aligned, 1)
        plt.plot(
            sensor1_aligned,
            np.polyval(trend, sensor1_aligned),
            label=f"Тренд: y = {trend[0]:.2f}x + {trend[1]:.2f}",
            color="red",
            linestyle='--',
            linewidth=2
        )

        # Расчет корреляции
        correlation, _ = pearsonr(sensor1_aligned, sensor2_aligned)
        plt.text(
            0.05, 0.95,
            f"Корреляция: {correlation:.2f}",
            transform=plt.gca().transAxes,
            fontsize=12,
            verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.8)
        )

        # Настройка графика
        plt.title(f"Корреляция {parameter} между датчиками {sensor1_mac} и {sensor2_mac}", fontsize=16)
        plt.xlabel(f"{parameter} ({sensor1_mac})", fontsize=12)
        plt.ylabel(f"{parameter} ({sensor2_mac})", fontsize=12)
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.legend(fontsize=10)
        plt.tight_layout()

        # Сохранение графика
        if save_plots:
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)

            current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            save_path = os.path.join(save_dir, f"correlation_{sensor1_mac}_vs_{sensor2_mac}_{current_time}.png")
            plt.savefig(save_path, dpi=300)
            print(f"График корреляции сохранен в {save_path}.")

        # Показ графика
        if show_plots:
            plt.show()

        plt.close()
    except Exception as e:
        print(f"Ошибка при построении графика корреляции: {e}")

def round_to_minute(dt):
    """Округляет временную метку до минут."""
    return dt.replace(second=0, microsecond=0)
def get_date_range(data):
    """Определение минимальной и максимальной даты в данных."""
    timestamps = [datetime.strptime(entry["MsgTimeStamp"], "%Y-%m-%d %H:%M:%S") for entry in data]
    return min(timestamps), max(timestamps)


def parse_date_input(date_str, year):
    """Преобразует строку формата 'день.месяц' в объект datetime."""
    try:
        day, month = map(int, date_str.split("."))
        return datetime(year, month, day)
    except Exception as e:
        print(f"Ошибка при разборе даты: {e}")
        return None


def filter_data_by_date_range(data, start_date, end_date):
    """Фильтрация данных по диапазону дат."""
    filtered_data = []
    for entry in data:
        entry_date = datetime.strptime(entry["MsgTimeStamp"], "%Y-%m-%d %H:%M:%S")
        if start_date <= entry_date <= end_date:
            filtered_data.append(entry)
    return filtered_data


def plot_sensor_data_for_sensor(mac_address, entries, color, linestyle, show_plots=True, save_plots=True, save_dir="sensor_plots"):
    """Функция для построения графиков для одного датчика."""
    try:
        # Создание новой фигуры для датчика
        fig, axes = plt.subplots(3, 1, figsize=(12, 15))  # Уменьшили количество графиков до 3
        fig.suptitle(f"Датчик {mac_address}", fontsize=16, fontweight='bold')

        # Извлечение данных
        timestamps = [datetime.strptime(entry["MsgTimeStamp"], "%Y-%m-%d %H:%M:%S") for entry in entries]
        temperature_c = [float(entry["TemperatureC"]) for entry in entries]
        humidity = [float(entry["Humidity"]) for entry in entries]

        # Преобразование времени в числовой формат для построения тренда
        time_numeric = np.arange(len(timestamps))

        # График температуры
        axes[0].plot(
            timestamps,
            temperature_c,
            label="Температура (°C)",
            color=color,
            linestyle=linestyle,
            linewidth=2,
            marker='o',
            markersize=3,
            markerfacecolor=color,
            markeredgecolor='black'
        )

        # Линия тренда для температуры
        trend_temperature = np.polyfit(time_numeric, temperature_c, 1)  # Линейная регрессия
        axes[0].plot(
            timestamps,
            np.polyval(trend_temperature, time_numeric),
            label=f"Тренд температуры: y = {trend_temperature[0]:.2f}x + {trend_temperature[1]:.2f}",
            color="orange",
            linestyle='--',
            linewidth=2
        )

        axes[0].set_title("Температура (°C)", fontsize=14)
        axes[0].set_xlabel("Время", fontsize=12)
        axes[0].set_ylabel("Температура (°C)", fontsize=12)
        axes[0].grid(True, linestyle='--', alpha=0.7)
        axes[0].legend(fontsize=10)
        axes[0].tick_params(axis='x', rotation=45)
        axes[0].tick_params(axis='both', labelsize=10)

        # График влажности
        axes[1].plot(
            timestamps,
            humidity,
            label="Влажность (%)",
            color=color,
            linestyle=linestyle,
            linewidth=2,
            marker='s',
            markersize=3,
            markerfacecolor=color,
            markeredgecolor='black'
        )

        # Линия тренда для влажности
        trend_humidity = np.polyfit(time_numeric, humidity, 1)  # Линейная регрессия
        axes[1].plot(
            timestamps,
            np.polyval(trend_humidity, time_numeric),
            label=f"Тренд влажности: y = {trend_humidity[0]:.2f}x + {trend_humidity[1]:.2f}",
            color="cyan",
            linestyle='--',
            linewidth=2
        )

        axes[1].set_title("Влажность (%)", fontsize=14)
        axes[1].set_xlabel("Время", fontsize=12)
        axes[1].set_ylabel("Влажность (%)", fontsize=12)
        axes[1].grid(True, linestyle='--', alpha=0.7)
        axes[1].legend(fontsize=10)
        axes[1].tick_params(axis='x', rotation=45)
        axes[1].tick_params(axis='both', labelsize=10)

        # График корреляции
        axes[2].scatter(
            temperature_c,
            humidity,
            label="Температура vs Влажность",
            color=color,
            marker='o',
            edgecolor='black'
        )

        # Линия тренда для корреляции
        trend_correlation = np.polyfit(temperature_c, humidity, 1)  # Линейная регрессия
        axes[2].plot(
            temperature_c,
            np.polyval(trend_correlation, temperature_c),
            label=f"Тренд корреляции: y = {trend_correlation[0]:.2f}x + {trend_correlation[1]:.2f}",
            color="purple",
            linestyle='--',
            linewidth=2
        )

        # Расчет корреляции
        correlation, _ = pearsonr(temperature_c, humidity)
        axes[2].text(
            0.05, 0.95,
            f"Корреляция: {correlation:.2f}",
            transform=axes[2].transAxes,
            fontsize=12,
            verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.8)
        )

        axes[2].set_title("Корреляция между температурой и влажностью", fontsize=14)
        axes[2].set_xlabel("Температура (°C)", fontsize=12)
        axes[2].set_ylabel("Влажность (%)", fontsize=12)
        axes[2].grid(True, linestyle='--', alpha=0.7)
        axes[2].legend(fontsize=10)
        axes[2].tick_params(axis='both', labelsize=10)

        # Сохранение графика в папку
        if save_plots:
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)  # Создание папки, если она не существует

            # Генерация имени файла с текущим временем
            current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            save_path = os.path.join(save_dir, f"sensor_{mac_address}_{current_time}.png")
            plt.tight_layout()
            plt.savefig(save_path, dpi=300)  # Сохранение графика
            print(f"График для датчика {mac_address} сохранен в {save_path}.")

        # Показ графика на экране
        if show_plots:
            plt.show()

        plt.close()  # Закрытие фигуры для освобождения памяти
    except Exception as e:
        print(f"Ошибка при построении графиков для датчика {mac_address}: {e}")


def plot_sensor_data(data, save_dir="sensor_plots", show_plots=True, save_plots=True):
    """Визуализация данных для датчиков."""
    if not data:
        print("Нет данных для построения графиков.")
        return

    # Группировка данных по MacAddress
    sensor_data = {}
    for entry in data:
        mac_address = entry["MacAddress"]
        if mac_address not in sensor_data:
            sensor_data[mac_address] = []
        sensor_data[mac_address].append(entry)

    # Переменные для настройки графиков
    colors = ["red", "blue", "green", "purple"]
    linestyles = ['-', '--', ':', '-.']

    # Создание процессов для каждого датчика
    processes = []
    for i, (mac_address, entries) in enumerate(sensor_data.items()):
        p = Process(
            target=plot_sensor_data_for_sensor,
            args=(mac_address, entries, colors[i], linestyles[i], show_plots, save_plots, save_dir)
        )
        processes.append(p)
        p.start()

    # Ожидание завершения всех процессов
    for p in processes:
        p.join()


def plot_all_correlations(sensor_data, parameter="TemperatureC", save_dir="sensor_plots", show_plots=True, save_plots=True):
    """
    Строит графики корреляции для всех возможных пар датчиков.
    """
    sensor_list = list(sensor_data.keys())
    for i in range(len(sensor_list)):
        for j in range(i + 1, len(sensor_list)):
            sensor1_mac = sensor_list[i]
            sensor2_mac = sensor_list[j]
            plot_correlation_between_sensors(
                sensor_data[sensor1_mac],
                sensor_data[sensor2_mac],
                sensor1_mac,
                sensor2_mac,
                parameter=parameter,
                save_dir=save_dir,
                show_plots=show_plots,
                save_plots=save_plots
            )


if __name__ == "__main__":
    # Параметры подключения к MongoDB
    mongodb_connection_string = "mongodb://localhost:27017"  # Замените на ваш URI
    database_name = "mqtt_database"  # Замените на имя вашей базы данных
    collection_name = "your_collection"  # Замените на имя вашей коллекции

    query = {}  # Пример запроса (можно оставить пустым для выбора всех документов)
    data = load_all_data_from_mongodb(mongodb_connection_string, database_name, collection_name, query)

    if not data:
        print("Данные из MongoDB не найдены.")
        exit()

    # Определение доступного интервала дат
    min_date, max_date = get_date_range(data)
    print(f"Доступный интервал данных: с {min_date.day}.{min_date.month} по {max_date.day}.{max_date.month}")

    # Запрос диапазона дат у пользователя
    date_range_input = input("Введите диапазон дат (например, 23.12 - 03.01): ")
    start_date_str, end_date_str = map(str.strip, date_range_input.split("-"))

    # Определение года для начальной и конечной даты
    start_year = min_date.year
    end_year = start_year + 1 if int(end_date_str.split(".")[1]) < int(start_date_str.split(".")[1]) else start_year

    # Преобразование введенных дат в объекты datetime
    start_date = parse_date_input(start_date_str, start_year)
    end_date = parse_date_input(end_date_str, end_year)

    if not start_date or not end_date:
        print("Ошибка при разборе дат. Проверьте формат ввода.")
        exit()

    filtered_data = filter_data_by_date_range(data, start_date, end_date)

    if not filtered_data:
        print("Нет данных для выбранного диапазона дат.")
        exit()

    # Визуализация данных
    plot_sensor_data(filtered_data, save_dir="sensor_plots", show_plots=True, save_plots=False)

    # Группировка данных по MacAddress
    sensor_data = {}
    for entry in filtered_data:
        mac_address = entry["MacAddress"]
        if mac_address not in sensor_data:
            sensor_data[mac_address] = []
        sensor_data[mac_address].append(entry)

    # Выбор параметра для анализа
    parameter = input("Введите параметр для анализа (TemperatureC или Humidity): ").strip()
    if parameter not in ["TemperatureC", "Humidity"]:
        print("Неверный параметр. Используется значение по умолчанию: TemperatureC.")
        parameter = "TemperatureC"

    # Проверка, что есть данные для минимум двух датчиков
    if len(sensor_data) >= 2:
        # Построение корреляций для всех пар датчиков
        plot_all_correlations(sensor_data, parameter=parameter, save_dir="sensor_plots", show_plots=True, save_plots=False)
    else:
        print("Недостаточно данных для построения корреляции между датчиками.")