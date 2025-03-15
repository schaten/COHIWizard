import os
import numpy as np
import subprocess

# Set parameters
sample_rate = 100e6  # Beispiel-Samplerate für den fl2k
buffer_size = 1024   # Anzahl der 16-Bit-Werte pro Block

# Erstelle zwei Pipes
r_read, r_write = os.pipe()
g_read, g_write = os.pipe()

# Starte fl2k_rgb mit den Pipes als Eingabe für R und G
fl2k_proc = subprocess.Popen(
    ["fl2k_rgb", "-d", "0", "-r", str(int(sample_rate)), "-i", "fifo_r", "fifo_g", "/dev/null"],
    stdin=subprocess.DEVNULL,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)

# Funktion zum Schreiben von Daten in die Pipes
def write_to_pipes():
    try:
        while True:
            # Erzeuge zufällige 16-Bit-Daten als Beispiel
            data = np.random.randint(0, 65536, buffer_size, dtype=np.uint16)

            # Zerlege die 16-Bit-Werte in High-Byte (R) und Low-Byte (G)
            r_data = (data >> 8).astype(np.uint8).tobytes()
            g_data = (data & 0xFF).astype(np.uint8).tobytes()

            # Schreibe die Daten in die Pipes
            os.write(r_write, r_data)
            os.write(g_write, g_data)
    except BrokenPipeError:
        pass
    finally:
        os.close(r_write)
        os.close(g_write)

# Starte die Datenübertragung
try:
    write_to_pipes()
finally:
    fl2k_proc.terminate()
    os.close(r_read)
    os.close(g_read)


# Chat GPT Erklärung:

#     Das Skript erstellt zwei Pipes mit os.pipe() für die zwei Datenströme.
#     fl2k_rgb wird mit den Pipes als Eingabe für die R- und G-Kanäle gestartet.
#     Eine Schleife generiert kontinuierlich zufällige 16-Bit-Daten, zerlegt sie in zwei 8-Bit-Datenströme (High-Byte für R, Low-Byte für G) und schreibt sie in die Pipes.
#     Falls fl2k_rgb beendet wird, fängt das Skript BrokenPipeError ab und schließt die Pipes.

# Falls fl2k_rgb mit echten Pipes (fifo_r, fifo_g) statt os.pipe() arbeitet, müsstest du mkfifo verwenden.