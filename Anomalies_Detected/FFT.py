import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
from scipy.fft import fft, fftfreq
from pymongo import MongoClient
from scipy.signal.windows import hann  # Исправленный импорт
from scipy.signal import spectrogram
import numpy as np
import matplotlib.pyplot as plt
import scipy.stats as stats
from scipy.stats import anderson, shapiro
import json
from sklearn.ensemble import IsolationForest
from datetime import datetime
import os

# Подключение к MongoDB и загрузка данных
client = MongoClient("mongodb://localhost:27017/")
collection = client["mqtt_database"]["your_collection"]
data = list(collection.find(
    {"MacAddress": "000DE0163B56"},
    {"TemperatureC": 1, "MsgTimeStamp": 1, "_id": 0}).limit(1000000))
df = pd.DataFrame(data)
values = pd.to_numeric(df["TemperatureC"], errors='coerce')
values = values[~np.isnan(values)]

if len(values) == 0:
    raise ValueError("Нет числовых данных для анализа!")

print(f"\n=== Основная статистика ===")
print(f"Всего записей: {len(values)}")
print(f"Среднее: {np.mean(values):.2f}, STD: {np.std(values):.2f}")
print(f"Минимум: {np.min(values):.2f}, Максимум: {np.max(values):.2f}")


def save_to_json(data, data_type):
    """Сохраняет данные в JSON файл с меткой времени"""
    output_dir = "../tools/prometheus-2.54.1.windows-amd64/temperature_data"
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{output_dir}/{data_type}_data_{timestamp}.json"

    # Преобразуем в словарь для сохранения
    if isinstance(data, pd.Series):
        data_dict = {
            'values': data.values.tolist(),
            'indices': data.index.tolist(),
            'timestamps': df.loc[data.index, 'MsgTimeStamp'].astype(str).tolist()
        }
    else:
        data_dict = {
            'values': data.tolist(),
            'timestamps': df['MsgTimeStamp'].astype(str).tolist()
        }

    # Добавляем метаданные
    result = {
        'metadata': {
            'type': data_type,
            'created_at': timestamp,
            'data_points': len(data_dict['values']),
            'mean': float(np.mean(data_dict['values'])),
            'std': float(np.std(data_dict['values']))
        },
        'data': data_dict
    }

    with open(filename, 'w') as f:
        json.dump(result, f, indent=2)

    print(f"\nСохранены {data_type} данные в {filename}")
# Функция для автоматического обнаружения аномалий
def detect_anomalies(data):
    clf = IsolationForest(contamination=0.05, random_state=42)
    anomalies = clf.fit_predict(data.values.reshape(-1, 1))
    return data[anomalies == 1], data[anomalies == -1]


# Разделение данных
good_data, bad_data = detect_anomalies(values)
print(f"\n=== Распределение данных ===")
print(f"Хорошие данные: {len(good_data)} записей")
print(f"Потенциальные аномалии: {len(bad_data)} записей")


# Модифицированная функция проверки нормальности
def check_normality(data, label=""):
    print(f"\n=== Проверка нормальности {label} ===")
    shapiro_test = stats.shapiro(data)
    print(f"Shapiro-Wilk: p-value = {shapiro_test.pvalue:.4f}")

    anderson_test = stats.anderson(data, dist='norm')
    print(f"Anderson-Darling: statistic = {anderson_test.statistic:.2f}")
    print("Критические значения:", anderson_test.critical_values)


# Модифицированная функция визуализации
def plot_normality_check(good_data, bad_data):
    plt.figure(figsize=(14, 10))

    # Гистограммы
    plt.subplot(2, 2, 1)
    plt.hist(good_data, bins=50, density=True, alpha=0.6, color='g', label='Хорошие')
    mu, std = stats.norm.fit(good_data)
    x = np.linspace(min(good_data), max(good_data), 100)
    plt.plot(x, stats.norm.pdf(x, mu, std), 'g', linewidth=2)
    plt.title("Хорошие данные")
    plt.grid()

    plt.subplot(2, 2, 2)
    plt.hist(bad_data, bins=50, density=True, alpha=0.6, color='r', label='Аномалии')
    if len(bad_data) > 1:  # Необходимо как минимум 2 точки для подбора распределения
        mu, std = stats.norm.fit(bad_data)
        x = np.linspace(min(bad_data), max(bad_data), 100)
        plt.plot(x, stats.norm.pdf(x, mu, std), 'r', linewidth=2)
    plt.title("Аномальные данные")
    plt.grid()

    # Q-Q plots
    plt.subplot(2, 2, 3)
    stats.probplot(good_data, dist="norm", plot=plt)
    plt.title("Q-Q plot (Хорошие)")
    plt.grid()

    plt.subplot(2, 2, 4)
    stats.probplot(bad_data, dist="norm", plot=plt)
    plt.title("Q-Q plot (Аномалии)")
    plt.grid()

    plt.tight_layout()
    plt.show()


# Сравнение спектров
def compare_spectrums(good_data, bad_data, sample_spacing=10):
    plt.figure(figsize=(14, 12))

    # Первый график - БПФ (как было)
    plt.subplot(2, 1, 1)
    for data, label, color in [(good_data, "Хорошие данные", "blue"),
                               (bad_data, "Аномалии", "red")]:
        n = len(data)
        if n < 10:  # Минимальный размер для FFT
            continue

        yf = fft(data - np.mean(data))
        xf = fftfreq(n, sample_spacing)[:n // 2]
        plt.plot(xf, 2.0 / n * np.abs(yf[0:n // 2]),
                 color=color, alpha=0.7, label=label)

    plt.ylim(0, 0.015)
    plt.xlim(0, 0.01)
    plt.xlabel("Частота (Гц)")
    plt.ylabel("Амплитуда")
    plt.title("Сравнение спектров FFT")
    plt.legend()
    plt.grid()

    # Второй график - данные по времени
    plt.subplot(2, 1, 2)

    # Получаем временные метки для хороших и плохих данных
    good_indices = good_data.index
    bad_indices = bad_data.index

    # Преобразуем временные метки в datetime, если они еще не в этом формате
    if not pd.api.types.is_datetime64_any_dtype(df['MsgTimeStamp']):
        df['MsgTimeStamp'] = pd.to_datetime(df['MsgTimeStamp'])

    # Отображаем данные с временными метками
    plt.plot(df.loc[good_indices, 'MsgTimeStamp'], good_data.values,
             'b', alpha=0.5, label="Хорошие данные")
    plt.plot(df.loc[bad_indices, 'MsgTimeStamp'], bad_data.values,
             'r', alpha=0.7, label="Аномалии")

    plt.xlabel("Время")
    plt.ylabel("Температура (°C)")
    plt.title("Температура по времени")
    plt.legend()
    plt.grid()

    # Автоматический поворот дат для лучшей читаемости
    plt.gcf().autofmt_xdate()

    plt.tight_layout()
    plt.show()

# Улучшенный анализ спектрограмм
def compare_spectrograms(good_data, bad_data, sample_spacing=10):
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8))

    for data, ax, title in [(good_data, ax1, "Хорошие данные"),
                            (bad_data, ax2, "Аномалии")]:
        if len(data) > 256:  # Минимальный размер для спектрограммы
            fs = 1 / sample_spacing
            f, t, Sxx = spectrogram(data, fs=fs, nperseg=256, noverlap=128)
            im = ax.pcolormesh(t, f, Sxx, shading='gouraud')
            fig.colorbar(im, ax=ax, label="Мощность спектра")
            ax.set_ylim(0.001, 0.003)

        ax.set_ylabel('Частота [Гц]')
        ax.set_title(title)

    plt.xlabel('Время [с]')
    plt.tight_layout()
    plt.show()


# Анализ доминирующих частот
def dominant_freq_comparison(good_data, bad_data, sample_spacing=10):
    plt.figure(figsize=(14, 6))

    for data, label, color in [(good_data, "Хорошие", "blue"),
                               (bad_data, "Аномалии", "red")]:
        if len(data) > 512:
            freqs = []
            for start in range(0, len(data) - 512, 64):
                window = data[start:start + 512]
                window = window - np.mean(window)
                fft_result = fft(window * hann(512))
                freq = fftfreq(512, d=sample_spacing)
                amp = 2.0 / 512 * np.abs(fft_result)
                dom_freq = freq[np.argmax(amp[:256])]  # Только положительные частоты
                freqs.append(dom_freq)

            plt.plot(np.arange(len(freqs)) * 64 * sample_spacing, freqs,
                     color=color, label=label, alpha=0.7)

    plt.ylim(0, 0.003)
    plt.xlabel("Время (сек)")
    plt.ylabel("Доминирующая частота (Гц)")
    plt.title("Сравнение доминирующих частот")
    plt.legend()
    plt.grid()
    plt.show()



# Скользящий статистический анализ
def rolling_comparison(data, window_size=1000):
    rolling_mean = data.rolling(window=window_size).mean()
    rolling_std = data.rolling(window=window_size).std()

    plt.figure(figsize=(14, 8))
    plt.subplot(2, 1, 1)
    plt.plot(data, label="Исходные данные", alpha=0.3)
    plt.plot(rolling_mean, 'r', label=f"Скользящее среднее ({window_size} точек)")
    plt.legend()
    plt.title("Скользящий статистический анализ")
    plt.grid()

    plt.subplot(2, 1, 2)
    plt.plot(rolling_std, 'g', label=f"Скользящее STD ({window_size} точек)")
    plt.legend()
    plt.grid()

    plt.tight_layout()
    plt.show()


def compare_spectrums_enhanced(good_data, bad_data, original_data, sample_spacing=10):
    plt.figure(figsize=(16, 12))

    # Используем доступный стиль
    available_styles = plt.style.available
    preferred_styles = ['seaborn-v0_8', 'seaborn', 'ggplot', 'classic']
    for style in preferred_styles:
        if style in available_styles:
            plt.style.use(style)
            break

    colors = {
        'good': '#4CAF50',
        'bad': '#F44336',
        'original': '#2196F3',
        'diff': '#9C27B0'
    }

    # 1. Основной график БПФ (все три типа данных)
    plt.subplot(3, 1, 1)

    # Оригинальные данные
    n_orig = len(original_data)
    if n_orig >= 10:
        yf_orig = fft(original_data - np.mean(original_data))
        xf_orig = fftfreq(n_orig, sample_spacing)[:n_orig // 2]
        plt.plot(xf_orig, 2.0 / n_orig * np.abs(yf_orig[0:n_orig // 2]),
                 color=colors['original'], alpha=0.6, label='Исходные данные', linewidth=1.2)

    # Нормальные данные
    n_good = len(good_data)
    if n_good >= 10:
        yf_good = fft(good_data - np.mean(good_data))
        xf_good = fftfreq(n_good, sample_spacing)[:n_good // 2]
        plt.plot(xf_good, 2.0 / n_good * np.abs(yf_good[0:n_good // 2]),
                 color=colors['good'], alpha=0.8, label='Нормальные данные', linewidth=1.5)

    # Аномальные данные
    n_bad = len(bad_data)

    if n_bad >= 10:
        yf_bad = fft(bad_data - np.mean(bad_data))
        xf_bad = fftfreq(n_bad, sample_spacing)[:n_bad // 2]
        #plt.plot(xf_bad, 2.0 / n_bad * np.abs(yf_bad[0:n_bad // 2]),
                # color=colors['bad'], alpha=0.8, label='Аномалии', linewidth=1.5)

    plt.ylim(0, 0.015)
    plt.xlim(0, 0.01)
    plt.xlabel("Частота (Гц)", fontsize=11)
    plt.ylabel("Амплитуда", fontsize=11)
    plt.title("Сравнение спектров FFT: исходные, нормальные и аномальные данные", fontsize=13, pad=12)
    plt.legend(fontsize=10, loc='upper right')
    plt.grid(True, alpha=0.3)

    # 2. График разницы между исходными и нормальными данными
    plt.subplot(3, 1, 2)

    if n_orig >= 10 and n_good >= 10:
        common_freq = np.linspace(0, min(xf_orig.max(), xf_good.max()), 1000)
        orig_interp = np.interp(common_freq, xf_orig, 2.0 / n_orig * np.abs(yf_orig[0:n_orig // 2]))
        good_interp = np.interp(common_freq, xf_good, 2.0 / n_good * np.abs(yf_good[0:n_good // 2]))

        diff = orig_interp - good_interp
        plt.plot(common_freq, diff, color=colors['diff'], linewidth=1.5)

        threshold = 0.001
        significant = np.abs(diff) > threshold
        plt.fill_between(common_freq, 0, diff, where=significant,
                         color=colors['diff'], alpha=0.15, label=f'Значимые различия (> {threshold})')

        plt.axhline(0, color='gray', linestyle='--', linewidth=0.8)
        plt.xlabel("Частота (Гц)", fontsize=11)
        plt.ylabel("Разница амплитуд", fontsize=11)
        plt.title("Разница спектров: Исходные - Нормальные", fontsize=13, pad=12)
        plt.legend(fontsize=10)
        plt.grid(True, alpha=0.3)
        plt.xlim(0, 0.005)
        plt.ylim(-0.005, 0.015)

    # 3. График сравнения нормальных и аномальных данных
    plt.subplot(3, 1, 3)

    if n_good >= 10 and n_bad >= 10:
        # Интерполируем к общим частотам
        common_freq = np.linspace(0, min(xf_good.max(), xf_bad.max()), 1000)
        good_interp = np.interp(common_freq, xf_good, 2.0 / n_good * np.abs(yf_good[0:n_good // 2]))
        bad_interp = np.interp(common_freq, xf_bad, 2.0 / n_bad * np.abs(yf_bad[0:n_bad // 2]))

        # Разница между нормальными и аномальными
        diff_gb = good_interp - bad_interp

        plt.plot(common_freq, good_interp, color=colors['good'],
                 label='Нормальные данные', linewidth=1.5, alpha=0.8)
        plt.plot(common_freq, bad_interp, color=colors['bad'],
                 label='Аномалии', linewidth=1.5, alpha=0.8)
        plt.plot(common_freq, diff_gb, color='black',
                 linestyle='--', label='Разница (Нормальные - Аномалии)', linewidth=1.2)

        plt.fill_between(common_freq, good_interp, bad_interp,
                         where=(good_interp > bad_interp),
                         color=colors['good'], alpha=0.1, label='Область превосходства нормальных')
        plt.fill_between(common_freq, good_interp, bad_interp,
                         where=(good_interp < bad_interp),
                         color=colors['bad'], alpha=0.1, label='Область превосходства аномалий')

        plt.xlabel("Частота (Гц)", fontsize=11)
        plt.ylabel("Амплитуда", fontsize=11)
        plt.title("Сравнение спектров: Нормальные vs Аномалии", fontsize=13, pad=12)
        plt.legend(fontsize=9, loc='upper right')
        plt.grid(True, alpha=0.3)
        plt.xlim(0, 0.01)
        plt.ylim(0, 0.02)

    plt.tight_layout()
    plt.show()


def compare_spectrums_enhanced_with_time(good_data, bad_data, original_data, sample_spacing=10):
    fig = plt.figure(figsize=(16, 12))

    # 1. График температуры по времени (верхний)
    ax1 = plt.subplot(2, 1, 1)

    # Преобразуем временные метки
    if not pd.api.types.is_datetime64_any_dtype(df['MsgTimeStamp']):
        df['MsgTimeStamp'] = pd.to_datetime(df['MsgTimeStamp'])

    # Все данные (фон)
    plt.plot(df['MsgTimeStamp'], original_data, 'gray', alpha=0.2, label='Все данные')

    # Нормальные данные
    plt.plot(df.loc[good_data.index, 'MsgTimeStamp'], good_data.values,
             'g', alpha=0.7, label='Нормальные', marker='o', markersize=3, linestyle='')

    # Аномалии
    plt.plot(df.loc[bad_data.index, 'MsgTimeStamp'], bad_data.values,
             'r', alpha=0.9, label='Аномалии', marker='x', markersize=4, linestyle='')

    plt.ylabel("Температура (°C)", fontsize=12)
    plt.title("Распределение данных по времени", fontsize=14)
    plt.legend(fontsize=10)
    plt.grid(True, alpha=0.3)
    plt.gcf().autofmt_xdate()

    # 2. График сравнения спектров (нижний)
    ax2 = plt.subplot(2, 1, 2)

    # Нормальные данные (спектр)
    n_good = len(good_data)
    if n_good >= 10:
        yf_good = fft(good_data - np.mean(good_data))
        xf_good = fftfreq(n_good, sample_spacing)[:n_good // 2]
        plt.plot(xf_good, 2.0 / n_good * np.abs(yf_good[0:n_good // 2]),
                 'g', alpha=0.8, label='Нормальные', linewidth=1.5)

    # Аномальные данные (спектр)
    n_bad = len(bad_data)
    if n_bad >= 10:
        yf_bad = fft(bad_data - np.mean(bad_data))
        xf_bad = fftfreq(n_bad, sample_spacing)[:n_bad // 2]
        plt.plot(xf_bad, 2.0 / n_bad * np.abs(yf_bad[0:n_bad // 2]),
                 'r', alpha=0.8, label='Аномалии', linewidth=1.5)

    plt.ylim(0, 0.015)
    plt.xlim(0, 0.01)
    plt.xlabel("Частота (Гц)", fontsize=12)
    plt.ylabel("Амплитуда", fontsize=12)
    plt.title("Сравнение спектров FFT", fontsize=14)
    plt.legend(fontsize=10)
    plt.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()

def save_data_to_json(data, filename):
    """Сохраняет данные в JSON файл"""
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"Данные сохранены в {filename}")
def plot_normality_check_one(data):
    plt.figure(figsize=(14, 6))

    # Гистограмма с нормальным распределением
    plt.subplot(1, 2, 1)
    plt.hist(data, bins=50, density=True, alpha=0.6, color='blue', label='Данные')
    mu, std = stats.norm.fit(data)
    x = np.linspace(min(data), max(data), 100)
    plt.plot(x, stats.norm.pdf(x, mu, std), 'r', linewidth=2, label='Нормальное распределение')
    plt.title("Гистограмма данных")
    plt.legend()
    plt.grid()

    # Q-Q plot
    plt.subplot(1, 2, 2)
    stats.probplot(data, dist="norm", plot=plt)
    plt.title("Q-Q plot")
    plt.grid()

    plt.tight_layout()
    plt.show()


def normality_tests(data, alpha=0.05):
    """
    Проверяет нормальность распределения с помощью тестов Шапиро-Уилка и Андерсона-Дарлинга.

    Параметры:
        data (array-like): Входные данные.
        alpha (float): Уровень значимости.

    Возвращает:
        dict: Результаты тестов.
    """
    # Тест Шапиро-Уилка (для n < 5000)
    shapiro_test = shapiro(data)
    shapiro_result = shapiro_test.pvalue > alpha

    # Тест Андерсона-Дарлинга
    anderson_test = anderson(data, dist='norm')
    critical_value = anderson_test.critical_values[2]  # Для alpha=0.05
    anderson_result = anderson_test.statistic < critical_value

    return {
        'Shapiro-Wilk': {
            'statistic': shapiro_test.statistic,
            'p-value': shapiro_test.pvalue,
            'is_normal': shapiro_result
        },
        'Anderson-Darling': {
            'statistic': anderson_test.statistic,
            'critical_value': critical_value,
            'is_normal': anderson_result
        }
    }


def calculate_skew_kurtosis(data):
    """
    Вычисляет коэффициент асимметрии и эксцесса.

    Параметры:
        data (array-like): Входные данные.

    Возвращает:
        tuple: (skewness, kurtosis)
    """
    skewness = stats.skew(data)
    kurtosis = stats.kurtosis(data, fisher=False)  # Fisher=False для эксцесса относительно нормального распределения
    return skewness, kurtosis


def plot_qq(data, title="Q-Q plot"):
    """
    Строит Q-Q plot для проверки нормальности распределения.

    Параметры:
        data (array-like): Входные данные.
        title (str): Заголовок графика.
    """
    plt.figure(figsize=(10, 6))
    stats.probplot(data, dist="norm", plot=plt)
    plt.title(title)
    plt.grid(True)
    plt.show()


def plot_histogram(data, bins=30, color='blue', title="Гистограмма данных"):
    """
    Строит гистограмму данных с наложенной кривой нормального распределения.

    Параметры:
        data (array-like): Входные данные.
        bins (int): Количество бинов в гистограмме.
        color (str): Цвет гистограммы.
        title (str): Заголовок графика.
    """
    plt.figure(figsize=(10, 6))

    # Гистограмма
    plt.hist(data, bins=bins, density=True, alpha=0.6, color=color, label='Данные')

    # Нормальное распределение
    mu, sigma = np.mean(data), np.std(data)
    x = np.linspace(min(data), max(data), 100)
    y = stats.norm.pdf(x, mu, sigma)
    plt.plot(x, y, 'r-', linewidth=2, label=f'Нормальное распределение\n(μ={mu:.2f}, σ={sigma:.2f})')

    plt.title(title)
    plt.xlabel('Значение')
    plt.ylabel('Плотность вероятности')
    plt.legend()
    plt.grid(True)
    plt.show()
def analyze_normality(data, bins=30, color='blue'):
    """
    Проводит полный анализ нормальности распределения:
    - Гистограмма с нормальной кривой
    - Q-Q plot
    - Расчет skewness и kurtosis
    - Статистические тесты

    Параметры:
        data (array-like): Входные данные.
        bins (int): Количество бинов в гистограмме.
        color (str): Цвет гистограммы.
    """
    print("=== Анализ нормальности распределения ===")

    # Визуализация
    plot_histogram(data, bins, color)
    plot_qq(data)

    # Коэффициенты
    skewness, kurtosis = calculate_skew_kurtosis(data)
    print(f"\nКоэффициент асимметрии (skewness): {skewness:.4f}")
    print(f"Коэффициент эксцесса (kurtosis): {kurtosis:.4f}")
    print("(Для нормального распределения: skewness ≈ 0, kurtosis ≈ 3)")

    # Статистические тесты
    test_results = normality_tests(data)
    print("\nРезультаты тестов:")
    for test_name, result in test_results.items():
        print(f"\n{test_name}:")
        for key, value in result.items():
            print(f"  {key}: {value:.4f}" if isinstance(value, float) else f"  {key}: {value}")

    # Заключение
    is_normal = test_results['Shapiro-Wilk']['is_normal'] and test_results['Anderson-Darling']['is_normal']
    print("\nЗаключение:",
          "Распределение можно считать нормальным." if is_normal else "Распределение отклоняется от нормального.")


import scipy.stats as stats


def fit_distributions(data):
    """
    Подбирает параметры распределений и вычисляет критерий AIC.
    Возвращает отсортированный список распределений по возрастанию AIC.
    """
    distributions = [
        stats.norm, stats.lognorm, stats.weibull_min, stats.expon
    ]
    results = []
    for dist in distributions:
        try:
            params = dist.fit(data)
            log_likelihood = dist.logpdf(data, *params).sum()
            aic = 2 * len(params) - 2 * log_likelihood
            results.append((dist.name, params, aic))
        except Exception as e:
            print(f"Ошибка при подборе {dist.name}: {str(e)}")
    return sorted(results, key=lambda x: x[2])


# Вызываем функцию и сохраняем результат
"""fitted_dists = fit_distributions(values)

# Красиво выводим результаты
print("\n=== Результаты подбора распределений ===")
print("(Чем меньше AIC, тем лучше соответствие)\n")
for i, (name, params, aic) in enumerate(fitted_dists, 1):
    print(f"{i}. {name.upper():<12} | AIC = {aic:.2f}")
    print(f"   Параметры: {params}\n")
"""
plot_normality_check_one(values)
analyze_normality(values)
check_normality(good_data, "хороших данных")
check_normality(bad_data, "аномалий")

plot_normality_check(good_data, bad_data)
compare_spectrums(good_data, bad_data)
compare_spectrograms(good_data, bad_data)
dominant_freq_comparison(good_data, bad_data)
rolling_comparison(pd.Series(values))

compare_spectrums_enhanced_with_time(good_data, bad_data, values)
compare_spectrums_enhanced(good_data, bad_data, values)
"""
save_to_json(good_data,"good")
save_to_json(bad_data,"bad")
save_to_json(values,"basic")
"""