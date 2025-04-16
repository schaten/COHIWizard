from collections import defaultdict
from pathlib import Path
import os

import csv

def write_results_to_csv(duplicates, output_csv='name_duplicates_with_paths.csv'):
    with open(output_csv, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        # Kopfzeile
        writer.writerow(['Dateiname', 'Vorkommen 1', 'Vorkommen 2', 'Vorkommen 3', '...'])

        for filename, occurrences in sorted(duplicates.items()):
            row = [filename] + [f"{source}: {path}" for source, path in occurrences]
            writer.writerow(row)

    print(f"📄 CSV-Ergebnis geschrieben in: {output_csv}")

# 🔄 Robust: Mehrere Encodings unterstützen
def try_open_file(file):
    for enc in ['utf-8', 'cp1252', 'latin1']:
        try:
            with open(file, 'r', encoding=enc) as f:
                entries = []
                for line in f:
                    full_path = line.strip().strip('"').strip()
                    if full_path:
                        filename = Path(full_path).name
                        #entries.append((filename, file, full_path))
                        entries.append((filename, Path(file).name, full_path))
                return entries
        except UnicodeDecodeError:
            continue
    print(f"⚠️ Konnte Datei {file} mit keinem bekannten Encoding lesen.")
    return []

# 🔃 Alle Dateinamen sammeln
def read_filenames(file_path, file_list):
    all_entries = []
    for file in file_list:
        full_file = os.path.join(file_path, file)
        all_entries.extend(try_open_file(full_file))
    return all_entries  # List of (filename, source_txtfile, full path string)

# 🔍 Duplikate anhand von Dateinamen finden
def find_name_duplicates(name_entries):
    name_map = defaultdict(list)
    for filename, source, full_path in name_entries:
        name_map[filename].append((source, full_path))
    return {name: info for name, info in name_map.items() if len(info) > 1}

# 📄 Ausgabe schreiben
def write_results_to_file(duplicates, output_path='name_duplicates_with_paths.txt'):
    with open(output_path, 'w', encoding='utf-8') as f:
        for filename, occurrences in sorted(duplicates.items()):
            f.write(f"{filename} erscheint in:\n")
            for source, full_path in sorted(occurrences):
                f.write(f"    {source}: {full_path}\n")
            f.write("\n")
    print(f"\n✅ Ergebnis geschrieben in: {output_path}")

# 🚀 Hauptfunktion
def main():
    file_path = "C:/Users/scharfetter_admin/Downloads/Plattenbereinigung"
    #list_files = ['TestAliste.txt', 'TestBliste.txt']  # Deine Eingabelisten
    list_files = ['merkur_dat_liste.txt', 'venus_dat_liste.txt', 'erde_dat_liste.txt',
                'mars_dat_liste.txt', 'jupiter_dat_liste.txt', 'saturn_dat_liste.txt',
                'uranus_dat_liste.txt', 'neptun_dat_liste.txt', 'io_dat_liste.txt',
                'iapetus_dat_liste.txt']
    # list_files = ['merkur_wav_liste.txt', 'venus_wav_liste.txt', 'erde_wav_liste.txt',
    #             'mars_wav_liste.txt', 'jupiter_wav_liste.txt', 'saturn_wav_liste.txt',
    #             'uranus_wav_liste.txt', 'neptun_wav_liste.txt', 'io_wav_liste.txt',
    #             'iapetus_wav_liste.txt']
    all_entries = read_filenames(file_path, list_files)

    print(f"🔎 Analysiere {len(all_entries)} Pfade...")

    duplicates = find_name_duplicates(all_entries)

    if not duplicates:
        print("✅ Keine mehrfach vorkommenden Dateinamen gefunden.")
    else:
        print(f"\n❗ {len(duplicates)} Dubletten (nach Namen) gefunden.")
        write_results_to_file(duplicates, os.path.join(file_path, 'name_duplicates_with_paths.txt'))
        write_results_to_csv(duplicates, os.path.join(file_path, 'name_duplicates_with_paths.csv'))

if __name__ == '__main__':
    main()

    ###############VARIANTE mit Filezugriff
# import hashlib
# from pathlib import Path
# from collections import defaultdict

# # --- 🔄 Robust: mehrere Encodings unterstützen
# def try_open_file(file):
#     for enc in ['utf-8', 'cp1252', 'latin1']:
#         try:
#             with open(file, 'r', encoding=enc) as f:
#                 return [(line.strip(), file) for line in f if line.strip()]
#         except UnicodeDecodeError:
#             continue
#     print(f"⚠️ Konnte Datei {file} mit keinem bekannten Encoding lesen.")
#     return []

# # --- 🔃 Dateien + Ursprungslisten einlesen
# def read_paths_with_sources(file_list):
#     all_paths = []
#     for file in file_list:
#         all_paths.extend(try_open_file(file))
#     return all_paths  # List of (path, sourcefile)

# # --- 📦 Hash berechnen
# def file_hash(path, hash_algo='sha256', block_size=65536):
#     h = hashlib.new(hash_algo)
#     with open(path, 'rb') as f:
#         for block in iter(lambda: f.read(block_size), b''):
#             h.update(block)
#     return h.hexdigest()

# # --- 🔍 Duplikate finden
# def find_duplicates(paths_with_sources):
#     hash_map = defaultdict(list)
#     for full_path, source_file in paths_with_sources:
#         p = Path(full_path)
#         if not p.is_file():
#             continue
#         try:
#             size = p.stat().st_size
#             hash_val = file_hash(p)
#             key = (size, hash_val)
#             hash_map[key].append((str(p), source_file))
#         except Exception as e:
#             print(f"Fehler bei {p}: {e}")

#     return {k: v for k, v in hash_map.items() if len(v) > 1}

# # --- 📄 Ergebnis in Datei schreiben
# def write_results_to_file(duplicates, output_path='duplicates_found.txt'):
#     with open(output_path, 'w', encoding='utf-8') as f:
#         for (size, hashval), filelist in duplicates.items():
#             f.write(f"\n[{len(filelist)}x] Größe: {size} Bytes | Hash: {hashval}\n")
#             for filepath, sourcefile in filelist:
#                 f.write(f"    {filepath}    (aus: {sourcefile})\n")
#     print(f"\n✅ Ergebnis wurde geschrieben in: {output_path}")

# # --- 🚀 Hauptfunktion
# def main():
#     list_files = ['liste1.txt', 'liste2.txt', 'liste3.txt']  # <- deine Eingabelisten
#     all_paths = read_paths_with_sources(list_files)

#     print(f"🔎 Analysiere {len(all_paths)} Dateien...")

#     duplicates = find_duplicates(all_paths)

#     if not duplicates:
#         print("✅ Keine echten Duplikate gefunden.")
#     else:
#         print(f"\n❗ {len(duplicates)} Duplikatgruppen gefunden.")
#         write_results_to_file(duplicates)

# if __name__ == '__main__':
#     main()

