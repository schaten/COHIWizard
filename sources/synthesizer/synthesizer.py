#IMPORT WHATEVER IS NEEDED
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5 import QtGui
from PyQt5 import QtWidgets, QtGui
import numpy as np
import locale
import os
import logging
from datetime import datetime
import datetime as ndatetime
import matplotlib.pyplot as plt
#import pyfda.pyfdax
from auxiliaries import auxiliaries as auxi
import logging
import yaml
import copy
import time
import pytz
import wave
import pyqtgraph as pg
#import contextlib
import struct
import soundfile as sf
from scipy.signal import sosfilt, butter, resample
from pathlib import Path
from auxiliaries import WAVheader_tools


class modulate_worker(QObject):
    """ worker class for generating modulated signals in a separate thread
    :param : no regular parameters; as this is a thread worker communication occurs via
        __slots__: Dictionary with parameters
    :return : none
    """
    __slots__ = ["carrier_frequencies", "playlists","sample_rate","block_size","cutoff_freq","modulation_depth","output_base_name","exp_num_samples","progress","logger","combined_signal_block","LO_freq","gain"]
    SigFinished = pyqtSignal()
    SigPupdate = pyqtSignal()
    SigMessage = pyqtSignal(str)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stopix = False #TODO: check if necessary
        self.mutex = QMutex() #TODO: check if necessary
        self.CHUNKSIZE = int(1024**2) #TODO: check if necessary, not used anywhere
        self.AUDIO_MAXAMP = 0.9 #max amplitude of the audio signal
 
    def set_carrier_frequencies(self,_value):
        self.__slots__[0] = _value
    def get_carrier_frequencies(self):
        return(self.__slots__[0])
    def set_playlists(self,_value):
        self.__slots__[1] = _value
    def get_playlists(self):
        return(self.__slots__[1])
    def set_sample_rate(self,_value):
        self.__slots__[2] = _value
    def get_sample_rate(self):
        return(self.__slots__[2])
    def set_block_size(self,_value):
        self.__slots__[3] = _value
    def get_block_size(self):
        return(self.__slots__[3])
    def set_cutoff_freq(self,_value):
        self.__slots__[4] = _value
    def get_cutoff_freq(self):
        return(self.__slots__[4])
    def set_modulation_depth(self,_value):
        self.__slots__[5] = _value
    def get_modulation_depth(self):
        return(self.__slots__[5])
    def set_output_base_name(self,_value):
        self.__slots__[6] = _value
    def get_output_base_name(self):
        return(self.__slots__[6])
    def set_exp_num_samples(self,_value):
        self.__slots__[7] = _value
    def get_exp_num_samples(self):
        return(self.__slots__[7])
    def set_progress(self,_value):
        self.__slots__[8] = _value
    def get_progress(self):
        return(self.__slots__[8])
    def set_logger(self,_value):
        self.__slots__[9] = _value
    def get_logger(self):
        return(self.__slots__[9])
    def set_combined_signal_block(self,_value):
        self.__slots__[10] = _value
    def get_combined_signal_block(self):
        return(self.__slots__[10])
    def set_LO_freq(self,_value):
        self.__slots__[11] = _value
    def get_LO_freq(self):
        return(self.__slots__[11])
    def set_gain(self,_value):
        self.__slots__[12] = _value
    def get_gain(self):
        return(self.__slots__[12])
    
    
    def modulate_terminate(self):
        self.stopix = True

    def start_modulator(self):
        """fetches several parameters from the main thread and starts process_multiple_carriers_blockwise
        emits SigFinished after comletion of the task for triggering termination of the worker thread
        """
        self.logger = self.get_logger()
        self.stopix = False
        carrier_frequencies = self.get_carrier_frequencies()
        playlists = self.get_playlists()
        sample_rate = self.get_sample_rate()
        block_size = self.get_block_size()
        cutoff_freq = self.get_cutoff_freq()
        modulation_depth = self.get_modulation_depth()
        output_base_name = self.get_output_base_name()
        exp_num_samples = self.get_exp_num_samples()
        self.process_multiple_carriers_blockwise(carrier_frequencies, playlists, sample_rate, block_size, cutoff_freq, modulation_depth, output_base_name, exp_num_samples)
        self.SigFinished.emit()

    def resample_audio(self,audio_data, original_rate, target_rate):
        """
        Resample audio data to the target sample rate.
        """
        num_samples = int(len(audio_data) * target_rate / original_rate)
        return resample(audio_data, num_samples)

    def convert_to_mono(self,audio_data, num_channels):
        """
        Convert multi-channel audio to mono by averaging channels.
        """
        if num_channels > 1:
            return np.mean(audio_data, axis=1)
        return audio_data

    def process_block(self,audio_block, sos, zi):
        """Apply the low-pass filter blockwise and maintain filter state (zi)."""
        filtered_block, zi = sosfilt(sos, audio_block, zi=zi)
        return filtered_block, zi
    
    def modulate_signal(self,filtered_signal, carrier_freq, sample_rate, sample_offset, modulation_depth):
        """Modulate the filtered signal onto a carrier frequency with adjustable modulation depth."""
        # time vector based on sample_offset
        t = np.arange(sample_offset, sample_offset + len(filtered_signal)) / sample_rate
        carrier = np.exp(2 * np.pi * 1j *carrier_freq * t)
        modulated_signal = (1 + modulation_depth * filtered_signal) * carrier
        #print(f"mean modulated signal: {np.mean(modulated_signal)} mean real part: {np.mean(np.real(modulated_signal))} mean imag part: {np.mean(np.imag(modulated_signal))}")
        return modulated_signal

    def display_signal_level(self,signal):
        """
        calculate the RMS and peak values of a signal
        """

    def get_wav_maxlevel(self,wav_file, threshold_percentile=95, spike_duration_ms=1):
        """determine expected max signal level of an audio file. Do not consider short spikes with a duration of less than a ms

        :param wav_file: path of the audio file
        :type wav_file: str
        :param threshold_percentile: allowable max signal in % of FSR, defaults to 95
        :type threshold_percentile: int, optional
        :param spike_duration_ms: max duration of a spike (will be ignored then), defaults to 1
        :type spike_duration_ms: int, optional
        :return: expected max amp
        :rtype: float
        """
        print(f"file: {Path(wav_file).stem} level checking")
        self.SigMessage.emit("auto level: " + Path(wav_file).stem)
        #self.gui.label_audioset_name.setText(f"file: {Path(wav_file).stem} level checking")
        data, sample_rate = sf.read(wav_file)
        
        # Konvertiere auf Mono, falls das Audiosignal Stereo ist TODO: check: mean may be lower than individual channel values !
        if len(data.shape) > 1:
            data = data.mean(axis=1)
        # Berechne die absolute Amplituden
        amplitudes = np.abs(data)   
        # Berechne die Dauer eines Samples in Millisekunden
        sample_duration_ms = 1000 / sample_rate
        # Berechne die Anzahl der Samples, die als "kurze Spitze" betrachtet werden
        max_spike_samples = int(spike_duration_ms / sample_duration_ms)
        # Berechne den Schwellenwert für die Amplitude auf Basis des `threshold_percentile`-Perzentils
        threshold_value = np.percentile(amplitudes, threshold_percentile)
        # Erstelle eine Kopie der Amplituden und setze kurze Spitzen auf Null
        filtered_amplitudes = amplitudes.copy() 
        # Durchlaufe die Amplituden und setze kurze Spitzen unterhalb der max_spike_samples auf 0
        for i in range(1, len(amplitudes) - 1):
            # Wenn eine Amplitude den Schwellenwert überschreitet
            if amplitudes[i] >= threshold_value:
                # Prüfe, ob es eine kurze Spitze ist (alle Amplituden in diesem Bereich überschreiten den Schwellenwert)
                start = max(i - max_spike_samples // 2, 0)
                end = min(i + max_spike_samples // 2, len(amplitudes))
                if np.all(amplitudes[start:end] >= threshold_value):
                    # Setze die Spitzen im Bereich auf 0
                    filtered_amplitudes[start:end] = 0
        # Bestimme die erwartete maximale Amplitude nach Filterung der Spitzen
        expected_max_amp = filtered_amplitudes.max() if filtered_amplitudes.size > 0 else amplitudes.max()
        expected_RMS_amp = filtered_amplitudes.std() if filtered_amplitudes.size > 0 else amplitudes.std()
        print("ready")
        self.SigMessage.emit("----")
        return expected_max_amp, expected_RMS_amp
    
    def read_and_process_audio_blockwise(self, file_list, carrier_freq, target_sample_rate, block_size, cutoff_freq, modulation_depth, zi, sample_offset, current_file_index, file_handles, audio_gain):
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
        #print(f"read_and_process_audio_blockwise; current_file_index: {current_file_index}, carrier_freq {carrier_freq}")
        sos = butter(4, cutoff_freq, btype='low', fs=target_sample_rate, output='sos')
        #print(f"carrier-freq: {carrier_freq}")
        threshold_percentile=95
        spike_duration_ms=1
        while current_file_index < len(file_list):
            file_path = file_list[current_file_index]

            # check if file open, if not: check level and power statistics, afterwards open the file and save the handles
            if current_file_index not in file_handles:
                #print(f"index: {current_file_index} file_handles: {file_handles}")
                max_level, RMS_amp = self.get_wav_maxlevel(file_path, threshold_percentile, spike_duration_ms)
                audio_gain = self.AUDIO_MAXAMP/max_level
                self.logger.debug(f"Audiofile {file_path} max_level: {max_level}, RMS_amp: {RMS_amp}, audio_gain auto: {audio_gain}")
                file_handles[current_file_index] = sf.SoundFile(file_path, 'r')

            f = file_handles[current_file_index]
            original_sample_rate = f.samplerate
            num_channels = f.channels

            # Blockweises Lesen
            audio_block = f.read(block_size)

            if len(audio_block) == 0:
                # Audio file is finished, close file and open next one
               
                print(f"close file {file_path} with index {current_file_index}; open next in list")
                f.close()
                del file_handles[current_file_index]  # remove Handle
                current_file_index += 1
                continue  # do not modulate, continue with the next audio file

            # Mono-conversion
            audio_block = audio_gain * self.convert_to_mono(audio_block, num_channels)
            #zero pad audio block to blocksize
            if len(audio_block) < block_size:
                delta = block_size - len(audio_block)
                aux = np.zeros(block_size)
                print(f"zeropad audio block, pad length = {delta}, len audioblock: {len(audio_block)}" )
                aux[0 : len(audio_block)] = audio_block
                audio_block = aux
            # Resampling falls notwendig
            if original_sample_rate != target_sample_rate:
                audio_block = self.resample_audio(audio_block, original_sample_rate, target_sample_rate)

            # Low-Pass-Filter audio signal
            filtered_block, zi = self.process_block(audio_block, sos, zi)

            # modulate to carrier
            modulated_block = self.modulate_signal(filtered_block, carrier_freq, target_sample_rate, sample_offset, modulation_depth)
            # update sample_offset for next block
            sample_offset += len(modulated_block)

            return modulated_block, zi, sample_offset, current_file_index, audio_gain
        
        return None, zi, sample_offset, current_file_index, audio_gain

    def process_multiple_carriers_blockwise(self, carrier_frequencies, playlists, sample_rate, block_size, cutoff_freq, modulation_depth, output_base_name, exp_num_samples):
        """
        Process audio from multiple playlists blockwise, each corresponding to a different carrier frequency.
        Write the combined output to multiple WAV files if the 2 GB limit is exceeded.
        """
        self.set_progress(0)
        self.logger.debug(f"process_multiple_carriers_blockwise; carrier_frequencies:{carrier_frequencies}")
        self.stopix = False
        max_file_size = 2 * 1024**3  # 2 GB in bytes
        self.logger.debug(f"process_multiple_carriers_blockwise: expected overall filesize: {4*exp_num_samples}")
        max_samples_per_file = max_file_size // 4  # complex 16-bit PCM = 4 bytes per sample
        perc_progress_old = 0
        # Initialize filter states for each carrier
        zis = [np.zeros((2, 2)) for _ in carrier_frequencies]  # Filter state buffer for each carrier (4th order filter)

        # Initialisiere sample_offset und current_file_index für jeden Carrier
        sample_offsets = [0] * len(carrier_frequencies)
        current_file_indices = [0] * len(carrier_frequencies)  # Track current file index for each carrier
        self.logger.debug(f"synthesizer worker carrier frequencies: {carrier_frequencies}")
        # Initialize file_handles as a list of dictionaries for each carrier
        file_handles = [{} for _ in carrier_frequencies] 

        total_samples_written = 0
        overall_samples_written = 0
        file_index = 0

        # Open first output file to write combined signal blockwise
        output_file_name = f"{output_base_name}_{file_index}.wav"
        out_file = sf.SoundFile(output_file_name, 'w', samplerate=sample_rate, channels=1, subtype='PCM_16')
        done = False
        #write 216 - 44 =  172 Null Bytes so as to leave room for the SDR-wavheader which will finally overwrite the current header
        prephaser = np.zeros(172)
        out_file.write(prephaser)
        #generate starting timestamp for wavheader
        next_starttime = datetime.now()
        next_starttime = next_starttime.astimezone(pytz.utc)
        self.logger.debug(f"synthesizer worker sample rate before modulating: {sample_rate}")
        audio_gain = np.zeros(len(playlists))
        while not done:
            combined_signal_block = None  # Buffer for combined signal block
            done = True  # Assume done unless we find more data
            
            # Process each carrier for the current block
            for i, (carrier_freq, zi) in enumerate(zip(carrier_frequencies, zis)):
                #print(f"audiogain {audio_gain[i]}")
                modulated_block, new_zi, sample_offsets[i], current_file_indices[i], audio_gain[i] = self.read_and_process_audio_blockwise(playlists[i], carrier_freq*1000, sample_rate, block_size, cutoff_freq, modulation_depth, zi, sample_offsets[i], current_file_indices[i], file_handles[i], audio_gain[i])
                
                # Wenn modulated_block None ist, dann ist das Playlist-Ende erreicht
                if modulated_block is None:
                    continue

                # Dynamically adjust combined signal block size based on modulated block size
                if combined_signal_block is None or len(combined_signal_block) < len(modulated_block):
                    combined_signal_block = np.zeros(len(modulated_block), dtype = np.complex128)
                gain = self.get_gain()
                if np.abs(len(combined_signal_block) - len(modulated_block)) > 0:
                    print(f"modulated block std gain*mb = {np.std(gain*modulated_block)} , gain = {gain} @ t = {sample_offsets[i]}, carrier = {i}")
                    print(f"diff len combined block -len mod block: {len(combined_signal_block) - len(modulated_block)}")
                combined_signal_block[:len(modulated_block)] += gain * modulated_block
                if np.std(gain*modulated_block) < 1e-1:
                    print(f"modulated block is zero, std gain*mb = {np.std(gain*modulated_block)} , gain = {gain} @ t = {sample_offsets[i]}")   
                # If we processed any blocks, we're not done
                done = False

                # Update filter state for this carrier
                zis[i] = new_zi
            
            # If all files are done, break the loop
            if done:
                break
            
            if self.stopix is True:
                break

            # Write the combined block to the current output file
            samples_to_write = len(combined_signal_block)

            if samples_to_write + total_samples_written > max_samples_per_file:
                # If the file exceeds 2GB, close the current file, enter the wav-header and start a new one
                out_file.close()
                filesize = max_samples_per_file*4
                self.logger.debug(f"process_multiple_carriers_blockwise: next starttime {next_starttime}")
                output_file_name_wavheader = output_file_name
                file_index += 1
                output_file_name = f"{output_base_name}_{file_index}.wav"
                next_starttime = self.wav_header_generator(output_file_name_wavheader,filesize,sample_rate,next_starttime,output_file_name)
                print("wavheader written")
                out_file = sf.SoundFile(output_file_name, 'w', samplerate=sample_rate, channels=1, subtype='PCM_16')
                total_samples_written = 0  # Reset the sample counter for the new file

        
            #convert complex 128 into 2 x float 64
            lend=2*len(combined_signal_block)
            #TODO check if carrier zero gap arises here
            block_to_write = np.zeros(lend)
            block_to_write[1::2] = np.imag(combined_signal_block)
            block_to_write[0::2] = np.real(combined_signal_block)
            try:
                out_file.write(block_to_write)
            except:
                print("write error")
            total_samples_written += samples_to_write
            overall_samples_written += samples_to_write
            perc_progress = 100*overall_samples_written / exp_num_samples
            if perc_progress - perc_progress_old > 0.1:
                perc_progress_old = perc_progress
                self.set_progress(perc_progress)
                self.set_combined_signal_block(combined_signal_block)
                self.SigPupdate.emit()
                if perc_progress > 100:
                    break

        # Close the final output file
        out_file.close()
        filesize = total_samples_written*4
        self.logger.debug(f"synthesizer modulate: filesize last out file: {filesize}")

        output_file_name_wavheader = output_file_name
        self.wav_header_generator(output_file_name_wavheader,filesize,sample_rate,next_starttime,"")
        self.logger.debug(f"write last wavheader into {output_file_name_wavheader}")
        
        #TODO : Check if already completely o.k. ! write true SDRUno-Header into the first 216 bytes of the closed file
        for file_handle_dict in file_handles:
            for handle in file_handle_dict.values():
                handle.close()
        self.logger.debug(f"synthesizer modulate task completed")

    def wav_header_generator(self, output_file_name, filesize,sample_rate, starttime, next_output_file_name):
        """generate wavheader for output_file_name:
        :param: output_file_name
        """
        LO_freq = self.get_LO_freq()
        playtime = filesize/4/sample_rate
        self.mutex.lock()
        self.logger.debug(f"wav_header_generator: playtime of file {playtime}")
        self.logger.debug(f"wav_header_generator: calculated filesize of file {filesize}")
        #generate basic SDR wavheader
        wavheader = WAVheader_tools.basic_wavheader(self,0,int(np.floor(sample_rate)),LO_freq,16,filesize,starttime)
        wavheader["starttime"] = [starttime.year, starttime.month, 0, starttime.day, starttime.hour, starttime.minute, starttime.second, int(starttime.microsecond/1000)]  
        wavheader["starttime_dt"] = starttime
        wavheader["stoptime_dt"] = wavheader["starttime_dt"] + ndatetime.timedelta(seconds = np.floor(playtime))
        spt = wavheader["stoptime_dt"] 
        wavheader["stoptime"] = [spt.year, spt.month, 0, spt.day, spt.hour, spt.minute, spt.second, int(spt.microsecond/1000)] 
        wavheader["nextfilename"] = Path(next_output_file_name).stem + Path(next_output_file_name).suffix
        self.logger.debug(f"wav_header_generator: wavheader {wavheader}")

        WAVheader_tools.write_sdruno_header(self,output_file_name,wavheader,True) ##TODO TODO TODO Linux conf: self.m["f1"],self.m["wavheader"] must be in Windows format
        self.mutex.unlock()
        return wavheader["stoptime_dt"]





class synthesizer_m(QObject):
    SigModelXXX = pyqtSignal()

    def __init__(self):
        super().__init__()
        # Constants
        self.CONST_SAMPLE = 0 # sample constant
        self.mdl = {}
        self.mdl["sample"] = 0
        self.mdl["_log"] = False
        self.mdl["fileopened"] = False
        self.mdl["playlist_active"] = False
        self.mdl["sample"] = 0
        self.mdl["TEST"] = False
        self.mdl["Buttloop_pressed"] = False
        self.mdl["errorf"] = False
        self.mdl["icorr"] = 0
        self.mdl["gain"] = 1
        self.mdl["audioBW"] = 4.5
        self.mdl["carrier_distance"] = 9
        self.mdl["carrier_ix"] = 0
        self.mdl["carrierarray"] = np.arange(0, 1, 1)
        self.mdl["cancelflag"] = True
        self.mdl["sample_rate"] = 0
        self.mdl["LO"] = 0
        self.mdl["SR_currindex"] = 0
        self.mdl["modfactor"] = 0.8
        # Create a custom logger
        logging.getLogger().setLevel(logging.DEBUG)
        # Erstelle einen Logger mit dem Modul- oder Skriptnamen
        self.logger = logging.getLogger(__name__)
        # Create handlers
        warning_handler = logging.StreamHandler()
        debug_handler = logging.FileHandler("system_log.log")
        warning_handler.setLevel(logging.WARNING)
        debug_handler.setLevel(logging.DEBUG)

        # Create formatters and add it to handlers
        warning_format = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
        debug_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        warning_handler.setFormatter(warning_format)
        debug_handler.setFormatter(debug_format)

        # Add handlers to the logger
        self.logger.addHandler(warning_handler)
        self.logger.addHandler(debug_handler)

        self.logger.debug('Init logger in abstract method reached')

class synthesizer_c(QObject):
    """_view method
    """
    SigAny = pyqtSignal()
    SigRelay = pyqtSignal(str,object)
    SigActivateOtherTabs = pyqtSignal(str,str,object)

    def __init__(self, synthesizer_m): #TODO: remove gui
        super().__init__()

        self.m = synthesizer_m.mdl
        self.logger = synthesizer_m.logger


    def dummy(self):
        print("hello from superclass")
        

class synthesizer_v(QObject):
    """_view methods for resampling module
    TODO: gui.wavheader --> something less general ?
    """

    SigAny = pyqtSignal()
    SigCancel = pyqtSignal()
    SigUpdateGUI = pyqtSignal(object)
    SigSyncGUIUpdatelist = pyqtSignal(object)
    SigRelay = pyqtSignal(str,object)
    SigActivateOtherTabs = pyqtSignal(str,str,object)

    def __init__(self, gui, synthesizer_c, synthesizer_m):
        super().__init__()

        self.m = synthesizer_m.mdl
        self.synthesizer_c = synthesizer_c
        self.headerlength = 44 #read audio wav after first 44bytes of header info; could be generalized by searching the next data chunk
        self.SORTCRITERION = 'name' #Sorting criterion for filelist: 'date': sort caa to date in ascending order, 'name': alphabetical 
        self.FILTER_OVERLAP = 800  #overlap samples due to filter delay
        self.READ_BIAS = -100     # pre-read audio samples to enable filter delay compensation

        self.AUTOSCALE_RF = 0     # Set to 1 to select autoscale mode causing exact RF levelling to max, otherwise set to 0 for fixed RF levelling  
        self.FIXSCALE_FAKTOR_RF = 0.8 # guard factor for fixed RF levelling: assumed max. RF level: #carriers * (1+C_m) * C_FIXSCALE_FAKTOR_RF. RF overload may occur if C_FIXSCALE_FAKTOR_RF < 1 

        self.DATABLOCKSIZE = 1024*32
        self.STD_AUDIOBW = "4.5"
        self.STD_CARRIERDISTANCE = "9"
        self.STD_fclow = "783"
        self.STD_LO = "1125"
        self.GAINOFFSET = 80
        self.gui = gui
        self.synthesizer_c = synthesizer_c
        #self.norepeat = False
        self.m["carrier_distance"] = float(self.STD_CARRIERDISTANCE)
        self.m["fc_low"] = int(self.STD_fclow)
        self.m["audioBW"] = float(self.STD_AUDIOBW)
        self.m["TEST"] = False
        self.m["wavheader"] = {}
        self.m["wavheader"]['centerfreq'] = 0
        self.m["icorr"] = 0
        self.m["cancelflag"] = False
        self.m["LO"] = 1125 
        
        self.rule_viol = False
        self.blinkstate = False         
        self.logger = synthesizer_m.logger
        self.synthesizer_c.SigRelay.connect(self.rxhandler)
        self.synthesizer_c.SigRelay.connect(self.SigRelay.emit)

        self.DATABLOCKSIZE = 1024*32
        self.gui = gui #gui_state["gui_reference"]#system_state["gui_reference"]
        self.logger = synthesizer_m.logger
        self.syntesisrunning = False
        self.load_index = False
        self.m["numcarriers"] = self.gui.spinBox_numcarriers.value()
        self.m["carrier_ix"] = 0
        self.init_synthesizer_ui()
        self.readFileList = []
        self.oldFileList = []
        self.readFilePath = []
        self.autosave = False
        for self.m["carrier_ix"] in range(0,2):
            self.readFileList.append([])
            self.readFileList[self.m["carrier_ix"]] = []
            self.oldFileList.append([])
            self.oldFileList[self.m["carrier_ix"]] = []
            self.readFilePath.append([])
            self.readFilePath[self.m["carrier_ix"]] = []
        self.m["carrier_ix"] = 0

        try:
            stream = open("config_wizard.yaml", "r")
            self.m["metadata"] = yaml.safe_load(stream)
            stream.close()
            self.ismetadata = True
        except:
            self.ismetadata = False
        try:
            self.default_directory = self.m["metadata"]["last_audiosource_path"]
        except:
            self.default_directory = ""

    def init_synthesizer_ui(self):
        self.m["SR_currindex"] = 5
        self.gui.comboBox_targetSR.setCurrentIndex(self.m["SR_currindex"])
        self.gui.lineEdit_LO.setText("1125")
        preset_time = QTime(00, 30, 00) 
        self.gui.timeEdit_reclength.setTime(preset_time)
        #self.gui.listWidget_sourcelist.setHeaderLabel("Directory tree")
        #self.gui.listWidget_sourcelist.itemClicked.connect(self.on_tree_item_clicked)
        #self.gui.listWidget_sourcelist.itemDoubleClicked.connect(self.on_tree_item_double_clicked)
        self.gui.pushButton_select_source.clicked.connect(self.select_tree)
        self.gui.listWidget_playlist.clear()
        item = QtWidgets.QListWidgetItem()
        self.gui.listWidget_sourcelist.addItem(item)
        self.gui.lineEdit_audiocutoff_freq.setText(self.STD_AUDIOBW)
        self.gui.lineEdit_carrierdistance.setText(self.STD_CARRIERDISTANCE)
        self.gui.spinBox_numcarriers.setProperty("value", 2)
        #self.gui.spinBox_numcarriers.editingFinished.connect(self.freq_carriers_update)
        #react to arrows press
        self.gui.spinBox_numcarriers.valueChanged.connect(self.on_value_changed)
        # react only to key input
        self.gui.spinBox_numcarriers.editingFinished.connect(self.on_editing_finished)

        self.gui.lineEdit_carrierdistance.editingFinished.connect(self.carrierdistance_update)
        self.gui.lineEdit_audiocutoff_freq.editingFinished.connect(self.audioBW_update)
        self.gui.lineEdit_fc_low.editingFinished.connect(self.fc_low_update)
        self.gui.lineEdit_LO.editingFinished.connect(self.LO_update)
        self.gui.lineEdit_modfactor.editingFinished.connect(self.modfactor_update)
        self.gui.comboBox_targetSR_2.setCurrentIndex(1)
        self.gui.comboBox_targetSR_2.currentIndexChanged.connect(self.preset_SR_LO)
        self.gui.comboBox_targetSR.currentIndexChanged.connect(self.RecBW_update)
        self.gui.listWidget_playlist.model().rowsInserted.connect(self.playlist_update_delayed)
        self.gui.listWidget_playlist.model().rowsRemoved.connect(self.playlist_update_delayed) 
        self.gui.listWidget_playlist.setSelectionMode(QListWidget.ExtendedSelection)
        self.gui.listWidget_playlist.setContextMenuPolicy(Qt.CustomContextMenu)
        self.gui.listWidget_playlist.customContextMenuRequested.connect(self.show_context_menu)
        self.gui.listWidget_playlist.model().rowsMoved.connect(self.on_rows_moved)
        self.gui.comboBox_cur_carrierfreq.currentIndexChanged.connect(self.carrier_ix_changed)
        self.gui.pushButton_saveproject.clicked.connect(self.save_project)
        self.gui.pushButton_loadproject.clicked.connect(self.load_project)
        self.gui.pushButton_clearproject.clicked.connect(self.clear_project)
        self.gui.synthesizer_pushbutton_create.clicked.connect(self.create_band_thread)
        #self.gui.synthesizer_pushbutton_create.clicked.connect(self.create_band)
        self.gui.timeEdit_reclength.timeChanged.connect(self.carrier_ix_changed)
        self.gui.synthesizer_pushbutton_cancel.clicked.connect(self.cancel_modulate)
        self.gui.verticalSlider_Gain.setProperty("value", 76) #percent

        self.gui.verticalSlider_Gain.valueChanged.connect(self.setgain)
        self.previous_value = self.gui.spinBox_numcarriers.value()
        self.canvasbuild()
        self.RecBW_update()
        #self.gui.lineEdit_carrierdistance.textEdited.connect(self.carriedistance_update)

    def clear_project(self):
        self.init_synthesizer_ui()
        self.gui.listWidget_sourcelist.clear()
        self.readFileList = []
        self.oldFileList = []
        self.readFilePath = []
        self.autosave = False
        for self.m["carrier_ix"] in range(0,2):
            self.readFileList.append([])
            self.readFileList[self.m["carrier_ix"]] = []
            self.oldFileList.append([])
            self.oldFileList[self.m["carrier_ix"]] = []
            self.readFilePath.append([])
            self.readFilePath[self.m["carrier_ix"]] = []
        self.m["carrier_ix"] = 0

    def setgain(self):
        """set gain which is set by the gain slider and pass it to the modulator worker
        """
        gain = 10**((self.gui.verticalSlider_Gain.value()/100*90 - self.GAINOFFSET)/20)
        #print(f"synthesizer gain: {gain}, slidervalue: {self.gui.verticalSlider_Gain.value()}")
        self.logger.debug("cb_setgain, gain: %f %i",gain,self.gui.verticalSlider_Gain.value())
        try:
            self.modulate_worker.set_gain(gain)
        except:
            pass
        #print(f"synthesizer, set gain: {gain}")


    def showRFdata(self):
        """_take over datasegment from player loop worker and caluclate from there the signal volume and present it in the volume indicator
        read gain value and present it in the player Tab on the 'progressbar' Widget 'progressBar_volume'
        Parameters: a = length form top to 0dB tick
        b = length between -80 and 0 dB ticks
        c = length between bottom and -80dB tick
        a+b+c = total length of the indicator and hence of the progress-bar volume 
        GUI Element
        :return: _False if error, True on succes_
        :rtype: _Boolean_
        """
        # geometry scaling; absolute numbers are not relevant, only relative lengths
        #a = #10/139.5 #7/86  
        c = 11/89 #16.5/139.5 #8/86
        b = 72/89 #(139.5 - 10 -16.5)/139.5 #(86 -7 -8)/86
        data = self.modulate_worker.get_combined_signal_block()
        #use RMS value as indicator for signal strength 
        refvol = 0.71 #could be used for rescaling to amplitude values
        volume = np.linalg.norm(data)/refvol/np.sqrt(len(data))
        self.logger.debug(f"synthesizer showRFdata volume: {volume} ")
        span = 80
        #vol = 1.5*np.std(volume)/scl/refvol
        dBvol = 20*np.log10(volume)
        rawvol = c + b + dBvol/span*b
        if dBvol > 0:
            dispvol = min(100, rawvol*100)
        elif (dBvol < 0) and (dBvol > -span):
            dispvol = rawvol*100
        elif dBvol < -span:
            dispvol = c*0.8*100
        if np.any(np.isnan(dispvol)):
            return
        #print(f"vol: {vol} dB: {dBvol} std: {np.std(cv)/scl} dispvol: {dispvol} rv: {np.std(cv)/scl}")
        self.gui.progressBar_volume.setValue(int(np.floor(dispvol*10))) 
        if dBvol > -3:
            self.gui.progressBar_volume.setStyleSheet("QProgressBar::chunk "
                    "{"
                        "background-color: red;"
                    "}")
        elif dBvol < -40:
            self.gui.progressBar_volume.setStyleSheet("QProgressBar::chunk "
                    "{"
                        "background-color: yellow;"
                    "}")           
        else:
            self.gui.progressBar_volume.setStyleSheet("QProgressBar::chunk "
                    "{"
                        "background-color: green;"
                    "}")

    def cancel_modulate(self):
        """Cancel synthesis job by terminating the modulate_worker thread
        """
        #TODO check how to handle and delete after change to model
        #schedule_objdict = self.m["schedule_objdict"]
        #TODO: look why that was used self.SigDisconnectExternalMethods.emit("cancel_resampling")
        self.gui.synthesizer_pushbutton_cancel.clicked.disconnect(self.cancel_modulate)
        if self.m["cancelflag"]:
            self.logger.debug("cancel_modulation: **** suppressed because cancelflag ___cancel_resamp reached")
            self.gui.synthesizer_pushbutton_cancel.clicked.connect(self.cancel_modulate)
            return
        self.m["cancelflag"] = True
        time.sleep(0.001)
        for i in range(5):
            self.logger.debug("**** 5 x BLOCK *****___cancel_synthesizer reached")
        try:
            self.modulate_worker.modulate_terminate()
        except:
            self.logger.debug("cancel synthesizer modulation: modulate worker could not be terminated")
            pass
        #TODO TODO TODO: delete out files produced so far ? or leave them ?
        self.gui.synthesizer_pushbutton_cancel.clicked.connect(self.cancel_modulate)
        #self.cleanup()

    def canvasbuild(self):
        """
        sets up a pyQTgraph canvas to which curves can be plotted
        """
        self.plot_widget = pg.PlotWidget()
        self.gui.gridLayout_synthesizer.addWidget(self.plot_widget,0,7,3,2)
        self.plot_widget.getAxis('left').setStyle(tickFont=pg.QtGui.QFont('Arial', 6))
        self.plot_widget.getAxis('bottom').setStyle(tickFont=pg.QtGui.QFont('Arial', 6))
        self.plot_widget.setBackground('w')

    def preset_gain(self):
        """determine optimal gain and set gain slider accordingly
        """
        numcar = self.gui.spinBox_numcarriers.value()
        wanted_gain = 0.568 /2/ np.sqrt(numcar)  # 0.568 is the product of a safety margin 0.8 and the RMS of 1 Vp, i.e. 0.71
        slider = (20*np.log10(wanted_gain) + self.GAINOFFSET)*10/9
        self.gui.verticalSlider_Gain.setProperty("value", float(slider))


    def create_band_thread(self):
        """pre-set gain, check some conditions. Then configure and start worker thread 'modulate_worker' for synthesis

        """
        self.gui.synthesizer_pushbutton_create.clicked.disconnect(self.create_band_thread)
        palette = self.gui.synthesizer_pushbutton_create.palette()
        self.cancel_background_color = palette.color(self.gui.synthesizer_pushbutton_create.backgroundRole())
        self.syntesisrunning = False

        # save settings to temp project
         #re-load the same project (patch bug with direct create)

        self.autosave = True
        self.save_project()
        print("save temporary project file")
        time.sleep(0.5)
        self.load_project()
        self.autosave = False
        self.gui.synthesizer_pushbutton_create.clicked.connect(self.create_band_thread)
       


        self.preset_gain()
        #if self.gui.radiobutton_AGC.isChecked():
        #TODO TODO TODO: implement AGC method and AUTO clipping repair or clipping warning
            #gain = 10**((self.gui.verticalSlider_Gain.value()/100*90 - self.GAINOFFSET)/20)

        #TODO TODO TODO: exit if no project defined
        #print("recording path received")
        #print(self.m["recording_path"])
        playlists = [[f"{path.rstrip('/')}/{file}" for file, path in zip(files, paths)] for files, paths in zip(self.readFileList, self.readFilePath)]
        cumlen = 0
        for elem in playlists:
            cumlen = cumlen + len(elem)
        if cumlen == 0:
            auxi.standard_errorbox("no playlists defined yet, cannot create anything")
            return
        self.SigActivateOtherTabs.emit("synthesizer","inactivate",["Synthesizer"])
        self.gui.progressBar_synth.setValue(0)
        self.activate_control_elements(False)
        self.logger.debug("modulate: configure modulate_worker thread et al")
        self.m["cancelflag"] = False
        modulation_depth = float(self.gui.lineEdit_modfactor.text())  # Modulation depth 
        playlists = [[f"{path.rstrip('/')}/{file}" for file, path in zip(files, paths)] for files, paths in zip(self.readFileList, self.readFilePath)]
        LO_frequency = int(np.round(self.m["LO"]*1000))
        fclow_frequency = int(np.round(float(self.gui.lineEdit_fc_low.text()))*1000)
        self.m["fclow"] = fclow_frequency
        #TODO TODO TODO: maybe correct for no carrier at frequency 0, make that correct ! subtract BW/2
        carrier_frequencies = self.m["carrierarray"] - self.m["LO"]
        existcheck = True
        while existcheck:
            options = QFileDialog.Options()
            options |= QFileDialog.DontUseNativeDialog
            output_base_name, _ = QFileDialog.getSaveFileName(self.m["QTMAINWINDOWparent"], 
                                                    "Save File", 
                                                    self.m["recording_path"],  # Standard rec path, Standardmäßig kein voreingestellter Dateiname
                                                    "wav Files (*.wav)",  # Filter for data type wav
                                                    options=options)
            if output_base_name:
                if (os.path.exists(output_base_name) or os.path.exists(output_base_name + "_0.wav")):
                    msg = QMessageBox()
                    msg.setIcon(QMessageBox.Question)
                    msg.setText("overwrite file")
                    msg.setInformativeText("you are about to overwrite an existing file. Do you really want to proceed ?")
                    msg.setWindowTitle("overwrite")
                    msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                    msg.buttonClicked.connect(self.popup)
                    msg.exec_()
                    if self.yesno == "&Yes":
                        existcheck = False
                else:
                    existcheck = False

        block_size = 2**16   # Maximum block length
        total_reclength = self.get_reclength()
        exp_num_samples = total_reclength * self.m["sample_rate"]*1000
        self.toggle = False
        self.modulate_thread = QThread(parent = self)
        self.modulate_worker = modulate_worker()
        self.modulate_worker.moveToThread(self.modulate_thread)
        self.modulate_worker.set_carrier_frequencies(carrier_frequencies)
        self.modulate_worker.set_playlists(playlists)
        self.modulate_worker.set_sample_rate(int(self.m["sample_rate"]*1000))
        self.modulate_worker.set_block_size(block_size)
        self.modulate_worker.set_cutoff_freq(self.m["audioBW"]*1000)
        self.modulate_worker.set_modulation_depth(modulation_depth)
        self.modulate_worker.set_output_base_name(output_base_name)
        self.modulate_worker.set_exp_num_samples(exp_num_samples)
        self.modulate_worker.set_logger(self.logger)
        self.modulate_worker.set_LO_freq(LO_frequency)
        self.setgain()
        self.modulate_thread.started.connect(self.modulate_worker.start_modulator)
        self.modulate_worker.SigPupdate.connect(self.PupdateSignalHandler)
        self.modulate_worker.SigMessage.connect(self.display_worker_message)
        self.modulate_worker.SigFinished.connect(self.modulate_thread.quit)
        self.modulate_worker.SigFinished.connect(lambda: print("#####>>>>>>>>>>>>>>>>>modulateworker SigFinished_arrived"))
        self.modulate_worker.SigFinished.connect(self.cleanup)
        self.modulate_worker.SigFinished.connect(self.modulate_worker.deleteLater)
        self.modulate_thread.finished.connect(self.modulate_thread.deleteLater)

        self.m["progress"] = 0
        self.m["blinkstate"] = True #TODO: not yet used
        self.m["actionlabelbg"] ="cyan" #TODO: not yet used
        self.m["blinking"] = False #TODO: not yet used

        time.sleep(0.0001)
        self.modulate_thread.start()
        if self.modulate_thread.isRunning():
            self.logger.debug("modulate: modulate_ thread started")
            self.syntesisrunning = True
        time.sleep(0.01) # wait state for worker to start up
        return(True)
    
    def display_worker_message(self,s):
        """display messages from the worker in the message window of the GUI"""
        self.gui.label_audioset_name.setText(s)
        if s.find("----") == 0:
            self.gui.label_audioset_name.setText('modulating')
            self.gui.label_audioset_name.setStyleSheet("background-color: #FFFFFF; color: black;")
        if self.toggle: 
            self.gui.label_audioset_name.setStyleSheet("background-color: #ADD8E6; color: black;")  # Blassblau (#ADD8E6)
        else:
           self.gui.label_audioset_name.setStyleSheet("background-color: #FFDAB9; color: black;")  # Blassorange (#FFDAB9)
        self.toggle = not self.toggle

    def cleanup(self):
        self.syntesisrunning = False
        self.activate_control_elements(True)
        self.SigActivateOtherTabs.emit("synthesizer","activate",[])
        auxi.standard_infobox("synthesis has been completed, files can be found in the recording path defined on the Player tab")
        self.gui.progressBar_synth.setValue(0)
        self.gui.synthesizer_pushbutton_create.setStyleSheet("background-color: lightgray; color: black;")
        self.display_worker_message('Job finished, ready for new job')

    def preset_SR_LO(self):
        """auto-define LO frequency and Rec bandwidth (= sampling rate) for pre-defined broadcasting bands on LW, MW and SW
        """
        text = self.gui.comboBox_targetSR_2.currentText()
        if text.find("LW") == 0:
            self.gui.lineEdit_LO.setText("220")
            self.gui.comboBox_targetSR.setCurrentIndex(3)
        if text.find("MW") == 0:
            self.gui.lineEdit_LO.setText("1125")
            self.gui.comboBox_targetSR.setCurrentIndex(5)
        if text.find("SW 49m") == 0:
            self.gui.lineEdit_LO.setText("6050")
            self.gui.comboBox_targetSR.setCurrentIndex(4)
        if text.find("SW 41m") == 0:
            self.gui.lineEdit_LO.setText("7325")
            self.gui.comboBox_targetSR.setCurrentIndex(3)
        if text.find("SW 31m") == 0:
            self.gui.lineEdit_LO.setText("9650")
            self.gui.comboBox_targetSR.setCurrentIndex(4)
        if text.find("SW 25m") == 0:
            self.gui.lineEdit_LO.setText("11850")
            self.gui.comboBox_targetSR.setCurrentIndex(4)
        if text.find("SW 22m") == 0:
            self.gui.lineEdit_LO.setText("13720")
            self.gui.comboBox_targetSR.setCurrentIndex(4)
        if text.find("SW 19m") == 0:
            self.gui.lineEdit_LO.setText("15450")
            self.gui.comboBox_targetSR.setCurrentIndex(5)
        self.LO_update()



    def activate_control_elements(self,value):
        """enable or disable all control elements of the tab via value
        value = True: enable
        value = False: disable
        :param: value
        :type: Boolean
        """  
        #self.gui.verticalSlider_Gain.setEnabled(value)
        self.gui.synthesizer_pushbutton_create.setEnabled(value)
        self.gui.comboBox_cur_carrierfreq.setEnabled(value)
        self.gui.pushButton_saveproject.setEnabled(value)
        self.gui.pushButton_loadproject.setEnabled(value)
        self.gui.pushButton_select_source.setEnabled(value)
        self.gui.comboBox_targetSR.setEnabled(value)
        self.gui.lineEdit_LO.setEnabled(value)

        self.gui.comboBox_targetSR_2.setEnabled(value)
        self.gui.lineEdit_fc_low.setEnabled(value)
        self.gui.lineEdit_carrierdistance.setEnabled(value)
        self.gui.lineEdit_modfactor.setEnabled(value)
        self.gui.spinBox_numcarriers.setEnabled(value)
        self.gui.lineEdit_audiocutoff_freq.setEnabled(value)
        self.gui.timeEdit_reclength.setEnabled(value)
        #self.gui.synthesizer_radioBut_Spectrum.setEnabled(value)
        self.gui.radiobutton_AGC.setEnabled(value)


    def PupdateSignalHandler(self):
        """
        update progress bar and handle other state display elements
        """
        progress = self.modulate_worker.get_progress()
        #print(f"progress: {progress}")
        combined_signal_block = self.modulate_worker.get_combined_signal_block()
        self.gui.progressBar_synth.setValue(min(100,int(np.floor(progress))))
        ts = 1/self.m["sample_rate"]/1000
        # clipping limits festlegen (Y-Werte)
        upper_limit = 0.7
        lower_limit = -0.7
        self.plot_widget.clear()
        if self.gui.synthesizer_radioBut_Spectrum.isChecked():
            self.logger.debug(f"percentage completed: {str(progress)}")
            spr = np.abs(np.fft.fft(combined_signal_block[0:min(2**16,len(combined_signal_block))]))
            N = len(spr)
            spr = np.fft.fftshift(spr)/N
            flo = self.m["LO"] - self.m["sample_rate"]/2 #+ #self.m["fclow"] - self.m["sample_rate"]*1000/2
            freq0  = np.linspace(0,self.m["sample_rate"],N)
            freq = freq0 + flo
            datax = (freq)
            self.plot_widget.setXRange(flo, freq[-1])
            self.plot_widget.setYRange(-120, 0)
            datay = 20*np.log10(spr)
            self.plot_widget.plot(datax, datay, pen=pg.mkPen('k'))

        else:
            datay = np.real(combined_signal_block[0:min(2**16,len(combined_signal_block))])
            datay = datay - np.mean(datay)
            tax = np.linspace(0,1,len(datay))
            datax = tax * ts
            self.plot_widget.setXRange(0, datax[-1])
            self.plot_widget.setYRange(-1,1)
            # clipping limits
            region = pg.LinearRegionItem(values=(lower_limit, upper_limit), orientation='horizontal')
            region.setBrush(pg.mkBrush(0, 255, 0, 30))  # pale green rectangle (RGBA: (0, 255, 0, 30) for transparency)
            self.plot_widget.addItem(region)
            upper_line = pg.InfiniteLine(pos=upper_limit, angle=0, pen=pg.mkPen('r', width=2))
            lower_line = pg.InfiniteLine(pos=lower_limit, angle=0, pen=pg.mkPen('r', width=2))
            self.plot_widget.addItem(upper_line)
            self.plot_widget.addItem(lower_line)
            self.plot_widget.plot(datax, datay, pen=pg.mkPen('k'))
            #print(f"mean value: {np.mean(datay)}")

        self.showRFdata()

    def save_project(self):
        """_save current settings and all playlists to a project file (*.proj) via intermediate dictionary pr
        *.proj files are have yaml format

        :param: none
        :returns: none
        : raises: none

        """
        pr = {}
        pr["projectdata"] = {}
        pr["projectdata"]["readFilePath"] = self.readFilePath
        pr["projectdata"]["readFileList"] = self.readFileList
        pr["projectdata"]["numcarriers"] = self.m["numcarriers"]
        pr["projectdata"]["carrier_distance"] = self.m["carrier_distance"]
        pr["projectdata"]["carrier_f_low"] = self.m["fc_low"]
        pr["projectdata"]["LO"] = self.m["LO"]
        pr["projectdata"]["audio_BW"] = self.m["audioBW"]
        #pr["projectdata"]["sample_rate"] = self.m["sample_rate"]
        pr["projectdata"]["current_listdir"] = self.current_listdir
        pr["projectdata"]["targetSR_index"] = self.gui.comboBox_targetSR.currentIndex()
        pr["projectdata"]["presetband_index"] = self.gui.comboBox_targetSR_2.currentIndex()
        #pr["projectdata"]["preset_time"] = 
        #TODO TODO TODO: add all settings to be saved:
        #self.comboBox_targetSR_2.setCurrentIndex(###)
        pr["projectdata"]["modfactor"] = self.gui.lineEdit_modfactor.text()
        #pr["projectdata"]["carrier_low"] = self.gui.lineEdit_fc_low.text()
        #Target filename
        qtimeedit = self.gui.timeEdit_reclength
        time_from_qtimeedit = qtimeedit.time()
        pr["projectdata"]["preset_time"] = [time_from_qtimeedit.hour(), time_from_qtimeedit.minute(), time_from_qtimeedit.second()]
        if not self.autosave:
            filename = self.save_file_dialog()
        else:
            filename = "temp.proj"
        stream = open(filename, "w") ###replace project.yaml with filename
        yaml.dump(pr["projectdata"], stream)
        stream.close()

    def load_project(self):
        """_load project file (*.proj) and read the settings of that project to dictionary pr
        fill playlists and re-initialize all settings according to loaded project.
        *.proj files are have yaml format

        :param: none
        :returns: none
        : raises: none

        """
        pr = {}
        pr["projectdata"] = {}
        if not self.autosave:
            filename = self.load_file_dialog()
        else:
            filename = "temp.proj"
        try:
            stream = open(filename, "r")
            pr["projectdata"] = yaml.safe_load(stream)
            stream.close()
            #self.m["sample_rate"] = pr["projectdata"]["sample_rate"]
            self.readFileList = pr["projectdata"]["readFileList"]
            self.readFilePath = pr["projectdata"]["readFilePath"]
            self.m["LO"] = pr["projectdata"]["LO"]
            #self.oldFileList = pr["projectdata"]["readFileList"]
            self.oldFileList = copy.deepcopy(pr["projectdata"]["readFileList"])
            self.gui.lineEdit_fc_low.setText(str(pr["projectdata"]["carrier_f_low"]))
            self.gui.lineEdit_LO.setText(str(pr["projectdata"]["LO"]))
            self.m["audioBW"]= pr["projectdata"]["audio_BW"]
            self.gui.lineEdit_audiocutoff_freq.setText(str(pr["projectdata"]["audio_BW"]))
            self.gui.lineEdit_carrierdistance.setText(str(pr["projectdata"]["carrier_distance"]))
            self.m["carrier_distance"] = pr["projectdata"]["carrier_distance"]
            self.m["numcarriers"] = pr["projectdata"]["numcarriers"]
            #self.gui.spinBox_numcarriers.valueChanged.disconnect(self.freq_carriers_update)
            self.gui.spinBox_numcarriers.valueChanged.disconnect(self.on_value_changed)
            self.gui.spinBox_numcarriers.editingFinished.disconnect(self.on_editing_finished)
            self.gui.spinBox_numcarriers.setProperty("value", self.m["numcarriers"])
            #self.gui.spinBox_numcarriers.valueChanged.connect(self.freq_carriers_update)
            self.gui.spinBox_numcarriers.valueChanged.connect(self.on_value_changed)
            self.gui.spinBox_numcarriers.editingFinished.connect(self.on_editing_finished)            
            self.m["carrier_ix"] = 0
            self.gui.comboBox_cur_carrierfreq.setCurrentIndex(self.m["carrier_ix"])
            #######preset_time = QTime(00, 30, 00) 
            aux_preset_time = pr["projectdata"]["preset_time"]
            preset_time = QTime(aux_preset_time[0],aux_preset_time[1],aux_preset_time[2]) 
            self.gui.timeEdit_reclength.setTime(preset_time)
            self.m["fc_low"] = pr["projectdata"]["carrier_f_low"]
            self.gui.comboBox_targetSR.setCurrentIndex(pr["projectdata"]["targetSR_index"])
            self.gui.comboBox_targetSR_2.setCurrentIndex(pr["projectdata"]["presetband_index"])
            self.gui.lineEdit_modfactor.setText(str(pr["projectdata"]["modfactor"])) 
            self.load_index = True
            try:
                self.fillplaylist()
            except:
                auxi.standard_errorbox("playlist is inconsistent with other settings, project file invalid, check project file")
                return 
            self.current_listdir = pr["projectdata"]["current_listdir"]
            self.fillsourcelist(self.current_listdir)
            self.RecBW_update()
            self.LO_update()
            self.carrierdistance_update()
            self.audioBW_update()
            self.fc_low_update()
            self.load_index = False

            #TODO TODO TODO load all remaining settings
            #self.comboBox_targetSR_2.setCurrentIndex(###) Preset menu
            #modulation factor

            #Target filename

        except:
            self.logger.error('cannot load project yaml file (proj files)')

    def save_file_dialog(self):
        # Erstellen des Datei-Speicher-Dialogs
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog  # Verwende das Qt-eigene Dialogfenster
        file_name, _ = QFileDialog.getSaveFileName(self.m["QTMAINWINDOWparent"], 
                                                   "Save File", 
                                                   "*.proj",  # Standardmäßig kein voreingestellter Dateiname
                                                   "proj Files (*.proj);;All Files (*)",  # Filter für Dateitypen
                                                   options=options)
        if file_name:
            return file_name
        else:
            return None

    def load_file_dialog(self):
        self.standardpath = os.getcwd()  #TODO TODO: take from core module via rxh; on file open core sets that to:
        #        self.SigRelay.emit("cm_all_",["standardpath",self.standardpath]); 
        ########### SET DEDICATED PROJECT FOLDER !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

        filters = "project files (*.proj);;all files (*)"
        selected_filter = "project files (*.proj)"
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog  # Verwende das Qt-eigene Dialogfenster
        file_name, _ = QFileDialog.getOpenFileName(self.m["QTMAINWINDOWparent"], 
                                                "Open project File", 
                                                self.standardpath,  # Standardmäßig kein voreingestellter Dateiname
                                                filters,  # Filter für Dateitypen
                                                selected_filter,
                                                options=options)
        if file_name:
            return file_name
        else:
            return None


    def get_wav_info(self,wav_file):
        """opens wav header of the sepcified file and reads out important information
        returns a dict with the keys:
         {
                'duration_seconds': duration,
                'n_channels': n_channels,
                'framerate': framerate,
                'sampwidth_bytes': sampwidth,
                'data_format': data_format
        }
        Example:
        file_path = 'your_audio_file.wav'
        wav_info = get_wav_info(file_path)

        print(f"playtime: {wav_info['duration_seconds']} Sekunden")
        print(f"sampling rate: {wav_info['framerate']} Hz")
        print(f"Data format: {wav_info['data_format']}")
        
        :param: wav_file
        :type: str
        :returns: dictionary with the information
        :rtype: dict
        """
        # open WAV-file
        with open(wav_file, 'rb') as file:
            # Lese den RIFF-Header (die ersten 12 Bytes)
            riff_header = file.read(12)
            
            # Lese den fmt-Chunk-Header (die nächsten 8 Bytes)
            fmt_chunk_header = file.read(8)
            
            # Extrahiere die Subchunk-ID und die Größe des fmt-Chunks
            subchunk_id = fmt_chunk_header[:4].decode('ascii')
            subchunk_size = struct.unpack('<I', fmt_chunk_header[4:])[0]
            
            # Lese den fmt-Chunk basierend auf der Größe
            fmt_chunk = file.read(subchunk_size)
            
            # Entpacke das Audioformat aus dem fmt-Chunk
            audio_format = struct.unpack('<H', fmt_chunk[:2])[0]

            # Mapping des Audioformats zu einer menschlich lesbaren Bezeichnung
            if audio_format == 1:
                data_format = f"PCM{8 * struct.unpack('<H', fmt_chunk[2:4])[0]}"
            elif audio_format == 3:
                sampwidth = struct.unpack('<H', fmt_chunk[2:4])[0] // 8
                if sampwidth == 4:
                    data_format = "Float32"
                elif sampwidth == 8:
                    data_format = "Float64"
                else:
                    data_format = "Unknown Float Format"
            else:
                data_format = f"Unknown Format Code: {audio_format}"

            # Anzahl der Kanäle, Abtastrate und weitere Informationen
            n_channels = struct.unpack('<H', fmt_chunk[2:4])[0]
            framerate = struct.unpack('<I', fmt_chunk[4:8])[0]
            sampwidth = struct.unpack('<H', fmt_chunk[2:4])[0] // 8

        # Nutze die `wave`-Bibliothek, um weitere Informationen zu extrahieren
        with wave.open(wav_file, 'rb') as wav:
            n_frames = wav.getnframes()
            duration = n_frames / float(framerate)            # return info
            
            return {
                'duration_seconds': duration,
                'n_channels': n_channels,
                'framerate': framerate,
                'sampwidth_bytes': sampwidth,
                'data_format': data_format
            }

    def get_reclength(self):
        qtimeedit = self.gui.timeEdit_reclength
        time_from_qtimeedit = qtimeedit.time()       
        # Zeit aus dem QTimeEdit-Objekt zu aktuellen Datum hinzufügen
        hours = time_from_qtimeedit.hour()
        minutes = time_from_qtimeedit.minute()
        seconds = time_from_qtimeedit.second()
        total_reclength = hours*3600 + minutes * 60 + seconds
        return total_reclength

    def show_fillprogress(self,duration):
        """show completion percentage of the current carrier track

        """
        total_reclength = self.get_reclength()
        progfract = duration/total_reclength * 100

        self.gui.progressBar_fillPlaylist.setValue(min(100,int(np.floor(progfract))))
        if progfract > 100:
            self.gui.progressBar_fillPlaylist.setStyleSheet("QProgressBar::chunk "
                    "{"
                        "background-color: red;"
                    "}")
        elif progfract > 90:
            self.gui.progressBar_fillPlaylist.setStyleSheet("QProgressBar::chunk "
                    "{"
                        "background-color: yellow;"
                    "}")           
        else:
            self.gui.progressBar_fillPlaylist.setStyleSheet("QProgressBar::chunk "
                    "{"
                        "background-color: green;"
                    "}")

    def carrier_ix_changed(self):
        """_slot function of comboBox_cur_carrierfreq
        get corresponding carrier index and call playlist update
        """
        self.m["carrier_ix"] = self.gui.comboBox_cur_carrierfreq.currentIndex()
        
        #print(f"carrier index changed to: {self.m['carrier_ix']}")
        self.fillplaylist()

    def fillplaylist(self):
        """update playlist of carrier with index self.m['carrier_ix']; clear old list and write new one
         :param: none
         :returns: none 
         """
        try:
            self.gui.listWidget_playlist.model().rowsInserted.disconnect(self.playlist_update_delayed)
        except:
            pass

        self.gui.listWidget_playlist.clear()
        ix = 0
        try:
            for x in self.readFileList[self.m["carrier_ix"]]:
                item = QtWidgets.QListWidgetItem()
                self.gui.listWidget_playlist.addItem(item)
                _item = self.gui.listWidget_playlist.item(ix)
                _item.setText(x)
                fnt = _item.font()
                fnt.setPointSize(11)
                _item.setFont(fnt)
                ix += 1
                #self.current_listdir = self.readFileList[self.m["carrier_ix"]]
        except:
            pass
        duration = self.show_playlength()
        self.show_fillprogress(duration)
        self.gui.listWidget_playlist.model().rowsInserted.connect(self.playlist_update_delayed)

    def show_context_menu(self, position):
        context_menu = QMenu(self.gui.listWidget_playlist)
        delete_action = context_menu.addAction("Delete")
        delete_action.triggered.connect(self.delete_selected_items)
        context_menu.exec_(self.gui.listWidget_playlist.viewport().mapToGlobal(position))

    def delete_selected_items(self):
        for item in self.gui.listWidget_playlist.selectedItems():
            self.gui.listWidget_playlist.takeItem(self.gui.listWidget_playlist.row(item))


    def on_rows_moved(self, parent, start, end, destinationParent, destinationRow):
        # calculate new position of the shifted items
        for i in range(start, end + 1):
            if destinationRow > start:
                new_index = destinationRow + (i - start) - 1
            else:
                new_index = destinationRow + (i - start)

            element = self.gui.listWidget_playlist.item(new_index).text()
            #print(f"Element '{element}' shifted from {i} to {new_index}")

    def show_playlength(self):
        """_update progress bar for total playlength for carrier with index [self.m['carrier_ix']
        """
        ix = 0
        duration = 0
        for x in self.readFileList[self.m["carrier_ix"]]:
            try:
                file_path =  self.readFilePath[self.m["carrier_ix"]][ix] + "/" + x
            except:
                #print(f"show readFilePath index out of range at index: {self.m['carrier_ix']} [{ix}]")
                return duration
            if not len(self.readFilePath[self.m["carrier_ix"]][ix] + x) < 1:
                #wav_info = self.get_wav_info(file_path)
                #duration += wav_info['duration_seconds']
                #if duration Blödsinn, das kann passieren !
                a = sf.SoundFile(file_path, 'r') #TODO: Umstellen auf mp3: 
                duration += a.frames/a.samplerate
                a.close()

            else:
                print("NNNNNNNNNN")
            ix += 1

        # print(f"Spieldauer: {wav_info['duration_seconds']} Sekunden")
        # print(f"Anzahl der Kanäle: {wav_info['n_channels']}")
        # print(f"Abtastrate: {wav_info['framerate']} Hz")
        # print(f"Sample-Breite: {wav_info['sampwidth_bytes']} Bytes")
        # print(f"Datenformat: {wav_info['data_format']}")
        #print(f"full duration of this carrier track: {duration}")
        return duration
        #TODO TODO: write progress bar update
        #for x in self.readFileList[self.m["carrier_ix"]]:
        #   open file
        #   read fileheader with test = WAVheader_tools.get_sdruno_header(self,self.m["f1"],'audio')
        #   close file
        #   calculate playtime from filesize and header info
        #   add to playtime
        #   set progress bar value and color on overtime
        #

    def carrierselect_update(self):
        #generate combobox entry list
        carrier_array = np.arange(self.m["fc_low"], self.cf_HI+1, self.m["carrier_distance"])
        carrierselector = carrier_array.tolist()
        self.gui.comboBox_cur_carrierfreq.clear()
        for cf in carrierselector:
            self.gui.comboBox_cur_carrierfreq.addItem(str(cf))
        self.m["carrierarray"] = carrier_array

    def on_value_changed(self, value):
        # Reagiere sofort, wenn der Wert geändert wird und die Spinbox nicht den Fokus hat
        print(f"###########Focus unlear")
        if self.gui.spinBox_numcarriers.value() != self.previous_value:
            print(f"Wert durch Pfeiltasten geändert: {value}")
            # Aktualisiere den vorherigen Wert
            self.previous_value = value
            self.freq_carriers_update()

    def on_editing_finished(self):
        self.freq_carriers_update()
        print("on editing finished")

    def freq_carriers_update(self):
#         Vergrößern: append differenz zu vorher mal self.readFileList mit []
# 	Verkleinern: ermittle differenz zu vorher letzte self.readFileList Elemente
# Wenn letzte self.readFileList[-1] nicht empty  Warnug, dass alle bis auf die verbleibenden Lisetneiträge gelöscht werde, Proceed ? Cancel ?
# Wenn bestätigt:
# 			Delete letzte self.readFileList Elemente

        self.numcarriers_old = self.m["numcarriers"]
        numcar = self.gui.spinBox_numcarriers.value()
        valid, errortext = self.validate_params()
        if not valid:
            self.gui.spinBox_numcarriers.valueChanged.disconnect(self.on_value_changed)
            self.gui.spinBox_numcarriers.editingFinished.disconnect(self.on_editing_finished)
            #self.gui.spinBox_numcarriers.editingFinished.disconnect(self.freq_carriers_update)
            auxi.standard_errorbox(errortext)
            self.gui.spinBox_numcarriers.setProperty("value", self.numcarriers_old)
            time.sleep(0.1)
            #self.m["numcarriers"] = self.numcarriers_old
            #self.gui.spinBox_numcarriers.editingFinished.connect(self.freq_carriers_update)
            self.gui.spinBox_numcarriers.valueChanged.connect(self.on_value_changed)
            self.gui.spinBox_numcarriers.editingFinished.connect(self.on_editing_finished)
            return False

        if numcar > self.numcarriers_old:
            #extend list
            curlen = self.numcarriers_old
            delta = numcar - self.numcarriers_old
            for i in range(delta):
                self.readFileList.append([])
                self.readFileList[curlen + i] = [] #TODO TODO TODO: CHECK: voher hatte ich -1 
                self.oldFileList.append([])
                self.oldFileList[curlen + i] = []
                self.readFilePath.append([])
                self.readFilePath[curlen + i] = []
        elif numcar < self.numcarriers_old:
            #TODO TODO TODO TESTING ! delete n list elements and ask if that is wanted
            delta = self.numcarriers_old - numcar
            if not self.load_index:
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Question)
                msg.setText("Warning")
                msg.setInformativeText(f"you are about to delete the last {delta} carriers. The corresponding playlists will be removed. Do you want to proceed")
                msg.setWindowTitle("Delete carriers")
                msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                msg.buttonClicked.connect(self.popup)
                msg.exec_()

                if self.yesno == "&Yes":
                    for i in range(delta):
                        del self.readFileList[self.numcarriers_old - 1 - i]
                        del self.oldFileList[self.numcarriers_old - 1 - i]
                        del self.readFilePath[self.numcarriers_old - 1 - i]
                else:
                    #self.gui.spinBox_numcarriers.editingFinished.disconnect(self.freq_carriers_update)
                    self.gui.spinBox_numcarriers.valueChanged.disconnect(self.on_value_changed)
                    self.gui.spinBox_numcarriers.editingFinished.disconnect(self.on_editing_finished)
                    self.gui.spinBox_numcarriers.setProperty("value", self.numcarriers_old)
                    time.sleep(0.1)
                    #self.gui.spinBox_numcarriers.editingFinished.connect(self.freq_carriers_update)
                    self.gui.spinBox_numcarriers.valueChanged.connect(self.on_value_changed)
                    self.gui.spinBox_numcarriers.editingFinished.connect(self.on_editing_finished)
                    return False
            else:
                for i in range(delta):
                    del self.readFileList[self.numcarriers_old - 1 - i]
                    del self.oldFileList[self.numcarriers_old - 1 - i]
                    del self.readFilePath[self.numcarriers_old - 1 - i]

        self.m["numcarriers"] = numcar  
        fc_low = float(self.gui.lineEdit_fc_low.text())
        # self.c_step = float(self.gui.lineEdit_carrierdistance.text())
        # self.cf_HI = fc_low + (self.m["numcarriers"] - 1) * self.c_step
        self.cf_HI = fc_low + (self.m["numcarriers"] - 1) * self.m["carrier_distance"]
        self.carrierselect_update()

    def popup(self,i):
        """
        """
        self.yesno = i.text()

    def isfloat(self,num):
        try:
            float(num)
            return True
        except ValueError:
            auxi.standard_errorbox("invalid characters, must be numeric float value !")
            return False

    def isint(self,num):
        try:
            int(num)
            return True
        except ValueError:
            auxi.standard_errorbox("invalid characters, must be numeric integer value !")
            return False

    def isnumeric(self,s):
        # Versuche, das deutsche Locale zu verwenden (Komma als Dezimaltrennzeichen)
        locale.setlocale(locale.LC_NUMERIC, 'de_DE.UTF-8')  # Für deutsches Format
        try:
            a = locale.atof(s)  # Parst eine Zahl mit deutschem Format
            return True, ""
        except ValueError:
            pass  # Wenn es nicht im deutschen Format ist, versuche es im englischen Format

        # Zurück zum englischen Locale für das Standardformat (Punkt als Dezimaltrennzeichen)
        locale.setlocale(locale.LC_NUMERIC, 'en_US.UTF-8')
        try:
            a = locale.atof(s)  # Parst eine Zahl mit englischem Format
            return True, ""
        except ValueError:
            errortext = "value is not numeric"
            return False, errortext

    def validate_params(self):
        """_validates certain parameter conditions which must be fulfilled for meaningful settings,
        e.g. carrier distance > 2* Audio-BW_
        :return: valid: True if all conditions met, else False
        :rtype: boolean
        :return: errortext: string specifying the type of violation
        :rtype: str
        """
        audioBW = float(self.gui.lineEdit_audiocutoff_freq.text())
        carrier_distance = float(self.gui.lineEdit_carrierdistance.text())
        sample_rate = int(self.gui.comboBox_targetSR.currentText())
        f_LO = float(self.gui.lineEdit_LO.text())
        fc_low = float(self.gui.lineEdit_fc_low.text())
        numcarriers = self.gui.spinBox_numcarriers.value()
        modfactor = float(self.gui.lineEdit_modfactor.text())
        if (carrier_distance < 2*audioBW):# and not self.load_index: ????
            self.rule_viol = True
            errortext = "carrier spacing is less than 2*audio bandwidth, this is not allowed, please either increase carrier spacing or reduce audio bandwidth"
            #self.gui.lineEdit_carrierdistance.setText(str(self.m["carrier_distance"]))
            #self.gui.lineEdit_audiocutoff_freq.setText(str(self.m["audioBW"]))
            print("return false from validate")
            return False, errortext
        #Fclow + numcarriers * DeltaC <  LO + BW/2 - AudioBW
        highlimit = f_LO + sample_rate/2 - audioBW
        lowlimit = f_LO - sample_rate/2 + audioBW
        violate_low = fc_low < lowlimit
        violate_high = fc_low + carrier_distance * numcarriers > highlimit
        if violate_low or violate_high :# and not self.load_index: ????
            self.rule_viol = True
            #Fclow > f_LO – samplerate/2 + AudioBW 
            if violate_low:
                errortext = "lowest carrier frequency is below the lowest edge of the band ()" + str(lowlimit) +"), please correct one or more of the following parameters: LO frequency, Rec-Bandwidth, lowest carrier frequency, carrier distance or audio cutoff frequency"
            if violate_high:
                errortext = "highest carrier frequency (" + str(fc_low + carrier_distance * numcarriers) + ") is above the highest edge of the band " + str(highlimit) +", please correct one or more of the following parameters: LO frequency, Rec-Bandwidth, lowest carrier frequency, carrier distance, number of carriers or audio cutoff frequency"
            if violate_low and violate_high:
                errortext = "lowest and highest carrier frequency are out of the band. Low limit: " + str(lowlimit) + ", please correct one or more of the following parameters: LO frequency, Rec-Bandwidth, lowest carrier frequency, carrier distance, number of carriers or audio cutoff frequency"

            print("return false from validate")
            return False, errortext
        if modfactor < 0.01 or modfactor > 1:
            errortext = "Modulation factor out of range, value must be >= 0.01 and <= 1"
            return False, errortext
        return True, ""

    def RecBW_update(self):
        """slot function for the recording Bandwidth (=SR) combobox; sets the model parameter self.m['sample_rate'] and triggers validation"""
        RecBW = int(self.gui.comboBox_targetSR.currentText()) #TODO: redundant ?
        valid, errortext = self.validate_params()
        if not valid:
            auxi.standard_errorbox(errortext)
            self.gui.comboBox_targetSR.setCurrentIndex(self.m["SR_currindex"])
            return False
        self.m["sample_rate"] = int(self.gui.comboBox_targetSR.currentText())
        self.m["SR_currindex"] = self.gui.comboBox_targetSR.currentIndex()
        #self.freq_carriers_update()

    def audioBW_update(self):
        """slot function for the audio Bandwidth line_edit; sets the model parameter m['audioBW'] and triggers validation"""
        audioBW = self.gui.lineEdit_audiocutoff_freq.text()
        if not self.isnumeric(audioBW):
            auxi.standard_errorbox("invalid characters, must be numeric value !")
            self.gui.lineEdit_audiocutoff_freq.setText(str(self.m["audioBW"]))
            return False
        # else: TODO: remove after tests
        #     self.m["audioBW"] = float(self.gui.lineEdit_audiocutoff_freq.text())
        if (float(audioBW) < 2.5) or (float(audioBW) > 16):
            auxi.standard_errorbox("audio bandwidth outside the range 2.5 - 16 kHz. Value must be in this interval, please cahnge")
            self.gui.lineEdit_audiocutoff_freq.setText(str(self.m["audioBW"]))
            return False
        valid, errortext = self.validate_params()
        if not valid:
            auxi.standard_errorbox(errortext)
            self.gui.lineEdit_audiocutoff_freq.setText(str(self.m["audioBW"]))
            return False
        self.m["audioBW"] = float(self.gui.lineEdit_audiocutoff_freq.text())
        self.freq_carriers_update()
        #print(f"carrier spacing: {self.m['audioBW']}")

    def LO_update(self):
        """slot function for the LO frequency line_edit; sets the model parameter m['LO'] and triggers validation"""
        cf_LO = self.gui.lineEdit_LO.text()
        if not self.isnumeric(cf_LO):
            auxi.standard_errorbox("invalid characters, must be numeric value !")
            self.gui.lineEdit_LO.setText(str(self.m["LO"]))
            return False
        valid, errortext = self.validate_params()
        if not valid:
            auxi.standard_errorbox(errortext)
            self.gui.lineEdit_LO.setText(str(self.m["LO"]))
            return False
        self.m["LO"] = float(self.gui.lineEdit_LO.text())
        self.freq_carriers_update()

    def modfactor_update(self):
        """slot function for the modulation factor line_edit; sets the model parameter m['modfactor'] and triggers validation"""
        self.gui.lineEdit_modfactor.editingFinished.disconnect(self.modfactor_update)
        modfactor = self.gui.lineEdit_modfactor.text()
        if not self.isnumeric(modfactor):
            auxi.standard_errorbox("invalid characters in modulation factor, must be numeric value !")
            self.gui.lineEdit_modfactor.setText(str(self.m["modfactor"]))
            self.gui.lineEdit_modfactor.editingFinished.connect(self.modfactor_update)
            return False
        valid, errortext = self.validate_params()
        if not valid:
            auxi.standard_errorbox(errortext)
            self.gui.lineEdit_modfactor.setText(str(self.m["modfactor"]))
            self.gui.lineEdit_modfactor.editingFinished.connect(self.modfactor_update)
            return False
        self.m["modfactor"] = float(self.gui.lineEdit_modfactor.text())
        #self.freq_carriers_update()
        self.gui.lineEdit_modfactor.editingFinished.connect(self.modfactor_update)

    def fc_low_update(self):
        """slot function for the low carrier frequency line_edit; sets the model parameter m['fc_low'] and triggers validation"""
        #self.gui.lineEdit_fc_low.setText(str(self.cf_LO)) TODO: remove self.cf_LO
        fc_low = self.gui.lineEdit_fc_low.text()
        if not self.isnumeric(fc_low):
            auxi.standard_errorbox("invalid characters, must be numeric value !")
            self.gui.lineEdit_fc_low.setText(str(self.m["fc_low"]))
            return False
        valid, errortext = self.validate_params()
        if not valid:
            auxi.standard_errorbox(errortext)
            self.gui.lineEdit_fc_low.setText(str(self.m["fc_low"]))
            return False
        self.m["fc_low"] = float(self.gui.lineEdit_fc_low.text())
        self.freq_carriers_update()
        #print(f"carrier spacing: {self.m['fc_low']}")

    def carrierdistance_update(self):
        """slot function for the carrier distance line_edit; sets the model parameter m["carrier_distance"] and triggers validation"""
        self.gui.lineEdit_carrierdistance.editingFinished.disconnect(self.carrierdistance_update)
        old_carrierdistance = self.m["carrier_distance"]
        carrier_delta = self.gui.lineEdit_carrierdistance.text()
        if not self.isnumeric(carrier_delta):
            auxi.standard_errorbox("invalid characters, must be numeric float value !")
            self.logger.error("plot_res_spectrum: wrong format of carrier distance")
            self.gui.lineEdit_carrierdistance.setText(str(self.m["carrier_distance"]))
            self.gui.lineEdit_carrierdistance.editingFinished.connect(self.carrierdistance_update)
            return False
        # if float(carrier_delta) < 0.1: #TODO: redundant, carrier_delta must be > 2*audioBW, audioBW must be > 2.5
        #     auxi.standard_errorbox("invalid carrier spacing, must be numeric float value > 0.1!")
        #     self.logger.error("plot_res_spectrum: wrong value of carrier distance")
        #     self.gui.lineEdit_carrierdistance.setText(str(self.m["carrier_distance"]))
        #     return False
        valid, errortext = self.validate_params()
        if not valid:
            auxi.standard_errorbox(errortext)
            self.gui.lineEdit_carrierdistance.setText(str(old_carrierdistance))
            self.gui.lineEdit_carrierdistance.editingFinished.connect(self.carrierdistance_update)
            return False
                
        self.m["carrier_distance"] = float(self.gui.lineEdit_carrierdistance.text())
        self.freq_carriers_update()
        self.load_index = False
        self.gui.lineEdit_carrierdistance.editingFinished.connect(self.carrierdistance_update)
        #print(f"carrier spacing: {self.m['carrier_distance']}")
        return True
    
    def select_tree(self):
        """
        initiates buildup of file selection tree
        :param : none
        :raises [ErrorType]:none
        :returns: none
        """  
        self.gui.pushButton_select_source.clicked.disconnect(self.select_tree)
        root_directory = QFileDialog.getExistingDirectory(self.m["QTMAINWINDOWparent"], "Please chose source file directory", self.default_directory)
        if root_directory:
            self.fillsourcelist(root_directory)
            self.m["metadata"]["last_audiosource_path"] = root_directory
            stream = open("config_wizard.yaml", "w")
            yaml.dump(self.m["metadata"], stream)
            stream.close()
        self.gui.pushButton_select_source.clicked.connect(self.select_tree)


    def add_children(self, parent, directory):
        for name in QDir(directory).entryList(QDir.NoDotAndDotDot | QDir.AllDirs):
            path = QDir(directory).absoluteFilePath(name)
            child = QTreeWidgetItem(parent, [name])
            child.setData(0, Qt.UserRole, path)
            self.add_children(child, path)

    # def on_tree_item_clicked(self, item, column):
    #     path = item.data(0, Qt.UserRole)
    #     #self.gui.listWidget_playlist.clear()
    #     for name in QDir(path).entryList(QDir.NoDotAndDotDot | QDir.Files):
    #         self.gui.listWidget_playlist.addItem(name)

    def fillsourcelist(self, rootdir):
        self.gui.listWidget_sourcelist.clear()
        item = QtWidgets.QListWidgetItem()
        self.gui.listWidget_sourcelist.addItem(item)
        ix = 0
        for x in os.listdir(rootdir):
            #if x.endswith(".wav"):
            #TODO: Umstellen auf mp3: 
            if x.endswith(".wav") or x.endswith(".mp3"):
                if True: #x != (self.m["my_filename"] + self.m["ext"]): #TODO: obsolete old form when automatically loading opened file to playlist
                    _item = self.gui.listWidget_sourcelist.item(ix)
                    _item.setText(x)
                    fnt = _item.font()
                    fnt.setPointSize(11)
                    _item.setFont(fnt)
                    item = QtWidgets.QListWidgetItem()
                    self.gui.listWidget_sourcelist.addItem(item)
                    ix += 1
                    self.current_listdir = rootdir

    def playlist_update_delayed(self,dum,first,last):
        #print(f"playlist_update, signal addrow: first ix: {first}, last ix: {last}")
        QTimer.singleShot(0, self.playlist_update)

    def playlist_update(self):
        """_currently loaded playlist in self.gui.listWidget_playlist is bering transferred 
        to the central list of playlists self.readFileList[self.m["carrier_ix"]]. Then playlist_purge()
        is called
        """
        self.gui.listWidget_playlist.model().rowsInserted.disconnect(self.playlist_update_delayed)
        try:
            self.oldFileList[self.m["carrier_ix"]] = copy.deepcopy(self.readFileList[self.m["carrier_ix"]])
            #TODO TODO TODO: Bei Indexerhöhung muss ein dummy self.oldFileList[self.m["carrier_ix"]] mit dem erhöhten Index angelegt werden, sonst stürzt später due diff-Methode in purge ab
        except:
            self.oldFileList = []

        self.readFileList[self.m["carrier_ix"]] = [self.gui.listWidget_playlist.item(i).text() for i in range(self.gui.listWidget_playlist.count())]
        self.playlist_purge()
        duration = self.show_playlength()
        self.show_fillprogress(duration)
        self.gui.listWidget_playlist.model().rowsInserted.connect(self.playlist_update_delayed)
        #print("playlist_update")
        # try:
        #     for file in readFileList:
        #         with open(file) as lstf:
        #             filesRead = lstf.read()
        #             print(filesRead)
        #             # return(filesReaded)

        # except Exception as e:
        #     print("the selected file is not readable because :  {0}".format(e)) 

    def playlist_purge(self):
        """_update path information in self.readFilePath for the corresponding readFileList at index  self.m['carrier_ix']
        """
        ix_diff = self.find_first_difference(self.oldFileList[self.m["carrier_ix"]] , self.readFileList[self.m["carrier_ix"]] )
        try:
            if len(self.readFileList[self.m["carrier_ix"]] ) <= len(self.oldFileList[self.m["carrier_ix"]] ):
                self.readFilePath[self.m["carrier_ix"]] = self.delete_at_index(self.readFilePath[self.m["carrier_ix"]], ix_diff)
            else:
                self.readFilePath[self.m["carrier_ix"]] = self.insert_or_append(self.readFilePath[self.m["carrier_ix"]], ix_diff, self.current_listdir)
            #print(f"playlist purge: change index: {ix_diff}, playlist: {self.readFileList[self.m['carrier_ix']] }, pathlist: {self.readFilePath[self.m['carrier_ix']]}")
        except:
            print("playlist purge: no difference, no action")

    def insert_or_append(self,pathlist, ix, element):

        if ix < len(pathlist):
            pathlist.insert(ix, element)
        else:
            pathlist.append(element)
        return pathlist

    def delete_at_index(self,pathlist, ix):
        if 0 <= ix < len(pathlist):
            del pathlist[ix]
        return pathlist

    def find_first_difference(self, list1, list2):
        min_length = min(len(list1), len(list2))

        for i in range(min_length):
            if list1[i] != list2[i]:
                return i

        if len(list1) != len(list2):
            return min_length

        return None  # Die Listen sind identisch
    
    def rxhandler(self,_key,_value):
        """
        handles remote calls from other modules via Signal SigRX(_key,_value)
        :param : _key
        :type : str
        :param : _value
        :type : object
        :raises [ErrorType]: [ErrorDescription]
        :return: none
        :rtype: none
        """
        if _key.find("cm_synthesizer") == 0 or _key.find("cm_all_") == 0:
            #set mdl-value
            self.m[_value[0]] = _value[1]
            if _value[0] == "recording_path":
                print("recording path received")
                print(_value)
                print(self.m["recording_path"])
        if _key.find("cui_synthesizer") == 0:
            _value[0](_value[1]) #STILL UNCLEAR
        if _key.find("cexex_synthesizer") == 0  or _key.find("cexex_all_") == 0:
            if  _value[0].find("updateGUIelements") == 0:
                self.updateGUIelements()
            if  _value[0].find("reset_GUI") == 0:
                self.reset_GUI()
            if  _value[0].find("logfilehandler") == 0:
                self.logfilehandler(_value[1])
            if  _value[0].find("timertick") == 0:
                    if self.syntesisrunning:
                        self.blinkstate = self.blinksynth(self.blinkstate)
                        #self.PupdateSignalHandler()


    def logfilehandler(self,_value):
        if _value is False:
            self.logger.debug("abstract module: INACTIVATE LOGGING")
            self.logger.setLevel(logging.ERROR)
        else:
            self.logger.debug("abstract module: REACTIVATE LOGGING")
            self.logger.setLevel(logging.DEBUG)

    def blinksynth(self,state):
        """
        let create button blink
        """
        if state:
            self.gui.synthesizer_pushbutton_create.setStyleSheet("background-color: " + self.cancel_background_color.name() + "; color: black;")
        else:
            self.gui.synthesizer_pushbutton_create.setStyleSheet("background-color: lightblue; color: black;")
        state = not state
        return state


    def updateGUIelements(self):
        """
        updates GUI elements , usually triggered by a Signal SigTabsUpdateGUIs to which 
        this method is connected in the __main__ of the core module
        :param : none
        :type : none
        :raises [ErrorType]: [ErrorDescription]
        :return: flag False or True, False on unsuccessful execution
        :rtype: Boolean
        """
        #print("synthesizer: updateGUIelements")
        #self.gui.DOSOMETHING

    def reset_GUI(self):
        pass

#TODO: 
# - Preset band Funktionen einbauen
# - im alten Synthesizer: jeder Carrier muss ein wav-File mit voller Spiellänge haben
#       nun wanted: Jeder Carrier hat eine eigene Playlist mit den vollen Pfadangaben aller Files
#   (1) Jede Playlist ist indiziert mit einem Index entsprechend dem Carrier, der gerade eingestellt ist; ein Label für die aktive Playlist wird irgendwo angezeigt
#   (2) Jede Playlist hat auch eine pathlist assoziiert, in der die Pfadnamen stehen
#   (3) wenn der Carrier gewechselt wird, wird die entsprechende Target Playlist angezeigt
#          Bei drag and drop soll das File nicht aus der Sourcelist verschwinden
#
#
# Jedes File der Playlist wird gecheckt, ob es einen gültigen wavheader hat und die Spieldauer wird aus dem Header und der Filesize ermittelt:
# wavheader-tool getsdruno_header() wurde erweitert, um auch Audio-header auszulesen
# test = WAVheader_tools.get_sdruno_header(self,self.m["f1"],'audio')
# import numpy as np
# from scipy.signal import iirnotch, lfilter_zi, lfilter

# def design_notch_filter(fn, BN, fs):
#     """
#     Entwirft einen Notch-Filter bei Mittenfrequenz fn mit Bandbreite BN.

#     Parameters:
#     - fn: Mittenfrequenz des Notch-Filters (Hz)
#     - BN: Notch-Bandbreite (Hz)
#     - fs: Abtastrate (Hz)

#     Returns:
#     - b, a: Notch-Filterkoeffizienten
#     """
#     Q = fn / BN  # Berechnung des Qualitätsfaktors Q
#     b, a = iirnotch(fn / (fs / 2), Q)
#     return b, a

# def process_block(input_block, b, a, zi_real, zi_imag):
#     """
#     Filtert einen Datenblock mit dem Notch-Filter und verwendet den Filterzustand.

#     Parameters:
#     - input_block: Block von komplexen Daten (1D-Array)
#     - b, a: Notch-Filterkoeffizienten
#     - zi_real, zi_imag: Filterzustände für Real- und Imaginärteil

#     Returns:
#     - Gefilterter Block von komplexen Daten (1D-Array)
#     - Neuer Filterzustand für den nächsten Block
#     """
#     # Filterung des Realteils und Aktualisierung des Filterzustands
#     filtered_real, zi_real = lfilter(b, a, np.real(input_block), zi=zi_real)
    
#     # Filterung des Imaginärteils und Aktualisierung des Filterzustands
#     filtered_imag, zi_imag = lfilter(b, a, np.imag(input_block), zi=zi_imag)
    
#     # Rückgabe des gefilterten komplexen Signals und des neuen Zustands
#     filtered_block = filtered_real + 1j * filtered_imag
#     return filtered_block, zi_real, zi_imag

# def notch_filter_file(input_file, output_file, fn, BN, fs, block_size=1024):
#     """
#     Liest ein komplexes Zeit-Signal blockweise, filtert es mit einem Notch-Filter
#     und speichert das Ergebnis in eine Datei. Der Filterzustand wird zwischen
#     den Blöcken gespeichert.

#     Parameters:
#     - input_file: Pfad zur Eingabedatei (komplexe Rohdaten im Binary-Format).
#     - output_file: Pfad zur Ausgabedatei (gefilterte Daten).
#     - fn: Mittenfrequenz des Notch-Filters (Hz).
#     - BN: Bandbreite des Notch-Filters (Hz).
#     - fs: Abtastrate des Signals (Hz).
#     - block_size: Anzahl der Samples pro Block (Standard: 1024).
#     """
#     # Entwerfen des Notch-Filters
#     b, a = design_notch_filter(fn, BN, fs)
    
#     # Initialisierung des Filterzustands (zi) für Real- und Imaginärteil
#     zi_real = lfilter_zi(b, a) * 0  # Nullinitialisierung
#     zi_imag = lfilter_zi(b, a) * 0

#     # Öffne die Input- und Output-Dateien im Binärmodus
#     with open(input_file, 'rb') as f_in, open(output_file, 'wb') as f_out:
#         while True:
#             # Blockweises Lesen der Daten
#             input_block = np.fromfile(f_in, dtype=np.complex64, count=block_size)
            
#             # Wenn keine Daten mehr vorhanden sind, beenden
#             if len(input_block) == 0:
#                 break

#             # Filtere den Datenblock und aktualisiere den Filterzustand
#             filtered_block, zi_real, zi_imag = process_block(input_block, b, a, zi_real, zi_imag)

#             # Schreibe den gefilterten Block in die Ausgabedatei
#             filtered_block.astype(np.complex64).tofile(f_out)

# # Beispielaufruf
# input_file = 'input_signal.dat'   # Pfad zur Eingabedatei
# output_file = 'filtered_signal.dat' # Pfad zur Ausgabedatei
# fs = 1000.0  # Abtastrate in Hz
# fn = 60.0    # Mittenfrequenz des Notch-Filters in Hz
# BN = 1.0     # Bandbreite des Notch-Filters in Hz
# block_size = 4096  # Größe der zu lesenden Blöcke

# notch_filter_file(input_file, output_file, fn, BN, fs, block_size)
