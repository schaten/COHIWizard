#IMPORT WHATEVER IS NEEDED
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5 import QtGui
from PyQt5 import QtWidgets, QtGui
import numpy as np
import os
import logging
from auxiliaries import auxiliaries as auxi
import logging
import yaml
import copy
import time
import wave
import contextlib
import struct


class synthesizer_m(QObject):
    SigModelXXX = pyqtSignal()

    def __init__(self):
        super().__init__()
        # Constants
        self.CONST_SAMPLE = 0 # sample constant
        self.mdl = {}
        self.mdl["sample"] = 0
        self.mdl["_log"] = False
        self.mdl["fileopened"] = False
        self.mdl["playlist_active"] = False
        self.mdl["sample"] = 0
        self.mdl["TEST"] = False
        self.mdl["Buttloop_pressed"] = False
        self.mdl["errorf"] = False
        self.mdl["icorr"] = 0
        self.mdl["gain"] = 1
        self.mdl["audioBW"] = 4.5
        self.mdl["carrier_distance"] = 9
        self.mdl["carrier_ix"] = 0
        # Create a custom logger
        logging.getLogger().setLevel(logging.DEBUG)
        # Erstelle einen Logger mit dem Modul- oder Skriptnamen
        self.logger = logging.getLogger(__name__)
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

class synthesizer_c(QObject):
    """_view method
    """
    SigAny = pyqtSignal()
    SigRelay = pyqtSignal(str,object)
    SigActivateOtherTabs = pyqtSignal(str,str,object)

    def __init__(self, synthesizer_m): #TODO: remove gui
        super().__init__()

        self.m = synthesizer_m.mdl
        self.logger = synthesizer_m.logger


    def dummy(self):
        print("hello from superclass")
        

class synthesizer_v(QObject):
    """_view methods for resampling module
    TODO: gui.wavheader --> something less general ?
    """

    SigAny = pyqtSignal()
    SigCancel = pyqtSignal()
    SigUpdateGUI = pyqtSignal(object)
    SigSyncGUIUpdatelist = pyqtSignal(object)
    SigRelay = pyqtSignal(str,object)
    SigActivateOtherTabs = pyqtSignal(str,str,object)

    def __init__(self, gui, synthesizer_c, synthesizer_m):
        super().__init__()

        self.m = synthesizer_m.mdl
        self.synthesizer_c = synthesizer_c
        self.headerlength = 44 #read audio wav after first 44bytes of header info; could be generalized by searching the next data chunk
        self.SORTCRITERION = 'name' #Sorting criterion for filelist: 'date': sort caa to date in ascending order, 'name': alphabetical 
        self.FILTER_OVERLAP = 800  #overlap samples due to filter delay
        self.READ_BIAS = -100     # pre-read audio samples to enable filter delay compensation

        self.AUTOSCALE_RF = 0     # Set to 1 to select autoscale mode causing exact RF levelling to max, otherwise set to 0 for fixed RF levelling  
        self.FIXSCALE_FAKTOR_RF = 0.8 # guard factor for fixed RF levelling: assumed max. RF level: #carriers * (1+C_m) * C_FIXSCALE_FAKTOR_RF. RF overload may occur if C_FIXSCALE_FAKTOR_RF < 1 

        self.DATABLOCKSIZE = 1024*32
        self.STD_AUDIOBW = "4.5"
        self.STD_CARRIERDISTANCE = "9"
        self.STD_fclow = "783"
        self.STD_LO = "1125"
        self.gui = gui
        self.synthesizer_c = synthesizer_c
        #self.norepeat = False
        self.c_step = int(self.STD_CARRIERDISTANCE)
        self.cf_LO = int(self.STD_fclow)
        self.m["audioBW"] = float(self.STD_AUDIOBW)
        self.m["TEST"] = False
        self.m["wavheader"] = {}
        self.m["wavheader"]['centerfreq'] = 0
        self.m["icorr"] = 0
        
        self.logger = synthesizer_m.logger
        self.synthesizer_c.SigRelay.connect(self.rxhandler)
        self.synthesizer_c.SigRelay.connect(self.SigRelay.emit)
        self.gui.lineEdit_LO.setText("1125")
        self.DATABLOCKSIZE = 1024*32
        self.gui = gui #gui_state["gui_reference"]#system_state["gui_reference"]
        self.logger = synthesizer_m.logger
        self.synthesizer_c.SigRelay.connect(self.rxhandler)
        self.synthesizer_c.SigRelay.connect(self.SigRelay.emit)
        self.synthesizer_c.SigRelay.connect(self.SigRelay.emit)

        self.init_synthesizer_ui()

        self.m["numcarriers"] = self.gui.spinBox_numcarriers.value()
        self.m["carrier_ix"] = 0
        self.readFileList = []
        self.oldFileList = []
        self.readFilePath = []
        for self.m["carrier_ix"] in range(0,2):
            self.readFileList.append([])
            self.readFileList[self.m["carrier_ix"]] = []
            self.oldFileList.append([])
            self.oldFileList[self.m["carrier_ix"]] = []
            self.readFilePath.append([])
            self.readFilePath[self.m["carrier_ix"]] = []
        self.m["carrier_ix"] = 0

        try:
            stream = open("config_wizard.yaml", "r")
            self.m["metadata"] = yaml.safe_load(stream)
            stream.close()
            self.ismetadata = True
        except:
            self.ismetadata = False
        try:
            self.default_directory = self.m["metadata"]["last_audiosource_path"]
        except:
            self.default_directory = ""

    def init_synthesizer_ui(self):
        self.gui.comboBox_targetSR.setCurrentIndex(5)
        preset_time = QTime(00, 30, 00) 
        self.gui.timeEdit_reclength.setTime(preset_time)
        #self.gui.listWidget_sourcelist.setHeaderLabel("Directory tree")
        #self.gui.listWidget_sourcelist.itemClicked.connect(self.on_tree_item_clicked)
        #self.gui.listWidget_sourcelist.itemDoubleClicked.connect(self.on_tree_item_double_clicked)
        self.gui.pushButton_select_source.clicked.connect(self.select_tree)
        self.gui.listWidget_playlist.clear()
        item = QtWidgets.QListWidgetItem()
        self.gui.listWidget_sourcelist.addItem(item)
        self.gui.lineEdit_audiocutoff_freq.setText(self.STD_AUDIOBW)
        self.gui.lineEdit_carrierdistance.setText(self.STD_CARRIERDISTANCE)
        self.gui.spinBox_numcarriers.valueChanged.connect(self.freq_carriers_update)
        self.gui.lineEdit_carrierdistance.editingFinished.connect(self.carrierdistance_update)
        self.gui.lineEdit_audiocutoff_freq.editingFinished.connect(self.audioBW_update)
        self.gui.lineEdit_fc_low.editingFinished.connect(self.fc_low_update)
        self.gui.listWidget_playlist.model().rowsInserted.connect(self.playlist_update_delayed)
        self.gui.listWidget_playlist.model().rowsRemoved.connect(self.playlist_update_delayed) 
        self.gui.listWidget_playlist.setSelectionMode(QListWidget.ExtendedSelection)
        self.gui.listWidget_playlist.setContextMenuPolicy(Qt.CustomContextMenu)
        self.gui.listWidget_playlist.customContextMenuRequested.connect(self.show_context_menu)
        self.gui.listWidget_playlist.model().rowsMoved.connect(self.on_rows_moved)
        self.gui.comboBox_cur_carrierfreq.currentIndexChanged.connect(self.carrier_ix_changed)
        self.gui.pushButton_saveproject.clicked.connect(self.save_project)
        self.gui.pushButton_loadproject.clicked.connect(self.load_project)

        #self.gui.lineEdit_carrierdistance.textEdited.connect(self.carriedistance_update)
        #editingFinished #editingFinished
        ###########TODO TODO TODO: remove after transfer to config Tab
        # try:
        #     stream = open("config_wizard.yaml", "r")
        #     self.metadata = yaml.safe_load(stream)
        #     stream.close()
        #     self.ismetadata = True
        #     if 'STM_IP_address' in self.metadata.keys():
        #         self.gui.lineEdit_IPAddress.setText(self.metadata["STM_IP_address"]) #TODO: Remove after transfer of playrec
        #         self.m["STM_IP_address"] = self.metadata["STM_IP_address"] #TODO: Remove after transfer of playrec
        # except:
        #     self.m["STM_IP_address"] = self.gui.lineEdit_IPAddress.text()
        #     self.logger.error("reset_gui: cannot get metadata")
        #     pass

    def save_project(self):
        """_save current settings and all playlists to a project file (*.proj) via intermediate dictionary pr
        *.proj files are have yaml format

        :param: none
        :returns: none
        : raises: none

        """
        pr = {}
        pr["projectdata"] = {}
        pr["projectdata"]["readFilePath"] = self.readFilePath
        pr["projectdata"]["readFileList"] = self.readFileList
        pr["projectdata"]["numcarriers"] = self.m["numcarriers"]
        pr["projectdata"]["carrier_step"] = self.c_step
        pr["projectdata"]["carrier_f_LO"] = self.cf_LO
        pr["projectdata"]["audio_BW"] = self.m["audioBW"]
        pr["projectdata"]["current_listdir"] = self.current_listdir
        pr["projectdata"]["targetSR_index"] = self.gui.comboBox_targetSR.currentIndex()
        #TODO TODO TODO: add all settings to be saved:
        #reclength
        #self.comboBox_targetSR_2.setCurrentIndex(###)
        #reclength
        #scale factor
        #modulation factor
        #Target filename
        #file list sort criterion ?????????????OBSOLETE ??????????????????????

        filename = self.save_file_dialog()
        stream = open(filename, "w") ###replace project.yaml with filename
        yaml.dump(pr["projectdata"], stream)
        stream.close()

    def load_project(self):
        """_load project file (*.proj) and read the settings of that project to dictionary pr
        fill playlists and re-initialize all settings according to loaded project.
        *.proj files are have yaml format

        :param: none
        :returns: none
        : raises: none

        """
        pr = {}
        pr["projectdata"] = {}
        filename = self.load_file_dialog()
        try:
            stream = open(filename, "r")
            pr["projectdata"] = yaml.safe_load(stream)
            stream.close()

            self.readFileList = pr["projectdata"]["readFileList"]
            self.readFilePath = pr["projectdata"]["readFilePath"]
            #self.oldFileList = pr["projectdata"]["readFileList"]
            self.oldFileList = copy.deepcopy(pr["projectdata"]["readFileList"])
            self.gui.lineEdit_audiocutoff_freq.setText(str(pr["projectdata"]["audio_BW"]))
            self.gui.lineEdit_carrierdistance.setText(str(pr["projectdata"]["carrier_step"]))
            self.m["numcarriers"] = pr["projectdata"]["numcarriers"]
            self.gui.spinBox_numcarriers.valueChanged.disconnect(self.freq_carriers_update)
            self.gui.spinBox_numcarriers.setProperty("value", self.m["numcarriers"])
            self.gui.spinBox_numcarriers.valueChanged.connect(self.freq_carriers_update)
            self.m["carrier_ix"] = 0
            self.gui.comboBox_cur_carrierfreq.setCurrentIndex(self.m["carrier_ix"])

            self.load_index = True
            self.fillplaylist()
            self.current_listdir = pr["projectdata"]["current_listdir"]
            self.fillsourcelist(self.current_listdir)
            self.audioBW_update()
            self.fc_low_update()
            self.carrierdistance_update()
            self.load_index = False

            #TODO TODO TODO load all remaining settings
            #self.comboBox_targetSR_2.setCurrentIndex(###)
            #self.gui.comboBox_targetSR.setCurrentIndex(pr["projectdata"]["targetSR_index"])
            #reclength
            #scale factor
            #modulation factor
            #Target filename
            #file list sort criterion ?????????????OBSOLETE ??????????????????????
        except:
            self.logger.error('cannot load project yaml file (proj files)')

    def save_file_dialog(self):
        # Erstellen des Datei-Speicher-Dialogs
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog  # Verwende das Qt-eigene Dialogfenster
        file_name, _ = QFileDialog.getSaveFileName(self.m["QTMAINWINDOWparent"], 
                                                   "Save File", 
                                                   "*.proj",  # Standardmäßig kein voreingestellter Dateiname
                                                   "proj Files (*.proj);;All Files (*)",  # Filter für Dateitypen
                                                   options=options)
        if file_name:
            return file_name
        else:
            return None

    def load_file_dialog(self):
        self.standardpath = os.getcwd()  #TODO TODO: take from core module via rxh; on file open core sets that to:
        #        self.SigRelay.emit("cm_all_",["standardpath",self.standardpath]); 
        ########### SET DEDICATED PROJECT FOLDER !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

        filters = "project files (*.proj);;all files (*)"
        selected_filter = "project files (*.proj)"
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog  # Verwende das Qt-eigene Dialogfenster
        file_name, _ = QFileDialog.getOpenFileName(self.m["QTMAINWINDOWparent"], 
                                                "Open project File", 
                                                self.standardpath,  # Standardmäßig kein voreingestellter Dateiname
                                                filters,  # Filter für Dateitypen
                                                selected_filter,
                                                options=options)
        if file_name:
            return file_name
        else:
            return None


    def get_wav_info(self,wav_file):
        """opens wav header of the sepcified file and reads out important information
        returns a dict with the keys:
         {
                'duration_seconds': duration,
                'n_channels': n_channels,
                'framerate': framerate,
                'sampwidth_bytes': sampwidth,
                'data_format': data_format
        }
        Example:
        file_path = 'your_audio_file.wav'
        wav_info = get_wav_info(file_path)

        print(f"playtime: {wav_info['duration_seconds']} Sekunden")
        print(f"sampling rate: {wav_info['framerate']} Hz")
        print(f"Data format: {wav_info['data_format']}")
        
        :param: wav_file
        :type: str
        :returns: dictionary with the information
        :rtype: dict
        """
        # open WAV-file
        with open(wav_file, 'rb') as file:
            # Lese den RIFF-Header (die ersten 12 Bytes)
            riff_header = file.read(12)
            
            # Lese den fmt-Chunk-Header (die nächsten 8 Bytes)
            fmt_chunk_header = file.read(8)
            
            # Extrahiere die Subchunk-ID und die Größe des fmt-Chunks
            subchunk_id = fmt_chunk_header[:4].decode('ascii')
            subchunk_size = struct.unpack('<I', fmt_chunk_header[4:])[0]
            
            # Lese den fmt-Chunk basierend auf der Größe
            fmt_chunk = file.read(subchunk_size)
            
            # Entpacke das Audioformat aus dem fmt-Chunk
            audio_format = struct.unpack('<H', fmt_chunk[:2])[0]

            # Mapping des Audioformats zu einer menschlich lesbaren Bezeichnung
            if audio_format == 1:
                data_format = f"PCM{8 * struct.unpack('<H', fmt_chunk[2:4])[0]}"
            elif audio_format == 3:
                sampwidth = struct.unpack('<H', fmt_chunk[2:4])[0] // 8
                if sampwidth == 4:
                    data_format = "Float32"
                elif sampwidth == 8:
                    data_format = "Float64"
                else:
                    data_format = "Unknown Float Format"
            else:
                data_format = f"Unknown Format Code: {audio_format}"

            # Anzahl der Kanäle, Abtastrate und weitere Informationen
            n_channels = struct.unpack('<H', fmt_chunk[2:4])[0]
            framerate = struct.unpack('<I', fmt_chunk[4:8])[0]
            sampwidth = struct.unpack('<H', fmt_chunk[2:4])[0] // 8

        # Nutze die `wave`-Bibliothek, um weitere Informationen zu extrahieren
        with wave.open(wav_file, 'rb') as wav:
            n_frames = wav.getnframes()
            duration = n_frames / float(framerate)            # return info
            
            return {
                'duration_seconds': duration,
                'n_channels': n_channels,
                'framerate': framerate,
                'sampwidth_bytes': sampwidth,
                'data_format': data_format
            }

    def show_fillprogress(self,duration):
        """show completion percentage of the current carrier track

        """
        qtimeedit = self.gui.timeEdit_reclength
        time_from_qtimeedit = qtimeedit.time()       
        # Zeit aus dem QTimeEdit-Objekt zu aktuellen Datum hinzufügen
        hours = time_from_qtimeedit.hour()
        minutes = time_from_qtimeedit.minute()
        seconds = time_from_qtimeedit.second()
        total_reclength = hours*3600 + minutes * 60 + seconds
        progfract = duration/total_reclength * 100

        self.gui.progressBar_fillPlaylist.setValue(int(np.floor(progfract)))
        if progfract > 100:
            self.gui.progressBar_fillPlaylist.setStyleSheet("QProgressBar::chunk "
                    "{"
                        "background-color: red;"
                    "}")
        elif progfract > 90:
            self.gui.progressBar_fillPlaylist.setStyleSheet("QProgressBar::chunk "
                    "{"
                        "background-color: yellow;"
                    "}")           
        else:
            self.gui.progressBar_fillPlaylist.setStyleSheet("QProgressBar::chunk "
                    "{"
                        "background-color: green;"
                    "}")

    def carrier_ix_changed(self):
        """_slot function of comboBox_cur_carrierfreq
        get corresponding carrier index and call playlist update
        """
        self.m["carrier_ix"] = self.gui.comboBox_cur_carrierfreq.currentIndex()
        print(f"carrier index changed to: {self.m['carrier_ix']}")
        self.fillplaylist()

    def fillplaylist(self):
        """update playlist of carrier with index self.m['carrier_ix']; clear old list and write new one
         :param: none
         :returns: none 
         """
        self.gui.listWidget_playlist.model().rowsInserted.disconnect(self.playlist_update_delayed)
        self.gui.listWidget_playlist.clear()
        ix = 0
        try:
            for x in self.readFileList[self.m["carrier_ix"]]:
                item = QtWidgets.QListWidgetItem()
                self.gui.listWidget_playlist.addItem(item)
                _item = self.gui.listWidget_playlist.item(ix)
                _item.setText(x)
                fnt = _item.font()
                fnt.setPointSize(11)
                _item.setFont(fnt)
                ix += 1
                #self.current_listdir = self.readFileList[self.m["carrier_ix"]]
        except:
            pass
        duration = self.show_playlength()
        self.show_fillprogress(duration)
        self.gui.listWidget_playlist.model().rowsInserted.connect(self.playlist_update_delayed)

    def show_context_menu(self, position):
        context_menu = QMenu(self.gui.listWidget_playlist)
        delete_action = context_menu.addAction("Delete")
        delete_action.triggered.connect(self.delete_selected_items)
        context_menu.exec_(self.gui.listWidget_playlist.viewport().mapToGlobal(position))

    def delete_selected_items(self):
        for item in self.gui.listWidget_playlist.selectedItems():
            self.gui.listWidget_playlist.takeItem(self.gui.listWidget_playlist.row(item))


    def on_rows_moved(self, parent, start, end, destinationParent, destinationRow):
        # calculate new position of the shifted items
        for i in range(start, end + 1):
            if destinationRow > start:
                new_index = destinationRow + (i - start) - 1
            else:
                new_index = destinationRow + (i - start)

            element = self.gui.listWidget_playlist.item(new_index).text()
            #print(f"Element '{element}' shifted from {i} to {new_index}")

    def show_playlength(self):
        """_update progress bar for total playlength for carrier with index [self.m['carrier_ix']
        """
        ix = 0
        duration = 0
        for x in self.readFileList[self.m["carrier_ix"]]:
            try:
                file_path =  self.readFilePath[self.m["carrier_ix"]][ix] + "/" + x
            except:
                print(f"show readFilePath index out of range at index: {self.m['carrier_ix']} [{ix}]")
                return duration
            if not len(self.readFilePath[self.m["carrier_ix"]][ix] + x) < 1:
                wav_info = self.get_wav_info(file_path)
                duration += wav_info['duration_seconds']
            else:
                print("NNNNNNNNNN")
            ix += 1

        # print(f"Spieldauer: {wav_info['duration_seconds']} Sekunden")
        # print(f"Anzahl der Kanäle: {wav_info['n_channels']}")
        # print(f"Abtastrate: {wav_info['framerate']} Hz")
        # print(f"Sample-Breite: {wav_info['sampwidth_bytes']} Bytes")
        # print(f"Datenformat: {wav_info['data_format']}")
        print(f"full duration of this carrier track: {duration}")
        return duration
        #TODO TODO: write progress bar update
        #for x in self.readFileList[self.m["carrier_ix"]]:
        #   open file
        #   read fileheader with test = WAVheader_tools.get_sdruno_header(self,self.m["f1"],'audio')
        #   close file
        #   calculate playtime from filesize and header info
        #   add to playtime
        #   set progress bar value and color on overtime
        #
        pass

    def carrierselect_update(self):
        #generate combobox entry list
        carrier_array = np.arange(self.cf_LO, self.cf_HI+1, self.c_step)
        carrierselector = carrier_array.tolist()
        self.gui.comboBox_cur_carrierfreq.clear()
        for cf in carrierselector:
            self.gui.comboBox_cur_carrierfreq.addItem(str(cf))


    def freq_carriers_update(self):
#         Vergrößern: append differenz zu vorher mal self.readFileList mit []
# 	Verkleinern: ermittle differenz zu vorher letzte self.readFileList Elemente
# Wenn letzte self.readFileList[-1] nicht empty  Warnug, dass alle bis auf die verbleibenden Lisetneiträge gelöscht werde, Proceed ? Cancel ?
# Wenn bestätigt:
# 			Delete letzte self.readFileList Elemente

        self.numcarriers_old = self.m["numcarriers"]
        numcar = self.gui.spinBox_numcarriers.value() 

        if numcar > self.numcarriers_old:
            #extend list
            curlen = self.numcarriers_old
            delta = numcar - self.numcarriers_old
            for i in range(delta):
                self.readFileList.append([])
                self.readFileList[curlen + i] = [] #TODO TODO TODO: CHECK: voher hatte ich -1 
                self.oldFileList.append([])
                self.oldFileList[curlen + i] = []
                self.readFilePath.append([])
                self.readFilePath[curlen + i] = []
        else:
            #TODO TODO TESTING ! delete n list elements and ask if that is wanted
            delta = self.numcarriers_old - numcar
            if not self.load_index:
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Question)
                msg.setText("Warning")
                msg.setInformativeText(f"you are about to delete the last {delta} carriers. The corresponding playlists will be removed. Do you want to proceed")
                msg.setWindowTitle("Delete carriers")
                msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                msg.buttonClicked.connect(self.popup)
                msg.exec_()

                if self.yesno == "&Yes":
                    for i in range(delta):
                        del self.readFileList[self.numcarriers_old - 1 - i]
                        del self.oldFileList[self.numcarriers_old - 1 - i]
                        del self.readFilePath[self.numcarriers_old - 1 - i]
                else:
                    self.gui.spinBox_numcarriers.valueChanged.disconnect(self.freq_carriers_update)
                    self.gui.spinBox_numcarriers.setProperty("value", self.numcarriers_old)
                    time.sleep(0.1)
                    self.gui.spinBox_numcarriers.valueChanged.connect(self.freq_carriers_update)
                    return False
            else:
                for i in range(delta):
                    del self.readFileList[self.numcarriers_old - 1 - i]
                    del self.oldFileList[self.numcarriers_old - 1 - i]
                    del self.readFilePath[self.numcarriers_old - 1 - i]

        self.m["numcarriers"] = numcar  
        self.cf_LO = int(self.gui.lineEdit_fc_low.text())
        self.c_step = int(self.gui.lineEdit_carrierdistance.text())
        self.cf_HI = self.cf_LO + (self.m["numcarriers"] - 1) * self.c_step
        self.carrierselect_update()

    def popup(self,i):
        """
        """
        self.yesno = i.text()

    def isfloat(self,num):
        try:
            float(num)
            return True
        except ValueError:
            auxi.standard_errorbox("invalid characters, must be numeric float value !")
            return False

    def isint(self,num):
        try:
            int(num)
            return True
        except ValueError:
            auxi.standard_errorbox("invalid characters, must be numeric integer value !")
            return False
    

    def audioBW_update(self):
        audioBW = self.gui.lineEdit_audiocutoff_freq.text()
        if not self.isfloat(audioBW):
            auxi.standard_errorbox("invalid characters, must be numeric float value !")
            return False
        else:
            self.m["audioBW"] = float(self.gui.lineEdit_audiocutoff_freq.text())
        if (self.m["audioBW"] < 2.5) or (self.m["audioBW"] > 16):
            auxi.standard_errorbox("audio bandwidth outside the range 2.5 - 16 kHz. Value must be in this interval, please cahnge")
            return False
        if (self.m["carrier_distance"] < 2*self.m["audioBW"]):
            auxi.standard_errorbox("carrier spacing is less than 2*audio bandwidth, this is not allowed, please either increase carrier spacing or reduce audio bandwidth")
            self.gui.lineEdit_audiocutoff_freq.setText(self.STD_AUDIOBW)
            return False
        self.m["audioBW"] = float(self.gui.lineEdit_audiocutoff_freq.text())
        self.freq_carriers_update()
        print(f"carrier spacing: {self.m['audioBW']}")

    def fc_low_update(self):
        #TODO TODO TODO: implement hibound, lowbound as lineEdit_LO - comboBox_targetSR/2
        fclowbound = 0
        fchibound = 1000
        fc_low = self.gui.lineEdit_fc_low.text()
        if not self.isint(fc_low):
            auxi.standard_errorbox("invalid characters, must be numeric integer value !")
            return False
        else:
            self.m["fc_low"] = float(self.gui.lineEdit_fc_low.text())
        if (self.m["fc_low"] < fclowbound) or (self.m["audioBW"] > fchibound):
            auxi.standard_errorbox(f"audio bandwidth outside the valid range. Value must be in this interval {str(fclowbound)} - {str(fclowbound)}, please cahnge")
            return False
        if (self.m["carrier_distance"] < 2*self.m["audioBW"]):
            auxi.standard_errorbox("carrier spacing is less than 2*audio bandwidth, this is not allowed, please either increase carrier spacing or reduce audio bandwidth")
            self.gui.lineEdit_fc_low.setText(self.STD_fclow)
            return False
        self.freq_carriers_update()
        self.m["fc_low"] = float(self.gui.lineEdit_fc_low.text())
        self.freq_carriers_update()
        print(f"carrier spacing: {self.m['fc_low']}")

    def carrierdistance_update(self):
        #TODO: check if integer !
        carrier_delta = self.gui.lineEdit_carrierdistance.text()
        if not self.isint(carrier_delta):
            auxi.standard_errorbox("invalid characters, must be numeric float value !")
            self.logger.error("plot_res_spectrum: wrong format of carrier distance")
            return False
        else:
            self.m["carrier_distance"] = float(self.gui.lineEdit_carrierdistance.text())
        
        if self.m["carrier_distance"] < 2*self.m["audioBW"]:
            auxi.standard_errorbox("carrier spacing is less than 2*audio bandwidth, please either increase carrier spacing or reduce audio bandwidth")
            self.gui.lineEdit_carrierdistance.setText(self.STD_CARRIERDISTANCE)
            return False
        self.m["carrier_distance"] = float(self.gui.lineEdit_carrierdistance.text())
        self.freq_carriers_update()
        print(f"carrier spacing: {self.m['carrier_distance']}")

    def select_tree(self):
        """
        initiates buildup of file selection tree
        :param : none
        :raises [ErrorType]:none
        :returns: none
        """  
        root_directory = QFileDialog.getExistingDirectory(self.m["QTMAINWINDOWparent"], "Please chose source file directory", self.default_directory)
        if root_directory:
            self.fillsourcelist(root_directory)
            self.m["metadata"]["last_audiosource_path"] = root_directory
            stream = open("config_wizard.yaml", "w")
            yaml.dump(self.m["metadata"], stream)
            stream.close()


    def add_children(self, parent, directory):
        for name in QDir(directory).entryList(QDir.NoDotAndDotDot | QDir.AllDirs):
            path = QDir(directory).absoluteFilePath(name)
            child = QTreeWidgetItem(parent, [name])
            child.setData(0, Qt.UserRole, path)
            self.add_children(child, path)

    # def on_tree_item_clicked(self, item, column):
    #     path = item.data(0, Qt.UserRole)
    #     #self.gui.listWidget_playlist.clear()
    #     for name in QDir(path).entryList(QDir.NoDotAndDotDot | QDir.Files):
    #         self.gui.listWidget_playlist.addItem(name)

    def fillsourcelist(self, rootdir):
        self.gui.listWidget_sourcelist.clear()
        item = QtWidgets.QListWidgetItem()
        self.gui.listWidget_sourcelist.addItem(item)
        ix = 0
        for x in os.listdir(rootdir):
            if x.endswith(".wav"):
                if True: #x != (self.m["my_filename"] + self.m["ext"]): #TODO: obsolete old form when automatically loading opened file to playlist
                    _item = self.gui.listWidget_sourcelist.item(ix)
                    _item.setText(x)
                    fnt = _item.font()
                    fnt.setPointSize(11)
                    _item.setFont(fnt)
                    item = QtWidgets.QListWidgetItem()
                    self.gui.listWidget_sourcelist.addItem(item)
                    ix += 1
                    self.current_listdir = rootdir

    def playlist_update_delayed(self,dum,first,last):
        print(f"playlist_update, signal addrow: first ix: {first}, last ix: {last}")
        QTimer.singleShot(0, self.playlist_update)

    def playlist_update(self):
        """_currently loaded playlist in self.gui.listWidget_playlist is bering transferred 
        to the central list of playlists self.readFileList[self.m["carrier_ix"]]. Then playlist_purge()
        is called
        """
 
        try:
            self.oldFileList[self.m["carrier_ix"]] = copy.deepcopy(self.readFileList[self.m["carrier_ix"]])
            #TODO TODO TODO: Bei Indexerhöhung muss ein dummy self.oldFileList[self.m["carrier_ix"]] mit dem erhöhten Index angelegt werden, sonst stürzt später due diff-Methode in purge ab
        except:
            self.oldFileList = []

        self.readFileList[self.m["carrier_ix"]] = [self.gui.listWidget_playlist.item(i).text() for i in range(self.gui.listWidget_playlist.count())]
        self.playlist_purge()
        duration = self.show_playlength()
        self.show_fillprogress(duration)

        print("playlist_update")
        # try:
        #     for file in readFileList:
        #         with open(file) as lstf:
        #             filesRead = lstf.read()
        #             print(filesRead)
        #             # return(filesReaded)

        # except Exception as e:
        #     print("the selected file is not readable because :  {0}".format(e)) 

    def playlist_purge(self):
        """_update path information in self.readFilePath for the corresponding readFileList at index  self.m['carrier_ix']
        """
        ix_diff = self.find_first_difference(self.oldFileList[self.m["carrier_ix"]] , self.readFileList[self.m["carrier_ix"]] )
        try:
            if len(self.readFileList[self.m["carrier_ix"]] ) <= len(self.oldFileList[self.m["carrier_ix"]] ):
                self.readFilePath[self.m["carrier_ix"]] = self.delete_at_index(self.readFilePath[self.m["carrier_ix"]], ix_diff)
            else:
                self.readFilePath[self.m["carrier_ix"]] = self.insert_or_append(self.readFilePath[self.m["carrier_ix"]], ix_diff, self.current_listdir)
            print(f"playlist purge: change index: {ix_diff}, playlist: {self.readFileList[self.m['carrier_ix']] }, pathlist: {self.readFilePath[self.m['carrier_ix']]}")
        except:
            print("playlist purge: no difference, no action")

    def insert_or_append(self,pathlist, ix, element):

        if ix < len(pathlist):
            pathlist.insert(ix, element)
        else:
            pathlist.append(element)
        return pathlist

    def delete_at_index(self,pathlist, ix):
        if 0 <= ix < len(pathlist):
            del pathlist[ix]
        return pathlist

    def find_first_difference(self, list1, list2):
        min_length = min(len(list1), len(list2))

        for i in range(min_length):
            if list1[i] != list2[i]:
                return i

        if len(list1) != len(list2):
            return min_length

        return None  # Die Listen sind identisch
    
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
        if _key.find("cm_synthesizer") == 0 or _key.find("cm_all_") == 0:
            #set mdl-value
            self.m[_value[0]] = _value[1]
        if _key.find("cui_synthesizer") == 0:
            _value[0](_value[1]) #STILL UNCLEAR
        if _key.find("cexex_synthesizer") == 0  or _key.find("cexex_all_") == 0:
            if  _value[0].find("updateGUIelements") == 0:
                self.updateGUIelements()
            if  _value[0].find("reset_GUI") == 0:
                self.reset_GUI()
            if  _value[0].find("logfilehandler") == 0:
                self.logfilehandler(_value[1])
            # if  _value[0].find("canvasbuild") == 0:
            #     self.canvasbuild(_value[1])

            #handle method
            # if  _value[0].find("plot_spectrum") == 0: #EXAMPLE
            #     self.plot_spectrum(0,_value[1])   #EXAMPLE

    # def canvasbuild(self,gui):
    #     """
    #     sets up a canvas to which graphs can be plotted
    #     Use: calls the method auxi.generate_canvas with parameters self.gui.gridlayoutX to specify where the canvas 
    #     should be placed, the coordinates and extensions in the grid and a reference to the QMainwidget Object
    #     generated by __main__ during system startup. This object is relayed via signal to all modules at system initialization 
    #     and is automatically available (see rxhandler method)
    #     the reference to the canvas object is written to self.cref
    #     :param : gui
    #     :type : QMainWindow
    #     :raises [ErrorType]: [ErrorDescription]
    #     :return: none
    #     :rtype: none
    #     """
    #     #TODO: activate call correctly, this is just an example
    #     #self.cref = auxi.generate_canvas(self,self.gui.gridLayout_5,[6,0,6,4],[-1,-1,-1,-1],gui)
    #     pass


    def logfilehandler(self,_value):
        if _value is False:
            self.logger.debug("abstract module: INACTIVATE LOGGING")
            self.logger.setLevel(logging.ERROR)
        else:
            self.logger.debug("abstract module: REACTIVATE LOGGING")
            self.logger.setLevel(logging.DEBUG)


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
        print("synthesizer: updateGUIelements")
        #self.gui.DOSOMETHING

    def reset_GUI(self):
        pass

#TODO: 
# - Preset band Funktionen einbauen
# - im alten Synthesizer: jeder Carrier muss ein wav-File mit voller Spiellänge haben
#       nun wanted: Jeder Carrier hat eine eigene Playlist mit den vollen Pfadangaben aller Files
#   (1) Jede Playlist ist indiziert mit einem Index entsprechend dem Carrier, der gerade eingestellt ist; ein Label für die aktive Playlist wird irgendwo angezeigt
#   (2) Jede Playlist hat auch eine pathlist assoziiert, in der die Pfadnamen stehen
#   (3) wenn der Carrier gewechselt wird, wird die entsprechende Target Playlist angezeigt
#          Bei drag and drop soll das File nicht aus der Sourcelist verschwinden
#
#
# Jedes File der Playlist wird gecheckt, ob es einen gültigen wavheader hat und die Spieldauer wird aus dem Header und der Filesize ermittelt:
# wavheader-tool getsdruno_header() wurde erweitert, um auch Audio-header auszulesen
# test = WAVheader_tools.get_sdruno_header(self,self.m["f1"],'audio')
