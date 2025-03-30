import os
import numpy as np
import subprocess

# Set parameters
sample_rate = 10_000_000  # 10 MS/s, anpassbar
buffer_size = 1024  # Anzahl der 16-Bit-Werte pro Block

# FIFO-Dateien erstellen
fifo_r = "fifo_r"
fifo_g = "fifo_g"

if not os.path.exists(fifo_r):
    os.mkfifo(fifo_r)
if not os.path.exists(fifo_g):
    os.mkfifo(fifo_g)

# Starte fl2k_rgb mit den FIFO-Dateien als Eingabe für R und G
fl2k_proc = subprocess.Popen(
    ["fl2k_rgb", "-d", "0", "-s", str(sample_rate),
     "-R8", "-R", fifo_r, "-G8", "-G", fifo_g, "-B8", "-B", "/dev/null"],
    stdin=subprocess.DEVNULL,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)

# Funktion zum Schreiben von Daten in die FIFOs
def write_to_pipes():
    try:
        with open(fifo_r, "wb") as fr, open(fifo_g, "wb") as fg:
            while True:
                # Erzeuge zufällige 16-Bit-Daten als Beispiel
                data = np.random.randint(0, 65536, buffer_size, dtype=np.uint16)

                # Zerlege die 16-Bit-Werte in High-Byte (R) und Low-Byte (G)
                r_data = (data >> 8).astype(np.uint8).tobytes()
                g_data = (data & 0xFF).astype(np.uint8).tobytes()

                # Schreibe die Daten in die FIFOs
                fr.write(r_data)
                fg.write(g_data)
                fr.flush()
                fg.flush()
    except BrokenPipeError:
        pass

# Starte die Datenübertragung
try:
    write_to_pipes()
finally:
    fl2k_proc.terminate()
    os.remove(fifo_r)
    os.remove(fifo_g)

# Änderungen & Verbesserungen:

#     Statt os.pipe() wird jetzt os.mkfifo() verwendet, da fl2k_rgb FIFO-Dateien benötigt.

#     Die roten und grünen Kanal-Daten werden direkt in die FIFO-Dateien geschrieben.

#     write_to_pipes() schreibt kontinuierlich Daten in die FIFOs.

#     fl2k_rgb liest die FIFO-Dateien, als wären es normale Binärdateien.

#     /dev/null dient als Dummy-Parameter für den blauen Kanal.

# Falls du Windows nutzt, musst du eine andere Methode finden, da Windows keine nativen FIFOs (mkfifo) unterstützt. In diesem Fall könnten Named Pipes (\\\\.\\pipe\\fifo_r) oder Threads mit subprocess.PIPE verwendet werden.