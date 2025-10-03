from pymongo import MongoClient
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt
from scipy.fft import fft, fftfreq
from scipy.signal import welch, lombscargle

client = MongoClient("mongodb://localhost:27017/")
collection = client["mqtt_database"]["your_collection"]
data = list(collection.find(
    {"MacAddress": "000DE0163B58"},
    {"TemperatureC": 1, "MsgTimeStamp": 1, "_id": 0}
).limit(20000))
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


Ts = np.median(np.diff(time_seconds))
fs = 1/Ts  # частота
detrended = values - np.polyval(np.polyfit(time_seconds, values, 1), time_seconds)
normalized = (detrended - np.mean(detrended)) / np.std(detrended)

plt.figure(figsize=(12, 6))
nperseg = min(1024, len(normalized)//2)
freqs_welch, psd = welch(normalized, fs=fs, nperseg=nperseg, scaling='spectrum')

plt.semilogy(freqs_welch, psd, 'b-', linewidth=1.5)
plt.title("Спектральная плотность мощности (метод Уэлча)\n", fontsize=14)
plt.xlabel("Частота (Гц)", fontsize=12)
plt.ylabel("Мощность (логарифмическая шкала)", fontsize=12)
plt.grid(True, linestyle='--', alpha=0.7)
plt.xlim([0, freqs_welch[-1]])


peaks = np.where(psd > 0.01*np.max(psd))[0] ##высота пиков
for peak in peaks:
    if freqs_welch[peak] > 0:
        plt.annotate(f'{freqs_welch[peak]:.4f} Гц',
                     xy=(freqs_welch[peak], psd[peak]),
                     xytext=(5, 10), textcoords='offset points',
                     arrowprops=dict(arrowstyle="->"))

plt.tight_layout()
plt.show()
#fft
plt.figure(figsize=(12, 6))
N = len(normalized)
yf = fft(normalized)
xf = fftfreq(N, Ts)[:N//2]
fft_spectrum = 2.0/N * np.abs(yf[:N//2])

plt.plot(xf, fft_spectrum, 'r-', linewidth=1.5)
plt.title("Амплитудный спектр (FFT)\n", fontsize=14)
plt.xlabel("Частота (Гц)", fontsize=12)
plt.ylabel("Амплитуда", fontsize=12)
plt.grid(True, linestyle='--', alpha=0.7)
plt.xlim([0, xf[-1]])

ymax = np.max(fft_spectrum[1:])*1.1
plt.ylim([0, ymax if ymax > 0 else 0.1])

plt.figure(figsize=(12, 6))
freqs_lomb = np.linspace(0.001, 0.5, 1000)
pgram = lombscargle(time_seconds, normalized, freqs_lomb, normalize=True)

plt.plot(freqs_lomb, pgram, 'g-', linewidth=1.5)
plt.title("Периодограмма Ломба-Скаргла\n", fontsize=14)
plt.xlabel("Частота (Гц)", fontsize=12)
plt.ylabel("Мощность", fontsize=12)
plt.grid(True, linestyle='--', alpha=0.7)
plt.xlim([0, freqs_lomb[-1]])

plt.tight_layout()
plt.show()

client.close()

print(f"Анализ завершен. Основные параметры:")
print(f"• Всего точек: {len(values)}")
print(f"• Период дискретизации: {Ts:.2f} сек")
print(f"• Частота дискретизации: {fs:.2f} Гц")
print(f"• Длительность записи: {time_seconds[-1]/3600:.2f} часов")
print(f"• Обнаружено {len(peaks)} значимых частотных компонент")