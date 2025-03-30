import numpy as np
import scipy.io.wavfile as wav
from scipy.signal import correlate
import soundfile as sf

def find_delay(sig1, sig2):
    """Berechnet den Zeitversatz zwischen zwei Signalen mit Kreuzkorrelation"""
    corr = correlate(sig1, sig2, mode="full")
    delay = np.argmax(corr) - (len(sig2) - 1)
    return delay

# Lade zwei Audiodateien
rate1, data1 = wav.read("audio1.wav")
rate2, data2 = wav.read("audio2.wav")

# Falls die Audiodaten mehrkanalig sind, auf Mono umwandeln
if len(data1.shape) > 1:
    data1 = np.mean(data1, axis=1)
if len(data2.shape) > 1:
    data2 = np.mean(data2, axis=1)

# Kürze auf gleiche Länge (zumindest initial)
min_length = min(len(data1), len(data2))
data1, data2 = data1[:min_length], data2[:min_length]

# Berechne den Zeitversatz
delay = find_delay(data1, data2)

print(f"Ermittelter Zeitversatz: {delay} Samples ({delay / rate1:.5f} Sekunden)")

# Korrigiere das verzögerte Signal
if delay > 0:
    data2 = np.pad(data2, (delay, 0), mode='constant')[:len(data1)]
elif delay < 0:
    data1 = np.pad(data1, (-delay, 0), mode='constant')[:len(data2)]

# Speichere die synchronisierten Audiodateien
sf.write("audio1_sync.wav", data1, rate1)
sf.write("audio2_sync.wav", data2, rate2)

print("Zeitsynchronisation abgeschlossen! Dateien als 'audio1_sync.wav' und 'audio2_sync.wav' gespeichert.")
