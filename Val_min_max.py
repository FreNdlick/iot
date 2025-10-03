from pymongo import MongoClient
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt
from scipy.fft import fft, fftfreq
from scipy.signal import welch

# 1. Подключение и загрузка данных
client = MongoClient("mongodb://localhost:27017/")
collection = client["mqtt_database"]["your_collection"]
data = list(collection.find(
    {"MacAddress": "000DE0163B56"},
    {"Humidity": 1, "MsgTimeStamp": 1, "_id": 0}
).limit(100000))

# 2. Подготовка данных
values = []
timestamps = []
for doc in data:
    try:
        values.append(float(doc["TemperatureC"]))
        timestamps.append(datetime.fromisoformat(doc["MsgTimeStamp"]))
    except:
        continue

values = np.array(values)
time_seconds = np.array([(t - timestamps[0]).total_seconds() for t in timestamps])

# 3. Параметры дискретизации
Ts = np.median(np.diff(time_seconds))
fs = 1 / Ts

# 4. Детрендирование и нормализация
detrended = values - np.polyval(np.polyfit(time_seconds, values, 1), time_seconds)
normalized = (detrended - np.mean(detrended)) / np.std(detrended)

# 5. Метод Уэлча
plt.figure(figsize=(12, 6))
nperseg = min(1024, len(normalized)//2)
freqs_welch, psd = welch(normalized, fs=fs, nperseg=nperseg, scaling='spectrum')

plt.semilogy(freqs_welch, psd, 'b-', linewidth=1.5)
plt.title("Спектральная плотность мощности (метод Уэлча)", fontsize=14)
plt.xlabel("Частота (Гц)", fontsize=12)
plt.ylabel("Мощность", fontsize=12)
plt.grid(True, linestyle='--', alpha=0.7)
plt.xlim([0, freqs_welch[-1]])

peaks = np.where(psd > 0.1 * np.max(psd))[0]
for peak in peaks:
    if freqs_welch[peak] > 0:
        plt.annotate(f'{freqs_welch[peak]:.4f} Гц',
                     xy=(freqs_welch[peak], psd[peak]),
                     xytext=(5, 10), textcoords='offset points',
                     arrowprops=dict(arrowstyle="->"))

plt.tight_layout()
plt.show()

# 6. FFT анализ
plt.figure(figsize=(12, 6))
N = len(normalized)
yf = fft(normalized)
xf = fftfreq(N, Ts)[:N//2]
fft_spectrum = 2.0 / N * np.abs(yf[:N//2])

plt.plot(xf, fft_spectrum, 'r-', linewidth=1.5)
plt.title("Амплитудный спектр (FFT)", fontsize=14)
plt.xlabel("Частота (Гц)", fontsize=12)
plt.ylabel("Амплитуда", fontsize=12)
plt.grid(True, linestyle='--', alpha=0.7)
plt.xlim([0, xf[-1]])

ymax = np.max(fft_spectrum[1:]) * 1.1
plt.ylim([0, ymax if ymax > 0 else 0.1])

plt.tight_layout()
plt.show()

# 7. Усреднение амплитуд и частот
peak_indices = np.where(fft_spectrum > 0.1 * np.max(fft_spectrum))[0]
significant_freqs = xf[peak_indices]
significant_amps = fft_spectrum[peak_indices]

avg_freq = np.mean(significant_freqs)
avg_amp = np.mean(significant_amps)

print("\nУсреднённые значения:")
print(f"• Средняя частота: {avg_freq:.4f} Гц")
print(f"• Средняя амплитуда: {avg_amp:.4f}")

# 8. Дельта-импульсы (на основе частотных пиков)
plt.figure(figsize=(12, 4))
delta_height = avg_amp
delta_freqs = significant_freqs

for f in delta_freqs:
    plt.vlines(f, 0, delta_height, color='purple', linewidth=2)

plt.title("Частотные компоненты как дельта-импульсы", fontsize=14)
plt.xlabel("Частота (Гц)", fontsize=12)
plt.ylabel("Амплитуда (условная)", fontsize=12)
plt.grid(True, linestyle='--', alpha=0.7)
plt.xlim([0, max(delta_freqs)*1.1])
plt.ylim([0, delta_height * 1.2])

plt.tight_layout()
plt.show()

# 9. Статистика
print(f"\nАнализ завершен:")
print(f"• Точек данных: {len(values)}")
print(f"• Период дискретизации: {Ts:.3f} сек")
print(f"• Частота дискретизации: {fs:.3f} Гц")
print(f"• Длительность записи: {time_seconds[-1] / 3600:.2f} часов")
print(f"• Обнаружено {len(significant_freqs)} частотных компонент")
from scipy.signal import spectrogram

# 10. Спектрограмма (STFT)
nperseg = 1024
noverlap = 512

frequencies, times, Sxx = spectrogram(normalized, fs=fs, nperseg=nperseg, noverlap=noverlap, scaling='spectrum')

plt.figure(figsize=(14, 6))
plt.pcolormesh(times, frequencies, 10 * np.log10(Sxx + 1e-10), shading='gouraud', cmap='viridis')
plt.colorbar(label='Мощность (дБ)')
plt.title('Спектрограмма сигнала (STFT)', fontsize=14)
plt.xlabel('Время (сек)', fontsize=12)
plt.ylabel('Частота (Гц)', fontsize=12)
plt.tight_layout()
plt.show()

from scipy.signal import spectrogram
import matplotlib.pyplot as plt
import numpy as np

# Параметры STFT
nperseg = 1024
noverlap = 512

# STFT
frequencies, times, Sxx = spectrogram(normalized, fs=fs, nperseg=nperseg, noverlap=noverlap, scaling='spectrum')

# Логарифм мощности (децибелы)
Sxx_db = 10 * np.log10(Sxx + 1e-10)

# Порог локализации: считаем, что хорошо, если в окне есть >=1 пик выше порога
quality_labels = []
threshold_db = np.percentile(Sxx_db, 95)  # Верхний 5% мощностей — за пики

for i in range(Sxx_db.shape[1]):
    spectrum_slice = Sxx_db[:, i]
    peak_count = np.sum(spectrum_slice > threshold_db)
    if peak_count > 2:  # если 2+ пиков — хорошие данные
        quality_labels.append("good")
    else:
        quality_labels.append("bad")

# Визуализация: столбчатая карта мощностей
plt.figure(figsize=(14, 6))
plt.imshow(Sxx_db, aspect='auto', origin='lower',
           extent=[times[0], times[-1], frequencies[0], frequencies[-1]],
           cmap='viridis')
plt.colorbar(label='Мощность (дБ)')
plt.title('Частоты по времени (спектрограмма)', fontsize=14)
plt.xlabel('Время (сек)', fontsize=12)
plt.ylabel('Частота (Гц)', fontsize=12)

# Добавим цветовую маску поверх — "плохие" окна оттеним красным
for i, label in enumerate(quality_labels):
    if label == "bad":
        t0 = times[i] - (times[1]-times[0])/2
        t1 = times[i] + (times[1]-times[0])/2
        plt.axvspan(t0, t1, color='red', alpha=0.2)

plt.tight_layout()
plt.show()

