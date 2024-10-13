import numpy as np
import soundfile as sf
from scipy.signal import sosfilt, butter, resample

def resample_audio(audio_data, original_rate, target_rate):
    """Resample audio data to the target sample rate."""
    num_samples = int(len(audio_data) * target_rate / original_rate)
    return resample(audio_data, num_samples)

def convert_to_mono(audio_data, num_channels):
    """Convert multi-channel audio to mono by averaging channels."""
    if num_channels > 1:
        return np.mean(audio_data, axis=1)
    return audio_data

def process_block(audio_block, sos, zi):
    """Apply the low-pass filter blockwise and maintain filter state (zi)."""
    filtered_block, zi = sosfilt(sos, audio_block, zi=zi)
    return filtered_block, zi

def modulate_signal(filtered_signal, carrier_freq, sample_rate, sample_offset, modulation_depth):
    """Modulate the filtered signal onto a carrier frequency with adjustable modulation depth."""
    # Zeitvektor basierend auf dem sample_offset
    t = np.arange(sample_offset, sample_offset + len(filtered_signal)) / sample_rate
    carrier = np.cos(2 * np.pi * carrier_freq * t)
    
    # Modulation: Signal amplitude-modulates the carrier with the given depth
    modulated_signal = (1 + modulation_depth * filtered_signal) * carrier
    return modulated_signal

def read_and_process_audio_blockwise(file_list, carrier_freq, target_sample_rate, block_size, cutoff_freq, modulation_depth, zi, sample_offset, current_file_index, file_handles):
    """
    Read and process audio blockwise from the current file in the file_list, keeping the file handle open.
    Process only one block and move to the next file when the current one is finished.
    
    Args:
    - file_list: List of audio file paths for the current carrier.
    - carrier_freq: Carrier frequency for modulation.
    - target_sample_rate: Target sample rate for processing.
    - block_size: Size of the audio block to be processed.
    - cutoff_freq: Cutoff frequency for the low-pass filter.
    - modulation_depth: Depth of modulation.
    - zi: Filter state to maintain continuity across blocks.
    - sample_offset: Current sample offset for phase continuity in modulation.
    - current_file_index: Index of the current file in the file_list.
    - file_handles: Dictionary of file handles to keep files open.

    Returns:
    - modulated_output: Modulated block of audio.
    - zi: Updated filter state.
    - sample_offset: Updated sample offset.
    - current_file_index: Updated file index (incremented if necessary).
    """
    sos = butter(4, cutoff_freq, btype='low', fs=target_sample_rate, output='sos')

    while current_file_index < len(file_list):
        file_path = file_list[current_file_index]

        # Überprüfen, ob das File bereits offen ist, falls nicht, öffne es und speichere den Handle
        if current_file_index not in file_handles:
            file_handles[current_file_index] = sf.SoundFile(file_path, 'r')

        f = file_handles[current_file_index]
        original_sample_rate = f.samplerate
        num_channels = f.channels

        # Blockweises Lesen
        audio_block = f.read(block_size)
        if len(audio_block) == 0:
            # Datei ist fertig, zum nächsten File wechseln und Datei schließen
            f.close()
            del file_handles[current_file_index]  # Handle entfernen
            current_file_index += 1
            continue  # Weiter zur nächsten Datei

        # Mono-Konvertierung falls notwendig
        audio_block = convert_to_mono(audio_block, num_channels)

        # Resampling falls notwendig
        if original_sample_rate != target_sample_rate:
            audio_block = resample_audio(audio_block, original_sample_rate, target_sample_rate)

        # Low-Pass-Filter anwenden
        filtered_block, zi = process_block(audio_block, sos, zi)

        # Modulation auf den Träger anwenden
        modulated_block = modulate_signal(filtered_block, carrier_freq, target_sample_rate, sample_offset, modulation_depth)

        # Aktualisierung von sample_offset für den nächsten Block
        sample_offset += len(modulated_block)

        return modulated_block, zi, sample_offset, current_file_index

    # Alle Dateien wurden verarbeitet, kehre None zurück
    return None, zi, sample_offset, current_file_index

def process_multiple_carriers_blockwise(carrier_frequencies, playlists, sample_rate, block_size, cutoff_freq, modulation_depth, output_base_name):
    """
    Process audio from multiple playlists blockwise, each corresponding to a different carrier frequency.
    Write the combined output to multiple WAV files if the 2 GB limit is exceeded.
    """
    # Set the 2GB limit and calculate the maximum samples per file (for 16-bit PCM WAV files)
    max_file_size = 2 * 1024**3  # 2 GB in bytes
    max_samples_per_file = max_file_size // 2  # 16-bit PCM = 2 bytes per sample

    # Initialize filter states for each carrier
    #zis = [np.zeros((4, 2)) for _ in carrier_frequencies]  # Filter state buffer for each carrier (4th order filter)
    zis = [np.zeros((2, 2)) for _ in carrier_frequencies]  # Filter state buffer for each carrier (4th order filter)
    
    # Initialisiere sample_offset und current_file_index für jeden Carrier
    sample_offsets = [0] * len(carrier_frequencies)
    current_file_indices = [0] * len(carrier_frequencies)  # Track current file index for each carrier
    
    # **Initialisiere file_handles als Liste von Dictionaries für jeden Carrier**
    file_handles = [{} for _ in carrier_frequencies]  # Für jeden Carrier ein eigenes Dictionary von Datei-Handles

    total_samples_written = 0
    file_index = 0

    # Open first output file to write combined signal blockwise
    output_file_name = f"{output_base_name}_{file_index}.wav"
    out_file = sf.SoundFile(output_file_name, 'w', samplerate=sample_rate, channels=1, subtype='PCM_16')

    done = False
    
    while not done:
        combined_signal_block = None  # Buffer for combined signal block
        done = True  # Assume done unless we find more data
        
        # Process each carrier for the current block
        for i, (carrier_freq, zi) in enumerate(zip(carrier_frequencies, zis)):
            modulated_block, new_zi, sample_offsets[i], current_file_indices[i] = read_and_process_audio_blockwise(
                playlists[i], carrier_freq, sample_rate, block_size, cutoff_freq, modulation_depth, zi, sample_offsets[i], current_file_indices[i], file_handles[i])
            
            # Wenn modulated_block None ist, dann ist das Playlist-Ende erreicht
            if modulated_block is None:
                continue

            # Dynamically adjust combined signal block size based on modulated block size
            if combined_signal_block is None or len(combined_signal_block) < len(modulated_block):
                combined_signal_block = np.zeros(len(modulated_block))

            combined_signal_block[:len(modulated_block)] += modulated_block
            
            # If we processed any blocks, we're not done
            done = False

            # Update filter state for this carrier
            zis[i] = new_zi
        
        # If all files are done, break the loop
        if done:
            break

        # Write the combined block to the current output file
        samples_to_write = len(combined_signal_block)
        
        if samples_to_write + total_samples_written > max_samples_per_file:
            # If the file exceeds 2GB, close the current file and start a new one
            out_file.close()
            file_index += 1
            output_file_name = f"{output_base_name}_{file_index}.wav"
            out_file = sf.SoundFile(output_file_name, 'w', samplerate=sample_rate, channels=1, subtype='PCM_16')
            total_samples_written = 0  # Reset the sample counter for the new file

        out_file.write(combined_signal_block)
        total_samples_written += samples_to_write

    # Close the final output file
    out_file.close()

    # **Am Ende sicherstellen, dass alle Datei-Handles geschlossen werden**
    for file_handle_dict in file_handles:
        for handle in file_handle_dict.values():
            handle.close()


# def process_multiple_carriers_blockwise(carrier_frequencies, playlists, sample_rate, block_size, cutoff_freq, modulation_depth, output_base_name):
#     """
#     Process audio from multiple playlists blockwise, each corresponding to a different carrier frequency.
#     Write the combined output to multiple WAV files if the 2 GB limit is exceeded.
#     """
#     # Set the 2GB limit and calculate the maximum samples per file (for 16-bit PCM WAV files)
#     max_file_size = 2 * 1024**3  # 2 GB in bytes
#     max_samples_per_file = max_file_size // 2  # 16-bit PCM = 2 bytes per sample

#     # Initialize filter states for each carrier
#     zis = [np.zeros((4, 2)) for _ in carrier_frequencies]  # Filter state buffer for each carrier (4th order filter)
    
#     # Initialisiere sample_offset für jeden Carrier mit 0
#     sample_offsets = [0] * len(carrier_frequencies)
    
#     total_samples_written = 0
#     file_index = 0
#     current_file_index = [0] * len(carrier_frequencies)  # Track current file index for each carrier

#     # Open first output file to write combined signal blockwise
#     output_file_name = f"{output_base_name}_{file_index}.wav"
#     out_file = sf.SoundFile(output_file_name, 'w', samplerate=sample_rate, channels=1, subtype='PCM_16')

#     done = False
    
#     while not done:
#         combined_signal_block = None  # Buffer for combined signal block
#         done = True  # Assume done unless we find more data
        
#         # Process each carrier for the current block
#         for i, (carrier_freq, zi) in enumerate(zip(carrier_frequencies, zis)):
#             modulated_block, new_zi, sample_offsets[i], current_file_index[i] = read_and_process_audio_blockwise(
#                 playlists, carrier_freq, sample_rate, block_size, cutoff_freq, modulation_depth, zi, sample_offsets[i], current_file_index[i])
            
#             # Dynamically adjust combined signal block size based on modulated block size
#             if modulated_block is not None:
#                 if combined_signal_block is None or len(combined_signal_block) < len(modulated_block):
#                     combined_signal_block = np.zeros(len(modulated_block))

#                 combined_signal_block[:len(modulated_block)] += modulated_block
#                 zis[i] = new_zi
#                 done = False  # As long as at least one file has data to process

#         # If all files are done, break the loop
#         if done:
#             break

#         # Write the combined block to the current output file
#         samples_to_write = len(combined_signal_block)
        
#         if samples_to_write + total_samples_written > max_samples_per_file:
#             # If the file exceeds 2GB, close the current file and start a new one
#             out_file.close()
#             file_index += 1
#             output_file_name = f"{output_base_name}_{file_index}.wav"
#             out_file = sf.SoundFile(output_file_name, 'w', samplerate=sample_rate, channels=1, subtype='PCM_16')
#             total_samples_written = 0  # Reset the sample counter for the new file

#         out_file.write(combined_signal_block)
#         total_samples_written += samples_to_write

#     # Close the final output file
#     out_file.close()

# Beispielhafte Anwendung
sample_rate = 44100  # Gemeinsame Abtastrate für alle Audiodateien und Träger
block_size = 2**16   # Maximalblocklänge für die Verarbeitung
cutoff_freq = 4000   # Tiefpass-Grenzfrequenz
modulation_depth = 0.5  # Modulationstiefe
output_base_name = 'combined_output'

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

# Verarbeitung und Blockweises Schreiben

#Codeschnipsel um die genaue Headerlänge eines wav-Files vorab zu bestimmen:
def find_wav_header_size(file_path):
    # Öffne die Datei im Binärmodus
    with open(file_path, 'rb') as f:
        content = f.read()

    # Suche nach der ersten Vorkommen des 'data' Strings
    data_index = content.find(b'data')

    if data_index != -1:
        # Der "data" Chunk beginnt, also endet hier der Header
        header_size = data_index + 8  # 4 Bytes für "data" + 4 Bytes für die Datenlänge
        return header_size
    else:
        # Kein 'data'-Chunk gefunden, Datei könnte fehlerhaft sein
        raise ValueError("Kein 'data' Chunk im WAV-File gefunden.")

# Beispielaufruf
file_path = 'your_audio_file.wav'
header_size = find_wav_header_size(file_path)
print(f'Die Headergröße beträgt: {header_size} Bytes')
