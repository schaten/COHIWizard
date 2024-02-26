"""
Created on Feb 24 2024

#@author: scharfetter_admin
"""
#from pickle import FALSE, TRUE #intrinsic
import time
#from datetime import timedelta
from socket import socket, AF_INET, SOCK_STREAM
from struct import pack, unpack
import numpy as np
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from scipy import signal as sig
from auxiliaries import auxiliaries as auxi
from auxiliaries import WAVheader_tools
#from stemlab_control import StemlabControl


class playrec_worker(QObject):
    """ worker class for data streaming thread from PC to STEMLAB
    object for playback and recording thread
    :param : no regular parameters; as this is a thread worker communication occurs via
        __slots__: Dictionary with entries:
        __slots__[0]: self.f1 = complete file path pathname/filename Type: str
        __slots__[1]: timescaler = bytes per second  TODO: rescaling to samples per second would probably be more logical, Type int
        __slots__[2]: TEST = flag for test mode Type: bool
        __slots__[3]: modality; currently not used TODO: remove ?
        __slots__[4]: filehandle
        __slots__[5]: data segment to be returned every second
        __slots__[6]: gain, scaling factor for playback
        __slots__[7]: formatlist: [formattag blockalign bitpsample]
    :type : dictionary
    '''
    :raises [ErrorType]: none
    '''
        :return: none
        :rtype: none
    """

    __slots__ = ["filename", "timescaler", "TEST", "modality","fileHandle","data","gain","formattag"]

    SigFinished = pyqtSignal()
    SigIncrementCurTime = pyqtSignal()
    SigBufferUnderflow = pyqtSignal()

    def __init__(self, stemlabcontrolinst,*args,**kwargs):

        super().__init__(*args, **kwargs)
        self.stopix = False
        self.pausestate = False
        self.JUNKSIZE = 2048*4
        self.DATABLOCKSIZE = 1024*4
        self.mutex = QMutex()
        self.stemlabcontrol = stemlabcontrolinst

    def set_0(self,_value):
        self.__slots__[0] = _value
    def get_0(self):
        return(self.__slots__[0])
    def set_1(self,_value):
        self.__slots__[1] = _value
    def get_1(self):
        return(self.__slots__[1])
    def set_2(self,_value):
        self.__slots__[2] = _value
    def get_2(self):
        return(self.__slots__[3])
    def set_3(self,_value):
        self.__slots__[3] = _value
    def get_3(self):
        return(self.__slots__[3])
    def get_4(self):
        return(self.__slots__[4])
    def set_4(self,_value):
        self.__slots__[4] = _value
    def get_5(self):
        return(self.__slots__[5])
    def set_5(self,_value):
        self.__slots__[5] = _value
    def get_6(self):
        return(self.__slots__[6])
    def set_6(self,_value):
        self.__slots__[6] = _value
    def get_7(self):
        return(self.__slots__[7])
    def set_7(self,_value):
        self.__slots__[7] = _value

    def play_loop16(self):
        """
        worker loop for sending data to STEMLAB server
        data format i16; 2xi16 complex; FormatTag 1
        sends signals:     
            SigFinished = pyqtSignal()
            SigIncrementCurTime = pyqtSignal()
            SigBufferUnderflow = pyqtSignal()

        :param : no regular parameters; as this is a thread worker communication occurs via
        class slots __slots__[i], i = 0...3
        __slots__[0]: self.f1 = complete file path pathname/filename Type: str
        __slots__[1]: timescaler = bytes per second  TODO: rescaling to samples per second would probably be more logical, Type int
        __slots__[2]: TEST = flag for test mode Type: bool
        __slots__[3]: modality; currently not used TODO: remove ?
        __slots__[4]: filehandle
        __slots__[5]: data segment to be returned every second
        __slots__[6]: gain, scaling factor for playback
        __slots__[7]: formatlist: [formattag blockalign bitpsample]
        :type : none
        '''
        :raises [ErrorType]: none
        '''
        :return: none
        :rtype: none
        """
        print("reached playloopthread")
        self.f1 = self.__slots__[0]
        timescaler = self.__slots__[1]
        TEST = self.__slots__[2]
        modality = self.__slots__[3]
        self.set_6(1)
        self.gain = self.__slots__[6]
        #TODO: self.fmtscl = self.__slots__[7] #scaler for data format        
        self.stopix = False
        position = 1
        self.fileHandle = open(self.f1, 'rb')
        print(f"filehandle for set_4: {self.fileHandle} of file {self.f1} ")
        self.set_4(self.fileHandle)
        format = self.get_7()
        #print(f"Filehandle :{self.fileHandle}")

        self.fileHandle.seek(216, 1)  #TODO: other formats than wav SDRUno not supported !
        #TODO: if format[0] == 1 and format[2] == 16 
        #data = np.empty(self.DATABLOCKSIZE, dtype=np.int16)
        #TODO: if format[0] == 1 and format[2] == 32
        if format[2] == 16:
            data = np.empty(self.DATABLOCKSIZE, dtype=np.int16)
        else:
            #data = np.empty(self.DATABLOCKSIZE, dtype=np.int32)
            data = np.empty(self.DATABLOCKSIZE, dtype=np.float32) #TODO: check if true for 32-bit wavs wie Gianni's

        #print(f"playloop: BitspSample: {format[2]}; wFormatTag: {format[0]}; Align: {format[1]}")
        if format[0] == 1:
            scl = int(2**int(format[2]-1))-1
        else:
            scl = 1
        #print(f"scl = {scl}")
        #size = self.fileHandle.readinto(data)
        if format[2] == 16 or format[2] == 32:
            size = self.fileHandle.readinto(data)
        elif format[2] == 24:
            data = self.read24(format,data)
            size = len(data)

        self.set_5(data)
        self.junkspersecond = timescaler / self.JUNKSIZE
        self.count = 0
        # print(f"Junkspersec:{self.junkspersecond}")
        while size > 0 and self.stopix is False:
            
            if TEST is False:
                if self.pausestate is False:
                    try:
                        self.stemlabcontrol.data_sock.send(
                                                self.gain*data[0:size].astype(np.float32)
                                                /scl)  # send next 4096 samples
                        # scl war ursprgl 32767 TODO remove comment nach Abspiel-Tests
                    except BlockingIOError:
                        print("Blocking data socket error in playloop worker")
                        time.sleep(0.1)
                        self.SigFinished.emit()
                        time.sleep(0.1)
                        return
                    except ConnectionResetError:
                        print("Connection data socket error in playloop worker")
                        time.sleep(0.1)
                        self.SigFinished.emit()
                        time.sleep(0.1)
                        return
                    except Exception as e:
                        print("Class e type error  data socket error in playloop worker")
                        print(e)
                        time.sleep(0.1)
                        self.SigFinished.emit()
                        time.sleep(0.1)
                        return
                    if format[2] == 16 or format[2] == 32:
                        size = self.fileHandle.readinto(data)
                    elif format[2] == 24:
                        data = self.read24(format,data)
                        size = len(data)

                    #  read next 2048 samples
                    self.count += 1
                    if self.count > self.junkspersecond:
                        self.SigIncrementCurTime.emit()
                        self.count = 0
                        #self.mutex.lock()
                        self.gain = self.__slots__[6]
                        #print(f"diagnostic: gain in worker: {self.gain}")
                        self.set_5(data)
                        #self.mutex.unlock()
                else:
                    #print("dontknowwhat")
                    time.sleep(0.1)
                    if self.stopix is True:
                        break
            else:
                if self.pausestate is False:
                    #print("test reached")
                    if format[2] == 16 or format[2] == 32:
                        size = self.fileHandle.readinto(data)
                    elif format[2] == 24:
                        data = self.read24(format,data)
                        size = len(data)
                    #print(f"size read: {size}")
                    #print(data[1:10])
                    #size = self.fileHandle.readinto(data)
                    time.sleep(0.0001)
                    #  read next 2048 bytes
                    self.count += 1
                    if self.count > self.junkspersecond and size > 0:
                        #print('timeincrement reached')
                        self.SigIncrementCurTime.emit()
                        self.gain = self.__slots__[6]
                        #print(f"diagnostic: gain in worker: {self.gain}")
                        #print(f"maximum: {np.max(data)}")
                        #self.set_5(self.gain*data)
                        self.set_5(data)
                        self.count = 0
                else:
                    time.sleep(1)
                    if self.stopix is True:
                        break
        #print('worker  thread finished')
        self.SigFinished.emit()
        print("SigFinished from playloop emitted")


    def stop_loop(self):
        self.stopix = True

    def resetCounter(self):
        self.count = 0

    def read24(self,format,data):
       for lauf in range(0,self.DATABLOCKSIZE):
        d = self.fileHandle.read(3)
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
       
class playrec_m(QObject):
    __slots__ = ["None"]
    SigModelXXX = pyqtSignal()

    #TODO: replace all gui by respective state references if appropriate
    def __init__(self):
        super().__init__()
        # Constants
        self.CONST_SAMPLE = 0 # sample constant
        self.mdl = {}
        self.mdl["sample"] = 0

class playrec_c(QObject):
    """_view method
    """
    __slots__ = ["contvars"]

    SigAny = pyqtSignal()

    def __init__(self, abstract_module_m): #TODO: remove gui
        super().__init__()

    # def __init__(self, *args, **kwargs): #TEST 09-01-2024
    #     super().__init__(*args, **kwargs)
        viewvars = {}
        self.m = abstract_module_m.mdl
        
class playrec_v(QObject):
    """_view methods for resampling module
    TODO: gui.wavheader --> something less general ?
    """
    __slots__ = ["viewvars"]

    SigAny = pyqtSignal()
    SigCancel = pyqtSignal()
    SigUpdateGUI = pyqtSignal(object)
    SigSyncGUIUpdatelist = pyqtSignal(object)

    def __init__(self, gui, abstract_module_c, abstract_module_m):
        super().__init__()

        self.m = abstract_module_m.mdl
        self.DATABLOCKSIZE = 1024*32
        self.gui = gui

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
        print("playrec: updateGUIelements")
        #self.gui.DOSOMETHING

    def update_GUI(self,_key): #TODO TODO: is this method still needed ? reorganize. gui-calls should be avoided, better only signalling and gui must call the routenes itself
        print(" view spectra updateGUI: new updateGUI in view spectra module reached")
        self.SigUpdateGUI.disconnect(self.update_GUI)
        if _key.find("ext_update") == 0:
            #update resampler gui with all elements
            #TODO: fetch model values and re-fill all tab fields
            print("playrec update_GUI reached")
            pass
        #other key possible: "none"
        #DO SOMETHING
        self.SigUpdateGUI.connect(self.update_GUI)