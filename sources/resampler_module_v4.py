import numpy as np
import time
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
import datetime as ndatetime
import os 
import subprocess
import shutil
from matplotlib.patches import Rectangle
from SDR_wavheadertools_v2 import WAVheader_tools
import system_module as wsys


#methods for wavheader manipulations 

# beforechange 16_11_2023: class soxwriter(QObject):
class res_workers(QObject):
    """ worker class for data streaming thread from PC to STEMLAB
    object for playback and recording thread
    :param : no regular parameters; as this is a thread worker communication occurs via
        __slots__: Dictionary with entries:
        __slots__[0]: soxstring Type: str
        __slots__[1]: return string from sox execution, type : str
    '''
    :raises [ErrorType]: none
    '''
        :return: none
        :rtype: none
    """
    __slots__ = ["soxstring", "ret","tfname","expfs","progress","sfilename","readoffset","readsegmentfn","sSR","centershift","sBPS","tBPS","wFormatTag"]

    SigFinished = pyqtSignal()
    SigPupdate = pyqtSignal()
    SigFinishedLOshifter = pyqtSignal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sys_state = wsys.status()
        self.system_state = self.sys_state.get_status()
        gui = self.system_state["gui_reference"]
 
    def set_soxstring(self,_value):
        self.__slots__[0] = _value
    def get_soxstring(self):
        return(self.__slots__[0])
    def set_ret(self,_value):
        self.__slots__[1] = _value
    def get_ret(self):
        return(self.__slots__[1])
    def set_tfname(self,_value):
        self.__slots__[2] = _value
    def get_tfname(self):
        return(self.__slots__[2])
    def set_expfs(self,_value):
        self.__slots__[3] = _value
    def get_expfs(self):
        return(self.__slots__[3])
    def set_progress(self,_value):
        self.__slots__[3] = _value
    def get_progress(self):
        return(self.__slots__[3])
    def set_sfname(self,_value):
        self.__slots__[4] = _value
    def get_sfname(self):
        return(self.__slots__[4])
    def set_readoffset(self,_value):
        self.__slots__[5] = _value
    def get_readoffset(self):
        return(self.__slots__[5])
    def set_readsegment(self,_value):
        self.__slots__[6] = _value
    def get_readsegment(self):
        return(self.__slots__[6])
    def set_sSR(self,_value):
        self.__slots__[7] = _value
    def get_sSR(self):
        return(self.__slots__[7])
    def set_centershift(self,_value):
        self.__slots__[8] = _value
    def get_centershift(self):
        return(self.__slots__[8])
    def set_sBPS(self,_value):
        self.__slots__[9] = _value
    def get_sBPS(self):
        return(self.__slots__[9])
    def set_tBPS(self,_value):
        self.__slots__[10] = _value
    def get_tBPS(self):
        return(self.__slots__[10])
    def set_wFormatTag(self,_value):
        self.__slots__[11] = _value
    def get_wFormatTag(self):
        return(self.__slots__[11])

    def sox_writer(self):

        print("#############sox_worker as sox_writer started##############")
        soxstring = self.get_soxstring()
        ret = subprocess.Popen(soxstring + " > logsox.txt", shell = True)
        self.set_ret(ret)
        time.sleep(1)
        print(ret)
        targetfilename = self.get_tfname()
        expected_filesize = self.get_expfs()
        print(targetfilename)
        print(expected_filesize)
        #self.SigStarted.emit()
        if os.path.exists(targetfilename) == True:
            print("temp file has been created")
            file_stats = os.stat(targetfilename)
            rel_finish = int(np.floor(100*file_stats.st_size/expected_filesize))
            progress_old = 0
            loop_ix = 0
            deltaold = 0
            #Bedingung: Delta size 
            while (file_stats.st_size < (expected_filesize - 2000)) and loop_ix < 20:  #HACK TODO: analyze why expected filesize is by > 1000 smaller than the one produced by sox 
                delta = file_stats.st_size - expected_filesize
                # if sox has finished but expected filesize is not reached, wait 20 cycles and then terminate
                if (deltaold == delta) and file_stats.st_size >0:
                    loop_ix += 1
                    #print(f"soxloop deltacount (break at 20): {loop_ix}")
                deltaold = delta
                file_stats = os.stat(targetfilename)
                rel_finish = int(np.floor(100*file_stats.st_size/expected_filesize))
                #print("resampling process running")
                time.sleep(0.5)
                print(f"resample: bytes resampled: {file_stats.st_size} / {expected_filesize}")
                progress = rel_finish
                if not progress > 0:
                    progress = 5
                    self.set_progress(progress)
                    self.SigPupdate.emit()
                #print(f"relative filesize in %: {progress}")
                if progress - progress_old > 5:
                    progress_old = progress
                    self.set_progress(progress)
                    self.SigPupdate.emit()
                    #print("NOW UPDATE STATUSBAR#############################################################################")

        else:
            print(f"ERROR: no file {targetfilename} created")
        print("success")
        time.sleep(0.5)
        print("#############sox_worker as sox_writer finished##############")
        self.SigFinished.emit()

    def LO_shifter_worker(self):
        DATABLOCKSIZE = 1024*4*256
        INCREMENT = 200000
        print("#############LOshifter_worker started##############")
        targetfilename = self.get_tfname()
        try:
            target_fileHandle = open(targetfilename, 'ab')
        except:
            print("cannot open resampling temp file")
            return False
        sourcefilename = self.get_sfname()
        try:
            source_fileHandle = open(sourcefilename, 'rb')
        except:
            print("cannot open resampling source file")
            return False
        readoffset = self.get_readoffset()
        source_fileHandle.seek(readoffset, 1)
        expected_filesize = self.get_expfs()
        readsegmentfn = self.get_readsegment()
        centershift = self.get_centershift()
        #print(f"centershift: <<<<<<<<<<<<<<<<<<<<<<<{centershift}>>>>>>>>>>>>>>>>>")
        sBPS = self.get_sBPS()
        tBPS = self.get_tBPS()
        wFormatTag = self.get_wFormatTag()
        position = 0
        #TODO: replace following by new readsegment call
        #ret = readsegmentfn(position,DATABLOCKSIZE) #TODO: transfer to auxiliary block
        #TODO: , define new readsegment-function, generalize to tBPS rather than 32 bit
        ret = readsegmentfn(sourcefilename,position,DATABLOCKSIZE,sBPS,32,wFormatTag)
        
        sSR = self.get_sSR()
        # print(f"LOshifter worker sSR: {sSR} sBPS: {sBPS} expfilesz: {expected_filesize}")
        # print(f"LOshifter worker souce: {sourcefilename} target: {targetfilename} ")
        # print(f"LOshifter worker centershift: {centershift} readoffset: {readoffset} ")
  
        dt = 1/sSR
        segment_tstart = 0
        print(targetfilename)
        print(expected_filesize)
        if os.path.exists(targetfilename) == True:
            print("LOshift worker: target file has been found")
            file_stats = os.stat(targetfilename)
            progress_old = 0
            fsize_old = 0
            while ret["size"] > 0:
                #TODO: implement cutstart/stop here
                # cutstartoffset = seconds(cutstart);
                ld = len(ret["data"])  #TODO: remove and replace [0:ld:2] by [0::2]
                y_sh = np.empty(len(ret["data"]), dtype=np.float32)
                if abs(centershift) > 1e-5:
                    #print("LOworker shifting active")
                    rp = ret["data"][0:ld-1:2]
                    ip = ret["data"][1:ld:2]
                    y = rp +1j*ip        
                    tsus = np.arange(segment_tstart, segment_tstart+len(y)*dt, dt)[:len(y)]
                    segment_tstart = tsus[len(tsus)-1] + dt
                    phasescaler = np.exp(2*np.pi*1j*centershift*tsus)
                    ys = np.multiply(y,phasescaler)
                    y_sh[0:ld:2] = (np.copy(np.real(ys)))
                    y_sh[1:ld:2] = (np.copy(np.imag(ys)))  
                else:   #if no frequency shift, just copy data to temp file as they are
                    #print("LOworker no shift, just dummy copy")
                    y_sh = np.copy(ret["data"])
                y_sh.tofile(target_fileHandle)
                #TODO: check if this is always meaningful (32 bit)
                if 2*ret["size"]/(sBPS/4) == DATABLOCKSIZE:
                    position = position + ret["size"]
                    ret = readsegmentfn(sourcefilename,position,DATABLOCKSIZE,sBPS,32,wFormatTag)
                else:
                    ret["size"] = 0
                file_stats = os.stat(targetfilename)
                progress = int(np.floor(100*file_stats.st_size/expected_filesize))
                print("LOshifting worker process running")
                time.sleep(0.001)

                print(f"absolute filesize: {file_stats.st_size}")
                print(f"relative filesize in %: {progress}")
                #delta = progress - progress_old
                #absolute delta for independence of refresh rate of filesize
                delta = file_stats.st_size - fsize_old
                print(f"progress delta: {delta} progress: {progress} progress_old: {progress_old}")
                #if delta > 4: #TODO: mod 5 operation einbauen

                if delta > INCREMENT: 
                    progress_old = progress
                    fsize_old = file_stats.st_size
                    self.set_progress(progress)
                    self.SigPupdate.emit()
                    print(f"LOshifter worker sSR: {sSR} sBPS: {sBPS} expfilesz: {expected_filesize}")
                    print(f"LOshifter worker souce: {sourcefilename} target: {targetfilename} pupdate_reference: {readsegmentfn}")
                    print(f"LOshifter worker centershift: {centershift} readoffset: {readoffset} ")  
                    print("LOshifter worker: NOW UPDATE STATUSBAR#############################################################################")
                
        else:
            print("LOshift worker: target file has not been found")
            print(f"ERROR: no file {targetfilename} created")
            print("success")
            time.sleep(0.1)
        source_fileHandle.close()    
        target_fileHandle.close()
        print("#############Loshifter_worker finished##############")
        time.sleep(1)
        self.SigFinishedLOshifter.emit()



class resampler(QObject):
    """_methods for resampling (= resampling controller)
    this class defines a state machine for variable sequences of tasks during several different modes of resampling
    the class methods communicate via the class variables of the central data class 'status' and via signalling.
    the state machine is defined via the scheduler method which needs to be configured and launched via a signal from the main thread (here the main GUI)
    """
    __slots__ = ["LOvars"]
    SigUpdateGUI = pyqtSignal()
    SigGP = pyqtSignal()
    SigResample = pyqtSignal()
    SigAccomplish = pyqtSignal()
    SigLOshift = pyqtSignal()
    SigProgress = pyqtSignal()
    Sigincrscheduler = pyqtSignal()
    SigTerminate_Finished = pyqtSignal()

    #TODO: replace all gui by respective state references if appropriate

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Constants
        self.TEST = True
        LOvars = {}
        self.set_LOvars(LOvars)
        self.sys_state = wsys.status()
        self.system_state = self.sys_state.get_status()
        gui = self.system_state["gui_reference"]
        self.SigProgress.connect(lambda: view_resampler.updateprogress_resampling(self))#TODO: untersuchen, ob Abonnieren besser vom GUI aus geschehen soll
        self.MAX_TARGETFILE_SIZE = 2 * 1024**3 #2GB max output filesize
    def set_LOvars(self,_value):
        self.__slots__[0] = _value

    def get_LOvars(self):
        return(self.__slots__[0])
    
    def resamp_configheader(self,wavheader,header_config):
        """inserts fields specified in header_config into wavheader
        :param: wavheader: dict of type wav_header (see main gui)
        :type: dict
        :param: header_config: list of fiels: wFormatTag; data_chkID, sdrtype_chckID, sdr_nChunksize, nBitsPerSample, nBlockalign, readoffset, centerfreq
        :type: dict
        ...
        :raises: none
        ...
        :return: mod_header (format wav_header)
        :rtype: dict
        """
        mod_header = wavheader
        mod_header['wFormatTag'] = header_config[0]
        mod_header['data_ckID'] = header_config[1]
        mod_header['sdrtype_chckID'] = header_config[2]
        mod_header['sdr_nChunkSize'] = header_config[3]
        mod_header["nBitsPerSample"] = header_config[4]
        mod_header['nBlockAlign'] = header_config[5]
        sizescaler = mod_header['nBlockAlign']/wavheader['nBlockAlign']
        mod_header['nAvgBytesPerSec'] = int(np.floor(mod_header['nAvgBytesPerSec'] * sizescaler))
        mod_header['filesize'] = int(np.floor((wavheader['filesize'] - header_config[6])*sizescaler + header_config[6]))
        mod_header['data_nChunkSize'] = mod_header['filesize'] - header_config[6] + 8
        mod_header['centerfreq'] = header_config[7]
        return mod_header
    
    def LOshifter_new(self):
        print("configure LOshifter _new reached")
        #sys_state = wsys.status()
        system_state = self.sys_state.get_status()
        #system_flags = self.sys_state.get_flags() #obsolete
        schedule_objdict = system_state["schedule_objdict"]
        schedule_objdict["signal"]["LOshift"].disconnect(schedule_objdict["connect"]["LOshift"])
        gui = system_state["gui_reference"]
        source_fn = system_state["source_fn"]  #TODO: define im GUI_Hauptprogramm bzw. im scheduler
        target_fn = system_state["target_fn"]
        s_wavheader = system_state["s_wavheader"]
        #system_state["actionlabel"] = "LO SHIFTING"
        system_state["progress_source"] = "sox"  #TODO: muss geändert werden ist das überhaupt nötig ?
        self.sys_state.set_status(system_state)
        expected_filesize = system_state["t_filesize"]
        print("configure LOshifter thread et al")
        self.LOshthread = QThread(parent = self)
        self.LOsh_worker = res_workers()
        self.LOsh_worker.moveToThread(self.LOshthread)
        self.LOsh_worker.set_ret("") #TODO: check if necessary, probably not
        self.LOsh_worker.set_tfname(target_fn )
        self.LOsh_worker.set_sfname(source_fn )
        self.LOsh_worker.set_readoffset(gui.readoffset ) #TODO: reference to system state, nou gui element
        self.LOsh_worker.set_sSR(system_state["sSR"])
        self.LOsh_worker.set_sBPS(system_state["sBPS"])
        self.LOsh_worker.set_tBPS(system_state["tBPS"])
        self.LOsh_worker.set_wFormatTag(system_state["wFormatTag"])
        self.LOsh_worker.set_centershift(system_state["fshift"])
        self.LOsh_worker.set_expfs(expected_filesize)
        self.LOsh_worker.set_readsegment(gui.readsegment_new)
        self.LOsh_worker.set_sBPS(system_state["sBPS"])
        self.LOshthread.started.connect(self.LOsh_worker.LO_shifter_worker)
        self.Sigincrscheduler.connect(self.res_scheduler)
        self.LOsh_worker.SigFinishedLOshifter.connect(lambda: self.Sigincrscheduler.emit())
        #z.B. schreibe die Referenz auf signal_state, damit sie der Scheduler dort abholen kann, schedule[n].["startsignal"] = diese Referenz
        self.LOsh_worker.SigPupdate.connect(lambda: view_resampler.updateprogress_resampling(self)) #TODO: eher aus der Klasse view, könnte auch ausserhalb geschehen
        self.LOsh_worker.SigFinishedLOshifter.connect(self.LOshthread.quit)
        self.LOsh_worker.SigFinishedLOshifter.connect(self.LOsh_worker.deleteLater)
        self.LOshthread.finished.connect(self.LOshthread.deleteLater)
        system_state["calling_worker"] = self.LOsh_worker 

        print("about to leave LOshifter actionmethod")
        self.sys_state.set_status(system_state)
        time.sleep(0.0001)
        self.LOshthread.start()
        if self.LOshthread.isRunning():
            print("LOsh thread started")
        time.sleep(0.01) # wait state so that the soxworker has already opened the file
        print("LOshifter action method sleep over")

    

    def progressupdate_interface(self):
        # Lies soxworker progress und pass zu updateprogress_resampling
        #print(">>>>>>>>>>>>>>>>>>>>progressupdate_interface reached")
        #print("#############################")
        system_state = self.sys_state.get_status()
        #change 26_11_2023: beforechange: progress = system_state["sox_worker"].get_progress()
        progress = system_state["calling_worker"].get_progress()
        #system_flags = self.sys_state.get_flags() #obsolete
        system_state["progress"] = progress
        system_state["progress_source"] = "normal"
        self.sys_state.set_status(system_state)

    def resample(self):
        """_generate soxstring from parameters
            configurates and starts sox execution thread
            generates wavheader for the target file to be generated            
            gui: reference to main window object (WizardGUI)
            target_fn: target filename
            source_fn: source filename
            s_wavheader: same type as wavheader produced by SDR_wavheadertools
            tSR: target sampling rate in S/s
            tLO: target center freqiency in Hz
            sys_state: communication dictionary of data class status; accessed only by get and set methods
        :param: none
        :type: none
        ...
        :raises
        ...
        :return: target_fn
        :rtype: string
        """

        system_state = self.sys_state.get_status()        
        schedule_objdict = system_state["schedule_objdict"]
        schedule_objdict["signal"]["resample"].disconnect(schedule_objdict["connect"]["resample"])

        gui = system_state["gui_reference"]
        s_wavheader = system_state["s_wavheader"]  #TODO: define im GUI_Hauptprogramm bzw. im scheduler
        source_fn = system_state["source_fn"]  #TODO: define im GUI_Hauptprogramm bzw. im scheduler
        target_fn = system_state["target_fn"]  #TODO: define im GUI_Hauptprogramm bzw. im scheduler
        tSR = system_state["tSR"]  #TODO: define im GUI_Hauptprogramm bzw. im scheduler
        tLO = system_state["tLO"]  #TODO: define im GUI_Hauptprogramm bzw. im scheduler
        system_state["progress_source"] = "sox"  #TODO: solve double function in better datacommunication structure

        if system_state['wFormatTag'] == 1:
            wFormatTag_TYPE = "signed-integer"
        elif system_state['wFormatTag']  == 3:
            wFormatTag_TYPE = "floating-point"
        else:
            wsys.WIZ_auxiliaries.standard_errorbox("wFormatTag is neither 1 nor 3; unsupported Format, this file cannot be processed")
            return False

        my_filename, filetype = os.path.splitext(os.path.basename(source_fn))
        if filetype == '.dat':
            sox_filetype = 'raw'
        else:
            sox_filetype = 'wav'
        soxstring = 'sox --norm=-3 -e ' + wFormatTag_TYPE + ' -t  ' + sox_filetype + ' -r ' + str(system_state["sSR"]) + ' -b '+ str(system_state["sBPS"]) + ' -c 2 ' + '"' + source_fn  + '"' + ' -e signed-integer -t raw -r ' + str(int(tSR)) + ' -b ' + str(system_state["tBPS"]) + ' -c 2 '  + '"' + target_fn  + '"' 
        #TODO: include trim command if starttime_cut and stoptime_cut are active
        # if system_state["starttrim"]:
        #   trimextension = " trim " + str(system_state["starttime_cut_secs"]) +" " + str(system_state["duration"]) 
        # if system_state["stoptrim"]:
        #   trimextension = " trim " + str(system_state["stoptime_cut_secs"]) 
        # soxstring = soxstring + trimextension
        
        print(f"<<<<resampler: soxstring: xxx")
        expected_filesize = system_state["t_filesize"]

        #system_state = self.sys_state.get_flags() #obsolete
        system_state["progress_source"] = "sox" #TODO rename sox reference to something more general: worker ?????
        print("set flags just before soxthread")
        self.sys_state.set_status(system_state)
        self.soxthread = QThread(parent = self)
        #change 26_11_2023: beforechange: self.sox_worker = soxwriter()
        self.sox_worker = res_workers()
        self.sox_worker.moveToThread(self.soxthread)
        self.sox_worker.set_soxstring(soxstring)
        self.sox_worker.set_ret("")
        self.sox_worker.set_tfname(target_fn )
        self.sox_worker.set_expfs(expected_filesize)
        self.soxthread.started.connect(self.sox_worker.sox_writer)
        self.Sigincrscheduler.connect(self.res_scheduler)
        self.sox_worker.SigFinished.connect(lambda: self.Sigincrscheduler.emit())
        #z.B. schreibe die Referenz auf signal_state, damit sie der Scheduler dort abholen kann, schedule[n].["startsignal"] = diese Referenz
        self.sox_worker.SigPupdate.connect(lambda: view_resampler.updateprogress_resampling(self)) #TODO: eher aus der Klasse view, könnte auch ausserhalb geschehen
        self.sox_worker.SigFinished.connect(self.soxthread.quit)
        self.sox_worker.SigFinished.connect(self.sox_worker.deleteLater)
        self.soxthread.finished.connect(self.soxthread.deleteLater)

        #change 26_11_2023: beforechange: system_state["res_blinkstate"] = True #TODO: shift to scheduler!
        system_state["calling_worker"] = self.sox_worker 

        #system_state["sox_worker"] = self.sox_worker 
        self.sys_state.set_status(system_state)
        print("soxthread starting now ###########################")
        self.soxthread.start()
        if self.soxthread.isRunning():
            print("soxthread started")
        time.sleep(1) # wait state so that the soxworker has already opened the file
        print("resampler sleep over")
        print("about to leave resampler")
        self.sys_state.set_status(system_state)
        print("resampler leave now")

    def accomplish_resampling(self):
        """_after sox-resampling a wav_fileheader is inserted into the resampled dat-File.
        Afterwards  and temporary files are removed
        this method is called via a signal from the soxwriter worker function sox_writer() after finishing the process
        communication occurs only via state variables, as this function is called asynchronously on signal emission
                system_state["tgt_wavheader"]: wavheader to be inserted
                system_state["new_name"]: name to which the temporary targetfile (targetfilename) should be renamed after processing
                system_state["targetfilename"]: complete target file path
                system_state["file_to_be_removed"]: temporary file to be removed if it exists
        :param: none
        :type: none
        ...
        :raises
        ...
        :return: none
        :rtype: none
        """
        system_state = self.sys_state.get_status()
        gui = system_state["gui_reference"]
        schedule_objdict = system_state["schedule_objdict"]
        schedule_objdict["signal"]["accomplish"].disconnect(schedule_objdict["connect"]["accomplish"])
        self.Sigincrscheduler.connect(self.res_scheduler)
        if system_state["accomp_label"] == True:
            print("accomplish reached twice: return without action")
            return
        system_state["accomp_label"] = True
        print("accomplish_resampling: soxstring thread finished")
        target_fn = system_state["source_fn"]  #TODO: define im GUI_Hauptprogramm bzw. im scheduler
        gui.ui.progressBar_resample.setProperty("value", 0)#TODO TODO: Transfer to scheduler
        #self.soxthreadActive = False  #TODO: check is obsolete
        print(f"accomplish reached, target_fn: {target_fn}")
        if os.path.exists(target_fn) == True:
            file_stats = os.stat(target_fn)
        else:
            wsys.WIZ_auxiliaries.standard_errorbox("Accomplish: File not found, severe error, terminate resampling procedure")
            return False
        tgt_wavheader = system_state["s_wavheader"]
        tgt_wavheader['filesize'] = file_stats.st_size
        tgt_wavheader['data_nChunkSize'] = tgt_wavheader['filesize'] - 208
        tgt_wavheader['nSamplesPerSec'] = int(system_state["tSR"])

        ###############TODOTODOTODO######################################################
        #entferne nextfilename und korrigiere nAvgBytesPerSec
        header_config = [int(1),"data","auxi",int(164),system_state["tBPS"],int(system_state["tBPS"]/4),int(system_state["readoffset"]),int(system_state["tLO"])] #TODO check obsolete ?
        tgt_wavheader = self.resamp_configheader(tgt_wavheader,header_config)
        tgt_wavheader['nAvgBytesPerSec'] = int(tgt_wavheader['nSamplesPerSec']*int(system_state["tBPS"]/4))
        ovwrt_flag = True
        time.sleep(1)
        WAVheader_tools.write_sdruno_header(self,target_fn,tgt_wavheader,ovwrt_flag)
        time.sleep(1)
        #if new_name exists --> delete
        newname = system_state["new_name"]
        if os.path.exists(newname) == True:
            os.remove(system_state["new_name"])
        print(f"accomplisher: new name: {newname}")
        print(f"accomplisher: target_fn: {target_fn}")
        # Renaming the file
        shutil.move(target_fn, system_state["new_name"]) #TODO. cannot shift last temp file to external directory (ext. harddisk)
        system_state["t_wavheader"] = tgt_wavheader
        #system_state["f1"] = system_state["new_name"]
        self.sys_state.set_status(system_state)
        #gui.f1 = system_state["new_name"] #TODO: remove after tests 17-12-2023: cleanup after complete resampler module implementation
        print("accomplish leave after signalling to scheduler")   
        self.Sigincrscheduler.emit()

    
    def res_scheduler(self):

        system_state = self.sys_state.get_status()
        gui = system_state["gui_reference"]
        cnt = system_state["r_sch_counter"]
        sch = system_state["res_schedule"]
        self.Sigincrscheduler.disconnect(self.res_scheduler)##############TODOTODOTODO
        print("reached scheduler")
        tests = sch[cnt]["action"]
        print(f"count: {cnt}, sch.action: {tests}")
        schedule_objdict = system_state["schedule_objdict"]
        system_state["actionlabel"] = sch[cnt]["actionlabel"]
        system_state["sSR"] = sch[cnt]["sSR"]
        system_state["tSR"] = sch[cnt]["tSR"]
        system_state["sBPS"] = sch[cnt]["sBPS"]
        system_state["tBPS"] = sch[cnt]["tBPS"]
        system_state["sfilesize"] = sch[cnt]["s_filesize"]
        system_state["wFormatTag"] = sch[cnt]["wFormatTag"]
        system_state["t_filesize"] = sch[cnt]["t_filesize"]
        system_state["target_fn"] = "temp_" + str(cnt) + '.dat' #<<< NEW vs LOshifter : filename automatism
        fid = open(self.system_state["target_fn"], 'w')
        fid.close()
        if cnt == 0:
            system_state["accomp_label"] = False
        
        if cnt > 0:
            system_state["source_fn"] = "temp_" + str(cnt-1) + '.dat' #<<< NEW vs LOshifter : filename automatism
        print(f'targetfilename: {system_state["target_fn"]}')
        print(f'sourcefilename: {system_state["source_fn"]}')
        if cnt > 1:
            remfile = "temp_" + str(cnt-2) + '.dat'
            #remove old temp file
            if os.path.exists(remfile) == True:
                print("new accomplish: remfile: " + remfile)
                os.remove(remfile)

        if sch[cnt]["blinkstate"]:
            system_state["res_blinkstate"] = True
        else:
            system_state["res_blinkstate"] = False
        system_state["r_sch_counter"] += 1
        if sch[cnt]["action"].find('terminate') == 0:
            print("scheduler: start termination")
            system_state["r_sch_counter"] = 0 #terminate schedule, reset counter
            self.sys_state.set_status(system_state)
            gui.ui.label_36.setStyleSheet("background-color: lightgray")
            gui.ui.label_36.setFont(QFont('arial',12))
            #setze Signal ab, das GUI Update auslöst:
            #TODO: lade das letzte resampelte File ?? aber erst wenn ganze eventloop abgearbeitet
            #system_state["f1"] = system_state["new_name"] #TODO: CHEKC TESTEN 17-12-2023
            self.SigUpdateGUI.connect(self.res_update_GUI) #TODO: check gui reference
            self.SigUpdateGUI.emit() #TODO:  check gui reference
            self.SigTerminate_Finished.emit() #general signal for e.g. cb_resampler
            time.sleep(0.01)
            #TODO TODO: check change 14-12-2023: self.SigUpdateGUI.disconnect(self.res_update_GUI) #TODO:  check gui reference
            gui.activate_tabs(["View_Spectra","Annotate","Resample","YAML_editor","WAV_header","Player"]) #TODO check if outside
            self.sys_state.set_status(system_state)
            return

        system_state["last_system_time"] = time.time()    
        self.sys_state.set_status(system_state) 

        if sch[cnt]["action"].find('resample') == 0:
            print("scheduler: resample rechaed, emit signal resample")
            schedule_objdict["signal"]["resample"].connect(schedule_objdict["connect"]["resample"])
            schedule_objdict["signal"]["resample"].emit()
            time.sleep(0.01)
            pass
        if sch[cnt]["action"].find('accomplish') == 0:
            print("scheduler: accomplish rechaed, emit signal accomplish")
            gui.ui.label_36.setText('FINALIZE')
            self.sys_state.set_status(system_state)
            #TODO: gleicher Aufruf wie in 'resample':
            schedule_objdict["signal"]["accomplish"].connect(schedule_objdict["connect"]["accomplish"])
            schedule_objdict["signal"]["accomplish"].emit()
        if sch[cnt]["action"].find('LOshift') == 0:
            print("scheduler: LOshift rechaed, emit signal LOshift")
            #TODO: gleicher Aufruf wie in 'resample':
            schedule_objdict["signal"]["LOshift"].connect(schedule_objdict["connect"]["LOshift"])
            schedule_objdict["signal"]["LOshift"].emit()
        if sch[cnt]["action"].find('progress') == 0:
            print("scheduler: progressupdate rechaed, no action")

    def res_update_GUI(self): #TODO TODO: is this method still needed ? reorganize. gui-calls should be avoided, better only signalling and gui must call the routenes itself
        print(" new updateGUI in resampler module reached")

        self.SigUpdateGUI.disconnect(self.res_update_GUI)

    def schedule_A(self):
        """_definition of schedule for simple resampling without LO shift
        :param: none, communication only via system_state
        :type: none
        ...
        :raises none
        ...
        :return: none
        :rtype: none
        """
        print("start define resampling schedule A, no LOshift, pure resampling")

        system_state = self.sys_state.get_status()
        system_state["r_sch_counter"] = 0
        target_SR = system_state["target_SR"] 
        target_LO = system_state["target_LO"]
        schedule = []

        wavheader = system_state['s_wavheader']
        sch1 = {}
        sch1["action"] = "resample"
        sch1["blinkstate"] = True
        sch1["actionlabel"] = "RESAMPLE"
        sch1["sSR"] = wavheader['nSamplesPerSec']
        sch1["tSR"] = float(target_SR)*1000
        sch1["tBPS"] = 16   #TODO: tBPS flexibel halten !
        sch1["sBPS"] = wavheader['nBitsPerSample']
        sch1["s_filesize"] = wavheader['filesize'] # TODO: source filesize better determine from true filesize
        sch1["t_filesize"] = np.ceil(sch1["s_filesize"]*sch1["tSR"]/sch1["sSR"]*sch1["tBPS"]/sch1["sBPS"])
        sch1["wFormatTag"] = wavheader['wFormatTag'] #source formattag; no previous LOshifter,thus Format of sourcefile

        schedule.append(sch1)
        sch2 = {}
        sch2["action"] = "accomplish"
        sch2["blinkstate"] = False
        sch2["actionlabel"] = "ACCOMPLISH"
        sch2["sSR"] = float(target_SR)*1000 
        sch2["tSR"] = float(target_SR)*1000
        sch2["sBPS"] = 16 #Dummy , plays no role in terminate
        sch2["tBPS"] = 16 #Dummy , plays no role in terminate
        sch2["s_filesize"] = 0 #Dummy , plays no role in terminate
        sch2["t_filesize"] = 0 #Dummy , plays no role in terminate
        sch2["wFormatTag"] = 1 #source formattag
        schedule.append(sch2)
        sch3 = {}
        sch3["action"] = "terminate"
        sch3["blinkstate"] = False
        sch3["actionlabel"] = ""
        sch3["sSR"] = float(target_SR)*1000
        sch3["tSR"] = float(target_SR)*1000
        sch3["sBPS"] = 16 #Dummy , plays no role in terminate
        sch3["tBPS"] = 16 #Dummy , plays no role in terminate
        sch3["s_filesize"] = 0 #Dummy , plays no role in terminate
        sch3["t_filesize"] = 0 #Dummy , plays no role in terminate
        sch3["wFormatTag"] = 1 #source formattag
        schedule.append(sch3)

        system_state["res_schedule"] = schedule
        self.sys_state.set_status(system_state)

    def schedule_B(self):
        """_definition of schedule for  resampling with previous LO shift
        do not use for files with BPS = 24bit; use version schedule_B24(self) in that case
        :param: none, communication only via system_state
        :type: none
        ...
        :raises none
        ...
        :return: none
        :rtype: none
        """
        print("start define resampling schedule A, no LOshift, pure resampling")

        system_state = self.sys_state.get_status()
        system_state["r_sch_counter"] = 0
        target_SR = system_state["target_SR"] 
        target_LO = system_state["target_LO"]
        schedule = []

        wavheader = system_state['s_wavheader']
        sch0 = {}
        sch0["action"] = "LOshift"
        sch0["blinkstate"] = True
        sch0["actionlabel"] = "LO shifting"
        sch0["sSR"] = wavheader['nSamplesPerSec'] 
        sch0["tSR"] = sch0["sSR"]
        sch0["sBPS"] = wavheader['nBitsPerSample']
        sch0["tBPS"] = 32 # TODO check if this should be always so: always defined so for LOshifter
        sch0["wFormatTag"] = wavheader['wFormatTag']
        sch0["s_filesize"] = wavheader['filesize'] 
        sch0["t_filesize"] = int(sch0["s_filesize"]*sch0["tBPS"]/sch0["sBPS"])
        schedule.append(sch0)

        sch1 = {}
        sch1["action"] = "resample"
        sch1["blinkstate"] = True
        sch1["actionlabel"] = "RESAMPLE"
        sch1["sSR"] = wavheader['nSamplesPerSec']
        sch1["tSR"] = float(target_SR)*1000
        sch1["tBPS"] = 16   #TODO: tBPS flexibel halten !
        sch1["sBPS"] = sch0["tBPS"]
        sch1["s_filesize"] = sch0["t_filesize"]
        sch1["t_filesize"] = sch1["s_filesize"]*sch1["tSR"]/sch1["sSR"]*sch1["tBPS"]/sch1["sBPS"]
        sch1["wFormatTag"] = 3 #source formattag; the previous LOshifter has produced 32bit IEEE float 32

        schedule.append(sch1)
        sch2 = {}
        sch2["action"] = "accomplish"
        sch2["blinkstate"] = False
        sch2["actionlabel"] = "ACCOMPLISH"
        sch2["sSR"] = float(target_SR)*1000 
        sch2["tSR"] = float(target_SR)*1000
        sch2["sBPS"] = 16 #Dummy , plays no role in terminate
        sch2["tBPS"] = 16 #Dummy , plays no role in terminate
        sch2["s_filesize"] = 0 #Dummy , plays no role in terminate
        sch2["t_filesize"] = 0 #Dummy , plays no role in terminate
        sch2["wFormatTag"] = 1 #source formattag
        schedule.append(sch2)
        sch3 = {}
        sch3["action"] = "terminate"
        sch3["blinkstate"] = False
        sch3["actionlabel"] = ""
        sch3["sSR"] = float(target_SR)*1000
        sch3["tSR"] = float(target_SR)*1000
        sch3["sBPS"] = 16 #Dummy , plays no role in terminate
        sch3["tBPS"] = 16 #Dummy , plays no role in terminate
        sch3["s_filesize"] = 0 #Dummy , plays no role in terminate
        sch3["t_filesize"] = 0 #Dummy , plays no role in terminate
        sch3["wFormatTag"] = 1 #source formattag
        schedule.append(sch3)

        system_state["res_schedule"] = schedule
        self.sys_state.set_status(system_state)

    def schedule_B24(self):
        """_definition of schedule for  resampling with previous LO shift
        do not use for files with BPS = 24bit; use version schedule_B24(self) in that case
        :param: none, communication only via system_state
        :type: none
        ...
        :raises none
        ...
        :return: none
        :rtype: none
        """
        print("start define resampling schedule A, no LOshift, pure resampling")

        system_state = self.sys_state.get_status()
        system_state["r_sch_counter"] = 0
        target_SR = system_state["target_SR"] 
        target_LO = system_state["target_LO"]
        schedule = []

        wavheader = system_state['s_wavheader']

        sch_m1 = {}
        sch_m1["action"] = "resample"
        sch_m1["blinkstate"] = True
        sch_m1["actionlabel"] = "RESAMPLE 24/32"
        sch_m1["sSR"] = wavheader['nSamplesPerSec'] 
        sch_m1["tSR"] = float(target_SR)*1000  # sch_m1["sSR"]
        sch_m1["sBPS"] = wavheader['nBitsPerSample']
        sch_m1["tBPS"] = 32
        sch_m1["wFormatTag"] = wavheader['wFormatTag']
        sch_m1["s_filesize"] = wavheader['filesize'] 
        sch_m1["t_filesize"] = np.ceil(sch_m1["s_filesize"]*sch_m1["tSR"]/sch_m1["sSR"]*sch_m1["tBPS"]/sch_m1["sBPS"])
        sch_m1["wFormatTag"] = wavheader['wFormatTag'] #source formattag; no previous LOshifter,thus Format of sourcefile
        schedule.append(sch_m1)

        sch0 = {}
        sch0["action"] = "LOshift"
        sch0["blinkstate"] = True
        sch0["actionlabel"] = "LO shifting"
        sch0["sSR"] = sch_m1["tSR"]
        sch0["tSR"] = sch0["sSR"]
        sch0["sBPS"] = 32
        sch0["tBPS"] = 32 # TODO check if this should be always so: always defined so for LOshifter
        sch0["wFormatTag"] = 1 #the previus resampler has produced integer values, resmpler prod always signed-integer
        sch0["s_filesize"] = sch_m1["t_filesize"] 
        sch0["t_filesize"] = sch0["s_filesize"]*sch0["tSR"]/sch0["sSR"]*sch0["tBPS"]/sch0["sBPS"]
        schedule.append(sch0)

        sch1 = {}
        sch1["action"] = "resample"
        sch1["blinkstate"] = True
        sch1["actionlabel"] = "RESAMPLE F"
        sch1["sSR"] = sch0["tSR"]
        sch1["tSR"] = sch1["sSR"] # float(target_SR)*1000
        sch1["tBPS"] = 16   #TODO: tBPS flexibel halten !
        sch1["sBPS"] = sch0["tBPS"]
        sch1["s_filesize"] = sch0["t_filesize"]
        sch1["t_filesize"] = sch1["s_filesize"]*sch1["tSR"]/sch1["sSR"]*sch1["tBPS"]/sch1["sBPS"]
        sch1["wFormatTag"] = 3 #source formattag; the previous LOshifter has produced 32bit IEEE float 32

        schedule.append(sch1)
        sch2 = {}
        sch2["action"] = "accomplish"
        sch2["blinkstate"] = False
        sch2["actionlabel"] = "ACCOMPLISH"
        sch2["sSR"] = float(target_SR)*1000 
        sch2["tSR"] = float(target_SR)*1000
        sch2["sBPS"] = 16 #Dummy , plays no role in terminate
        sch2["tBPS"] = 16 #Dummy , plays no role in terminate
        sch2["s_filesize"] = 0 #Dummy , plays no role in terminate
        sch2["t_filesize"] = 0 #Dummy , plays no role in terminate
        sch2["wFormatTag"] = 1 #source formattag
        schedule.append(sch2)
        sch3 = {}
        sch3["action"] = "terminate"
        sch3["blinkstate"] = False
        sch3["actionlabel"] = ""
        sch3["sSR"] = float(target_SR)*1000
        sch3["tSR"] = float(target_SR)*1000
        sch3["sBPS"] = 16 #Dummy , plays no role in terminate
        sch3["tBPS"] = 16 #Dummy , plays no role in terminate
        sch3["s_filesize"] = 0 #Dummy , plays no role in terminate
        sch3["t_filesize"] = 0 #Dummy , plays no role in terminate
        sch3["wFormatTag"] = 1 #source formattag
        schedule.append(sch3)
        system_state["res_schedule"] = schedule
        self.sys_state.set_status(system_state)

    def merge2G_files(self,input_file_list):  # 2 GB in Bytes
        """_merge all files in system_state["list_out_files_resampled"]
        (these are all files produced by one resampling sequence)
        into a set of final wav files which have size 2GB and the correct wav-Header entries
        The general wavheader is fetched from the target wavheader of the previous resampling run
        the fields to be updated are: filesize, datachunksize and start/stoptimes as well as the nextfile entry
        Additionally the different standard filenames acc ro SDRUno nameconvention must be generated 
        (these are related to the nextfile entries)
        :param: none, communication only via system_state
        :type: none
        ...
        :raises none
        ...
        :return: none
        :rtype: none
        """
        system_state = self.sys_state.get_status()
        gui = system_state["gui_reference"]
        wavheader = system_state["t_wavheader"]

        output_file_prefix = system_state["out_dirname"] + "/temp_resized_"
        current_output_file_index = 1
        current_output_file_size = 0
        current_output_file_path = f"{output_file_prefix}_{current_output_file_index}.dat"
        gui = self.system_state["gui_reference"]
        #system_state = self.sys_state.get_flags() #obsolete
        system_state["progress_source"] = "normal"
        system_state["progress"] = 0
        #self.sys_state.set_flags(system_flags) #obsolete
        system_state["blinkstate"] = True
        system_state["actionlabel"] = "MERGE 2G"
        self.sys_state.set_status(system_state)
        print("start merging files")
        maxprogress = 100
        lenlist = len(input_file_list)
        list_ix = 0
        with open(current_output_file_path, 'wb') as current_output_file:
            # Schreibe die ersten 216 Bytes mit Nullen
            print(f"generate outputfile {current_output_file_path}")
            current_output_file.write(b'\x00' * 216)
            current_output_file_size = 216
            for input_file in input_file_list: #TODO: rewrite with enumerate for list index
                list_ix += 1
                system_state["progress"] = list_ix/lenlist*maxprogress
                self.sys_state.set_status(system_state)
                #self.sys_state.set_flags(system_state)
                self.SigProgress.emit()
                with open(input_file, 'rb') as input_file:
                    while True:
                        # Lese 1 MB Daten aus der Eingabedatei
                        data_chunk = input_file.read(1024**2)  # 1 MB in Bytes

                        # Überprüfe, ob die Eingabedatei vollständig gelesen wurde
                        if not data_chunk:
                            if list_ix > (lenlist-1):
                                print(f"last write file reached, ix = {lenlist}")
                                #write last wavheader
                                duration = (current_output_file_size - 216)/wavheader["nAvgBytesPerSec"]
                                stt = wavheader["starttime_dt"]
                                spt = stt + ndatetime.timedelta(seconds= np.floor(duration)) + ndatetime.timedelta(milliseconds = 1000*(duration - np.floor(duration)))
                                wavheader['stoptime_dt'] = spt
                                wavheader['stoptime'] = [spt.year, spt.month, 0, spt.day, spt.hour, spt.minute, spt.second, int(spt.microsecond/1000)] 
                                wavheader['filesize'] = current_output_file_size
                                wavheader['data_nChunkSize'] = wavheader['filesize'] - 208
                                wavheader['nextfilename'] = ""
                                WAVheader_tools.write_sdruno_header(self,current_output_file.name,wavheader,True)
                                #TODO: rename to newfile
                                nametrunk, extension = os.path.splitext(current_output_file.name)
                                nametrunk = f"{os.path.dirname(current_output_file_path)}/resampled_{str(current_output_file_index)}_"
                                aux = str(wavheader['starttime_dt'])
                                if aux.find('.') < 1:
                                    SDRUno_suff = aux
                                else:
                                    SDRUno_suff = aux[:aux.find('.')]
                                SDRUno_suff = SDRUno_suff.replace(" ","_")
                                SDRUno_suff = SDRUno_suff.replace(":","")
                                SDRUno_suff = SDRUno_suff.replace("-","")
                                new_name = nametrunk + str(SDRUno_suff) + '_' + str(int(np.round(wavheader["centerfreq"]/1000))) + 'kHz.wav'
                                current_output_file.close()
                                shutil.move(current_output_file_path, new_name)

                            break

                        # Überprüfe, ob die Ausgabedatei die maximale Größe überschreiten würde
                        if current_output_file_size + len(data_chunk) > self.MAX_TARGETFILE_SIZE: #TEST: 50 * 1024**2: #TODO: zurückstellen nach Test self.MAX_TARGETFILE_SIZE:
                            #generate individual wavheaders
                            #generate nextfilename
                            current_output_file.close()
                            #insert wav header
                            duration = (current_output_file_size - 216)/wavheader["nAvgBytesPerSec"]
                            stt = wavheader["starttime_dt"]
                            spt = stt + ndatetime.timedelta(seconds= np.floor(duration))  + ndatetime.timedelta(milliseconds = 1000*(duration - np.floor(duration)))
                            wavheader['stoptime_dt'] = spt
                            #if int(1000*(duration - np.floor(duration))) > 0: #TODO: check, may be inconsistent, unsinn
                            wavheader['stoptime'] = [spt.year, spt.month, 0, spt.day, spt.hour, spt.minute, spt.second, int(spt.microsecond/1000)] 
                            # else:
                            #     wavheader['stoptime'] = [spt.year, spt.month, 0, spt.day, spt.hour, spt.minute, spt.second, 0]
                            wavheader['filesize'] = current_output_file_size
                            wavheader['data_nChunkSize'] = wavheader['filesize'] - 208
                            next_output_file = f"{output_file_prefix}_{current_output_file_index+1}.dat" #TODO: The case that this file is EXACTLY the last one (by chance) is not treated correctly here
                            #next_nametrunk, extension = os.path.splitext(os.path.basename(next_output_file))
                            #nametrunk, extension = os.path.splitext(current_output_file.name)#TODO:obsolet
                            nametrunk = f"{os.path.dirname(current_output_file_path)}/resampled_{str(current_output_file_index)}_"
                            next_nametrunk = f"resampled_{str(current_output_file_index + 1)}_" 
                            aux = str(wavheader['starttime_dt'])
                            if aux.find('.') < 1:
                                SDRUno_suff = aux
                            else:
                                SDRUno_suff = aux[:aux.find('.')]
                            SDRUno_suff = SDRUno_suff.replace(" ","_")
                            SDRUno_suff = SDRUno_suff.replace(":","")
                            SDRUno_suff = SDRUno_suff.replace("-","")
                            aux = str(wavheader['stoptime_dt'])
                            if aux.find('.') < 1:
                                next_suff = aux
                            else:
                               next_suff = aux[:aux.find('.')]
                            next_suff = next_suff.replace(" ","_")
                            next_suff = next_suff.replace(":","")
                            next_suff = next_suff.replace("-","")
                            next_name = next_nametrunk + str(next_suff) + '_' + str(int(np.round(wavheader["centerfreq"]/1000))) + 'kHz.wav'
                            new_name = nametrunk + str(SDRUno_suff) + '_' + str(int(np.round(wavheader["centerfreq"]/1000))) + 'kHz.wav'
                            wavheader['nextfilename'] = next_name
                            WAVheader_tools.write_sdruno_header(self,current_output_file.name,wavheader,True)
                            #TODO: rename to newfile
                            shutil.move(current_output_file_path, new_name)
                            # prepare next wavheader starttime
                            wavheader['starttime_dt'] = wavheader['stoptime_dt']
                            wavheader['starttime'] = wavheader['stoptime']
                            current_output_file_size = 0
                            current_output_file_index += 1
                            current_output_file_path = f"{output_file_prefix}_{current_output_file_index}.dat"
                            current_output_file = open(current_output_file_path, 'wb')
                            current_output_file.write(b'\x00' * 216)  # Schreibe die ersten 216 Bytes mit Nullen

                        # Schreibe Daten in die Ausgabedatei: if last file: nextfile = ''
                        current_output_file.write(data_chunk)
                        current_output_file_size += len(data_chunk)

                        #
        print("merge files done, deleting intermediate files")
        for input_file in input_file_list:
            print(f"remove {input_file}")
            os.remove(input_file)

        gui.ui.listWidget_playlist.clear() #TODO: shift to a central updater/GUI reset
        gui.ui.listWidget_sourcelist.clear() #TODO: shift to a central updater/GUI reset
        gui.clear_WAVwidgets() #TODO: shift to a central updater/GUI reset
        #system_flags = self.sys_state.get_flags() #obsolete
        system_state["progress_source"] = "normal"
        system_state["progress"] = 0
        self.SigProgress.emit()
        system_state["blinkstate"] = False
        system_state["actionlabel"] = ""
        self.sys_state.set_status(system_state)
        gui.ui.label_36.setStyleSheet("background-color: lightgray")
        self.sys_state.set_status(system_state)
        self.res_update_GUI
        


class view_resampler(QObject):
    """_view methods for resampling module
    TODO: gui.wavheader --> something less general ?
    """
    __slots__ = ["viewvars"]

    SigAny = pyqtSignal()
    SigUpdateList = pyqtSignal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        viewvars = {}
        self.set_viewvars(viewvars)
        self.sys_state = wsys.status()
        system_state = self.sys_state.get_status()
        system_state["reslistdoubleemit_ix"] = False
        gui = system_state["gui_reference"]
        gui.ui.listWidget_playlist_2.itemClicked.connect(self.reslist_itemselected) #TODO transfer to resemplar view
        gui.ui.listWidget_playlist_2.itemChanged.connect(self.reslist_update)
        self.sys_state.set_status(system_state)
        self.DATABLOCKSIZE = 1024*32
        
    def set_viewvars(self,_value):
        self.__slots__[0] = _value

    def get_viewvars(self):
        return(self.__slots__[0])

    def reslist_update(self): #TODO: list is only updated up to the just before list change dragged item,
        """
        VIEW
        updates resampler list whenever the playlist Widget is changed
        :param: none
        :type: none
        ...
        :raises: none
        ...
        :return: none
        :rtype: none
        """

        print("resampling list updated")  
        time.sleep(0.1)
        system_state = self.sys_state.get_status()
        gui = system_state["gui_reference"]
        #get all items of playlist Widget and write them to system_state["playlist"]
        lw = gui.ui.listWidget_playlist_2
        # let lw haven elements in it.
        reslist = []
        for x in range(lw.count()):
            item = lw.item(x)
            #playlist.append(lw.item(x))
            reslist.append(item.text())
        system_state["reslist"] = reslist
        self.sys_state.set_status(system_state)

        #system_state["reslistdoubleemit_ix"] = False
        print(f"reslist: {reslist}")
        system_state["f1"] = gui.my_dirname + '/' + reslist[0] #TODO: replace self.mydirname by status entry
        print(f'cb_resample: file: {system_state["f1"]}')
        gui.wavheader = WAVheader_tools.get_sdruno_header(self,system_state["f1"])
        gui.showfilename()
        self.plot_spectrum_resample(0)
        self.sys_state.set_status(system_state)
        #TODO: fetch starttime of the first file and stoptime of the last file to copy the values to the starttime_cut and stoptime_cut windows of the GUI


        print("resampler view reslist reached")


    def reslist_itemselected(self,item):
        """
        VIEW
        show clicked item in resampler list whenever an item is clicked
        :param: none
        :type: none
        ...
        :raises: none
        ...
        :return: none
        :rtype: none
        """
        system_state = self.sys_state.get_status()
        gui = system_state["gui_reference"]
        print(f"reslist: item clicked, itemtext: {item.text()}")        
        system_state["f1"] = gui.my_dirname + '/' + item.text() #TODO: replace self.mydirname by status entry
        print(f'cb_resample: file: {system_state["f1"]}')
        gui.wavheader = WAVheader_tools.get_sdruno_header(self,system_state["f1"])
        gui.showfilename()
        self.plot_spectrum_resample(0)
        self.sys_state.set_status(system_state)

    def plot_spectrum_resample(self,position):
        """assign a plot window and a toolbar to the tab 'resample' and plot data from currently loaded file at position 'position'
        :param : position
        :type : int
        :raises [ErrorType]: [ErrorDescription]
        :return: flag False or True, False on unsuccessful execution
        :rtype: Boolean
        """
        #TODO: define: ax_res, canvas_resample
        # gui.ui.lineEdit_resample_targetLO.setStyleSheet("background-color: white")
        # gui.ui.lineEdit_resample_Gain.setText('')
        system_state = self.sys_state.get_status()
        gui = system_state["gui_reference"]
        if system_state["fileopened"] == False:
            return(False)
        else:
            #print('plot spectrum resample')
            #data = self.readsegment() ##TODO: position ist die des scrollbars im View spectra tab, das ist etwas unschön. Man sollte auch hier einen scrollbar haben, der mit dem anderen synchronisiert wird
            pscale = gui.wavheader['nBlockAlign']
            position = int(np.floor(pscale*np.round(gui.wavheader['data_nChunkSize']*system_state["horzscal"]/pscale/1000)))
            ret = gui.readsegment(position,self.DATABLOCKSIZE)  ##TODO: position ist die des scrollbars im View spectra tab, das ist etwas unschön. Man sollte auch hier einen scrollbar haben, der mit dem anderen synchronisiert wird
            #NEW 08-12-2023 #######################TODO###################### tBPS not yet clear
            ret = gui.readsegment_new(system_state["f1"],position,self.DATABLOCKSIZE,gui.wavheader["nBitsPerSample"],
                                      32,gui.wavheader["wFormatTag"])
            ####################################################################################
            data = ret["data"]
            if 2*ret["size"]/gui.wavheader["nBlockAlign"] < self.DATABLOCKSIZE:
                return False
            # TODO: ####FFFFFFFFFFFFFFFFFFF replace by new invalidity condition
            # if len(data) == 10:
            #     if np.all(data == np.linspace(0,9,10)):
            #         return False
            #NEW: 
            # if len(data) < self.DATABLOCKSIZE
            #     return False
            gui.Tabref["Resample"]["ax"].clear()
            realindex = np.arange(0,self.DATABLOCKSIZE,2)
            imagindex = np.arange(1,self.DATABLOCKSIZE,2)
            #calculate spectrum and shift/rescale appropriately
            spr = np.abs(np.fft.fft((data[realindex]+1j*data[imagindex])))
            N = len(spr)
            spr = np.fft.fftshift(spr)
            flo = gui.wavheader['centerfreq'] - gui.wavheader['nSamplesPerSec']/2
            fup = gui.wavheader['centerfreq'] + gui.wavheader['nSamplesPerSec']/2
            freq0 = np.linspace(0,gui.wavheader['nSamplesPerSec'],N)
            freq = freq0 + flo
            datax = freq
            datay = 20*np.log10(spr)
            gui.Tabref["Resample"]["ax"].plot(datax,datay, '-')
            gui.Tabref["Resample"]["ax"].set_xlabel('frequency (Hz)')
            gui.Tabref["Resample"]["ax"].set_ylabel('amplitude (dB)')       
            #plot bandlimits of resampling window
            target_SR = float(gui.ui.comboBox_resample_targetSR.currentText())*1000
            #lineEdit_resample_targetLO          
            target_LO_test = gui.ui.lineEdit_resample_targetLO.text()
            numeraltest = True
            if not target_LO_test[0].isdigit():
                numeraltest = False
            target_LO_test = target_LO_test.replace(".", "")
            if not target_LO_test[1:].isdigit():
                numeraltest = False
            if numeraltest == False:
                wsys.WIZ_auxiliaries.standard_errorbox("invalid characters, must be numeric float value !")
                return False
            try:
                target_LO = float(gui.ui.lineEdit_resample_targetLO.text())*1000
            except TypeError:
                print("wrong format of TARGET_LO")
                wsys.WIZ_auxiliaries.standard_errorbox("invalid characters, must be numeric float value !")
                #TARGET_LO = gui.wavheader['centerfreq']
                return False
            except ValueError:
                print("wrong format of TARGET_LO")
                wsys.WIZ_auxiliaries.standard_errorbox("invalid characters, must be numeric float value !")
                #TARGET_LO = gui.wavheader['centerfreq']
                return False
            xlo = target_LO - target_SR/2
            xup = target_LO + target_SR/2
            gui.Tabref["Resample"]["ax"].vlines(x=[target_LO], ymin = [min(datay)], ymax = [max(datay)], color = "C1")
            gui.Tabref["Resample"]["ax"].add_patch(Rectangle((xlo, min(datay)), xup-xlo, max(datay)-min(datay),edgecolor='red',
                facecolor='none', fill = False,
                lw=4))
            gui.Tabref["Resample"]["canvas"].draw()
        return(True)

    def updateprogress_resampling(self):
        """_duringr sox-resampling the progress of sox resampling is indicated in the progressbar.
        The active state is indicated by blinking of the label field label_36
        this method is called via a signal from the soxwriter worker function sox_writer() repetitively every second
        communication occurs only via state variables, as this function is called asynchronously on signal emission
                system_state["res_blinkstate"]
        :param: none
        :type: none
        ...
        :raises
        ...
        :return: none
        :rtype: none
        """
        system_state = self.sys_state.get_status()
        gui = system_state["gui_reference"]

        blink_free = False
        current_time = time.time()  
        if current_time - system_state["last_system_time"] >= 1:
            system_state["last_system_time"] = current_time
            blink_free = True

        if system_state["progress_source"].find('normal') > -1:  #TODO: solve double function in better datacommunication structure
            progress = system_state["progress"]
        elif system_state["progress_source"].find('sox') > -1:
            #change 26_11_2023: beforechange: progress = system_state["sox_worker"].get_progress() #TODO: dazu muss aber system_state["sox_worker"] erst einmal existieren 
            progress = system_state["calling_worker"].get_progress() #TODO: check wie gewährleistet (aktuell im action_method beim thread konfigurieren): dazu muss aber system_state["sox_worker"] erst einmal existieren 
        else:
            print("error, progress source system flag invalid")
            self.sys_state.set_status(system_state)
            return False

        gui.ui.progressBar_resample.setProperty("value", progress)

        print(f"statusbar updater sysflags_progress_source: {progress}")
        gui.ui.label_36.setText(system_state["actionlabel"])
        gui.ui.label_36.setFont(QFont('arial',12))
        print(f'statusbar updater actionlabel: {system_state["actionlabel"]}')
        if blink_free:
            if system_state["res_blinkstate"]:
                gui.ui.label_36.setStyleSheet("background-color: yellow")
            else:
                gui.ui.label_36.setStyleSheet("background-color: orange")
            system_state["res_blinkstate"] = not system_state["res_blinkstate"]
        self.sys_state.set_status(system_state)

    def update_resample_GUI(self): #wurde ins resampler-Modul verschoben
        """fills the control elements of the resample GUI with parameters from the wav header
        RESAMPLER VIEW !!
        :param [ParamName]: none
        :type [ParamName]: none
        ...
        :raises [ErrorType]: [ErrorDescription]TODO
        ...
        :return: [ReturnDescription]
        :rtype: [ReturnType]
        """
        system_state = self.sys_state.get_status()
        gui = system_state["gui_reference"]
        gui.ui.timeEdit_resample_startcut.setDateTime(gui.wavheader['starttime_dt'])
        gui.ui.timeEdit_resample_stopcut.setDateTime(gui.wavheader['stoptime_dt'])
        gui.ui.lineEdit_resample_targetLO.setText(str((gui.wavheader['centerfreq']/1000)))
        gui.ui.lineEdit_resample_Gain.setText(str(1))
        gui.ui.comboBox_resample_targetSR.setCurrentIndex(5)
        self.plot_spectrum_resample(gui.position)#TODO TODO: self position ist zu verstrickt überall in gui
        gui.showfilename() # TODO: in future versions check if this should be a gui-method
        #print("cb_resample reached")
        if not(gui.wavheader['wFormatTag'] in [1,3]): #TODO:future system state
            wsys.WIZ_auxiliaries.standard_errorbox("wFormatTag is neither 1 nor 3; unsupported Format, this file cannot be processed")
            self.sys_state.set_status(system_state)
            return False
        signtab = list(np.sign(list(system_state["rates"].keys())-system_state["irate"]*np.ones(len(system_state["rates"]))))
        #print(signtab)
        try:
            sugg_index = signtab.index(0.0) # index of SR == irate, if exists
        except:
            try:
                sugg_index = signtab.index(1.0) # else index of first positive outcome = index of SR slightly above irate
            except:
                wsys.WIZ_auxiliaries.standard_errorbox("unsupported sampling rate in filename, this file cannot be processed")
                self.sys_state.set_status(system_state)
                return False
        #set selection of SR to suggested value
        gui.ui.comboBox_resample_targetSR.setCurrentIndex(sugg_index)
        self.sys_state.set_status(system_state)

    def getCuttime(self):
        """get the values from the cut start and stop times as datetime elements
        :param [ParamName]: none
        :type [ParamName]: none
        ...
        :raises [ErrorType]: [ErrorDescription]TODO
        ...
        :return: [ReturnDescription]
        :rtype: [ReturnType]
        """
        system_state = self.sys_state.get_status()
        gui = system_state["gui_reference"]
        cutstart_datetime = gui.ui.timeEdit_resample_startcut.dateTime().toPyDateTime() #datetime object
        cutstop_datetime = gui.ui.timeEdit_resample_stoptcut.dateTime().toPyDateTime()
        print(f"cutstart datetime: {cutstart_datetime}")
        self.sys_state.set_status(system_state)
