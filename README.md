# COHIWizard

COHIWizard is an application which allows for playback, recording, analysis and processing of broadband RF signals when using a [STEMLAB125-14](https://redpitaya.com/de/stemlab-125-14/) by Red Pitaya . Main purpose is archiving AM radio bands like LW, MW, SW, VLF in the context of [COHIRADIA](https://www.radiomuseum.org/dsp_cohiradia.cfm) but other purposes can be thought of. While recording the data is stored in IQ data files with 32 bit per sample (2 x 16 bits complex) and carries an extended wav-header in the standard format used for most software defined radios (SDR). 

Appropriate recordings can be played back on historic Radio receivers with external antenna jack and all transmitters active at the time of the recording can then be tuned through and listened to on the radio. Detailed information for installation, hardware setup and an archive with many recordings from 2006 on can be found on [COHIRADIA](https://www.radiomuseum.org/dsp_cohiradia.cfm).

# Installation:

## Method A (different versions, Windows 10/11 only): 

1) download the respective installation package from the [COHIRADIA webpage](https://www.radiomuseum.org/dsp_cohiradia.cfm) (zip file)
2) unpack the zip file to a local directory of your PC, say `cohihome`
3) start the exe File SDR_COHIWizard_v26.exe

## Method B (most recent version) for execution under Python (also running under LUNIX but not yet excessively tested. The main functions have been successfully executed under DEBIAN 10): 

<<<<<<< HEAD
1) install Python v3.9.7 on your PC; the COHIWIzard may fail with other versions, though they may work (not yet tested)
2) clone the repository from GITHUB to your PC to a folder say cohihome
=======
1) install Python on your PC
2) clone the repository from GITHUB to your PC to a folder, say cohihome
>>>>>>> 393a2bd7848c718107a214e4678fbc33f5faf77f
3) change to this folder
4) create a virtual environment with `python –m venv venv`
5) activate the venv by `venv/Scripts/activate`
6) install the required packages from the requirements.txt (in cohihome) file by typing `pip install -r requirements.txt`
7) change dir to cohifolder/sources
7) run the main script: `python SDR_COHIWizard.py`

SDR_COHIWizard.py starts up a GUI with a recorder/player and various utilities for e.g. visualization of the spectra, resampling, annotation (beta version) and editing of wav-headers.

When using a local git you can also access the branch 1.3 which is currently experimental and contains the version currently under development.
