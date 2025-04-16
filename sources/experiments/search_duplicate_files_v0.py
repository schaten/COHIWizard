
import hashlib
from pathlib import Path
import os

file_path = "C:/Users/scharfetter_admin/Downloads/Plattenbereinigung"
# list_files = ['merkur_wav_liste.txt', 'venus_wav_liste.txt', 'erde_wav_liste.txt',
#                 'mars_wav_liste.txt', 'jupiter_wav_liste.txt', 'saturn_wav_liste.txt',
#                 'uranus_wav_liste.txt', 'neptun_wav_liste.txt', 'io_wav_liste.txt',
#                 'iapetus_wav_liste.txt']
list_files = ['TestAliste.txt', 'TestBliste.txt']


def try_open_file(file):
    # Liste möglicher Encodings – utf-8, dann Windows-1252 (ANSI), ISO-8859-1
    for enc in ['utf-8', 'cp1252', 'latin1']:
        try:
            with open(file, 'r', encoding=enc) as f:
                return [line.strip() for line in f if line.strip()]
        except UnicodeDecodeError:
            continue
    print(f"⚠️ Konnte Datei {file} mit keinem bekannten Encoding lesen.")
    return []

def read_paths_from_files(file_path,file_list):
    all_paths = []
    for file in file_list:
        all_paths.extend(try_open_file(os.path.join(file_path,file)))
    # for file in file_list:
    #     with open(os.path.join(file_path,file), 'r', encoding='utf-8') as f:
    #         all_paths.extend(line.strip() for line in f if line.strip())
    return all_paths

def file_hash(path, hash_algo='sha256', block_size=65536):
    h = hashlib.new(hash_algo)
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(block_size), b''):
            h.update(block)
    return h.hexdigest()

def find_duplicates(paths):
    #import os
    from collections import defaultdict

    hash_map = defaultdict(list)

    for path in paths:
        p = Path(path)
        if not p.is_file():
            continue
        try:
            size = p.stat().st_size
            hash_val = file_hash(p)
            key = (size, hash_val)
            hash_map[key].append(str(p))
        except Exception as e:
            print(f"Fehler bei {p}: {e}")

    # Nur Dubletten behalten
    duplicates = {k: v for k, v in hash_map.items() if len(v) > 1}
    return duplicates

#def main():
# 👇 Hier gib deine Listendateien ein

all_paths = read_paths_from_files(file_path,list_files)

print(f"Prüfe {len(all_paths)} Dateien...")

dupes = find_duplicates(all_paths)

if not dupes:
    print("✅ Keine echten Duplikate gefunden.")
else:
    print(f"\n❗ {len(dupes)} Duplikatgruppen gefunden:\n")
    for (size, hashval), files in dupes.items():
        print(f"[{len(files)}x] Größe: {size} Bytes | Hash: {hashval}")
        for f in files:
            print(f"    {f}")
        print()