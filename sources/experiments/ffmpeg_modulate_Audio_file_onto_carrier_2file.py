import subprocess
import psutil
import numpy as np
import os
import time
from pathlib import Path
import numpy as np
import scipy.signal as signal

"""read audio file ,complex modulate to carrier and write result to a IQ-File.
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

formatstring = "s16le"
tSR = 1250000
fcenter = 1125000
fcarrier = 1400000
fcarrier = 1251000
lo_shift = abs(fcenter - fcarrier) #TODO: modify so as to also accept negative frequencies by sign change in sine signal
modulation_factor = 0.0001
pregain = 0.5
#format = self.get_formattag()
a = (np.tan(np.pi * lo_shift / tSR) - 1) / (np.tan(np.pi * lo_shift / tSR) + 1)

#a = (np.tan(np.pi * deltaf / iSR) - 1) / (np.tan(np.pi * deltaf / iSR) + 1)
b = [a, 1]      # Numerator-Koeffizienten
a_coeffs = [1, a]  # Denominator-Koeffizienten
#filepath = "C:/Users/scharfetter_admin/Documents/MW_Aufzeichnungen/COHIRADIA/Softwareentwicklung/COHIRADIA_RFCorder/COHIRADIA_RFCorder"
filepath = "C:/Users/scharfetter_admin/Downloads"

# filelist1 = ["cohiwizard_20250309_200914Z_1125kHz.wav"]
# filelist2 = ["synth_caro_spur6_0.wav"]
#TODO: Filestart durch die sequenz '-skip_initial_bytes N', N = Byteoffset  genau trimmen
filelist1 = ["AUDIOFILE"]
output_filename = "test_output.wav"
out_path = os.path.join(filepath, output_filename)
# for ix, input_filename in enumerate(filelist1):
#     input_filename1 = filelist1[ix]
#     print(f"next audio file: {input_filename1}")
#     output_filename = "remix_" + Path(input_filename).stem + ".wav"
#     in_path1 = os.path.join(filepath, input_filename1)
#     out_path = os.path.join(filepath, output_filename)
#     datachunkstart1 = find_data_chunk(in_path1)     #TODO: modify for general read from mp3 or wav
#     ffmpeg_path = "C:/Users/scharfetter_admin/Documents/MW_Aufzeichnungen/COHIRADIA/Softwareentwicklung/COHIWizard_2023/sources/ffmpeg-master-latest-win64-gpl-shared/bin"
#     ffmpeg_execmd = os.path.join(ffmpeg_path, "ffmpeg.exe")


        #######################################################
        #
        # TASK: read data from an audio stream from elsewhere in form of 16bit PCM audio data
        # if mp3: read mp3 via appropriate ffmpeg command
        # if wav: read wav via appropriate ffmpeg command
        # if format == stereo: join the two channels to one channel
        # if format == mono: do nothing
        # if format == 24bit: convert to 16bit PCM
        # if format == 32bit: convert to 16bit PCM 
        # if format == 32bit float: convert to 16bit PCM
        # 
        # 
        # ffmpeg_cmd = [
        #     ffmpeg_file_path, "-y", "-loglevel", "error", "-hide_banner",
        # ########################## implement correct reading format/codec, channel layout, sample rate  
        #     "-f", formatstring, "-ar", str(sampling_rate), "-ac", "2", "-i", "str(in_path1)",  # Lese später von PIPE, auf die der Audiostream kommt
        #     "-filter_complex",
        #     "[0:a]aresample=osr=" + str(tSR) + ",channelsplit=channel_layout=stereo [re][im];"   ###### Umbauen, soll nur mono-stream lesen
        #     "sine=frequency=" + str(lo_shift) + ":sample_rate="  + str(tSR) + "[sine_base];"
        #     "[sine_base] asplit=2[sine_sin1][sine_sin2];"
        #     "[sine_sin2]biquad=b0=" + str(a) + ":b1=1:b2=0:a0=1:a1=" + str(a) + ":a2=0[sine_cos];"
        #     "[re][sine_cos]amultiply[mul_re];"
        #     "[im][sine_sin1]amultiply[mul_im];"
        #     "[mul_re]volume=volume=" + str(modulation_factor) + "[mfre];"
        #     "[im]volume=volume=" + str(modulation_factor) + "[mfim];"
        #     "[mfre][sine_cos]amix=inputs=2:duration=shortest[modre];"
        #     "[mfim][sine_sin1]amix=inputs=2:duration=shortest[modim];"
        #     "[modre]volume=volume=" + str(pregain) + "[outre];"
        #     "[modim]volume=volume=" + str(pregain) + "[outim];"
        #     "-map", "[###out###]", "-c:a", "pcm_s16", "-f", "caf", "out_path"  ###########TODO: modify for mapping outre, outim to stereo PCM aof stdout oder out PIPE
        #     ]

            #     # Prozess starten
            #     ffmpeg_process = subprocess.Popen(ffmpeg_cmd, 
            #         stdin=subprocess.PIPE, 
            #         stdout=subprocess.PIPE, 
            #         stderr=subprocess.PIPE,
            #         bufsize=10**7)
            #     print(f"ffmpeg_command: {ffmpeg_cmd}")
            # except FileNotFoundError:
            #     print(f"Input file not found, probably ffmpeg path is wrong")
            #     return()
            # except subprocess.SubprocessError as e:
            #     print(f"Error when executing ffmpeg: {e}")
            #     return()    
            # except Exception as e:
            #     print(f"Unexpected error: {e}")
            #     return()    
            
            # if os.name.find("posix") >= 0:
            #     pass
            # else:
            #     psutil.Process(ffmpeg_process.pid).nice(psutil.HIGH_PRIORITY_CLASS)
            #     pass


# Konfigurierbare Parameter

stream_url = "http://ght.phonomuseum.at/Sound/x/pa_0002-6918.mp3"  # Dein Webstream-URL
#output_file = "output.caf"     # Output-Datei

ffmpeg_cmd = [
    "ffmpeg", "-y", "-loglevel", "error", "-hide_banner",
    "-i", stream_url,  # Lies direkt vom Webstream
    "-filter_complex",
    # FILTERCHAIN
    # 1. Downmix zu Mono, Resampling, Normalisierung
    "[0:a]aresample=osr=" + str(tSR) + ",pan=mono|c0=.5*c0+.5*c1,volume=1.0[mono];"
    #"[0:a]aresample=osr=" + str(tSR) + ",channelsplit=channel_layout=stereo [re][im];"
    # 2. Sinus-Generator, Cosinus über Allpassfilter (biquad)
    "sine=frequency=" + str(lo_shift) + ":sample_rate=" + str(tSR) + "[sine_base];"
    "[sine_base]asplit=2[sine_sin][sine_for_cos];"
    "[sine_for_cos]biquad=b0=" + str(a) + ":b1=1:b2=0:a0=1:a1=" + str(a) + ":a2=0[sine_cos];"
    # # 3. Modulation (1 + modulation_factor * Y)
    "[mono]volume=volume=" + str(modulation_factor) + "[modsig];"
    "[modsig]asplit=2[modsig1][modsig2];"
    "[modsig1][sine_cos]amultiply[mod_re_component];"
    "[modsig2][sine_sin]amultiply[mod_im_component];"
    # 3. Modulationsanteil berechnen
    #"[mono]volume={modulation_factor}[modsig];",
    # "[modsig][sine_cos]amultiply[mul_re];"
    # "[modsig][sine_sin]amultiply[mul_im];"

    # 4. Add DC = sin/cos-Anteil (1 * sin(t) bzw. 1 * cos(t))
    "[mod_im_component]volume=volume=0.00001[inv_mod_im_component];"
    "[mod_re_component][sine_cos]amix=inputs=2:duration=shortest[modre];"
    "[sine_sin]volume=volume=1.0[sine_carrier];"
    "[inv_mod_im_component][sine_carrier]amix=inputs=2:duration=shortest[modim];"
    # 4. Trägeranteil separat skalieren (1.0) und addieren
    # "[sine_cos]volume=1.0[carrier_cos];"
    # "[sine_sin]volume=1.0[carrier_sin];"
    # "[mul_re][carrier_cos]amix=inputs=2:duration=shortest[modre];"
    # "[mul_im][carrier_sin]amix=inputs=2:duration=shortest[modim];"


    # 5. Pregain anwenden
    "[modre]volume=volume=" + str(pregain) + "[outre];"
    "[modim]volume=volume=" + str(pregain) + "[outim];"
    # "[carrier_cos]volume=" + str(pregain) + "[outre];"
    # "[carrier_sin]volume=" + str(0.2*pregain) + "[outim];"
    # "[re]anullsink;"
    # "[im]anullsink;"
    # aufteilen in Stereo-Output und auf Ausgabefile schreiben
    #"[outre][outim]amerge=inputs=2,pan=stereo|c0<c0|c1<c1[stereoout]",
    #"[outre][outim]amerge=inputs=2[interm]"
    #"[outre][outim]amerge=inputs=2[merged];[merged]pan=stereo|c0<0.1*c0|c1<0.5*c1[stereoout]",
    "[outre][outim]amerge=inputs=2[merged];[merged]pan=stereo|c0=0.5*c0|c1=0.5*c1[stereoout]",
    #"[interm]pan=stereo|c0<c0|c1<c1[stereoout]"
    #"[stereoout]anull[out]",
    "-map", "[stereoout]", "-c:a", "pcm_s16le", "-f", "wav", out_path
    # "-map", "[stereoout]",
    # #"-ac", "2", "-ar", str(tSR),
    # "-c:a", "pcm_s16le",
    # "-f", "wav", out_path
]


        #"[rsin][rcos]amerge=inputs=2,pan=stereo|c0<c0|c1<c1[out]",
        #"-map", "[out]", "-c:a", "pcm_s16le", "-f", "wav", out_path
#"[rsin][rcos]amerge=inputs=2,pan=stereo|c0<c0|c1<c1[out]",
# ffmpeg_cmd = [
#     "ffmpeg", "-y", "-loglevel", "error", "-hide_banner",
#     "-i", stream_url,  # Lies direkt vom Webstream
#     "-filter_complex",
#     "[0:a]aresample=osr=" + str(tSR) + ",channelsplit=channel_layout=stereo [re][im];"
#     "sine=frequency=" + str(lo_shift) + ":sample_rate=" + str(tSR) + "[sine_base];"
#     "[sine_base]asplit=2[sine_sin][sine_for_cos];"
#     "[sine_for_cos]biquad=b0=" + str(a) + ":b1=1:b2=0:a0=1:a1=" + str(a) + ":a2=0[sine_cos];"
#     "[sine_cos]volume=" + str(pregain) + "[outre];"
#     "[sine_sin]volume=" + str(0.5*pregain) + "[outim];"
#     "[re]anullsink;"
#     "[im]anullsink;"
#     "[outre][outim]amerge=inputs=2[stereoout]",
#     "-map", "[stereoout]",
#     "-c:a", "pcm_s16le",
#     "-f", "wav", out_path
# ]

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

try:
    stdout, stderr = ffmpeg_process.communicate()  # Timeout nach 60 Sekunden
except subprocess.TimeoutExpired:
    ffmpeg_process.kill()
    stdout, stderr = ffmpeg_process.communicate()
    print(f"ffmpeg wurde wegen Timeout beendet")