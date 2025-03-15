import numpy as np
import subprocess
import threading
import queue
import struct

class StreamProcessor:
    def __init__(self, fileHandle, sourcefile2, data_sock, DATABLOCKSIZE, SAMPLERATE):
        self.fileHandle = fileHandle
        self.sourcefile2 = sourcefile2
        self.data_sock = data_sock
        self.DATABLOCKSIZE = DATABLOCKSIZE
        self.SAMPLERATE = SAMPLERATE
        
        self.audio_queue = queue.Queue()
        self.stop_flag = threading.Event()
        
        # Starte den FFmpeg-Prozess und den Lese-Thread
        self.start_ffmpeg()
        self.start_audio_reader()

    def start_ffmpeg(self):
        """Startet FFmpeg als Subprozess und leitet die Audiodaten in einen Puffer (Queue)."""
        ffmpeg_cmd = [
            "ffmpeg", "-loglevel", "error", "-y",
            "-ac", "2", "-i", self.sourcefile2,
            "-ar", str(self.SAMPLERATE), "-ac", "1",  # Resampling & Mono
            "-map", "0:a", "-c:a", "pcm_f32le",  # Float32 Ausgabe
            "-f", "wav", "pipe:1"
        ]

        self.ffmpeg_proc = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=4096)

    def start_audio_reader(self):
        """Liest die von FFmpeg generierten Audiodaten und speichert sie in eine Queue."""
        def read_audio():
            while not self.stop_flag.is_set():
                raw_data = self.ffmpeg_proc.stdout.read(self.DATABLOCKSIZE * 4)  # 4 Bytes pro Float32-Wert
                if not raw_data:
                    break  # EOF erreicht

                # Konvertiere Binärdaten in ein NumPy-Array
                audio_data = np.frombuffer(raw_data, dtype=np.float32)
                
                # Falls weniger als DATABLOCKSIZE Werte vorliegen, auffüllen mit Nullen
                if len(audio_data) < self.DATABLOCKSIZE:
                    audio_data = np.pad(audio_data, (0, self.DATABLOCKSIZE - len(audio_data)), mode="constant")

                self.audio_queue.put(audio_data)

            # Nach EOF: Fülle die Queue mit Nullarrays, damit der Hauptthread weiterarbeiten kann
            while not self.stop_flag.is_set():
                self.audio_queue.put(np.zeros(self.DATABLOCKSIZE, dtype=np.float32))

        self.audio_thread = threading.Thread(target=read_audio, daemon=True)
        self.audio_thread.start()

    def send_data(self):
        """Liest Datenpakete aus Datei, addiert Audiopaket und sendet es über TCP."""
        data = np.empty(self.DATABLOCKSIZE, dtype=np.float32)
        size = self.fileHandle.readinto(data)

        while size > 0:
            # Warte auf Paket2 aus der Queue (blockierend, falls notwendig)
            try:
                audio_data = self.audio_queue.get(timeout=1)
            except queue.Empty:
                audio_data = np.zeros(self.DATABLOCKSIZE, dtype=np.float32)

            # Pakete addieren
            combined_data = data[:size] + audio_data[:size]

            # Senden
            self.data_sock.send(combined_data.astype(np.float32).tobytes())

            # Nächstes Paket einlesen
            size = self.fileHandle.readinto(data)

        self.cleanup()

    def cleanup(self):
        """Beendet den FFmpeg-Prozess und den Audiothread sauber."""
        self.stop_flag.set()
        self.audio_thread.join()
        if self.ffmpeg_proc.poll() is None:
            self.ffmpeg_proc.terminate()
            self.ffmpeg_proc.wait()
        self.fileHandle.close()

# Beispielhafte Nutzung (fileHandle und data_sock müssen vorher definiert sein)
# processor = StreamProcessor(fileHandle, "sourcefile2.wav", data_sock, 1024, 44100)
# processor.send_data()
