# -*- coding: utf-8 -*-
"""
Created on Mar 25 2023
#@author: scharfetter_admin
"""
#from pickle import FALSE, TRUE #intrinsic
import sys
import time
import os
#import subprocess
import datetime as ndatetime
from datetime import datetime
from pathlib import Path, PureWindowsPath
#from datetime import timedelta
#from socket import socket, AF_INET, SOCK_STREAM
#from struct import pack, unpack
import numpy as np
#from PyQt5.QtCore import QTimer
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
#from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg,  NavigationToolbar2QT as NavigationToolbar
#from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from scipy import signal as sig
from scipy.ndimage.filters import median_filter
import pandas as pd  #TODO: check, not installed under this name
import yaml
import logging
#from COHIWizard_GUI_v10 import Ui_MainWindow as MyWizard
#from auxiliaries import WAVheader_tools
from auxiliaries import auxiliaries as auxi
from auxiliaries import timer_worker as tw
from PyQt5.QtCore import QObject, QThread, pyqtSignal, QMutex       #TODO: OBSOLETE
import system_module as wsys


class statlst_gen_worker(QtCore.QThread):
    __slots__ = ["continue","T","freq","closed","stations_filename","rectime","stichtag","locs_union","annotation","progressvalue","statusfilename"]
    
    SigProgressBar = pyqtSignal()
    SigFinished = pyqtSignal()

    def __init__(self, host_window):
        super(statlst_gen_worker, self).__init__()
        self.host = host_window
        self.__slots__[2] = []
        self.__slots__[3] = []
        self.mutex = QtCore.QMutex()
    def set_continue(self,_value):
        self.__slots__[0] = _value
    def get_continue(self):  ##TODO: obsolete ??
        return(self.__slots__[0])
    def set_T(self,_value):
        self.__slots__[1] = _value
    def get_T(self):
        return(self.__slots__[1])  
    def set_freq(self,_value):
        self.__slots__[2] = _value
    def get_freq(self):
        return(self.__slots__[2])
    def set_closed(self,_value):
        self.__slots__[3] = _value
    def get_closed(self):
        return(self.__slots__[3])            
    def set_stations_filename(self,_value):
        self.__slots__[4] = _value  
    def get_stations_filename(self):
        return(self.__slots__[4])    
    def set_rectime(self,_value):
        self.__slots__[5] = _value  
    def get_rectime(self):  
        return(self.__slots__[5])    
    def set_stichtag(self,_value):
        self.__slots__[6] = _value  
    def get_stichtag(self):  
        return(self.__slots__[6])    
    def set_locs_union(self,_value):
        self.__slots__[7] = _value  
    def get_locs_union(self):  
        return(self.__slots__[7])    
    def set_annotation(self,_value):
        self.__slots__[8] = _value  
    def get_annotation(self):  
        return(self.__slots__[8])    
    def set_progressvalue(self,_value):
        self.__slots__[9] = _value  
    def get_progressvalue(self):  
        return(self.__slots__[9])
    def set_status_filename(self,_value):
        self.__slots__[10] = _value  
    def get_status_filename(self):  
        return(self.__slots__[10]) 
    
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
        locs_union = self.get_locs_union()
        rectime = self.get_rectime()
        stichtag = self.get_stichtag()
        annotation = self.get_annotation()
        #progressvalue = self.get_stichtag()

        try:
            f = open(self.get_stations_filename(), 'w', encoding='utf-8')
            # Laufe durch alle Peak-Frequenzen des Spektrums mit index ix
            #make this a thread
            #print(f"statslist gen worker: stations_loop reached, write file: {self.get_stations_filename()}, fileref: {f}")
            #for ix in range(len(self.host.locs_union)):
            for ix in range(len(locs_union)):
                
                #progress = np.floor(100*ix/len(self.host.locs_union))
                progress = np.floor(100*ix/len(locs_union))
                
                self.set_progressvalue(int(progress))
                #print(f"peak index during annotation:{ix}")
                # f.write('- frequency: "{}"\n'.format(self.host.annotation["FREQ"][ix]))
                # f.write('  snr: "{}"\n'.format(round(self.host.annotation["MSNR"][ix])))
                f.write('- frequency: "{}"\n'.format(annotation["FREQ"][ix]))
                f.write('  snr: "{}"\n'.format(round(annotation["MSNR"][ix])))
                # locs union enthält nur Frequenzindices, nicht Frequenzen ! ggf. umrechnen !
                # suche für jede freq ix alle MWtabellen-Einträge mit der gleichen Frequenz und sammle die entspr Tabellenindices im array ixf
                #ixf = [i for i, x in enumerate(self.__slots__[2]) if np.abs((x - self.host.annotation["FREQ"][ix])) < 1e-6]
                ixf = [i for i, x in enumerate(self.__slots__[2]) if np.abs((x - annotation["FREQ"][ix])) < 1e-6]
                _T = self.get_T()
                if np.size(ixf) > 0:
                    #print("annoate: npsize>0 reached")
                    # wenn ixf nicht leer setze Landeszähler ix_c auf 0, initialisiere flag cs auf 'none'
                    cs = [] # memory for current country
                    sortedtable = [] #Setze sortedtable zurück
                    yaml_ix = 0
                    for ix2 in ixf:
                        #print(f"annotate worker: ix2: {ix2}, ixf: {ixf}")
                        # für jeden index ix2 in ixf zum Peak ix prüfe ob es den String 'ex ' in der Stationsspalte der MWTabelle gibt
                        #if type(self.__slots__[1].station.iloc[ix2]) != str:
                        if type(_T.station.iloc[ix2]) != str:    
                            curr_station = 'No Name'
                        else:
                            #curr_station = self.__slots__[1].station.iloc[ix2]
                            curr_station = _T.station.iloc[ix2]
                        #print(f"Hurraa 1, current station: {curr_station}")
                        #if type(self.__slots__[1].programme.iloc[ix2]) != str:
                        if type(_T.programme.iloc[ix2]) != str:
                            #print("typecheck A")
                            curr_programme = 'No Name'
                        else:
                            #print("typecheck B")
                            #curr_programme = self.__slots__[1].programme.iloc[ix2]
                            curr_programme = _T.programme.iloc[ix2]
                            #print("typecheck B")
                        #print(f"Hurraa 1, current programme: {curr_programme}")
                        #if type(self.__slots__[1].tx_site.iloc[ix2]) != str:
                        if type(_T.tx_site.iloc[ix2]) != str:
                            curr_tx_site = 'No Name'
                        else:
                            #curr_tx_site = self.__slots__[1].tx_site.iloc[ix2]
                            curr_tx_site = _T.tx_site.iloc[ix2]
                        #print(f"Hurraa 1, current tx site: {curr_tx_site}")
                        if curr_station.find("ex ") == 0:
                            stdcheck = True
                        else:
                            stdcheck = False
                        #print(f"Hurraa 1, stdcheck: {stdcheck}")
                        # für jeden index ix2 in ixf zum Peak ix prüfe ob es den String 'INACTI' in der Stationsspalte der MWTabelle gibt
                        inactcheck = 'INACTI' in curr_station
                        # logisches label falls ()'ex ' oder 'INACT') und recording-time > Stichtag der MWTabellen-Erstellung
                        # kennzeichnet, wenn ein Sender sicher zum Zeitpunkt der Aufnahme geschlossen war
                        #auto_closedlabel = (stdcheck or inactcheck) and (self.host.rectime >= self.host.STICHTAG)
                        auto_closedlabel = (stdcheck or inactcheck) and (rectime >= stichtag)
                        #print(f"auto_closedlabel: {auto_closedlabel}")
                        # if not ((self.__slots__[3][ix2] - self.host.rectime).days <= 0 or auto_closedlabel):
                        if not ((self.__slots__[3][ix2] - rectime).days <= 0 or auto_closedlabel):
                            #print("ifnot case Hurraa 2")
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
                            #print("end of ifnot case quest reached")
                    #print(f"annotate after first loop: ix2: {ix2}")
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
                #print("stationsloop progressvalue emit <<<<<<<<<<<<<<<<<<<<")
                #self.host.progressvalue = int(progress)*10
                #self.set_progressvalue(int(progress))
                #self.set_continue(False)
                #self.mutex.lock()
                #self.SigProgressBar.emit()
                #self.mutex.unlock()
                # wait for confirmation from Progress bar updating
                # while self.get_continue() == False:
                #     time.sleep(0.001)
        except:
            print("annotation file not yet existent")
            #logging.info("annotation file not yet existent")
            return False

        status = {}
        status["freqindex"] = 0
        status["annotated"] = False
        stream = open(self.get_status_filename(), "w")
        yaml.dump(status, stream)
        stream.close()
        self.set_continue(False)
        self.set_progressvalue(int(progress))
        self.SigProgressBar.emit()
        # wait for confirmation from Progress bar updating
        while self.get_continue() == False:
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
    __slots__ = ["GUI_parameters", "continue","pdata","progressvalue","horzscal",
             "filepath","readoffset","wavheader","datablocksize","baselineoffset",
             "unions","annotation_filename","annotation"]

    SigUpdateUnions = pyqtSignal()
    SigUpdateGUI = pyqtSignal()
    SigScandeactivate = pyqtSignal()
    SigFinished = pyqtSignal()
    SigProgressBar = pyqtSignal()
    SigStatustable = pyqtSignal()
    SigPlotdata = pyqtSignal()
    SigAnnSpectrum = pyqtSignal(object)
    SigAnnotation = pyqtSignal()


    def __init__(self, host_window):
        super(autoscan_worker, self).__init__()
        self.host = host_window
        self.locs_union = []
        self.freq_union = []
        self.slot_0 = []
        self.slot_1 = [False]
        self.slot_2 = {}

    def set_GUI_parameters(self,_value):
        """
        __slots__[0] has entries: NUMSNAPS, PROMINENCE
        """
        self.__slots__[0] = _value
    def get_GUI_parameters(self):
        return(self.__slots__[0])
    def set_continue(self,_value):
        self.__slots__[1] = _value
    def get_continue(self):
        return(self.__slots__[1])
    def set_pdata(self,_value):
        self.__slots__[2] = _value
    def get_pdata(self):
        return(self.__slots__[2])
    def set_progressvalue(self,_value):
        self.__slots__[3] = _value
    def get_progressvalue(self):
        return(self.__slots__[3])
    def set_horzscal(self,_value):
        self.__slots__[4] = _value
    def get_horzscal(self):
        return(self.__slots__[4])
    def set_filepath(self,_value):
        self.__slots__[5] = _value
    def get_filepath(self):
        return(self.__slots__[5])
    def set_readoffset(self,_value):
        self.__slots__[6] = _value
    def get_readoffset(self):
        return(self.__slots__[6])
    def set_wavheader(self,_value):
        self.__slots__[7] = _value
    def get_wavheader(self):
        return(self.__slots__[7])
    def set_datablocksize(self,_value):
        self.__slots__[8] = _value
    def get_datablocksize(self):
        return(self.__slots__[8])
    def set_baselineoffset(self,_value):
        self.__slots__[9] = _value
    def get_baselineoffset(self):
        return(self.__slots__[9])
    def set_unions(self,_value):
        self.__slots__[10] = _value
    def get_unions(self):
        return(self.__slots__[10])
    def set_annotation_filename(self,_value):
        self.__slots__[11] = _value
    def get_annotation_filename(self):
        return(self.__slots__[11])
    def set_annotation(self,_value):
        self.__slots__[12] = _value
    def get_annotation(self):
        return(self.__slots__[12])

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
        self.SigUpdateGUI.emit()
        self.SigScandeactivate.emit()
        # TODO: CHECK: connect self.scan_deactivate()
        self.NUMSNAPS = self.get_GUI_parameters()[0]
        self.PROMINENCE = self.get_GUI_parameters()[1]
        self.annot = [dict() for x in range(self.NUMSNAPS)]
        #print(f"annotate autoscan fu reached, GUI params: {self.get_GUI_parameters()}")
        for self.autoscan_ix in range(self.NUMSNAPS):
            self.position = int(np.floor(self.autoscan_ix/self.NUMSNAPS*100))
            self.set_progressvalue(self.position)
            self.set_continue(False)
            self.SigProgressBar.emit()
            # wait for confirmation from Progress bar updating
            #print(f"annotate autoscan fu reached, position: {self.position}")
            while self.get_continue() == False:
                time.sleep(0.01)
            wavheader = self.get_wavheader()
            pscale = wavheader['nBlockAlign']
            position = int(np.floor(pscale*np.round(wavheader['data_nChunkSize']*self.position/pscale/100)))
            BPS = wavheader["nBitsPerSample"]
            ret = auxi.readsegment_new(self,self.get_filepath(),position,self.get_readoffset(), self.get_datablocksize(),BPS,BPS,wavheader["wFormatTag"])#TODO: replace by slots communication
            data = ret["data"]
            if 2*ret["size"]/wavheader["nBlockAlign"] < self.get_datablocksize(): #TODO: replace by slots communication
                return False
            #TODO: new invalidity condition, replace/remove old one: 
            # if len(data) == 10:
            #     if np.all(data == np.linspace(0,9,10)):
            #         return False
            self.set_continue(False)
            self.SigAnnSpectrum.emit(data)
            while self.get_continue() == False:
                time.sleep(0.001)
            self.SigAnnSpectrum.emit(data)
            pdata = self.get_pdata()
            self.set_continue(False)
            self.SigPlotdata.emit()
            # wait until plot has been carried out
            while self.get_continue() == False:
                time.sleep(0.001)
            self.annot[self.autoscan_ix]["FREQ"] = pdata["datax"] 
            self.annot[self.autoscan_ix]["PKS"] = pdata["peaklocs"]
            peaklocs = pdata["peaklocs"]
            datay = pdata["datay"]
            basel = pdata["databasel"] + self.get_baselineoffset()
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
        self.set_unions([self.locs_union,self.freq_union])
        self.SigUpdateUnions.emit()

        meansnr = np.zeros(len(self.locs_union))
        minsnr = 1000*np.ones(len(self.locs_union))
        maxsnr = -1000*np.ones(len(self.locs_union))
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
        #TODO: check if file exists
        try:
            stream = open(self.get_annotation_filename(), "w")
            yaml.dump(yamldata, stream)
            stream.close()
        except:
            print("cannot write annotation yaml")
            pass
        self.set_annotation(self.annotation)
        self.SigAnnotation.emit()
        self.SigStatustable.emit()
        self.set_continue(False)
        while self.get_continue() == False:
                time.sleep(0.001)
        self.SigFinished.emit()
        print("+++++++++++++++++++++++++++++          leave autoscan thread")


class annotate_m(QObject):
    __slots__ = ["None"]
    SigModelXXX = pyqtSignal()

    def __init__(self):
        super().__init__()
        # Constants
        self.CONST_SAMPLE = 0 # sample constant
        self.mdl = {}
        self.mdl["sample"] = 0
        self.mdl["_log"] = False
        self.mdl["baselineoffset"] = 0
        # Create a custom logger
        logging.getLogger().setLevel(logging.DEBUG)
        # Erstelle einen Logger mit dem Modul- oder Skriptnamen
        self.logger = logging.getLogger(__name__)
        # Create handlers
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


class annotate_c(QObject):
    """_view method
    """
    __slots__ = ["contvars"]

    SigAny = pyqtSignal()
    SigRelay = pyqtSignal(str,object)

    def __init__(self, annotate_m): #TODO: remove gui
        super().__init__()
        self.m = annotate_m.mdl
        self.logger = annotate_m.logger
        self.DATABLOCKSIZE = 1024*32
        self.m["DELTAF"] = 5000 #minimum peak distance in Hz for peak detector #TODO:occurs in ann-module; values also used in spectrum view; ; must be shifted to the respective modules in future
        self.m["PEAKWIDTH"] = 10 # minimum peak width in Hz for peak detector #TODO:occurs in ann-module; values also used in spectrum view; ; must be shifted to the respective modules in future
        self.m["PROMINENCE"] = 15 # minimum peak prominence in dB above baseline for peak detector #TODO:occurs in ann-module; values also used in spectrum view; ; must be shifted to the respective modules in future
        self.m["FILTERKERNEL"] = 2 # length of the moving median filter kernel in % of the spectral span #TODO:occurs in ann-module; values also used in spectrum view; ; must be shifted to the respective modules in future
        self.STICHTAG = datetime(2023,2,25,0,0,0)

    def autoscan(self):
        """
        _summary_
        """
        #print("autoscan reached")
        self.logger.debug("autoscan reached")
        if os.path.exists(self.m["cohiradia_yamlheader_filename"]) == False:         #exist yaml file: create from yaml-editor
            self.m["cohiradia_yamlheader_dirname"] = self.m["my_dirname"] + '/' + self.m["annotationdir_prefix"] + self.m["my_filename"]
            if os.path.exists(self.m["cohiradia_yamlheader_dirname"]) == False:
                os.mkdir(self.m["cohiradia_yamlheader_dirname"])

        self.autoscanthread = QThread()
        self.autoscaninst = autoscan_worker(self)
        self.autoscaninst.moveToThread(self.autoscanthread)
        self.SigRelay.emit("cexex_annotate",["getGUIvalues",0])
        time.sleep(0.001)
        self.autoscaninst.set_GUI_parameters([self.m["NumScan"],self.m["minSNR"],[]])
        self.autoscaninst.set_filepath(self.m["f1"])
        self.autoscaninst.set_readoffset(self.m["readoffset"])
        self.autoscaninst.set_wavheader(self.m["wavheader"])
        self.autoscaninst.set_datablocksize(self.DATABLOCKSIZE)
        self.autoscaninst.set_baselineoffset(self.m["baselineoffset"])
        self.autoscaninst.set_annotation_filename(self.m["annotation_filename"])
        self.autoscanthread.started.connect(self.autoscaninst.autoscan_fun)
        self.autoscaninst.SigFinished.connect(self.ann_stations)
        self.autoscaninst.SigFinished.connect(self.autoscanthread.quit)
        self.autoscaninst.SigFinished.connect(self.autoscaninst.deleteLater)
        self.autoscanthread.finished.connect(self.autoscanthread.deleteLater)
        self.autoscaninst.SigUpdateUnions.connect(self.annupdateunions)
        self.autoscaninst.SigAnnSpectrum.connect(self.annspectrumhandler)
        self.autoscaninst.SigAnnotation.connect(self.annotationset)
        # connect autoscaninst signals with annotate_v methods (GUI updates, displays ...)
        self.SigRelay.emit("cexex_annotate",["connect_autoscan",0])
        time.sleep(0.001)
        self.autoscanthread.start()
        if self.autoscanthread.isRunning():
            self.autoscanthreadActive = True

    def annotationset(self):
        self.annotation = self.autoscaninst.get_annotation()
        self.autoscaninst.set_continue(True)

    def annupdateunions(self):
        #print("annupdate unions")
        [self.locs_union,self.freq_union] =self.autoscaninst.get_unions()

    def annspectrumhandler(self,data):
        pdata = self.ann_spectrum(data)
        self.autoscaninst.set_pdata(pdata)
        self.autoscaninst.set_continue(True)
        pass

    def ann_spectrum(self,data):
        """
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
        flo = self.m["wavheader"]['centerfreq'] - self.m["wavheader"]['nSamplesPerSec']/2
        fup = self.m["wavheader"]['centerfreq'] + self.m["wavheader"]['nSamplesPerSec']/2
        freq0 = np.linspace(0,self.m["wavheader"]['nSamplesPerSec'],N)
        freq = freq0 + flo
        datax = freq
        datay = 20*np.log10(spr)
        # filter out all data below the baseline; baseline = moving median
        # filter kernel is self.m["FILTERKERNEL"] % of the spectral span
        datay_filt = datay
        kernel_length = int(N*self.m["FILTERKERNEL"]/100)
        # kernel length must be odd integer
        if (kernel_length % 2) == 0:
            kernel_length += 1
        
        databasel = median_filter(datay,kernel_length, mode = 'constant')
        datay_filt[datay_filt < databasel] = databasel[datay_filt < databasel]
        # find all peaks which are self.PROMINENCE dB above baseline and 
        # have a min distance of self.["DELTAF"] and a min width of self.["PEAKWIDTH"]
        dist = np.floor(np.maximum(self.m["DELTAF"]/self.m["wavheader"]['nSamplesPerSec']*N,100))
        wd = np.floor(self.m["PEAKWIDTH"]/self.m["wavheader"]['nSamplesPerSec']*N)

        peaklocs, peakprops = sig.find_peaks(datay_filt,
                        prominence=(self.m["PROMINENCE"],None), distance=dist, width = wd)
        ret = {"datax": datax, "datay": datay, "datay_filt": datay_filt,
               "peaklocs": peaklocs, "peakprops": peakprops, "databasel": databasel}
        return ret
    
    @auxi.waiting_effect
    def mwlistread(self,MWlistname):
        T = pd.read_excel(MWlistname)
        return T

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
        #self.m = sys_state.get_status()

        self.stations_filename = self.m["annotationpath"] + '/stations_list.yaml'
        if os.path.exists(self.stations_filename) == False:

            # read Annotation_basis table from mwlist.org
            self.SigRelay.emit("cexex_annotate",["annotatestatusdisplay","Status: read MWList table for annotation"])
            filters ="MWList files (*.xlsx)"
            selected_filter = "MWList files (*.xlsx)"
            filename=""
            if self.m["ismetadata"] == False:
                filename =  QtWidgets.QFileDialog.getOpenFileName(self.m["QTMAINWINDOWparent"],
                                                                    "Open new stations list (e.g. MWList) file"
                                                                    , self.m["standardpath"], filters, selected_filter)
            else:
                #print('open file with last path')
                if "last_MWlist" in self.m["metadata"]:
                    filters =  "MWList files (*.xlsx)"
                    selected_filter = filters
                    filename =  QtWidgets.QFileDialog.getOpenFileName(self.m["QTMAINWINDOWparent"],
                                                                    "Open stations list (e.g. MWList) file (last used is selected)"
                                                                    ,self.m["metadata"]["last_MWlist"] , filters, selected_filter)
                else:
                    filename =  QtWidgets.QFileDialog.getOpenFileName(self.m["QTMAINWINDOWparent"],
                                                    "Open new stations list (e.g. MWList) file"
                                                    , self.m["standardpath"], filters, selected_filter)
            if len(filename[0]) == 0:
                return False
            list_selection = filename[0]   
            self.m["metadata"]["last_MWlist"] = list_selection

            stream = open("config_wizard.yaml", "w")
            yaml.dump(self.m["metadata"], stream)
            stream.close()

            #MWlistname = self.m["standardpath"] + '\\MWLIST_Volltabelle.xlsx' ###TODO remove if checked
            MWlistname = list_selection

            #print('read MWLIST table from ' + MWlistname)
            time.sleep(0.01)
            T = self.mwlistread(MWlistname)
            # @auxi.waiting_effect
            # T = pd.read_excel(MWlistname)

            #print("generate annotation basis")
            #self.gui.label.setText("Status: Generate annotation basis") ###################
            self.SigRelay.emit("cexex_annotate",["annotatestatusdisplay","Status: Generate annotation basis"])

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
            self.SigRelay.emit("cexex_annotate",["annotatestatusdisplay","Status: annotate peaks and write stations list to yaml file"])
            #start generation of stations list as a separate thread
            starttime = self.m["wavheader"]['starttime']
            stoptime = self.m["wavheader"]['stoptime']
            self.rectime = datetime(starttime[0],starttime[1],starttime[3],starttime[4],starttime[5],starttime[6])
            self.recstop = datetime(stoptime[0],stoptime[1],stoptime[3],stoptime[4],stoptime[5],stoptime[6]) #TODO: seems to be unused
            #self.m["scan_completed_ref"]()
            self.statlst_genthread = QThread()
            self.statlst_geninst = statlst_gen_worker(self)
            self.statlst_geninst.moveToThread(self.statlst_genthread)
            self.statlst_geninst.set_continue(True)
            self.statlst_geninst.set_T(T)
            self.statlst_geninst.set_freq(freq)
            self.statlst_geninst.set_closed(closed)
            self.statlst_geninst.set_stations_filename(self.stations_filename)
            self.statlst_geninst.set_locs_union(self.locs_union)
            self.statlst_geninst.set_rectime(self.rectime)
            self.statlst_geninst.set_stichtag(self.STICHTAG)
            self.statlst_geninst.set_annotation(self.annotation)
            self.statlst_geninst.set_status_filename(self.m["status_filename"])
            self.statlst_genthread.started.connect(self.statlst_geninst.stationsloop)
            self.statlst_geninst.SigProgressBar.connect(self.m["Progressbarupdate2_ref"])  #TODO: unsaubere Lösung; controller funs should not access GUI functions
            self.statlst_geninst.SigFinished.connect(self.m["scan_completed_ref"])  #TODO: unsaubere Lösung; controller funs should not access GUI functions
            self.statlst_geninst.SigFinished.connect(self.statlst_genthread.quit)
            self.statlst_geninst.SigFinished.connect(lambda: print("statlst_geninst is being terminated###############!!!!!!!!!!!!!!!!#######################!!!!!!!!!!!!!!!!!!!!!!!!#################"))
            self.statlst_geninst.SigFinished.connect(self.statlst_geninst.deleteLater)
            self.statlst_genthread.finished.connect(self.statlst_genthread.deleteLater)
            self.statlst_genthread.start()
            if self.statlst_genthread.isRunning():
                self.statlst_genthreadActive = True
            pass

    #    self.merge2G_thread.started.connect(self.merge2G_worker.merge2G_worker)
    #     #self.merge2G_worker.SigPupdate.connect(lambda: resample_v.updateprogress_resampling(self)) #TODO: check if lambda call is appropriate.
    #     self.merge2G_worker.SigPupdate.connect(self.PupdateSignalHandler)
    #     self.merge2G_worker.SigFinishedmerge2G.connect(self.merge2G_thread.quit)
    #     self.merge2G_worker.SigFinishedmerge2G.connect(self.merge2G_worker.deleteLater)
    #     self.merge2G_thread.finished.connect(self.merge2G_thread.deleteLater)
    #     self.merge2G_thread.finished.connect(lambda: self.merge2G_cleanup(input_file_list))


        else:
            self.m["scan_completed_ref"]()  #TODO: unsaubere Lösung; controller funs should not access GUI functions
            try:
                stream = open(self.m["status_filename"], "r")
                status = yaml.safe_load(stream)
                stream.close()
            except:
                #print("cannot get status")
                return False 
            if status["annotated"] == True:
                self.m["scan_completed_ref"]()  #TODO: unsaubere Lösung; controller funs should not access GUI functions
            else:
                freq_ix = status["freqindex"]
                try:
                    stream = open(self.stations_filename, "r", encoding="utf8")
                    self.stations = yaml.safe_load(stream)
                    stream.close()
                except:
                    print("cannot get stations list")
                    return False
                ######################################## GUI UPDATE AND GUI RESET RELAY ##############################################################################################
                #self.gui.labelFrequency.setText('Frequency: ' + str(self.stations[freq_ix]['frequency'] + ' kHz'))
                self.SigRelay.emit("cexex_annotate",["labelFrequencySetText",'Frequency: ' + str(self.stations[freq_ix]['frequency'] + ' kHz')])
                self.SigRelay.emit("cexex_annotate",["reset_GUI",0])
                # self.gui.lineEdit.setFont(QFont('MS Shell Dlg 2', 12))
                # self.gui.lineEdit.setText('')
                # self.gui.lineEdit_TX_Site.setText('')
                # self.gui.lineEdit_Country.setText('')
                # self.gui.lineEdit.setStyleSheet("background-color : white")
                # self.gui.lineEdit.setFont(QFont('MS Shell Dlg 2', 12))
            self.SigRelay.emit("cexex_annotate",["pushButtonENTERdisable",0])
            #self.gui.pushButtonENTER.setEnabled(False)
                #######################################################################################################################################
            self.SigRelay.emit("cexex_annotate",["interactive_station_select",0])
            #self.interactive_station_select()


    def enterlinetoannotation(self):
        """
        CONTROLLER
        read yaml stations_list.yaml

        """
        #self.gui.lineEdit.setEnabled(False)
        #print('Editline copy to metadata file')
        #self.gui.pushButtonENTER.setEnabled(False) ##############################################################################################
        self.SigRelay.emit("cexex_annotate",["pushButtonENTERdisable",0])
        try:
            stream = open(self.m["status_filename"], "r")
            status = yaml.safe_load(stream)
            stream.close()
        except:
            #print("cannot get status")
            return False
        
        freq_ix = status["freqindex"]
        programstr = self.gui.lineEdit.text() ##############################################################################################
        txstr = self.gui.lineEdit_TX_Site.text() ##############################################################################################
        countrystr = self.gui.lineEdit_Country.text() ##############################################################################################

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
        stream = open(self.m["status_filename"], "w")
        yaml.dump(status, stream)
        stream.close()
        self.gui.progressBar_2.setProperty("value", (freq_ix + 1)/len(self.stations)*100) ##############################################################################################
        self.gui.Annotate_listWidget.clear() ##############################################################################################
        self.SigRelay.emit("cexex_annotate",["interactive_station_select",0])
        #self.interactive_station_select()

    def discard_annot_line(self):
        """
        CONTROLLER
        read yaml stations_list.yaml

        """
        print("discard reached")
        try:
            stream = open(self.m["status_filename"], "r")
            status = yaml.safe_load(stream)
            stream.close()
        except:
            print("discard cannot write to yaml")
            return False 
        freq_ix = status["freqindex"] # read last frequency index which was treated in interactive list checking
        #Discard this frequency, advance freq counter, do not write to cohiradia annotation
        freq_ix += 1
        status["freqindex"] = freq_ix
        status["annotated"] = False
        stream = open(self.m["status_filename"], "w")
        yaml.dump(status, stream)
        stream.close()
        #self.interactive_station_select()
        self.SigRelay.emit("cexex_annotate",["interactive_station_select",0])
        self.gui.progressBar_2.setProperty("value", (freq_ix + 1)/len(self.stations)*100) ##############################################################################################
        return False


class annotate_v(QObject):
    """_view methods for resampling module
    TODO: gui.wavheader --> something less general ?
    """
    __slots__ = ["viewvars"]

    SigAny = pyqtSignal()
    SigCancel = pyqtSignal()
    SigUpdateGUI = pyqtSignal(object)
    SigSyncGUIUpdatelist = pyqtSignal(object)
    SigRelay = pyqtSignal(str,object)

    def __init__(self, gui, annotate_c, annotate_m):
        super().__init__()

        #viewvars = {}
        #self.set_viewvars(viewvars)
        self.m = annotate_m.mdl
        self.annotate_c = annotate_c
        self.gui = gui #gui_state["gui_reference"]#self.m["gui_reference"]
        self.logger = annotate_m.logger
        self.annotate_c.SigRelay.connect(self.rxhandler)
        self.init_annotate_ui()
        self.annotate_c.SigRelay.connect(self.SigRelay.emit)
        self.NUMSNAPS = 5 #number of segments evaluated for annotation 
        self.STICHTAG = datetime(2023,2,25,0,0,0) #TODO: only used in stationsloop of statslist_gen_worker as self.host.STICHTAG, Move to module annotation
        self.autoscanthreadActive = False
        self.m["scan_completed_ref"] = self.scan_completed
        self.m["Progressbarupdate_ref"] = self.Progressbarupdate
        self.m["Progressbarupdate2_ref"] = self.Progressbarupdate2

    def init_annotate_ui(self):
        #preset ui elements of annotator
        self.gui.pushButtonAnnotate.setFont(QFont('MS Shell Dlg 2', 12))
        self.gui.pushButtonAnnotate.setStyleSheet("background-color : rgb(220, 220, 220)")
        self.gui.pushButtonAnnotate.setEnabled(False)
        self.gui.pushButton_Scan.setFont(QFont('MS Shell Dlg 2', 12))
        self.gui.pushButton_Scan.setStyleSheet("background-color : rgb(220, 220, 220)")
        self.gui.pushButton_Scan.setEnabled(False)
        self.gui.lineEdit.setText('')
        self.gui.lineEdit.setAlignment(QtCore.Qt.AlignLeft)
        self.gui.lineEdit_TX_Site.setText('')
        self.gui.lineEdit_Country.setText('')
        self.gui.label_Filename_Annotate.setText('')
        self.gui.pushButtonDiscard.setEnabled(False)
        self.gui.lineEdit.setStyleSheet("background-color : white")
        self.gui.lineEdit.setFont(QFont('MS Shell Dlg 2', 12))
        self.gui.tab_annotate.setEnabled(True) 
        self.gui.pushButtonENTER.setEnabled(False)
        self.gui.progressBar_2.setProperty("value", 0)
        self.gui.Annotate_listWidget.clear()
        self.m["baselineoffset"] = self.gui.spinBoxminBaselineoffset.value()  ##########TODO: introduce separate GUI element because this one belongs to view_spectra
        self.m["NumScan"] = self.gui.spinBoxNumScan.value()
        self.m["minSNR"] = self.gui.spinBoxminSNR.value()

        #connect ui element events with annotator methods
        self.gui.pushButton_Scan.clicked.connect(self.annotate_c.autoscan)
        self.gui.pushButtonAnnotate.clicked.connect(self.annotate_c.ann_stations) 
        self.gui.pushButtonDiscard.clicked.connect(self.discard_annot_line)
        self.gui.spinBoxminSNR.valueChanged.connect(self.minSNRupdate) 
        self.gui.pushButtonENTER.clicked.connect(self.enterlinetoannotation)
        self.gui.Annotate_listWidget.itemClicked.connect(self.cb_ListClicked)
        self.gui.spinBoxNumScan.valueChanged.connect(self.cb_numscanchange) 
        self.gui.spinBoxminSNR.valueChanged.connect(self.cb_minSNRchange) 
        #self.gui.lineEdit.returnPressed.connect(self.enterlinetoannotation)
        #self.gui.pushButton_ScanAnn.clicked.connect(self.listclick_test)

                
        #TODO: reade info on spinbox settings MF kernel etc from status file if it exists
        #self.gui.spinBoxKernelwidth.setProperty("value", 15)
        #self.gui.spinBoxNumScan.setProperty("value", 10)
        #self.gui.spinBoxminBaselineoffset.setProperty("value", 5)

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
#        print(f"####################annotate rxhandler: key: {_key}, value: {_value}")
        if _key.find("cm_annotate") == 0 or _key.find("cm_all_") == 0:
            #set mdl-value
            self.m[_value[0]] = _value[1]
        if _key.find("cui_annotate") == 0:
            _value[0](*_value[1])
        if _key.find("cexex_annotate") == 0  or _key.find("cexex_all_") == 0:
            if  _value[0].find("updateGUIelements") == 0:
                self.updateGUIelements()
            if  _value[0].find("reset_GUI") == 0:
                self.reset_GUI()
            if  _value[0].find("getGUIvalues") == 0:
                self.getGUIvalues()
            if  _value[0].find("connect_autoscan") == 0:
                self.connect_autoscan()
            if  _value[0].find("annotatestatusdisplay") == 0:
                self.annotatestatusdisplay(_value[1])
            if  _value[0].find("interactive_station_select") == 0:
                self.interactive_station_select()
            if  _value[0].find("labelFrequencySetText") == 0:
                self.gui.labelFrequency.setText(_value[1])
            if  _value[0].find("pushButtonENTERdisable") == 0:
                self.gui.pushButtonENTER.setEnabled(False)
            if  _value[0].find("annotation_deactivate") == 0:
                self.annotation_deactivate()
            if  _value[0].find("scan_deactivate") == 0:
                self.scan_deactivate()
            #handle method
            # if  _value[0].find("plot_spectrum") == 0: #EXAMPLE
            #     self.plot_spectrum(0,_value[1])   #EXAMPLE
                
    def annotatestatusdisplay(self,dispstring):
        self.gui.label.setText(dispstring)

    def connect_autoscan(self):
        self.annotate_c.autoscaninst.SigFinished.connect(self.autoscan_finished)
        self.annotate_c.autoscaninst.SigProgressBar.connect(self.Progressbarupdate)
        self.annotate_c.autoscaninst.SigPlotdata.connect(self.scanplot)
        self.annotate_c.autoscaninst.SigScandeactivate.connect(self.scan_deactivate)
        self.annotate_c.autoscaninst.SigUpdateGUI.connect(self.scanupdateGUI)
        self.annotate_c.autoscaninst.SigStatustable.connect(self.status_writetableread)


    def getGUIvalues(self):
                self.m["NumScan"] = self.gui.spinBoxNumScan.value()
                self.m["minSNR"] = self.gui.spinBoxminSNR.value()


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
        print("annotate: updateGUIelements")
        #self.gui.DOSOMETHING


    def reset_GUI(self):
        self.gui.lineEdit.setFont(QFont('MS Shell Dlg 2', 12))
        self.gui.lineEdit.setText('')
        self.gui.lineEdit_TX_Site.setText('')
        self.gui.lineEdit_Country.setText('')
        self.gui.lineEdit.setStyleSheet("background-color : white")
        self.gui.lineEdit.setFont(QFont('MS Shell Dlg 2', 12))
        self.gui.Annotate_listWidget.clear()
        self.gui.pushButtonDiscard.setEnabled(False)
        self.gui.labelFrequency.setText("Freq:")
        self.annotation_deactivate()
        self.scan_deactivate()
        self.stations_filename = self.m["annotationpath"] + '/stations_list.yaml'
        if os.path.exists(self.stations_filename) == True:
            self.scan_completed()
            try:
                stream = open(self.status_filename, "r")
                status = yaml.safe_load(stream)
                stream.close()
            except:
                print("cannot get status")
                return False 
            if status["annotated"] == True:
                self.annotation_completed()
                self.ui.pushButton_Writeyamlheader.setEnabled(True)
            else:
                self.annotation_activate()
        else:
            self.scan_activate()



        pass

    def cb_numscanchange(self):
        self.m["NumScan"] = self.gui.spinBoxNumScan.value()

    def cb_minSNRchange(self):
        self.m["minSNR"] = self.gui.spinBoxminSNR.value()

    def annotation_completed(self):
        """_summary_
        VIEW, gehört zum Tab Annotate
        """
        self.gui.pushButtonAnnotate.setStyleSheet("background-color : rgb(170, 255, 127)")
        self.gui.pushButtonAnnotate.setEnabled(False)
        self.gui.pushButtonAnnotate.setFont(QFont('MS Shell Dlg 2', 12))
        self.gui.pushButtonDiscard.setEnabled(False)
        self.gui.progressBar_2.setProperty("value", 100)
        self.gui.lineEdit.setText('Record has already been annotated. For re-annotation delete annotation folder')
        self.gui.lineEdit.setStyleSheet("background-color : yellow")
        self.gui.lineEdit.setFont(QFont('MS Shell Dlg 2', 12))
        self.gui.pushButton_Writeyamlheader.setEnabled(True)
        self.flag_ann_completed = True

    def annotation_activate(self):
        """_summary_
        VIEW, gehört zum Tab Annotate
        """
        self.gui.pushButtonAnnotate.setStyleSheet("background-color : rgb(220,220,220)")
        self.gui.pushButtonAnnotate.setEnabled(True)
        self.gui.pushButtonAnnotate.setFont(QFont('MS Shell Dlg 2', 12))
        self.gui.pushButtonDiscard.setEnabled(False)
        self.gui.lineEdit.setText('annotation can be started or continued')
        self.gui.lineEdit.setStyleSheet("background-color : yellow")
        self.gui.lineEdit.setFont(QFont('MS Shell Dlg 2', 12))

    def annotation_deactivate(self):
        """_summary_
        VIEW, gehört zum Tab Annotate
        """        
        self.gui.pushButtonAnnotate.setStyleSheet("background-color : rgb(220,220,220)")
        self.gui.pushButtonAnnotate.setEnabled(False)
        self.gui.pushButtonAnnotate.setFont(QFont('MS Shell Dlg 2', 12))

    def scan_completed(self):
        """_summary_
        VIEW, gehört zum Tab Annotate
        """
        self.gui.pushButton_Scan.setStyleSheet("background-color : rgb(170, 255, 127)")
        self.gui.pushButton_Scan.setFont(QFont('MS Shell Dlg 2', 12))
        self.gui.pushButton_Scan.setEnabled(False)
        self.gui.pushButtonAnnotate.setEnabled(True)
        self.gui.pushButtonAnnotate.setFont(QFont('MS Shell Dlg 2', 12))
        self.gui.lineEdit.setText('autoscan has been completed, peaks and SNRs identified')
        self.gui.lineEdit.setStyleSheet("background-color : yellow")
        self.gui.lineEdit.setFont(QFont('MS Shell Dlg 2', 12))
        #TODO: save settings for MF Kernel, SNR baselineoffset min peak width min peak distance to status file
        #TODO: write spinbox values to status file
        peakwidth = self.gui.spinBoxminPeakwidth.value()
        filterkernel = self.gui.spinBoxKernelwidth.value()
        self.m["baselineoffset"] = self.gui.spinBoxminBaselineoffset.value()  ##########TODO: introduce separate GUI element because this one belongs to view_spectra
        minSNR = self.gui.spinBoxminSNR_ScannerTab.value()
        minPeakDist = self.gui.spinBoxminPeakDistance.value()
        self.m["NumScan"] = self.gui.spinBoxNumScan.value()
        try:
            stream = open(self.m["status_filename"], "r")
            status = yaml.safe_load(stream)
            stream.close()
            status["peakwidth"] = peakwidth
            status["filterkernel"] = filterkernel
            status["baselineoffset"] = self.m["baselineoffset"]
            status["minSNR"] = minSNR
            status["minPeakDist"] = minPeakDist
            status["NumScan"] = self.m["NumScan"]       
            stream = open(self.m["status_filename"], "w")
            yaml.dump(status, stream)
            stream.close()
        except:
            #print("cannot get/put status")
            self.logger.error("scan_completed: cannot get/put status")

    def scan_activate(self):
        """_summary_
        VIEW, gehört zum Tab Annotate
        """
        self.gui.pushButton_Scan.setStyleSheet("background-color : rgb(220,220,220)")
        self.gui.pushButton_Scan.setFont(QFont('MS Shell Dlg 2', 12))
        self.gui.pushButton_Scan.setEnabled(True)
        self.gui.pushButtonAnnotate.setEnabled(False)
        self.gui.pushButtonAnnotate.setFont(QFont('MS Shell Dlg 2', 12))
        self.gui.lineEdit.setText('autoscan can be started (search for TX peaks and SNR values)')
        self.gui.lineEdit.setStyleSheet("background-color : yellow")
        self.gui.lineEdit.setFont(QFont('MS Shell Dlg 2', 12))

    def scan_deactivate(self):
        """_summary_
        VIEW, gehört zum Tab Annotate
        """
        self.gui.pushButton_Scan.setStyleSheet("background-color : rgb(220,220,220)")
        self.gui.pushButton_Scan.setFont(QFont('MS Shell Dlg 2', 12))
        self.gui.pushButton_Scan.setEnabled(False)
        self.gui.lineEdit.setText('')
        self.gui.lineEdit_TX_Site.setText('')
        self.gui.lineEdit_Country.setText('')
        self.gui.lineEdit.setStyleSheet("background-color : white")
        self.gui.lineEdit.setFont(QFont('MS Shell Dlg 2', 12))

    def minSNRupdate(self):
        """_summary_
        VIEW of Annotator Module
        """
        self.m["PROMINENCE"] = self.gui.spinBoxminSNR.value()
        self.gui.spinBoxminSNR_ScannerTab.setProperty("value", self.m["PROMINENCE"])
        self.SigRelay.emit("cm_all_",["prominence",self.m["PROMINENCE"]])
        self.SigRelay.emit("cexex_view-spectrum",["updateGUIelements",0])
        #self.cb_plot_spectrum()
        #.cb_plot_spectrum()

    def activate_WAVEDIT(self):
        self.show()
        if self.gui.radioButton_WAVEDIT.isChecked() is True:
                    self.gui.tableWidget_basisfields.setEnabled(True)
                    self.gui.tableWidget_starttime.setEnabled(True)
                    self.gui.tableWidget_3.setEnabled(True)      
        else:
                    self.gui.tableWidget_basisfields.setEnabled(False)
                    self.gui.tableWidget_starttime.setEnabled(False)
                    self.gui.tableWidget_3.setEnabled(False)

    def scanupdateGUI(self):
        """_summary_
        VIEW
        """
        self.gui.label.setText("Status: Scan spectra for prominent TX peaks")
        self.gui.pushButton_Scan.setEnabled(False)
        self.gui.horizontalScrollBar_view_spectra.setEnabled(False)
        self.gui.lineEdit.setText('Please wait while spectra are analyzed for peaks')
        self.gui.lineEdit.setStyleSheet("background-color : yellow")
        self.gui.lineEdit.setFont(QFont('MS Shell Dlg 2', 12))

    def Progressbarupdate(self):
        """
        VIEW
        _summary_
        """
        # self.gui.progressBar_2.setProperty("value", int(self.annotate_c.autoscaninst.get_progressvalue())) ##TODO: remove after tests
        # #send continue flag to autoscan task
        # if self.autoscanthreadActive == True:
        #     self.annotate_c.autoscaninst.set_1(True)
        print("Progressbarupdate")
        self.gui.progressBar_2.setProperty("value", int(self.annotate_c.autoscaninst.get_progressvalue()))
        #send continue flag to autoscan task
        if self.annotate_c.autoscanthreadActive == True:
            self.annotate_c.autoscaninst.set_continue(True)

    def Progressbarupdate2(self):
        """
        VIEW
        _summary_
        """
        # self.gui.progressBar_2.setProperty("value", int(self.annotate_c.autoscaninst.get_progressvalue())) ##TODO: remove after tests
        # #send continue flag to autoscan task
        # if self.autoscanthreadActive == True:
        #     self.annotate_c.autoscaninst.set_1(True)
        print("Progressbarupdate 2 222222222222222")
        self.gui.progressBar_2.setProperty("value", int(self.annotate_c.statlst_geninst.get_progressvalue()))
        #send continue flag to autoscan task
        if self.annotate_c.statlst_genthreadActive == True:
            self.annotate_c.statlst_geninst.set_continue(True)

    def status_writetableread(self):
        """
        VIEW
        _summary_
        """
        self.gui.progressBar_2.setProperty("value", int(0))
        self.gui.label.setText("Status: read MWList table for annotation")
        #send continue flag to autoscan task
        if self.autoscanthreadActive == True:
            self.annotate_c.autoscaninst.set_continue(True)

    def autoscan_finished(self):
        """
        VIEW
        _summary_
        """
        self.gui.horizontalScrollBar_view_spectra.setEnabled(True)
        self.gui.lineEdit.setText('')
        self.gui.lineEdit_TX_Site.setText('')
        self.gui.lineEdit_Country.setText('')
        self.gui.lineEdit.setStyleSheet("background-color : white")
        self.gui.lineEdit.setFont(QFont('MS Shell Dlg 2', 12))
        self.autoscanthreadActive = True
        if self.gui.radioButton_plotpreview.isChecked() is True:
            plt.close()

    def scanplot(self):
        """
        VIEW
        _summary_
        """
        #TODO: only execute if Preview_plot == True   radioButton_plotpreview
        if self.gui.radioButton_plotpreview.isChecked() is True:
            plt.close()
            plt.cla()
            pdata = self.autoscaninst.get_pdata()
            #pdata = autoscan_ret[2]
            #self.__slots__[0][2] = pdata
            plt.plot(pdata["datax"],pdata["datay"])
            plt.xlabel("frequency (Hz)")
            plt.ylabel("peak amplitude (dB)")
            plt.show()
            plt.pause(1)
        #send continue flag to autoscan task
        if self.autoscanthreadActive == True:
            self.annotate_c.autoscaninst.set_continue(True)

#########################????????????????????????####################

        # self.autoscanthread = QThread()
        # self.autoscaninst = autoscan_worker(self)
        # self.autoscaninst.moveToThread(self.autoscanthread)
        # #TODO: Implement further slot communicationa shown here
        # self.autoscaninst.set_0([self.m["Numscan"],self.gui.spinBoxminSNR.value(),[]])


        self.gui.tab_view_spectra.setEnabled(True)
        self.gui.label_8.setEnabled(False)
        self.gui.label_36.setText('READY')
        self.gui.label_36.setFont(QFont('arial',12))
        self.gui.label_36.setStyleSheet("background-color: lightgray")



############################## TAB ANNOTATE ####################################



    def scanupdateGUI(self):
        """_summary_
        VIEW
        """
        self.gui.label.setText("Status: Scan spectra for prominent TX peaks")
        self.gui.pushButton_Scan.setEnabled(False)
        self.gui.horizontalScrollBar_view_spectra.setEnabled(False)
        self.gui.lineEdit.setText('Please wait while spectra are analyzed for peaks')
        self.gui.lineEdit.setStyleSheet("background-color : yellow")
        self.gui.lineEdit.setFont(QFont('MS Shell Dlg 2', 12))

            
    def status_writetableread(self):
        """
        VIEW
        _summary_
        """
        self.gui.progressBar_2.setProperty("value", int(0))
        self.gui.label.setText("Status: read MWList table for annotation")
        #send continue flag to autoscan task
        if self.autoscanthreadActive == True:
            self.annotate_c.autoscaninst.set_continue(True)

    def autoscan_finished(self):
        """
        VIEW
        _summary_
        """
        self.gui.horizontalScrollBar_view_spectra.setEnabled(True)
        self.gui.lineEdit.setText('')
        self.gui.lineEdit_TX_Site.setText('')
        self.gui.lineEdit_Country.setText('')
        self.gui.lineEdit.setStyleSheet("background-color : white")
        self.gui.lineEdit.setFont(QFont('MS Shell Dlg 2', 12))
        self.autoscanthreadActive = True
        if self.gui.radioButton_plotpreview.isChecked() is True:
            plt.close()


    def scanplot(self):
        """
        VIEW
        _summary_
        """
        #TODO: only execute if Preview_plot == True   radioButton_plotpreview
        if self.gui.radioButton_plotpreview.isChecked() is True:
            plt.close()
            plt.cla()
            autoscan_ret = self.annotate_c.autoscaninst.get_GUI_parameters()
            pdata = autoscan_ret[2]
            #self.__slots__[0][2] = pdata
            plt.plot(pdata["datax"],pdata["datay"])
            plt.xlabel("frequency (Hz)")
            plt.ylabel("peak amplitude (dB)")
            plt.show()
            plt.pause(1)
        #send continue flag to autoscan task
        if self.autoscanthreadActive == True:
            self.annotate_c.autoscaninst.set_continue(True)

    #@njit
    def interactive_station_select(self):  #TODO: move to annotation module
        """
        TODO: write text
        read yaml stations_list.yaml

        """
        print("interactive station select annotator module")
        self.gui.Annotate_listWidget.clear()
        self.gui.lineEdit.setText('')
        self.gui.lineEdit_TX_Site.setText('')
        self.gui.lineEdit_Country.setText('')
        ### reading again the yaml is inefficient: could be passed from ann_stations
        try:
            stream = open(self.m["status_filename"], "r")
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
            stream = open(self.m["status_filename"], "w")
            yaml.dump(status, stream)
            stream.close()
            return False
        plen = int((len(self.stations[freq_ix])-2)/3) #number of station candidates
        self.gui.labelFrequency.setText('f: ' + str(self.stations[freq_ix]['frequency'] + ' kHz'))
        self.gui.progressBar_2.setProperty("value", freq_ix/len(self.stations)*100)
        #self.gui.lineEdit.setText('Frequency: ' + str(self.stations[freq_ix]['frequency'] + ' kHz'))
        time.sleep(0.01)
        
        for ix2 in range(plen):
            country_string = self.stations[freq_ix]['country' + str(ix2)]
            programme_string = self.stations[freq_ix]['programme' + str(ix2)]
            tx_site_string = self.stations[freq_ix]['tx-site' + str(ix2)]
            item = QtWidgets.QListWidgetItem()
            self.gui.Annotate_listWidget.addItem(item)
            item = self.gui.Annotate_listWidget.item(ix2)
            item.setText(country_string.strip('\n') + ' | ' + programme_string.strip('\n') + ' | ' + tx_site_string.strip('\n'))
            time.sleep(0.01)
        #add dummy line in list for selecting own entry
        # item = QtWidgets.QListWidgetItem()
        # self.gui.Annotate_listWidget.addItem(item)
        # item = self.gui.Annotate_listWidget.item(ix2+1)
        # dum_cstr = 'OTHER COUNTRY, Please enter manually'
        # dum_pstr = 'OTHER STATION, Please enter manually'
        # dum_txstr = 'OTHER TX SITE, Please enter manually'
        # item.setText(dum_cstr.strip('\n') + ' | ' + dum_pstr.strip('\n') + ' | ' + dum_txstr.strip('\n'))
        # time.sleep(0.01)
        self.gui.pushButtonDiscard.setEnabled(True)


    def cb_ListClicked(self,item):
        """
        CONTROLLER
        read yaml stations_list.yaml

        """
        #memorize status and advance freq_ix
        print("list clicked annotator module")
        try:
            stream = open(self.m["status_filename"], "r")
            status = yaml.safe_load(stream)
            stream.close()
        except:
            #print("cannot get status")
            return False 
        freq_ix = status["freqindex"] # read last frequency index which was treated in interactive list checking
        if freq_ix < len(self.stations):
            #read index of clicked row and fetch associated content from stations list
            cr_ix = self.gui.Annotate_listWidget.currentRow()
            Ecountry_string = self.stations[freq_ix]['country' + str(cr_ix)]
            Eprogramme_string = self.stations[freq_ix]['programme' + str(cr_ix)]
            Etx_site_string = self.stations[freq_ix]['tx-site' + str(cr_ix)]
            self.gui.labelFrequency.setText('f: ' + str(self.stations[freq_ix]['frequency']) + ' kHz')

            self.gui.lineEdit.setText(Eprogramme_string)
            self.gui.lineEdit.setAlignment(QtCore.Qt.AlignLeft)
            self.gui.lineEdit.home(True)
            self.gui.lineEdit_TX_Site.setText(Etx_site_string)
            self.gui.lineEdit_TX_Site.setAlignment(QtCore.Qt.AlignLeft)
            self.gui.lineEdit_TX_Site.home(True)
            self.gui.lineEdit_Country.setText(Ecountry_string)
            self.gui.lineEdit_Country.setAlignment(QtCore.Qt.AlignLeft)
            self.gui.lineEdit_Country.home(True)
            self.current_freq_ix = freq_ix

        # end of stationslist reached
            self.gui.pushButtonENTER.setEnabled(True)
        else:
            status["freqindex"] = freq_ix
            status["annotated"] = True
            stream = open(self.m["status_filename"], "w")
            yaml.dump(status, stream)
            stream.close()
            self.gui.progressBar_2.setProperty("value", 100)
            self.annotation_completed()

    def enterlinetoannotation(self):
        """
        CONTROLLER
        read yaml stations_list.yaml

        """
        #self.gui.lineEdit.setEnabled(False)
        print('Editline copy to metadata file, module annotator')
        self.gui.pushButtonENTER.setEnabled(False)
        try:
            stream = open(self.m["status_filename"], "r")
            status = yaml.safe_load(stream)
            stream.close()
        except:
            print("enterlineannotation cannot get status")
            return False
        
        freq_ix = status["freqindex"]
        programstr = self.gui.lineEdit.text()
        txstr = self.gui.lineEdit_TX_Site.text()
        countrystr = self.gui.lineEdit_Country.text()

        country_string = '  country: "{}"\n'.format(countrystr)
        programme_string = '  programme: "{}"\n'.format(programstr)
        tx_site_string = '  tx-site: "{}"\n'.format(txstr)
        freq_ix = self.current_freq_ix
        with open(self.m["cohiradia_metadata_filename"], 'a+', encoding='utf-8') as f:
            f.write('- frequency: "{}"\n'.format(self.stations[freq_ix]['frequency']))
            f.write('  snr: "{}"\n'.format(self.stations[freq_ix]['snr']))
            f.write(country_string)
            f.write(programme_string)
            f.write(tx_site_string)
        freq_ix += 1
        status["freqindex"] = freq_ix
        status["annotated"] = False
        stream = open(self.m["status_filename"], "w")
        yaml.dump(status, stream)
        stream.close()
        #print(f"forward progressbar enterline_annotation, value: {(freq_ix + 1)/len(self.stations)*100}")
        #self.gui.progressBar_2.setProperty("value", (freq_ix + 1)/len(self.stations)*100)
        self.gui.Annotate_listWidget.clear()
        self.interactive_station_select()

    def discard_annot_line(self):
        """
        CONTROLLER
        read yaml stations_list.yaml

        """
        print("DISCARD annotatemodule")
        try:
            stream = open(self.m["status_filename"], "r")
            status = yaml.safe_load(stream)
            stream.close()
        except:
            print("stream not iopened DISCARD annotatemodule")
            return False 
        freq_ix = status["freqindex"] # read last frequency index which was treated in interactive list checking
        #Discard this frequency, advance freq counter, do not write to cohiradia annotation
        freq_ix += 1
        status["freqindex"] = freq_ix
        status["annotated"] = False
        stream = open(self.m["status_filename"], "w")
        yaml.dump(status, stream)
        stream.close()
        self.interactive_station_select()
        #print(f"forward progressbar discard annot line , value: {(freq_ix + 1)/len(self.stations)*100}")
        #self.gui.progressBar_2.setProperty("value", (freq_ix + 1)/len(self.stations)*100)
        return False

    def interactive_station_select(self):  #TODO: move to annotation module
        """
        CONTROLLER
        read yaml stations_list.yaml

        """
        print("interactive station_select annotater module")
        self.gui.Annotate_listWidget.clear()
        self.gui.lineEdit.setText('')
        self.gui.lineEdit_TX_Site.setText('')
        self.gui.lineEdit_Country.setText('')
        ### reading again the yaml is inefficient: could be passed from ann_stations
        try:
            stream = open(self.m["status_filename"], "r")
            status = yaml.safe_load(stream)
            stream.close()
        except:
            print("interactive stats loop cannot get status. module annotate")
            return False 
        try:
            stream = open(self.m["stations_filename"], "r", encoding="utf8")
            self.stations = yaml.safe_load(stream)
            stream.close()
        except:
            print("interactive stats loop cannot get stations list, module annotator")
            return False
        
        freq_ix = status["freqindex"] # read last frequency index which was treated in interactive list checking
        if freq_ix >= len(self.stations):
            self.annotation_completed()
            status["annotated"] = True
            stream = open(self.m["status_filename"], "w")
            yaml.dump(status, stream)
            stream.close()
            print("interactive stats loop, freq ix > len, module annotator")
            return False
        plen = int((len(self.stations[freq_ix])-2)/3) #number of station candidates
        self.gui.labelFrequency.setText('f: ' + str(self.stations[freq_ix]['frequency'] + ' kHz'))
        print(f"forward progressbar interactive stations select, value: {freq_ix/len(self.stations)*100}")
        self.gui.progressBar_2.setProperty("value", freq_ix/len(self.stations)*100)
        #self.gui.lineEdit.setText('Frequency: ' + str(self.stations[freq_ix]['frequency'] + ' kHz'))
        time.sleep(0.01)
        
        for ix2 in range(plen):
            country_string = self.stations[freq_ix]['country' + str(ix2)]
            programme_string = self.stations[freq_ix]['programme' + str(ix2)]
            tx_site_string = self.stations[freq_ix]['tx-site' + str(ix2)]
            item = QtWidgets.QListWidgetItem()
            self.gui.Annotate_listWidget.addItem(item)
            item = self.gui.Annotate_listWidget.item(ix2)
            item.setText(country_string.strip('\n') + ' | ' + programme_string.strip('\n') + ' | ' + tx_site_string.strip('\n'))
            time.sleep(0.01)
        #add dummy line in list for selecting own entry
        # item = QtWidgets.QListWidgetItem()
        # self.gui.Annotate_listWidget.addItem(item)
        # item = self.gui.Annotate_listWidget.item(ix2+1)
        # dum_cstr = 'OTHER COUNTRY, Please enter manually'
        # dum_pstr = 'OTHER STATION, Please enter manually'
        # dum_txstr = 'OTHER TX SITE, Please enter manually'
        # item.setText(dum_cstr.strip('\n') + ' | ' + dum_pstr.strip('\n') + ' | ' + dum_txstr.strip('\n'))
        # time.sleep(0.01)
        self.gui.pushButtonDiscard.setEnabled(True)


    def cb_ListClicked(self,item):
        """
        VIEW OR CONTROLLER ???
        read yaml stations_list.yaml

        """
        #memorize status and advance freq_ix
        print("LIST CLICKED module annotator")
        try:
            stream = open(self.m["status_filename"], "r")
            status = yaml.safe_load(stream)
            stream.close()
        except:
            print("LIST clicked, cannot get status, module annotate")
            return False 
        freq_ix = status["freqindex"] # read last frequency index which was treated in interactive list checking
        if freq_ix < len(self.stations):
            #read index of clicked row and fetch associated content from stations list
            cr_ix = self.gui.Annotate_listWidget.currentRow()
            Ecountry_string = self.stations[freq_ix]['country' + str(cr_ix)]
            Eprogramme_string = self.stations[freq_ix]['programme' + str(cr_ix)]
            Etx_site_string = self.stations[freq_ix]['tx-site' + str(cr_ix)]
            self.gui.labelFrequency.setText('f: ' + str(self.stations[freq_ix]['frequency']) + ' kHz')

            self.gui.lineEdit.setText(Eprogramme_string)
            self.gui.lineEdit.setAlignment(QtCore.Qt.AlignLeft)
            self.gui.lineEdit.home(True)
            self.gui.lineEdit_TX_Site.setText(Etx_site_string)
            self.gui.lineEdit_TX_Site.setAlignment(QtCore.Qt.AlignLeft)
            self.gui.lineEdit_TX_Site.home(True)
            self.gui.lineEdit_Country.setText(Ecountry_string)
            self.gui.lineEdit_Country.setAlignment(QtCore.Qt.AlignLeft)
            self.gui.lineEdit_Country.home(True)
            self.current_freq_ix = freq_ix
        # end of stationslist reached
            self.gui.pushButtonENTER.setEnabled(True)
        else:
            status["freqindex"] = freq_ix
            status["annotated"] = True
            stream = open(self.m["status_filename"], "w")
            yaml.dump(status, stream)
            stream.close()
            self.gui.progressBar_2.setProperty("value", 100)
            self.annotation_completed()

