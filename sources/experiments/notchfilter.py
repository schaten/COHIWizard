import subprocess
import psutil
import numpy as np
import os
import time
from pathlib import Path
import numpy as np
import scipy.signal as signal

"""read wav-IQ file and apply notch filter
filelist 1: List of filenames of the master trace
"""

import matplotlib.pyplot as plt


# Filterparameter
fs = 1250000  # Abtastfrequenz in Hz (z.B. 5 kHz)
fbm = 1125000  # Bandmittenfrequenz
fbm = 1100000  # Bandmittenfrequenz
fct = 1422250  # Mittenfrequenz des Notch-Filters in Hz
fc = abs(-fct + fbm)  # Mittenfrequenz des Notch-Filters in Hz
bw = 9000    # Bandbreite des Notch-Filters in Hz
N = 4     # Ordnung des Filters

# Berechne die obere und untere Grenzfrequenz des Notch-Filters
lowcut = fc - bw / 2
highcut = fc + bw / 2

# Normalisiere die Frequenzen (Nyquist-Grenze)
nyquist = 0.5 * fs
low = lowcut / nyquist
high = highcut / nyquist

# Erstelle das Butterworth Notch-Filter
b, a = signal.butter(N, [low, high], btype='bandstop')

# Pole und Nullstellen berechnen
z, p, k = signal.tf2zpk(b, a)

# Frequenzgang berechnen
w, h = signal.freqz(b, a, worN=8000)

# Plot der Pole und Nullstellen im komplexen Bereich
plt.figure(figsize=(6,6))
plt.scatter(np.real(z), np.imag(z), color='blue', label='Nullstellen')  # Nullstellen
plt.scatter(np.real(p), np.imag(p), color='red', label='Pole')  # Pole
plt.axhline(0, color='black',linewidth=0.5)
plt.axvline(0, color='black',linewidth=0.5)
plt.title('Pole-Zero Plot für einen Butterworth-Notch-Filter')
plt.xlabel('Realteil')
plt.ylabel('Imaginärteil')
plt.legend()
plt.grid()

# Frequenzgang plotten
plt.figure(figsize=(6, 4))
plt.subplot(2, 1, 1)
plt.plot(w / np.pi * (fs / 2), 20*np.log10(abs(h)), 'b')
plt.title('Frequenzgang des Filters')
plt.xlabel('Frequenz [Hz]')
plt.ylabel('Amplitude')
plt.grid()

plt.subplot(2, 1, 2)
plt.plot(w / np.pi * (fs / 2), np.angle(h), 'b')
plt.xlabel('Frequenz [Hz]')
plt.ylabel('Phase [radians]')
plt.grid()

plt.tight_layout()
plt.show()

# Ausgabe der Pole und Nullstellen
print("Nullstellen:", z)
print("Pole:", p)


# Ausgabe der Pole und Nullstellen
print("Nullstellen:", z)
print("Pole:", p)

def format_complex_number(c):
    """Formatiert eine komplexe Zahl so, dass ffmpeg sie korrekt versteht (z.B. 0.5+0.3i)."""
    if np.iscomplex(c):
        return f"{c.real:.8f}{'+' if c.imag >= 0 else '-'}{abs(c.imag):.8f}i"
    return f"{c.real:.8f}"

def generate_ffmpeg_command(b, a):
    # Berechnung von Nullstellen (z), Polen (p) und Verstärkungsfaktor (k)
    z, p, k = signal.tf2zpk(b, a)

    # for k,z_i in enumerate(z):
    #     if np.imag(z_i) <0:
    #         z[k] = 1
    # Entferne negative Imaginärteile

    # for k,p_i in enumerate(p):
    #     if np.imag(p_i) <0:
    #         p[k] = 0
    # Formatieren der Nullstellen und Pole mit `i` für den Imaginärteil
    zeros_str = " ".join(format_complex_number(z_i) for z_i in z)
    poles_str = " ".join(format_complex_number(p_i) for p_i in p)
    gain_str = f"{k:.8f}"  # Verstärkungsfaktor
    
    # Erstellen des `aiir`-Filterstrings für Zero-Pole-Darstellung
    filter_command = f"aiir=k={gain_str}:z={zeros_str}:p={poles_str}:f=zp:r=s"

    return filter_command

def find_data_chunk(wav_file):
    with open(wav_file, "rb") as f:
        data = f.read()
        pos = data.find(b"data")  # Suche nach "data" im Header
        if pos != -1:
            print(f'"data"-Chunk gefunden an Byte-Position: {pos}')
        else:
            print('"data"-Chunk nicht gefunden.')
    return pos

#TODO: replace by argparse
#TODO: Filestart durch die sequenz '-skip_initial_bytes N', N = Byteoffset  genau trimmen
formatstring = "s16le"
sSR = fs
filepath = "C:/Users/scharfetter_admin/Documents/MW_Aufzeichnungen/COHIRADIA/Softwareentwicklung/COHIRADIA_RFCorder/COHIRADIA_RFCorder"
#filepath = "E:/COHIRADIA/Unbearbeitet_P1/Caroline_Ross_Revenge_2025_03_09/Barteczek"
filepath = "E:/COHIRADIA/Archiviert/unvollst_MW_30_and_31_12_2006_analogue_VR/Optional_intermediate_files/2GBSplit"
# fc = 100000
# bw = 10000
filelist1 = ["SDRuno_20220910_095058Z_1125kHz.wav"]
filelist1 = ["B2006_20210801_184741_1100kHz_10_20061230_235828_1100kHz.wav"]
# filelist2 = ["synth_caro_spur6_0.wav"]
#TODO: Filestart durch die sequenz '-skip_initial_bytes N', N = Byteoffset  genau trimmen
# filelist1 = ["cohiwizard_20250309_193314Z_1125kHz.wav", "cohiwizard_20250309_194026Z_1125kHz.wav",
#             "cohiwizard_20250309_194738Z_1125kHz.wav", "cohiwizard_20250309_195450Z_1125kHz.wav",
#             "cohiwizard_20250309_200202Z_1125kHz.wav", "cohiwizard_20250309_200914Z_1125kHz.wav",
#             "cohiwizard_20250309_201626Z_1125kHz.wav", "cohiwizard_20250309_202338Z_1125kHz.wav"]

for ix, input_filename in enumerate(filelist1):
    input_filename1 = filelist1[ix]
    print(f"next master file: {input_filename1}")
    output_filename = "notch_" + str(fc) + Path(input_filename).stem + ".wav"
    in_path1 = os.path.join(filepath, input_filename1)
    out_path = os.path.join(filepath, output_filename)
    datachunkstart1 = find_data_chunk(in_path1)
    ffmpeg_path = "C:/Users/scharfetter_admin/Documents/MW_Aufzeichnungen/COHIRADIA/Softwareentwicklung/COHIWizard_2023/sources/ffmpeg-master-latest-win64-gpl-shared/bin"
    ffmpeg_execmd = os.path.join(ffmpeg_path, "ffmpeg.exe")

    filter_command = generate_ffmpeg_command(b, a)
    
    # ffmpeg-Kommando für die Anwendung des Filters
    ffmpeg_cmd = [
        ffmpeg_execmd, "-y", "-f", formatstring, "-ar", str(sSR), "-ac", "2",
        "-i", in_path1,      # Eingabedatei
        "-filter_complex", filter_command,  # Filter
        #output_audio            # Ausgabedatei
        "-c:a", "pcm_s16le", "-f", "wav", out_path
    ]
    # ffmpeg_cmd = [
    #     ffmpeg_execmd, "-y", "-f", formatstring, "-ar", str(sSR), "-ac", "2",
    #     "-i", in_path1, "-af", filter_str,  # "-af" statt "-filter_complex"
    #     "-c:a", "pcm_s16le", "-f", "wav", out_path
    # ]
    #ffmpeg -i input.wav -filter_complex "[0:a]afftfilt=real='notch(f, fc)':imag='notch(f, fc)'[out]" -map "[out]" output.wav
    print("Generierter FFmpeg-Befehl:")
    print(" ".join(ffmpeg_cmd))  # Zum Debuggen

    try:
        # Prozess starten
        ffmpeg_process = subprocess.Popen(ffmpeg_cmd, 
            stdout=None, 
            stderr=None,
            text=True
        )

    except FileNotFoundError:
        print(f"Input file not found")
    except subprocess.SubprocessError as e:
        print(f"Error when executing ffmpeg_file: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
    
    print(f"Waiting for ffmpeg to finish, at file: {input_filename1}")

    #ffmpeg_process.wait()  # Wartet auf das Ende
    try:
        stdout, stderr = ffmpeg_process.communicate()  # Timeout nach 60 Sekunden
    except subprocess.TimeoutExpired:
        ffmpeg_process.kill()
        stdout, stderr = ffmpeg_process.communicate()
        print(f"ffmpeg wurde wegen Timeout beendet für: {input_filename1}")

    with open(out_path, "rb") as f_in:
        data = f_in.read()


#TODO: automatische erkennung, welcheb byte offset man braucht (CCPT):

# Beispielaufruf in_path1
# find_data_chunk("example.wav")

    # Die ersten 2 Byte entfernen und den Rest schreiben
    with open(out_path, "wb") as f_out:
        f_out.write(data[2:])

    # 🔹 **Nachträglich die ersten 216 Bytes von input1.wav in output.wav kopieren**
    try:
        with open(in_path1, "rb") as infile, open(out_path, "r+b") as outfile:
            header = infile.read(216)  # Erste 216 Bytes lesen
            outfile.seek(0)            # Zum Anfang der Datei springen
            outfile.write(header)      # Header überschreiben

        print(f"Header erfolgreich kopiert für: {output_filename}")

    except Exception as e:
        print(f"Fehler beim Kopieren des Headers: {e}")