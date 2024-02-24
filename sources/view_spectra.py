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

class view_spectra_m(QObject):
    __slots__ = ["None"]
    SigModelXXX = pyqtSignal()

    #TODO: replace all gui by respective state references if appropriate
    def __init__(self):
        super().__init__()
        # Constants
        self.CONST_SAMPLE = 0 # sample constant
        self.mdl = {}
        self.mdl["sample"] = 0

class view_spectra_c(QObject):
    """_view methods for resampling module
    TODO: gui.wavheader --> something less general ?
    """
    __slots__ = ["contvars"]

    SigAny = pyqtSignal()
    SigCancel = pyqtSignal()
    #SigDisplaySpectrum = pyqtSignal(object,object)

    def __init__(self, gui, view_spectra_m):
        super().__init__()

    # def __init__(self, *args, **kwargs): #TEST 09-01-2024
    #     super().__init__(*args, **kwargs)
        viewvars = {}
        #self.set_viewvars(viewvars)
        self.m = view_spectra_m.mdl
        

class view_spectra_v(QObject):
    """_view methods for resampling module
    TODO: gui.wavheader --> something less general ?
    """
    __slots__ = ["viewvars"]

    SigAny = pyqtSignal()
    SigCancel = pyqtSignal()
    SigUpdateGUI = pyqtSignal(object)
    SigSyncGUIUpdatelist = pyqtSignal(object)
    SigUpdateOtherGUIs = pyqtSignal()

    def __init__(self, gui, view_spectra_c, view_spectra_m):
        super().__init__()

        #viewvars = {}
        #self.set_viewvars(viewvars)
        self.m = view_spectra_m.mdl
        self.DATABLOCKSIZE = 1024*32
        #self.sys_state = wsys.status() #TEST: commented out 09-01-2024
        #self.sys_state = gui_state
        #system_state = self.sys_state.get_status()
        self.m["reslistdoubleemit_ix"] = False
        self.m["starttrim"] = False
        self.m["stoptrim"] = False
        self.gui = gui #gui_state["gui_reference"]#system_state["gui_reference"]
        self.SigUpdateGUI.connect(self.update_GUI)

    # def connector(self):
    #     self.SigSyncGUIUpdatelist.emit(self.updateGUIelements)

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
        print("view spectra: updateGUIelements")
        self.gui.label_Filename_ViewSpectra.setText(self.m["my_filename"] + self.m["ext"])
        dummy = 0
        self.plot_spectrum(dummy,self.m["position"])


    def update_GUI(self,_key): #TODO TODO: is this method still needed ? reorganize. gui-calls should be avoided, better only signalling and gui must call the routenes itself
        print(" view spectra updateGUI: new updateGUI in view spectra module reached")
        self.SigUpdateGUI.disconnect(self.update_GUI)
        if _key.find("ext_update") == 0:
            #update resampler gui with all elements
            #TODO: fetch model values and re-fill all tab fields
            print("view_spectra update_GUI reached")
            pass
        #other key possible: "none"
        dummy = 0
        self.plot_spectrum(dummy,self.m["position"])
        time.sleep(0.1)
        self.SigUpdateGUI.connect(self.update_GUI)


    def plot_spectrum(self,dummy,position):
        """
        assign a plot window and a toolbar to the tab 'scanner'
        :param : none
        :type : none
        :raises [ErrorType]: [ErrorDescription]
        :return: flag False or True, False on unsuccessful execution
        :rtype: Boolean
        """
        #test TODO: remove after tests
        #system_state = sys_state.get_status()
        #testirate = system_state["irate"]
        #print(f"TEST TEST TEST: plot_spectrum testirate:{testirate}")
        #sys_state.set_status(system_state)
        print("view_spectra plot_spectum reached")
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
            print(f"view_spectra plot_spectum, gain: {self.m['resampling_gain']}")
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

