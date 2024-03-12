# -*- coding: utf-8 -*-
# Um alle print messages auf logfile umzuleiten: Aktiviere am Ende des init-Teils: sys.stdout = self.logfile
#statt: self.menubar = File(MainWindow)
#self.menubar = QtWidgets.QMenuBar(MainWindow)
#pyinstaller --icon=COHIWizard_ico4.ico –F SDR_COHIWizard_v26.py
#pyuic5 -x  COHIWizard_GUI_v10.ui -o COHIWizard_GUI_v10.py
#TODO: shift action to respective tab machine by: currix = self.ui.tabWidget.currentIndex() self.ui.tabWidget.tabText(currix)
# For reducing to RFCorder: place the following just before the line with 
#check if sox is installed so as to throw an error message on resampling, if not
#        self.soxlink = "https://sourceforge.net/projects/sox/files/sox/14.4.2/"
#Bei Änderungen des Gridlayouts und Neuplazierung der canvas:
#self.generate_canvas(self,self.ui.gridLayout_5,[4,0,7,4],[-1,-1,-1,-1],self.Tabref["Resample"])
#in init_Tabref()
# in the GUI init method:

        # #THIS IS JUST A VERSION OF COHIWizard_v25; Here I disable all unnecessary tabs and functions
        # self.ui.tabWidget.removeTab(4)
        # self.ui.tabWidget.removeTab(3)
        # self.ui.tabWidget.removeTab(2)
        # self.ui.tabWidget.removeTab(1)
        # # Resampling only in direct mode without LO shifting
        # self.ui.lineEdit_resample_targetLO.textEdited.disconnect()
        # self.ui.lineEdit_resample_targetLO.setEnabled(False)
        # self.ui.actionOverwrite_header.setVisible(False)
# Start-Tab setzen:self.ui.tabWidget.setCurrentIndex(1) #TODO: avoid magic number, unidentified

"""
Created on Sa Dec 08 2023

#@author: scharfetter_admin
"""
#from pickle import FALSE, TRUE #intrinsic
import sys
import time
import os
import subprocess
import datetime as ndatetime
from datetime import datetime
#from datetime import timedelta
#from socket import socket, AF_INET, SOCK_STREAM
from struct import pack, unpack
import numpy as np
#from PyQt5.QtCore import QTimer
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg,  NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from scipy import signal as sig
from scipy.ndimage.filters import median_filter
import pandas as pd  #TODO: check, not installed under this name
import yaml
import logging
from COHIWizard_GUI_v10 import Ui_MainWindow as MyWizard
from auxiliaries import WAVheader_tools
from auxiliaries import auxiliaries as auxi
from PyQt5.QtCore import QObject, QThread, pyqtSignal, QMutex       #TODO: OBSOLETE
import system_module as wsys
import resampler_module_v5 as rsmp
import view_spectra as vsp
import yaml_editor as yed
import waveditor as waved
from stemlab_control import StemlabControl
from playrec import playrec_worker
#import playrec
#import configuration as conf

class statlst_gen_worker(QtCore.QThread):
    __slots__ = ["status_position","T","freq","closed"]
    
    SigProgressBar1 = pyqtSignal()
    SigFinished = pyqtSignal()

    def __init__(self, host_window):
        super(statlst_gen_worker, self).__init__()
        self.host = host_window
        self.__slots__[2] = []
        self.__slots__[3] = []
        self.mutex = QtCore.QMutex()

    def set_status_position(self,_value):
        self.__slots__[0] = _value

    def set_T(self,_value):
        self.__slots__[1] = _value

    def set_freq(self,_value):
        self.__slots__[2] = _value

    def set_closed(self,_value):
        self.__slots__[3] = _value                

    def get_status_position(self):  ##TODO: obsolete
        return(self.__slots__[0])
    
    #@njit
    def stationsloop(self):
        """[Summary]TODO

        :param [ParamName]: [ParamDescription], defaults to [DefaultParamVal]
        :type [ParamName]: [ParamType](, optional)
        ...
        :raises [ErrorType]: [ErrorDescription]
        ...
        :return: [ReturnDescription]
        :rtype: [ReturnType]
        """
        try:
            f = open(self.host.stations_filename, 'w', encoding='utf-8')
            # Laufe durch alle Peak-Frequenzen des Spektrums mit index ix
            #make this a thread
            for ix in range(len(self.host.locs_union)):
                progress = np.floor(100*ix/len(self.host.locs_union))
                #print(f"peak index during annotation:{ix}")
                f.write('- frequency: "{}"\n'.format(self.host.annotation["FREQ"][ix]))
                f.write('  snr: "{}"\n'.format(round(self.host.annotation["MSNR"][ix])))
                # locs union enthält nur Frequenzindices, nicht Frequenzen ! ggf. umrechnen !
                # suche für jede freq ix alle MWtabellen-Einträge mit der gleichen Frequenz und sammle die entspr Tabellenindices im array ixf
                ixf = [i for i, x in enumerate(self.__slots__[2]) if np.abs((x - self.host.annotation["FREQ"][ix])) < 1e-6]
                if np.size(ixf) > 0:
                    # wenn ixf nicht leer setze Landeszähler ix_c auf 0, initialisiere flag cs auf 'none'
                    cs = [] # memory for current country
                    sortedtable = [] #Setze sortedtable zurück
                    yaml_ix = 0
                    for ix2 in ixf:
                        #print(ix2)
                        # für jeden index ix2 in ixf zum Peak ix prüfe ob es den String 'ex ' in der Stationsspalte der MWTabelle gibt
                        if type(self.__slots__[1].station.iloc[ix2]) != str:
                            curr_station = 'No Name'
                        else:
                            curr_station = self.__slots__[1].station.iloc[ix2]
                        if type(self.__slots__[1].programme.iloc[ix2]) != str:
                            curr_programme = 'No Name'
                        else:
                            curr_programme = self.__slots__[1].programme.iloc[ix2]
                        if type(self.__slots__[1].tx_site.iloc[ix2]) != str:
                            curr_tx_site = 'No Name'
                        else:
                            curr_tx_site = self.__slots__[1].tx_site.iloc[ix2]

                        if curr_station.find("ex ") == 0:
                            stdcheck = True
                        else:
                            stdcheck = False

                        # für jeden index ix2 in ixf zum Peak ix prüfe ob es den String 'INACTI' in der Stationsspalte der MWTabelle gibt
                        inactcheck = 'INACTI' in curr_station
                        # logisches label falls ()'ex ' oder 'INACT') und recording-time > Stichtag der MWTabellen-Erstellung
                        # kennzeichnet, wenn ein Sender sicher zum Zeitpunkt der Aufnahme geschlossen war
                        auto_closedlabel = (stdcheck or inactcheck) and (self.host.rectime >= self.host.STICHTAG)
                        if not ((self.__slots__[3][ix2] - self.host.rectime).days <= 0 or auto_closedlabel):
                            #wenn NICHT (geschlossen oder recording-time >= explizite Schließzeit in der Spalte closed) --> Sender ist Kandidat
                            # Progeamm und Station aus MWTabelle übernehmen
                            # Land country aus MWTabelle übernehmen
                            station = '{}{}'.format(curr_programme, curr_station)
                            tx_site = curr_tx_site
                            country = self.__slots__[1].country.iloc[ix2]
                            if country in cs:  # falls cs bereits das aktuelle Land innerhalb der aktuellen Liste ixf der Einträge zu Frequenz ix beinhaltet 
                                cix = [i for i,x in enumerate(cs) if x == country][0]
                                sortedtable[cix]['station' + str(cix)] += station + '; '
                                sortedtable[cix]['tx_site' + str(cix)] += tx_site + '; '
                            else:
                            # Trag ins dictionary sortedtable die Felder Station, Tx-site und country 
                            # als neuen Block ein
                                sortedtable.append({'station' + str(yaml_ix): station + '; ',
                                                'tx_site' + str(yaml_ix): tx_site + '; ',
                                                'country' + str(yaml_ix): country})
                                cs.append(country)  # memorize the entered country
                                yaml_ix += 1
                    # for this ixf (i.e. this peak frequency) write all entries of the sorted table

                    #print(ix2)
                    ix2 = -1
                    for ix2 in range(len(sortedtable)):
                        
                        country_string = '  country' +str(ix2) + ': "{}"\n'.format(sortedtable[ix2]['country' + str(ix2)])
                        programme_string = '  programme' +str(ix2) + ': "{}"\n'.format(sortedtable[ix2]['station' + str(ix2)])
                        tx_site_string = '  tx-site' +str(ix2) + ': "{}"\n'.format(sortedtable[ix2]['tx_site' + str(ix2)])
                        f.write(country_string)
                        f.write(programme_string)
                        f.write(tx_site_string)
                        time.sleep(0.01)
                        #print(ix2)
                    # write dummy entry for own editing
                    dum_cstr = 'OTHER COUNTRY, Please enter manually'
                    dum_pstr = 'OTHER STATION, Please enter manually'
                    dum_txstr = 'OTHER TX SITE, Please enter manually'
                    ix2 = ix2 + 1
                    country_string = '  country' +str(ix2) + ': "{}"\n'.format(dum_cstr)
                    programme_string = '  programme' +str(ix2) + ': "{}"\n'.format(dum_pstr)
                    tx_site_string = '  tx-site' +str(ix2) + ': "{}"\n'.format(dum_txstr)
                    f.write(country_string)
                    f.write(programme_string)
                    f.write(tx_site_string)
                    time.sleep(0.01)
                    # item.setText(dum_cstr.strip('\n') + ' | ' + dum_pstr.strip('\n') + ' | ' + dum_txstr.strip('\n'))

                else:
                    f.write('  country0: "not identified"\n')
                    f.write('  programme0: "not identified"\n')
                    f.write('  tx-site0: "not identified"\n')

                self.host.progressvalue = int(progress)*10
                self.mutex.lock()
                self.SigProgressBar1.emit()
                self.mutex.unlock()
                time.sleep(0.001)
        except:
            #print("annotation file not yet existent")
            #logging.info("annotation file not yet existent")
            return False

        status = {}
        status["freqindex"] = 0
        status["annotated"] = False
        stream = open(self.host.status_filename, "w")
        yaml.dump(status, stream)
        stream.close()

        self.host.progressvalue = int(0)
        self.SigProgressBar1.emit()
        time.sleep(0.001)
        self.SigFinished.emit()

class autoscan_worker(QtCore.QThread):
    """[Summary] TODO

    :param [ParamName]: [ParamDescription], defaults to [DefaultParamVal]
    :type [ParamName]: [ParamType](, optional)
    ...
    :raises [ErrorType]: [ErrorDescription]
    ...
    :return: [ReturnDescription]
    :rtype: [ReturnType]
    """
    __slots__ = ["slot_0", "slot_1","hoststates"]

    SigUpdatestatus = pyqtSignal()
    SigUpdateGUI = pyqtSignal()
    SigScandeactivate = pyqtSignal()
    SigFinished = pyqtSignal()
    SigProgressBar = pyqtSignal()
    SigStatustable = pyqtSignal()
    SigPlotdata = pyqtSignal()

    def __init__(self, host_window):
        super(autoscan_worker, self).__init__()
        self.host = host_window
        self.locs_union = []
        self.freq_union = []
        self.slot_0 = []
        self.slot_1 = [False]
        self.slot_2 = {}

    def set_0(self,_value):
        """TODO
        sets __slots__[0]
        __slots__[0] has entries: NUMSNAPS, PROMINENCE, pdata
        """
        self.__slots__[0] = _value

    def get_0(self):
        return(self.__slots__[0])
    
    def set_1(self,_value):
        """TODO
        sets __slots__[1]
        __slots__[1] has 1 entry: if True --> continue this thread worker task 
        """
        self.__slots__[1] = _value

    def get_1(self):
        return(self.__slots__[1])
    
    def set_2(self,_value):
        """TODO
        sets __slots__[2]
        __slots__[2] has entries: self.host.progressvalue, 
        self.host.horzscal, self.host.wavheader, self.host.Baselineoffset,  self.host.DATABLOCKSIZE
        self.host.locs_union 
        self.host.freq_union 
        elf.host.my_dirname + '/' + self.host.my_filename
        self.host.annotation_filename
        self.host.annotation

        needed: access method self.host.readsegment, self.host.ann_spectrum
        """
        self.__slots__[2] = _value

    def get_2(self):
        return(self.__slots__[2])


    #@njit
    def autoscan_fun(self):
        """
        scan through the recording, plot spectra and calculate mean peak info
            in tab 'scanner' as well as SNR
            Signalling: TODO
        :param : none
        :type : none
        :raises [ErrorType]: TODO [ErrorDescription]
        :return: none
        :rtype: none
        """
        print(f"slots received, value 0= :{self.__slots__[0][0]}")
        print(f"slots received, value 1 = :{self.__slots__[0][1]}")
        status = self.get_2()
        pv = status["progressvalue"]
        hs = status["horzscal"]
        print(f"status: {status}")
        print(f"slots received, progressvalue = :{pv} , horzscal = {hs}")
        self.SigUpdateGUI.emit()
        self.SigScandeactivate.emit()
        # TODO: CHECK: connect self.scan_deactivate()

        self.NUMSNAPS = self.__slots__[0][0]
        self.PROMINENCE = self.__slots__[0][1]
        self.annot = [dict() for x in range(self.NUMSNAPS)]
        for self.autoscan_ix in range(self.NUMSNAPS+1):
            self.position = int(np.floor(self.autoscan_ix/self.NUMSNAPS*1000))
            self.host.progressvalue = self.position #TODO: replace by SLOTS Baustelle eröffnet:
            status["progressvalue"] = self.position
            self.SigProgressBar.emit()
            self.__slots__[1] = False
            #print("progressbar updated")
            # write for confirmation from Progress bar updating
            while self.__slots__[1] == False:
                time.sleep(0.01)
            self.host.horzscal = self.position #TODO: replace by SLOTS Baustelle eröffnet:
            status["horzscal"] = self.position
            #print("horzscal set")
            if self.autoscan_ix > self.NUMSNAPS-1:
                self.autoscan_ix = 0  #??????????? necessary
            else:
                #print(f"autoindex:{self.autoscan_ix}")
                #data = self.host.readsegment() #TODO: replace by slots communication
                pscale = self.host.wavheader['nBlockAlign']#TODO: replace by slots communication
                position = int(np.floor(pscale*np.round(self.host.wavheader['data_nChunkSize']*self.host.horzscal/pscale/1000)))
                #TODO: in future replace by:
                #remove readsegment in this class !
                #from auxiliaries import readsegment
                #filepath = system_state["f1"]
                #readoffset = system_state["readoffset"]
                #readsegment(filepath,position,readoffset,DATABLOCKSIZE)
                #self.duration = ret["duration"]
                ret = self.host.readsegment(position,self.host.DATABLOCKSIZE)#TODO: replace by slots communication
                #TODO: in future replace by:
                #remove readsegment in this class !
                #from auxiliaries import readsegment
                #filepath = system_state["f1"]
                #readoffset = system_state["readoffset"]
                #readsegment(filepath,position,readoffset,DATABLOCKSIZE)
                #self.duration = ret["duration"]

                data = ret["data"]
                
                if 2*ret["size"]/self.host.wavheader["nBlockAlign"] < self.host.DATABLOCKSIZE:
                    return False
                # ret = {}
                # ret["data"] = data
                # ret["size"] = size
                # #print('annotator: data read')

                #TODO: new invalidity condition, replace/remove old one: 
                # if len(data) == 10:
                #     if np.all(data == np.linspace(0,9,10)):
                #         return False

                pdata = self.host.ann_spectrum(self,data)#TODO: replace by slots communication
                self.__slots__[0][2] = pdata
                self.SigPlotdata.emit()
                # wait until plot has been carried out
                self.__slots__[1] = False
                while self.__slots__[1] == False:
                    time.sleep(0.01)
                self.annot[self.autoscan_ix]["FREQ"] = pdata["datax"] 
                self.annot[self.autoscan_ix]["PKS"] = pdata["peaklocs"]
                #TODO: remove: peakprops = pdata["peakprops"]
                peaklocs = pdata["peaklocs"]
                datay = pdata["datay"]
                basel = pdata["databasel"] + self.host.baselineoffset#TODO: replace by slots communication
                self.annot[self.autoscan_ix]["SNR"] = datay[peaklocs] - basel[peaklocs]

                #collect all peaks which have occurred at least once in an array
                self.locs_union = np.union1d(self.locs_union, self.annot[self.autoscan_ix]["PKS"])
                self.freq_union = np.union1d(self.freq_union, self.annot[self.autoscan_ix]["FREQ"][self.annot[self.autoscan_ix]["PKS"]])
        # purge self.locs.union and remove elements the frequencies of which are
        # within 1 kHz span 
        uniquefreqs = pd.unique(np.round(self.freq_union/1000))
        xyi, x_ix, y_ix = np.intersect1d(uniquefreqs, np.round(self.freq_union/1000), return_indices=True)

        self.locs_union= self.locs_union[y_ix]
        self.freq_union = self.freq_union[y_ix]
        self.host.locs_union = self.locs_union #TODO: replace by slots communication
        self.host.freq_union = self.freq_union #TODO: replace by slots communication

        meansnr = np.zeros(len(self.locs_union))
        minsnr = 1000*np.ones(len(self.locs_union))
        maxsnr = -1000*np.ones(len(self.locs_union))
        #print('annotator: start reannotation')
        reannot = {}
        for ix in range(self.NUMSNAPS): 
            # find indices of current LOCS in the unified LOC vector self.locs_union
            sharedvals, ix_un, ix_ann = np.intersect1d(self.locs_union, self.annot[ix]["PKS"], return_indices=True)
            # write current SNR to the corresponding places of the self.reannotated matrix
            reannot["SNR"] = np.zeros(len(self.locs_union))
            reannot["SNR"][ix_un] = self.annot[ix]["SNR"][ix_ann]
            #Global Statistics, without consideration whether some peaks vanish or
            #appear when running through all values of ix
            meansnr = meansnr + reannot["SNR"]
            #min and max SNR data are currently not being used.
            minsnr = np.minimum(minsnr, reannot["SNR"])
            maxsnr = np.maximum(maxsnr, reannot["SNR"])

        # collect cumulative info in a dictionary and write the info to the annotation yaml file 
        self.annotation = {}
        self.annotation["MSNR"] = meansnr/self.NUMSNAPS
        self.annotation["FREQ"] = np.round(self.freq_union/1000) # signifikante Stellen
        yamldata = [dict() for x in range(len(self.annotation["FREQ"]))]

        for ix in range(len(self.annotation["FREQ"])):
            yamldata[ix]["FREQ:"] = str(self.annotation["FREQ"][ix])
            yamldata[ix]["SNR:"] = str(np.floor(self.annotation["MSNR"][ix]))
        
        #if os.path.isdir(self.host.my_dirname + '/' + self.host.my_filename) == False:
        #    os.mkdir(self.host.my_dirname + '/' + self.host.my_filename)#TODO: replace by slots communication
        #print("annotator: reannot finished")
        #self.annotation_filename = self.annotationpath + '/snrannotation.yaml'
        #TODO: check if file exists
        try:
            stream = open(self.host.annotation_filename, "w")#TODO: replace by slots communication
            yaml.dump(yamldata, stream)
            stream.close()
        except:
            print("cannot write annotation yaml")
            pass
        self.host.annotation = self.annotation#TODO: replace by slots communication
        self.SigStatustable.emit()
        self.__slots__[1] = False #TODO: replace by stter and getter access
        while self.__slots__[1] == False:
                time.sleep(0.01)

        #time.sleep(0.01)
        self.set_2(status)
        self.SigFinished.emit()

class timer_worker(QObject):
    """_generates time signals for clock and recording timer_

    :param [ParamName]: [ParamDescription], defaults to [DefaultParamVal]
    :type [ParamName]: [ParamType](, optional)
    ...
    :raises [ErrorType]: [ErrorDescription]TODO
    ...
    :return: [ReturnDescription]
    :rtype: [ReturnType]
    """
    SigTick = pyqtSignal()
    SigFinished = pyqtSignal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def tick(self):
        """send a signal self.SigTick every second
        :param : none
        :type : none
        :raises: none
        :return: none
        :rtype: none
        """
        while True:
            time.sleep(1 - time.monotonic() % 1)
            self.SigTick.emit()

    def stoptick(self):
        self.SigFinished.emit()        

class core_m(QObject):
    def __init__(self):
        super().__init__()
        # Constants
        self.CONST_SAMPLE = 0 # sample constant
        self.mdl = {}
        self.mdl["sample"] = 0
        self.mdl["_log"] = False

class core_c(QObject):
    """_view method
    """
    __slots__ = ["contvars"]

    SigAny = pyqtSignal()
    SigRelay = pyqtSignal(str,object)

    def __init__(self, core_m): #TODO: remove gui
        super().__init__()

    # def __init__(self, *args, **kwargs): #TEST 09-01-2024
    #     super().__init__(*args, **kwargs)
        viewvars = {}
        #self.set_viewvars(viewvars)
        self.m = core_m.mdl
        

class core_v(QObject):
    """_view methods for resampling module
    TODO: gui.wavheader --> something less general ?
    """
    __slots__ = ["viewvars"]

    SigUpdateGUI = pyqtSignal(object)
    SigRelay = pyqtSignal(str,object)

    def __init__(self, gui, core_c, core_m): 
        super().__init__()

        #viewvars = {}
        #self.set_viewvars(viewvars)
        self.m = core_m.mdl
        self.gui = gui #gui_state["gui_reference"]#system_state["gui_reference"]

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
        if _key.find("cm_xcore") == 0 or _key.find("cm_all_") == 0:
            #set mdl-value
            self.m[_value[0]] = _value[1]
            system_state = sys_state.get_status()    
            system_state[_value[0]] = _value[1]
            sys_state.set_status(system_state)

        if _key.find("cui_xcore") == 0:
            _value[0](_value[1]) #STILL UNCLEAR
        if _key.find("cexex_xcore") == 0  or _key.find("cexex_all_") == 0:
            if  _value[0].find("updateGUIelements") == 0:
                self.updateGUIelements()

            #handle method
            # if  _value[0].find("plot_spectrum") == 0: #EXAMPLE
            #     self.plot_spectrum(0,_value[1])   #EXAMPLE

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
        print("core: updateGUIelements")
        #self.gui.DOSOMETHING

    def update_GUI(self,_key): #TODO TODO: is this method still needed ? reorganize. gui-calls should be avoided, better only signalling and gui must call the routenes itself
        print(" view spectra updateGUI: new updateGUI in view spectra module reached")
        self.SigUpdateGUI.disconnect(self.update_GUI)
        if _key.find("ext_update") == 0:
            pass
        self.SigUpdateGUI.connect(self.update_GUI)

class WizardGUI(QMainWindow):
    #TODO: make this the core_view method
    SigToolbar = pyqtSignal()
    SigUpdateGUI = pyqtSignal()
    SigGP = pyqtSignal()
    SigProgress = pyqtSignal()
    SigGUIReset = pyqtSignal()
    SigEOFStart = pyqtSignal()
    SigSyncTabs = pyqtSignal(object)
    SigUpdateOtherGUIs = pyqtSignal()
    SigRelay = pyqtSignal(str,object)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        print("Initializing GUI, please wait....")


        self.TEST = True    # Test Mode Flag for testing the App, --> playloop  ##NOT USED #TODO:future system status
        self.CURTIMEINCREMENT = 5 # für playloop >>, << TODO: shift to playrec module once it exists
        self.DATABLOCKSIZE = 1024*32 # für diverse Filereader/writer TODO: occurs in plot spectrum and ANN_Spectrum; must be shifted to the respective modules in future
        self.DELTAF = 5000 #minimum peak distance in Hz for peak detector #TODO:occurs in ann-module; values also used in spectrum view; ; must be shifted to the respective modules in future
        self.PEAKWIDTH = 10 # minimum peak width in Hz for peak detector #TODO:occurs in ann-module; values also used in spectrum view; ; must be shifted to the respective modules in future
        self.PROMINENCE = 15 # minimum peak prominence in dB above baseline for peak detector #TODO:occurs in ann-module; values also used in spectrum view; ; must be shifted to the respective modules in future
        self.FILTERKERNEL = 2 # length of the moving median filter kernel in % of the spectral span #TODO:occurs in ann-module; values also used in spectrum view; ; must be shifted to the respective modules in future
        self.NUMSNAPS = 5 #number of segments evaluated for annotation #TODO:occurs in ann-module; must be shifted to the respective module in future
        self.STICHTAG = datetime(2023,2,25,0,0,0) #TODO: only used in stationsloop of statslist_gen_worker as self.host.STICHTAG, Move to module annotation
        self.GAINOFFSET = 40 #TODO: move to player module
        self.autoscan_ix = 0 #TODO:future system state
        self.gain = 1 #TODO:future system state
        self.bps = ['8', '16', '24', '32'] #TODO:future system state
        self.standardLO = 1100 #TODO:future system state
        self.locs_union = [] #TODO:future system state
        self.freq_union = [] #TODO:future system state
        self.oldposition = 0 #TODO:future system state
        self.ovwrt_flag = False #TODO:future system state
        self.autoscanthreadActive = False #TODO:future system state
        self.progressvalue = 0 #TODO:future system state
        self.cohiradia_yamlheader_filename = 'dummy' #TODO:future system state
        self.cohiradia_yamltailer_filename = 'dummy' #TODO:future system state
        self.cohiradia_yamlfinal_filename = 'dummy' #TODO:future system state
        self.annotationdir_prefix = 'ANN_' #TODO:future system state
        self.flag_ann_completed = False #TODO:future system state
        self.lock_playthreadstart = True #TODO:future system state
        self.playthreadActive = False #TODO:future system state
        self.curtime = 0 #TODO:future system state
        self.timechanged=False #TODO:future system state
        self.position = 0 #TODO:future system state URGENT !!!!!!!!!!!!!!
        self.tab_dict = {}

        #logging.basicConfig(filename='system_log.log', filemode='a', format='%(name)s - %(levelname)s - %(message)s', level=logging.INFO)

        self.GUIupdaterlist =[]
        # create method which inactivates all tabs except the one which is passed as keyword
        self.GUI_reset_status()
        self.ui = MyWizard()
        self.ui.setupUi(self)
        self.ui.tableWidget_basisfields.verticalHeader().setVisible(True)   

        ## TODO: wavheader-Writing zum Button Insert Header connecten
        # connect menubar events
        #Abonnierung von system state update wie folgt:
        #sys_state.SigUpdateStatus.connect(lambda: print("5§§§§§% ------- Statusupdate on Signal received ------"))

        ### UI MASTER ####################################
        self.ui.actionFile_open.triggered.connect(self.cb_open_file)
        #self.ui.actionOverwrite_header.triggered.connect(self.overwrite_header)
        self.SigGUIReset.connect(self.reset_GUI)
        self.ui.pushButton_resample_GainOnly.setEnabled(False)
    
        self.ui.checkBox_writelog.clicked.connect(self.togglelogmodus) #TODO TODO TODO: logfilemodus anders implementieren
        self.ui.tabWidget.setCurrentIndex(1) #TODO: avoid magic number, unidentified

        ### END UI MASTER ####################################

        ###EUI TAB ANNOTATE####################################
        self.ui.pushButton_Scan.setEnabled(False)
        self.ui.pushButtonAnnotate.setEnabled(False)
        self.ui.pushButton_Scan.clicked.connect(self.autoscan)
        self.ui.pushButtonAnnotate.clicked.connect(self.ann_stations) 
        self.ui.pushButtonDiscard.setEnabled(False)
        self.ui.pushButtonDiscard.clicked.connect(self.discard_annot_line)
        self.ui.spinBoxminSNR.valueChanged.connect(self.minSNRupdate) 
        self.ui.lineEdit.setAlignment(QtCore.Qt.AlignLeft)
        #self.ui.lineEdit.returnPressed.connect(self.enterlinetoannotation)
        self.ui.pushButtonENTER.clicked.connect(self.enterlinetoannotation)
        self.ui.pushButtonENTER.setEnabled(False)
        #self.ui.pushButton_ScanAnn.clicked.connect(self.listclick_test)
        self.ui.Annotate_listWidget.itemClicked.connect(self.cb_ListClicked)
        self.ui.Annotate_listWidget.clear()
        self.ui.progressBar_2.setProperty("value", 0)
        ###END UI TAB ANNOTATE ####################################

        ###UI TAB PLAYER ####################################
        self.ui.pushButton_Shutdown.clicked.connect(self.shutdown)
        self.ui.pushButton_FF.clicked.connect(
            lambda: self.updatecurtime(self.CURTIMEINCREMENT))
        self.ui.pushButton_REW.clicked.connect(
                    lambda: self.updatecurtime(-self.CURTIMEINCREMENT))
        self.ui.pushButton_adv1byte.clicked.connect(
                    lambda: self.jump_1_byte())          ########### INACTIVATE if 1 byte correction should be disabled
        self.ui.pushButton_adv1byte.setEnabled(False)  #TODO: rename: manual tracking
        self.ui.verticalSlider_Gain.valueChanged.connect(self.cb_setgain)
        self.ui.ScrollBar_playtime.sliderReleased.connect(self.jump_to_position)
        self.ui.lineEdit_LO_bias.setFont(QFont('arial',12))
        self.ui.lineEdit_LO_bias.setEnabled(True)
        self.ui.lineEdit_LO_bias.setText("0000")
        self.ui.radioButton_LO_bias.setEnabled(True)
        self.ui.lineEdit_LO_bias.textChanged.connect(self.update_LO_bias)
        self.ui.radioButton_LO_bias.clicked.connect(self.activate_LO_bias)
        self.stopstate = True
        self.ui.pushButton_Play.setIcon(QIcon("play_v4.PNG"))
        self.ui.pushButton_Play.clicked.connect(self.cb_Butt_toggleplay)
        self.ui.pushButton_Stop.clicked.connect(self.cb_Butt_STOP)
        self.ui.pushButton_REC.clicked.connect(self.cb_Butt_REC)        
        self.ui.pushButton_act_playlist.clicked.connect(self.cb_Butt_toggle_playlist)

        self.ui.lineEdit_IPAddress.returnPressed.connect(self.set_IP)#TODO: Remove after transfer of playrec
        self.ui.lineEdit_IPAddress.setInputMask('000.000.000.000')#TODO: Remove after transfer of playrec
        self.ui.lineEdit_IPAddress.setText("000.000.000.000")#TODO: Remove after transfer of playrec
        self.ui.lineEdit_IPAddress.setEnabled(False)#TODO: Remove after transfer of playrec
        self.ui.lineEdit_IPAddress.setReadOnly(True)#TODO: Remove after transfer of playrec
        #####INFO: IP address validator from Trimmal Software    rx = QRegExp('^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])|rp-[0-9A-Fa-f]{6}\.local$')
        #                                                          self.addrValue.setValidator(QRegExpValidator(rx, self.addrValue))
        #pushButton->setIcon(QIcon(":/on.png"));
        self.ui.pushButton_IP.clicked.connect(self.editHostAddress) #TODO: Remove after transfer
        self.ui.lineEdit_IPAddress.returnPressed.connect(self.set_IP) #TODO: Remove after transfer
        self.ui.listWidget_playlist.setEnabled(False)
        self.ui.listWidget_sourcelist_2.setEnabled(False)
        self.ui.listWidget_sourcelist.setEnabled(False)
        self.ui.listWidget_playlist_2.setEnabled(False)
        self.ui.ScrollBar_playtime.setEnabled(False)
        ##############transfer done for next 2 lines:
        self.ui.listWidget_playlist.model().rowsInserted.connect(lambda: self.playlist_update()) #TODO transfer to resemplar view
        self.ui.listWidget_playlist.model().rowsRemoved.connect(lambda: self.playlist_update()) #TODO transfer to resemplar view

        ###END UI TAB PLAYER ####################################

        #read config file if it exists
        self.standardpath = os.getcwd()  #TODO: this is a core variable in core model
        self.metadata = {"last_path": self.standardpath}
        self.ismetadata = False
        try:
            stream = open("config_wizard.yaml", "r")
            self.metadata = yaml.safe_load(stream)
            stream.close()
            self.ismetadata = True
            if 'STM_IP_address' in self.metadata.keys():
                self.ui.lineEdit_IPAddress.setText(self.metadata["STM_IP_address"]) #TODO: Remove after transfer of playrec
                self.ui.Conf_lineEdit_IPAddress.setText(self.metadata["STM_IP_address"]) #TODO TODO TODO: reorganize and shift to config module
        except:
            #return False

            print("cannot get metadata")

        system_state = sys_state.get_status()    
        system_state["HostAddress"] = self.ui.lineEdit_IPAddress.text() #TODO: Remove after transfer of playrec
        configparams = {"ifreq":system_state["ifreq"], "irate":system_state["irate"],
                            "rates": system_state["rates"], "icorr":system_state["icorr"],
                            "HostAddress":system_state["HostAddress"], "LO_offset":system_state["LO_offset"]}
        system_state["sdr_configparams"] = configparams
        system_state["_log"] = False
        # TODO: define all other states and transfer to system_state; then restore system state in every method which accesses and/or modifies the state
        if "resampler_module_v5" in sys.modules:
            system_state["OLD"] = False  #Umschalter altes, neues GUI zum Umbauen, alt = v26, resampler_module_v4
        else:
            system_state["OLD"] = True
        #neu = resampler_module_v5, neue Modell/Signal/corestruktur
        sys_state.set_status(system_state)
        self.reset_LO_bias()
        self.Tabref={}
        self.init_Tabref()
        self.timeref = datetime.now()
        self.autoscanthread = QThread()
        self.autoscaninst = autoscan_worker(self)
        self.autoscaninst.moveToThread(self.autoscanthread)
        #TODO: Implement further slot communicationa shown here
        self.autoscaninst.set_0([self.ui.spinBoxNumScan.value(),self.ui.spinBoxminSNR.value(),[]])

        ################# start timer tick
        self.timethread = QThread()
        self.timertick = timer_worker()
        self.timertick.moveToThread(self.timethread)
        self.timethread.started.connect(self.timertick.tick)
        self.timertick.SigFinished.connect(self.timethread.quit)
        self.timertick.SigFinished.connect(self.timertick.deleteLater)
        self.timethread.finished.connect(self.timethread.deleteLater)
        self.timertick.SigTick.connect(self.updatetimer)
        self.timethread.start()
        if self.timethread.isRunning():
            self.timethreaddActive = True #TODO:future system state
        # Create a custom logger
        # Setze den Level des Root-Loggers auf DEBUG
        logging.getLogger().setLevel(logging.DEBUG)
        # Erstelle einen Logger mit dem Modul- oder Skriptnamen
        self.logger = logging.getLogger(__name__)
        # Create handlers
        warning_handler = logging.StreamHandler()
        debug_handler = logging.FileHandler("system_log.log","w")
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
        #check if sox is installed so as to throw an error message on resampling, if not
        self.soxlink = "https://sourceforge.net/projects/sox/files/sox/14.4.2/"
        self.soxlink_altern = "https://sourceforge.net/projects/sox"
        self.soxnotexist = False
        try:
            subproc3 = subprocess.run('sox -h', stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True, check=True)
        except subprocess.CalledProcessError as ex:
            #print("sox FAIL")
            self.logger.error("sox FAIL")
            print(ex.stderr, file=sys.stderr, end='', flush=True)
            print(ex.stdout, file=sys.stdout, end='', flush=True)
            if len(ex.stderr) > 0: 
                self.soxnotexist = True

        self.logger.info("Init logger in core reached")

    # GENRAL GUI METHODS

    def togglelogmodus(self):
        """
        ?? general core method ??
        set modus of stdout to either file or console
        :param: npne
        :type: none
        :raises: none
        ...
        :return: none
        :rtype: none
        """
        #TODO
        if self.ui.checkBox_writelog.isChecked:
            system_state["_log"] = True
            self.SigRelay.emit("cm_all_",["_log", True])

        else:
            system_state["_log"] = False
            self.SigRelay.emit("cm_all_",["_log", False])


############## CORE VIEW METHOD #################
    def GUI_reset_status(self):
        system_state = {}
        system_state["my_filename"] = ""
        system_state["ext"] = ""
        system_state["annotation_prefix"] = 'ANN_' #TODO: not used anywhere
        system_state["resampling_gain"] = 0
        system_state["emergency_stop"] = False
        system_state["timescaler"] = 0
        system_state["fileopened"] = False
        system_state["rates"] = {20000:0, 50000:1, 100000:2, 250000:3, 
                      500000:4, 1250000:5, 2500000:6}
        system_state["ifreq"] = 0
        system_state["irate"] = 0
        system_state["icorr"] = 0
        system_state["irates"] = ['2500', '1250', '500', '250', '100', '50', '20']
        system_state["gui_reference"] = self
        system_state["actionlabel"] = ""
        system_state["LO_offset"] = 0
        system_state["playlist_ix"] = 0
        system_state["reslist_ix"] = 0
        system_state["list_out_files_resampled"] = []
        system_state["playlist_active"] = False
        system_state["progress"] = 0
        system_state["temp_LOerror"] = False
        system_state["starttrim"] = False
        system_state["stoptrim"] = False
        sys_state.set_status(system_state)

    def generate_canvas(self,dummy,gridref,gridc,gridt,Tabref):
        """
        --> VIEW or auxiliary
        initialize central Tab management dictionary Tabref
        :param: gridref
        :type: ui.gridLayout_# object from GUI, e.g. self.ui.gridLayout_4 given by QT-designer
        :param: gridc, position of canvas, list with 4 entries: row_index, col_index, line_span, col_span
        :type: list 
        :param: gridt, position and span of toolbar with 4 entries: row_index, col_index, line_span, col_span
                if gridt[0] < 0 --> no toolbar is being assigned
        :type: list
        :param: Tabref["name"], name = name of tab
        :type: dict["name"]
        ...
        :raises: none
        ...
        :return: none
        :rtype: none
        """
        figure = Figure()
        canvas = FigureCanvasQTAgg(figure)
        gridref.addWidget(canvas,gridc[0],gridc[1],gridc[2],gridc[3])
        ax = figure.add_subplot(111)
        if gridt[0] >= 0:
            toolbar = NavigationToolbar(canvas, self)
            gridref.addWidget(toolbar,gridt[0],gridt[1],gridt[2],gridt[3])
        Tabref["ax"] = ax
        Tabref["canvas"] = canvas
        Tabref["ax"].plot([], [])
        Tabref["canvas"].draw()

##############################  RESAMPLE MODULE, REMOVE ###########################
        
    def init_Tabref(self): #TODO:future system state
        """
        UNKLAR: Definition einer Referenztabelle für das Ansprechen verschiedener TABs und insb CANVAS-Zuweisung
        könnte auch im Datenmodul residieren
        initialize central Tab management dictionary Tabref
        :param: none
        :type: none
        ...
        :raises: none
        ...
        :return: none
        :rtype: none
        """
        #TODO: Umbenennen der tab-Referenzen nach ordentlichem System, so wie bereits 'tab_resample', nicht 'tab_4'
        # Bei Erweiterungen: für jeden neuen Tab einen neuen Tabref Eintrag generieren, generate_canvas nur wenn man dort einen Canvas will
        #TODO:future system state
        self.Tabref["Player"] = {}
        self.Tabref["Player"]["tab_reference"] = self.ui.tab_playrec
        #Tab View spectra
        self.Tabref["View_Spectra"] = {}
        self.Tabref["View_Spectra"]["tab_reference"] = self.ui.tab_view_spectra
        self.generate_canvas(self,self.ui.gridLayout_4,[4,0,1,5],[2,2,2,1],self.Tabref["View_Spectra"])
        #generiert einen Canvas auf den man mit self.Tabref["View_Spectra"]["canvas"] und
        #self.Tabref["View_Spectra"]["ax"] als normale ax und canvas Objekte zugreifen kann
        #wie plot(...), show(), close()
        # Tab Resampler
        self.Tabref["Resample"] = {}
        self.Tabref["Resample"]["tab_reference"] = self.ui.tab_resample
        #TODO: change 10-12-2023: since GUI10: self.generate_canvas(self,self.ui.gridLayout_5,[10,0,1,5],[-1,-1,-1,-1],self.Tabref["Resample"])
        self.generate_canvas(self,self.ui.gridLayout_5,[6,0,6,4],[-1,-1,-1,-1],self.Tabref["Resample"])

##############################  RESAMPLE MODULE, END REMOVE ###########################

    def setactivity_tabs(self,caller,statuschange,exceptionlist):
        """
        VIEW
        activates or inactivaes all tabs except the caller
        caller can be any tab name
        statuschange: 'activate': activate all tabs except the caller
                        'inactivate' inactivate all tabs except the caller
        :param caller
        :type str
        :param statuschange
        :type str
        :param exceptionlist
        :type list        
        ...
        :raises [ErrorType]: none
        ...
        :return: success label: True, False
        :rtype: boolean
        """
        for i in range(self.ui.tabWidget.count()):
            #self.ui.tab_3.objectName()
            #self.ui.tabWidget.indexOf(self.ui.tab_3)
            if statuschange.find("inactivate") == 0:
                if (self.ui.tabWidget.tabText(i).find(caller) == -1) and (self.ui.tabWidget.tabText(i) not in exceptionlist):
                    self.ui.tabWidget.widget(i).setEnabled(False)
            elif statuschange.find("activate") == 0:
                if (self.ui.tabWidget.tabText(i).find(caller) == -1) and (self.ui.tabWidget.tabText(i) not in exceptionlist):
                    self.ui.tabWidget.widget(i).setEnabled(True)
            else:
                return False
        return True
            #self.ui.tabWidget.tabText(i).setEnabled(True)
        #    if self.tabWidget.tabText(i) == "product add":
        #        self.tabWidget.setCurrentIndex(i)

        #TODO: shift action to respective tab machine by: currix = self.ui.tabWidget.currentIndex() self.ui.tabWidget.tabText(currix)

    def reset_GUI(self):
        """
        VIEW
        TODO: nach den einzelnen Tabs zerlegen
        reset GUI elements to their defaults, re-initialize important variables
        code is executed after new file open
        :param none
        :type: none
        :raises [ErrorType]: [ErrorDescription]TODO
        :return: True after completion, False if status-yaml not accessible
        :rtype: boolean
        """
        ########################TODO: change mode: make reset functions  for each tab which are just registered with the signal 
        # self.SigGUIReset
        # like:
        # self.SigGUIReset.connect(self.reset_GUI)
        ##################################################################

        self.autoscan_ix = 0
        #TODO: remove self.autoscan_active = False
        self.locs_union = []
        self.freq_union = []
        self.oldposition = 0
        
        ###########transfer to tab Annotator
        self.ui.pushButtonAnnotate.setFont(QFont('MS Shell Dlg 2', 12))
        self.ui.pushButton_Scan.setFont(QFont('MS Shell Dlg 2', 12))
        self.ui.pushButtonAnnotate.setStyleSheet("background-color : rgb(220, 220, 220)")
        self.ui.pushButton_Scan.setStyleSheet("background-color : rgb(220, 220, 220)")
        self.ui.lineEdit.setText('')
        self.ui.lineEdit_TX_Site.setText('')
        self.ui.lineEdit_Country.setText('')
        #self.ui.line_Edit.setAlignment(QtCore.Qt.AlignLeft)
        self.ui.lineEdit.setStyleSheet("background-color : white")
        self.ui.lineEdit.setFont(QFont('MS Shell Dlg 2', 12))
        self.ui.Annotate_listWidget.clear()
        #self.ui.tab_2.setEnabled(True)
        self.ui.tab_view_spectra.setEnabled(True)
        self.ui.tab_annotate.setEnabled(True)
        #self.ui.pushButton_InsertHeader.setEnabled(False)   #####TODO shift to WAV editor or send Relay for inactivation via WAV 
        self.ui.label_8.setEnabled(False)
        self.ui.label_36.setText('READY')
        self.ui.label_36.setFont(QFont('arial',12))
        self.ui.label_36.setStyleSheet("background-color: lightgray")
        self.ui.radioButton_WAVEDIT.setChecked(False)
        #self.activate_WAVEDIT() # to wav editor Tab reset
        self.SigRelay.emit("cexex_waveditor",["activate_WAVEDIT",0])
        self.Tabref["View_Spectra"]["ax"].clear() #shift to Plot spectrum Tab reset
        self.Tabref["View_Spectra"]["canvas"].draw() #shift to Plot spectrum Tab reset
        self.Tabref["Resample"]["ax"].clear() #shift to Resampler Tab reset
        self.ui.listWidget_sourcelist.clear() # shift to resampler Tab

        self.Tabref["Resample"]["canvas"].draw() #shift to Resampler Tab reset
        self.ui.label_Filename_Player.setText('')  #shift to Player Tab reset
        self.ui.label_Filename_ViewSpectra.setText('') #shift to Plot spectrum Tab reset
        self.ui.label_Filename_Annotate.setText('') #shift to Annotator Tab reset
        self.ui.label_Filename_WAVHeader.setText('') #shift to wav editor Tab reset
        self.ui.label_Filename_resample.setText('') #shift to resampler Tab reset
        self.ui.listWidget_playlist.clear() #TODO: shift to Player Tab reset
        self.ui.listWidget_sourcelist.clear() #TODO: shift to Player Tab reset
        #self.clear_WAVwidgets() #TODO: shift to to a WAVeditor reset

        try:
            stream = open("config_wizard.yaml", "r")
            self.metadata = yaml.safe_load(stream)
            if 'STM_IP_address' in self.metadata.keys():
                self.ui.lineEdit_IPAddress.setText(self.metadata["STM_IP_address"]) #TODO: Remove after transfer of playrec
            stream.close()
        except:
            #return False
            #print("cannot get metadata")
            #logging.error("reset_gui: cannot get metadata")
            self.logger.error("reset_gui: cannot get metadata")
        #self.open_template_flag = False
        try:
            stream = open(self.status_filename, "r")
            status = yaml.safe_load(stream)
            stream.close()
        except:
            #print("cannot get status")
            return False 
        
        #TODO: reade info on spinbox settings MF kernel etc from status file if it exists
        #self.ui.spinBoxKernelwidth.setProperty("value", 15)
        #self.ui.spinBoxNumScan.setProperty("value", 10)
        #self.ui.spinBoxminBaselineoffset.setProperty("value", 5)

        return True

    ############################## TAB PLAYER ####################################
    def cb_Butt_toggle_playlist(self):
        system_state = sys_state.get_status()
        if system_state["playlist_active"] == False:
            self.ui.pushButton_act_playlist.setChecked(True)
            self.ui.listWidget_sourcelist.setEnabled(True)
            self.ui.listWidget_playlist.setEnabled(True)
            system_state["playlist_active"] = True
        else:
            self.ui.pushButton_act_playlist.setChecked(False)
            self.ui.listWidget_sourcelist.setEnabled(False)
            self.ui.listWidget_playlist.setEnabled(False)
            system_state["playlist_active"] = False

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
        system_state = sys_state.get_status()
        #get all items of playlist Widget and write them to system_state["playlist"]
        lw = self.ui.listWidget_playlist
        # let lw haven elements in it.
        playlist = []
        for x in range(lw.count()-1):
            item = lw.item(x)
            #playlist.append(lw.item(x))
            playlist.append(item.text())
        system_state["playlist"] = playlist
        self.SigRelay.emit("cm_playrec",["playlist",playlist])
        sys_state.set_status(system_state)

                    # _item2.setText(x)

    def cb_setgain(self):
        '''
        VIEW: cb of Tab player
        #TODO
        '''
        if self.playthreadActive is False:
            return False
        self.gain = 10**((self.ui.verticalSlider_Gain.value() - self.GAINOFFSET)/20)
        #print(f"self.gain in cb:  {self.gain}")
        self.playrec_tworker.set_6(self.gain)
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

        if self.ui.checkBox_UTC.isChecked():
            self.UTC = True #TODO:future system state
        else:
            self.UTC = False
        if self.ui.checkBox_TESTMODE.isChecked():
            self.TEST = True #TODO:future system state
        else:
            self.TEST = False

        if self.UTC:
            dt_now = datetime.now(ndatetime.timezone.utc)
            self.ui.label_showdate.setText(
                dt_now.strftime('%Y-%m-%d'))
            self.ui.label_showtime.setText(
                dt_now.strftime('%H:%M:%S'))
        else:
            dt_now = datetime.now()
            self.ui.label_showdate.setText(
                dt_now.strftime('%Y-%m-%d'))
            self.ui.label_showtime.setText(
                dt_now.strftime('%H:%M:%S'))
            
        #TODO: reimplement recorder

        # if self.ui.radioButton_timeract.isChecked():
        #     self.ui.radioButton_Timer.setChecked(False)
        #     self.ui.dateTimeEdit_setclock.setEnabled(False)
        #     self.ui.checkBox_UTC.setEnabled(False)
        #     st = self.ui.dateTimeEdit_setclock.dateTime().toPyDateTime()
        #     if self.UTC:
        #         ct = QtCore.QDateTime.currentDateTime().toUTC().toPyDateTime()
        #     else:
        #         ct = QtCore.QDateTime.currentDateTime().toPyDateTime()
        #     self.diff = np.floor((st-ct).total_seconds())
        #     if self.diff > 0:
        #         countdown = str(ndatetime.timedelta(seconds=self.diff))
        #         self.ui.label_ctdn_time.setText(countdown)
        #     else:
        #         if self.recording_wait is True:
        #             self.recording_wait = False
        #             self.recordingsequence()
        #         return
        # else:
        #     self.ui.checkBox_UTC.setEnabled(True)
        #     if not self.ui.radioButton_Timer.isChecked():
        #         self.ui.dateTimeEdit_setclock.setEnabled(False)
        #     else:
        #         self.ui.dateTimeEdit_setclock.setEnabled(True)

    
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
        system_state = sys_state.get_status()
        if self.ui.pushButton_Play.isChecked() == True:
            if not system_state["fileopened"]:
                if self.ui.radioButton_LO_bias.isChecked() is True:
                    msg = QMessageBox()
                    msg.setIcon(QMessageBox.Question)
                    msg.setText("Apply LO offset")
                    msg.setInformativeText("center frequency offset is activated, the LO will be shifted by " + str(int(system_state["LO_offset"]/1000)) + " kHz. Do you want to proceed ? If no, please inactivate center frequency offset")
                    msg.setWindowTitle("Apply LO offset")
                    msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                    msg.buttonClicked.connect(self.popup)
                    msg.exec_()
                    if self.yesno == "&No":
                        ###RESET playgroup
                        self.reset_playerbuttongroup()
                        self.reset_LO_bias()
                        sys_state.set_status(system_state)
                        return False

                self.ui.radioButton_LO_bias.setEnabled(False)
                if self.cb_open_file() is False:
                    self.reset_playerbuttongroup()
                    sys_state.set_status(system_state)
                    return False
                #TODO: return if open file is false
                if not self.LO_bias_checkbounds():
                    self.reset_playerbuttongroup()
                    return False
                self.ui.lineEdit_LO_bias.setEnabled(False)
                ######Setze linedit f LO_Bias inaktiv
            if not self.checkSTEMLABrates():
                self.reset_playerbuttongroup()
                return False
            self.ui.pushButton_Play.setIcon(QIcon("pause_v4.PNG"))
            if self.playthreadActive == True:
                self.playrec_tworker.pausestate = False
            self.play_manager()
            self.pausestate = False
            self.stopstate = False
            self.ui.ScrollBar_playtime.setEnabled(True)
            self.ui.pushButton_adv1byte.setEnabled(True)
        else:
            self.ui.pushButton_Play.setIcon(QIcon("play_v4.PNG"))
            self.pausestate = True ##TODO CHECK: necessary ? es gibt ja self.playrec_tworker.pausestate
            if self.playthreadActive == True:
                self.playrec_tworker.pausestate = True


    def editHostAddress(self):     #TODO Check if this is necessary, rename to cb_.... ! shift to config Menu
        ''' 
        VIEW, cb of player, not marked as cb, RENAME !
        TODO
        Purpose: Callback for edidHostAddress Lineedit item
        activate Host IP address field and enable saving mode
        Returns: nothing
        '''
        self.ui.lineEdit_IPAddress.setEnabled(True)
        self.ui.lineEdit_IPAddress.setReadOnly(False)
        self.ui.pushButton_IP.clicked.connect(self.set_IP)
        self.ui.pushButton_IP.setText("save IP Address")
        self.ui.pushButton_IP.adjustSize()
        self.IP_address_set = False

    def set_IP(self): #TODO TODO TODO: shift to config tab
        """ 
        CONTROLLER
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
        system_state = sys_state.get_status()
        #self.HostAddress = self.ui.lineEdit_IPAddress.text()
        system_state["HostAddress"] = self.ui.lineEdit_IPAddress.text() #TODO: Remove after transfer of playrec
        #print("IP address read")
        try:
            stream = open("config_wizard.yaml", "r")
            self.metadata = yaml.safe_load(stream)
            stream.close()
        except:
            auxi.standard_errorbox("Cannot open Config File")
            self.logger.error("cannot get metadata")
            #print("cannot get metadata")
        self.metadata["STM_IP_address"] = system_state["HostAddress"]
        stream = open("config_wizard.yaml", "w")
        yaml.dump(self.metadata, stream)

        self.ui.lineEdit_IPAddress.setReadOnly(True)#TODO: Remove after transfer of playrec
        self.ui.lineEdit_IPAddress.setEnabled(False)#TODO: Remove after transfer of playrec
        self.ui.pushButton_IP.clicked.connect(self.editHostAddress)#TODO: Remove after transfer of playrec
        self.ui.pushButton_IP.setText("Set IP Address")#TODO: Remove after transfer of playrec
        self.ui.pushButton_IP.adjustSize()#TODO: Remove after transfer of playrec
        sys_state.set_status(system_state)

    def shutdown(self):
        '''
        VIEW
        TODO: rew spinx Purpose: Callback for SHUTDOWN Button
        Returns: nothing
        '''
        system_state = sys_state.get_status()
        self.cb_Butt_STOP()
        self.timertick.stoptick()
        stemlabcontrol.RPShutdown(system_state["sdr_configparams"])

        
    def stemlabcontrol_errorhandler(self,errorstring): #TODO: is not being used anywhere !
        """handler for error signals from stemlabcontrol class
            display error in standard errormessagebox
            reset playerbuttongroup and GUI
        VIEW
        :param: errorstring
        :type: str
        :raises [none]: [none]
        :return: none
        :rtype: none
        """     
        auxi.standard_errorbox(errorstring)
        stemlabcontrol.SigError.connect(self.reset_playerbuttongroup) #TODO: wird bis dato nicht emittiert
        stemlabcontrol.SigError.connect(self.reset_GUI) #TODO: wird bis dato nicht emittiert

        
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
        system_state = sys_state.get_status()
        if self.playthreadActive is True:
            #print("playthread is active, no action")

            self.logger.debug("playthread is active, no action")
            sys_state.set_status(system_state)
            return False
        self.updatecurtime(0) #TODO: true datetime from record

        if system_state["f1"] == "": #TODO: replace by line below
        # if resample_m.mdl["f1"] == "":
            sys_state.set_status(system_state)
            return False
        stemlabcontrol.SigError.connect(self.stemlabcontrol_errorhandler) #
        stemlabcontrol.SigMessage.connect(self.display_status) 
        stemlabcontrol.set_play()
        self.modality = "play"
        # start server unless already started
        if self.TEST is False:
            configparams = {"ifreq":system_state["ifreq"], "irate":system_state["irate"],
                            "rates": system_state["rates"], "icorr":system_state["icorr"],
                            "HostAddress":system_state["HostAddress"], "LO_offset":system_state["LO_offset"]}
            system_state["sdr_configparams"] = configparams
            stemlabcontrol.sdrserverstart(system_state["sdr_configparams"])
            stemlabcontrol.set_play() #wozu ? war ja schon oben !
            #print(f'play_manager configparams: {configparams}')

            self.logger.info(f'play_manager configparams: {configparams}')

            sys_state.set_status(system_state)
            if stemlabcontrol.config_socket(configparams):
                #print("playthread now activated in play_manager")
                self.logger.info("playthread now activated in play_manager")
                self.play_tstarter()
            else:
                sys_state.set_status(system_state)
                return False
        else:
            if self.play_tstarter() is False:
                sys_state.set_status(system_state)
                return False
        #TODO: activateself.ui.label_RECORDING.setStyleSheet(('background-color: \
        #                                     rgb(46,210,17)'))
        #TODO: activateself.ui.label_RECORDING.setText("PLAY")
        #TODO: activateself.ui.indicator_Stop.setStyleSheet('background-color: rgb(234,234,234)')
        #TODO: activate.ui.pushButton_Rec.setEnabled(False)
            #print("stemlabcontrols activated")
            self.logger.info("stemlabcontrols activated")
        sys_state.set_status(system_state)
        return True
    
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


    def cb_Butt_STOP(self):
        """
        VIEW
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
        system_state = sys_state.get_status()
####STRUCT TODO: das könnte ein eigener stop_manager sein :
        if self.playthreadActive is False:
            system_state["fileopened"] = False ###CHECK
            self.SigRelay.emit("cm_all_",["fileopened",False])
            sys_state.set_status(system_state) ####Remove after core full impl
            return
        if self.playthreadActive:
            self.playrec_tworker.stop_loop()
        if self.TEST is False:
            stemlabcontrol.sdrserverstop()
        self.updatecurtime(0)        # reset playtime counter #TODO: true datetime from record
        self.reset_playerbuttongroup()
        sys_state.set_status(system_state)
        #self.reset_GUI()
        self.SigGUIReset.emit()


    def reset_playerbuttongroup(self):
        """
        VIEW

        """
        system_state = sys_state.get_status()
        self.ui.pushButton_Play.setIcon(QIcon("play_v4.PNG"))
        self.ui.pushButton_Play.setChecked(False)
        self.ui.pushButton_Loop.setChecked(False)
        self.playthreadActive = False
        #self.activate_tabs(["View_Spectra","Annotate","Resample","YAML_editor","WAV_header"])
        self.setactivity_tabs("Player","activate",[])
        system_state["fileopened"] = False ###CHECK
        self.SigRelay.emit("cm_all_",["fileopened",False])
        self.ui.radioButton_LO_bias.setEnabled(True)
        self.ui.lineEdit_LO_bias.setEnabled(True)
        self.ui.ScrollBar_playtime.setEnabled(False)
        self.ui.pushButton_adv1byte.setEnabled(False)
        sys_state.set_status(system_state)


    def play_tstarter(self):  # TODO: Argument (self, modality), modality= "recording", "play", move to module cplayrec controller
        """_start playback via data stream to STEMLAB sdr server
        starts thread 'playthread' for data streaming to the STEMLAB
        instantiates thread worker method
        initializes signalling_
        CONTROLLER
        :return: _False if error, True on succes_
        :rtype: _Boolean_
        """        

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
        '''
        print("file opened in playloop thread starter")
        if self.wavheader['nBitsPerSample'] == 16 or self.wavheader['nBitsPerSample'] == 24 or self.wavheader['nBitsPerSample'] == 32:
            pass
            #TODO: Anpassen an andere Fileformate, Einbau von Positionen 
        else:
            auxi.standard_errorbox("dataformat not supported, only 16, 24 and 32 bits per sample are possible")
            return False
        system_state = sys_state.get_status()
        self.playthread = QThread()
        self.playrec_tworker = playrec_worker(stemlabcontrol)
        self.playrec_tworker.moveToThread(self.playthread)
        self.playrec_tworker.set_0(system_state["f1"])
        self.playrec_tworker.set_1(system_state["timescaler"])
        self.playrec_tworker.set_2(self.TEST)
        self.playrec_tworker.set_3(self.modality)
        self.playrec_tworker.set_6(self.gain)
        format = [self.wavheader["wFormatTag"], self.wavheader['nBlockAlign'], self.wavheader['nBitsPerSample']]
        self.playrec_tworker.set_7(format)
        
        self.prfilehandle = self.playrec_tworker.get_4() #TODO CHECK IF REQUIRED test output, no special other function
        #if self.modality == "play": #TODO: activate
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
            #self.inactivate_tabs(["View_Spectra","Annotate","Resample","YAML_editor","WAV_header"])
            self.setactivity_tabs("Player","inactivate",[])
            self.logger.info("playthread started in playthread_threadstarter = play_tstarter() (threadstarter)")
            # TODO replace playthreadflag by not self.playthread.isFinished()
            sys_state.set_status(system_state)
            return True
        else:
            auxi.standard_errorbox("STEMLAB data transfer thread could not be started")
            sys_state.set_status(system_state)
            return False

    def showRFdata(self):
        """_take over datasegment from player loop worker and caluclate from there the signal volume and present it in the volume indicator
        read gain value and present it in the player Tab
        read data segment and correlate with previous one --> detect tracking errors and correct them_
        GUI Element
        :return: _False if error, True on succes_
        :rtype: _Boolean_
        """        
        system_state = sys_state.get_status()
        gain = self.playrec_tworker.get_6()
        data = self.playrec_tworker.get_5()
        #print("dispRFdata reached")
        #TODO: Test tracking error detector: not yet good  ! Bisher kompletter Blödsinn
        #Idea: evaluate the correlation coefficient between the current and the previous data segment. 
        # If lo and hi byte are interchanged I would expect much worse correlation, because the low byte then dominates the number and noise is much more prominent there
        # if that is too weak, try with second highest nibble
        if "previous_RF_data" in system_state.keys(): 
            # x1 = np.bitwise_and(data[0::2], 0xFFFF) #+ 1j * data[1::2]
            # x2 = np.bitwise_and(system_state["previous_RF_data"][0::2], 0xFFFF) #+1j * system_state["previous_RF_data"][1::2]
            # lx1 = (x1 >> 8) & 0xF
            # lx2 = (x2 >> 8) & 0xF

            # ccf = np.corrcoef([x1, x2])
            ccf = np.corrcoef([data[0::2], system_state["previous_RF_data"][0::2]])
            #print(f"correlation RF with previous segment: {ccf} len(data): {len(data[0::2])} meandelta: {np.mean(data[0::2]-system_state['previous_RF_data'][0::2])}")

        system_state["previous_RF_data"] = data
        # end tracking error detector

        s = len(data)
        nan_ix = [i for i, x in enumerate(data) if np.isnan(x)]
        if np.any(np.isnan(data)):
            self.stopstate = True
            time.sleep(1)
            data[nan_ix] = np.zeros(len(nan_ix))
            #ff = median_filter(data,30, mode = 'constant')
            #print(f"showRFdata: NaN found in data, length: {len(nan_ix)} , maxval: {np.max(data)}, avg: {np.median(data)}")
            self.logger.error("show RFdata: NaN found in data, length: %i ,maxval: %f , avg: %f" , len(nan_ix),  np.max(data), np.median(data))
            sys_state.set_status(system_state)
            return(False)
        cv = (data[0:s-1:2].astype(np.float32) + 1j * data[1:s:2].astype(np.float32))*gain
        if self.wavheader['wFormatTag'] == 1:
            scl = int(2**int(self.wavheader['nBitsPerSample']-1))-1
        elif self.wavheader['wFormatTag']  == 3:
            scl = 1 #TODO:future system state
        else:
            auxi.standard_errorbox("wFormatTag is neither 1 nor 3; unsupported Format, this file cannot be processed")
            sys_state.set_status(system_state)
            return False
        #print(f"scl = {scl}")
        av = np.abs(cv)/scl  #TODO rescale according to scaler from formattag:
        vol = np.mean(av)
        #print(f"average signal: {vol} , gain: {gain}, scl: {self.scl}")
        # make vol a dB value and rescale to 1000
        # 900 = 0 dB
        # 1000 = overload und mache Balken rot
        # min Anzeige = 1 entspricht -100 dB
        #print(f"data update from showRFdata: {vol}")
        refvol = 1
        dBvol = 20*np.log10(vol/refvol)
        dispvol = min(dBvol + 80, 100)
        self.ui.progressBar_volume.setValue(int(np.floor(dispvol*10))) 
        if dispvol > 80:
            self.ui.progressBar_volume.setStyleSheet("QProgressBar::chunk "
                    "{"
                        "background-color: red;"
                    "}")
        elif dispvol < 30:
            self.ui.progressBar_volume.setStyleSheet("QProgressBar::chunk "
                    "{"
                        "background-color: yellow;"
                    "}")           
        else:
            self.ui.progressBar_volume.setStyleSheet("QProgressBar::chunk "
                    "{"
                        "background-color: green;"
                    "}")
        sys_state.set_status(system_state)

    ######################## REPLACE BY INDIVIDUAL GUI updaters #############################


    def showfilename(self):
        """_updates the name of currenly loaded data file in all instances of filename labels_
        :param : none if old system, args[0] = string with filename to be displayed 
        :type : none if old system, str else
        '''
        :raises [ErrorType]: [ErrorDescription]
        '''
        :return: none
        :rtype: none
        """ 
        #self.SigRelay.emit("cm_all_",["prominence",self.PROMINENCE])
        self.SigRelay.emit("cexex_all_",["updateGUIelements",0])
        #TODO TODO TODO: remove the following after change to all new modules and Relay
        self.my_dirname = os.path.dirname(system_state["f1"])
        self.my_filename, self.ext = os.path.splitext(os.path.basename(system_state["f1"]))
        self.ui.label_Filename_Annotate.setText(self.my_filename + self.ext)
        self.ui.label_Filename_WAVHeader.setText(self.my_filename + self.ext)
        self.ui.label_Filename_Player.setText(self.my_filename + self.ext)
        #system_state = sys_state.get_status()
######################## END REPLACE BY INDIVIDUAL GUI updaters #############################

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
        system_state = sys_state.get_status()
        prfilehandle = self.playrec_tworker.get_4()
        self.playthread.quit()
        self.playthread.wait()
        time.sleep(0.1)
        prfilehandle.close()
        system_state["fileopened"] = False
        self.SigRelay.emit("cm_all_",["fileopened",False])
        if self.stopstate == True:
            #print("EOF-manager: player has been stopped")
            self.logger.info("EOF-manager: player has been stopped")
            time.sleep(0.5)
            sys_state.set_status(system_state)
            return
        if (os.path.isfile(self.my_dirname + '/' + self.wavheader['nextfilename']) == True and self.wavheader['nextfilename'] != "" ):
            #TODO: new wavheader needs to be extracted
            # play next file in nextfile-list
            system_state["f1"] = self.my_dirname + '/' + self.wavheader['nextfilename']
            self.SigRelay.emit("cm_all_",["f1",self.my_dirname + '/' + self.wavheader['nextfilename']])
            self.SigRelay.emit("cm_all_",["my_filename",self.my_filename])
            self.wavheader = WAVheader_tools.get_sdruno_header(self,system_state["f1"])
            time.sleep(0.1)
            self.play_tstarter()
            time.sleep(0.1)
            system_state["fileopened"] = True
            self.SigRelay.emit("cm_all_",["fileopened",True])
            #TODO: self.my_filename + self.ext müssen updated werden, übernehmen aus open file
            self.showfilename() #Remove after implementing all Modules Relay
            self.SigRelay.emit("cexex_all_",["updateGUIelements",0])
            self.updatecurtime(0) #TODO: true datetime from record
            self.logger.info("fetch nextfile")

        elif self.ui.pushButton_Loop.isChecked() == True:
            time.sleep(0.1)
            #("restart same file in endless loop")
            self.logger.debug("restart same file in endless loop")
            #no next file, but endless mode active, replay current system_state["f1"]
            self.play_tstarter()
            time.sleep(0.1)
            self.logger.info("playthread active: %s", self.playthreadActive)
            system_state["fileopened"] = True
            self.SigRelay.emit("cm_all_",["fileopened",True])
            self.updatecurtime(0) #TODO: true datetime from record
        elif self.ui.listWidget_playlist.count() > 0:
            # filecheck_loop = True
            # while filecheck_loop == True:
            if system_state["playlist_ix"] == 0:
                system_state["playlist_ix"] += 1 #TODO: aktuell Hack, um bei erstem File keine Doppelabspielung zu triggern
            playlist_len = self.ui.listWidget_playlist.count()
            if system_state["playlist_ix"] < playlist_len: #TODO check if indexing is correct
                self.playthreadActive = False
                #print(f"EOF manager: playlist index: {system_state['playlist_ix']}")
                self.logger.debug("EOF manager: playlist index: %i", system_state['playlist_ix'])
                lw = self.ui.listWidget_playlist

                self.logger.info("fetch next list file")
                item_valid = False
                
                while (not item_valid) and (system_state["playlist_ix"] < playlist_len):
                    item = lw.item(system_state["playlist_ix"])
                    system_state["f1"] = self.my_dirname + '/' + item.text() #TODO replace by line below
                    self.SigRelay.emit("cm_all_",["f1",self.my_dirname + '/' + item.text()])
                    self.SigRelay.emit("cm_all_",["my_filename",self.my_filename])
                    self.logger.info("EOF manager file: %s", system_state["f1"])
                    self.wavheader = WAVheader_tools.get_sdruno_header(self,system_state["f1"])
                    item_valid = True
                    if not self.wavheader:
                        self.logger.warning("EOF_manager: wrong wav file, skip to next listentry")
                        system_state["playlist_ix"] += 1
                        item_valid = False

                if not (system_state["playlist_ix"] < playlist_len):
                    system_state["playlist_ix"] = 0
                    sys_state.set_status(system_state)
                    self.logger.info("EOF_manager: end of list, stop player")
                    time.sleep(0.5)
                    self.updatecurtime(0)
                    self.cb_Butt_STOP()
                    self.ui.listWidget_playlist.clear()
                    self.ui.listWidget_sourcelist.clear()
                    sys_state.set_status(system_state)
                    return()
                
                system_state["playlist_ix"] += 1                #TODO: system_state Eintragung von icorr etc erfolgt an mehreren STellen, fileopen, extract dat header und hier. Könnte an einer Stelle passieren, immer, sobald ein wav-header extrahiert wird
                system_state["ifreq"] = self.wavheader['centerfreq'] + system_state["LO_offset"]
                system_state["irate"] = self.wavheader['nSamplesPerSec']
                system_state["icorr"] = 0
                system_state["readoffset"] = self.readoffset
                system_state["timescaler"] = self.wavheader['nSamplesPerSec']*self.wavheader['nBlockAlign']
                #print(f'EOF manager new wavheader: {self.wavheader["nSamplesPerSec"]}')
                self.logger.debug("EOF manager new wavheader: %i", self.wavheader["nSamplesPerSec"])
                #TODO: write new header to wav edior
                sys_state.set_status(system_state)
                time.sleep(0.1)
                self.showfilename()
                if not self.TEST:
                    stemlabcontrol.sdrserverstop()
                    self.logger.info("EOF manager start play_manager")
                self.play_manager()
                system_state["fileopened"] = True
                self.SigRelay.emit("cm_all_",["fileopened",True])
                time.sleep(0.5) #TODO: necessary because otherwise file may not yet have been opened by playloopworker and then updatecurtime crashes because of invalid filehandel 
                #may be solved by updatecurtime not accessing the filehandle returned from playworker but directly from system_state["f1"]
                self.updatecurtime(0) #TODO: true datetime from record
            else:
                #reset playlist_ix
                system_state["playlist_ix"] = 0
                sys_state.set_status(system_state)
                self.logger.info("EOF_manager: stop player")
                time.sleep(0.5)
                self.updatecurtime(0)
                self.cb_Butt_STOP()
                self.ui.listWidget_playlist.clear()
                self.ui.listWidget_sourcelist.clear()
        else:
            #no next file,no endless loop --> stop player
            #print("stop player")
            self.logger.info("EOF_manager: stop player 2")
            time.sleep(0.5)
            self.cb_Butt_STOP()
            ##TODO: introduce separate stop_manager
            # if self.playthread.isRunning():
            # self.playthreadActive = True
        sys_state.set_status(system_state)


    def updatecurtime(self,increment):             #increment current time in playtime window and update statusbar
        """
        VIEW or CONTROLLER ?
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
        #print("incrementcurtime reached")
        system_state = sys_state.get_status()
        progress = 0
        if self.playthreadActive is False:
            sys_state.set_status(system_state)
            return False
        timestr = str(self.wavheader['starttime_dt'] + ndatetime.timedelta(seconds=self.curtime))

        if increment == 0:
            timestr = str(ndatetime.timedelta(seconds=0))
            self.curtime = 0
            self.ui.lineEditCurTime.setText(timestr)

        if self.modality == 'play' and self.pausestate is False:
            if self.curtime > 0 and increment < 0:
                self.curtime += increment
            if self.curtime < system_state["playlength"] and increment > 0:
                self.curtime += increment
            if system_state["playlength"] > 0:
                progress = int(np.floor(1000*(self.curtime/system_state["playlength"])))
            else:
                sys_state.set_status(system_state)
                return False
            position_raw = self.curtime*system_state["timescaler"]
            # TODO: check, geändert 09-12-2023: byte position mit allen Blockaligns auch andere als 4(16 bits); 
            # TODO: adapt for other than header 216
            position = min(max(216, position_raw-position_raw % self.wavheader['nBlockAlign']),
                           self.wavheader['data_nChunkSize'])
            # guarantee integer multiple of nBlockalign, > 0, <= filesize
            if increment != -1 and increment != 1 or self.timechanged == True:
                if system_state["fileopened"] is True:
                    #print(f'increment curtime cond seek cur file open: {system_state["f1"]}')
                    self.prfilehandle = self.playrec_tworker.get_4()
                    self.prfilehandle.seek(int(position), 0) #TODO: Anpassen an andere Fileformate
        
        #timestr = str(self.wavheader['starttime_dt'] + ndatetime.timedelta(seconds=self.curtime))
        self.ui.lineEditCurTime.setText(timestr) 
        self.ui.ScrollBar_playtime.setProperty("value", progress)
        sys_state.set_status(system_state)
        #print("leave updatecurtime")
        return True


    def jump_1_byte(self):             #increment current time in playtime window and update statusbar
        """
        VIEW or CONTROLLER ?
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
        system_state = sys_state.get_status()
        #print("tracking: jump 1 byte")
        self.logger.debug("tracking: jump 1 byte")
        if self.modality == 'play' and self.pausestate is False:
            if system_state["fileopened"] is True:
                self.prfilehandle = self.playrec_tworker.get_4()
                self.prfilehandle.seek(1,1) #TODO: ##OPTION from current position## 0 oder 1 ?
        sys_state.set_status(system_state)
        # not yet safe, because increment may happen beyond EOF, check for EOF

   
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
        system_state = sys_state.get_status()
        sbposition = self.ui.ScrollBar_playtime.value() #TODO: already in updatecurtime(...)
        self.curtime = int(np.floor(sbposition/1000*system_state["playlength"]))  # seconds
        timestr = str(self.wavheader['starttime_dt'] + ndatetime.timedelta(seconds=self.curtime))
        #win.ui.lineEditCurTime.setText(timestr)
        self.ui.lineEditCurTime.setText(timestr)
        position_raw = self.curtime*system_state["timescaler"]  #timescaler = bytes per second
        # TODO: check, geändert 09-12-2023: byte position mit allen Blockaligns auch andere als 4(16 bits); 
        # TODO: adapt for other than header 216
        position = min(max(216, position_raw-position_raw % self.wavheader['nBlockAlign']),
                            self.wavheader['data_nChunkSize']+216) # guarantee reading from integer multiples of 4 bytes, TODO: change '4', '216' to any wav format ! 
        if system_state["fileopened"] is True:
            #print("Jump to next position")
            self.logger.debug("jumptoposition reached")
            #print(f'system_state["fileopened"]: {system_state["fileopened"]}')
            self.logger.debug("system_state['fileopened']: %s",system_state["fileopened"])
            self.prfilehandle = self.playrec_tworker.get_4()
            self.prfilehandle.seek(int(position), 0) #TODO: Anpassen an andere Fileformate
        #calculate corresponding position in the record file; value = 216 : 1000
        #jump to the targeted position with integer multiple of wavheader["nBitsPerSample"]/4
        sys_state.set_status(system_state)

 
    def GuiEnterCurTime(self):     ###########TODO: wird nirgends verwendet, remove ?

        timestr = self.ui.lineEditCurTime.text()
        #Convert timestr back to seconds
        diagnostic = timestr.split(":")
        if int(diagnostic[1]) > 59 or int(diagnostic[2]) > 59:
            auxi.standard_errorbox("Minutes and Seconds cannot be > 59")
            return                                                 
        total_seconds = sum(x * int(t) for x, t in zip([3600, 60, 1], timestr.split(":"))) 

        self.curtime = total_seconds
        self.timechanged = True


    def reset_LO_bias(self):

        system_state = sys_state.get_status()
        self.ui.radioButton_LO_bias.setChecked(False)
        self.ui.radioButton_LO_bias.setEnabled(True)
        system_state["LO_offset"] = 0
        sys_state.set_status(system_state)
        self.ui.lineEdit_LO_bias.setText("0")
        self.ui.lineEdit_LO_bias.setStyleSheet("background-color: white")


    def update_LO_bias(self):
        """ Purpose: update LO bias setting; 
        check validity of offset value: isnumeric, integer
        :param [ParamName]: none
        :type [ParamName]: none
        :raises none
        :return: True if successful, otherwise False
        :rtype: Boolean
        """
        system_state = sys_state.get_status()

        if self.playthreadActive:
            sys_state.set_status(system_state)
            return False
        
        LObiasraw = self.ui.lineEdit_LO_bias.text().lstrip(" ")
        if len(LObiasraw) < 1:
            sys_state.set_status(system_state)
            return False
        LObias_sign = 1
        if LObiasraw[0] == "-":
            LObias_sign = -1
            LObias_test = LObiasraw.lstrip("-")
            if len(LObias_test)<1:
                sys_state.set_status(system_state)
                return False
        else:
            LObias_test = LObiasraw
        if LObias_test.isnumeric() == True: 
            i_LO_bias = LObias_sign*int(LObias_test)
        else:
            auxi.standard_errorbox("invalid numeral in center frequency offset field, please enter valid integer value (kHz)")
            self.reset_LO_bias()
            sys_state.set_status(system_state)
            return False
        #transfer to systemstate
        if self.ui.radioButton_LO_bias.isChecked() is True:
            system_state["LO_offset"] = int(i_LO_bias*1000)
            system_state["ifreq"] = int(self.wavheader['centerfreq'] + system_state["LO_offset"])
            sys_state.set_status(system_state)
        sys_state.set_status(system_state)
        return True
    
###############################################CURRENT STATE OF TRANSFER


    def LO_bias_checkbounds(self):
        """ Purpose: checks if LO bias setting is within valid bounds; 
        :param [ParamName]: none
        :type [ParamName]: none
        :raises none
        :return: True if successful, otherwise False
        :rtype: Boolean
        """

        system_state = sys_state.get_status()
        eff_ifreq = system_state["LO_offset"] + system_state["ifreq"]
        if not self.update_LO_bias():
            sys_state.set_status(system_state)
            return False                 
        if (eff_ifreq <= 0):
            auxi.standard_errorbox("invalid negative center frequency offset, magnitude greater than LO frequency of the record, please correct value")
            self.reset_LO_bias()
            self.cb_Butt_STOP()
            sys_state.set_status(system_state)
            return False
        if (eff_ifreq > 60000000):
            auxi.standard_errorbox("invalid  center frequency offset, sum of record LO and offset must be < 60000 kHz, please correct value")
            self.reset_LO_bias()
            self.cb_Butt_STOP()
            sys_state.set_status(system_state)
            return False
        sys_state.set_status(system_state)
        return True

    def activate_LO_bias(self):
        """ Purpose: handle radiobutton for LO bias setting; 
        (1) highlight LO_lineEdit window
        (2) call update of offset value
        :param [ParamName]: none
        :type [ParamName]: none
        :raises none
        :return: none
        :rtype: none
        """

        # if self.ui.radioButton_LO_bias.isChecked() is True:
        #     self.ui.lineEdit_LO_bias.setEnabled(True)
        # else:
        #     self.ui.lineEdit_LO_bias.setEnabled(False)
        #     self.ui.lineEdit_LO_bias.setText("0000")

        #i_LO_bias = 0 ###TODO: activate ???
        self.ui.lineEdit_LO_bias.setStyleSheet("background-color: white")
        #TODO: ACTIVATE LObias check code
        if self.ui.radioButton_LO_bias.isChecked() is True:
            self.ui.lineEdit_LO_bias.setStyleSheet("background-color: yellow")
            self.update_LO_bias()



 
############################## END TAB PLAYER ####################################

############################## TAB RESAMPLER, REMOVE COMPLETELY ####################################

    # def reformat_targetLOpalette(self): #TODO: check, if this stays part of gui or should be shifted to resampler module
    #     """
    #     VIEW Element of Tab 'resample
    #     """
    #     self.ui.lineEdit_resample_targetLO.setStyleSheet("background-color: bisque1")

    # def cb_Butt_resample(self):
    #     #REMOVE AFTER CHANGE TO NEW STRUCTURE ; call 
    #     #self.ui.listWidget_playlist_2.itemChanged.connect(resample_v.reslist_update) #dummy in order to prevent exceptions in case the signal is already disconnevted
    #     #system_state = sys_state.get_status()
    #     try:
    #         self.ui.listWidget_playlist_2.itemChanged.disconnect(resample_v.reslist_update)
    #     except:
    #         pass

    #     resample_v.cb_resample()
    #     self.ui.radioButton_advanced_sampling.setChecked(False)

    
############################## TAB ANNOTATE ####################################

    def annotation_completed(self):
        """_summary_
        VIEW, gehört zum Tab Annotate
        """
        self.ui.pushButtonAnnotate.setStyleSheet("background-color : rgb(170, 255, 127)")
        self.ui.pushButtonAnnotate.setEnabled(False)
        self.ui.pushButtonAnnotate.setFont(QFont('MS Shell Dlg 2', 12))
        self.ui.pushButtonDiscard.setEnabled(False)
        self.ui.progressBar_2.setProperty("value", 100)
        self.ui.lineEdit.setText('Record has already been annotated. For re-annotation delete annotation folder')
        self.ui.lineEdit.setStyleSheet("background-color : yellow")
        self.ui.lineEdit.setFont(QFont('MS Shell Dlg 2', 12))
        self.ui.pushButton_Writeyamlheader.setEnabled(True)
        self.flag_ann_completed = True

    def annotation_activate(self):
        """_summary_
        VIEW, gehört zum Tab Annotate
        """
        self.ui.pushButtonAnnotate.setStyleSheet("background-color : rgb(220,220,220)")
        self.ui.pushButtonAnnotate.setEnabled(True)
        self.ui.pushButtonAnnotate.setFont(QFont('MS Shell Dlg 2', 12))
        self.ui.pushButtonDiscard.setEnabled(False)
        self.ui.lineEdit.setText('annotation can be started or continued')
        self.ui.lineEdit.setStyleSheet("background-color : yellow")
        self.ui.lineEdit.setFont(QFont('MS Shell Dlg 2', 12))

    def annotation_deactivate(self):
        """_summary_
        VIEW, gehört zum Tab Annotate
        """        
        self.ui.pushButtonAnnotate.setStyleSheet("background-color : rgb(220,220,220)")
        self.ui.pushButtonAnnotate.setEnabled(False)
        self.ui.pushButtonAnnotate.setFont(QFont('MS Shell Dlg 2', 12))

    def scan_completed(self):
        """_summary_
        VIEW, gehört zum Tab Annotate
        """
        self.ui.pushButton_Scan.setStyleSheet("background-color : rgb(170, 255, 127)")
        self.ui.pushButton_Scan.setFont(QFont('MS Shell Dlg 2', 12))
        self.ui.pushButton_Scan.setEnabled(False)
        self.ui.pushButtonAnnotate.setEnabled(True)
        self.ui.pushButtonAnnotate.setFont(QFont('MS Shell Dlg 2', 12))
        self.ui.lineEdit.setText('autoscan has been completed, peaks and SNRs identified')
        self.ui.lineEdit.setStyleSheet("background-color : yellow")
        self.ui.lineEdit.setFont(QFont('MS Shell Dlg 2', 12))
        #TODO: save settings for MF Kernel, SNR baselineoffset min peak width min peak distance to status file
        #TODO: write spinbox values to status file
        peakwidth = self.ui.spinBoxminPeakwidth.value()
        filterkernel = self.ui.spinBoxKernelwidth.value()
        baselineoffset = self.ui.spinBoxminBaselineoffset.value()
        minSNR = self.ui.spinBoxminSNR_ScannerTab.value()
        minPeakDist = self.ui.spinBoxminPeakDistance.value()
        NumScan = self.ui.spinBoxNumScan.value()
        try:
            stream = open(self.status_filename, "r")
            status = yaml.safe_load(stream)
            stream.close()
            status["peakwidth"] = peakwidth
            status["filterkernel"] = filterkernel
            status["baselineoffset"] = baselineoffset
            status["minSNR"] = minSNR
            status["minPeakDist"] = minPeakDist
            status["NumScan"] = NumScan        
            stream = open(self.status_filename, "w")
            yaml.dump(status, stream)
            stream.close()
        except:
            #print("cannot get/put status")
            self.logger.error("scan_completed: cannot get/put status")

    def scan_activate(self):
        """_summary_
        VIEW, gehört zum Tab Annotate
        """
        self.ui.pushButton_Scan.setStyleSheet("background-color : rgb(220,220,220)")
        self.ui.pushButton_Scan.setFont(QFont('MS Shell Dlg 2', 12))
        self.ui.pushButton_Scan.setEnabled(True)
        self.ui.pushButtonAnnotate.setEnabled(False)
        self.ui.pushButtonAnnotate.setFont(QFont('MS Shell Dlg 2', 12))
        self.ui.lineEdit.setText('autoscan can be started (search for TX peaks and SNR values)')
        self.ui.lineEdit.setStyleSheet("background-color : yellow")
        self.ui.lineEdit.setFont(QFont('MS Shell Dlg 2', 12))

    def scan_deactivate(self):
        """_summary_
        VIEW, gehört zum Tab Annotate
        """
        self.ui.pushButton_Scan.setStyleSheet("background-color : rgb(220,220,220)")
        self.ui.pushButton_Scan.setFont(QFont('MS Shell Dlg 2', 12))
        self.ui.pushButton_Scan.setEnabled(False)
        self.ui.lineEdit.setText('')
        self.ui.lineEdit_TX_Site.setText('')
        self.ui.lineEdit_Country.setText('')
        self.ui.lineEdit.setStyleSheet("background-color : white")
        self.ui.lineEdit.setFont(QFont('MS Shell Dlg 2', 12))

    def minSNRupdate(self):
        """_summary_
        VIEW of Annotator Module
        """
        self.PROMINENCE = self.ui.spinBoxminSNR.value()
        self.ui.spinBoxminSNR_ScannerTab.setProperty("value", self.PROMINENCE)
        self.SigRelay.emit("cm_all_",["prominence",self.PROMINENCE])
        self.SigRelay.emit("cexex_view-spectrum",["updateGUIelements",0])


        #self.cb_plot_spectrum()


        #.cb_plot_spectrum()

    def activate_WAVEDIT(self):
        self.show()
        if self.ui.radioButton_WAVEDIT.isChecked() is True:
                    self.ui.tableWidget_basisfields.setEnabled(True)
                    self.ui.tableWidget_starttime.setEnabled(True)
                    self.ui.tableWidget_3.setEnabled(True)      
        else:
                    self.ui.tableWidget_basisfields.setEnabled(False)
                    self.ui.tableWidget_starttime.setEnabled(False)
                    self.ui.tableWidget_3.setEnabled(False)

    def ann_spectrum(self,dummy,data):      #TODO: This is a controller method, should be transferred to an annotation module
        """
        CONTROLLER
        generate a single spectrum from complex data
        scale x-axis as frequencies in the recorded AM band
        scale y-axis in dB
        calculate baseline basel from moving median filtering
        find spectral peaks (= transmitters) and calculate the corresponding properties
        requires the following properties to exist:
            self.DATABLOCKSIZE
        :param self: An instance of the class containing attributes such as header information and filtering parameters.
        :type self: object
        :param dummy: A dummy variable not used in the function.
        :type dummy: any
        :param data: A numpy array containing the complex data IQ data read from wav file
        :type data: numpy.ndarray of float32, even entries = real odd entries = imaginary
                part of the IQ signal
        :raises [ErrorType]: [ErrorDescription]
        :return: A dictionary containing various arrays related to the spectral analysis:
                - datax: The frequency data.type: float32
                - datay: The amplitude data.type: float32
                - datay_filt: The filtered amplitude data.type: float32
                - peaklocs: The indices of the identified peaks in the amplitude data.type: float32
                - peakprops: Properties of the identified peaks, such as their height and width. type: dict
                - databasel: The baseline data used in the filtering process.type: float32
        :rtype: dict
        """
        # extract imaginary and real parts from complex data 
        realindex = np.arange(0,self.DATABLOCKSIZE,2)
        imagindex = np.arange(1,self.DATABLOCKSIZE,2)
        #calculate spectrum and shift/rescale appropriately
        spr = np.abs(np.fft.fft((data[realindex]+1j*data[imagindex])))
        N = len(spr)
        spr = np.fft.fftshift(spr)
        flo = self.wavheader['centerfreq'] - self.wavheader['nSamplesPerSec']/2
        fup = self.wavheader['centerfreq'] + self.wavheader['nSamplesPerSec']/2
        freq0 = np.linspace(0,self.wavheader['nSamplesPerSec'],N)
        freq = freq0 + flo
        datax = freq
        datay = 20*np.log10(spr)
        # filter out all data below the baseline; baseline = moving median
        # filter kernel is self.FILTERKERNEL % of the spectral span
        datay_filt = datay
        kernel_length = int(N*self.FILTERKERNEL/100)
        # kernel length must be odd integer
        if (kernel_length % 2) == 0:
            kernel_length += 1
        
        databasel = median_filter(datay,kernel_length, mode = 'constant')
        datay_filt[datay_filt < databasel] = databasel[datay_filt < databasel]
        # find all peaks which are self.PROMINENCE dB above baseline and 
        # have a min distance of self.DELTAF and a min width of self.PEAKWIDTH
        dist = np.floor(np.maximum(self.DELTAF/self.wavheader['nSamplesPerSec']*N,100))
        wd = np.floor(self.PEAKWIDTH/self.wavheader['nSamplesPerSec']*N)

        peaklocs, peakprops = sig.find_peaks(datay_filt,
                        prominence=(self.PROMINENCE,None), distance=dist, width = wd)
        ret = {"datax": datax, "datay": datay, "datay_filt": datay_filt,
               "peaklocs": peaklocs, "peakprops": peakprops, "databasel": databasel}
        return ret

    def readsegment(self,position,DATABLOCKSIZE):       #TODO: This is a controller method, should be transferred to an annotation module
        """
        CONTROLLER
        opens file system_state["f1"] and reads a data segment from position 216 + position
        the segment has length DATABLOCKSIZE
        segment is returned as float array of complex numbers, even entries = real, odd entries = imaginary
        :param self: An instance of the class containing attributes such as header information and filtering parameters.
        :type self: object
        :param: position
        :type position: int
        :param: DATABLOCKSIZE: size of bytes to be read
        :type position: int
        :raises [ErrorType]: [ErrorDescription]
        :return: ret = dictionary with fields: ret["data"], ret["size]; size is either the number of bytes read or -1 in case of invalid file formats
        :rtype: dictionary; type of field "data": np.float32 array of size self.DATABLOCKSIZE ; type of field "size": int
        """
        #print(f"read segment reached, position: {position}")
        #data = np.empty(DATABLOCKSIZE, dtype=np.int16) #TODO: DATABLOCKSIZE dynamisch anpassen !
        system_state = sys_state.get_status()
        self.fileHandle = open(system_state["f1"], 'rb')
        pscale = self.wavheader['nBlockAlign']
        if self.wavheader['wFormatTag'] == 1:
            scl = int(2**int(self.wavheader['nBitsPerSample']-1))-1   #if self.wavheader['nBitsPerSample'] 2147483648 8388608 32767
        else:
            scl = 1
        #TODO:
        #position = int(np.floor(pscale*np.round(self.wavheader['data_nChunkSize']*system_state["horzscal"]/pscale/1000)))
        if self.wavheader['nBitsPerSample'] == 16:
            #position = int(np.floor(pscale*np.round(self.wavheader['data_nChunkSize']*system_state["horzscal"]/pscale/1000)))
            self.fileHandle.seek(self.readoffset+position, 0)
            # invalid = np.empty(10, dtype=np.int16)  %TODO: remove after tests, 05-12-2023
            # invalid = np.linspace(0,9,10)  %TODO: remove after tests, 05-12-2023
            if self.wavheader['wFormatTag'] == 3:
                data = np.empty(DATABLOCKSIZE, dtype=np.float16)
                size = self.fileHandle.readinto(data)
            elif self.wavheader['wFormatTag'] == 1:
                dataraw = np.empty(DATABLOCKSIZE, dtype=np.int16)
                size = self.fileHandle.readinto(dataraw)
                data = dataraw.astype(np.float32)/scl
            else:
                auxi.standard_errorbox("unsupported Format Tag (wFormatTag): value other than 1 or 3 encountered")
                #return invalid
                size = -1
            self.fileHandle.close()
            # if size < DATABLOCKSIZE:
            #     return invalid
            self.duration = self.wavheader['data_nChunkSize']/pscale/self.wavheader['nSamplesPerSec']
        elif self.wavheader['nBitsPerSample'] == 32:
            #position = int(np.floor(pscale*np.round(self.wavheader['data_nChunkSize']*system_state["horzscal"]/pscale/1000)))
            self.fileHandle.seek(216+position, 0) #TODO: ist 216 allgemein oder self.readoffset+position, 0)
            if self.wavheader['wFormatTag'] == 3:
                data = np.empty(DATABLOCKSIZE, dtype=np.float32)
                size = self.fileHandle.readinto(data)
            elif self.wavheader['wFormatTag'] == 1:
                dataraw = np.empty(DATABLOCKSIZE, dtype=np.int32)
                size = self.fileHandle.readinto(dataraw)
                data = dataraw.astype(np.float32)/2147483648        
            else:
                auxi.standard_errorbox("Unsupported FormatTag (wFormatTag): value other than 1 or 3 encountered")
                #return invalid
                size = -1
            self.fileHandle.close()
            # if size < DATABLOCKSIZE:
            #     return invalid
            #data = dataraw.astype(np.float32)
            self.duration = self.wavheader['data_nChunkSize']/pscale/self.wavheader['nSamplesPerSec']
        elif self.wavheader['nBitsPerSample'] == 24:
            #localize data identifier
            self.fileHandle.seek(self.readoffset+position, 0)
            data = np.empty(DATABLOCKSIZE, dtype=np.float32)
            #data = np.empty(self.DATABLOCKSIZE, dtype=np.int32)
            # if self.wavheader['wFormatTag'] == 3:
            #     data = np.empty(self.DATABLOCKSIZE, dtype=np.float32)
            # elif self.wavheader['wFormatTag'] == 1:
            #     dataraw = np.empty(self.DATABLOCKSIZE, dtype=np.int32)
            #size = self.fileHandle.readinto(data)
            size = 0
            for lauf in range(0,DATABLOCKSIZE):
                d = self.fileHandle.read(3)
                if d == None:
                    self.fileHandle.close()
                    #return invalid
                    size = 3*(lauf-1)
                else:
                    #dataraw = unpack('<i', d + (0x00 if d[2] < 128 else 0xff))
                    dataraw = unpack('<%ul' % 1 ,d + (b'\x00' if d[2] < 128 else b'\xff'))
                    if self.wavheader['wFormatTag'] == 1:
                        data[lauf] = np.float32(dataraw[0]/8388608)
                    else:
                        data[lauf] = dataraw[0]
                    size += 3
            self.duration = self.wavheader['data_nChunkSize']/pscale/self.wavheader['nSamplesPerSec']
        else:
            auxi.standard_errorbox("no encodings except 16, 24 and 32 bits are supported")
            #return invalid
            size = -1
        self.fileHandle.close()
        ret = {}
        ret["data"] = data
        ret["size"] = size
        #return data
        sys_state.set_status(system_state)
        return ret

    def readsegment_new(self,f1,position,DATABLOCKSIZE,sBPS,tBPS,wFormatTag):       #TODO: This is a controller method, should be transferred to an annotation module
        """
        CONTROLLER
        opens file f1 and reads a data segment from position 216 + position #TODO: check if 216 is universal !
        the segment has length DATABLOCKSIZE
        segment is read according to format specified in wFormattag (int, float) and sBPS(16, 32, 24)
        segment is returned as float array of complex numbers, even entries = real, odd entries = imaginary
        output format is 16 or 32bit according to value specified in tBPS. No other BPS (e.g. 8) are allowed.
        24 Bit mode is not recommended for frequent calling, because inefficient (slow !)
        :param self: An instance of the class containing attributes such as header information and filtering parameters.
        :type self: object
        :param: position
        :type position: int
        :param: DATABLOCKSIZE: size of bytes to be read
        :type position: int
        :param: sBPS: Bits per sample of source file 
        :type sBPS: int
        :param: tBPS: Bits per sample of target file 
        :type tBPS: int
        :param: wFormatTag: 1 or 3, wav-Format of source file 
        :type wFormatTag: int
        :raises [ErrorType]: [ErrorDescription]
        :return: ret = dictionary with fields: ret["data"], ret["size]; size is either the number of bytes read or -1 in case of invalid file formats
        :rtype: dictionary; type of field "data": np.float32 array of size self.DATABLOCKSIZE ; type of field "size": int
        """
        #print(f"read segment reached, position: {position}")
        #data = np.empty(DATABLOCKSIZE, dtype=np.int16) #TODO: DATABLOCKSIZE dynamisch anpassen !
        fid = open(f1, 'rb')
        if wFormatTag == 1:
            scl = int(2**int(sBPS-1))-1   #if self.wavheader['nBitsPerSample'] 2147483648 8388608 32767
        else:
            scl = 1
        if sBPS == 16:
            fid.seek(self.readoffset+position, 0)
            if wFormatTag == 3: # read 16bit float
                dataraw = np.empty(DATABLOCKSIZE, dtype=np.float16)
                size = fid.readinto(dataraw)
                if tBPS == 32: #write 32 bit float
                    data = dataraw.astype(np.float32)
                else: # write to 16bit float
                    data = dataraw.astype(np.float16)
            elif wFormatTag == 1: # read int16
                dataraw = np.empty(DATABLOCKSIZE, dtype=np.int16)
                size = fid.readinto(dataraw)
                if tBPS == 32:
                    data = dataraw.astype(np.float32)/scl
                else:
                    data = dataraw.astype(np.float16)/scl
            else:
                auxi.standard_errorbox("unsupported Format Tag (wFormatTag): value other than 1 or 3 encountered")
                size = -1
            fid.close()
        elif sBPS == 32:
            fid.seek(216+position, 0) #TODO: ist 216 allgemein oder self.readoffset+position, 0)
            if  wFormatTag == 3: #read float32
                dataraw = np.empty(DATABLOCKSIZE, dtype=np.float32)
                size = fid.readinto(dataraw)
                if tBPS == 32: # write to float32
                    data = dataraw.astype(np.float32)
                else:
                    data = (dataraw>>16).astype(np.float16)# check ob das für float gilt oder nur für INT !!TODO 
                size = fid.readinto(data)
            elif  wFormatTag == 1: #read int32
                dataraw = np.empty(DATABLOCKSIZE, dtype=np.int32)
                size = fid.readinto(dataraw)
                if tBPS == 32:
                    data = dataraw.astype(np.float32)/scl
                else:
                    data = ((dataraw/scl)>>16).astype(np.float16)
                size = fid.readinto(dataraw)
            else:
                auxi.standard_errorbox("Unsupported FormatTag (wFormatTag): value other than 1 or 3 encountered")
                size = -1
            fid.close()
        elif sBPS == 24:   #This mode is useful ONLY for general short reading purposes (plotting) NOT for LOshifting !
            #localize data identifier
            fid.seek(self.readoffset+position, 0)
            data = np.empty(DATABLOCKSIZE, dtype=np.float32)
            size = 0
            for lauf in range(0,DATABLOCKSIZE):
                d = fid.read(3)
                if d == None:
                    fid.close()
                    size = 3*(lauf-1)
                else:
                    dataraw = unpack('<%ul' % 1 ,d + (b'\x00' if d[2] < 128 else b'\xff'))
                    if  wFormatTag == 1:
                        data[lauf] = np.float32(dataraw[0]/8388608)
                    else:
                        data[lauf] = dataraw[0]
                    size += 3
        else:
            auxi.standard_errorbox("no encodings except 16, 24 and 32 bits are supported")
            #return invalid
            size = -1
        fid.close()
        ret = {}
        ret["data"] = data
        ret["size"] = size
        #return data
        return ret



    def scanupdateGUI(self):
        """_summary_
        VIEW
        """
        self.ui.label.setText("Status: Scan spectra for prominent TX peaks")
        self.ui.pushButton_Scan.setEnabled(False)
        self.ui.horizontalScrollBar_view_spectra.setEnabled(False)
        self.ui.lineEdit.setText('Please wait while spectra are analyzed for peaks')
        self.ui.lineEdit.setStyleSheet("background-color : yellow")
        self.ui.lineEdit.setFont(QFont('MS Shell Dlg 2', 12))

    def Progressbarupdate(self):
        """
        VIEW
        _summary_
        """
        self.ui.progressBar_2.setProperty("value", int(self.progressvalue/10))
        #send continue flag to autoscan task
        if self.autoscanthreadActive == True:
            self.autoscaninst.set_1(True)
            #TODO: check if here appropriate: set/get_2
            #autoscan_statuspars = {}
            #autoscan_statuspars["progressvalue"] = self.progressvalue 
            #autoscan_statuspars["horzscal"] = system_state["horzscal"]
            # __slots__[2] has entries: self.host.progressvalue, 
            # self.host.horzscal, self.host.wavheader, self.host.Baselineoffset,  self.host.DATABLOCKSIZE
            # self.host.locs_union 
            # self.host.freq_union 
            # elf.host.my_dirname + '/' + self.host.my_filename
            # self.host.annotation_filename
            # self.host.annotation

            #self.autoscaninst.set_2(autoscan_statuspars)
            checkstatus = self.autoscaninst.get_2()
            #print(f"check status from get_2 in Progresbarupdate: {checkstatus}")
            
    def status_writetableread(self):
        """
        VIEW
        _summary_
        """
        self.ui.progressBar_2.setProperty("value", int(0))
        self.ui.label.setText("Status: read MWList table for annotation")
        #send continue flag to autoscan task
        if self.autoscanthreadActive == True:
            self.autoscaninst.set_1(True)

    def autoscan_finished(self):
        """
        VIEW
        _summary_
        """
        self.ui.horizontalScrollBar_view_spectra.setEnabled(True)
        self.ui.lineEdit.setText('')
        self.ui.lineEdit_TX_Site.setText('')
        self.ui.lineEdit_Country.setText('')
        self.ui.lineEdit.setStyleSheet("background-color : white")
        self.ui.lineEdit.setFont(QFont('MS Shell Dlg 2', 12))
        self.autoscanthreadActive = True
        if self.ui.radioButton_plotpreview.isChecked() is True:
            plt.close()


    def scanplot(self):
        """
        VIEW
        _summary_
        """
        #TODO: only execute if Preview_plot == True   radioButton_plotpreview
        if self.ui.radioButton_plotpreview.isChecked() is True:
            plt.close()
            plt.cla()
            autoscan_ret = self.autoscaninst.get_0()
            pdata = autoscan_ret[2]
            #self.__slots__[0][2] = pdata
            plt.plot(pdata["datax"],pdata["datay"])
            plt.xlabel("frequency (Hz)")
            plt.ylabel("peak amplitude (dB)")
            plt.show()
            plt.pause(1)
        #send continue flag to autoscan task
        if self.autoscanthreadActive == True:
            self.autoscaninst.set_1(True)

    def autoscan(self):  #TODO: shift to controller module associated with annotation
        """
        CONTROL
        _summary_
        """
        #print("autoscan reached")
        self.logger.debug("autoscan reached")
        system_state = sys_state.get_status()
        self.baselineoffset = system_state["baselineoffset"]
        #check if annotation path exists and create if not
        if os.path.exists(self.cohiradia_yamlheader_filename) == False:         #exist yaml file: create from yaml-editor
            self.cohiradia_yamlheader_dirname = self.my_dirname + '/' + self.annotationdir_prefix + self.my_filename
            if os.path.exists(self.cohiradia_yamlheader_dirname) == False:
                os.mkdir(self.cohiradia_yamlheader_dirname)

        self.autoscanthread = QThread()
        self.autoscaninst = autoscan_worker(self)
        self.autoscaninst.moveToThread(self.autoscanthread)
        #TODO: Implement further slot communicationa shown here
        self.autoscaninst.set_0([self.ui.spinBoxNumScan.value(),self.ui.spinBoxminSNR.value(),[]])
        #TODO: Check if here appropriate FFFFFFFFFFFFFFFFFFFFFFFFFFF
        autoscan_statuspars = {}
        autoscan_statuspars["progressvalue"] = self.progressvalue 
        autoscan_statuspars["horzscal"] = system_state["horzscal"]
            # __slots__[2] has entries: self.host.progressvalue, 
        self.autoscaninst.set_2(autoscan_statuspars)

        #self.PROMINENCE = self.host.ui.spinBoxminSNR.value()

        self.autoscanthread.started.connect(self.autoscaninst.autoscan_fun)
        self.autoscaninst.SigFinished.connect(self.autoscan_finished)
        self.autoscaninst.SigFinished.connect(self.ann_stations)
        self.autoscaninst.SigFinished.connect(self.autoscanthread.quit)
        self.autoscaninst.SigFinished.connect(self.autoscanthread.deleteLater)
        #self.timertick.SigFinished.connect(self.timertick.deleteLater)
        self.autoscaninst.SigProgressBar.connect(self.Progressbarupdate)
        self.autoscaninst.SigPlotdata.connect(self.scanplot)
        self.autoscaninst.SigScandeactivate.connect(self.scan_deactivate)
        self.autoscaninst.SigUpdateGUI.connect(self.scanupdateGUI)
        self.autoscaninst.SigStatustable.connect(self.status_writetableread)
        self.autoscanthread.start()
        if self.autoscanthread.isRunning():
            self.autoscanthreadActive = True
        sys_state.set_status(system_state)

    #@njit
    def ann_stations(self): #TODO: shift to annotation module, this is a controller method
        """
        CONTROLLER
        read MWLIST and collect stations info in dictionary, initialize yamlheader, starts statlst_gen_worker for stationslist generation, 
            finally calls interactive_station_select()
            depends on: statlst_gen_worker, Progressbarupdate(), csan_completed(), write_yaml_header(), interactive_station_select(), annotation_completed()
        :param : none
        :type : none
        :raises [ErrorType]: [ErrorDescription]
        :return: flag False on unsuccessful execution if stations list or status file non-existent
        :rtype: Boolean
        """
        system_state = sys_state.get_status()

        self.stations_filename = self.annotationpath + '/stations_list.yaml'
        if os.path.exists(self.stations_filename) == False:

            # read Annotation_basis table from mwlist.org
            self.ui.label.setText("Status: read MWList table for annotation")
            #TODO: make list selectable
            filters ="MWList files (*.xlsx)"
            selected_filter = "MWList files (*.xlsx)"
            filename=""
            if self.ismetadata == False:
                filename =  QtWidgets.QFileDialog.getOpenFileName(self,
                                                                    "Open new stations list (e.g. MWList) file"
                                                                    , self.standardpath, filters, selected_filter)
            else:
                #print('open file with last path')
                if "last_MWlist" in self.metadata:
                    filters =  "MWList files (*.xlsx)"
                    selected_filter = filters
                    filename =  QtWidgets.QFileDialog.getOpenFileName(self,
                                                                    "Open stations list (e.g. MWList) file (last used is selected)"
                                                                    ,self.metadata["last_MWlist"] , filters, selected_filter)
                else:
                    filename =  QtWidgets.QFileDialog.getOpenFileName(self,
                                                    "Open new stations list (e.g. MWList) file"
                                                    , self.standardpath, filters, selected_filter)
            if len(filename[0]) == 0:
                return False
            list_selection = filename[0]   
            self.metadata["last_MWlist"] = list_selection

            stream = open("config_wizard.yaml", "w")
            yaml.dump(self.metadata, stream)
            stream.close()

            #MWlistname = self.standardpath + '\\MWLIST_Volltabelle.xlsx' ###TODO remove if checked
            MWlistname = list_selection

            #print('read MWLIST table from ' + MWlistname)
            time.sleep(0.01)
            T = pd.read_excel(MWlistname)
            #print("generate annotation basis")
            self.ui.label.setText("Status: Generate annotation basis")

            freq = [] # column with all tabulated frequencies in MWtabelle
            closed = [] # column with dates of corresponding closure times if available (if element in table is type datetime)
            for ix in range(len(T)):
                testclosed = T.closed.iloc[ix]
                dummytime = datetime(5000,1,1,1,1,1)
                if type(testclosed) == datetime:
                    closed.append(datetime.strptime(str(testclosed), '%Y-%m-%d %H:%M:%S'))
                    #stations which are not closed must have dummy entries where no datetime
                else:
                    closed.append(datetime.strptime(str(dummytime), '%Y-%m-%d %H:%M:%S'))
                freq.append(float(T.freq.iloc[ix]))
            self.ui.label.setText("Status: annotate peaks and write stations list to yaml file")

            #self.write_yaml_header()            #write header part of the cohiradia yaml

            #start generation of stations list as a separate thread
            starttime = self.wavheader['starttime']
            stoptime = self.wavheader['stoptime']
            self.rectime = datetime(starttime[0],starttime[1],starttime[3],starttime[4],starttime[5],starttime[6])
            self.recstop = datetime(stoptime[0],stoptime[1],stoptime[3],stoptime[4],stoptime[5],stoptime[6]) #TODO: seems to be unused

            self.statlst_genthread = QThread()
            self.statlst_geninst = statlst_gen_worker(self)
            self.statlst_geninst.moveToThread(self.statlst_genthread)
            self.statlst_geninst.set_status_position(0)
            self.statlst_geninst.set_T(T)
            self.statlst_geninst.set_freq(freq)
            self.statlst_geninst.set_closed(closed)
            self.statlst_genthread.started.connect(self.statlst_geninst.stationsloop)
            self.statlst_geninst.SigFinished.connect(self.scan_completed)
            self.statlst_geninst.SigFinished.connect(self.statlst_genthread.quit)
            self.statlst_geninst.SigFinished.connect(self.statlst_genthread.deleteLater)
            self.statlst_geninst.SigProgressBar1.connect(self.Progressbarupdate)
            self.statlst_genthread.start()
            if self.statlst_genthread.isRunning():
                self.statlst_genthreadActive = True

        else:
            self.scan_completed()
            try:
                stream = open(self.status_filename, "r")
                status = yaml.safe_load(stream)
                stream.close()
            except:
                #print("cannot get status")
                return False 
            
            if status["annotated"] == True:
                self.annotation_completed()
            else:
                freq_ix = status["freqindex"]
                try:
                    stream = open(self.stations_filename, "r", encoding="utf8")
                    self.stations = yaml.safe_load(stream)
                    stream.close()
                except:
                    #print("cannot get stations list")
                    return False
                self.ui.labelFrequency.setText('Frequency: ' + str(self.stations[freq_ix]['frequency'] + ' kHz'))
                #self.ui.lineEdit.setText('Frequency: ' + str(self.stations[freq_ix]['frequency'] + ' kHz'))
                self.ui.lineEdit.setFont(QFont('MS Shell Dlg 2', 12))
                self.ui.lineEdit.setText('')
                self.ui.lineEdit_TX_Site.setText('')
                self.ui.lineEdit_Country.setText('')
                self.ui.lineEdit.setStyleSheet("background-color : white")
                self.ui.lineEdit.setFont(QFont('MS Shell Dlg 2', 12))
            self.ui.pushButtonENTER.setEnabled(False)
            self.interactive_station_select()

    #@njit
    def interactive_station_select(self):  #TODO: move to annotation module
        """
        CONTROLLER
        read yaml stations_list.yaml

        """
        self.ui.Annotate_listWidget.clear()
        self.ui.lineEdit.setText('')
        self.ui.lineEdit_TX_Site.setText('')
        self.ui.lineEdit_Country.setText('')
        ### reading again the yaml is inefficient: could be passed from ann_stations
        try:
            stream = open(self.status_filename, "r")
            status = yaml.safe_load(stream)
            stream.close()
        except:
            #print("cannot get status")
            return False 
        try:
            stream = open(self.stations_filename, "r", encoding="utf8")
            self.stations = yaml.safe_load(stream)
            stream.close()
        except:
            #print("cannot get stations list")
            return False
        
        freq_ix = status["freqindex"] # read last frequency index which was treated in interactive list checking
        if freq_ix >= len(self.stations):
            self.annotation_completed()
            status["annotated"] = True
            stream = open(self.status_filename, "w")
            yaml.dump(status, stream)
            stream.close()
            return False
        plen = int((len(self.stations[freq_ix])-2)/3) #number of station candidates
        self.ui.labelFrequency.setText('f: ' + str(self.stations[freq_ix]['frequency'] + ' kHz'))
        self.ui.progressBar_2.setProperty("value", freq_ix/len(self.stations)*100)
        #self.ui.lineEdit.setText('Frequency: ' + str(self.stations[freq_ix]['frequency'] + ' kHz'))
        time.sleep(0.01)
        
        for ix2 in range(plen):
            country_string = self.stations[freq_ix]['country' + str(ix2)]
            programme_string = self.stations[freq_ix]['programme' + str(ix2)]
            tx_site_string = self.stations[freq_ix]['tx-site' + str(ix2)]
            item = QtWidgets.QListWidgetItem()
            self.ui.Annotate_listWidget.addItem(item)
            item = self.ui.Annotate_listWidget.item(ix2)
            item.setText(country_string.strip('\n') + ' | ' + programme_string.strip('\n') + ' | ' + tx_site_string.strip('\n'))
            time.sleep(0.01)
        #add dummy line in list for selecting own entry
        # item = QtWidgets.QListWidgetItem()
        # self.ui.Annotate_listWidget.addItem(item)
        # item = self.ui.Annotate_listWidget.item(ix2+1)
        # dum_cstr = 'OTHER COUNTRY, Please enter manually'
        # dum_pstr = 'OTHER STATION, Please enter manually'
        # dum_txstr = 'OTHER TX SITE, Please enter manually'
        # item.setText(dum_cstr.strip('\n') + ' | ' + dum_pstr.strip('\n') + ' | ' + dum_txstr.strip('\n'))
        # time.sleep(0.01)
        self.ui.pushButtonDiscard.setEnabled(True)


    def cb_ListClicked(self,item):
        """
        CONTROLLER
        read yaml stations_list.yaml

        """
        #memorize status and advance freq_ix
        try:
            stream = open(self.status_filename, "r")
            status = yaml.safe_load(stream)
            stream.close()
        except:
            #print("cannot get status")
            return False 
        freq_ix = status["freqindex"] # read last frequency index which was treated in interactive list checking
        if freq_ix < len(self.stations):
            #read index of clicked row and fetch associated content from stations list
            cr_ix = self.ui.Annotate_listWidget.currentRow()
            Ecountry_string = self.stations[freq_ix]['country' + str(cr_ix)]
            Eprogramme_string = self.stations[freq_ix]['programme' + str(cr_ix)]
            Etx_site_string = self.stations[freq_ix]['tx-site' + str(cr_ix)]
            self.ui.labelFrequency.setText('f: ' + str(self.stations[freq_ix]['frequency']) + ' kHz')

            self.ui.lineEdit.setText(Eprogramme_string)
            self.ui.lineEdit.setAlignment(QtCore.Qt.AlignLeft)
            self.ui.lineEdit.home(True)
            self.ui.lineEdit_TX_Site.setText(Etx_site_string)
            self.ui.lineEdit_TX_Site.setAlignment(QtCore.Qt.AlignLeft)
            self.ui.lineEdit_TX_Site.home(True)
            self.ui.lineEdit_Country.setText(Ecountry_string)
            self.ui.lineEdit_Country.setAlignment(QtCore.Qt.AlignLeft)
            self.ui.lineEdit_Country.home(True)
            self.current_freq_ix = freq_ix

        # end of stationslist reached
            self.ui.pushButtonENTER.setEnabled(True)
        else:
            status["freqindex"] = freq_ix
            status["annotated"] = True
            stream = open(self.status_filename, "w")
            yaml.dump(status, stream)
            stream.close()
            self.ui.progressBar_2.setProperty("value", 100)
            self.annotation_completed()

    def enterlinetoannotation(self):
        """
        CONTROLLER
        read yaml stations_list.yaml

        """
        #self.ui.lineEdit.setEnabled(False)
        #print('Editline copy to metadata file')
        self.ui.pushButtonENTER.setEnabled(False)
        try:
            stream = open(self.status_filename, "r")
            status = yaml.safe_load(stream)
            stream.close()
        except:
            #print("cannot get status")
            return False
        
        freq_ix = status["freqindex"]
        programstr = self.ui.lineEdit.text()
        txstr = self.ui.lineEdit_TX_Site.text()
        countrystr = self.ui.lineEdit_Country.text()

        country_string = '  country: "{}"\n'.format(countrystr)
        programme_string = '  programme: "{}"\n'.format(programstr)
        tx_site_string = '  tx-site: "{}"\n'.format(txstr)
        freq_ix = self.current_freq_ix
        with open(self.cohiradia_metadata_filename, 'a+', encoding='utf-8') as f:
            f.write('- frequency: "{}"\n'.format(self.stations[freq_ix]['frequency']))
            f.write('  snr: "{}"\n'.format(self.stations[freq_ix]['snr']))
            f.write(country_string)
            f.write(programme_string)
            f.write(tx_site_string)
        freq_ix += 1
        status["freqindex"] = freq_ix
        status["annotated"] = False
        stream = open(self.status_filename, "w")
        yaml.dump(status, stream)
        stream.close()
        self.ui.progressBar_2.setProperty("value", (freq_ix + 1)/len(self.stations)*100)
        self.ui.Annotate_listWidget.clear()
        self.interactive_station_select()

    def discard_annot_line(self):
        """
        CONTROLLER
        read yaml stations_list.yaml

        """
        try:
            stream = open(self.status_filename, "r")
            status = yaml.safe_load(stream)
            stream.close()
        except:
            return False 
        freq_ix = status["freqindex"] # read last frequency index which was treated in interactive list checking
        #Discard this frequency, advance freq counter, do not write to cohiradia annotation
        freq_ix += 1
        status["freqindex"] = freq_ix
        status["annotated"] = False
        stream = open(self.status_filename, "w")
        yaml.dump(status, stream)
        stream.close()
        self.interactive_station_select()
        self.ui.progressBar_2.setProperty("value", (freq_ix + 1)/len(self.stations)*100)
        return False

############################## END TAB ANNOTATE ####################################

############################## GENERAL MENU FUNCTIONS  ####################################

    def cb_open_file(self):
        """
        VIEW
        check conditions for proper opening of a new data file; if all conditions met:
        call FileOpen() for getting the file handling parameters
        conditions: playthread is not currently active

        returns: True if successful, False if condition not met.        
        """
        system_state = sys_state.get_status()
        #self.SigRelay.emit("cm_playrec",["cbopenfile",self.m["baselineoffset"]])
        #self.activate_tabs(["View_Spectra","Annotate","Player","YAML_editor","WAV_header","Resample"])
        self.setactivity_tabs("all","activate",[])
        self.SigRelay.emit("cm_playrec",["sdr_configparams",system_state["sdr_configparams"]])

        #resample_c.SigUpdateGUI.connect(self.GUI_reset_after_resamp) ###TODO: check, seems not to be active any more
        self.ui.checkBox_merge_selectall.setChecked(False)
        if self.playthreadActive == True:
            auxi.standard_errorbox("Player is currently active, no access to data file is possible; Please stop Player before new file access")
            sys_state.set_status(system_state)
            return False
        #self.open_template_flag = False
        try:
            stream = open("config_wizard.yaml", "r")
            self.metadata = yaml.safe_load(stream)
            stream.close()
            self.ismetadata = True
        except:
            self.ismetadata = False
            sys_state.set_status(system_state)
            #return False
            #print("cannot get metadata")
        system_state["HostAddress"] = self.ui.lineEdit_IPAddress.text()   ### TODO TODO TODO check if still necesary after transfer to modules playrec and config
        configparams = {"ifreq":system_state["ifreq"], "irate":system_state["irate"],
                            "rates": system_state["rates"], "icorr":system_state["icorr"],
                            "HostAddress":system_state["HostAddress"], "LO_offset":system_state["LO_offset"]}
        system_state["sdr_configparams"] = configparams

        self.ui.spinBoxminSNR_ScannerTab.setProperty("value", self.PROMINENCE)
        
        if system_state["fileopened"] is True:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Question)
            msg.setText("open new file")
            msg.setInformativeText("you are about o open another file. Current file will be closed; Do you want to proceed")
            msg.setWindowTitle("FILE OPEN")
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msg.buttonClicked.connect(self.popup)
            msg.exec_()

            if self.yesno == "&Yes":
                if self.FileOpen() is False:
                    self.SigRelay.emit("cm_all_",["fileopened", False])
                    return False

        else:
            if self.FileOpen() is False:
                system_state["fileopened"] = False #CHECK: obsolete, because self.SigRelay.emit("cm_all_",["fileopened",False]) does the job
                self.SigRelay.emit("cm_all_",["fileopened",False])
                #self.SigRelay.emit("cexex_view_spectra",["updateGUIelements",0])
                sys_state.set_status(system_state)
                return False
            else:
                system_state["fileopened"] = True #CHECK: obsolete, because self.SigRelay.emit("cm_all_",["fileopened",False]) does the job
                self.SigRelay.emit("cm_all_",["fileopened",True])
                #self.SigRelay.emit("cexex_view_spectra",["updateGUIelements",0])
        sys_state.set_status(system_state)

        
        #TODO: check change 12-01-2024: temporary path is set differently
        temppath = system_state["temp_directory"]
        for x in os.listdir(temppath):
            if x.find("temp_") == 0:
                try:
                    os.remove(x)
                except:
                    self.logger.debug("res_scheduler terminate: file access to temp file refused")

    ############################## END TAB GENERAL MENUFUNCTIONS ####################################

  

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
        system_state = sys_state.get_status()
        errorf = False
        #check: has been done on 13-12-2023 TODO: replace ifreq by system_state["ifreq"]
        if system_state["ifreq"] < 0 or system_state["ifreq"] > 62500000:
            errorf = True
            errortxt = "center frequency not in range (0 - 62500000) \
                      after _lo\n Probably not a COHIRADIA File"

        if system_state["irate"] not in system_state["rates"]:
            errorf = True
            errortxt = "The sample rate of this file is inappropriate for the STEMLAB!\n\
            Probably it is not a COHIRADIA File. \n \n \
            PLEASE USE THE 'Resample' TAB TO CREATE A PLAYABLE FILE ! \n\n \
            SR must be in the set: 20000, 50000, 100000, 250000, 500000, 1250000, 2500000"
            
        if system_state["icorr"] < -100 or system_state["icorr"] > 100:
            errorf = True
            errortxt = "frequency correction min ppm must be in \
                      the interval (-100 - 100) after _c \n \
                      Probably not a COHIRADIA File "

        if errorf:
            auxi.standard_errorbox(errortxt)
            
            return False
        else:
            return True


    def popup(self,i):
        """
        VIEW or CONTROLLER ??
        
        """
        self.yesno = i.text()

    def setstandardpaths(self):  #TODO: shift to general system module ?
        """
        CONTROLLER
        
        """
        #TODO TODO TODO: check if the selfs must be selfs !
        self.annotationpath = self.my_dirname + '/' + self.annotationdir_prefix + self.my_filename
        self.stations_filename = self.annotationpath + '/stations_list.yaml'
        self.status_filename = self.annotationpath + '/status.yaml'
        self.annotation_filename = self.annotationpath + '/snrannotation.yaml'
        self.cohiradia_metadata_filename = self.annotationpath + '/cohiradia_metadata.yaml'
        self.cohiradia_yamlheader_filename = self.annotationpath + '/cohiradia_metadata_header.yaml'
        self.cohiradia_yamltailer_filename = self.annotationpath + '/cohiradia_metadata_tailer.yaml'
        self.cohiradia_yamlfinal_filename = self.annotationpath + '/COHI_YAML_FINAL.yaml'
        self.SigRelay.emit("cm_yamleditor",["cohiradia_yamlheader_filename",self.cohiradia_yamlheader_filename])
        self.SigRelay.emit("cm_yamleditor",["cohiradia_yamltailer_filename",self.cohiradia_yamltailer_filename])
        self.SigRelay.emit("cm_yamleditor",["cohiradia_yamlfinal_filename",self.cohiradia_yamlfinal_filename])
        self.SigRelay.emit("cm_yamleditor",["cohiradia_metadata_filename",self.cohiradia_metadata_filename])
            #self.SigRelay.emit("cexex_view_spectra",["updateGUIelements",0])

            ############################ CURRENT STATE RELAY, CONTINUE FROM HERE

    def resread_playlist(self): #TODO: not yet used
        """
        VIEW ?
        
        """    
        playlist = []
        self.ui.listWidget_playlist.clear()
        self.ui.listWidget_sourcelist.clear()
        #preset playlist
        ix = 0
        for x in os.listdir(self.my_dirname):
            if x.endswith(".wav"):
                if x != (self.my_filename + self.ext):
                    playlist.append(x) 
                    _item1=self.ui.listWidget_sourcelist.item(ix)
                    _item1.setText(x)
                    fnt = _item1.font()
                    fnt.setPointSize(9)
                    #_item2.setFont(fnt)
                    item = QtWidgets.QListWidgetItem()
                    self.ui.listWidget_sourcelist.addItem(item)
                    ix += 1
                else:
                    self.logger.debug("resread_playlist: automat remove from selectlist: %s", self.my_filename + self.ext)
        #TODO: erzeuge einen Einag in Playlist    listWidget_playlist

    #@njit
    def FileOpen(self):   #TODO: shift to general system module ?
        '''
        CONTROLLER
        Purpose: 
        If self.####### == True:
            (1) Open data file for read
            (2) call routine for extraction of recording parameters from filename
            (3) present recording parameters in info fields
        Returns: True, if successful, False otherwise
        '''
        #TODO: shift action to respective tab machine by: currix = self.ui.tabWidget.currentIndex() self.ui.tabWidget.tabText(currix)
        system_state = sys_state.get_status()
        self.SigGUIReset.emit()
        #TODO: replace by RELAY; call this signal only if resample_c is instantiated !
        resample_c.SigResampGUIReset.emit()
        #resample_c.SigTerminate_Finished.connect(self.cb_resample_new)
        self.ui.pushButton_resample_split2G.clicked.connect(resample_v.cb_split2G_Button)
        #TODO:  replace by RELAY; call this function only if resample_v is instantiated !
        resample_v.enable_resamp_GUI_elemets(True)

        filters = "SDR wav files (*.wav);;Raw IQ (*.dat *.raw )"
        selected_filter = "SDR wav files (*.wav)"
        if True: #TODO: remove after TESTS change 17-12-2023
            if self.ismetadata == False:
                filename =  QtWidgets.QFileDialog.getOpenFileName(self,
                                                                "Open data file"
                                                                , self.standardpath, filters, selected_filter)
            else:
                filename =  QtWidgets.QFileDialog.getOpenFileName(self,
                                                                "Open data file"
                                                                ,self.metadata["last_path"] , filters, selected_filter)
            system_state["f1"] = filename[0] #TODO: replace by line below:
            self.SigRelay.emit("cm_all_",["f1", filename[0]])
        else:
            pass
        
        if not system_state["f1"]:
            sys_state.set_status(system_state)
            return False
        self.logger.info(f'File opened: {system_state["f1"]}')
        file_stats = os.stat(system_state["f1"])
        ti_m = os.path.getmtime(system_state["f1"]) 
        # Converting the time in seconds to a timestamp
        self.file_mod = datetime.fromtimestamp(ti_m)
        system_state["sfilesize"] = file_stats.st_size
        self.my_dirname = os.path.dirname(system_state["f1"])
        #TODO TODO TODO: replace self.my_filename and self.ext by resp system state entries
        self.my_filename, self.ext = os.path.splitext(os.path.basename(system_state["f1"]))
        system_state["ext"] = self.ext
        system_state["my_filename"] = self.my_filename
        
        self.SigRelay.emit("cm_all_",["my_dirname", self.my_dirname])
        self.SigRelay.emit("cm_all_",["ext",self.ext])
        self.SigRelay.emit("cm_all_",["my_filename",self.my_filename])

        system_state["temp_directory"] = self.my_dirname + "/temp"
        self.SigRelay.emit("cm_all_",["temp_directory",self.my_dirname + "/temp"])

        if os.path.exists(system_state["temp_directory"]) == False:         #exist yaml file: create from yaml-editor
            os.mkdir( system_state["temp_directory"])

        if self.ext == ".dat" or self.ext == ".raw":
            self.filetype = "dat"
            ## TODO: wavheader-Writing zum Button Insert Header connecten
            self.ui.label_8.setEnabled(True)
            self.ui.pushButton_InsertHeader.setEnabled(True)   #####TODO shift to WAV editor or send Relay for inactivation via WAV 
        else:
            if self.ext == ".wav":
                self.filetype = "wav"
                self.ui.tab_view_spectra.setEnabled(True)  ##########TODO: replace by Tab disable function inactivate/activate_tabs(self,selection)
                self.ui.tab_annotate.setEnabled(True)  ##########TODO: replace by Tab disable function inactivate/activate_tabs(self,selection)
                self.ui.label_8.setEnabled(False)
                self.ui.pushButton_InsertHeader.setEnabled(False)                 #####TODO shift to WAV editor or send Relay for inactivation via WAV 
            else:
                auxi.standard_errorbox("no valid data forma, neiter wav, nor dat nor raw !")
                sys_state.set_status(system_state)
                return

        if self.filetype == "dat": # namecheck only if dat --> makes void all wav-related operation sin filenameextract
            if self.dat_extractinfo4wavheader() == False:
                auxi.standard_errorbox("Unexpected error, dat_extractinfo4wavheader() == False; ")
                sys_state.set_status(system_state)
                return False
                #TODO: dat_extractinfo4wavheader() automatically asks for lacking wav header info, so this exit could be replaced alrady !
        else:
            self.wavheader = WAVheader_tools.get_sdruno_header(self,system_state["f1"])
            if self.wavheader != False:
                #self.next_filename = self.extract_startstoptimes_auxi(self.wavheader)
                self.next_filename = waveditor_c.extract_startstoptimes_auxi(self.wavheader)
            else:
                auxi.standard_errorbox("File is not recognized as a valid IQ wav file (not auxi/rcvr compatible or not a RIFF file)")
                sys_state.set_status(system_state)
                return False

        if self.wavheader['sdrtype_chckID'].find('auxi') > -1 or self.wavheader['sdrtype_chckID'].find('rcvr') > -1: #TODO: CHECK: is this obsolete because of the above quest ?
            pass
        else:
            auxi.standard_errorbox("cannot process wav header, does not contain auxi or rcvr ID")
            self.sdrtype = 'FALSE'
            sys_state.set_status(system_state)
            return False
        self.SigRelay.emit("cm_waveditor",["filetype",self.filetype])
        #TODO: mache das konfigurierbar:
        self.ui.lineEdit_resample_targetnameprefix.setText(self.my_filename)
        self.setstandardpaths()
        self.SigRelay.emit("cm_all_",["wavheader",self.wavheader])
        self.showfilename()
        #self.SigRelay.emit("cexex_all_",["updateGUIelements", 0])
        self.annotation_deactivate()
        self.scan_deactivate()
        self.ui.pushButtonDiscard.setEnabled(False)

################TODO:  method initialize listitems, decompose to player and resampler items and encapsulate in the respective tab classes
        playlist = []
        #TODO: look if this is the right place or maybe gui_reset
        #clear playlist
        self.ui.listWidget_playlist.clear()
        self.ui.listWidget_sourcelist_2.clear()
        self.ui.listWidget_sourcelist.clear()
        self.ui.listWidget_playlist_2.clear()
        item = QtWidgets.QListWidgetItem()
        self.ui.listWidget_sourcelist_2.addItem(item)
        item = QtWidgets.QListWidgetItem()
        self.ui.listWidget_sourcelist.addItem(item)
        #preset playlist

        reslist = []
        resfilelist = [] #TODO: obsolete ?
        ix = 0
        for x in os.listdir(self.my_dirname):
            if x.endswith(".wav"):
                if True: #x != (self.my_filename + self.ext): #TODO: obsolete old form when automatically loading opened file to playlist
                    resfilelist.append(x) 
                    _item1=self.ui.listWidget_sourcelist_2.item(ix)
                    _item1.setText(x)
                    fnt = _item1.font()
                    fnt.setPointSize(7)
                    #_item1.setFont(fnt)
                    item = QtWidgets.QListWidgetItem()
                    self.ui.listWidget_sourcelist_2.addItem(item)
                    _item2=self.ui.listWidget_sourcelist.item(ix)
                    _item2.setText(x)
                    fnt = _item2.font()
                    fnt.setPointSize(7)
                    #_item2.setFont(fnt)
                    item = QtWidgets.QListWidgetItem()
                    self.ui.listWidget_sourcelist.addItem(item)
                    ix += 1

        #TODO: erzeuge einen Eintrag in Playlist listWidget_playlist
        if system_state["f1"].endswith(".wav"):
            item = QtWidgets.QListWidgetItem()
            self.ui.listWidget_playlist.addItem(item)
            _item1=self.ui.listWidget_playlist.item(0)
            _item1.setText(self.my_filename + self.ext)
            fnt = _item1.font()
            fnt.setPointSize(9)
            playlist.append(system_state["f1"])
            system_state["playlist"] = playlist

            item = QtWidgets.QListWidgetItem()
            self.ui.listWidget_playlist_2.addItem(item)
            _item2=self.ui.listWidget_playlist_2.item(0)
            #TODO: problematic when invalid wav file (music)
            _item2.setText(self.my_filename + self.ext)
            fnt = _item2.font()
            fnt.setPointSize(9)
            reslist.append(system_state["f1"])
            system_state["reslist"] = reslist


        self.ui.listWidget_playlist.setEnabled(False)
        self.ui.listWidget_sourcelist_2.setEnabled(False)
        self.ui.listWidget_sourcelist.setEnabled(False)
        self.ui.listWidget_playlist_2.setEnabled(False)

        #self.ui.listWidget_playlist_2.model().rowsInserted.connect(resample_v.reslist_update) #TODO transfer to resemplar view
        #self.ui.listWidget_playlist_2.model().rowsRemoved.connect(resample_v.reslist_update) #TODO transfer to resemplar view
        #self.ui.listWidget_playlist_2.itemChanged.connect(resample_v.reslist_update) #TODO transfer to resemplar view
        #self.ui.listWidget_playlist_2.itemClicked.connect(resample_v.reslist_itemselected) #TODO transfer to resemplar view
        
################TODO: end method initialize listitems
        
        if self.wavheader['sdrtype_chckID'].find('rcvr') > -1:
            self.readoffset = 86
        else:
            self.readoffset = 216

        system_state["ifreq"] = self.wavheader['centerfreq'] + system_state["LO_offset"] #ONLY used in player, so shift
        system_state["irate"] = self.wavheader['nSamplesPerSec'] #ONLY used in palyer, so shift
        system_state["readoffset"] = self.readoffset   
        self.SigRelay.emit("cm_resample",["readoffset",system_state["readoffset"]])
        #self.SigRelay.emit("cm_resample",["readoffset",system_state["readoffset"]])
        #self.fill_wavtable()

        #generate STM_cont_params for future passage to player_theradworkers instead of push pop strategy
        #self.STM_cont_params = {"HostAddress": system_state["HostAddress"], "ifreq": system_state["ifreq"],"rates": system_state["rates"], "irate": system_state["irate"], "icorr": system_state["icorr"]}
        # TODO: rootpath for config file ! 
        # TODO: append metadata instead of new write
        self.metadata["last_path"] = self.my_dirname
        self.metadata["STM_IP_address"] = system_state["HostAddress"]
        stream = open("config_wizard.yaml", "w")
        yaml.dump(self.metadata, stream)
        stream.close()

        system_state["timescaler"] = self.wavheader['nSamplesPerSec']*self.wavheader['nBlockAlign']
        self.stations_filename = self.annotationpath + '/stations_list.yaml'
        if os.path.exists(self.stations_filename) == True:
            self.scan_completed()
            try:
                stream = open(self.status_filename, "r")
                status = yaml.safe_load(stream)
                stream.close()
            except:
                #print("cannot get status")
                sys_state.set_status(system_state)
                return False 
            if status["annotated"] == True:
                self.annotation_completed()
            else:
                self.annotation_activate()
        else:
            self.scan_activate()
        system_state["fileopened"] = True
        self.SigRelay.emit("cm_all_",["fileopened",True])

        self.ui.spinBoxKernelwidth.setEnabled(True)
        self.ui.label_6.setText("Baseline Offset:" + str(self.ui.spinBoxminBaselineoffset.value()))
        self.position = self.ui.horizontalScrollBar_view_spectra.value()
        self.lock_playthreadstart = True
        
        system_state = sys_state.get_status()#TODO: check: obsolete ! because of Relay !
        system_state["horzscal"] = self.position #TODO: check: obsolete ! because of Relay !
        self.SigRelay.emit("cm_all_",["horzscal", self.position])
        self.SigRelay.emit("cm_view_spectra",["position",self.position])

        #self.SigRelay.emit("cexex_all_",["updateGUIelements", 0]) 
        #TODO TODO TODO: track multiple calls of plot_spectrum
        self.lock_playthreadstart = False
        #TODO: is that really necessary on each fileopen ? 
        #self.read_yaml_header(self)
        resample_v.update_resample_GUI()
        # TODO: check, added 09-12-2023
        system_state["playlength"] = self.wavheader['filesize']/self.wavheader['nAvgBytesPerSec']
        system_state["list_out_files_resampled"] = []
        #resp = self.sync_tabs(["resample","win","u","list_out_files_resampled",system_state["list_out_files_resampled"]])
        self.SigRelay.emit("cm_resample",["list_out_files_resampled",system_state["list_out_files_resampled"]])
        
        out_dirname = self.my_dirname + '/out'
        if os.path.exists(out_dirname) == False:         #exist yaml file: create from yaml-editor
            os.mkdir(out_dirname)
        self.SigRelay.emit("cm_all_",["out_dirname",out_dirname])
        sys_state.set_status(system_state)
        return True

    def dat_extractinfo4wavheader(self):
        #TODO: erkennt COHIRADIA Namenskonvention nicht, wenn vor den _lo_r_c literalen noch andere _# Felder existieren.  shift to controller module
        """ 
        CONTROLLER
        extract control parameters from dat and raw files if existent (COHIRADIA nameconvention)
        and generates standard wavheader
        check for consistency with COHIRADIA file name convention
        if no wav information present: generate dummy entries for most wavheaderitems and ask for SR and LO

        :param [ParamName]: none
        :type [ParamName]: none
        :raises Filename error 1: center frequency offset not integer
        :raises Filename error 2: filename convention not met, cannot extractplayback/resording parameters
        :raises Filename error 3: center frequency not in range (0 - 62500000)
        :raises Filename error 4: sampling rate not in set 20000, 50000, 100000, 250000, 500000, 1250000, 2500000
        :raises Filename error 5: center frequency offset out of range +/- 100 ppm
        :raises warning 1: LO frequency not identifiable in wav-filename, default value 1250 kS/s is used
        :return: Returns: True, if successful, False otherwise (if error exception raised)
        :rtype: Boolean
        """
        system_state = sys_state.get_status()
        loix = self.my_filename.find('_lo')
        cix = self.my_filename.find('_c')
        rateix = self.my_filename.find('_r')
        icheck = True
        i_LO_bias = 0 ###TODO: remove, activate ???

        # #TODO: ACTIVATE LObias check code
        # if self.ui.radioButton_LO_bias.isChecked() is True:
        #     if (self.ui.lineEdit_LO_bias.text()).isnumeric() == False:
        #         auxi.standard_errorbox("invalid numeral in center frequency offset field, please enter valid integer value (kHz)")
        #         return False

        #     LObiasraw = self.ui.lineEdit_LO_bias.text()
        #     LObias_sign = 1

        #     if LObiasraw[0] == "-":
        #         LObias_sign = -1
        #     if LObiasraw.lstrip("-").isnumeric() is True:
        #         i_LO_bias = LObias_sign*int(LObiasraw.lstrip("-"))
        #     else:
        #         auxi.standard_errorbox("invalid numeral in center frequency offset field, please enter valid integer value (kHz)")
        #         return False

        if rateix == -1 or cix == -1 or loix == -1:
            icheck = False
        
        freq = self.my_filename[loix+3:loix+7]
        freq = freq + '000'
        if freq.isdecimal() == False:
            icheck = False

        rate = self.my_filename[rateix+2:cix]
        rate = rate + '000'
        if rate.isdecimal() == False:
            icheck = False            
        system_state["icorr"] = int(0)
        bps = 16
        #generate standard wavheader

        if icheck == False:
            freq, done0 = QtWidgets.QInputDialog.getInt(
                    self, 'Input Dialog', 'Enter center frequency:', self.standardLO)
            rate_index = 1 #TODO: make system constant
            rate, done1 = QtWidgets.QInputDialog.getItem(
                    self, 'Input Dialog', 'Bandwidth', system_state["irates"], rate_index)
            bps, done2 = QtWidgets.QInputDialog.getItem(
                    self, 'Input Dialog', 'bits per sample', self.bps, 1)

            #TODO: validity check for freq, maybe warning if rate cancelled and no valid value, check done0, done1
            system_state["irate"] = 1000*int(rate)
            system_state["ifreq"] = int(1000*(int(freq) + system_state["LO_offset"]))
        else:
            system_state["irate"] = int(rate)
            system_state["ifreq"] = int(int(freq) + system_state["LO_offset"])  # TODO: LO_bias dazuzählrn system_state["LO_offset"]
        #TODO: ACTIVATE wav header generator
        self.wavheader = WAVheader_tools.basic_wavheader(self,system_state["icorr"],int(system_state["irate"]),int(system_state["ifreq"]),int(bps),system_state["sfilesize"],self.file_mod)
        sys_state.set_status(system_state)
        return True

    def generate_GUIupdaterlist(self,item):
        self.GUIupdaterlist.append(item)

    def sendupdateGUIs(self):
        """  goes through the list of all registered Tabs and calls their GUI-Updatemethod
        :param : none
        :type : none
        :raises [ErrorType]: none
        :return: none
        :rtype: none
        """        
        for item in self.GUIupdaterlist:
            item()

    def rxhandler(self,_key,_value):
        """
        handles remote calls from other modules via Signal SigRX(_key,_value)
        :param : _key
        :type : str
        :param : _value
        :type : object
        :raises [ErrorType]: [ErrorDescription]
        :return: flag False or True, False on unsuccessful execution
        :rtype: Boolean
        """
        system_state = sys_state.get_status()
        if _key.find("cm_core") == 0 or _key.find("cm_all_") == 0:
            #set mdl-value
            system_state[_value[0]] = _value[1] 
            #self.m[_value[0]] = _value[1]
        if _key.find("cui_core") == 0:
            _value[0](_value[1])    #TODO TODO: still unclear implementation
        if _key.find("cexex_core") == 0:
            if  _value[0].find("GUIreset") == 0:
                self.SigGUIReset.emit()
            pass

if __name__ == '__main__':
    print("starting main, initializing GUI, please wait ... ")
    
    if hasattr(QtCore.Qt, 'AA_EnableHighDpiScaling'):
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    if hasattr(QtCore.Qt, 'AA_UseHighDpiPixmaps'):
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication([])
    sys_state = wsys.status()
    win = WizardGUI()
    #win.setupUi(MyWizard)
#    app.aboutToQuit.connect(win.stop_worker)    #graceful thread termination on app exit
    win.show()
    stemlabcontrol = StemlabControl() #TODO TODO TODO: remover after transfer of player

    system_state = sys_state.get_status()

    tab_dict ={}
    #tab_dict["list"] = ["resample","view_spectra","yamleditor","xcore","waveditor"]
    tab_dict["list"] = ["xcore"]

    if 'resampler_module_v5' in sys.modules:
        resample_m = rsmp.resample_m() #TODO: wird gui in _m jemals gebraucht ? ich denke nein !
        resample_c = rsmp.resample_c(resample_m) #TODO: replace sys_state
        resample_v = rsmp.resample_v(win.ui,resample_c, resample_m) #TODO: replace sys_state
        tab_dict["list"].append("resample")
        resample_v.SigActivateOtherTabs.connect(win.setactivity_tabs)
        resample_c.SigActivateOtherTabs.connect(win.setactivity_tabs)

    else:
        win.ui.tabWidget.setTabVisible('tab_resample',False)

    if 'view_spectra' in sys.modules:
        view_spectra_m = vsp.view_spectra_m()
        view_spectra_c = vsp.view_spectra_c(view_spectra_m)
        view_spectra_v = vsp.view_spectra_v(win.ui,view_spectra_c,view_spectra_m)
        tab_dict["list"].append("view_spectra")

    if 'yaml_editor' in sys.modules:
        yamleditor_m = yed.yamleditor_m()
        yamleditor_c = yed.yamleditor_c(yamleditor_m)
        yamleditor_v = yed.yamleditor_v(win.ui,yamleditor_c,yamleditor_m)
        tab_dict["list"].append("yamleditor")
    else:
        page = win.ui.tabWidget.findChild(QWidget, "tab_yamleditor")
        c_index = win.ui.tabWidget.indexOf(page)
        win.ui.tabWidget.setTabVisible(c_index,False)

    xcore_m = core_m()
    xcore_c = core_c(xcore_m)
    xcore_v = core_v(win.ui,xcore_c,xcore_m)

    if 'waveditor' in sys.modules:
        waveditor_m = waved.waveditor_m()
        waveditor_c = waved.waveditor_c(waveditor_m)
        waveditor_v = waved.waveditor_v(win.ui,waveditor_c,waveditor_m)
        tab_dict["list"].append("waveditor")
    else:
        page = win.ui.tabWidget.findChild(QWidget, "tab_waveditor")
        c_index = win.ui.tabWidget.indexOf(page)
        win.ui.tabWidget.setTabVisible(c_index,False)

    if 'configuration' in sys.modules:
        configuration_m = conf.configuration_m()
        configuration_c = conf.configuration_c(configuration_m)
        configuration_v = conf.configuration_v(win.ui,configuration_c,configuration_m)
    else:
        page = win.ui.tabWidget.findChild(QWidget, "tab_configuration")
        c_index = win.ui.tabWidget.indexOf(page)
        win.ui.tabWidget.setTabVisible(c_index,False)
        pass
        #win.ui.tabWidget.setTabVisible('configuration',False)

    # if 'playrec' in sys.modules:
    #     playrec_m = playrec.playrec_m()
    #     playrec_c = playrec.playrec_c(configuration_m)
    #     playrec_v = playrec.playrec_v(win.ui,configuration_c,configuration_m)
    #     playrec_v.SigActivateOtherTabs.connect(win.setactivity_tabs)
    #     playrec_c.SigActivateOtherTabs.connect(win.setactivity_tabs)
    # else:
    #     page = win.ui.tabWidget.findChild(QWidget, "tab_playrec")
    #     c_index = win.ui.tabWidget.indexOf(page)
    #     win.ui.tabWidget.setTabVisible(c_index,False)

    #resample_v.SigUpdateOtherGUIs.connect(win.showfilename)
    #TODO TODO TODO: das muss für alle Tabs gemacht werden
    #view_spectra_v.SigSyncGUIUpdatelist.connect(win.generate_GUIupdaterlist)
    resample_v.SigUpdateOtherGUIs.connect(win.sendupdateGUIs)
    #resample_c.SigUpdateGUIelements.connect(resample_v.updateGUIelements)
    win.SigUpdateOtherGUIs.connect(view_spectra_v.updateGUIelements)

    #directory of tab objects to be activated ####TODO: simplify to simple list
    

    #tab_dict["list"] = ["view_spectra","view_spectra"]
    
    for tabitem1 in tab_dict["list"]:
        for tabitem2 in tab_dict["list"]:
            eval(tabitem1 + "_v.SigRelay.connect(" + tabitem2 + "_v.rxhandler)")
                ########## TODO: temporary hack for core module, change after last Module change:
            eval(tabitem1 + "_v.SigRelay.connect(win.rxhandler)" )
            win.logger.debug(f'File opened: {tabitem1 + "_v.SigRelay.connect(" + tabitem2 + "_v.rxhandler)"}')
            #print(tabitem1 + "_v.SigRelay.connect(" + tabitem2 + "_v.rxhandler)")
        eval("win.SigRelay.connect(" + tabitem1 + "_v.rxhandler)" )
    
    #######################TODO: CHECK IF STILL NECESSARY #######################
    for tabitem in tab_dict["list"]:     
        tab_dict[tabitem + "_m"] = eval(tabitem + "_m") #resample_m     
        tab_dict[tabitem + "_c"] = eval(tabitem + "_c") #resample_c     
        tab_dict[tabitem + "_v"] = eval(tabitem + "_v") #resample_v  
        win.generate_GUIupdaterlist(eval(tabitem + "_v.updateGUIelements"))
    #make tab dict visible to core module
    win.tab_dict = tab_dict
    system_state = sys_state.get_status()
    system_state["tab_dict"] = tab_dict
    sys_state.set_status(system_state)
    ###################CHECK IF STILL NECESSARY END ###########################

    win.SigRelay.emit("cm_all_",["emergency_stop",False])
    win.SigRelay.emit("cm_all_",["fileopened",False])
    win.SigRelay.emit("cm_all_",["Tabref",win.Tabref])
    win.SigRelay.emit("cm_resample",["rates",system_state["rates"]])
    win.SigRelay.emit("cm_resample",["irate",system_state["irate"]])
    win.SigRelay.emit("cm_resample",["reslist_ix",system_state["reslist_ix"]]) #TODO check: maybe local in future !
    win.SigRelay.emit("cm_playrec",["Obj_stemlabcontrol",stemlabcontrol])
    win.SigRelay.emit("cm_configuration",["tablist",tab_dict["list"]])
    win.SigRelay.emit("cexex_configuration",["updateGUIelements",0])
    sys.exit(app.exec_())

#TODOs:

    # fix error with SNR calculation: there seems to be no reactio to baselineshifts when calculating the SNR for praks and identifying those above threshold
    #
        #################TODO TEST in resample module: implement next line newly with Relay after tarnsfer of wavedit module 
        #self.gui.fill_wavtable() has already been replaced by Relay
    #
    # * Player-Modul übertragen: 10h
    #
    # + Player Modul um Rec ausbauen: 5h
    #
    # * Annotator Modul übertragen: 20 h
    #
    # * // \\ Problem lösen: 2h: in aktuellem Core, Annotator UND waveditor !!!!
    #
    # * Core-Modul umstellen: 3h
    #
    # * Tabs von nicht importierten Modulen deaktivieren/blinden: 30min
    #
    # * eval-Befehl bei Kompilation testen: 30 min
    #
    # * Windows Installer mit https://www.pythonguis.com/tutorials/packaging-pyside6-applications-windows-pyinstaller-installforge/ erstellen
#
    # * Configuration Tab with: IP address, tempdir, outdir, LT/UTC, Logging, checkboxes for Tab activation

#
    # Recorder: New impl: worker gets setter/getter structure
    #                       
    #                       progress-clock: SigSpecplotemit(object: data) for external spectrum plot
    # Recorder starter routine: setup thread
    #                           finished.connect close file and complete wav header
    #                           SigSpecplot.connect: plot signal somewhere
    #
    #   zerlege plot_spectrum in einen view_spectra spezifischen Teil und einen generellen Spektralplotter, der in einen Canvas das Spektrum eines Datenstrings plottet
    #       spectrum(canvas_ref,data,*args) in auxiliary Modul







  # ############################## TAB WAV EDITOR ####################################
        
    # def clear_WAVwidgets(self):
    #     """_VIEW: clear the tabwidgets of the wav-editor tab
    #     :param : none
    #     :type : none
    #     :raises [ErrorType]: [ErrorDescription]
    #     :return: none
    #     :rtype: none
    #     """
    #     for ix in range(0,14):
    #         self.ui.tableWidget_basisfields.item(ix, 0).setData(0,0)
    #     for ix in range(0,8):
    #         self.ui.tableWidget_starttime.item(ix, 0).setData(0,0)
    #         self.ui.tableWidget_starttime.item(ix, 1).setData(0,0)

    #     # write other info to table 3 (strings)                    
    #     self.ui.tableWidget_3.item(2, 0).setText("")
    #     self.ui.tableWidget_3.item(1, 0).setText("")
    #     self.ui.tableWidget_3.item(0, 0).setText("")
    #     self.ui.tableWidget_3.item(3, 0).setText("")


    # def overwrite_header(self):
    #     """
    #     VIEW or CONTROLLER ??
        
    #     """
    #     """_VIEW: clear the tabwidgets of the wav-editor tab
    #     :param : none
    #     :type : none
    #     :raises [ErrorType]: [ErrorDescription]
    #     :return: none
    #     :rtype: none
    #     """
    #     system_state = sys_state.get_status()
    #     if system_state["fileopened"] is False:
    #         sys_state.set_status(system_state)
    #         return False
    #     msg = QMessageBox()
    #     msg.setIcon(QMessageBox.Question)
    #     msg.setText("overwrite wav header")
    #     msg.setInformativeText("you are about to overwrite the header of the current wav file with the values in the tables of Tab 'WAV Header'. Do you really want to proceed ?")
    #     msg.setWindowTitle("overwrite")
    #     msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    #     msg.buttonClicked.connect(self.popup)
    #     msg.exec_()

    #     if self.yesno == "&Yes":
    #         self.ovwrt_flag = True
    #         self.write_edited_wavheader()
    #     else:
    #         sys_state.set_status(system_state)
    #         return False

    #     #TODO: write backup dump header
    #     #TODO: rename file to SDRUno name convention if filetype = .dat
    #     if self.filetype == "dat":
    #         old_name = system_state["f1"]
    #         SDRUno_suffix = str(self.wavheader['starttime_dt'])
    #         SDRUno_suffix = SDRUno_suffix.replace(" ","_")
    #         SDRUno_suffix = SDRUno_suffix.replace(":","")
    #         SDRUno_suffix = SDRUno_suffix.replace("-","")
    #         usix = self.my_filename.find('lo')
    #         if usix == -1:
    #             auxi.standard_infobox("dat file does not meet old COHIRADIA RFCorder name convention; file will be renamed with correct suffixes")
    #             usix = len(self.my_filename)+2
    #         bbb = self.my_filename[0:usix-2]
    #         new_name = self.my_dirname + '/' + bbb + '_' + str(SDRUno_suffix) + '_' + str(int(np.round(self.wavheader["centerfreq"]/1000))) + 'kHz.wav'
    #         shutil.move(old_name, new_name)
    #         system_state["f1"] = new_name #TODO: replace by line below
    #         self.SigRelay.emit("cm_all_",["f1",new_name])
    #         self.SigRelay.emit("cm_all_",["my_filename",self.my_filename])
    #         self.SigRelay.emit("cexex_view_spectra",["updateGUIelements",0])
    #         self.showfilename() #remove after complete transtition to Relay
    #     self.ui.label_8.setEnabled(False)
    #     self.ui.pushButton_InsertHeader.setEnabled(False)
    #     self.filetype = "wav"
    #     sys_state.set_status(system_state)

    # def fill_wavtable(self):
    #     """
    #     VIEW
    #     fill tables on TAB wavedit with the respective values from the vaw header
    #     """
    #     starttime = self.wavheader['starttime']
    #     stoptime = self.wavheader['stoptime']

    #     #check TODO OBSOLET : diese Info müsste ja nun in  wavheader['starttime_dt'],  wavheader['stoptime_dt'] drin sein !   OBSOLET !
    #     # wird aber noch in stationsloop in auto_closedlabel = (stdcheck or inactcheck) and (self.host.rectime >= self.host.STICHTAG)
    #     #verwendet
    #     self.rectime = datetime(starttime[0],starttime[1],starttime[3],starttime[4],starttime[5],starttime[6])
    #     self.recstop = datetime(stoptime[0],stoptime[1],stoptime[3],stoptime[4],stoptime[5],stoptime[6])
    #     start_str = str(self.wavheader['starttime_dt'])

    #     ###Einträge der Tabelle 1 nur Integers
    #     metastring1 = [self.wavheader['filesize'], self.wavheader['sdr_nChunkSize']]
    #     metastring1.append(self.wavheader['wFormatTag'])
    #     metastring1.append(self.wavheader['nChannels'])
    #     metastring1.append(self.wavheader['nSamplesPerSec'])
    #     metastring1.append(self.wavheader['nAvgBytesPerSec'])
    #     metastring1.append(self.wavheader['nBlockAlign'])
    #     metastring1.append(self.wavheader['nBitsPerSample'])
    #     metastring1.append(self.wavheader['centerfreq'])
    #     metastring1.append(self.wavheader['data_nChunkSize'])
    #     metastring1.append(self.wavheader['ADFrequency'])
    #     metastring1.append(self.wavheader['IFFrequency'])
    #     metastring1.append(self.wavheader['Bandwidth'])
    #     metastring1.append(self.wavheader['IQOffset'])               
    #     for ix in range(0,14):
    #         self.ui.tableWidget_basisfields.item(ix, 0).setData(0,metastring1[ix])
    #     for ix in range(0,8):
    #         self.ui.tableWidget_starttime.item(ix, 0).setData(0,starttime[ix])
    #         self.ui.tableWidget_starttime.item(ix, 1).setData(0,stoptime[ix])

    #     # write other info to table 3 (strings)                    
    #     self.ui.tableWidget_3.item(2, 0).setText(start_str)
    #     self.ui.tableWidget_3.item(1, 0).setText(str(self.wavheader['sdrtype_chckID']))
    #     self.ui.tableWidget_3.item(0, 0).setText(str(self.wavheader['nextfilename']))
    #     self.ui.tableWidget_3.item(3, 0).setText(str(self.wavheader['data_ckID']))

    # def check_consistency(self,item,dtype,label):
    #     typetab = {"long": [-2147483648, 2147483647], "ulong": [0, 4294967295], 
    #                 "short": [-32768, 32767]  , "ushort": [0, 65535],
    #                 "float": [-3.4E38, 3.4E38]}

    #     if item < typetab[dtype][0] or item > typetab[dtype][1]:
    #         auxi.standard_errorbox(label + "must be of type " + dtype + ", i.e. in range " + str(typetab[dtype]) + "\n Please correct !")
    #         return False
    #     else:
    #         return True
        
    # def write_edited_wavheader(self):  #TODO move to controller module wavheader
    #     """
    #     CONTROLLER        
    #     """
    #     system_state = sys_state.get_status()
    #     crit1 = False
    #     #TODO : ?Sonderzeichencheck ??
    #     self.wavheader['nextfilename'] = self.ui.tableWidget_3.item(0, 0).text()
    #     preview = {}
    #     for ix in range(0,8):
    #         preview[ix] = int(self.ui.tableWidget_starttime.item(ix, 0).text())
    #     try:
    #         a = datetime(preview[0],preview[1],preview[3],preview[4],preview[5],preview[6])
    #     except ValueError:
    #         auxi.standard_errorbox("start date or time entry is out of valid range, please check and retry")
    #         sys_state.set_status(system_state)
    #         return False
    #     if preview[6] > 999:
    #         crit1 = True

    #     for ix in range(0,8):
    #         preview[ix] = int(self.ui.tableWidget_starttime.item(ix, 1).text())
    #     try:
    #         a = datetime(preview[0],preview[1],preview[3],preview[4],preview[5],preview[6])
    #     except ValueError:
    #         auxi.standard_errorbox("stop date or time entry is out of valid range, please check and retry")
    #         sys_state.set_status(system_state)
    #         return False
    #     if preview[6] > 999 or crit1 == True:
    #         auxi.standard_errorbox("ms value in start or stoptime must not be > 999, please check and retry")
    #         sys_state.set_status(system_state)
    #         return False      
           
    #     for ix in range(0,8):
    #         self.wavheader['starttime'][ix] = int(self.ui.tableWidget_starttime.item(ix, 0).text())
    #         self.wavheader['stoptime'][ix] = int(self.ui.tableWidget_starttime.item(ix, 1).text())

    #     checklist = ['filesize','sdr_nChunkSize','wFormatTag','nChannels', 'nSamplesPerSec',
    #         'nAvgBytesPerSec', 'nBlockAlign','nBitsPerSample','centerfreq','data_nChunkSize',
    #         'ADFrequency','IFFrequency','Bandwidth','IQOffset']
    #     typelist = ['ulong', 'long', 'short', 'short', 'long', 
    #                 'long', 'short', 'short', 'long', 'ulong',
    #                  'long',  'long',  'long',  'long']
    #     for ix2 in range(len(checklist)):
    #         self.wavheader[checklist[ix2]] = int(self.ui.tableWidget_basisfields.item(ix2, 0).text())
    #         chk = False
    #         chk = self.check_consistency(self.wavheader[checklist[ix2]],typelist[ix2],checklist[ix2])
    #         if chk == False:
    #             sys_state.set_status(system_state)
    #             return False
    #             #self.wavheader[checklist[ix2]] = int(self.ui.tableWidget.item(ix2, 0).text())

    #     if system_state["fileopened"] is True:
    #         if self.ovwrt_flag == False: #TODO: wird nie mehr erreicht, oder ?
    #             wav_filename = self.my_dirname + '/templatewavheader.wav'
    #             auxi.standard_errorbox("Template wavheader File is being written, useful ?")
    #         else: 
    #             wav_filename = system_state["f1"]            
    #         WAVheader_tools.write_sdruno_header(self,wav_filename,self.wavheader,self.ovwrt_flag)
    #     sys_state.set_status(system_state)

    # def extract_startstoptimes_auxi(self, wavheader): #TODO: move to controller module edit wavheader
    #     """_synthetize next filename in the playlist in case the latter cannot be extracted
    #     from auxi SDR-wav-header because it is longar than 96 chars_
    #     can only be used for SDRUno and RFCorder header
    #     CONTROLLER
    #     :param : wavheader [dictionary]
    #     :type : dictionary
    #     :raises [ErrorType]: [ErrorDescription]
    #     :return: next_filename
    #     :rtype: str
    #     """
    #     ###TODO error handling
    #     ###TODO: check if the following fixes for binary representations are necessary when using UNICODE
    #     wavheader['nextfilename'] = (wavheader['nextfilename']).replace('x00','')
    #     wavheader['nextfilename'] = (wavheader['nextfilename']).replace("'","")
    #     wavheader['nextfilename'] = (wavheader['nextfilename']).replace('b''','')
    #     wavheader['nextfilename'] = wavheader['nextfilename'].rstrip(' ')
    #     wavheader['nextfilename'] = wavheader['nextfilename'].rstrip('\\')
    #     nextfilename = wavheader['nextfilename']
    #     nextfilename_purged = nextfilename.replace('/','\\')
    #     nextfile_dirname = os.path.dirname(nextfilename_purged)
    #     #TODO: nextfilename dirname is frequently 0 --> quest is invalid
    #     if len(nextfile_dirname) > 3:
    #         if (wavheader['nextfilename'][0:2] == "'\\") is False:
    #             self.loopalive = False   ### stop playlist loop  #######################  loop must be handled inside this method !
    #             true_nextfilename = ''
    #         else:
    #             if wavheader['nextfilename'].find('.wav') != -1: ### take next filename from wav header
    #                 true_nextfilename, next_ext = os.path.splitext(os.path.basename(nextfilename_purged))
    #             else: ### synthetize next filename because wav header string for nextfile longer 92 chars
    #                 self.logger.debug("nextfile entry in wavheader invalid, please edit wav header")
    #                 true_nextfilename = ''
    #                 return true_nextfilename
    #             self.loopalive = True
    #         return true_nextfilename
    ############################## END TAB WAV EDITOR ####################################

    ############################## GENERAL FUNCTIONS ####################################


            # ### UI TAB WAVHEADER ####################################
        # self.ui.pushButton_InsertHeader.setEnabled(False)
        # self.ui.pushButton_InsertHeader.clicked.connect(self.overwrite_header)
        # self.ui.radioButton_WAVEDIT.setEnabled(True)
        # self.ui.radioButton_WAVEDIT.setChecked(False)
        # self.ui.radioButton_WAVEDIT.clicked.connect(self.activate_WAVEDIT)
        # self.ui.tableWidget_basisfields.setEnabled(False)
        # self.ui.tableWidget_starttime.setEnabled(False)
        # self.ui.tableWidget_3.setEnabled(False)
        # ###END UI TAB WAVHEADER ####################################

        # elements of yaml header generator tab
        #self.ui.pushButton_Writeyamlheader.setEnabled(False) # activate after completion of the annotation procedure
        #self.ui.pushButton_Writeyamlheader.clicked.connect(self.yaml_header_buttonfcn)
        #self.scanplotcreated = False
    # def inactivate_tabs(self,selection):
    #     """
    #     VIEW
    #     TODO: zentrale self.Tabref-Struktur für die Eintragung Tab-Definitionen dieser Art verwenden und auf diese zugreifen
    #     TODO. Tab-Namen anpassen
    #     inactivates selected tabs, selection by list of strings which refer to the individual tabs
    #     :param selection: list of strings, possible: ["Player","View_Spectra","Annotate","Resampler","YAML_editor","WAV_header"]
    #     :type selection: list of strings
    #     ...
    #     :raises [ErrorType]: none
    #     ...
    #     :return: none
    #     :rtype: none
    #     """
    #     if "Player" in selection:
    #         self.ui.tab.setEnabled(False)
    #     if "View_Spectra" in selection:
    #         self.ui.tab_3.setEnabled(False)
    #         #self.ui.tab_3.setVisible(False)
    #     if "Annotate" in selection:
    #         self.ui.tab_4.setEnabled(False)
    #     #if "Resampler" in selection:
    #         #self.ui.tab_2.setEnabled(False)
    #     if "YAML_editor" in selection:
    #         self.ui.tab_5.setEnabled(False)
    #     if "WAV_header" in selection:            
    #         self.ui.tab_1.setEnabled(False)
    #     if "Resample" in selection:            
    #         self.ui.tab_resample.setEnabled(False)

            
    # def activate_tabs(self,selection):
    #     """
    #     VIEW
    #     TODO: zentrale self.Tabref-Struktur für die Eintragung Tab-Definitionen dieser Art verwenden und auf diese zugreifen
    #     TODO. Tab-Namen anpassen
    #     activates selected tabs
    #     :param selection: list of strings, possible: ["Player","View_Spectra","Annotate","Resampler","YAML_editor","WAV_header"]
    #     :type selection: list of strings, selection by list of strings which refer to the individual tabs
    #     ...
    #     :raises [ErrorType]: none
    #     ...
    #     :return: none
    #     :rtype: none
    #     """
    #     if "Player" in selection:
    #         self.ui.tab.setEnabled(True)
    #     if "View_Spectra" in selection:
    #         self.ui.tab_3.setEnabled(True)
    #     if "Annotate" in selection:
    #         self.ui.tab_4.setEnabled(True)
    #     if "YAML_editor" in selection:
    #         self.ui.tab_5.setEnabled(True)
    #     if "WAV_header" in selection:            
    #         self.ui.tab_1.setEnabled(True)
    #     if "Resample" in selection:            
    #         self.ui.tab_resample.setEnabled(True)


