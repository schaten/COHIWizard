import numpy as np
import matplotlib.pyplot as plt

def generate_multisine(frequencies, amplitudes, sampling_rate, duration, optimize_phases=True):
    """
    Generiert ein Multisinus-Signal mit optionaler Optimierung der Anfangsphasen (Schröder-Phasen).
    
    Parameters:
    - frequencies: Liste der Frequenzkomponenten (Hz)
    - amplitudes: Liste der Amplituden (gleiche Länge wie frequencies)
    - sampling_rate: Abtastrate (Hz)
    - duration: Dauer des Signals (Sekunden)
    - optimize_phases: Bool, ob Schröder-Phasen genutzt werden sollen
    
    Returns:
    - t: Zeitvektor
    - signal: Multisinus-Signal
    """
    N = len(frequencies)  # Anzahl der Frequenzkomponenten
    t = np.linspace(0, duration, int(sampling_rate * duration), endpoint=False)
    
    # Berechne die Phasen
    if optimize_phases:
        phases = np.array([-np.pi * k * (k - 1) / N for k in range(1, N + 1)])
    else:
        phases = np.zeros(N)  # Default: alle Phasen = 0
    
    # Generiere das Signal
    signal = np.zeros_like(t)
    for i, (f, A, phi) in enumerate(zip(frequencies, amplitudes, phases)):
        signal += A * np.sin(2 * np.pi * f * t + phi)
    
    return t, signal

# Beispielparameter
frequencies = [100, 200, 300, 400]  # Frequenzen in Hz
amplitudes = [1, 1, 1, 1]  # Gleiche Amplitude für alle Komponenten
sampling_rate = 10000  # Abtastrate in Hz
duration = 0.1  # Dauer in Sekunden

# Multisinus ohne Phasenoptimierung
t, signal_no_opt = generate_multisine(frequencies, amplitudes, sampling_rate, duration, optimize_phases=False)

# Multisinus mit Schröder-Phasen
_, signal_opt = generate_multisine(frequencies, amplitudes, sampling_rate, duration, optimize_phases=True)

# Berechne Crest-Faktor
def crest_factor(signal):
    peak = np.max(np.abs(signal))
    rms = np.sqrt(np.mean(signal**2))
    return peak / rms

print("Crest-Faktor ohne Optimierung:", crest_factor(signal_no_opt))
print("Crest-Faktor mit Optimierung:", crest_factor(signal_opt))

# Plot der Signale
plt.figure(figsize=(10, 6))
plt.subplot(2, 1, 1)
plt.plot(t, signal_no_opt, label="Ohne Optimierung")
plt.title("Multisinus ohne Phasenoptimierung")
plt.xlabel("Zeit (s)")
plt.ylabel("Amplitude")

plt.subplot(2, 1, 2)
plt.plot(t, signal_opt, label="Mit Schröder-Phasen", color='orange')
plt.title("Multisinus mit Schröder-Phasen")
plt.xlabel("Zeit (s)")
plt.ylabel("Amplitude")

plt.tight_layout()
plt.show()
