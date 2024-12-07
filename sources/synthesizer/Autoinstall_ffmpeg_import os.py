import os
import subprocess
import platform
import urllib.request
import zipfile
import tarfile
import shutil

def is_ffmpeg_installed():
    """Überprüft, ob ffmpeg auf dem System verfügbar ist."""
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except FileNotFoundError:
        return False

def download_ffmpeg(url, output_path):
    """Lädt ffmpeg von der angegebenen URL herunter."""
    print(f"Lade ffmpeg von {url} herunter...")
    urllib.request.urlretrieve(url, output_path)
    print("Download abgeschlossen.")

def install_ffmpeg_linux(destination):
    """Installiert ffmpeg unter Linux."""
    os.makedirs(destination, exist_ok=True)
    ffmpeg_url = "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
    archive_path = os.path.join(destination, "ffmpeg.tar.xz")
    
    download_ffmpeg(ffmpeg_url, archive_path)
    
    print("Entpacke ffmpeg...")
    with tarfile.open(archive_path, "r:xz") as tar:
        tar.extractall(destination)
    
    ffmpeg_dir = next((d for d in os.listdir(destination) if d.startswith("ffmpeg")), None)
    if ffmpeg_dir:
        ffmpeg_path = os.path.join(destination, ffmpeg_dir)
        print(f"ffmpeg erfolgreich in {ffmpeg_path} entpackt.")
    else:
        raise RuntimeError("Fehler beim Entpacken von ffmpeg.")
    
    os.remove(archive_path)  # Lösche die Archivdatei
    return os.path.join(ffmpeg_path, "ffmpeg")

def install_ffmpeg_windows(destination):
    """Installiert ffmpeg unter Windows."""
    os.makedirs(destination, exist_ok=True)
    ffmpeg_url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
    archive_path = os.path.join(destination, "ffmpeg.zip")
    
    download_ffmpeg(ffmpeg_url, archive_path)
    
    print("Entpacke ffmpeg...")
    with zipfile.ZipFile(archive_path, "r") as zip_ref:
        zip_ref.extractall(destination)
    
    ffmpeg_dir = next((d for d in os.listdir(destination) if "ffmpeg" in d), None)
    if ffmpeg_dir:
        ffmpeg_path = os.path.join(destination, ffmpeg_dir)
        print(f"ffmpeg erfolgreich in {ffmpeg_path} entpackt.")
    else:
        raise RuntimeError("Fehler beim Entpacken von ffmpeg.")
    
    os.remove(archive_path)  # Lösche die Archivdatei
    return os.path.join(ffmpeg_path, "bin", "ffmpeg.exe")

def configure_path(ffmpeg_path):
    """Setzt den ffmpeg-Pfad in den Umgebungsvariablen."""
    os.environ["PATH"] += os.pathsep + os.path.dirname(ffmpeg_path)
    print(f"Der ffmpeg-Pfad wurde auf {os.path.dirname(ffmpeg_path)} gesetzt.")

def main():
    if is_ffmpeg_installed():
        print("ffmpeg ist bereits installiert.")
        return
    
    print("ffmpeg ist nicht installiert.")
    install_choice = input("Möchten Sie ffmpeg installieren? (ja/nein): ").strip().lower()
    if install_choice not in ("ja", "j", "yes", "y"):
        print("Installation abgebrochen.")
        return
    
    root_dir = os.path.dirname(os.path.abspath(__file__))
    ffmpeg_dir = os.path.join(root_dir, "ffmpeg")
    
    system = platform.system().lower()
    if system == "linux":
        ffmpeg_path = install_ffmpeg_linux(ffmpeg_dir)
    elif system == "windows":
        ffmpeg_path = install_ffmpeg_windows(ffmpeg_dir)
    else:
        print("Dieses Betriebssystem wird nicht unterstützt.")
        return
    
    configure_choice = input("Soll der ffmpeg-Pfad automatisch konfiguriert werden? (ja/nein): ").strip().lower()
    if configure_choice in ("ja", "j", "yes", "y"):
        configure_path(ffmpeg_path)
    else:
        print(f"ffmpeg wurde in {ffmpeg_path} installiert. Bitte fügen Sie diesen Pfad manuell zu den Umgebungsvariablen hinzu.")
    
    print("ffmpeg-Installation abgeschlossen.")

if __name__ == "__main__":
    main()
