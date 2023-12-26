from struct import pack
from datetime import datetime
from datetime import timedelta
import numpy as np

#methods for wavheader manipulations 

class WAVheader_tools():

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Constants
        self.TEST = True    # Test Mode Flag for testing the App without a


    def get_sdruno_header(self,filename):
        """
        opens a file with name self.f1
        extracts meta information from SDR-wav-header_
        recognized formats: SDRUno, PERSEUS, SpectraVue
        closes file after headerreading

        :param : none
        :type : none
        :raises : none
        :return: dictionary wavheader containing the individual metadata items or False if unsuccessful
        :rtype: dictionary or Boolean
        """
        self.fileHandle = open(filename, 'rb')#TODO:replace self.f1 durch f1 als Übergabeparamezet
        wavheader={}
        wavheader['riff_chckID'] = str(self.fileHandle.read(4))
        if wavheader['riff_chckID'].find('RIFF') < 0:
            return False
        wavheader['filesize'] = int.from_bytes(self.fileHandle.read(4), byteorder='little')
        wavheader['wave_string'] = str(self.fileHandle.read(4))
        wavheader['fmt_chckID'] = str(self.fileHandle.read(4))
        wavheader['fmt_nChunkSize'] = int.from_bytes(self.fileHandle.read(4), byteorder='little')
        wavheader['wFormatTag'] = int.from_bytes(self.fileHandle.read(2), byteorder='little')
        wavheader['nChannels'] = int.from_bytes(self.fileHandle.read(2), byteorder='little')
        wavheader['nSamplesPerSec'] = int.from_bytes(self.fileHandle.read(4), byteorder='little')
        wavheader['nAvgBytesPerSec'] = int.from_bytes(self.fileHandle.read(4), byteorder='little')
        wavheader['nBlockAlign'] = int.from_bytes(self.fileHandle.read(2), byteorder='little')
        wavheader['nBitsPerSample'] = int.from_bytes(self.fileHandle.read(2), byteorder='little')
        bbb = (self.fileHandle.read(4)).decode('utf-8')
        #wavheader['sdrtype_chckID'] = str(self.fileHandle.read(4))
        wavheader['sdrtype_chckID'] = bbb
        #####TODO: if sdrtype == 'auxi' do the next, else if 'rcvr' do PERSEUS, else error
        wavheader['sdr_nChunkSize'] = int.from_bytes(self.fileHandle.read(4), byteorder='little')
        if  wavheader['sdrtype_chckID'].find('auxi') > -1:
            starttime=[0, 0, 0, 0, 0, 0, 0, 0]
            for i in range(8):
                starttime[i] = int.from_bytes(self.fileHandle.read(2), byteorder='little')
            stoptime=[0, 0, 0, 0, 0, 0, 0, 0]
            for i in range(8):
                stoptime[i] = int.from_bytes(self.fileHandle.read(2), byteorder='little')
            wavheader['starttime'] = starttime
            wavheader['stoptime'] = stoptime
            wavheader['centerfreq'] = int.from_bytes(self.fileHandle.read(4), byteorder='little')
            wavheader['ADFrequency'] = int.from_bytes(self.fileHandle.read(4), byteorder='little')
            wavheader['IFFrequency'] = int.from_bytes(self.fileHandle.read(4), byteorder='little')
            wavheader['Bandwidth'] = int.from_bytes(self.fileHandle.read(4), byteorder='little')
            wavheader['IQOffset'] = int.from_bytes(self.fileHandle.read(4), byteorder='little')
            self.fileHandle.read(16) #dummy read, unused fields
            #aaa = str(self.fileHandle.read(96))
            aaa = (self.fileHandle.read(96)).decode('utf-8')
            wavheader['nextfilename'] = aaa.replace('\\\\','\\')
            wavheader['starttime_dt'] =  datetime(starttime[0],starttime[1],starttime[3],starttime[4],starttime[5],starttime[6])
            wavheader['stoptime_dt'] =  datetime(stoptime[0],stoptime[1],stoptime[3],stoptime[4],stoptime[5],stoptime[6])
            #wavheader['data_ckID'] = str(self.fileHandle.read(4))   #TODO: (self.fileHandle.read(4)).decode('utf-8')
            ccc = (self.fileHandle.read(4)).decode('utf-8')
            wavheader['data_ckID'] = ccc

            wavheader['data_nChunkSize'] = int.from_bytes(self.fileHandle.read(4), byteorder='little')
        else:
            if wavheader['sdrtype_chckID'].find('rcvr') > -1:

                print('rcvr reached in wavheader reader')

                wavheader['centerfreq'] = int.from_bytes(self.fileHandle.read(4), byteorder='little')
                wavheader['SamplingRateIdx'] = int.from_bytes(self.fileHandle.read(4), byteorder='little')
                wavheader['starttime_epoch'] = int.from_bytes(self.fileHandle.read(4), byteorder='little')
                startt = datetime.fromtimestamp(wavheader['starttime_epoch'])
                wavheader['starttime_dt'] = startt
                wavheader['wAttenId'] = int.from_bytes(self.fileHandle.read(2), byteorder='little', signed=False)
                wavheader['bAdcPresel'] = str(self.fileHandle.read(1))
                wavheader['bAdcPreamp'] = str(self.fileHandle.read(1))
                wavheader['bAdcDither'] = str(self.fileHandle.read(1))
                wavheader['bSpare'] = str(self.fileHandle.read(1))
                wavheader['rsrvd'] = str(self.fileHandle.read(16))
                ccc = (self.fileHandle.read(4)).decode('utf-8')
                wavheader['data_ckID'] = ccc
                #wavheader['data_ckID'] = str(self.fileHandle.read(4))   #TODO: (self.fileHandle.read(4)).decode('utf-8')
                wavheader['data_nChunkSize'] = int.from_bytes(self.fileHandle.read(4), byteorder='little')
                
                if wavheader['SamplingRateIdx'] == 0:
                    wavheader['samplingrate'] = 125000
                elif wavheader['SamplingRateIdx'] == 1:
                    wavheader['samplingrate'] = 250000
                elif wavheader['SamplingRateIdx'] == 2:
                    wavheader['samplingrate'] = 500000
                elif wavheader['SamplingRateIdx'] == 3:
                    wavheader['samplingrate'] = 1000000
                elif wavheader['SamplingRateIdx'] == 4:
                    wavheader['samplingrate'] = 2000000
                else:
                    print('Wrong samplingrate in fileheader')
                # write dummy entries for wavtable
                wavheader['ADFrequency'] = 0
                wavheader['IFFrequency'] = 0
                wavheader['Bandwidth'] = 0
                wavheader['IQOffset'] = 0
                wavheader['nextfilename'] = ''
                #modify field to auxi format
                ## calculate stoptime from SR, headersize, #samples, bytespersample and starttime
                playseconds = wavheader['data_nChunkSize']/wavheader['nAvgBytesPerSec']
                stoptt = startt + timedelta(seconds= np.round(playseconds))
                wavheader['stoptime_dt'] =  stoptt
                # recode starttime and stoptime to auxi format
                # startt = self.wavheader['starttime']
                wavheader['starttime'] = [startt.year, startt.month, 0, startt.day, startt.hour, startt.minute, startt.second, 0]
                wavheader['stoptime'] = [stoptt.year, stoptt.month, 0, stoptt.day, stoptt.hour, stoptt.minute, stoptt.second, 0]

                wavheader['nextfilename'] = ('')    
                #wavheader['starttime_dt'] =  datetime(starttime[0],starttime[1],starttime[3],starttime[4],starttime[5],starttime[6])
                #wavheader['stoptime_dt'] =  datetime(stoptime[0],stoptime[1],stoptime[3],stoptime[4],stoptime[5],stoptime[6])
            else:
                #TODO: implement raw format if wanted
                print('unrecognized SDR')
                return False


        self.fileHandle.close()
        return(wavheader)
    
    def write_sdruno_header(self,wavfilename,wavheader,ovwrt_flag):       
        """write wavheader to the beginning of the current file 'wavfilename'
        if ovwrt_flag == True: 
            overwrite the first 216 bytes of an existing file with wavheader
        else:
            write a new file with the wavheader only; size is always 216 bytes
        
        Important: no check for the right datatypes in wavheader; if incorrect --> program crashes

        :param : wavtargetfilename
        :type : str
        :param : wavheader
        :type : dictionary
        :param : ovwrt_flag
        :type : boolean
        :raises : none
        :return: 
        :rtype: 
        """
        #print("wavheader writer reached")
        if wavheader['filesize'] > 2147483647:
            wavheader['filesize'] = int(2147483647)
            wavheader['data_nChunkSize'] = int(wavheader['filesize'] - 208)
            print(wavheader['fmt_nChunkSize'])
        if ovwrt_flag == True:
            fid = open(wavfilename, 'r+b')
            fid.seek(0)
        else:
            fid = open(wavfilename, 'wb')
        riff = "RIFF"
        wav = "WAVE"
        fmt = "fmt "
        #fid.write(pack("<4sL4s", wavheader['riff_chckID'][0:4].encode('ascii'), wavheader['filesize'], wavheader['wave_string'][0:4].encode('ascii')))
        fid.write(pack("<4sL4s", riff.encode('ascii'), wavheader['filesize'], wav.encode('ascii')))
        #  self.wavheader['starttime'][ix] = int(self.ui.tableWidget_starttime.item(ix, 0).text())
        #  self.wavheader['stoptime'][ix] = int(self.ui.tableWidget_starttime.item(ix, 1).text())
        #fid.write(pack("<4sI", wavheader['fmt_chckID'][0:4].encode('ascii'), wavheader['fmt_nChunkSize']))
        fid.write(pack("<4sI", fmt.encode('ascii'), wavheader['fmt_nChunkSize']))
        fid.write(pack("<hhllhh", wavheader['wFormatTag'], wavheader['nChannels'], wavheader['nSamplesPerSec'], 
                       wavheader['nAvgBytesPerSec'], wavheader['nBlockAlign'], wavheader['nBitsPerSample']))
        fid.write(pack("<4sl", wavheader['sdrtype_chckID'][0:4].encode('ascii'), wavheader['sdr_nChunkSize']))

        fid.write(pack("<16h", wavheader['starttime'][0], wavheader['starttime'][1], wavheader['starttime'][2], 
                       wavheader['starttime'][3], wavheader['starttime'][4], wavheader['starttime'][5], 
                       wavheader['starttime'][6], wavheader['starttime'][7], wavheader['stoptime'][0], 
                       wavheader['stoptime'][1], wavheader['stoptime'][2], wavheader['stoptime'][3], 
                       wavheader['stoptime'][4], wavheader['stoptime'][5], wavheader['stoptime'][6], wavheader['stoptime'][7]))
        fid.write(pack("<l", wavheader['centerfreq']))
        # Write ADFrequency, IFFrequency, Bandwidth, and IQOffset as long integers
        fid.write(pack('<l', wavheader['ADFrequency']))
        fid.write(pack('<l', wavheader['IFFrequency']))
        fid.write(pack('<l', wavheader['Bandwidth']))
        fid.write(pack('<l', wavheader['IQOffset']))

        # Write Unused array as four long integers
        dum = 0
        for i in range(4):
            fid.write(pack('<l', dum))

        # Write up to 96 characters of nextfilename as ASCII characters
        for i in range(min(96, len(wavheader['nextfilename']))):
            fid.write(pack('<c', bytes(wavheader['nextfilename'][i], 'ascii')))

        # Write spaces to fill up to 96 characters if nextfilename is shorter
        if len(wavheader['nextfilename']) < 96:
            for i in range(len(wavheader['nextfilename']), 96):
                fid.write(pack('<c', b' '))

        # Write data_ckID and data_nChunkSize

        fid.write(pack("<4sl", wavheader['data_ckID'][0:4].encode('ascii'), wavheader['data_nChunkSize']))


        fid.close()

    def basic_wavheader(self,icorr,irate,ifreq,bps,fsize,file_mod):
        """generate standard wavheader 
        Important: no check for the right datatypes in wavheader; if incorrect --> program crashes
        :param : icorr: icorr value for dat file
        :type : int
        :param : irate: irate value for dat file
        :type : int
        :param : ifreq: ifreq value for dat file
        :type : int
        :param : bps: bits per sample
        :type : int
        :param : fsize: file size in bytes
        :type : int
        :param : file_mod: file modification date/time as datetime object
        :type : datetime.datetime
        :raises : none
        :return: wavheader
        :rtype: dictionary
        """
        wavheader = {}
        wavheader['riff_chckID'] = str('RIFF')
        wavheader['filesize'] = fsize 
        wavheader['wave_string'] = str('WAVE')
        wavheader['fmt_chckID'] = str('fmt ')
        wavheader['fmt_nChunkSize'] = 16
        wavheader['wFormatTag'] = int(1)
        wavheader['nChannels'] = int(2)
        wavheader['nSamplesPerSec'] = int(irate)
        wavheader['nBitsPerSample'] = int(bps)
        wavheader['nBlockAlign'] = int(wavheader['nBitsPerSample']/8*2)
        wavheader['nAvgBytesPerSec'] = int(wavheader['nSamplesPerSec']*wavheader['nBitsPerSample']/4)
        wavheader['sdr_nChunkSize'] = 164
        wavheader['sdrtype_chckID'] = 'auxi'
        playtime = (fsize)/wavheader['nAvgBytesPerSec']
        starttime = [2000, 1, 1, 1, 0, 0, 0, 0]
        wavheader['starttime'] = starttime
        stoptime = [2000, 1, 1, 1, 0, 0, 0, 0]
        stoptime = [file_mod.year, file_mod.month, 0, file_mod.day, file_mod.hour, file_mod.minute, file_mod.second, int(1000*(playtime - np.floor(playtime)))]  
        
        wavheader['stoptime'] = stoptime
        wavheader['stoptime_dt'] =  datetime(stoptime[0],stoptime[1],stoptime[3],stoptime[4],stoptime[5],stoptime[6]) + timedelta(seconds = np.floor(playtime))
        wavheader['starttime_dt'] = wavheader['stoptime_dt'] - timedelta(seconds = np.floor(playtime))
        stt = wavheader['starttime_dt']
        if int(1000*(playtime - np.floor(playtime))) > 0:
            starttime = [stt.year, stt.month, 0, stt.day, stt.hour, stt.minute, stt.second - 1, int(1000*(1 - playtime + np.floor(playtime)))]  
        else:
            starttime = [stt.year, stt.month, 0, stt.day, stt.hour, stt.minute, stt.second, 0]  
        wavheader['starttime'] = starttime
        wavheader['centerfreq'] = ifreq
        wavheader['ADFrequency'] = 0
        wavheader['IFFrequency'] = 0
        wavheader['Bandwidth'] = 0
        wavheader['IQOffset'] = 0
        wavheader['nextfilename'] = ''
        wavheader['data_ckID'] = 'data'
        #aus filezize extrahieren
        wavheader['data_nChunkSize'] = wavheader['filesize'] - 208
        return(wavheader)
 
    def extract_startdatetimestring(self,wavheader):
        """_synthetize a string which contains the 
        start date and time and returns it in the SDRUno filename format
        Format: _YYYYMMDD_hhmmssZ

        :param : wavheader
        :type : dictionary
        :raises [ErrorType]: [ErrorDescription]
        :return: datetimestring
        :rtype: str
            """
        starttime = wavheader['starttime']
        start_year=str(starttime[0])
        if starttime[1] < 10:
            start_month ='0' + str(starttime[1])
        else:
            start_month = str(starttime[1])
        if starttime[3] < 10:
            start_day ='0' + str(starttime[3])
        else:
            start_day = str(starttime[3])
        startdate_string = start_year + start_month + start_day
        if starttime[4] < 10:
            start_hour = '0' + str(starttime[4])
        else:
            start_hour = str(starttime[4])
        if starttime[5] < 10:
            start_min = '0' + str(starttime[5])
        else:            
            start_min = str(starttime[5])
        if starttime[6] < 10:
            start_sec='0' + str(starttime[6])
        else:
            start_sec = str(starttime[6])
        datetimestring = '_' + start_year + start_month + start_day
        datetimestring = datetimestring + '_' +start_hour + start_min +start_sec + 'Z'
        ###TODO: check if also MHz names are possible
                # timeobj1 =  ndatetime.timedelta(seconds=20)
        # str(timeobj2-timeobj1)

        return datetimestring

