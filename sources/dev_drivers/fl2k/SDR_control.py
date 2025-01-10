"""
Created on Jan 08 2025

#@author: scharfetter_admin
"""
from PyQt5.QtCore import *
#from pickle import FALSE, TRUE #intrinsic
import time
#from datetime import timedelta
from socket import socket, AF_INET, SOCK_STREAM
import numpy as np
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from scipy import signal as sig

class SDR_control(QObject):
    """     Class for general SDR ssh connection, server start and stop,
    data stream socket control and shutdown of the SDR
    some methods emit a pyqtSignal(str) named SigMessage(messagestring) with argument messagestring 
    two settings are called via methods, i.e. set_play() and set_rec() for selecting play or rec
    :param : no regular parameters; communication occurs via
        __slots__: Dictionary with entries:
        __slots__[0]: irate, Type: int
        __slots__[1]: ifreq = LO, Type integer
        __slots__[2]: icorr Type: integer
        __slots__[3]: rates Type: list
    :raises [ErrorType]: none
    :return: none
    :rtype: none
    """
    __slots__ = ["irate", "ifreq", "icorr", "rates", "HostAddress"]

    
    SigError = pyqtSignal(str)
    SigMessage = pyqtSignal(str)

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)
        # self.HostAddress = self.get_HostAddress()
        # print(f"init stemlabcontrol Hostaddress: {self.HostAddress}")


    def identify(self):
        """return important device characteristics:
        (1) allowed samplingrates as a dict: if discrete: give values, if continuous: give lower and upper bound
        (2) rate_type: discrete or continuous
        (3) RX, TX, or RX & TX
        (3) device name
        (4) device ID
        (5) max_IFREQ
        (6) min IFREQ
        (7) connection type: ethernet, USB, USB_Vethernet
        
        : param: none

        : return: device_ID_dict
        : rtype: dict
        """
        device_ID_dict = {"rates": {10000:0, 100000000:1},
                          "ryte_type": "continuous",
                          "RX": False,
                          "TX": True,
                          "device_name": "fl2k",
                          "device_ID": 1,
                          "max_IFREQ": 100000000,
                          "min_IFREQ": 0,
                          "connection_type": "USB_Vethernet"}
        #connection type USB_Vethernet is virtual, as the device in reality is USB but communication occurs via TCP to IP 127.0.0.1
        return(device_ID_dict)

    def set_play(self):
        self.modality = "play"
        errorstate = False
        value = ""
        # if no play mode available, return error and respective message
        return(errorstate, value)

    def set_rec(self):
        self.modality = "rec"
        errorstate = False
        value = ""
        # if no rec mode available, return error and respective message
        return(errorstate, value)

    def monitor(self):
        # print(f"Stemlabcontrol modality: {self.modality}")
        pass

    def config_socket(self,configparams):     ##TODO: make modality a slot rather than a method 
        '''
        initialize stream socket for communication to sdr_transceiver_wide on
        returns as errorflag 'False' if an error occurs, else it returns 'True'
        In case of unsuccessful socket setup popup error messages are sent
        param: configparams
        type: dict
        Returns:
            True if socket can be configures, False in case of error
            requires self.modality to have been set by set_play() or set_rec()
        '''
        errorstate = False
        value = ""
        print(f'configparams ifreq: {configparams["ifreq"]} , HostAddress: {configparams["HostAddress"]}')
        print(f'configparams irate: {configparams["irate"]} , icorr: {configparams["icorr"]}')
        print(f'configparams rates: {configparams["rates"]} , LO_offset: {configparams["LO_offset"]}')
        ifreq = configparams["ifreq"]
        irate = configparams["irate"]
        rates = configparams["rates"]
        icorr = configparams["icorr"]
        LO_offset = configparams["LO_offset"]
        value = [ifreq, irate, rates, icorr, LO_offset]
        if (self.modality != "play") and (self.modality != "rec"):
            errormessage = "Error , self.modality must be rec or play"
            self.SigError.emit(errormessage)
            errorstate = True
            value = errormessage
            return(errorstate, value)
        self.SigMessage.emit("socket started")
        return (errorstate, value)

    def startssh(self,configparams):
        '''
        login to Host and start ssh session with SDR    
        '''

        errorstate = False
        value = ""
        # start SDR server here (e.g. fl2k_tcp)
        return(errorstate, value)

    def sshsendcommandseq(self, shcomm):
        '''
        send ssh command string sequence via command string list shcomm
        '''
        count = 0
        while (count < len(shcomm)):  #TODO REM FIN check list, only diagnostic    TODO: rewrite loop more pythonian
            try:
                self.ssh.exec_command(shcomm[count])
            except:
                print("stemlab control sshsendcommandseq, command cannot be sent")
            count = count + 1
            time.sleep(0.1)
        self.SigMessage.emit("ssh command sent")

    def sdrserverstart(self,configparams):
        '''
        Purpose: start server on the SDR if this applies.
        Stop potentially running server instance before so as to prevent
        undefined communication
        '''
        errorstate = False
        value = ""
        # start SDR server here (e.g. fl2k_tcp)
        return(errorstate, value)

    def sdrserverstop(self):
        '''
        Purpose: stop server on the SDR.
        '''
        errorstate = False
        value = ""
        # start SDR server here (e.g. fl2k_tcp)
        return(errorstate, value)
        

    def RPShutdown(self,configparams):
        '''
        Purpose: Shutdown the OS on the SDR if applicable
        '''
        errorstate = False
        value = ""
        # start SDR server here (e.g. fl2k_tcp)
        return(errorstate, value)
