import numpy as np
import scipy.io.wavfile as wav
from scipy.signal import correlate
import os
import soundfile as sf
import matplotlib.pyplot as plt

def find_delay(sig1, sig2):
    """Berechnet den Zeitversatz zwischen zwei Signalen mit Kreuzkorrelation"""
    print(f"Berechne Zeitversatz zwischen {len(sig1)} und {len(sig2)} Samples")
    c1 = sig1 / np.max(sig1)    # Normalisiere auf 1
    c2 = sig2 / np.max(sig2)    # Normalisiere auf 1
    x = np.linspace(0,len(sig1)-1,len(sig1))
    #corr = correlate(c1, c2, mode="full", method = "direct")
    corr = correlate(c1, c2, mode="full")
    xc = np.linspace(-len(sig1) + 1, len(sig2) - 1, len(corr))

    delay = np.argmax(corr) - (len(sig2) - 1)
    plt.figure(1)
    plt.plot(x,c1,x,c2)
    plt.xlabel('time [samples]')
    plt.ylabel('normalized signal amplitude')
    plt.title('raw signals')
    plt.show()
    plt.figure(2)
    plt.plot(xc, corr)
    plt.xlabel('delay [samples]')
    plt.ylabel('corr function')
    plt.title('cross correlation')
    plt.show()
    return delay

plt.close('all')
filepath = "E:/COHIRADIA/Archiviert/unvollst_MW_30_and_31_12_2006_analogue_VR/Optional_intermediate_files/2GBSplit"
input_filename1 = "06-filtered_B2006_20210801_184741_1100kHz_10_20061230_235828_1100kHz_demod550.wav"
input_filename2 = "02-filtered_B2006_20210801_184741_1100kHz_10_20061230_235828_1100kHz_demod1423.wav"
#input_filename1 = "02-filtered_B2006_20210801_184741_1100kHz_10_20061230_235828_1100kHz_demod1423.wav"
infile1 = os.path.join(filepath, input_filename1)
infile2 = os.path.join(filepath, input_filename2)

# Lade zwei Audiodateien
rate1, data1 = wav.read(infile1)
rate2, data2 = wav.read(infile2)

# Falls die Audiodaten mehrkanalig sind, auf Mono umwandeln
if len(data1.shape) > 1:
    data1 = np.mean(data1, axis=1)
if len(data2.shape) > 1:
    data2 = np.mean(data2, axis=1)

# Kürze auf gleiche Länge (zumindest initial)
samplelength = 100000  # Beispielwert, kann angepasst werden
offset = 2000000

min_length = min(len(data1), len(data2))
min_length_corr = min(samplelength, min_length)
data1, data2 = data1[:min_length], data2[:min_length]
cdata1, cdata2 = data1[offset:offset + min_length_corr], data2[offset:offset + min_length_corr]
# Berechne den Zeitversatz
delay = find_delay(cdata1, cdata2)

print(f"Ermittelter Zeitversatz: {delay} Samples ({delay / rate1:.5f} Sekunden)")

# Korrigiere das verzögerte Signal
if delay > 0:
    data2 = np.pad(data2, (delay, 0), mode='constant')[:len(data1)]
elif delay < 0:
    data1 = np.pad(data1, (-delay, 0), mode='constant')[:len(data2)]



# Speichere die synchronisierten Audiodateien
outfile1 = os.path.join(filepath, "audio1_sync.wav")
outfile2 = os.path.join(filepath, "audio2_sync.wav")
sf.write(outfile1, data1, rate1)
sf.write(outfile2, data2, rate2)

print("Zeitsynchronisation abgeschlossen! Dateien als 'audio1_sync.wav' und 'audio2_sync.wav' gespeichert.")
