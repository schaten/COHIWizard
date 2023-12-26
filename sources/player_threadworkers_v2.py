
import sys
import time
import os
import numpy as np
import math
import datetime as ndatetime
from datetime import datetime
from socket import socket, AF_INET, SOCK_STREAM
from struct import pack
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import QObject, QThread, pyqtSignal, QMutex
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox
from PyQt5.QtGui import QFont
import paramiko

# class ANYWORKER ?????????????? (QtCore.QThread):
#     '''
#     Class for STEMLAB ssh connection, server start and stop,
#     data stream socket control and shutdown of the STEMLAB LINUX
#     call: set slots with 
#         set_0(Host_Address)
#         set_1([ifreq, rates, irate, icorr])
#         start thread

#     '''
#     __slots__ = ["slot_0", "slot_1"]


#     def __init__(self, host_window):

#         super(StemlabControl, self).__init__()
#         self.host = host_window
#         self.slot_0 = []
#         self.slot_1 = []
#         self.mutex = QtCore.QMutex()



#     def set_0(self,_value):
#         """
#         sets __slots__[0]
#         __slots__[0] has entries: self.HostAddress, IP Address of RP
#         """
#         self.__slots__[0] = _value

#     def get_0(self):
#         return(self.__slots__[0])
    
#     def set_1(self,_value):
#         """
#         sets __slots__[1]
#         __slots__[1] has entries: ifreq, rates, irate, icorr
#         """
#         self.__slots__[1] = _value

#     def get_1(self):
#         return(self.__slots__[1])

class StemlabControl(QObject):
    '''
    Class for STEMLAB ssh connection, server start and stop,
    data stream socket control and shutdown of the STEMLAB LINUX
    TODO: reprogram for communication via slots

    '''
    def __init__(self, sdr_params, *args, **kwargs):

        self.HostAddress = sdr_params.pop("HostAddress")
        self.ifreq = sdr_params.pop("ifreq")
        self.rates = sdr_params.pop("rates")
        self.irate = sdr_params.pop("irate")
        self.icorr = sdr_params.pop("icorr")
        super().__init__(*args, **kwargs)
        # self.ifreq = STM_cont_params["ifreq"]
        # self.rates = STM_cont_params["rates"]
        # self.irate = STM_cont_params["irate"]
        # self.icorr = STM_cont_params["icorr"]
        
        #self.HostAddress = STM_cont_params["HostAddress"]

    def set_play(self):
        self.modality = "play"
        print("set play")

    def set_rec(self):
        self.modality = "rec"

    def monitor(self):
        # print(f"Stemlabcontrol modality: {self.modality}")
        pass

    def config_socket(self):     ##TODO: atgument (self,modality) 
        '''
        initialize stream socket for communication to sdr_transceiver_wide on
        the STEMLAB
        returns as errorflag 'False' if an error occurs, else it returns 'True'
        In case of unsuccessful socket setup popup error messages are sent

        params: STM_cont_params = {"HostAddress": HostAddress
                                "ifreq": ifreq,
                                  "rates": rates,
                                  "irate": irate,
                                  "icorr": icorr}

        Returns:
            True if socket can be configures, False in case of error
            requires self.modality to have been set by set_play() or set_rec()
        '''
        self.ctrl_sock = socket(AF_INET, SOCK_STREAM)
        self.ctrl_sock.settimeout(5)
        try:
            self.ctrl_sock.connect((self.HostAddress, 1001))
        except:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Socket Connection Error")
            msg.setInformativeText(
                                  "Cannot establish socket connection "
                                  "for streaming to the STEMLAB")
            msg.setWindowTitle("Socket Connection Error")
            msg.exec_()
            return False

        self.ctrl_sock.settimeout(None)

        self.data_sock = socket(AF_INET, SOCK_STREAM)
        self.data_sock.settimeout(5)
        try:
            self.data_sock.connect((self.HostAddress, 1001))
        except:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Socket Connection Error")
            msg.setInformativeText(
                                  "Cannot establish socket connection "
                                  "for streaming to the STEMLAB")
            msg.setWindowTitle("Socket Connection Error")
            msg.exec_()
            return False

        self.data_sock.settimeout(None)

        if (self.modality != "play") and (self.modality != "rec"):
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Socket Configuration Error")
            msg.setInformativeText("Error , self.modality must be rec or play")
            msg.setWindowTitle("Socket Configuration Error")
            msg.exec_()
            return False

        # send control parameters to ctrl_sock:

        ifreq = self.ifreq
        rates = self.rates
        irate = self.irate
        icorr = self.icorr
        
        if self.modality == "play":
            self.ctrl_sock.send(pack('<I', 2))
            self.ctrl_sock.send(pack('<I', 0 << 28
                                     | int((1.0 + 1e-6 * icorr)
                                           * ifreq)))
            self.ctrl_sock.send(pack('<I', 1 << 28 | rates[irate]))
            self.data_sock.send(pack('<I', 3))
        else:
            self.ctrl_sock.send(pack('<I', 0))
            self.ctrl_sock.send(pack('<I', 0 << 28
                                     | int((1.0 + 1e-6 * icorr)
                                           * ifreq)))
            self.ctrl_sock.send(pack('<I', 1 << 28 | rates[irate]))

            self.data_sock.send(pack('<I', 1))

        # TODO in further versions: diagnostic output to status message window
        # ("socket started")
        return True

    def startssh(self):
        '''
        login to Host and start ssh session with STEMLAB
        Returns False if a connection error occurs, returns True if
        successful
        '''
        #TODO: nicht auf host Window zugreifen ! self.HostAddress = self.host.ui.lineEdit_IPAddress.text() ##########################
        port = 22
        username = "root"
        password = "root"
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            self.ssh.connect(self.HostAddress, port, username, password)
            print('ssh connection successful')
            return True
        except:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Connection Error")
            msg.setInformativeText(
                                  "Cannot connect to Host " + self.HostAddress)
            msg.setWindowTitle("Error")
            msg.exec_()
            return False

    def sshsendcommandseq(self, shcomm):
        '''
        send ssh command string sequence via command string list shcomm
        '''
        count = 0
        while (count < len(shcomm)):  #TODO REM FIN check list, only diagnostic    
            self.ssh.exec_command(shcomm[count])
            count = count + 1
            time.sleep(0.1)

        #TODO: diagnostic output to status message window ("ssh command sent")

    def sdrserverstart(self):
        '''
        Purpose: start server sdr-transceiver-wide on the STEMLAB.
        Stop potentially running server instance before so as to prevent
        undefined communication
        '''

        # TODO: future versions could send diagnostic output to status message indicator
        shcomm = []
        shcomm.append('/bin/bash /sdrstop.sh &')
        shcomm.append('/bin/bash /sdrstart.sh &')

        # connect to remote server via ssh
        if self.startssh() is False:
            return
       # TODO: future versions could send diagnostic output to status message indicator
        self.sdrserverstop()  #TODO ?is this necessary ?
        time.sleep(0.1)
        self.sshsendcommandseq(shcomm)
       # TODO: future versions could send diagnostic output to status message indicator
        print('STM serverstart connection successful')

    def sdrserverstop(self):
        '''
        Purpose: stop server sdr-transceiver-wide on the STEMLAB.
        '''
        shcomm = []
        shcomm.append('/bin/bash /sdrstop.sh &')
        self.sshsendcommandseq(shcomm)

    def RPShutdown(self):
        '''
        Purpose: Shutdown the LINUX running on the STEMLAB
        Sequence:   (1) stop server sdr-transceiver-wide on the STEMLAB.
                    (2) send 'halt' command via ssh, track result via stdout
                    (3) communicate steps and progress via popup messages
        '''

        if self.startssh() is False:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setText("ignoring command")
            msg.setInformativeText(
                              "No Connection to STEMLAB or STEMLAB OS is down")
            msg.setWindowTitle("MISSION IMPOSSIBLE")
            msg.exec_()
            return
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setText("SHUTDOWN")
        msg.setInformativeText(
                              "Shutting down the STEMLAB !"
                              "Please wait until heartbeat stops flashing")
        msg.setWindowTitle("SHUTDOWN")
        msg.exec_()
        self.sdrserverstop()
        stdin, stdout, stderr = self.ssh.exec_command("/sbin/halt >&1 2>&1")
        chout = stdout.channel
        textout = ""
        while True:
            bsout = chout.recv(1)
            textout = textout + bsout.decode("utf-8")
            if not bsout:
                break
        # print(f"stdout: {textout}")
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setText("POWER DOWN")
        msg.setInformativeText("It is now safe to power down the STEMLAB")
        msg.setWindowTitle("SHUTDOWN")
        msg.exec_()


def stop_worker(self):
    if self.playthreadActive:
        self.playrec.stop_loop()
    self.timertick.stoptick()