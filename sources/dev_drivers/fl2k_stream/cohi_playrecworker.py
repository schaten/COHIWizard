"""
Created on Feb 24 2024

#@author: scharfetter_admin
"""
#from pickle import FALSE, TRUE #intrinsic
import time
#from datetime import timedelta
from socket import socket, AF_INET, SOCK_STREAM
from struct import unpack
import numpy as np
import os
import psutil
import subprocess
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *


class playrec_worker(QObject):
    """ worker class for data streaming thread from PC to a SDR device
    object for playback and recording thread
    :param : no regular parameters; as this is a thread worker communication occurs via
        __slots__: Dictionary with entries:
        __slots__[0]: filename = complete file path pathname/filename Type: str
        __slots__[1]: timescaler = bytes per second  TODO: rescaling to samples per second would probably be more logical, Type int
        __slots__[2]: TEST = flag for test mode Type: bool
        __slots__[3]: pause = flag if stream should be paused (True) or not (False)
        __slots__[4]: filehandle
        __slots__[5]: data segment to be returned every second
        __slots__[6]: gain, scaling factor for playback
        __slots__[7]: formatlist: [formattag blockalign bitpsample]
        __slots__[9]: file_close
        __slots__[10]: sampling_parameters
    :type : dictionary
    '''
    :raises [ErrorType]: none
    '''
        :return: none
        :rtype: none
    """

    __slots__ = ["filename", "timescaler", "TEST", "pause", "fileHandle", "data", "gain" ,"formattag" ,"datablocksize","fileclose","configparameters"]

    SigFinished = pyqtSignal()
    SigIncrementCurTime = pyqtSignal()
    SigBufferOverflow = pyqtSignal()
    SigError = pyqtSignal(str)
    SigNextfile = pyqtSignal(str)

    def __init__(self, stemlabcontrolinst,*args,**kwargs):

        super().__init__(*args, **kwargs)
        self.stopix = False
        self.DATABLOCKSIZE = 1024*16
        self.DATASHOWSIZE = 1024
        self.JUNKSIZE = self.DATABLOCKSIZE/2
        self.mutex = QMutex()
        self.stemlabcontrol = stemlabcontrolinst

    def set_filename(self,_value):
        self.__slots__[0] = _value
    def get_filename(self):
        return(self.__slots__[0])
    def set_timescaler(self,_value):
        self.__slots__[1] = _value
    def get_timescaler(self):
        return(self.__slots__[1])
    def set_TEST(self,_value):
        self.__slots__[2] = _value
    def get_TEST(self):
        return(self.__slots__[2])
    def set_pause(self,_value):
        self.__slots__[3] = _value
    def get_pause(self):
        return(self.__slots__[3])
    def get_fileHandle(self):
        return(self.__slots__[4])
    def set_fileHandle(self,_value):
        self.__slots__[4] = _value
    def get_data(self):
        return(self.__slots__[5])
    def set_data(self,_value):
        self.__slots__[5] = _value
    def get_gain(self):
        return(self.__slots__[6])
    def set_gain(self,_value):
        self.__slots__[6] = _value
    def get_formattag(self):
        return(self.__slots__[7])
    def set_formattag(self,_value):
        self.__slots__[7] = _value
    def get_datablocksize(self):
        return(self.__slots__[8])
    def set_datablocksize(self,_value):
        self.__slots__[8] = _value
    def get_fileclose(self):
        return(self.__slots__[9])
    def set_fileclose(self,_value):
        self.__slots__[9] = _value
    def get_configparameters(self):
        return(self.__slots__[10])
    def set_configparameters(self,_value):
        self.__slots__[10] = _value

    def play_loop_filelist(self):
        """
        worker loop for sending data to STEMLAB server
        data format i16; 2xi16 complex; FormatTag 1
        sends signals:     
            SigFinished = pyqtSignal()
            SigIncrementCurTime = pyqtSignal()
            SigBufferOverflow = pyqtSignal()

        :param : no regular parameters; as this is a thread worker communication occurs via
        class slots __slots__[i], i = 0...8
        __slots__[0]: filename = complete file path pathname/filename Type: list
        __slots__[1]: timescaler = bytes per second Type: int
        __slots__[2]: TEST = flag for test mode Type: bool
        __slots__[3]: pause : if True then do not send data; Boolean
        __slots__[4]: filehandle: returns current filehandle to main thread methods on request 
        __slots__[5]: data segment to be returned every second
        __slots__[6]: gain, scaling factor for playback
        __slots__[7]: formatlist: [formattag blockalign bitpsample]
        __slots__[9]: file_close
        __slots__[10]: sampling_parameters
        """
        #print("reached playloopthread")
        filenames = self.get_filename()
        TEST = self.get_TEST()
        gain = self.get_gain()
        self.stopix = False
        self.set_fileclose(False)
        configuration = self.get_configparameters() # = {"ifreq":self.m["ifreq"], "irate":self.m["irate"],"rates": self.m["rates"], "icorr":self.m["icorr"],"HostAddress":self.m["HostAddress"], "LO_offset":self.m["LO_offset"]}
        sampling_rate = configuration["irate"]
        lo_shift = configuration["ifreq"]# - configuration["LO_offset"]
        tSR = 10000000*(1 + np.floor((lo_shift+sampling_rate/2)*4/10000000)) #TODO: investigate more thoroughly and optimize !
        tSR = min(100000000,tSR)
        format = self.get_formattag()
        a = (np.tan(np.pi * lo_shift / tSR) - 1) / (np.tan(np.pi * lo_shift / tSR) + 1)
        fl2k_file_path = os.path.join(os.getcwd(),"dev_drivers/fl2k/osmo-fl2k-64bit-20250105", "fl2k_file.exe")
        #print("checking for fl2k")
        self.mutex.lock()
        errorstate, value = self.check_ready_fl2k()
        if errorstate:
            print("no fl2k present")
            self.SigError.emit(value)
            self.SigFinished.emit()
            return()
        self.mutex.unlock()
        if format[0] == 1:  #PCM
            if format[2] == 16:
                formatstring = "s16le"
            elif format[2] == 24:   #24 bit PCM
                formatstring = "s24le"
            elif format[2] == 32:
                formatstring = "s32le"  #32 bit PCM 
            else:
                self.SigError.emit(f"Format not supported: {format[2]}")
                self.SigFinished.emit()
                return()
        else: #IEEE float   
            if format[2] == 32:
                formatstring = "f32le"
            elif format[2] == 16:   #16 bit float
                formatstring = "f16le"
            else:
                self.SigError.emit(f"Format not supported: {format[2]}")
                self.SigFinished.emit()
                return()

        if not TEST:
            #Start ffmpeg Process:
            try:
                ffmpeg_cmd = [
                "ffmpeg", "-y", "-loglevel", "error", "-hide_banner",  
                "-f", formatstring, "-ar", str(sampling_rate), "-ac", "2", "-i", "-",  # Lese von stdin
                "-filter_complex",
                "[0:a]aresample=osr=" + str(tSR) + ",channelsplit=channel_layout=stereo [re][im];"
                "sine=frequency=" + str(lo_shift) + ":sample_rate="  + str(tSR) + "[sine_base];"
                "[sine_base] asplit=2[sine_sin1][sine_sin2];"
                "[sine_sin2]biquad=b0=" + str(a) + ":b1=1:b2=0:a0=1:a1=" + str(a) + ":a2=0[sine_cos];"
                "[re][sine_cos]amultiply[mod_re];"
                "[im][sine_sin1]amultiply[mod_im];"
                "[mod_im]volume=volume=2[part_im];"
                "[mod_re]volume=volume=2[part_re];"
                "[part_re][part_im]amix=inputs=2:duration=shortest[out]",
                "-map", "[out]", "-c:a", "pcm_s8", "-f", "caf", "-"
                ]

                print(f"ffmpeg_command: {ffmpeg_cmd}")
                # Prozess starten
                ffmpeg_process = subprocess.Popen(ffmpeg_cmd, 
                    stdin=subprocess.PIPE, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE,
                    bufsize=10**6
                )

            except FileNotFoundError:
                print(f"Input file not found")
                return()
            except subprocess.SubprocessError as e:
                print(f"Error when executing fl2k_file: {e}")
                return()    
            except Exception as e:
                print(f"Unexpected error: {e}")
                return()    
            
            if os.name.find("posix") >= 0:
                pass
            else:
                psutil.Process(ffmpeg_process.pid).nice(psutil.HIGH_PRIORITY_CLASS)
                pass

            if os.name.find("posix") >= 0:
                try:
                    fl2k_process = subprocess.Popen(
                        ["fl2k_file", "-s", str(tSR), "-r", "0", "-"],
                        stdin=ffmpeg_process.stdout,  # Hier kommt der FFmpeg-Stream an
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        bufsize=10**6
                    )
                    
                except FileNotFoundError:
                    self.SigError.emit(f"Input file not found")
                    self.SigFinished.emit()
                    return()
                except subprocess.SubprocessError as e:
                    self.SigError.emit(f"Error when executing fl2k_file: {e}")
                    self.SigFinished.emit()
                    return()
                except Exception as e:
                    self.SigError.emit(f"Unexpected error: {e}")
                    print("unexpected error in play_loop_filelist for fl2k")
                    self.SigFinished.emit()
                    return()
            else:

                # Starten von fl2k_file mit den entsprechenden Parametern
                try:
                    fl2k_process = subprocess.Popen(
                        [fl2k_file_path, "-s", str(tSR), "-r", "0", "-"],
                        stdin=ffmpeg_process.stdout,  # Hier kommt der FFmpeg-Stream an
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        bufsize=10**6
                    )

                except FileNotFoundError:
                    self.SigError.emit(f"Input file not found")
                    self.SigFinished.emit()
                    return()
                except subprocess.SubprocessError as e:
                    self.SigError.emit(f"Error when executing fl2k_file: {e}")
                    self.SigFinished.emit()
                    return()
                except Exception as e:
                    self.SigError.emit(f"Unexpected error: {e}")
                    self.SigFinished.emit()
                    return()
                psutil.Process(fl2k_process.pid).nice(psutil.HIGH_PRIORITY_CLASS)

        else:
            print("fl2k worker TEST condition , no fl2k_file process started <<<<<<<<<<<<<<<<")

        #print(f"<<<<<<<<<<<<< oooooo >>>>>>>>>>>> format: {format}")
        if format[0] == 1: #PCM              
            if format[2] == 16:
                data = np.empty(self.DATABLOCKSIZE, dtype=np.int16)
            elif format[2] == 32:
                data = np.empty(self.DATABLOCKSIZE, dtype=np.int32)
        else:
            if format[2] == 16:
                data = np.empty(self.DATABLOCKSIZE, dtype=np.float16)
            elif format[2] == 32:
                data = np.empty(self.DATABLOCKSIZE, dtype=np.float32) #TODO: check if true for 32-bit wavs wie Gianni's

        #print(f"playloop: BitspSample: {format[2]}; wFormatTag: {format[0]}; Align: {format[1]}")

        for ix,filename in enumerate(filenames):
            fileHandle = open(filename, 'rb')

            if format[0] == 1:
                normfactor = int(2**int(format[2]-1))-1
            else:
                normfactor = 1
            if format[2] == 16 or format[2] == 32:
                size = fileHandle.readinto(data)
            elif format[2] == 24: #TODO: not yet supported or tested
                data = self.read24(format,data,fileHandle)
                size = len(data)
            self.set_data(data)
            junkspersecond = sampling_rate / self.JUNKSIZE
            self.SigNextfile.emit(filename)
            self.set_fileHandle(fileHandle)
            format = self.get_formattag()
            data_blocksize = self.DATABLOCKSIZE
            self.set_datablocksize(data_blocksize)
            fileHandle.seek(216, 1)
            count = 0

            while size > 0 and not self.stopix:
                self.mutex.lock()
                if ffmpeg_process.poll() != None:
                    self.SigError.emit(f"ffmpeg process terminated unexpectedly, pipe broken")
                    print("Error: ffmpeg process terminated")
                    break
                if fl2k_process.poll() != None:
                    self.SigError.emit(f"fl2k process terminated unexpectedly, pipe broken; Please check if the USB-VGA dongle is connected")
                    print("Error: fl2k process terminated")
                    break
                self.mutex.unlock()
                #reftime = time.time() ###DISTINCT
                if not TEST:
                    if not self.get_pause():
                        try:
                            #TODO: AGC pending
                            aux1 = gain*data[0:size]
                            if formatstring == "s16le":
                                ffmpeg_process.stdin.write(aux1.astype(np.int16))
                            elif formatstring == "s32le":
                                ffmpeg_process.stdin.write(aux1.astype(np.int32))
                            elif formatstring == "f32le":
                                ffmpeg_process.stdin.write(aux1.astype(np.float32))
                            else :   #16 bit float	
                                ffmpeg_process.stdin.write(aux1.astype(np.float16))

                            ffmpeg_process.stdin.flush()
                        except BlockingIOError:
                            print("Blocking data socket error in playloop worker")
                            time.sleep(0.1)
                            self.SigError.emit("Blocking data socket error in playloop worker")
                            self.SigFinished.emit()
                            time.sleep(0.1)
                            return
                        except ConnectionResetError:
                            print("Diagnostic Message: Connection data socket error in playloop worker")
                            time.sleep(0.1)
                            self.SigError.emit("Diagnostic Message: Connection data socket error in playloop worker")
                            self.SigFinished.emit()
                            time.sleep(0.1)
                            return
                        except Exception as e:
                            print("Class e type error  data socket error in playloop worker")
                            print(e)
                            time.sleep(0.1)
                            self.SigError.emit(f"Diagnostic Message: Error in playloop worker: {str(e)}")
                            self.SigFinished.emit()
                            time.sleep(0.1)
                            return
                        except BrokenPipeError:
                            time.sleep(0.1)
                            self.SigError.emit(f"Broken Pipe: FFMPEG-Prozess beendet oder Pipe geschlossen. Neustart erforderlich.")
                            self.SigFinished.emit()
                            time.sleep(0.1)
                            print("FFMPEG-Prozess beendet oder Pipe geschlossen. Neustart erforderlich.")
                            return

                        QThread.usleep(1) #sleep 5 us for keeping main GUI responsive
                        size = fileHandle.readinto(data)
                        count += 1
                        if count > junkspersecond:
                            cv = np.zeros(2*self.DATASHOWSIZE)
                            cv[0:2*self.DATASHOWSIZE-1:2] = data[0:self.DATASHOWSIZE] #write only real part
                            self.set_data(cv)
                            self.SigIncrementCurTime.emit()
                            count = 0
                            gain = self.get_gain()
                    else:
                        aux1 = 0*data[0:size]
                        ffmpeg_process.stdin.write(aux1)
                        ffmpeg_process.stdin.flush()
                        time.sleep(0.1)
                        if self.stopix is True:
                            break
                else:
                    if not self.get_pause():
                        print(" SDR_control fl2k test reached")
                        size = fileHandle.readinto(data)
                        time.sleep(self.DATABLOCKSIZE/2/sampling_rate)
                        count += 1
                        if count > junkspersecond and size > 0:
                            self.set_data(data[0:self.DATASHOWSIZE-1])
                            self.SigIncrementCurTime.emit()
                            gain = self.get_gain()
                            count = 0
                    else:
                        time.sleep(1)
                        if self.stopix is True:
                            break
        print("close file ")
        self.set_fileclose(True)
        fileHandle.close()

        if not TEST:
            # terminate fl2k_file process and wait for actual termination
            ffmpeg_process.stdin.close()  # close stdin
            ffmpeg_process.stdout.close()  # close stdout
            ffmpeg_process.terminate()  # stop process gently
            ffmpeg_process.wait()  # wait for process termination
            stdout, stderr = fl2k_process.communicate()  # wait for the end of fl2k_file
            # report result
            print("fl2k output:")
            print(stdout.decode())
            if stderr:
                print("fl2k_file errors:")
                print(stderr.decode())

        self.SigFinished.emit()
        return()


    def check_ready_fl2k(self):
        """check if fl2k device is connected and ready for use
        """
        errorstate = False
        value = ""
        tSR = 10000000
        if os.name.find("posix") >= 0:
            try:
                fl2k_process = subprocess.Popen(
                    ["fl2k_file", "-s", str(tSR), "-r", "0", "-"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
            except FileNotFoundError:
                value = (f"Input file not found")
                errorstate = True
                return(errorstate, value)
            except subprocess.SubprocessError as e:
                value = (f"Error when executing fl2k_file: {e}")
                errorstate = True
                return(errorstate, value)
            except Exception as e:
                value = (f"unexpected error in play_loop_filelist for fl2k {e}")
                errorstate = True
                return(errorstate, value)    
        else:
            print("check_ready_fl2k: WINDOWS: try popen fl2k")
            try:
                fl2k_file_path = os.path.join(os.getcwd(),"dev_drivers/fl2k/osmo-fl2k-64bit-20250105", "fl2k_file.exe")
                fl2k_process = subprocess.Popen(
                    [fl2k_file_path, "-s", str(tSR), "-r", "0", "-"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )

            except FileNotFoundError:
                value = (f"Input file not found")
                errorstate = True
                return(errorstate, value)
            except subprocess.SubprocessError as e:
                value = (f"Error when executing fl2k_file: {e}")
                errorstate = True
                return(errorstate, value)
            except Exception as e:
                value = (f"unexpected error in play_loop_filelist for fl2k {e}")
                errorstate = True
                return(errorstate, value)
        time.sleep(0.2)
        print(f"check_ready_fl2k: poll: {fl2k_process.poll()}")
        if fl2k_process.poll() != None:
            errorstate = True
            value = "check_ready_fl2k: fl2k device not ready"
        else:
            value = "check_ready_fl2k: fl2k device ready"
            fl2k_process.terminate()
            fl2k_process.wait()
        return(errorstate, value)

    def stop_loop(self):
        self.stopix = True

    def read24(self,format,data,filehandle,data_blocksize):
       """probably not applicable"""
       for lauf in range(0,data_blocksize):
        d = filehandle.read(3)
        if d == None:
            data = []
        else:
            dataraw = unpack('<%ul' % 1 ,d + (b'\x00' if d[2] < 128 else b'\xff'))
            #formatlist: [formattag blockalign bitpsample]
            if format[0] == 1:
                data[lauf] = np.float32(dataraw[0]/8388608)
            else:
                data[lauf] = dataraw[0]
        return data
       
    def rec_loop(self):
        """
        not applicable
        """
        return()
