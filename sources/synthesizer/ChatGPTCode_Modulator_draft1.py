import numpy as np
from scipy.signal import sosfilt, butter, resample

import numpy as np
import soundfile as sf
from scipy.signal import sosfilt, butter

def process_block(audio_block, sos, zi):
    """Apply the low-pass filter blockwise and maintain filter state (zi)."""
    filtered_block, zi = sosfilt(sos, audio_block, zi=zi)
    return filtered_block, zi

def modulate_signal(filtered_signal, carrier_freq, sample_rate, block_start, block_size, modulation_depth):
    """Modulate the filtered signal onto a carrier frequency with adjustable modulation depth."""
    t = np.arange(block_start, block_start + block_size) / sample_rate
    carrier = np.cos(2 * np.pi * carrier_freq * t)
    
    # Modulation: Signal amplitude-modulates the carrier with the given depth
    modulated_signal = (1 + modulation_depth * filtered_signal) * carrier
    return modulated_signal

def read_and_process_audio(file_list, carrier_freq, sample_rate, block_size, cutoff_freq, modulation_depth):
    """
    Read and process audio blockwise from a list of files.
    Apply low-pass filtering and modulate onto a carrier frequency.
    """
    sos = butter(4, cutoff_freq, btype='low', fs=sample_rate, output='sos')
    zi = np.zeros((sos.shape[0], 2))  # Initial filter states
    modulated_output = []

    for file in file_list:
        with sf.SoundFile(file, 'r') as f:
            # Ensure the file is in the target sample rate and mono
            if f.samplerate != sample_rate:
                raise ValueError(f"File {file} has different sample rate. Expected {sample_rate}, got {f.samplerate}.")
            if f.channels > 1:
                raise ValueError(f"File {file} is not mono. Convert to mono before processing.")
            
            block_start = 0
            while True:
                # Read the file blockwise
                audio_block = f.read(block_size)
                if len(audio_block) == 0:
                    break  # End of file
                
                # Apply low-pass filtering
                filtered_block, zi = process_block(audio_block, sos, zi)
                
                # Modulate onto the carrier
                modulated_block = modulate_signal(filtered_block, carrier_freq, sample_rate, block_start, len(audio_block), modulation_depth)
                modulated_output.append(modulated_block)
                
                block_start += len(audio_block)

    return np.concatenate(modulated_output)

def process_multiple_carriers(carrier_frequencies, playlists, sample_rate, block_size, cutoff_freq, modulation_depth):
    """
    Process audio from multiple playlists, each corresponding to a different carrier frequency.
    """
    modulated_signals = []
    for carrier_freq, playlist in zip(carrier_frequencies, playlists):
        print(f"Processing carrier at {carrier_freq} Hz")
        modulated_signal = read_and_process_audio(playlist, carrier_freq, sample_rate, block_size, cutoff_freq, modulation_depth)
        modulated_signals.append(modulated_signal)
    
    return modulated_signals

# Beispielhafte Anwendung
sample_rate = 44100  # Gemeinsame Abtastrate für alle Audiodateien und Träger
block_size = 1024    # Blockgröße für die Verarbeitung
cutoff_freq = 4000   # Tiefpass-Grenzfrequenz
modulation_depth = 0.5  # Modulationstiefe

# Trägerfrequenzen für 5 Kanäle
carrier_frequencies = [10000, 15000, 20000, 25000, 30000]  # 10 kHz, 15 kHz, etc.

# Beispielhafte Playlists (Liste von WAV-Dateipfaden)
playlists = [
    ['playlist1_file1.wav', 'playlist1_file2.wav'],
    ['playlist2_file1.wav', 'playlist2_file2.wav'],
    ['playlist3_file1.wav', 'playlist3_file2.wav'],
    ['playlist4_file1.wav', 'playlist4_file2.wav'],
    ['playlist5_file1.wav', 'playlist5_file2.wav'],
]

# Verarbeitung aller Carrier
modulated_signals = process_multiple_carriers(carrier_frequencies, playlists, sample_rate, block_size, cutoff_freq, modulation_depth)

# Das Ergebnis ist eine Liste der modulierten Signale für jeden Carrier



############################# Verbesserte Version mit automatischem Resampling #######################
# 
# 
 