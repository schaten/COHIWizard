import subprocess
import psutil
import numpy as np
import os
import time
from pathlib import Path
import numpy as np
import scipy.signal as signal

"""read two wav-IQ files , weight the second one with a certain gain and then mix the two.
write the resulting IQ-File to output audio file PCM16
filelist 1: List of filenames of the master trace
filelist 2: List of filenames of the slave trace to be attenuated by gain dB
"""

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
deltagain = -15
gainmaster = -3
gainslave = deltagain + gainmaster
formatstring = "s16le"
sSR = 1250000
#filepath = "C:/Users/scharfetter_admin/Documents/MW_Aufzeichnungen/COHIRADIA/Softwareentwicklung/COHIRADIA_RFCorder/COHIRADIA_RFCorder"
filepath = "E:/COHIRADIA/Unbearbeitet_P1/Caroline_Ross_Revenge_2025_03_09/Barteczek"

# filelist1 = ["cohiwizard_20250309_200914Z_1125kHz.wav"]
# filelist2 = ["synth_caro_spur6_0.wav"]
#TODO: Filestart durch die sequenz '-skip_initial_bytes N', N = Byteoffset  genau trimmen
filelist1 = ["cohiwizard_20250309_193314Z_1125kHz.wav", "cohiwizard_20250309_194026Z_1125kHz.wav",
            "cohiwizard_20250309_194738Z_1125kHz.wav", "cohiwizard_20250309_195450Z_1125kHz.wav",
            "cohiwizard_20250309_200202Z_1125kHz.wav", "cohiwizard_20250309_200914Z_1125kHz.wav",
            "cohiwizard_20250309_201626Z_1125kHz.wav", "cohiwizard_20250309_202338Z_1125kHz.wav"]
filelist2 = ["synth_caro_spur1_0.wav","synth_caro_spur2_0.wav",
            "synth_caro_spur3_0.wav", "synth_caro_spur4_0.wav",
            "synth_caro_spur5_0.wav", "synth_caro_spur6_0.wav",
            "synth_caro_spur7_0.wav", "synth_caro_spur8_0.wav"]

for ix, input_filename in enumerate(filelist1):
    input_filename1 = filelist1[ix]
    input_filename2 = filelist2[ix]
    print(f"next master file: {input_filename1}, next slave file: {input_filename2}")
    output_filename = "remix_" + Path(input_filename).stem + ".wav"
    in_path1 = os.path.join(filepath, input_filename1)
    in_path2 = os.path.join(filepath, input_filename2)
    out_path = os.path.join(filepath, output_filename)
    datachunkstart1 = find_data_chunk(in_path1)
    datachunkstart2 = find_data_chunk(in_path2)
    ffmpeg_path = "C:/Users/scharfetter_admin/Documents/MW_Aufzeichnungen/COHIRADIA/Softwareentwicklung/COHIWizard_2023/sources/ffmpeg-master-latest-win64-gpl-shared/bin"
    ffmpeg_execmd = os.path.join(ffmpeg_path, "ffmpeg.exe")


    ffmpeg_cmd = [
        ffmpeg_execmd, "-y", "-f", formatstring, "-ar", str(sSR), "-ac", "2", 
        "-i", str(in_path1), "-i", str(in_path2),
        "-filter_complex",
        "[1:a]volume=volume=" + str(gainslave) + "dB[b1];"
        "[0:a]volume=volume=" + str(gainmaster) + "dB[b2];"
        #"[b1][b2]amix=inputs=2[y];"
        "[b1][b2]amix=inputs=2[out]",
        #"[y]pan=stereo|c0=c1|c1=c0[out]",  
        "-map", "[out]", "-c:a", "pcm_s16le", "-f", "wav", out_path
    ]
    #-f wav -acodec pcm_f32le 
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
    
    #psutil.Process(ffmpeg_process.pid).nice(psutil.IDLE_PRIORITY_CLASS)

    # while ffmpeg_process.poll() is None:
    #     print(f"Waiting for ffmpeg to finish, at file: {input_filename1}")
    #     time.sleep(1)   # Warte 1 Sekunde
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