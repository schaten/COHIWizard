import numpy as np
import scipy.io.wavfile as wav
from sklearn.decomposition import FastICA, PCA
import soundfile as sf
import os

import numpy as np
import scipy.io.wavfile as wav
from sklearn.decomposition import FastICA
import soundfile as sf

# Funktion zur Normierung der Signale
def normalize_audio(signal):
    return signal / np.max(np.abs(signal))


NO_ICA = True # no ICA, just LMS/RLS

filepath = "C:/Users/scharfetter_admin/Eigene Musik/Mixes_for_experiments"
filepath = "E:/COHIRADIA/Archiviert/unvollst_MW_30_and_31_12_2006_analogue_VR/Optional_intermediate_files/2GBSplit"
# Lade mehrere Audiodateien
audio_files = ["mix_1.wav", "mix_2.wav","mix_3.wav"]
audio_files = ["B2006_20210801_184741_1100kHz_10_20061230_235828_1100kHz_demod1423_hpf.wav",
                "B2006_20210801_184741_1100kHz_10_20061230_235828_1100kHz_demod901_hpf.wav",
                "B2006_20210801_184741_1100kHz_10_20061230_235828_1100kHz_demod550_hpf.wav",
                "B2006_20210801_184741_1100kHz_10_20061230_235828_1100kHz_demod1263_hpf.wav"]
audio_files = [
                "01-filtered_B2006_20210801_184741_1100kHz_10_20061230_235828_1100kHz_demod1423.wav",
                "02-filtered_B2006_20210801_184741_1100kHz_10_20061230_235828_1100kHz_demod901.wav",
                ]

audio_files = [
                "01-filtered_B2006_20210801_184741_1100kHz_10_20061230_235828_1100kHz_demod1423.wav",
                "02-filtered_B2006_20210801_184741_1100kHz_10_20061230_235828_1100kHz_demod901.wav",
                ]
audio_files = [
                "02-filtered_B2006_20210801_184741_1100kHz_10_20061230_235828_1100kHz_demod1423.wav",
                "06-filtered_B2006_20210801_184741_1100kHz_10_20061230_235828_1100kHz_demod550.wav",
                ]
audio_files = [
                "audio1_sync.wav",
                "audio2_sync.wav",
                ]
audio_data = []
sampling_rates = []

if not NO_ICA:
    for file in audio_files:
        rate, data = wav.read(os.path.join(filepath, file))
        if len(data.shape) > 1:
            data = np.mean(data, axis=1)  # Stereo zu Mono
        audio_data.append(data)
        sampling_rates.append(rate)

    # Prüfe auf gleiche Sampling-Rate
    if len(set(sampling_rates)) > 1:
        raise ValueError("Sampling-Raten stimmen nicht überein!")

    # Kürze auf gleiche Länge
    min_length = min(map(len, audio_data))
    audio_data = [data[:min_length] for data in audio_data]

    # Erstelle die Mix-Matrix X
    X = np.column_stack(audio_data).astype(np.float64)

    # Führe ICA durch
    n_sources = len(audio_files)

    pca = PCA(n_components=n_sources)  # Reduziert Dimensionen
    X_pca = pca.fit_transform(X)       # Transformiere das Signal
    ica = FastICA(n_components=n_sources, max_iter=1000, tol=1e-6, whiten="arbitrary-variance", fun='exp')
    #S_ = ica.fit_transform(X)
    S_ = ica.fit_transform(X_pca)      # ICA darauf anwenden
    print("PCA Varianzen:", pca.explained_variance_ratio_)
    # Speichere die separierten Quellen mit Normierung
    for i, source in enumerate(S_.T):
    #for i, source in enumerate(X_PCA.T):
        source_norm = normalize_audio(source)  # Wichtige Normierung!
        outpath = os.path.join(filepath, f"source_{i+1}.wav")
        sf.write(outpath, source_norm.astype(np.float32), sampling_rates[0])

    print("Separation abgeschlossen! Dateien als 'source_1.wav', 'source_2.wav', ... gespeichert.")

else:
    import padasip as pa

    print("LMS/RLS-Filterung...")
    # Audio-Dateien laden (Mischung + Referenz)
    audio_files = [
                    "02-filtered_B2006_20210801_184741_1100kHz_10_20061230_235828_1100kHz_demod1423.wav",
                    "01-filtered_B2006_20210801_184741_1100kHz_10_20061230_235828_1100kHz_demod901.wav",
                    ]
    audio_files = [
                    "02-filtered_B2006_20210801_184741_1100kHz_10_20061230_235828_1100kHz_demod1423.wav",
                    "01-filtered_B2006_20210801_184741_1100kHz_10_20061230_235828_1100kHz_demod901.wav",
                    ]
    # audio_files = ["B2006_20210801_184741_1100kHz_10_20061230_235828_1100kHz_demod1423.wav",
    #                "B2006_20210801_184741_1100kHz_10_20061230_235828_1100kHz_demod901.wav"             
    #                 ]
    audio_files = [
                    "05-filtered_B2006_20210801_184741_1100kHz_10_20061230_235828_1100kHz_demod883.wav",
                    "RAI__LMS1_sig__01-filtered_B2006_20210801_184741_1100kHz_10_20061230_235828_1100kHz_demod901.wav",
                    ]
    audio_files = [
                    "audio1_sync.wav",
                    "audio2_sync.wav",
                    ]
    # audio_files = [
    #                 "02-filtered_B2006_20210801_184741_1100kHz_10_20061230_235828_1100kHz_demod1423.wav",
    #                 "06-filtered_B2006_20210801_184741_1100kHz_10_20061230_235828_1100kHz_demod550.wav",
    #                 ]
    mix, sr = sf.read(os.path.join(filepath, audio_files[1]))  # Signal mit Störgeräusch
    ref, sr = sf.read(os.path.join(filepath, audio_files[0]))  # Reines Störsignal

    # Sicherstellen, dass beide gleich lang sind
    min_len = min(len(mix), len(ref))
    mix, ref = mix[:min_len], ref[:min_len]

    # Adaptive Filter (LMS)
    filter_order = 64  # Länge des adaptiven Filters
    lms = pa.filters.FilterLMS(n=filter_order, mu=0.001)  # LMS-Filter mit Lernrate 0.01
    #rls = pa.filters.FilterRLS(n=filter_order, mu=0.0000001, w="random")
    # Signal in kleine Abschnitte aufteilen
    X = pa.input_from_history(0.5*ref, filter_order)  # Erzeugt eine Matrix mit vergangenen Werten
    d = 0.5*mix [filter_order-1:]  # Zielsignal
    if np.any(np.isnan(X)) or np.any(np.isinf(X)):
        print("Eingabedaten enthalten NaN oder Inf!")
    # LMS-Filter anwenden
    y, e, w = lms.run(d, X)
    #y, e, w = rls.run(d, X)

    # Ergebnis speichern
    sf.write(os.path.join(filepath, ("__LMS_sig__" + audio_files[1])), e, sr)
    sf.write(os.path.join(filepath, ("__LMS_ref__" + audio_files[0])), y, sr)

