# Installation:

## Method A (different versions, Windows 10/11 only): 

1) download the respective installation package from the [COHIRADIA webpage](https://www.radiomuseum.org/dsp_cohiradia.cfm) (zip file)
2) unpack the zip file to a local directory of your PC, say `cohihome`
3) start the exe File SDR_COHIWizard_v26.exe

## Method B (most recent version) for execution under Python (not yet tested in LUNIX environments !): 

1) install Python on your PC
2) clone the repository from GITHUB to your PC to a folder say cohihome
3) change to this folder
4) create a virtual environment with `python –m venv venv`
5) activate the venv by `venv/Scripts/activate`
6) install the required packages from the requirements.txt (in cohihome) file by typing `pip install -r requirements.txt`
7) change dir to cohifolder/sources
7) run the main script: `python SDR_COHIWizard_v26.py`

SDR_COHIWizard_v26.py starts up a GUI with a recorder/player and various utilities for e.g. visualization of the spectra, resampling, annotation (beta version) and editing of wav-headers.
