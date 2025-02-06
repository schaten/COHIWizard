

def play_loop_filelist(self):
    """
    worker loop for sending data to STEMLAB server
    data format i16; 2xi16 complex; FormatTag 1
    sends signals:     
        SigFinished = pyqtSignal()
        SigIncrementCurTime = pyqtSignal()
        SigBufferOverflow = pyqtSignal()

    :param : no regular parameters; as this is a thread worker communication occurs via
    class slots __slots__[i], i = 0...8
    __slots__[0]: filename = complete file path pathname/filename Type: list
    __slots__[1]: timescaler = bytes per second  TODO: rescaling to samples per second would probably be more logical, Type int
    __slots__[2]: TEST = flag for test mode Type: bool
    __slots__[3]: pause : if True then do not send data; Boolean
    __slots__[4]: filehandle: returns current filehandle to main thread methods on request 
    __slots__[5]: data segment to be returned every second
    __slots__[6]: gain, scaling factor for playback
    __slots__[7]: formatlist: [formattag blockalign bitpsample]
    __slots__[9]: file_close
    __slots__[10]: sampling_parameters
    """

    filenames = self.get_filename()
    timescaler = self.get_timescaler()
    gain = self.get_gain()
    self.stopix = False
    self.set_fileclose(False)
    # start fl2k_file with reading from stdin
    sampling_rate = 10000000
    fl2k_file_path = os.path.join(os.getcwd(),"dev_drivers/fl2k/osmo-fl2k-64bit-20250105", "fl2k_file.exe")
    print(f"cohi_playrecworker fl2k_file_path exists: {os.path.exists(fl2k_file_path)}")
    try:
        process = subprocess.Popen(
            [fl2k_file_path, "-s", str(sampling_rate), "-r", "0", "-"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0
        )

    except FileNotFoundError:
        self.SigError.emit(f"Input file not found")
        self.SigFinished.emit()
        return()
    except subprocess.SubprocessError as e:
        self.SigError.emit(f"Error when executing fl2k_file: {e}")
        self.SigFinished.emit()
        return()
    except Exception as e:
        self.SigError.emit(f"Unexpected error: {e}")
        print("unexpected error in play_loop_filelist for fl2k")
        self.SigFinished.emit()
        return()

    for ix,filename in enumerate(filenames):
        fileHandle = open(filename, 'rb')
        self.SigNextfile.emit(filename)
        self.set_fileHandle(fileHandle)
        format = self.get_formattag()
        data_blocksize = self.DATABLOCKSIZE
        self.set_datablocksize(data_blocksize)
        fileHandle.seek(216, 1)
        data = np.empty(data_blocksize, dtype=np.int8)
        if format[0] == 1:
            normfactor = int(2**int(format[2]-1))-1
        else:
            normfactor = 1
        size = fileHandle.readinto(data)
        self.set_data(data)
        junkspersecond = timescaler / self.JUNKSIZE
        count = 0
        while size > 0 and not self.stopix:
            try:
                #scale data with gain and normfactor
                aux1 = gain*data[0:size]/normfactor
                # Skalieren, damit die Werte in den Bereich von int8 passen (-128 bis 127)
                scaled_array = np.clip(150*aux1, -128, 127)
                #write aux4 to fl2k_file via stdin
                process.stdin.write(scaled_array.astype(np.int8))
                process.stdin.flush()
            except BlockingIOError:
                print("Blocking data socket error in playloop worker")
                time.sleep(0.1)
                self.SigError.emit("Blocking data socket error in playloop worker")
                self.SigFinished.emit()
                time.sleep(0.1)
                return
            except ConnectionResetError:
                print("Diagnostic Message: Connection data socket error in playloop worker")
                time.sleep(0.1)
                self.SigError.emit("Diagnostic Message: Connection data socket error in playloop worker")
                self.SigFinished.emit()
                time.sleep(0.1)
                return
            except Exception as e:
                print("Class e type error  data socket error in playloop worker")
                print(e)
                time.sleep(0.1)
                self.SigError.emit(f"Diagnostic Message: Error in playloop worker: {str(e)}")
                self.SigFinished.emit()
                time.sleep(0.1)
                return
            size = fileHandle.readinto(data)

            count += 1
            if count > junkspersecond:
                self.SigIncrementCurTime.emit()
                #Dieser Aufruf blockiert das weitere Streaming immer für einige Zeit
                count = 0
                gain = self.get_gain()
                self.set_data(data)
              
    print("close file ")
    self.set_fileclose(True)
    fileHandle.close()
    # terminate fl2k_file process and wait for actual termination
    process.stdin.close()
    process.terminate
    while process.poll() == None:
        print("poll and close")
        time.sleep(1)
    
    stdout, stderr = process.communicate() ### TODO TODO TODO: Timeout ???
    # Report result
    print("cohi_playrecworker: fl2k_file output:")
    print(stdout.decode())
    if stderr:
        print("cohi_playrecworker: fl2k_file errors:")
        self.SigError.emit(f"error when terminating fl2k_file: {stderr.decode()}")
    self.SigFinished.emit()
    return()






def updatecurtime(self,increment):         
    """
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
    if not self.m["fileopened"]:
        return
    if increment == 0:
        timestr = str(ndatetime.timedelta(seconds=0))
        self.m["curtime"] = 0
        self.gui.lineEditCurTime.setText(timestr)
    delta =  datetime.now() - self.lastupdatecurtime
    if delta.microseconds < 10000:
        return
    self.m["playprogress"] = 0 #TODO: always ?
    timestr = str(self.m["wavheader"]['starttime_dt'] + ndatetime.timedelta(seconds=self.m["curtime"]))
    true_filesize = os.path.getsize(self.m["f1"]) #TODO: can be calculated outside on file opening in the play thread
    playlength = true_filesize/self.m["wavheader"]['nAvgBytesPerSec'] #TODO: can be calculated outside on file opening
    if self.m["modality"] == 'play' and self.m["pausestate"] is False:
        if self.m["curtime"] > 0 and increment < 0:
            self.m["curtime"] += increment
        if self.m["curtime"] < playlength and increment > 0:
            self.m["curtime"] += increment
        if playlength > 0:
            self.m["playprogress"] = int(np.floor(1000*(self.m["curtime"]/playlength)))
        else:
            return False
        position_raw = self.m["curtime"]*self.m["timescaler"]
        position = min(max(216, position_raw-position_raw % self.m["wavheader"]['nBlockAlign']),
                        self.m["wavheader"]['data_nChunkSize'])
        # guarantee integer multiple of nBlockalign, > 0, <= filesize
        if increment != -1 and increment != 1 or self.m["timechanged"] == True:
            if self.m["fileopened"] and self.m["playthreadActive"] is True:
                try:
                    self.prfilehandle = self.playrec_c.playrec_tworker.get_fileHandle()
                    
                except:
                        #TODO: intro standard errorhandling
                        auxi.standard_errorbox("Cannot activate background thread (tworker), maybe SDR device (STEMLAB ?) is not connected")
                        self.SigRelay.emit("cexex_all_",["reset_GUI",0])
                        self.SigRelay.emit("cm_all_",["fileopened",False]) ###TODO: Test after 09-04-2024 !
                        return False
                try:
                    self.prfilehandle.seek(int(position), 0) #TODO: Anpassen an andere Fileformate
                except:
                    self.logger.error("playrec.updatecurtimer: seek in closed file error")
    else:
        self.m["curtime"] += increment
        timestr = str(ndatetime.timedelta(seconds=0) + ndatetime.timedelta(seconds=self.m["curtime"]))
    if not self.gui.playrec_radioButton_RECAUTOSTART.isChecked():
        self.gui.lineEditCurTime.setText(timestr)
    self.gui.ScrollBar_playtime.setProperty("value", self.m["playprogress"])
    self.lastupdatecurtime = datetime.now()
    return True