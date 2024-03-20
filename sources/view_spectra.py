import numpy as np
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5 import QtGui
from scipy import signal as sig
from scipy.ndimage.filters import median_filter
#from SDR_wavheadertools_v2 import WAVheader_tools
from auxiliaries import WAVheader_tools
import time
from auxiliaries import auxiliaries as auxi
import logging

class view_spectra_m(QObject):
    __slots__ = ["None"]
    SigModelXXX = pyqtSignal()

    #TODO: replace all gui by respective state references if appropriate
    def __init__(self):
        super().__init__()
        # Constants
        self.CONST_SAMPLE = 0 # sample constant
        self.mdl = {}
        self.mdl["_log"] = False
        self.mdl["sample"] = 0
        self.mdl["resampling_gain"] = 0
        self.mdl["my_filename"] = ""
        self.mdl["ext"] = ""
        self.mdl["deltaf"] = 5000 #minimum peak distance in Hz for peak detector #TODO:occurs in ann-module; values also used in spectrum view; ; must be shifted to the respective modules in future
        self.mdl["peakwidth"] = 10 # minimum peak width in Hz for peak detector #TODO:occurs in ann-module; values also used in spectrum view; ; must be shifted to the respective modules in future
        self.mdl["prominence"] = 15 # minimum peak prominence in dB above baseline for peak detector #TODO:occurs in ann-module; values also used in spectrum view; ; must be shifted to the respective modules in future
        #self.mdl["FILTERKERNEL"] =15 # length of the moving median filter kernel in % of the spectral span #TODO:occurs in ann-module; values also used in spectrum view; ; must be shifted to the respective modules in future
        self.mdl["filterkernel"] = 15
        self.mdl["baselineoffset"] = 0
        self.mdl["position"] = 0

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

        self.logger.debug('Init logger in view_spectra reached')

class view_spectra_c(QObject):
    """_view methods for resampling module
    TODO: gui.wavheader --> something less general ?
    """
    __slots__ = ["contvars"]

    SigAny = pyqtSignal()
    SigCancel = pyqtSignal()
    #SigDisplaySpectrum = pyqtSignal(object,object)

    def __init__(self, view_spectra_m):
        super().__init__()

    # def __init__(self, *args, **kwargs): #TEST 09-01-2024
    #     super().__init__(*args, **kwargs)
        viewvars = {}
        #self.set_viewvars(viewvars)
        self.m = view_spectra_m.mdl
        self.logger = view_spectra_m.logger

class view_spectra_v(QObject):
    """_view methods for resampling module
    TODO: gui.wavheader --> something less general ?
    """
    __slots__ = ["viewvars"]

    SigAny = pyqtSignal()
    SigCancel = pyqtSignal()
    #SigUpdateGUI = pyqtSignal(object) #TODO: remove after tests
    SigSyncGUIUpdatelist = pyqtSignal(object)
    SigUpdateOtherGUIs = pyqtSignal()
    SigRX = pyqtSignal(str,object)
    SigRelay = pyqtSignal(str,object)

    def __init__(self, gui, view_spectra_c, view_spectra_m):
        super().__init__()

        #viewvars = {}
        #self.set_viewvars(viewvars)
        self.m = view_spectra_m.mdl
        self.logger = view_spectra_m.logger
        self.DATABLOCKSIZE = 1024*32
        #self.sys_state = wsys.status() #TEST: commented out 09-01-2024
        #self.sys_state = gui_state
        #system_state = self.sys_state.get_status()
        self.m["reslistdoubleemit_ix"] = False
        self.m["starttrim"] = False
        self.m["stoptrim"] = False
        self.gui = gui #gui_state["gui_reference"]#system_state["gui_reference"]
        #self.SigUpdateGUI.connect(self.update_GUI) #TODO: remove after tests
        self.SigRX.connect(self.rxhandler)
        self.init_view_spectra_ui()

    def init_view_spectra_ui(self):
        self.gui.spinBoxminPeakwidth.valueChanged.connect(self.minPeakwidthupdate)
        self.gui.spinBoxminPeakDistance.valueChanged.connect(self.minPeakDistanceupdate)
        self.gui.spinBoxminSNR_ScannerTab.valueChanged.connect(self.minSNRupdate_ScannerTab)
        self.gui.spinBoxKernelwidth.valueChanged.connect(self.setkernelwidth)
        self.gui.spinBoxKernelwidth.setEnabled(False)
        self.gui.spinBoxKernelwidth.setProperty("value", self.m["filterkernel"])
        self.gui.spinBoxminBaselineoffset.setProperty("value", 0)#TODO: avoid magic number
        self.gui.spinBoxminBaselineoffset.valueChanged.connect(self.set_baselineoffset)
        self.gui.horizontalScrollBar_view_spectra.sliderReleased.connect(self.cb_plot_spectrum)
        self.gui.radioButton_plotraw.clicked.connect(self.cb_plot_spectrum)
    #     #self.SigToolbar.connect(lambda: self.plot_spectrum(self,self.position)) #TODO Remove ???
        self.gui.spinBoxNumScan.setProperty("value", 10) #TODO: avoid magic number
        
    # def connector(self):
    #     self.SigSyncGUIUpdatelist.emit(self.updateGUIelements)

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
        #self.logger.debug("key: %s , value: %s", _key,_value)

        if _key.find("cm_view_spectra") == 0 or _key.find("cm_all_") == 0:
            #set mdl-value
            self.m[_value[0]] = _value[1]
        if _key.find("cui_view_spectra") == 0:
            _value[0](_value[1])    #TODO TODO: still unclear implementation
        if _key.find("cexex_view_spectra") == 0:
            if  _value[0].find("plot_spectrum") == 0:
                self.plot_spectrum(0,_value[1])
        if _key.find("cexex_view_spectra") == 0 or _key.find("cexex_all_") == 0:
            if  _value[0].find("plot_spectrum") == 0:
                self.plot_spectrum(0,_value[1])
                self.logger.debug("call plot spectrum")
            if  _value[0].find("updateGUIelements") == 0:
                self.updateGUIelements()
                self.logger.debug("call updateGUIelements")
            if  _value[0].find("reset_GUI") == 0:
                self.reset_GUI()


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
        #print("view spectra: updateGUIelements")

        self.logger.debug("view spectra: updateGUIelements")
        self.gui.label_Filename_ViewSpectra.setText(self.m["my_filename"] + self.m["ext"])
        dummy = 0
        self.plot_spectrum(dummy,self.m["position"])
        self.logger.debug("view spectra: emit baselineoffset %i", self.m["baselineoffset"])
        self.SigRelay.emit("cm_xcore",["baselineoffset",self.m["baselineoffset"]])

    # def update_GUI(self,_key): #TODO TODO: is this method still needed ? reorganize. gui-calls should be avoided, better only signalling and gui must call the routenes itself
    #     #print(" view spectra updateGUI: new updateGUI in view spectra module reached")

    #     self.logger.debug(" view spectra updateGUI: new updateGUI in view spectra module reached")
    #     self.SigUpdateGUI.disconnect(self.update_GUI)
    #     if _key.find("ext_update") == 0:
    #         #update resampler gui with all elements
    #         #TODO: fetch model values and re-fill all tab fields
    #         print("view_spectra update_GUI reached")
    #         pass
    #     #other key possible: "none"
    #     dummy = 0
    #     self.plot_spectrum(dummy,self.m["position"])
    #     time.sleep(0.1)
    #     self.SigUpdateGUI.connect(self.update_GUI)
    #     self.SigRelay.emit("cm_xcore",["baselineoffset",self.m["baselineoffset"]])

    def reset_GUI(self):
        #clear canvas
        self.m["Tabref"]["View_Spectra"]["ax"].clear()
        self.m["Tabref"]["View_Spectra"]["canvas"].draw()
        self.gui.label_Filename_ViewSpectra.setText("")

        pass

    def cb_plot_spectrum(self):
        position = self.gui.horizontalScrollBar_view_spectra.value()
        self.SigRelay.emit("cm_resample",["spectrum_position",position])
        self.SigRelay.emit("cm_view_spectra",["position",position])
        self.SigRelay.emit("cexex_view_spectra",["updateGUIelements",0])
        self.plot_spectrum(0,position)
        self.logger.debug("cb_plot_spectrum in module view_spectra reached")

    def plot_spectrum(self,dummy,position):
        """
        plot a segment at position 'position' of the spectrum or raw data from file f1. posiion is a fraction of the filesize between 0 and 1
        The filepath f1 must be set as self.m["f1 before in another module (typically core)
        :param : dummy
        :type : none
        :param : position
        :type : float
        :raises [ErrorType]: [ErrorDescription]
        :return: flag False or True, False on unsuccessful execution
        :rtype: Boolean
        """
        #test TODO: remove after tests
        #system_state = sys_state.get_status()
        #testirate = system_state["irate"]
        #print(f"TEST TEST TEST: plot_spectrum testirate:{testirate}")
        #sys_state.set_status(system_state)
        #print("view_spectra plot_spectum reached")
        self.logger.debug("view_spectra plot_spectum reached")
        if self.m["fileopened"] is False:
            #sys_state.set_status(system_state)
            return(False)
        else:
            #print('plot spectrum')
            self.m["horzscal"] = position
            #syncdict = ["resample", "win", "u", "horzscal", position]
            ########################################## EINZIGES VERBLEIBENDES RÄTSEL
            #zu ersetzen durch 
            #self.SigSyncTabs.emit(syncdict)
            #print(f"scrollbar value:{system_state["horzscal"]}")
            
            # read datablock corresponding to current sliderposition
            #TODO: correct 32 bit case if wFormatTag != 3
            #print("plot spectrum reached, start readsegment")
            #self.m["wavheader"] = WAVheader_tools.get_sdruno_header(self,self.m["f1"])
            #print("-------------> before pscale")
            pscale = self.m["wavheader"]['nBlockAlign']
            #print(f"---> wavheader: {self.m['wavheader']} pscale: {pscale} horzscal: {self.m['horzscal']}")
            position = int(np.floor(pscale*np.round(self.m["wavheader"]['data_nChunkSize']*self.m["horzscal"]/pscale/1000)))
            #ret = auxi.readsegment_new(position,self.DATABLOCKSIZE)
            #NEW 08-12-2023 #######################TODO###################### tBPS not yet clear
                #TODO: in future replace by:
                #remove readsegment, readsegment_new in this class !
                #from auxiliaries import readsegment, readsegment_new
                #filepath = system_state["f1"]
                #readoffset = system_state["readoffset"]
                #readsegment(filepath,position,readoffset,DATABLOCKSIZE)
                #readsegment_new(filepath,position,readoffset,DATABLOCKSIZE,self.m["wavheader"]["nBitsPerSample"],32,self.m["wavheader"]["wFormatTag"])
                #self.duration = ret["duration"]
            #ret = auxi.readsegment_new(self.m["f1"],position,self.DATABLOCKSIZE,self.m["wavheader"]["nBitsPerSample"],32,self.m["wavheader"]["wFormatTag"])
            if self.m["wavheader"]['sdrtype_chckID'].find('rcvr') > -1:
                self.readoffset = 86
            else:
                self.readoffset = 216
            ret = auxi.readsegment_new(self,self.m["f1"],position,self.readoffset,self.DATABLOCKSIZE,self.m["wavheader"]["nBitsPerSample"],
                                      32,self.m["wavheader"]["wFormatTag"])
            ####################################################################################
            data = ret["data"]
            if 2*ret["size"]/self.m["wavheader"]["nBlockAlign"] < self.DATABLOCKSIZE:
                #sys_state.set_status(system_state)
                return False

            self.m["Tabref"]["View_Spectra"]["ax"].clear()
            #print("datalen > 10")
            #print(f"view_spectra plot_spectum, gain: {self.m['resampling_gain']}")
            if self.gui.radioButton_plotraw.isChecked() is True:
                realindex = np.arange(0,self.DATABLOCKSIZE,2)
                imagindex = np.arange(1,self.DATABLOCKSIZE,2)
                #calculate spectrum and shift/rescale appropriately
                trace = np.abs(data[realindex]+1j*data[imagindex])
                trace = trace * np.power(10,self.m["resampling_gain"]/20)
                N = len(trace)
                deltat = 1/self.m["wavheader"]['nSamplesPerSec']
                time_ = np.linspace(0,N*deltat,N)

                self.m["Tabref"]["View_Spectra"]["ax"].plot(time_,trace, '-')
                self.m["Tabref"]["View_Spectra"]["ax"].set_xlabel('time (s)')
                self.m["Tabref"]["View_Spectra"]["ax"].set_ylabel('RFCorder amplitude (V)')

            else:
                pdata = self.ann_spectrum(0,data)
                #TODO: make function for plotting data , reuse in autoscan
                datax = pdata["datax"]
                datay = pdata["datay"] + self.m["resampling_gain"]
                basel = pdata["databasel"] + self.m["baselineoffset"]
                peaklocs = pdata["peaklocs"]
                peakprops = pdata["peakprops"]
                # create axis, clear old one and plot data

                self.m["Tabref"]["View_Spectra"]["ax"].plot(datax,datay, '-')
                self.m["Tabref"]["View_Spectra"]["ax"].plot(datax[peaklocs], datay[peaklocs], "x")
                self.m["Tabref"]["View_Spectra"]["ax"].plot(datax,basel, '-', color = "C2")
                self.m["Tabref"]["View_Spectra"]["ax"].set_xlabel('frequency (Hz)')
                self.m["Tabref"]["View_Spectra"]["ax"].set_ylabel('amplitude (dB)')
                #     ymax = datay[peaklocs], color = "C1")
                self.m["Tabref"]["View_Spectra"]["ax"].vlines(x=datax[peaklocs], ymin = basel[peaklocs],
                    ymax = datay[peaklocs], color = "C1")
                self.m["Tabref"]["View_Spectra"]["ax"].hlines(y=peakprops["width_heights"], xmin=datax[peakprops["left_ips"].astype(int)],
                    xmax=datax[peakprops["right_ips"].astype(int)], color = "C1")
                
            self.m["Tabref"]["View_Spectra"]["canvas"].draw()
            #display ev<luation time
            displtime = str(self.m["wavheader"]['starttime_dt'] + (self.m["wavheader"]['stoptime_dt']-self.m["wavheader"]['starttime_dt'])*self.m["horzscal"]/1000)
            self.gui.lineEdit_evaltime.setText('Evaluation time: '+ displtime + ' UTC')
            #self.plotcompleted = True
        #sys_state.set_status(system_state)

        return(True)
    
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
        flo = self.m["wavheader"]['centerfreq'] - self.m["wavheader"]['nSamplesPerSec']/2
        fup = self.m["wavheader"]['centerfreq'] + self.m["wavheader"]['nSamplesPerSec']/2
        freq0 = np.linspace(0,self.m["wavheader"]['nSamplesPerSec'],N)
        freq = freq0 + flo
        datax = freq
        datay = 20*np.log10(spr)
        # filter out all data below the baseline; baseline = moving median
        # filter kernel is self.FILTERKERNEL % of the spectral span
        datay_filt = datay
        kernel_length = int(N*self.m["filterkernel"]/100)
        # kernel length must be odd integer
        if (kernel_length % 2) == 0:
            kernel_length += 1
        
        #databasel = sig.medfilt(datay,kernel_length)
        databasel = median_filter(datay,kernel_length, mode = 'constant')
        datay_filt[datay_filt < databasel] = databasel[datay_filt < databasel]
        # find all peaks which are self.PROMINENCE dB above baseline and 
        # have a min distance of self.DELTAF and a min width of self.PEAKWIDTH
        dist = np.floor(np.maximum(self.m["deltaf"]/self.m["wavheader"]['nSamplesPerSec']*N,100))
        wd = np.floor(self.m["peakwidth"]/self.m["wavheader"]['nSamplesPerSec']*N)
        #print(f"peakwidth: {wd}")

        peaklocs, peakprops = sig.find_peaks(datay_filt,
                        prominence=(self.m["prominence"],None), distance=dist, width = wd)
        ret = {"datax": datax, "datay": datay, "datay_filt": datay_filt,
                "peaklocs": peaklocs, "peakprops": peakprops, "databasel": databasel}
        return ret

    def minSNRupdate_ScannerTab(self):
        self.m["prominence"] = self.gui.spinBoxminSNR_ScannerTab.value()
        #das ist ein externer Zugriff
        self.SigRelay.emit("cui_annotate",[self.gui.spinBoxminSNR.setProperty,["value",self.m["prominence"]]]) 
        self.gui.spinBoxminSNR.setProperty("value", self.m["prominence"]) #TODO TODO TODO: remove after relocation of annotator and activate line above
        #self.m["position"] = self.gui.horizontalScrollBar_view_spectra.value()
        #self.SigRelay.emit("cm_all_",["horzscal", self.m["position"]])
        self.SigRelay.emit("cm_all_",["prominence", self.m["prominence"]])
        self.SigRelay.emit("cexex_view_spectra",["updateGUIelements",0])


    def set_baselineoffset(self):        
        baselineoffset = self.gui.spinBoxminBaselineoffset.value()
        self.gui.label_6.setText("Baseline Offset:" + str(baselineoffset))
        #position = self.gui.horizontalScrollBar_view_spectra.value()
        #self.SigRelay.emit("cm_all_",["horzscal", position])
        self.SigRelay.emit("cm_all_",["baselineoffset",baselineoffset])
        #self.SigRelay.emit("cm_view_spectra",["position",position]) # TODO: CHECK THIS IS STRANGE !
        self.SigRelay.emit("cexex_view_spectra",["updateGUIelements",0])

    def setkernelwidth(self):               
        filterkernel = self.gui.spinBoxKernelwidth.value()
        self.SigRelay.emit("cm_all_",["filterkernel",filterkernel])
        #self.SigRelay.emit("cm_view_spectra",["fileopened",False])# TODO: CHECK THIS IS STRANGE !
        #self.SigRelay.emit("cm_view_spectra",["position",self.position])
        self.SigRelay.emit("cexex_view_spectra",["updateGUIelements",0])

    def minPeakwidthupdate(self):
        peakwidth = self.gui.spinBoxminPeakwidth.value()
        #position = self.gui.horizontalScrollBar_view_spectra.value()
        self.SigRelay.emit("cm_all_",["peakwidth",peakwidth])
        #self.SigRelay.emit("cm_all_",["deltaf",self.DELTAF])# TODO: CHECK THIS IS STRANGE !
        #self.SigRelay.emit("cm_view_spectra",["position",position])# TODO: CHECK THIS IS STRANGE !
        self.SigRelay.emit("cexex_view_spectra",["updateGUIelements",0])

    def minPeakDistanceupdate(self):
        deltaf = self.gui.spinBoxminPeakDistance.value()
        #self.position = self.ui.horizontalScrollBar_view_spectra.value()# TODO: CHECK THIS IS STRANGE !
        # self.SigRelay.emit("cm_all_",["horzscal", self.position])# TODO: CHECK THIS IS STRANGE !
        self.SigRelay.emit("cm_all_",["deltaf",deltaf])
        # self.SigRelay.emit("cm_view_spectra",["position",self.position])# TODO: CHECK THIS IS STRANGE !
        self.SigRelay.emit("cexex_view_spectra",["updateGUIelements",0])