#IMPORT WHATEVER IS NEEDED
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5 import QtGui
import logging
import numpy as np
import os
from datetime import datetime
import shutil
from auxiliaries import auxiliaries as auxi
from auxiliaries import WAVheader_tools

class waveditor_m(QObject):
    __slots__ = ["None"]
    SigModelXXX = pyqtSignal()

    def __init__(self):
        super().__init__()
        # Constants
        self.CONST_SAMPLE = 0 # sample constant
        self.mdl = {}
        self.mdl["sample"] = 0
        self.mdl["_log"] = False
        self.mdl["fileopened"] = False
        self.mdl["ovwrt_flag"] = False
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

class waveditor_c(QObject):
    """_view method
    """
    __slots__ = ["contvars"]

    SigAny = pyqtSignal()

    def __init__(self, waveditor_m): #TODO: remove gui
        super().__init__()

    # def __init__(self, *args, **kwargs): #TEST 09-01-2024
    #     super().__init__(*args, **kwargs)
        viewvars = {}
        #self.set_viewvars(viewvars)
        self.m = waveditor_m.mdl
        self.logger = waveditor_m.logger

    def extract_startstoptimes_auxi(self, wavheader): #TODO: move to controller module edit wavheader
        """_synthetize next filename in the playlist in case the latter cannot be extracted
        from auxi SDR-wav-header because it is longar than 96 chars_
        can only be used for SDRUno and RFCorder header
        CONTROLLER
        :param : wavheader [dictionary]
        :type : dictionary
        :raises [ErrorType]: [ErrorDescription]
        :return: next_filename
        :rtype: str
        """
        ###TODO error handling
        ###TODO TODO TODO: check if the following fixes for binary representations are necessary when using UNICODE
        wavheader['nextfilename'] = (wavheader['nextfilename']).replace('x00','')
        wavheader['nextfilename'] = (wavheader['nextfilename']).replace("'","")
        wavheader['nextfilename'] = (wavheader['nextfilename']).replace('b''','')
        wavheader['nextfilename'] = wavheader['nextfilename'].rstrip(' ')
        wavheader['nextfilename'] = wavheader['nextfilename'].rstrip('\\')  #####TODO CHECK if odd for LINUX
        nextfilename = wavheader['nextfilename']
        nextfilename_purged = nextfilename.replace('/','\\')  #####TODO CHECK if odd for LINUX
        nextfile_dirname = os.path.dirname(nextfilename_purged)
        #TODO: nextfilename dirname is frequently 0 --> quest is invalid
        if len(nextfile_dirname) > 3:
            if (wavheader['nextfilename'][0:2] == "'\\") is False:  #####TODO CHECK if odd for LINUX
                self.loopalive = False   ### stop playlist loop  #######################  loop must be handled inside this method !
                true_nextfilename = ''
            else:
                if wavheader['nextfilename'].find('.wav') != -1: ### take next filename from wav header
                    true_nextfilename, next_ext = os.path.splitext(os.path.basename(nextfilename_purged))
                else: ### synthetize next filename because wav header string for nextfile longer 92 chars
                    self.logger.debug("nextfile entry in wavheader invalid, please edit wav header")
                    true_nextfilename = ''
                    return true_nextfilename
                self.loopalive = True
            return true_nextfilename
        

class waveditor_v(QObject):
    """_view methods for resampling module
    TODO: gui.wavheader --> something less general ?
    """
    __slots__ = ["viewvars"]

    SigAny = pyqtSignal()
    SigCancel = pyqtSignal()
    SigUpdateGUI = pyqtSignal(object)
    SigSyncGUIUpdatelist = pyqtSignal(object)
    SigRelay = pyqtSignal(str,object)

    def __init__(self, gui, waveditor_c, waveditor_m):
        super().__init__()

        #viewvars = {}
        #self.set_viewvars(viewvars)
        self.m = waveditor_m.mdl
        self.DATABLOCKSIZE = 1024*32
        self.gui = gui #gui_state["gui_reference"]#system_state["gui_reference"]
        self.logger = waveditor_m.logger
        self.init_waveditor_ui()


    def init_waveditor_ui(self):
        self.gui.actionOverwrite_header.triggered.connect(self.overwrite_header)
        self.gui.pushButton_InsertHeader.setEnabled(False)
        self.gui.pushButton_InsertHeader.clicked.connect(self.overwrite_header)
        self.gui.radioButton_WAVEDIT.setEnabled(True)
        self.gui.radioButton_WAVEDIT.setChecked(False)
        self.gui.radioButton_WAVEDIT.clicked.connect(self.activate_WAVEDIT)
        self.gui.tableWidget_basisfields.setEnabled(False)
        self.gui.tableWidget_starttime.setEnabled(False)
        self.gui.tableWidget_3.setEnabled(False)
        self.clear_WAVwidgets()



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
        if _key.find("cm_waveditor") == 0 or _key.find("cm_all_") == 0:
            #set mdl-value
            self.m[_value[0]] = _value[1]
        if _key.find("cui_waveditor") == 0:
            _value[0](_value[1]) #STILL UNCLEAR
        if _key.find("cexex_waveditor") == 0  or _key.find("cexex_all_") == 0:
            if  _value[0].find("updateGUIelements") == 0:
                self.updateGUIelements()
            if  _value[0].find("activate_WAVEDIT") == 0:
                self.activate_WAVEDIT()
            #handle method
            # if  _value[0].find("plot_spectrum") == 0: #EXAMPLE
            #     self.plot_spectrum(0,_value[1])   #EXAMPLE

    def activate_WAVEDIT(self):
        #self.show()
        if self.gui.radioButton_WAVEDIT.isChecked() is True:
                    self.gui.tableWidget_basisfields.setEnabled(True)
                    self.gui.tableWidget_starttime.setEnabled(True)
                    self.gui.tableWidget_3.setEnabled(True)      
        else:
                    self.gui.tableWidget_basisfields.setEnabled(False)
                    self.gui.tableWidget_starttime.setEnabled(False)
                    self.gui.tableWidget_3.setEnabled(False)

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
        print("waveditor: updateGUIelements")
        self.fill_wavtable()
        #self.gui.DOSOMETHING

    def update_GUI(self,_key): #TODO TODO: is this method still needed ? reorganize. gui-calls should be avoided, better only signalling and gui must call the routenes itself
        print(" view spectra updateGUI: new updateGUI in view spectra module reached")
        self.SigUpdateGUI.disconnect(self.update_GUI)
        if _key.find("ext_update") == 0:
            #update resampler gui with all elements
            #TODO: fetch model values and re-fill all tab fields
            print("waveditor update_GUI reached")
            pass
        #other key possible: "none"
        #DO SOMETHING
        self.SigUpdateGUI.connect(self.update_GUI)

    def reset_GUI(self):
        self.clear_WAVwidgets()
    
    def popup(self,i):
        """
        VIEW or CONTROLLER ??
        
        """
        self.yesno = i.text()

    def clear_WAVwidgets(self):
        """clear the tabwidgets of the wav-editor tab
        :param : none
        :type : none
        :raises [ErrorType]: [ErrorDescription]
        :return: none
        :rtype: none
        """
        for ix in range(0,14):
            self.gui.tableWidget_basisfields.item(ix, 0).setData(0,0)
        for ix in range(0,8):
            self.gui.tableWidget_starttime.item(ix, 0).setData(0,0)
            self.gui.tableWidget_starttime.item(ix, 1).setData(0,0)
        self.gui.tableWidget_3.item(2, 0).setText("")
        self.gui.tableWidget_3.item(1, 0).setText("")
        self.gui.tableWidget_3.item(0, 0).setText("")
        self.gui.tableWidget_3.item(3, 0).setText("")

    def overwrite_header(self):
        """overwrite the tabwidget items of the wav-editor tab
        :param : none
        :type : none
        :raises [ErrorType]: [ErrorDescription]
        :return: False if some conditions are not met (fileopened False, no overwrite wanted,...)
        :rtype: Boolean
        """
        # system_state = sys_state.get_status()
        if self.m["fileopened"] is False:
            return False
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Question)
        msg.setText("overwrite wav header")
        msg.setInformativeText("you are about to overwrite the header of the current wav file with the values in the tables of Tab 'WAV Header'. Do you really want to proceed ?")
        msg.setWindowTitle("overwrite")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.buttonClicked.connect(self.popup)
        msg.exec_()

        if self.yesno == "&Yes":
            self.m["ovwrt_flag"] = True
            self.write_edited_wavheader()
        else:
            #sys_state.set_status(system_state)
            return False

        #TODO: write backup dump header
        #TODO: rename file to SDRUno name convention if filetype = .dat
        if self.m["filetype"] == "dat":
            old_name = self.m["f1"]
            SDRUno_suffix = str(self.m["wavheader"]['starttime_dt'])
            SDRUno_suffix = SDRUno_suffix.replace(" ","_")
            SDRUno_suffix = SDRUno_suffix.replace(":","")
            SDRUno_suffix = SDRUno_suffix.replace("-","")
            usix = self.m["my_filename"].find('lo')
            if usix == -1:
                auxi.standard_infobox("dat file does not meet old COHIRADIA RFCorder name convention; file will be renamed with correct suffixes")
                usix = len(self.m["my_filename"])+2
            bbb = self.m["my_filename"][0:usix-2]
            new_name = self.m["my_dirname"] + '/' + bbb + '_' + str(SDRUno_suffix) + '_' + str(int(np.round(self.m["wavheader"]["centerfreq"]/1000))) + 'kHz.wav'
            shutil.move(old_name, new_name)
            #system_state["f1"] = new_name #TODO: replace by line below
            self.SigRelay.emit("cm_all_",["f1",new_name])
            #self.SigRelay.emit("cm_all_",["my_filename",self.my_filename]) #remove after tests
            self.SigRelay.emit("cexex_all_",["updateGUIelements",0])
            #self.showfilename() #remove after complete transtition to Relay
        self.gui.label_8.setEnabled(False)
        self.gui.pushButton_InsertHeader.setEnabled(False)
        self.m["filetype"] = "wav"
        self.SigRelay.emit("cm_all_",["filetype",self.m["filetype"]])
        #sys_state.set_status(system_state) #remove after tests

    def fill_wavtable(self):
        """
        VIEW
        fill tables on TAB wavedit with the respective values from the vaw header
        """
        starttime = self.m["wavheader"]['starttime']
        stoptime = self.m["wavheader"]['stoptime']
        start_str = str(self.m["wavheader"]['starttime_dt'])

        ###Einträge der Tabelle 1 nur Integers
        metastring1 = [self.m["wavheader"]['filesize'], self.m["wavheader"]['sdr_nChunkSize']]
        metastring1.append(self.m["wavheader"]['wFormatTag'])
        metastring1.append(self.m["wavheader"]['nChannels'])
        metastring1.append(self.m["wavheader"]['nSamplesPerSec'])
        metastring1.append(self.m["wavheader"]['nAvgBytesPerSec'])
        metastring1.append(self.m["wavheader"]['nBlockAlign'])
        metastring1.append(self.m["wavheader"]['nBitsPerSample'])
        metastring1.append(self.m["wavheader"]['centerfreq'])
        metastring1.append(self.m["wavheader"]['data_nChunkSize'])
        metastring1.append(self.m["wavheader"]['ADFrequency'])
        metastring1.append(self.m["wavheader"]['IFFrequency'])
        metastring1.append(self.m["wavheader"]['Bandwidth'])
        metastring1.append(self.m["wavheader"]['IQOffset'])               
        for ix in range(0,14):
            self.gui.tableWidget_basisfields.item(ix, 0).setData(0,metastring1[ix])
        for ix in range(0,8):
            self.gui.tableWidget_starttime.item(ix, 0).setData(0,starttime[ix])
            self.gui.tableWidget_starttime.item(ix, 1).setData(0,stoptime[ix])

        # write other info to table 3 (strings)                    
        self.gui.tableWidget_3.item(2, 0).setText(start_str)
        self.gui.tableWidget_3.item(1, 0).setText(str(self.m["wavheader"]['sdrtype_chckID']))
        self.gui.tableWidget_3.item(0, 0).setText(str(self.m["wavheader"]['nextfilename']))
        self.gui.tableWidget_3.item(3, 0).setText(str(self.m["wavheader"]['data_ckID']))

    def check_consistency(self,item,dtype,label):
        typetab = {"long": [-2147483648, 2147483647], "ulong": [0, 4294967295], 
                    "short": [-32768, 32767]  , "ushort": [0, 65535],
                    "float": [-3.4E38, 3.4E38]}

        if item < typetab[dtype][0] or item > typetab[dtype][1]:
            auxi.standard_errorbox(label + "must be of type " + dtype + ", i.e. in range " + str(typetab[dtype]) + "\n Please correct !")
            return False
        else:
            return True
        
    def write_edited_wavheader(self):  #TODO move to controller module wavheader
        """
        CONTROLLER        
        """
        #system_state = sys_state.get_status()
        crit1 = False
        #TODO : ?Sonderzeichencheck ??
        self.m["wavheader"]['nextfilename'] = self.gui.tableWidget_3.item(0, 0).text()
        preview = {}
        for ix in range(0,8):
            preview[ix] = int(self.gui.tableWidget_starttime.item(ix, 0).text())
        try:
            a = datetime(preview[0],preview[1],preview[3],preview[4],preview[5],preview[6]) #remove ?
        except ValueError:
            auxi.standard_errorbox("start date or time entry is out of valid range, please check and retry")
            self.SigRelay.emit("cm_all_",["wavheader",self.m["wavheader"]])
            #sys_state.set_status(system_state)
            return False
        if preview[6] > 999:
            crit1 = True

        for ix in range(0,8):
            preview[ix] = int(self.gui.tableWidget_starttime.item(ix, 1).text())
        try:
            a = datetime(preview[0],preview[1],preview[3],preview[4],preview[5],preview[6])
        except ValueError:
            auxi.standard_errorbox("stop date or time entry is out of valid range, please check and retry")
            self.SigRelay.emit("cm_all_",["wavheader",self.m["wavheader"]])
            #sys_state.set_status(system_state)
            return False
        if preview[6] > 999 or crit1 == True:
            auxi.standard_errorbox("ms value in start or stoptime must not be > 999, please check and retry")
            self.SigRelay.emit("cm_all_",["wavheader",self.m["wavheader"]])
           #sys_state.set_status(system_state)
            return False      
           
        for ix in range(0,8):
            self.m["wavheader"]['starttime'][ix] = int(self.gui.tableWidget_starttime.item(ix, 0).text())
            self.m["wavheader"]['stoptime'][ix] = int(self.gui.tableWidget_starttime.item(ix, 1).text())

        checklist = ['filesize','sdr_nChunkSize','wFormatTag','nChannels', 'nSamplesPerSec',
            'nAvgBytesPerSec', 'nBlockAlign','nBitsPerSample','centerfreq','data_nChunkSize',
            'ADFrequency','IFFrequency','Bandwidth','IQOffset']
        typelist = ['ulong', 'long', 'short', 'short', 'long', 
                    'long', 'short', 'short', 'long', 'ulong',
                     'long',  'long',  'long',  'long']
        for ix2 in range(len(checklist)):
            self.m["wavheader"][checklist[ix2]] = int(self.gui.tableWidget_basisfields.item(ix2, 0).text())
            chk = False
            chk = self.check_consistency(self.m["wavheader"][checklist[ix2]],typelist[ix2],checklist[ix2])
            if chk == False:
                self.SigRelay.emit("cm_all_",["wavheader",self.m["wavheader"]])
                #sys_state.set_status(system_state)
                return False
                #self.m["wavheader"][checklist[ix2]] = int(self.gui.tableWidget.item(ix2, 0).text())

        if self.m["fileopened"] is True:
            if self.m["ovwrt_flag"] == False: #TODO: wird nie mehr erreicht, oder ?
                wav_filename = self.m["my_dirname"] + '/templatewavheader.wav'
                auxi.standard_errorbox("Template wavheader File is being written, useful ?")
            else: 
                wav_filename = self.m["f1"]            
            WAVheader_tools.write_sdruno_header(self,wav_filename,self.m["wavheader"],self.m["ovwrt_flag"])
        #sys_state.set_status(system_state)






