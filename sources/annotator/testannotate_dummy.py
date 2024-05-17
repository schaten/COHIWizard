def autoscan_fun(self):
        for ix in range(self.NUMSNAPS):
            position = int(np.floor(ix/self.NUMSNAPS*100))
            self.set_progressvalue(position)
            self.set_continue(False)
            self.SigProgressBar.emit()
            # wait for confirmation from Progress bar updating
            while self.get_continue() == False:
                time.sleep(0.01)
            ............
            ret = auxi.readsegment_new(self,self.get_filepath(),file_readix,self.get_readoffset(), self.get_datablocksize(),BPS,BPS,wavheader["wFormatTag"])#TODO: replace by slots communication
            data = ret["data"]
            ....................
            self.set_continue(False)
            self.SigAnnSpectrum.emit(data)
....................
            pdata = self.get_pdata()
            ann_master[ix]["FREQ"] = pdata["datax"] 
            ann_master[ix]["PKS"] = pdata["peaklocs"]
            peaklocs = pdata["peaklocs"]
            basel = pdata["databasel"] + self.get_baselineoffset()
            ann_master[ix]["SNR"] = pdata["datay"][peaklocs] - basel[peaklocs]
            ann_master[ix]["PEAKVALS"] = pdata["datay"][peaklocs]
            self.peakvals_union = np.union1d(self.peakvals_union, ann_master[ix]["PEAKVALS"])  #TODO: UNSINN
            locs_union = np.union1d(locs_union, ann_master[ix]["PKS"])
            freq_union = np.union1d(freq_union, ann_master[ix]["FREQ"][ann_master[ix]["PKS"]])
        # purge self.locs.union and remove elements the frequencies of which are
        # within 1 kHz span 
        uniquefreqs = pd.unique(np.round(freq_union/1000))
        ################# THIS IS PROBLEMATIC
        xyi, x_ix, y_ix = np.intersect1d(uniquefreqs, np.round(freq_union/1000), return_indices=True)
        locs_union= locs_union[y_ix]
        freq_union = freq_union[y_ix]
        self.peakvals_union = self.peakvals_union[y_ix] #TODO: UNSINN
        #########################################################
        self.set_unions([locs_union,freq_union, self.peakvals_union])
        self.SigUpdateUnions.emit()
        meansnr = np.zeros(len(locs_union))
        meanpeakval = np.zeros(len(locs_union))
        minsnr = 1000*np.ones(len(locs_union))
        maxsnr = -1000*np.ones(len(locs_union))
        reannot = {}
        datasnaps = []
        for ix in range(self.NUMSNAPS):
            # find indices of current LOCS in the unified LOC vector locs_union
            sharedvals, ix_un, ix_ann = np.intersect1d(locs_union, ann_master[ix]["PKS"], return_indices=True)
            # write current SNR to the corresponding places of the self.reannotated matrix
            reannot["SNR"] = np.zeros(len(locs_union))
            reannot["SNR"][ix_un] = ann_master[ix]["SNR"][ix_ann]
            reannot["PEAKVALS"] = np.zeros(len(locs_union)) #TODO: UNSINN

            reannot["PEAKVALS"][ix_un] = ann_master[ix]["PEAKVALS"][ix_ann]
            datasnaps.append(reannot["PEAKVALS"])
            #Global Statistics, without consideration whether some peaks vanish or
            #appear when running through all values of ix
            meansnr = meansnr + reannot["SNR"]
            meanpeakval = meanpeakval + reannot["PEAKVALS"]
            #min and max SNR data are currently not being used.
            minsnr = np.minimum(minsnr, reannot["SNR"])
            maxsnr = np.maximum(maxsnr, reannot["SNR"])
            #print("annotate worker findpeak")
        self.set_datasnaps(datasnaps)

