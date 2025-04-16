import numpy as np
import soundfile as sf
import os
import padasip as pa

# Pfad und Dateinamen
dir_path = "E:/COHIRADIA/Archiviert/unvollst_MW_30_and_31_12_2006_analogue_VR/Optional_intermediate_files/2GBSplit"
audio_files = ["audio2_sync.wav", "audio1_sync.wav"]

# Chunk-Größe in Samples berechnen (10 MB pro Chunk)
chunk_size_bytes = 10 * 1024 * 1024  # 10 MB
sample_size_bytes = 4  # Float32 entspricht 4 Bytes

# Abtastrate ermitteln
with sf.SoundFile(os.path.join(dir_path, audio_files[0])) as f:
    sr = f.samplerate
    num_channels = f.channels
    chunk_size_samples = chunk_size_bytes // (sample_size_bytes * num_channels)

# Adaptive Filter initialisieren
filter_order = 256
lms = pa.filters.FilterLMS(n=filter_order, mu=0.003)

# Output-Dateien vorbereiten
e_out = sf.SoundFile(os.path.join(dir_path, "__LMS_sig__" + audio_files[1]), mode='w', samplerate=sr, channels=num_channels, format='WAV', subtype='PCM_32')
y_out = sf.SoundFile(os.path.join(dir_path, "__LMS_ref__" + audio_files[0]), mode='w', samplerate=sr, channels=num_channels, format='WAV', subtype='PCM_32')
samples_written = 0
# Chunkweise Verarbeitung
with sf.SoundFile(os.path.join(dir_path, audio_files[0])) as ref_file, sf.SoundFile(os.path.join(dir_path, audio_files[1])) as mix_file:
    while True:
        ref_chunk = ref_file.read(chunk_size_samples)
        mix_chunk = mix_file.read(chunk_size_samples)
        samples_written += len(ref_chunk)
        print(f"Bisher verarbeitet, Gesamtlänge: {samples_written/44100} Sekunden")

        if len(ref_chunk) == 0 or len(mix_chunk) == 0:
            break  # Ende der Datei erreicht

        # Sicherstellen, dass beide gleich lang sind
        min_len = min(len(ref_chunk), len(mix_chunk))
        ref_chunk, mix_chunk = ref_chunk[:min_len], mix_chunk[:min_len]

        # Eingabe für LMS-Filter vorbereiten
        X = pa.input_from_history(0.5 * ref_chunk, filter_order)
        d = 0.5 * mix_chunk[filter_order - 1:]

        if np.any(np.isnan(X)) or np.any(np.isinf(X)):
            print("Eingabedaten enthalten NaN oder Inf!")
            continue

        # LMS-Filter anwenden
        y, e, w = lms.run(d, X)

        # Ergebnisse speichern
        e_out.write(e)
        y_out.write(y)

e_out.close()
y_out.close()
 


# import numpy as np
# import soundfile as sf
# import os
# import padasip as pa

# filepath = "E:/COHIRADIA/Archiviert/unvollst_MW_30_and_31_12_2006_analogue_VR/Optional_intermediate_files/2GBSplit"
# audio_files = [
#                     "audio1_sync.wav",
#                     "audio2_sync.wav",
#                     ]

# mix, sr = sf.read(os.path.join(filepath, audio_files[1]))  # Signal mit Störgeräusch
# ref, sr = sf.read(os.path.join(filepath, audio_files[0]))  # Reines Störsignal

# # Sicherstellen, dass beide gleich lang sind
# min_len = min(len(mix), len(ref))
# mix, ref = mix[:min_len], ref[:min_len]

# # Adaptive Filter (LMS)
# filter_order = 64  # Länge des adaptiven Filters
# lms = pa.filters.FilterLMS(n=filter_order, mu=0.001)  # LMS-Filter mit Lernrate 0.01

# # Signal in kleine Abschnitte aufteilen
# X = pa.input_from_history(0.5*ref, filter_order)  # Erzeugt eine Matrix mit vergangenen Werten
# d = 0.5*mix [filter_order-1:]  # Zielsignal
# if np.any(np.isnan(X)) or np.any(np.isinf(X)):
#     print("Eingabedaten enthalten NaN oder Inf!")
# # LMS-Filter anwenden
# y, e, w = lms.run(d, X)

# # Ergebnis speichern
# sf.write(os.path.join(filepath, ("__LMS_sig__" + audio_files[1])), e, sr)
# sf.write(os.path.join(filepath, ("__LMS_ref__" + audio_files[0])), y, sr)