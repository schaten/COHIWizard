"""
Created on Feb 25 2024

#@author: scharfetter_admin
"""

import os
import numpy as np
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
import yaml
from auxiliaries import WAVheader_tools
from auxiliaries import auxiliaries as auxi
import system_module as wsys

class yamleditor_m(QObject):
    __slots__ = ["None"]
    SigModelXXX = pyqtSignal()

    #TODO: replace all gui by respective state references if appropriate
    def __init__(self):
        super().__init__()
        # Constants
        self.CONST_SAMPLE = 0 # sample constant
        self.mdl = {}
        self.mdl["sample"] = 0


class  yamleditor_m(QObject):
    __slots__ = ["None"]
    SigModelXXX = pyqtSignal()

    #TODO: replace all gui by respective state references if appropriate
    def __init__(self):
        super().__init__()
        # Constants
        self.CONST_SAMPLE = 0 # sample constant
        self.mdl = {}
        self.mdl["sample"] = 0

class  yamleditor_c(QObject):
    """_view method
    """
    __slots__ = ["contvars"]

    SigAny = pyqtSignal()

    def __init__(self, yamleditor_m): #TODO: remove gui
        super().__init__()

    # def __init__(self, *args, **kwargs): #TEST 09-01-2024
    #     super().__init__(*args, **kwargs)
        viewvars = {}
        #self.set_viewvars(viewvars)
        self.m =  yamleditor_m.mdl


    def  write_yaml_header(self,dummy):
        """
        CONTROLLER
        ###DESCRIPTION
        :param : dummy
        :type : none
        :raises [ErrorType]: [ErrorDescription]
        :return: True/False on successful/unsuccesful operation
        :rtype: Boolean
        """
        # treat yaml header
        #if self.flag_ann_completed == False:  #TODO: check if this should only be available if annotation is completed or already before
        #    return
        system_state = sys_state.get_status()
        if len(self.cohiradia_yamlheader_filename) >=256:
            auxi.standard_errorbox("file path/name is longer than 256 characters, cannot proceed with yaml headers. This may cause significant problems when using the annotator. Please use less deeply nested paths for your files")
            #system_state["f1"] =""
            self.reset_GUI()
            #TODO: close file reset GU totally
            sys_state.set_status(system_state)
            return False

        if os.path.exists(self.cohiradia_yamlheader_filename) == True:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Question)
            msg.setText("overwrite file")
            msg.setInformativeText("you are about to overwrite the existing yaml header file. Do you want to proceed")
            msg.setWindowTitle("FILE OPEN")
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msg.buttonClicked.connect(self.popup)
            msg.exec_()
            if self.yesno == "&No":
                sys_state.set_status(system_state)
                return False

        if os.path.exists(self.cohiradia_yamlheader_filename) == False:         #exist yaml file: create from yaml-editor
            self.cohiradia_yamlheader_dirname = self.my_dirname + '/' + self.annotationdir_prefix + self.my_filename
            if os.path.exists(self.cohiradia_yamlheader_dirname) == False:
                os.mkdir(self.cohiradia_yamlheader_dirname)

            
        with open(self.cohiradia_yamlheader_filename, 'w', encoding='utf-8') as f:
            #prefix = '###/' #TODO: remove
            prefix = self.gui.tableWidget_YAMLHEADER.item(13, 0).text()
            uri_string = 'uri: "{}"\n'.format(prefix + '/' + self.my_filename + '.wav')
            dt_now = self.wavheader['starttime_dt']
            recdatestr = str(dt_now.strftime('%Y-%m-%d')) + 'T'  + str(dt_now.strftime('%H:%M:%S')) + '+###UTC OFFSET###'  #TODO: automatci UTC offset ?
            #
            recdate = 'recording-date: "{}"\n'.format(recdatestr) ###TODO take from wav-header
            duration = np.round(self.wavheader['data_nChunkSize']/self.wavheader['nAvgBytesPerSec'])
            flow = np.round((self.wavheader["centerfreq"] - self.wavheader["nSamplesPerSec"]/2)/1000,decimals = 2)
            fhigh = np.round((self.wavheader["centerfreq"] + self.wavheader["nSamplesPerSec"]/2)/1000,decimals = 2)
            bandstr = self.gui.tableWidget_YAMLHEADER.item(2, 0).text()
            band = 'band: "{}"\n'.format(bandstr)
            frequnit = 'frequency-unit: "{}"\n'.format('kHz')
            enc = 'encoding: "{}"\n'.format('ci16')
            cfreq = np.round(self.wavheader["centerfreq"]/1000,decimals = 2)
            bw = self.wavheader["nSamplesPerSec"]/1000
            antennastr = self.gui.tableWidget_YAMLHEADER.item(3, 0).text()
            antenna = 'antenna: "{}"\n'.format(antennastr)         
            rectypestr = self.gui.tableWidget_YAMLHEADER.item(4, 0).text()
            rectype = 'recording-type: "{}"\n'.format(rectypestr)
            remarkstr = self.gui.tableWidget_YAMLHEADER.item(1, 0).text()
            remark = 'remark: "{}"\n'.format(remarkstr)
            contentstr = self.gui.tableWidget_YAMLHEADER.item(0, 0).text()
            content = 'content: "{}"\n'.format(contentstr)

            f.write('---\n')
            f.write('id: \n')
            f.write(uri_string)
            f.write(recdate)
            f.write('duration: ' + str(duration) + '\n')
            f.write(band)
            f.write(frequnit)
            f.write('frequency-low: ' + str(flow) + '\n')
            f.write('frequency-high: ' + str(fhigh) + '\n')
            f.write('frequency-correction: 0.0' + '\n')
            f.write(enc)
            f.write('center-frequency: ' + str(cfreq) + '\n')
            f.write('bandwidth: ' + str(bw) + '\n')
            f.write(antenna)
            f.write(rectype)
            f.write(remark)
            f.write(content)
            f.write('radio-stations:\n')
            f.close()

        # treat yaml tailer
        #if os.path.exists(self.cohiradia_yamltailer_filename) == False:         #if not exist yaml file: create from yaml-editor
        with open(self.cohiradia_yamltailer_filename, 'w', encoding='utf-8') as f:
            RXlongitudestr = self.gui.tableWidget_YAMLHEADER.item(7, 0).text()
            RXlongitude = 'location-longitude: "{}"\n'.format(RXlongitudestr)     
            RXlatitudestr = self.gui.tableWidget_YAMLHEADER.item(8, 0).text()
            RXlatitude = 'location-latitude: "{}"\n'.format(RXlatitudestr)
            if "\"" in RXlatitudestr or "\"" in RXlongitudestr:
                auxi.standard_errorbox("\' \" \' is not allowed in the yaml file. Please replace by two single quotes, i.e.:  \'\'")
                sys_state.set_status(system_state)
                return
            RXQTHstr = self.gui.tableWidget_YAMLHEADER.item(9, 0).text()
            RXQTH = 'location-qth: "{}"\n'.format(RXQTHstr)
            RXcountrystr = self.gui.tableWidget_YAMLHEADER.item(10, 0).text()
            RXcountry = 'location-country: "{}"\n'.format(RXcountrystr)
            RXcitystr = self.gui.tableWidget_YAMLHEADER.item(11, 0).text()
            RXcity = 'location-city: "{}"\n'.format(RXcitystr)
            memberstr = self.gui.tableWidget_YAMLHEADER.item(12, 0).text()
            member_ = 'upload-user-fk: "{}"\n'.format(memberstr)
            filtersstr = self.gui.tableWidget_YAMLHEADER.item(5, 0).text()
            filters = 'filters: "{}"\n'.format(filtersstr)
            preampsetstr = self.gui.tableWidget_YAMLHEADER.item(6, 0).text()
            preampset = 'preamp-settings: "{}"\n'.format(preampsetstr)                
            f.write(RXlongitude)
            f.write(RXlatitude)
            f.write(RXQTH)
            f.write(RXcountry)
            f.write(RXcity)
            f.write(member_)
            f.write(filters)
            f.write(preampset)
            f.close()

        if os.path.exists(self.cohiradia_metadata_filename) == True:
        #TODO: alternative, more strict only after completion of annotation if self.flag_ann_completed = True
            #concatenate files
            filenames = [self.cohiradia_yamlheader_filename, self.cohiradia_metadata_filename , self.cohiradia_yamltailer_filename]
            with open(self.cohiradia_yamlfinal_filename, 'w', encoding='utf-8') as outfile:   
                for fname in filenames:
                    with open(fname, 'r', encoding='utf-8') as infile:
                        for line in infile:
                            outfile.write(line)


class  yamleditor_v(QObject):
    """_view methods for resampling module
    TODO: gui.wavheader --> something less general ?
    """
    __slots__ = ["viewvars"]

    SigAny = pyqtSignal()
    SigCancel = pyqtSignal()
    SigUpdateGUI = pyqtSignal(object)
    SigSyncGUIUpdatelist = pyqtSignal(object)

    def __init__(self, gui,  yamleditor_c,  yamleditor_m):
        super().__init__()

        #viewvars = {}
        #self.set_viewvars(viewvars)
        self.m =  yamleditor_m.mdl
        self.DATABLOCKSIZE = 1024*32
        self.gui = gui #gui_state["gui_reference"]#system_state["gui_reference"]
        self.yamleditor_c = yamleditor_c

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
        print(" yamleditor: updateGUIelements")
        #self.gui.DOSOMETHING

    def yaml_header_buttonfcn(self):
        """
        VIEW
        """
        self.yamleditor_c.write_yaml_header(self)
        #TODO: write yaml_directory on demand ?

    def read_yaml_header(self,dummy):
        """
        VIEW
        ###DESCRIPTION
        :param : dummy
        :type : none
        :raises [ErrorType]: [ErrorDescription]
        :return: none
        :rtype: none
        """

        # if self.flag_ann_completed == False:
        #     return
        nofile_flag = False
        #print('read info from existing yaml-headerfile to editor table')
        try:
            stream = open(self.cohiradia_yamlheader_filename, "r", encoding="utf8")
            self.yamlheader_ = yaml.safe_load(stream)
            stream.close()
            self.gui.tableWidget_YAMLHEADER.item(0, 0).setText(str(self.yamlheader_['content']))
            self.gui.tableWidget_YAMLHEADER.item(1, 0).setText(str(self.yamlheader_['remark']))
            self.gui.tableWidget_YAMLHEADER.item(2, 0).setText(str(self.yamlheader_['band']))
            self.gui.tableWidget_YAMLHEADER.item(3, 0).setText(str(self.yamlheader_['antenna']))
            self.gui.tableWidget_YAMLHEADER.item(4, 0).setText(str(self.yamlheader_['recording-type']))
            prefix = self.yamlheader_['uri'].split('/')[0]
            self.gui.tableWidget_YAMLHEADER.item(12, 0).setText(str(prefix))
        except:
            nofile_flag = True
            #return False        
        try:
            stream = open(self.cohiradia_yamltailer_filename, "r", encoding="utf8")
            self.yamltailer_ = yaml.safe_load(stream)
            stream.close()
            self.gui.tableWidget_YAMLHEADER.item(5, 0).setText(str(self.yamltailer_['filters']))
            self.gui.tableWidget_YAMLHEADER.item(6, 0).setText(str(self.yamltailer_['preamp-settings']))
            self.gui.tableWidget_YAMLHEADER.item(7, 0).setText(str(self.yamltailer_['location-longitude']))
            self.gui.tableWidget_YAMLHEADER.item(8, 0).setText(str(self.yamltailer_['location-latitude']))
            self.gui.tableWidget_YAMLHEADER.item(9, 0).setText(str(self.yamltailer_['location-qth']))  ## location-qth ist das noch nie verwendete Keyword
            self.gui.tableWidget_YAMLHEADER.item(10, 0).setText(str(self.yamltailer_['location-country']))                
            self.gui.tableWidget_YAMLHEADER.item(11, 0).setText(str(self.yamltailer_['location-city']))
            self.gui.tableWidget_YAMLHEADER.item(12, 0).setText(str(self.yamltailer_['upload-user-fk']))
        except:
            nofile_flag == True
            #return False
        #TODO: write yaml_directory on demand only
        if nofile_flag == True: #TODO remove if unnecessary after tests 23-02-2024; no unnecessary creation of ANN_folders
            pass
            #self.write_yaml_header(self)
        self.gui.pushButton_Writeyamlheader.setEnabled(True)
