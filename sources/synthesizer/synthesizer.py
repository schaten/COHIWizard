#IMPORT WHATEVER IS NEEDED
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5 import QtGui
from PyQt5 import QtWidgets, QtGui
import numpy as np
import os
import logging
import matplotlib.pyplot as plt
#import pyfda.pyfdax
from auxiliaries import auxiliaries as auxi
import logging
import yaml
import copy
import time
import wave
import pyqtgraph as pg
#import contextlib
import struct
import soundfile as sf
from scipy.signal import sosfilt, butter, resample
from auxiliaries import WAVheader_tools


class modulate_worker(QObject):
    """ worker class for generating modulated signals in a separate thread
    :param : no regular parameters; as this is a thread worker communication occurs via
        __slots__: Dictionary with parameters
    :return: none
    """
    __slots__ = ["carrier_frequencies", "playlists","sample_rate","block_size","cutoff_freq","modulation_depth","output_base_name","exp_num_samples","progress","logger","combined_signal_block"]
    SigFinished = pyqtSignal()
    SigPupdate = pyqtSignal()
    #SigFinishedLOshifter = pyqtSignal()
    #SigFinishedmerge2G = pyqtSignal()
    #SigSoxerror = pyqtSignal(str)
    #SigMergeerror = pyqtSignal(str)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stopix = False #TODO: check if necessary
        self.mutex = QMutex() #TODO: check if necessary
        self.CHUNKSIZE = int(1024**2) #TODO: check if necessary
 
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
    
    def modulate_terminate(self):
        self.stopix = True

    def start_modulator(self):
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
        # Zeitvektor basierend auf dem sample_offset
        t = np.arange(sample_offset, sample_offset + len(filtered_signal)) / sample_rate
        carrier = np.exp(2 * np.pi * 1j *carrier_freq * t)
        
        # Modulation: Signal amplitude-modulates the carrier with the given depth
        modulated_signal = (1 + modulation_depth * filtered_signal) * carrier
        return modulated_signal

    def read_and_process_audio_blockwise(self, file_list, carrier_freq, target_sample_rate, block_size, cutoff_freq, modulation_depth, zi, sample_offset, current_file_index, file_handles):
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
            audio_block = self.convert_to_mono(audio_block, num_channels)

            # Resampling falls notwendig
            if original_sample_rate != target_sample_rate:
                audio_block = self.resample_audio(audio_block, original_sample_rate, target_sample_rate)

            # Low-Pass-Filter anwenden
            filtered_block, zi = self.process_block(audio_block, sos, zi)

            # Modulation auf den Träger anwenden
            modulated_block = self.modulate_signal(filtered_block, carrier_freq, target_sample_rate, sample_offset, modulation_depth)

            # Aktualisierung von sample_offset für den nächsten Block
            sample_offset += len(modulated_block)

            return modulated_block, zi, sample_offset, current_file_index

        return None, zi, sample_offset, current_file_index

    def process_multiple_carriers_blockwise(self, carrier_frequencies, playlists, sample_rate, block_size, cutoff_freq, modulation_depth, output_base_name, exp_num_samples):
        """
        Process audio from multiple playlists blockwise, each corresponding to a different carrier frequency.
        Write the combined output to multiple WAV files if the 2 GB limit is exceeded.
        """
        # TODO CHECK Set the 2GB limit and calculate the maximum samples per file (for 16-bit PCM WAV files)
        self.stopix = False
        max_file_size = 2 * 1024**3  # 2 GB in bytes
        max_samples_per_file = max_file_size // 4  # complex 16-bit PCM = 4 bytes per sample
        perc_progress_old = 0
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

        #write 216 - 44 =  172 Null Bytes so as to leave room for the SDR-wavheader which will finally overwrite the current header
        prephaser = np.zeros(172)
        out_file.write(prephaser)

        while not done:
            combined_signal_block = None  # Buffer for combined signal block
            done = True  # Assume done unless we find more data
            
            # Process each carrier for the current block
            for i, (carrier_freq, zi) in enumerate(zip(carrier_frequencies, zis)):
                modulated_block, new_zi, sample_offsets[i], current_file_indices[i] = self.read_and_process_audio_blockwise(
                    playlists[i], carrier_freq*1000, sample_rate, block_size, cutoff_freq, modulation_depth, zi, sample_offsets[i], current_file_indices[i], file_handles[i])
                
                # Wenn modulated_block None ist, dann ist das Playlist-Ende erreicht
                if modulated_block is None:
                    continue

                # Dynamically adjust combined signal block size based on modulated block size
                if combined_signal_block is None or len(combined_signal_block) < len(modulated_block):
                    combined_signal_block = np.zeros(len(modulated_block), dtype = np.complex128)

                combined_signal_block[:len(modulated_block)] += 0.1 * modulated_block ####TODO TODO TODO: Gain control einbauen, 0.1 ist nur ein erster Versuch
                
                # If we processed any blocks, we're not done
                done = False

                # Update filter state for this carrier
                zis[i] = new_zi
            
            # If all files are done, break the loop
            if done:
                break
            
            if self.stopix is True:
                self.logger.debug("***modulator worker cancelled")
                break

            # Write the combined block to the current output file
            samples_to_write = len(combined_signal_block)
            
            if samples_to_write + total_samples_written > max_samples_per_file:
                # If the file exceeds 2GB, close the current file and start a new one
                out_file.close()
                self.wav_header_generator(output_file_name)
                file_index += 1
                output_file_name = f"{output_base_name}_{file_index}.wav"
                out_file = sf.SoundFile(output_file_name, 'w', samplerate=sample_rate, channels=1, subtype='PCM_16')
                total_samples_written = 0  # Reset the sample counter for the new file

            #convert complex 128 into 2 x float 64
            lend=2*len(combined_signal_block)
            block_to_write = np.zeros(lend)
            block_to_write[1::2] = np.imag(combined_signal_block)
            block_to_write[0::2] = np.real(combined_signal_block)
            # block_to_write[0:2:lend-1] = np.real(combined_signal_block)
            # block_to_write[1:2:lend] = np.imag(combined_signal_block)
            try:
                out_file.write(block_to_write)
            except:
                print("write error")
            total_samples_written += samples_to_write
            perc_progress = 100*total_samples_written / exp_num_samples
            if perc_progress - perc_progress_old > 1:
                perc_progress_old = perc_progress
                #self.logger.debug(f"percentage completed: {str(perc_progress)}")
                print(f"percentage completed: {str(perc_progress)}")
                #print(f"merge2Gworker renamefile trial {str(jx)}")
                self.set_progress(perc_progress)
                self.set_combined_signal_block(combined_signal_block)
                self.SigPupdate.emit()
                if perc_progress > 100:
                    break
                # spr = np.abs(np.fft.fft(combined_signal_block[0:min(2**16,len(combined_signal_block))]))
                # N = len(spr)
                # spr = np.fft.fftshift(spr)/N
                # fax = np.linspace(-1,1,len(spr))
                # plt.plot(fax,spr)
                # #plt.legend((np.round(self.freq_union,self.m["round_digits"])).astype('str'), loc="lower right")
                # plt.xlabel("norm freq (-)")
                # plt.ylabel("peak value")
                # plt.title("spectrum of block")
                # plt.show()

        # Close the final output file
        out_file.close()
        ####TODO TODO TODO: write true SDRUno-Header into the first 216 bytes of the closed file
        for file_handle_dict in file_handles:
            for handle in file_handle_dict.values():
                handle.close()
        self.logger.debug(f"synthesizer modulate task completed")

    def wav_header_generator(self,output_file_name):
        # if firstpass:
        #     wavheader = WAVheader_tools.get_sdruno_header(self,input_file)
        # if firstsource:     ##########NEW AFTER GAPFIXING
        #     wavheader = WAVheader_tools.get_sdruno_header(self,input_file)
        #     prev_stoptime = wavheader['stoptime_dt']
        #     prev_stoptime_ms = wavheader['stoptime'][7]
        #     gap = 0
        # else:
        #     aux_wavheader = WAVheader_tools.get_sdruno_header(self,input_file)
        #     aux_starttime = aux_wavheader['starttime_dt']
        #     gap = (aux_starttime - prev_stoptime).seconds + (aux_wavheader['starttime'][7] - prev_stoptime_ms)/1000
        #     prev_stoptime = aux_wavheader['stoptime_dt']
        #     prev_stoptime_ms = aux_wavheader['stoptime'][7]
        #     if firstpass:
        #         firstpass = False
        #         stt = self.get_sttime_atrim()
        #         self.logger.debug(f"merge2G: last == first write file reached, ix = 0")
        #         wavheader['starttime_dt'] = stt
        #         wavheader['starttime'] = [stt.year, stt.month, 0, stt.day, stt.hour, stt.minute, stt.second, int(stt.microsecond/1000)] 
        #     else:
        #         stt = wavheader["starttime_dt"]
        #     spt = stt + ndatetime.timedelta(seconds = np.floor(duration)) + ndatetime.timedelta(milliseconds = 1000*(duration - np.floor(duration)))
        #     wavheader['stoptime_dt'] = spt
        #     wavheader['stoptime'] = [spt.year, spt.month, 0, spt.day, spt.hour, spt.minute, spt.second, int(spt.microsecond/1000)] 
        #     wavheader['filesize'] = current_output_file_size
        #     wavheader['data_nChunkSize'] = wavheader['filesize'] - 208
        #     wavheader['nextfilename'] = ""
        #     WAVheader_tools.write_sdruno_header(self,current_output_file.name,wavheader,True) ##TODO TODO TODO Linux conf: self.m["f1"],self.m["wavheader"] must be in Windows format

        pass
            # generate wav header
        
            # %Write wav-header
            # currtime=datetime('now');
            # starttime=currtime - seconds(C_PLAYLENGTH);
            # wavinfo.FILENAME = [C_TargetFILENAME '.dat'];
            # wavinfo.PATHNAME = [WPATHNAME];
            # %Diagnostic:     [header,type] = read_wavheader_func_v1(wavinfo);
            # wavinfo.OVERWRITEHEADERONLY = true;
            # wavinfo.riff_ckID = 'RIFF';
            # wavinfo.nextfilename = '';
            # wavinfo.filesize = length(tsr)*numsegments*4-8;
            # wavinfo.nBitsPerSample = 16;
            # wavinfo.nSamplesPerSec=C_SRR;
            # wavinfo.nAvgBytesPerSec=C_SRR*4;
            # wavinfo.stoptime = [year(currtime) month(currtime) 0 day(currtime) hour(currtime) minute(currtime) second(currtime) 0];
            # wavinfo.starttime = [year(starttime) month(starttime) 0 day(starttime) hour(starttime) minute(starttime) second(starttime) 0];
            # wavinfo.centerfreq = C_fc;
            # wavinfo.data_nChunkSize = wavinfo.filesize - 216;
            # aaa=dir([WPATHNAME '\' C_TargetFILENAME '.dat']);
            # checkfilesize = aaa.bytes-8; %strange 8 bytes offset, filesize must be by 8 smaller than true filesize for SDRUno, reason unknown
            # checkfilesize - wavinfo.filesize;    %####################
            # wavinfo.headerfilename = [WPATHNAME '\' C_TargetFILENAME '.dat']; %write header to the first 216 bytes of the dat file
            # wavinfo.nBlockAlign = 4;
            # wavinfo.wFormatTag = 1;
            # wavinfo.sdr_nChunkSize = 164;
            # wavinfo.wave_string = 'WAVE';
            # wavinfo.fmt_ckID = 'fmt ';
            # wavinfo.fmt_nChunkSize = 16;%4
            # wavinfo.nChannels = 2;
            # wavinfo.sdr_ckID = 'auxi';
            # wavinfo.ADFrequency = 0;
            # wavinfo.IFFrequency = 0;
            # wavinfo.Bandwidth = 0;
            # wavinfo.IQOffset = 0;
            # wavinfo.Unused = [0 0 0 0];
            # wavinfo.data_ckID = 'data';
            # wavinfo.data_nChunkSize = wavinfo.filesize - 208;
            # write_wav_header_func_v2(wavinfo);

                            # if list_ix > (lenlist-1):
                            #     self.logger.debug(f"merge2G: last write file reached, ix = {lenlist}")
                            #     #write last wavheader
                            #     duration = (current_output_file_size - 216)/wavheader["nAvgBytesPerSec"]
                            #     #TODO: this is wrong except for the last file! must be the stoptime of the last output file
                            #     if firstpass:
                            #         firstpass = False
                            #         stt = self.get_sttime_atrim()
                            #         self.logger.debug(f"merge2G: last == first write file reached, ix = 0")
                            #         wavheader['starttime_dt'] = stt
                            #         wavheader['starttime'] = [stt.year, stt.month, 0, stt.day, stt.hour, stt.minute, stt.second, int(stt.microsecond/1000)] 
                            #     else:
                            #         stt = wavheader["starttime_dt"]
                            #     spt = stt + ndatetime.timedelta(seconds = np.floor(duration)) + ndatetime.timedelta(milliseconds = 1000*(duration - np.floor(duration)))
                            #     wavheader['stoptime_dt'] = spt
                            #     wavheader['stoptime'] = [spt.year, spt.month, 0, spt.day, spt.hour, spt.minute, spt.second, int(spt.microsecond/1000)] 
                            #     wavheader['filesize'] = current_output_file_size
                            #     wavheader['data_nChunkSize'] = wavheader['filesize'] - 208
                            #     wavheader['nextfilename'] = ""
                            #     WAVheader_tools.write_sdruno_header(self,current_output_file.name,wavheader,True) ##TODO TODO TODO Linux conf: self.m["f1"],self.m["wavheader"] must be in Windows format
                            #     #TODO: rename to newfile
                            #     nametrunk, extension = os.path.splitext(current_output_file.name)
                            #     nametrunk = f"{os.path.dirname(current_output_file_path)}/{basename}_{str(current_output_file_index)}_"
                            #     aux = str(wavheader['starttime_dt'])
                            #     if aux.find('.') < 1:
                            #         SDRUno_suff = aux
                            #     else:
                            #         SDRUno_suff = aux[:aux.find('.')]
                            #     SDRUno_suff = SDRUno_suff.replace(" ","_")
                            #     SDRUno_suff = SDRUno_suff.replace(":","")
                            #     SDRUno_suff = SDRUno_suff.replace("-","")
                            #     new_name = nametrunk + str(SDRUno_suff) + '_' + str(int(np.round(wavheader["centerfreq"]/1000))) + 'kHz.wav'
                            #     current_output_file.close()
                            #     time.sleep(0.01)
                            #     jx = 0
                            #     while jx <1:
                            #         try:
                            #             #print(f"merge2Gworker try shutil {current_output_file_path} to {new_name}")
                            #             shutil.move(current_output_file_path, new_name)
                            #         except:
                            #             jx += 1
                            #             #print(f"merge2Gworker renamefile trial {str(jx)}")
                            #             time.sleep(0.5)
                            #     # if jx == 10:
                            #     #     auxi.standard_errorbox("The output file was written, but the temp file could not be renamed for unknown reason . Please repeat the merging process")                                    
                            # self.logger.debug("break merget2Gworker")

                        # # check if output file exceeds maximum size
                        # if current_output_file_size + len(data_chunk) > MAX_TARGETFILE_SIZE: #TEST: 50 * 1024**2: #TODO: zurückstellen nach Test self.MAX_TARGETFILE_SIZE:
                        #     #generate individual wavheaders, generate nextfilename
                        #     current_output_file.close()
                        #     #insert wav header
                        #     duration = (current_output_file_size - 216)/wavheader["nAvgBytesPerSec"]
                        #     if firstpass:
                        #         #print(f"merge2G: first write file reached, ix = 0")
                        #         #TODO: write first starttime from cut_times
                        #         firstpass = False
                        #         stt = self.get_sttime_atrim()
                        #         wavheader['starttime_dt'] = stt
                        #         wavheader['starttime'] = [stt.year, stt.month, 0, stt.day, stt.hour, stt.minute, stt.second, int(stt.microsecond/1000)] 
                        #     else:
                        #         #TODO: 
                        #         #aktuell: wenn aktuelles Ausgabefile fertig, hole Startzeit vom Header des aktuellen
                        #         #Ausgabefiles, addiere Dauer und generiere daraus den nächsten wavheader
                        #         #beim ersten Listeneintrag hole Startzit von starttime after trim
                        #         stt = wavheader["starttime_dt"]
                        #     spt = stt + ndatetime.timedelta(seconds= np.floor(duration))  + ndatetime.timedelta(milliseconds = 1000*(duration - np.floor(duration)))
                        #     wavheader['stoptime_dt'] = spt
                        #     wavheader['stoptime'] = [spt.year, spt.month, 0, spt.day, spt.hour, spt.minute, spt.second, int(spt.microsecond/1000)] 
                        #     wavheader['filesize'] = current_output_file_size
                        #     wavheader['data_nChunkSize'] = wavheader['filesize'] - 208
                        #     nametrunk = f"{os.path.dirname(current_output_file_path)}/{basename}_{str(current_output_file_index)}_"
                        #     aux = str(wavheader['starttime_dt'])
                        #     if aux.find('.') < 1:
                        #         SDRUno_suff = aux
                        #     else:
                        #         SDRUno_suff = aux[:aux.find('.')]
                        #     SDRUno_suff = SDRUno_suff.replace(" ","_")
                        #     SDRUno_suff = SDRUno_suff.replace(":","")
                        #     SDRUno_suff = SDRUno_suff.replace("-","")
                        #     new_name = nametrunk + str(SDRUno_suff) + '_' + str(int(np.round(wavheader["centerfreq"]/1000))) + 'kHz.wav'

                        #     # generate name for the wav-header 'nextfilename'
                        #     next_nametrunk = f"{basename}_{str(current_output_file_index + 1)}_" 
                        #     aux = str(wavheader['stoptime_dt'])
                        #     if aux.find('.') < 1:
                        #         next_suff = aux
                        #     else:
                        #        next_suff = aux[:aux.find('.')]
                        #     next_suff = next_suff.replace(" ","_")
                        #     next_suff = next_suff.replace(":","")
                        #     next_suff = next_suff.replace("-","")
                        #     next_name = next_nametrunk + str(next_suff) + '_' + str(int(np.round(wavheader["centerfreq"]/1000))) + 'kHz.wav'
                        #     wavheader['nextfilename'] = next_name
                        #     WAVheader_tools.write_sdruno_header(self,current_output_file.name,wavheader,True) ##TODO TODO TODO Linux conf: self.m["f1"],self.m["wavheader"] must be in Windows format

                            # while True:
                            #     try:
                            #         shutil.move(current_output_file_path, new_name)
                            #         break
                            #     except:
                            #         print("Warning 202 merge2Gworker: cannot access temp file, retry in 2 s")
                            #         time.sleep(2)

                            # # prepare next wavheader starttime
                            # wavheader['starttime_dt'] = wavheader['stoptime_dt']
                            # wavheader['starttime'] = wavheader['stoptime']
                            # current_output_file_size = 0
        #                     current_output_file_index += 1
        #                     current_output_file_path = f"{output_file_prefix}_{current_output_file_index}.dat"
        #                     #print(f"merge2G next outputfile {current_output_file_path}")
        #                     current_output_file = open(current_output_file_path, 'wb')
        #                     current_output_file.write(b'\x00' * 216)  # Schreibe die ersten 216 Bytes mit Nullen
        #                 # write data to target file: if last file: nextfile = ''
        #                 current_output_file.write(data_chunk)
        #                 current_output_file_size += len(data_chunk)
        # self.logger.debug("#################_______________merge2G: merge files done")
        # self.SigFinishedmerge2G.emit()




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
        self.gui = gui
        self.synthesizer_c = synthesizer_c
        #self.norepeat = False
        self.c_step = int(self.STD_CARRIERDISTANCE)
        self.cf_LO = int(self.STD_fclow)
        self.m["audioBW"] = float(self.STD_AUDIOBW)
        self.m["TEST"] = False
        self.m["wavheader"] = {}
        self.m["wavheader"]['centerfreq'] = 0
        self.m["icorr"] = 0
        self.m["cancelflag"] = False
        
        self.logger = synthesizer_m.logger
        self.synthesizer_c.SigRelay.connect(self.rxhandler)
        self.synthesizer_c.SigRelay.connect(self.SigRelay.emit)
        self.gui.lineEdit_LO.setText("1125")
        self.DATABLOCKSIZE = 1024*32
        self.gui = gui #gui_state["gui_reference"]#system_state["gui_reference"]
        self.logger = synthesizer_m.logger
        self.synthesizer_c.SigRelay.connect(self.rxhandler)
        self.synthesizer_c.SigRelay.connect(self.SigRelay.emit)
        self.synthesizer_c.SigRelay.connect(self.SigRelay.emit)

        self.init_synthesizer_ui()

        self.m["numcarriers"] = self.gui.spinBox_numcarriers.value()
        self.m["carrier_ix"] = 0
        self.readFileList = []
        self.oldFileList = []
        self.readFilePath = []
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
        self.gui.comboBox_targetSR.setCurrentIndex(5)
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
        self.gui.spinBox_numcarriers.valueChanged.connect(self.freq_carriers_update)
        self.gui.lineEdit_carrierdistance.editingFinished.connect(self.carrierdistance_update)
        self.gui.lineEdit_audiocutoff_freq.editingFinished.connect(self.audioBW_update)
        self.gui.lineEdit_fc_low.editingFinished.connect(self.fc_low_update)
        self.gui.listWidget_playlist.model().rowsInserted.connect(self.playlist_update_delayed)
        self.gui.listWidget_playlist.model().rowsRemoved.connect(self.playlist_update_delayed) 
        self.gui.listWidget_playlist.setSelectionMode(QListWidget.ExtendedSelection)
        self.gui.listWidget_playlist.setContextMenuPolicy(Qt.CustomContextMenu)
        self.gui.listWidget_playlist.customContextMenuRequested.connect(self.show_context_menu)
        self.gui.listWidget_playlist.model().rowsMoved.connect(self.on_rows_moved)
        self.gui.comboBox_cur_carrierfreq.currentIndexChanged.connect(self.carrier_ix_changed)
        self.gui.pushButton_saveproject.clicked.connect(self.save_project)
        self.gui.pushButton_loadproject.clicked.connect(self.load_project)
        self.gui.synthesizer_pushbutton_create.clicked.connect(self.create_band_thread)
        #self.gui.synthesizer_pushbutton_create.clicked.connect(self.create_band)
        self.gui.timeEdit_reclength.timeChanged.connect(self.carrier_ix_changed)
        self.gui.synthesizer_pushbutton_cancel.clicked.connect(self.cancel_modulate)
        self.canvasbuild()
        #self.gui.lineEdit_carrierdistance.textEdited.connect(self.carriedistance_update)
        #editingFinished #editingFinished
        ###########TODO TODO TODO: remove after transfer to config Tab
        # try:
        #     stream = open("config_wizard.yaml", "r")
        #     self.metadata = yaml.safe_load(stream)
        #     stream.close()
        #     self.ismetadata = True
        #     if 'STM_IP_address' in self.metadata.keys():
        #         self.gui.lineEdit_IPAddress.setText(self.metadata["STM_IP_address"]) #TODO: Remove after transfer of playrec
        #         self.m["STM_IP_address"] = self.metadata["STM_IP_address"] #TODO: Remove after transfer of playrec
        # except:
        #     self.m["STM_IP_address"] = self.gui.lineEdit_IPAddress.text()
        #     self.logger.error("reset_gui: cannot get metadata")
        #     pass


    def cancel_modulate(self):
        #TODO check how to handle and delete after change to model
        #schedule_objdict = self.m["schedule_objdict"]
        #TODO: look why that was used self.SigDisconnectExternalMethods.emit("cancel_resampling")
        self.cleanup()
        if self.m["cancelflag"]:
            self.logger.debug("cancel_modulation: **** suppressed because cancelflag ___cancel_resamp reached")
            return
        self.m["cancelflag"] = True
        time.sleep(0.001)
        for i in range(5):
            self.logger.debug("**** 5 x BLOCK *****___cancel_synthesizer reached")
        # self.m["emergency_stop"] = True
        # print(f"Cance_resamapling: emergency stop: {self.m['emergency_stop']}")
        # self.logger.debug("Cance_resamapling: emergency stop: %s", self.m['emergency_stop'])
        try:
            self.modulate_worker.modulate_terminate()
        except:
            self.logger.debug("cancel synthesizer modulation: modulate worker could not be terminated")
            pass
        #TODO TODO TODO: delete out files produced so far

    def canvasbuild(self):
        """
        sets up a canvas to which graphs can be plotted
        Use: calls the method auxi.generate_canvas with parameters self.gui.gridlayoutX to specify where the canvas 
        should be placed, the coordinates and extensions in the grid and a reference to the QMainwidget Object
        generated by __main__ during system startup. This object is relayed via signal to all modules at system initialization 
        and is automatically available (see rxhandler method)
        the reference to the canvas object is written to self.cref
        :param : gui
        :type : QMainWindow
        :raises [ErrorType]: [ErrorDescription]
        :return: none
        :rtype: none
        """
        # self.cref = auxi.generate_canvas(self,self.gui.gridLayout_10,[13,11,1,2],[-1,-1,-1,-1],gui)
        # self.cref["ax"].tick_params(axis='both', which='major', labelsize=6)
        self.plot_widget = pg.PlotWidget()
        self.gui.gridLayout_synthesizer.addWidget(self.plot_widget,1,8,1,2)
        self.plot_widget.getAxis('left').setStyle(tickFont=pg.QtGui.QFont('Arial', 6))
        self.plot_widget.getAxis('bottom').setStyle(tickFont=pg.QtGui.QFont('Arial', 6))
        self.plot_widget.setBackground('w')
        self.xdata = np.linspace(0, 10, 100)
        self.ydata = np.sin(self.xdata)
        ymin = -120
        ymax = 0
        self.plot_widget.setYRange(ymin, ymax)
        self.curve = self.plot_widget.plot(self.xdata, self.ydata, pen=pg.mkPen('k'))


    # def create_band(self):
    #     #TODO TODO TODO: start and manage thread for modulator_worker
    #     #TODO TODO TODO: write method for progressbar update
    #     #
    #     #
    #     # Beispielhafte Anwendung
    #     sample_rate = int(self.gui.comboBox_targetSR.currentText())*1000 # Gemeinsame Abtastrate für Hf-Signal
    #     cutoff_freq = float(self.gui.lineEdit_audiocutoff_freq.text())*1000   # Tiefpass-Grenzfrequenz   float32(self.gui.lineEdit_audiocutoff_freq.text())
    #     modulation_depth = float(self.gui.lineEdit_modfactor.text())  # Modulationstiefe 
    #     playlists = [[f"{path.rstrip('/')}/{file}" for file, path in zip(files, paths)] for files, paths in zip(self.readFileList, self.readFilePath)]
    #     carrier_frequencies = self.m["carrierarray"]
    #     output_base_name = 'combined_output'
    #     block_size = 2**16   # Maximalblocklänge für die Verarbeitung
    #     total_reclength = self.get_reclength()
    #     exp_num_samples = total_reclength * sample_rate
    #     #exp_num_blocks = exp_num_samples/block_size
    #     self.process_multiple_carriers_blockwise(carrier_frequencies, playlists, sample_rate, block_size, cutoff_freq, modulation_depth, output_base_name, exp_num_samples)
    #     #TODO TODO TODO: 
    #     # zero pad all rows in modulated_signals to greatest subsignal length

    def create_band_thread(self):
        self.SigActivateOtherTabs.emit("synthesizer","inactivate",["Synthesizer"])
        self.gui.progressBar_synth.setValue(0)
        self.gui.synthesizer_pushbutton_create.setEnabled(False)
        self.logger.debug("modulate: configure modulate_worker thread et al")
        self.m["cancelflag"] = False
        sample_rate = int(self.gui.comboBox_targetSR.currentText())*1000 # samplingrate of RF-Signal
        cutoff_freq = float(self.gui.lineEdit_audiocutoff_freq.text())*1000   # Lowpass cutoff frequency   
        modulation_depth = float(self.gui.lineEdit_modfactor.text())  # Modulation depth 
        playlists = [[f"{path.rstrip('/')}/{file}" for file, path in zip(files, paths)] for files, paths in zip(self.readFileList, self.readFilePath)]
        carrier_frequencies = self.m["carrierarray"]
        output_base_name = 'combined_output'
        block_size = 2**16   # Maximum block length
        total_reclength = self.get_reclength()
        exp_num_samples = total_reclength * sample_rate
        
        self.modulate_thread = QThread(parent = self)
        self.modulate_worker = modulate_worker()
        self.modulate_worker.moveToThread(self.modulate_thread)
        self.modulate_worker.set_carrier_frequencies(carrier_frequencies)
        self.modulate_worker.set_playlists(playlists)
        self.modulate_worker.set_sample_rate(sample_rate)
        self.modulate_worker.set_block_size(block_size)
        self.modulate_worker.set_cutoff_freq(cutoff_freq)
        self.modulate_worker.set_modulation_depth(modulation_depth)
        self.modulate_worker.set_output_base_name(output_base_name)
        self.modulate_worker.set_exp_num_samples(exp_num_samples)
        self.modulate_worker.set_logger(self.logger)
        self.modulate_thread.started.connect(self.modulate_worker.start_modulator)
        self.modulate_worker.SigPupdate.connect(self.PupdateSignalHandler)
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
        time.sleep(0.01) # wait state for worker to start up
        #print("modulate_ action method sleep over")
        #self.SigProgress.emit()       
        return(True)
    
    def cleanup(self):
        self.gui.synthesizer_pushbutton_create.setEnabled(True)
        self.SigActivateOtherTabs.emit("synthesizer","activate",[])
        self.gui.progressBar_synth.setValue(0)


    def PupdateSignalHandler(self):
        """
        update progress bar and handle other state display elements
        """
        progress = self.modulate_worker.get_progress()
        print(f"progress: {progress}")
        combined_signal_block = self.modulate_worker.get_combined_signal_block()
        self.gui.progressBar_synth.setValue(min(100,int(np.floor(progress))))
        if self.gui.synthesizer_radioBut_diagnosticmode.isChecked():
            self.logger.debug(f"percentage completed: {str(progress)}")
            spr = np.abs(np.fft.fft(combined_signal_block[0:min(2**16,len(combined_signal_block))]))
            N = len(spr)
            spr = np.fft.fftshift(spr)/N
            fax = np.linspace(-1,1,len(spr))
            # plt.plot(fax,spr)
            # #plt.legend((np.round(self.freq_union,self.m["round_digits"])).astype('str'), loc="lower right")
            # plt.xlabel("norm freq (-)")
            # plt.ylabel("peak value")
            # plt.title("spectrum of block")
            # plt.show()

            #flo = self.m["wavheader"]['centerfreq'] - self.m["wavheader"]['nSamplesPerSec']/2
            #freq0 = np.linspace(0,self.m["wavheader"]['nSamplesPerSec'],N)
            #freq = freq0 + flo
            #datax = (np.floor(freq/1000))
            datax = fax
            datay = 20*np.log10(spr)
            self.curve.setData(datax, datay)


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
        # Zeitvektor basierend auf dem sample_offset
        t = np.arange(sample_offset, sample_offset + len(filtered_signal)) / sample_rate
        carrier = np.exp(2 * np.pi * 1j *carrier_freq * t)
        
        # Modulation: Signal amplitude-modulates the carrier with the given depth
        modulated_signal = (1 + modulation_depth * filtered_signal) * carrier
        return modulated_signal

    def read_and_process_audio_blockwise(self, file_list, carrier_freq, target_sample_rate, block_size, cutoff_freq, modulation_depth, zi, sample_offset, current_file_index, file_handles):
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
            audio_block = self.convert_to_mono(audio_block, num_channels)

            # Resampling falls notwendig
            if original_sample_rate != target_sample_rate:
                audio_block = self.resample_audio(audio_block, original_sample_rate, target_sample_rate)

            # Low-Pass-Filter anwenden
            filtered_block, zi = self.process_block(audio_block, sos, zi)

            # Modulation auf den Träger anwenden
            modulated_block = self.modulate_signal(filtered_block, carrier_freq, target_sample_rate, sample_offset, modulation_depth)

            # Aktualisierung von sample_offset für den nächsten Block
            sample_offset += len(modulated_block)

            return modulated_block, zi, sample_offset, current_file_index

        # Alle Dateien wurden verarbeitet, kehre None zurück
        return None, zi, sample_offset, current_file_index

    def process_multiple_carriers_blockwise(self, carrier_frequencies, playlists, sample_rate, block_size, cutoff_freq, modulation_depth, output_base_name, exp_num_samples):
        """
        Process audio from multiple playlists blockwise, each corresponding to a different carrier frequency.
        Write the combined output to multiple WAV files if the 2 GB limit is exceeded.
        """
        # Set the 2GB limit and calculate the maximum samples per file (for 16-bit PCM WAV files)
        max_file_size = 2 * 1024**3  # 2 GB in bytes
        max_samples_per_file = max_file_size // 4  # complex 16-bit PCM = 4 bytes per sample
        perc_progress_old = 0
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

        #write 216 - 44 =  172 Null Bytes so as to leave room for the SDR-wavheader which will finally overwrite the current header
        prephaser = np.zeros(172)
        out_file.write(prephaser)

        while not done:
            combined_signal_block = None  # Buffer for combined signal block
            done = True  # Assume done unless we find more data
            
            # Process each carrier for the current block
            for i, (carrier_freq, zi) in enumerate(zip(carrier_frequencies, zis)):
                modulated_block, new_zi, sample_offsets[i], current_file_indices[i] = self.read_and_process_audio_blockwise(
                    playlists[i], carrier_freq*1000, sample_rate, block_size, cutoff_freq, modulation_depth, zi, sample_offsets[i], current_file_indices[i], file_handles[i])
                
                # Wenn modulated_block None ist, dann ist das Playlist-Ende erreicht
                if modulated_block is None:
                    continue

                # Dynamically adjust combined signal block size based on modulated block size
                if combined_signal_block is None or len(combined_signal_block) < len(modulated_block):
                    combined_signal_block = np.zeros(len(modulated_block), dtype = np.complex128)

                combined_signal_block[:len(modulated_block)] += 0.1 * modulated_block ####TODO TODO TODO: Gain control einbauen, 0.1 ist nur ein erster Versuch
                
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
            #convert complex 128 into 2 x float 64
            lend=2*len(combined_signal_block)
            block_to_write = np.zeros(lend)
            block_to_write[1::2] = np.imag(combined_signal_block)
            block_to_write[0::2] = np.real(combined_signal_block)
            # block_to_write[0:2:lend-1] = np.real(combined_signal_block)
            # block_to_write[1:2:lend] = np.imag(combined_signal_block)
            try:
                out_file.write(block_to_write)
            except:
                print("write error")
            total_samples_written += samples_to_write
            perc_progress = 100*total_samples_written / exp_num_samples
            if perc_progress - perc_progress_old > 1:
                perc_progress_old = perc_progress
                self.logger.debug(f"percentage completed: {str(perc_progress)}")
                print(f"percentage completed: {str(perc_progress)}")
                spr = np.abs(np.fft.fft(combined_signal_block[0:min(2**16,len(combined_signal_block))]))
                N = len(spr)
                spr = np.fft.fftshift(spr)/N
                fax = np.linspace(-1,1,len(spr))
                plt.plot(fax,spr)
                #plt.legend((np.round(self.freq_union,self.m["round_digits"])).astype('str'), loc="lower right")
                plt.xlabel("norm freq (-)")
                plt.ylabel("peak value")
                plt.title("spectrum of block")
                plt.show()


        # Close the final output file
        out_file.close()
        ####TODO TODO TODO: write true SDRUno-Header into the first 216 bytes of the closed file

        # **Am Ende sicherstellen, dass alle Datei-Handles geschlossen werden**
        for file_handle_dict in file_handles:
            for handle in file_handle_dict.values():
                handle.close()

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
        pr["projectdata"]["carrier_step"] = self.c_step
        pr["projectdata"]["carrier_f_LO"] = self.cf_LO
        pr["projectdata"]["audio_BW"] = self.m["audioBW"]
        pr["projectdata"]["current_listdir"] = self.current_listdir
        pr["projectdata"]["targetSR_index"] = self.gui.comboBox_targetSR.currentIndex()
        #pr["projectdata"]["preset_time"] = 
        #pr["projectdata"]["LO"] = self.gui.lineEdit_LO.setText("1125") #TODO TODO TODO, diese Variable wird aktuell noch nirgends verwendet (--> wav header)
        #TODO TODO TODO: add all settings to be saved:
        #self.comboBox_targetSR_2.setCurrentIndex(###)
        #scale factor
        #modulation factor
        #Target filename
        qtimeedit = self.gui.timeEdit_reclength
        time_from_qtimeedit = qtimeedit.time()
        pr["projectdata"]["preset_time"] = [time_from_qtimeedit.hour(), time_from_qtimeedit.minute(), time_from_qtimeedit.second()]
         


        filename = self.save_file_dialog()
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
        filename = self.load_file_dialog()
        try:
            stream = open(filename, "r")
            pr["projectdata"] = yaml.safe_load(stream)
            stream.close()

            self.readFileList = pr["projectdata"]["readFileList"]
            self.readFilePath = pr["projectdata"]["readFilePath"]
            #self.oldFileList = pr["projectdata"]["readFileList"]
            self.oldFileList = copy.deepcopy(pr["projectdata"]["readFileList"])
            self.gui.lineEdit_audiocutoff_freq.setText(str(pr["projectdata"]["audio_BW"]))
            self.gui.lineEdit_carrierdistance.setText(str(pr["projectdata"]["carrier_step"]))
            self.m["numcarriers"] = pr["projectdata"]["numcarriers"]
            self.gui.spinBox_numcarriers.valueChanged.disconnect(self.freq_carriers_update)
            self.gui.spinBox_numcarriers.setProperty("value", self.m["numcarriers"])
            self.gui.spinBox_numcarriers.valueChanged.connect(self.freq_carriers_update)
            self.m["carrier_ix"] = 0
            self.gui.comboBox_cur_carrierfreq.setCurrentIndex(self.m["carrier_ix"])
            #######preset_time = QTime(00, 30, 00) 
            aux_preset_time = pr["projectdata"]["preset_time"]
            preset_time = QTime(aux_preset_time[0],aux_preset_time[1],aux_preset_time[2]) 
            self.gui.timeEdit_reclength.setTime(preset_time)

            self.load_index = True
            self.fillplaylist()
            self.current_listdir = pr["projectdata"]["current_listdir"]
            self.fillsourcelist(self.current_listdir)
            self.audioBW_update()
            self.fc_low_update()
            self.carrierdistance_update()
            self.load_index = False

            #TODO TODO TODO load all remaining settings
            #self.comboBox_targetSR_2.setCurrentIndex(###)
            #self.gui.comboBox_targetSR.setCurrentIndex(pr["projectdata"]["targetSR_index"])
            #scale factor
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
        
        print(f"carrier index changed to: {self.m['carrier_ix']}")
        self.fillplaylist()

    def fillplaylist(self):
        """update playlist of carrier with index self.m['carrier_ix']; clear old list and write new one
         :param: none
         :returns: none 
         """
        self.gui.listWidget_playlist.model().rowsInserted.disconnect(self.playlist_update_delayed)
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
                print(f"show readFilePath index out of range at index: {self.m['carrier_ix']} [{ix}]")
                return duration
            if not len(self.readFilePath[self.m["carrier_ix"]][ix] + x) < 1:
                wav_info = self.get_wav_info(file_path)
                duration += wav_info['duration_seconds']
            else:
                print("NNNNNNNNNN")
            ix += 1

        # print(f"Spieldauer: {wav_info['duration_seconds']} Sekunden")
        # print(f"Anzahl der Kanäle: {wav_info['n_channels']}")
        # print(f"Abtastrate: {wav_info['framerate']} Hz")
        # print(f"Sample-Breite: {wav_info['sampwidth_bytes']} Bytes")
        # print(f"Datenformat: {wav_info['data_format']}")
        print(f"full duration of this carrier track: {duration}")
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
        carrier_array = np.arange(self.cf_LO, self.cf_HI+1, self.c_step)
        carrierselector = carrier_array.tolist()
        self.gui.comboBox_cur_carrierfreq.clear()
        for cf in carrierselector:
            self.gui.comboBox_cur_carrierfreq.addItem(str(cf))
        self.m["carrierarray"] = carrier_array


    def freq_carriers_update(self):
#         Vergrößern: append differenz zu vorher mal self.readFileList mit []
# 	Verkleinern: ermittle differenz zu vorher letzte self.readFileList Elemente
# Wenn letzte self.readFileList[-1] nicht empty  Warnug, dass alle bis auf die verbleibenden Lisetneiträge gelöscht werde, Proceed ? Cancel ?
# Wenn bestätigt:
# 			Delete letzte self.readFileList Elemente

        self.numcarriers_old = self.m["numcarriers"]
        numcar = self.gui.spinBox_numcarriers.value() 

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
        else:
            #TODO TODO TESTING ! delete n list elements and ask if that is wanted
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
                    self.gui.spinBox_numcarriers.valueChanged.disconnect(self.freq_carriers_update)
                    self.gui.spinBox_numcarriers.setProperty("value", self.numcarriers_old)
                    time.sleep(0.1)
                    self.gui.spinBox_numcarriers.valueChanged.connect(self.freq_carriers_update)
                    return False
            else:
                for i in range(delta):
                    del self.readFileList[self.numcarriers_old - 1 - i]
                    del self.oldFileList[self.numcarriers_old - 1 - i]
                    del self.readFilePath[self.numcarriers_old - 1 - i]

        self.m["numcarriers"] = numcar  
        self.cf_LO = int(self.gui.lineEdit_fc_low.text())
        self.c_step = int(self.gui.lineEdit_carrierdistance.text())
        self.cf_HI = self.cf_LO + (self.m["numcarriers"] - 1) * self.c_step
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
    

    def audioBW_update(self):
        audioBW = self.gui.lineEdit_audiocutoff_freq.text()
        if not self.isfloat(audioBW):
            auxi.standard_errorbox("invalid characters, must be numeric float value !")
            return False
        else:
            self.m["audioBW"] = float(self.gui.lineEdit_audiocutoff_freq.text())
        if (self.m["audioBW"] < 2.5) or (self.m["audioBW"] > 16):
            auxi.standard_errorbox("audio bandwidth outside the range 2.5 - 16 kHz. Value must be in this interval, please cahnge")
            return False
        if (self.m["carrier_distance"] < 2*self.m["audioBW"]):
            auxi.standard_errorbox("carrier spacing is less than 2*audio bandwidth, this is not allowed, please either increase carrier spacing or reduce audio bandwidth")
            self.gui.lineEdit_audiocutoff_freq.setText(self.STD_AUDIOBW)
            return False
        self.m["audioBW"] = float(self.gui.lineEdit_audiocutoff_freq.text())
        self.freq_carriers_update()
        print(f"carrier spacing: {self.m['audioBW']}")

    def fc_low_update(self):
        #TODO TODO TODO: implement hibound, lowbound as lineEdit_LO - comboBox_targetSR/2
        fclowbound = 0
        fchibound = 1000
        fc_low = self.gui.lineEdit_fc_low.text()
        if not self.isint(fc_low):
            auxi.standard_errorbox("invalid characters, must be numeric integer value !")
            return False
        else:
            self.m["fc_low"] = float(self.gui.lineEdit_fc_low.text())
        if (self.m["fc_low"] < fclowbound) or (self.m["audioBW"] > fchibound):
            auxi.standard_errorbox(f"audio bandwidth outside the valid range. Value must be in this interval {str(fclowbound)} - {str(fclowbound)}, please cahnge")
            return False
        if (self.m["carrier_distance"] < 2*self.m["audioBW"]):
            auxi.standard_errorbox("carrier spacing is less than 2*audio bandwidth, this is not allowed, please either increase carrier spacing or reduce audio bandwidth")
            self.gui.lineEdit_fc_low.setText(self.STD_fclow)
            return False
        self.freq_carriers_update()
        self.m["fc_low"] = float(self.gui.lineEdit_fc_low.text())
        self.freq_carriers_update()
        print(f"carrier spacing: {self.m['fc_low']}")

    def carrierdistance_update(self):
        #TODO: check if integer !
        carrier_delta = self.gui.lineEdit_carrierdistance.text()
        if not self.isint(carrier_delta):
            auxi.standard_errorbox("invalid characters, must be numeric float value !")
            self.logger.error("plot_res_spectrum: wrong format of carrier distance")
            return False
        else:
            self.m["carrier_distance"] = float(self.gui.lineEdit_carrierdistance.text())
        
        if self.m["carrier_distance"] < 2*self.m["audioBW"]:
            auxi.standard_errorbox("carrier spacing is less than 2*audio bandwidth, please either increase carrier spacing or reduce audio bandwidth")
            self.gui.lineEdit_carrierdistance.setText(self.STD_CARRIERDISTANCE)
            return False
        self.m["carrier_distance"] = float(self.gui.lineEdit_carrierdistance.text())
        self.freq_carriers_update()
        print(f"carrier spacing: {self.m['carrier_distance']}")

    def select_tree(self):
        """
        initiates buildup of file selection tree
        :param : none
        :raises [ErrorType]:none
        :returns: none
        """  
        root_directory = QFileDialog.getExistingDirectory(self.m["QTMAINWINDOWparent"], "Please chose source file directory", self.default_directory)
        if root_directory:
            self.fillsourcelist(root_directory)
            self.m["metadata"]["last_audiosource_path"] = root_directory
            stream = open("config_wizard.yaml", "w")
            yaml.dump(self.m["metadata"], stream)
            stream.close()


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
            if x.endswith(".wav"):
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
        print(f"playlist_update, signal addrow: first ix: {first}, last ix: {last}")
        QTimer.singleShot(0, self.playlist_update)

    def playlist_update(self):
        """_currently loaded playlist in self.gui.listWidget_playlist is bering transferred 
        to the central list of playlists self.readFileList[self.m["carrier_ix"]]. Then playlist_purge()
        is called
        """
 
        try:
            self.oldFileList[self.m["carrier_ix"]] = copy.deepcopy(self.readFileList[self.m["carrier_ix"]])
            #TODO TODO TODO: Bei Indexerhöhung muss ein dummy self.oldFileList[self.m["carrier_ix"]] mit dem erhöhten Index angelegt werden, sonst stürzt später due diff-Methode in purge ab
        except:
            self.oldFileList = []

        self.readFileList[self.m["carrier_ix"]] = [self.gui.listWidget_playlist.item(i).text() for i in range(self.gui.listWidget_playlist.count())]
        self.playlist_purge()
        duration = self.show_playlength()
        self.show_fillprogress(duration)

        print("playlist_update")
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
            print(f"playlist purge: change index: {ix_diff}, playlist: {self.readFileList[self.m['carrier_ix']] }, pathlist: {self.readFilePath[self.m['carrier_ix']]}")
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
        if _key.find("cui_synthesizer") == 0:
            _value[0](_value[1]) #STILL UNCLEAR
        if _key.find("cexex_synthesizer") == 0  or _key.find("cexex_all_") == 0:
            if  _value[0].find("updateGUIelements") == 0:
                self.updateGUIelements()
            if  _value[0].find("reset_GUI") == 0:
                self.reset_GUI()
            if  _value[0].find("logfilehandler") == 0:
                self.logfilehandler(_value[1])
            # if  _value[0].find("canvasbuild") == 0:
            #     self.canvasbuild(_value[1])

            #handle method
            # if  _value[0].find("plot_spectrum") == 0: #EXAMPLE
            #     self.plot_spectrum(0,_value[1])   #EXAMPLE

    # def canvasbuild(self,gui):
    #     """
    #     sets up a canvas to which graphs can be plotted
    #     Use: calls the method auxi.generate_canvas with parameters self.gui.gridlayoutX to specify where the canvas 
    #     should be placed, the coordinates and extensions in the grid and a reference to the QMainwidget Object
    #     generated by __main__ during system startup. This object is relayed via signal to all modules at system initialization 
    #     and is automatically available (see rxhandler method)
    #     the reference to the canvas object is written to self.cref
    #     :param : gui
    #     :type : QMainWindow
    #     :raises [ErrorType]: [ErrorDescription]
    #     :return: none
    #     :rtype: none
    #     """
    #     #TODO: activate call correctly, this is just an example
    #     #self.cref = auxi.generate_canvas(self,self.gui.gridLayout_5,[6,0,6,4],[-1,-1,-1,-1],gui)
    #     pass


    def logfilehandler(self,_value):
        if _value is False:
            self.logger.debug("abstract module: INACTIVATE LOGGING")
            self.logger.setLevel(logging.ERROR)
        else:
            self.logger.debug("abstract module: REACTIVATE LOGGING")
            self.logger.setLevel(logging.DEBUG)


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
        print("synthesizer: updateGUIelements")
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
