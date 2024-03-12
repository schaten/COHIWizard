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
import os 
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from scipy import signal as sig
import yaml
from auxiliaries import auxiliaries as auxi
from auxiliaries import WAVheader_tools, timer_worker
from datetime import datetime
import datetime as ndatetime
from stemlab_control import StemlabControl


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
        self.mdl["playlist_active"] == False
        self.mdl["sample"] = 0
        self.mdl["LO_offset"] = 0
        self.mdl["UTC"] = False
        self.mdl["TEST"] = False
        self.m["Buttloop_pressed"] = False


class playrec_c(QObject):
    """_view method
    """
    __slots__ = ["contvars"]

    SigAny = pyqtSignal()
    SigRelay = pyqtSignal(str,object)
    SigEOFStart = pyqtSignal()
    SigActivateOtherTabs = pyqtSignal(str,str,object)

    def __init__(self, playrec_m): #TODO: remove gui
        super().__init__()

    # def __init__(self, *args, **kwargs): #TEST 09-01-2024
    #     super().__init__(*args, **kwargs)
        viewvars = {}
        self.m = playrec_m.mdl
        self.stemlabcontrol = StemlabControl()
        self.m["playlist_ix"] = 0

    def checkSTEMLABrates(self):        # TODO: this is ratrer a controller method than a GUI method. Transfer to other module
        """
        CONTROLLER
        _checks if the items ifreq, irate and icorr in system_state have the proper values acc. to RFCorder filename convention
        checks if system_state["irate"] has a value out of the values defined for the STEMLAB in system_state["rates"] 
        :param: none
        :type: none
        ...
        :raises TODO [popup error message]: corresponding to different format errors
        ...
        :return: True/False acc to success of the check
        :rtype: bool
        """
        #system_state = sys_state.get_status()
        self.m["errorf"] = False
        #check: has been done on 13-12-2023 TODO: replace ifreq by system_state["ifreq"]
        if self.m["ifreq"] < 0 or self.m["ifreq"] > 62500000:
            self.m["errorf"] = True
            self.m["errortxt"] = "center frequency not in range (0 - 62500000) \
                      after _lo\n Probably not a COHIRADIA File"

        if self.m["irate"] not in self.m["rates"]:
            self.m["errorf"] = True
            self.m["errortxt"] = "The sample rate of this file is inappropriate for the STEMLAB!\n\
            Probably it is not a COHIRADIA File. \n \n \
            PLEASE USE THE 'Resample' TAB TO CREATE A PLAYABLE FILE ! \n\n \
            SR must be in the set: 20000, 50000, 100000, 250000, 500000, 1250000, 2500000"
            
        if self.m["icorr"] < -100 or self.m["icorr"] > 100:
            self.m["errorf"] = True
            self.m["errortxt"] = "frequency correction min ppm must be in \
                      the interval (-100 - 100) after _c \n \
                      Probably not a COHIRADIA File "

    def play_manager(self):
        """Callback function for Play Button; Calls file_open
           starts data streaming to STEMLAB sdr server via method play_tstarter
        VIEW
        :raises [none]: [none]
        :return: False if IP address not set, File could not be opened
                 False if STEMLAB socket cannot be started
                 False if playback thread cannot be started
                 True if player can be started successfully
        :rtype: Boolean
        """        
        #system_state = sys_state.get_status()
        if self.m["playthreadActive"] is True:
            self.logger.debug("playthread is active, no action")
            return False
        self.updatecurtime(0) #TODO: true datetime from record

        if self.m["f1"] == "": #TODO: replace by line below
            return False
        self.stemlabcontrol.SigError.connect(self.stemlabcontrol_errorhandler)
        self.stemlabcontrol.SigMessage.connect(self.display_status) 
        self.stemlabcontrol.set_play()
        self.modality = "play"
        # start server unless already started
        if self.m["TEST"] is False:
            self.stemlabcontrol.sdrserverstart(self.m["sdr_configparams"])
            self.logger.info(f'play_manager configparams: {self.m["sdr_configparams"]}')
            #sys_state.set_status(system_state)
            if self.stemlabcontrol.config_socket(self.m["sdr_configparams"]):
                self.logger.info("playthread now activated in play_manager")
                self.play_tstarter()
            else:
                #sys_state.set_status(system_state)
                return False
        else:
            if self.play_tstarter() is False:
                #sys_state.set_status(system_state)
                return False
        #TODO: activateself.gui.label_RECORDING.setStyleSheet(('background-color: \
        #                                     rgb(46,210,17)'))
        #TODO: activateself.gui.label_RECORDING.setText("PLAY")
        #TODO: activateself.gui.indicator_Stop.setStyleSheet('background-color: rgb(234,234,234)')
        #TODO: activate.gui.pushButton_Rec.setEnabled(False)
            #print("stemlabcontrols activated")
            self.logger.info("stemlabcontrols activated")
        #sys_state.set_status(system_state)
        return True
        
    def play_tstarter(self):  # TODO: Argument (self, modality), modality= "recording", "play", move to module cplayrec controller
        """_start playback via data stream to STEMLAB sdr server
        starts thread 'playthread' for data streaming to the STEMLAB
        instantiates thread worker method
        initializes signalling_
        CONTROLLER
        :return: _False if error, True on succes_
        :rtype: _Boolean_
        '''
        Purpose: 
        SigFinished:                 emitted by: thread worker on end of stream
                thread termination, activate callback for Stop button
        thread.finished:
                thread termination
        thread.started:
                start worker method streaming loop
        SigIncrementCurTime:         emitted by: thread worker every second
                increment playtime counter by 1 second
        Returns: False if error, True on success
        """        
        print("file opened in playloop thread starter")
        if self.m["wavheader"]['nBitsPerSample'] == 16 or self.m["wavheader"]['nBitsPerSample'] == 24 or self.m["wavheader"]['nBitsPerSample'] == 32:
            pass
            #TODO: Anpassen an andere Fileformate, Einbau von Positionen 
        else:
            auxi.standard_errorbox("dataformat not supported, only 16, 24 and 32 bits per sample are possible")
            return False
        #system_state = sys_state.get_status()
        self.playthread = QThread()
        self.playrec_tworker = playrec_worker(self.stemlabcontrol)
        self.playrec_tworker.moveToThread(self.playthread)
        self.playrec_tworker.set_0(self.m["f1"])
        self.playrec_tworker.set_1(self.m["timescaler"])
        self.playrec_tworker.set_2(self.m["TEST"])
        self.playrec_tworker.set_3(self.m["modality"])
        self.playrec_tworker.set_6(self.m["gain"])
        format = [self.m["wavheader"]["wFormatTag"], self.m["wavheader"]['nBlockAlign'], self.m["wavheader"]['nBitsPerSample']]
        self.playrec_tworker.set_7(format)
        
        self.prfilehandle = self.playrec_tworker.get_4() #TODO CHECK IF REQUIRED test output, no special other function
        #if self.m["modality"] == "play": #TODO: activate
        if True:
            self.playthread.started.connect(self.playrec_tworker.play_loop16)
        # else:
        #     self.playthread.started.connect(self.playrec_tworker.rec_loop)

        self.playrec_tworker.SigFinished.connect(self.EOF_manager)
        self.SigEOFStart.connect(self.EOF_manager)
        self.playrec_tworker.SigFinished.connect(self.playrec_tworker.deleteLater)

        self.playthread.finished.connect(self.playthread.deleteLater)
        self.playrec_tworker.SigIncrementCurTime.connect(
                                                lambda: self.updatecurtime(1))
        self.playrec_tworker.SigIncrementCurTime.connect(self.showRFdata)
        #self.playrec_tworker.SigBufferUnderflow.connect(
        #                                         lambda: self.bufoverflowsig()) #TODO reactivate
        # TODO: check, if updatecurtime is also controlled from within
        # the recording loop
        self.playthread.start()
        if self.playthread.isRunning():
            self.playthreadActive = True
            #self.setactivity_tabs("Player","inactivate",[]) #TODO remove after tests
            self.SigActivateOtherTabs.emit("Player","inactivate",[])
            self.logger.info("playthread started in playthread_threadstarter = play_tstarter() (threadstarter)")
            # TODO replace playthreadflag by not self.playthread.isFinished()
            #sys_state.set_status(system_state)
            return True
        else:
            auxi.standard_errorbox("STEMLAB data transfer thread could not be started")
            #sys_state.set_status(system_state)
            return False

    def EOF_manager(self):
        """_target of SigFinished from playloop. If signal is received, a decision is made whether 
            to stop the player completely, 
            continue with next file if 'nextfile' in wavheader exists
            continue restarting the same file as long as in endless mode_

        :param : none
        :type : none
        '''
        :raises [ErrorType]: [ErrorDescription]
        '''
        :return:
        :rtype:
        """ 
        #TODO: check why this sequence incl file close needs to be outside the playthred worker; causes some problems
        prfilehandle = self.playrec_tworker.get_4()
        self.playthread.quit()
        self.playthread.wait()
        time.sleep(0.1)
        prfilehandle.close()
        self.m["fileopened"] = False #OBSOLETE ?
        self.SigRelay.emit("cm_all_",["fileopened",False])
        if self.m["stopstate"] == True:
            self.logger.info("EOF-manager: player has been stopped")
            time.sleep(0.5)
            return
        if (os.path.isfile(self.m["my_dirname"] + '/' + self.m["wavheader"]['nextfilename']) == True and self.wavheader['nextfilename'] != "" ):
            # play next file in nextfile-list
            self.m["f1"] = self.m["my_dirname"] + '/' + self.m["wavheader"]['nextfilename']
            self.SigRelay.emit("cm_all_",["f1",self.m["my_dirname"] + '/' + self.m["wavheader"]['nextfilename']])
            self.SigRelay.emit("cm_all_",["my_filename",self.m["my_filename"]])
            self.m["wavheader"] = WAVheader_tools.get_sdruno_header(self,self.m["f1"])
            time.sleep(0.1)
            self.play_tstarter()
            time.sleep(0.1)
            self.m["fileopened"] = True
            self.SigRelay.emit("cm_all_",["fileopened",True])
            #TODO: self.my_filename + self.ext müssen updated werden, übernehmen aus open file
            #self.showfilename() #Remove after implementing all Modules Relay
            self.SigRelay.emit("cexex_all_",["updateGUIelements",0])
            self.updatecurtime(0) #TODO: true datetime from record
            self.logger.info("fetch nextfile")
        elif self.m["Buttloop_pressed"]:
            time.sleep(0.1)
            #("restart same file in endless loop")
            self.logger.debug("restart same file in endless loop")
            #no next file, but endless mode active, replay current system_state["f1"]
            self.play_tstarter()
            time.sleep(0.1)
            self.logger.info("playthread active: %s", self.playthreadActive)
            self.m["fileopened"] = True
            self.SigRelay.emit("cm_all_",["fileopened",True])
            self.updatecurtime(0) #TODO: true datetime from record
        elif self.m["playlist_len"] > 0:
            # filecheck_loop = True
            # while filecheck_loop == True:
            if self.m["playlist_ix"] == 0:
                self.m["playlist_ix"] += 1 #TODO: aktuell Hack, um bei erstem File keine Doppelabspielung zu triggern
            if self.m["playlist_ix"] < self.m["playlist_len"]: #TODO check if indexing is correct
                self.playthreadActive = False
                #print(f"EOF manager: playlist index: {system_state['playlist_ix']}")
                self.logger.debug("EOF manager: playlist index: %i", self.m['playlist_ix'])
                lw = self.m["playlist"] #ODO: simplify by replacing lw below
                self.logger.info("fetch next list file")
                item_valid = False
                while (not item_valid) and (self.m["playlist_ix"] < self.m["playlist_len"]):
                    item = lw.item(self.m["playlist_ix"])
                    self.m["f1"] = self.m["my_dirname"] + '/' + item.text() #TODO replace by line below
                    self.SigRelay.emit("cm_all_",["f1",self.my_dirname + '/' + item.text()])
                    self.SigRelay.emit("cm_all_",["my_filename",self.my_filename])
                    self.logger.info("EOF manager file: %s", self.m["f1"])
                    self.m["wavheader"] = WAVheader_tools.get_sdruno_header(self,self.m["f1"])
                    item_valid = True
                    if not self.m["wavheader"]:
                        self.logger.warning("EOF_manager: wrong wav file, skip to next listentry")
                        self.m["playlist_ix"] += 1
                        item_valid = False

                if not (self.m["playlist_ix"] < self.m["playlist_len"]):
                    self.m["playlist_ix"] = 0
                    #sys_state.set_status(system_state)
                    self.logger.info("EOF_manager: end of list, stop player")
                    time.sleep(0.5)
                    self.updatecurtime(0)
                    self.cb_Butt_STOP()
                    #########################################----> view
        
                    #self.gui.listWidget_playlist.clear()
                    self.SigRelay.emit("cm_playrec",["reset_GUI",0])
                    #self.gui.listWidget_sourcelist.clear()
                    #sys_state.set_status(system_state)
                    return()
                
                self.m["playlist_ix"] += 1                #TODO: self.m Eintragung von icorr etc erfolgt an mehreren STellen, fileopen, extract dat header und hier. Könnte an einer Stelle passieren, immer, sobald ein wav-header extrahiert wird
                self.m["ifreq"] = self.m["wavheader"]['centerfreq'] + self.m["LO_offset"]
                self.m["irate"] = self.m["wavheader"]['nSamplesPerSec']
                self.m["icorr"] = 0
                self.m["readoffset"] = self.readoffset
                self.m["timescaler"] = self.m["wavheader"]['nSamplesPerSec']*self.m["wavheader"]['nBlockAlign']
                #print(f'EOF manager new wavheader: {self.wavheader["nSamplesPerSec"]}')
                self.logger.debug("EOF manager new wavheader: %i", self.m["wavheader"]["nSamplesPerSec"])
                #TODO: write new header to wav edior
                #sys_state.set_status(system_state)
                time.sleep(0.1)
                self.showfilename()
                if not self.m["TEST"]:
                    self.stemlabcontrol.sdrserverstop()
                    self.logger.info("EOF manager start play_manager")
                self.play_manager()
                self.m["fileopened"] = True
                self.SigRelay.emit("cm_all_",["fileopened",True])
                time.sleep(0.5) #TODO: necessary because otherwise file may not yet have been opened by playloopworker and then updatecurtime crashes because of invalid filehandel 
                #may be solved by updatecurtime not accessing the filehandle returned from playworker but directly from self.m["f1"]
                self.updatecurtime(0) #TODO: true datetime from record
            else:
                #reset playlist_ix
                self.m["playlist_ix"] = 0
                #sys_state.set_status(system_state)
                self.logger.info("EOF_manager: stop player")
                time.sleep(0.5)
                self.updatecurtime(0)

                #########################################----> view
                self.cb_Butt_STOP()

                #########################################----> view
                # self.gui.listWidget_playlist.clear()
                # self.gui.listWidget_sourcelist.clear()
                self.SigRelay.emit("cm_playrec",["reset_GUI",0])
        
        else:
            #no next file,no endless loop --> stop player
            #print("stop player")
            self.logger.info("EOF_manager: stop player 2")
            time.sleep(0.5)
            self.cb_Butt_STOP()
            ##TODO: introduce separate stop_manager
            # if self.playthread.isRunning():
            # self.playthreadActive = True
        #sys_state.set_status(system_state)

    def cb_Butt_STOP(self):
        """
        Callback function for Stop Button; 
        sets stopstate flag True
        stops playrec_thread
        stops sdrserver if running --> stops data streaming to STEMLAB sdr server
        resets all player buttons to initial state
        set all tabs which 
        :raises [none]: [none]
        :return: none
        :rtype: none
        """        
        #TODO: activate for player
        #if True:
        self.stopstate = True
        if self.m["playthreadActive"] is False:
            self.m["fileopened"] = False ###CHECK
            self.SigRelay.emit("cm_all_",["fileopened",False])
            #sys_state.set_status(system_state) ####Remove after core full impl
            return
        if self.m["playthreadActive"]:
            self.playrec_tworker.stop_loop()
        if self.m["TEST"] is False:
            self.stemlabcontrol.sdrserverstop()
        self.updatecurtime(0)        # reset playtime counter #TODO: true datetime from record

        self.SigRelay.emit("cexex_playrec",["reset_playerbuttongoup",0])
        self.SigRelay.emit("cexex_win",["GUIreset",0])
        #self.SigGUIReset.emit()

    def jump_1_byte(self):             #increment current time in playtime window and update statusbar
        """
        _increments file reading position by +1 byte for manually correcting for sample jumps 
        which deviate from integer multiples of sample size (4, 8); possible needs to be repeated several times
        this is an emergency method for exceptional usecases and not for regular operation
        if self.modality == "play":
            - update position slider
            - set file read pointer to new position, |if increment| > 1
        :param : none
        :type : int
        '''
        :raises [ErrorType]: [ErrorDescription]
        '''
        :return: True/False on successful/unsuccesful operation
        :rtype: bool
        """ 
        self.logger.debug("tracking: jump 1 byte")
        if self.modality == 'play' and self.m["pausestate"] is False:
            if self.m["fileopened"] is True:
                self.prfilehandle = self.playrec_tworker.get_4()
                self.prfilehandle.seek(1,1) #TODO: ##OPTION from current position## 0 oder 1 ?
        # TODO: not yet safe, because increment may happen beyond EOF, check for EOF
                

    def jump_to_position(self):
        """
        VIEW 

        :param : none
        :type : none
        '''
        :raises [ErrorType]: [ErrorDescription]
        '''
        :return: none
        :rtype: none
        """ 
        #print("jumptoposition reached")
        self.logger.debug("jumptoposition reached")
        #system_state = sys_state.get_status()
        ####################################################################
        #sbposition = self.ui.ScrollBar_playtime.value() #TODO: already in updatecurtime(...)
        #ERSETZE DURCH: ####################################################
        sbposition = self.m["playprogress"]
        ####################################################################
        self.curtime = int(np.floor(sbposition/1000*self.m["playlength"]))  # seconds
        timestr = str(self.m["wavheader"]['starttime_dt'] + ndatetime.timedelta(seconds=self.curtime))
        #win.ui.lineEditCurTime.setText(timestr)
        self.SigRelay.emit("cexex_playrec",["setplaytimedisplay",timestr])
        #self.ui.lineEditCurTime.setText(timestr)
        position_raw = self.curtime*self.m["timescaler"]  #timescaler = bytes per second
        # TODO: check, geändert 09-12-2023: byte position mit allen Blockaligns auch andere als 4(16 bits); 
        # TODO: adapt for other than header 216
        position = min(max(216, position_raw-position_raw % self.m["wavheader"]['nBlockAlign']),
                            self.m["wavheader"]['data_nChunkSize']+216) # guarantee reading from integer multiples of 4 bytes, TODO: change '4', '216' to any wav format ! 
        if self.m["fileopened"] is True:
            #print("Jump to next position")
            self.logger.debug("jumptoposition reached")
            #print(f'system_state["fileopened"]: {system_state["fileopened"]}')
            self.logger.debug("system_state['fileopened']: %s",self.m["fileopened"])
            self.prfilehandle = self.playrec_tworker.get_4()
            self.prfilehandle.seek(int(position), 0) #TODO: Anpassen an andere Fileformate
        #calculate corresponding position in the record file; value = 216 : 1000
        #jump to the targeted position with integer multiple of wavheader["nBitsPerSample"]/4
        #sys_state.set_status(system_state)


class playrec_v(QObject):
    """_view methods for resampling module
    TODO: gui.wavheader --> something less general ?
    """
    __slots__ = ["viewvars"]

    SigAny = pyqtSignal()
    SigCancel = pyqtSignal()
    SigUpdateGUI = pyqtSignal(object)
    SigSyncGUIUpdatelist = pyqtSignal(object)
    SigGUIReset =pyqtSignal()
    SigRelay = pyqtSignal(str,object)
    SigActivateOtherTabs = pyqtSignal(str,str,object)

    def __init__(self, gui, playrec_c, playrec_m):
        super().__init__()

        self.m = playrec_m.mdl
        self.DATABLOCKSIZE = 1024*32
        self.GAINOFFSET = 40
        self.gui = gui
        self.playrec_c = playrec_c
        self.timertick = timer_worker()
        self.m["UTC"] = False
        self.m["TEST"] = False
        self.init_playrec_ui()

    def init_playrec_ui(self):
        self.gui.pushButton_Loop.setChecked(False)
        self.gui.pushButton_Loop.clicked.connect(self.Buttloopmanager)
        self.ui.listWidget_playlist.model().rowsInserted.connect(lambda: self.playlist_update())
        self.ui.listWidget_playlist.model().rowsRemoved.connect(lambda: self.playlist_update()) 


    def Buttloopmanager(self):
        if self.gui.pushButton_Loop.isChecked == True:
            self.m["Buttloop_pressed"] = True
        else:
            self.m["Buttloop_pressed"] = False

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
        self.gui.checkBox_UTC.clicked.connect(self.toggleUTC)
        self.gui.checkBox_TESTMODE.clicked.connect(self.toggleTEST)

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

    def reset_GUI(self):
        self.gui.listWidget_playlist.clear()
        self.gui.listWidget_sourcelist.clear()


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
        if _key.find("cm_playrec") == 0 or _key.find("cm_all_") == 0:
            #set mdl-value
            self.m[_value[0]] = _value[1]
        if _key.find("cui_playrec") == 0:
            _value[0](_value[1]) #STILL UNCLEAR
        if _key.find("cexex_playrec") == 0  or _key.find("cexex_all_") == 0:
            if  _value[0].find("updateGUIelements") == 0:
                self.updateGUIelements()
            if  _value[0].find("reset_playerbuttongoup") == 0:
                self.reset_playerbuttongroup()
            if  _value[0].find("reset_GUI") == 0:
                self.reset_GUI()
            if  _value[0].find("setplaytimedisplay") == 0:
                self.gui.lineEditCurTime.setText(_value[1])



    def toggleUTC(self):
        if self.gui.checkBox_UTC.isChecked():
            self.m["UTC"] = True #TODO: check if is needed in view, otherwise make local or ebven just pass to 
        else:
            self.m["UTC"] = False
    
    def toggleTEST(self):
        if self.gui.checkBox_TESTMODE.isChecked():
            self.m["TEST"] = True 
        else:
            self.m["TEST"] = False

    def cb_Butt_toggle_playlist(self):
        #system_state = sys_state.get_status()
        if self.m["playlist_active"] == False:
            self.gui.pushButton_act_playlist.setChecked(True)
            self.gui.listWidget_sourcelist.setEnabled(True)
            self.gui.listWidget_playlist.setEnabled(True)
            self.m["playlist_active"] = True
        else:
            self.gui.pushButton_act_playlist.setChecked(False)
            self.gui.listWidget_sourcelist.setEnabled(False)
            self.gui.listWidget_playlist.setEnabled(False)
            self.m["playlist_active"] = False

    def playlist_update(self): #TODO: list is only updated up to the just before list change dragged item,
        """
        VIEW
        updates playlist whenever the playlist Widget is changed
        :param: none
        :type: none
        ...
        :raises: none
        ...
        :return: none
        :rtype: none
        """
        #print("playlist updated")  
        self.logger.info("playlist_update: playlist updated")
        
        time.sleep(1)
        #system_state = sys_state.get_status()
        #get all items of playlist Widget and write them to system_state["playlist"]
        lw = self.gui.listWidget_playlist
        # let lw haven elements in it.
        self.m["playlist"] = []
        for x in range(lw.count()-1):
            item = lw.item(x)
            #playlist.append(lw.item(x))
            self.m["playlist"].append(item.text())
        self.m["playlist"] = self.m["playlist"]
        self.m["playlist_len"] = self.gui.listWidget_playlist.count()
        #self.SigRelay.emit("cm_playrec",["playlist",self.m["playlist"]])

    def cb_setgain(self):
        '''
        Descr
        #TODO
        '''
        if self.m["playthreadActive"] is False:
            return False
        self.gain = 10**((self.gui.verticalSlider_Gain.value() - self.GAINOFFSET)/20)
        #print(f"self.gain in cb:  {self.gain}")
        self.playrec_tworker.set_6(self.gain)   #############TODO TODO TODO
        #print(self.gain)
        #TODO: display gain value somewhere


    def updatetimer(self):
        """
        VIEW: cb of Tab player
        updates timer functions
        shows date and time
        changes between UTC and local time
        manages recording timer
        :param: none
        :type: none
        ...
        :raises: none
        ...
        :return: none
        :rtype: none
        """
        if self.gui.checkBox_UTC.isChecked():
            self.UTC = True #TODO:future system state
        else:
            self.UTC = False
        if self.gui.checkBox_TESTMODE.isChecked():
            self.TEST = True #TODO:future system state
        else:
            self.TEST = False

        if self.UTC:
            dt_now = datetime.now(ndatetime.timezone.utc)
            self.gui.label_showdate.setText(
                dt_now.strftime('%Y-%m-%d'))
            self.gui.label_showtime.setText(
                dt_now.strftime('%H:%M:%S'))
        else:
            dt_now = datetime.now()
            self.gui.label_showdate.setText(
                dt_now.strftime('%Y-%m-%d'))
            self.gui.label_showtime.setText(
                dt_now.strftime('%H:%M:%S'))

    
    def cb_Butt_toggleplay(self):
        """ 
        toggles the play button between play and pause states
        TODO
        :param: none
        :type: none
        ...
        :raises: none
        ...
        :return: none
        :rtype: none
        """
        if self.gui.pushButton_Play.isChecked() == True:
            self.m["ifreq"] = self.m["wavheader"]['centerfreq'] + self.m["LO_offset"]
            self.m["irate"] = self.m["wavheader"]['nSamplesPerSec']
            if not self.m["fileopened"]:
                if self.gui.radioButton_LO_bias.isChecked() is True:
                    msg = QMessageBox()
                    msg.setIcon(QMessageBox.Question)
                    msg.setText("Apply LO offset")
                    msg.setInformativeText("center frequency offset is activated, the LO will be shifted by "
                        + str(int(self.m["LO_offset"]/1000)) + " kHz. Do you want to proceed ? If no, please inactivate center frequency offset")
                    msg.setWindowTitle("Apply LO offset")
                    msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                    msg.buttonClicked.connect(self.popup)
                    msg.exec_()
                    if self.yesno == "&No":
                        ###RESET playgroup
                        self.reset_playerbuttongroup()
                        self.reset_LO_bias()
                        #sys_state.set_status(system_state)
                        return False

                self.gui.radioButton_LO_bias.setEnabled(False)
                #TODO TODO TODO. HOW TO CALL A CORE FUNCTION ?
                #if self.cb_open_file() is False: #TODO TODO: check if works equally as before, 
                # now the quest is for fileopened and not, if open file returned True
                if self.m["fileopened"] is False:
                    self.reset_playerbuttongroup()
                    #sys_state.set_status(system_state)
                    return False
                if not self.LO_bias_checkbounds():
                    self.reset_playerbuttongroup()
                    return False
                self.gui.lineEdit_LO_bias.setEnabled(False)
                ######Setze linedit f LO_Bias inaktiv
            if not self.playrec_c.checkSTEMLABrates():
                self.reset_playerbuttongroup()
                return False
            self.gui.pushButton_Play.setIcon(QIcon("pause_v4.PNG"))
            if self.playthreadActive == True:
                self.playrec_tworker.pausestate = False
            self.play_manager()
            self.pausestate = False
            self.stopstate = False
            self.gui.ScrollBar_playtime.setEnabled(True)
            self.gui.pushButton_adv1byte.setEnabled(True)
        else:
            self.gui.pushButton_Play.setIcon(QIcon("play_v4.PNG"))
            self.pausestate = True ##TODO CHECK: necessary ? es gibt ja self.playrec_tworker.pausestate
            if self.m["playthreadActive"] == True:
                self.playrec_tworker.pausestate = True

        if self.m["errorf"]:
            auxi.standard_errorbox(self.m["errortxt"])
            
            return False
        else:
            return True

    def shutdown(self):
        '''
        Returns: nothing
        '''
        #system_state = sys_state.get_status()
        self.cb_Butt_STOP()
        self.timertick.stoptick()
        self.playrec_c.stemlabcontrol.RPShutdown(self.m["sdr_configparams"])
        #TODO TODO TODO: check if it would also be fine to instantiate the stemlabcontrol object only here in the player
        #it is certainly not used in other modules

    def stemlabcontrol_errorhandler(self,errorstring):
        """handler for error signals from stemlabcontrol class
            display error in standard errormessagebox
            NOT YET IMPLEMENTED: reset playerbuttongroup and GUI
        VIEW
        :param: errorstring
        :type: str
        :raises [none]: [none]
        :return: none
        :rtype: none
        """     
        auxi.standard_errorbox(errorstring)
        #self.stemlabcontrol.SigError.connect(self.reset_playerbuttongroup) #TODO TODO TODO: wird bis dato nicht emittiert
        #self.stemlabcontrol.SigError.connect(self.reset_GUI) #TODO: wird bis dato nicht emittiert

    def display_status(self,messagestring):
        """handler for message signals from stemlabcontrol class
            display message in GUI status field, if exists
        VIEW
        :param: messaagestring
        :type: str
        :raises [none]: [none]
        :return: none
        :rtype: none
        """         
        #print(f"display status of stemlabcontrol, status = {messagestring}") #TODO: define displaystatus in more elaborate form

    def cb_Butt_REC(self):
        """
        VIEW
        Callback function for REC Button; 
        so far dummy, as not yet implemented
        :raises [none]: [none]
        :return: none
        :rtype: none
        """                
        auxi.standard_errorbox("Recording is not yet implemented in this version of the COHIWizard; Please use RFCorder until a new version has been released")
        return False


    def reset_playerbuttongroup(self):
        """

        """
        #system_state = sys_state.get_status()
        self.gui.pushButton_Play.setIcon(QIcon("play_v4.PNG"))
        self.gui.pushButton_Play.setChecked(False)
        self.gui.pushButton_Loop.setChecked(False)
        self.playthreadActive = False
        #self.activate_tabs(["View_Spectra","Annotate","Resample","YAML_editor","WAV_header"])
        #self.setactivity_tabs("Player","activate",[])
        self.SigActivateOtherTabs.emit("Player","activate",[])
        self.m["fileopened"] = False ###CHECK
        self.SigRelay.emit("cm_all_",["fileopened",False])
        self.gui.radioButton_LO_bias.setEnabled(True)
        self.gui.lineEdit_LO_bias.setEnabled(True)
        self.gui.ScrollBar_playtime.setEnabled(False)
        self.gui.pushButton_adv1byte.setEnabled(False)

    def showRFdata(self):
        """_take over datasegment from player loop worker and caluclate from there the signal volume and present it in the volume indicator
        read gain value and present it in the player Tab
        read data segment and correlate with previous one --> detect tracking errors and correct them_
        GUI Element
        :return: _False if error, True on succes_
        :rtype: _Boolean_
        """        
        self.m["gain"] = self.playrec_c.playrec_tworker.get_6()
        data = self.playrec_c.playrec_tworker.get_5()
        #tracking error detector removed, appears in old main module
        s = len(data)
        nan_ix = [i for i, x in enumerate(data) if np.isnan(x)]
        if np.any(np.isnan(data)):
            self.m["stopstate"] = True
            time.sleep(1)
            data[nan_ix] = np.zeros(len(nan_ix))
            self.logger.error("show RFdata: NaN found in data, length: %i ,maxval: %f , avg: %f" , len(nan_ix),  np.max(data), np.median(data))
            #sys_state.set_status(system_state)
            return(False)
        cv = (data[0:s-1:2].astype(np.float32) + 1j * data[1:s:2].astype(np.float32))*self.m["gain"]
        if self.m["wavheader"]['wFormatTag'] == 1:
            scl = int(2**int(self.m["wavheader"]['nBitsPerSample']-1))-1
        elif self.m["wavheader"]['wFormatTag']  == 3:
            scl = 1 #TODO:future system state
        else:
            auxi.standard_errorbox("wFormatTag is neither 1 nor 3; unsupported Format, this file cannot be processed")
            #sys_state.set_status(system_state)
            return False
        av = np.abs(cv)/scl  #TODO rescale according to scaler from formattag:
        vol = np.mean(av)
        # make vol a dB value and rescale to 1000
        # 900 = 0 dB
        # 1000 = overload und mache Balken rot
        # min Anzeige = 1 entspricht -100 dB
        refvol = 1
        dBvol = 20*np.log10(vol/refvol)
        dispvol = min(dBvol + 80, 100)
        self.gui.progressBar_volume.setValue(int(np.floor(dispvol*10))) 
        if dispvol > 80:
            self.gui.progressBar_volume.setStyleSheet("QProgressBar::chunk "
                    "{"
                        "background-color: red;"
                    "}")
        elif dispvol < 30:
            self.gui.progressBar_volume.setStyleSheet("QProgressBar::chunk "
                    "{"
                        "background-color: yellow;"
                    "}")           
        else:
            self.gui.progressBar_volume.setStyleSheet("QProgressBar::chunk "
                    "{"
                        "background-color: green;"
                    "}")



    def updatecurtime(self,increment):             #increment current time in playtime window and update statusbar
        """
        _increments time indicator by value in increment, except for 0. 
        With increment == 0 the indicator is reset to 0
        if self.modality == "play":
            - update position slider
            - set file read pointer to new position, |if increment| > 1
        :param : increment
        :type : int
        '''
        :raises [ErrorType]: [ErrorDescription]
        '''
        :return: True/False on successful/unsuccesful operation
        :rtype: bool
        """ 
        #self.curtime varies between 0 and system_state["playlength"]
        self.m["playprogress"] = 0
        if self.m["playthreadActive"] is False:
            return False
        timestr = str(self.m["wavheader"]['starttime_dt'] + ndatetime.timedelta(seconds=self.curtime))
        playlength = self.m["wavheader"]['filesize']/self.m["wavheader"]['nAvgBytesPerSec']
        if increment == 0:
            timestr = str(ndatetime.timedelta(seconds=0))
            self.m["curtime"] = 0
            self.gui.lineEditCurTime.setText(timestr)

        if self.m["modality"] == 'play' and self.m["pausestate"] is False:
            if self.m["curtime"] > 0 and increment < 0:
                self.m["curtime"] += increment
            if self.m["curtime"] < playlength and increment > 0:
                self.m["curtime"] += increment
            if playlength > 0:
                self.m["playprogress"] = int(np.floor(1000*(self.m["curtime"]/playlength)))
            else:
                return False
            position_raw = self.m["curtime"]*self.m["timescaler"]
            # TODO: check, geändert 09-12-2023: byte position mit allen Blockaligns auch andere als 4(16 bits); 
            # TODO: adapt for other than header 216
            position = min(max(216, position_raw-position_raw % self.m["wavheader"]['nBlockAlign']),
                           self.m["wavheader"]['data_nChunkSize'])
            # guarantee integer multiple of nBlockalign, > 0, <= filesize
            if increment != -1 and increment != 1 or self.m["timechanged"] == True:
                if self.m["fileopened"] is True:
                    #print(f'increment curtime cond seek cur file open: {system_state["f1"]}')
                    self.prfilehandle = self.playrec_c.playrec_tworker.get_4()
                    self.prfilehandle.seek(int(position), 0) #TODO: Anpassen an andere Fileformate
        #timestr = str(self.wavheader['starttime_dt'] + ndatetime.timedelta(seconds=self.curtime))
        self.gui.lineEditCurTime.setText(timestr) 
        self.gui.ScrollBar_playtime.setProperty("value", self.m["playprogress"])
        #sys_state.set_status(system_state)
        #print("leave updatecurtime")
        return True
    
    def reset_LO_bias(self):
        """ Purpose: reset LO bias setting to 0; 
        :param [ParamName]: none
        :type [ParamName]: none
        :raises none
        :return: none
        :rtype: none
        """
        self.gui.radioButton_LO_bias.setChecked(False)
        self.gui.radioButton_LO_bias.setEnabled(True)
        self.m["LO_offset"] = 0
        self.gui.lineEdit_LO_bias.setText("0")
        self.gui.lineEdit_LO_bias.setStyleSheet("background-color: white")

    def update_LO_bias(self):
        """ Purpose: update LO bias setting; 
        check validity of offset value: isnumeric, integer
        :param [ParamName]: none
        :type [ParamName]: none
        :raises none
        :return: True if successful, otherwise False
        :rtype: Boolean
        """
        if self.playthreadActive:
            return False        
        LObiasraw = self.gui.lineEdit_LO_bias.text().lstrip(" ")
        if len(LObiasraw) < 1:
            return False
        LObias_sign = 1
        if LObiasraw[0] == "-":
            LObias_sign = -1
            LObias_test = LObiasraw.lstrip("-")
            if len(LObias_test)<1:
                return False
        else:
            LObias_test = LObiasraw
        if LObias_test.isnumeric() == True: 
            i_LO_bias = LObias_sign*int(LObias_test)
        else:
            auxi.standard_errorbox("invalid numeral in center frequency offset field, please enter valid integer value (kHz)")
            self.reset_LO_bias()
            return False
        #transfer to systemstate
        if self.ui.radioButton_LO_bias.isChecked() is True:
            self.m["LO_offset"] = int(i_LO_bias*1000)
            self.m["ifreq"] = int(self.m["wavheader"]['centerfreq'] + self.m["LO_offset"])
        return True
    
    def editHostAddress(self):     #TODO Check if this is necessary, rename to cb_.... ! 
        ''' 
        Purpose: Callback for edidHostAddress Lineedit item
        activate Host IP address field and enable saving mode
        Returns: nothing
        '''
        self.gui.Conf_lineEdit_IPAddress.setEnabled(True)
        self.gui.Conf_lineEdit_IPAddress.setReadOnly(False)
        self.gui.Conf_pushButton_IP.clicked.connect(self.set_IP)
        self.gui.Conf_pushButton_IP.setText("save IP Address")
        self.gui.Conf_pushButton_IP.adjustSize()
        self.IP_address_set = False

    def set_IP(self):
        """ 
        set IP Address and save to config yaml
            disable IP address line
            enable Button for editing address 
        :param: none
        :type: none
        ...
        :raises warning message: Read error if config_wizard.yaml does not exist
        ...
        :return: none
        :rtype: none
        """
        #system_state = sys_state.get_status()
        #self.HostAddress = self.gui.Conf_lineEdit_IPAddress.text()
        self.m["HostAddress"] = self.gui.Conf_lineEdit_IPAddress.text()
        #print("IP address read")
        try:
            stream = open("config_wizard.yaml", "r")
            self.metadata = yaml.safe_load(stream)
            stream.close()
        except:
            auxi.standard_errorbox("Cannot open Config File")
            self.logger.error("cannot get metadata")
            #print("cannot get metadata")
        self.metadata["STM_IP_address"] = self.m["HostAddress"]
        stream = open("config_wizard.yaml", "w")
        yaml.dump(self.metadata, stream)

        self.gui.Conf_lineEdit_IPAddress.setReadOnly(True)
        self.gui.Conf_lineEdit_IPAddress.setEnabled(False)
        self.gui.Conf_pushButton_IP.clicked.connect(self.editHostAddress)
        self.gui.Conf_pushButton_IP.setText("Set IP Address")
        self.gui.Conf_pushButton_IP.adjustSize()
        self.SigRelay.emit("cm_xcore",["HostAddress",self.m["HostAddress"]])
        #sys_state.set_status(system_state)
