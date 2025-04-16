import os
import requests

def finde_m3u_dateien(source_directory):
    return [os.path.join(source_directory, f) 
            for f in os.listdir(source_directory) 
            if f.lower().endswith(".m3u")]

def download_audio_from_m3u_files(source_directory, target_directory):
    if not os.path.exists(target_directory):
        os.makedirs(target_directory)

    m3u_files = finde_m3u_dateien(source_directory)

    if not m3u_files:
        print(f"[INFO] Keine .m3u-Dateien im Verzeichnis '{source_directory}' gefunden.")
        return

    for m3u_file in m3u_files:
        with open(m3u_file, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip()]

        if not urls:
            print(f"[WARNUNG] Keine URLs in {m3u_file} gefunden.")
            continue

        for url in urls:
            filename = os.path.basename(url.split('?')[0])
            target_path = os.path.join(target_directory, filename)

            if os.path.exists(target_path):
                print(f"[SKIP] Datei existiert bereits: {filename}")
                continue

            try:
                print(f"[INFO] Lade herunter: {url}")
                response = requests.get(url, stream=True)
                response.raise_for_status()

                with open(target_path, 'wb') as out_file:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            out_file.write(chunk)

                print(f"[OK] Gespeichert unter: {target_path}")

            except requests.RequestException as e:
                print(f"[FEHLER] Konnte {url} nicht herunterladen: {e}")

# # Beispielaufruf:
# if __name__ == "__main__":
#     quellordner = "m3u_files"     # Verzeichnis mit .m3u-Dateien
#     zielordner = "downloads"      # Zielverzeichnis
#     download_audio_from_m3u_files(quellordner, zielordner)


# Beispielaufruf:
if __name__ == "__main__":
    quellordner = "C:/Users/scharfetter_admin/Downloads/m3u_for_download"     # Verzeichnis, in dem die .m3u-Dateien liegen
    zielordner = "C:/Users/scharfetter_admin/Downloads/audios"      # Zielverzeichnis für Audiofiles
    download_audio_from_m3u_files(quellordner, zielordner)
