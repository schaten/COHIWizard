#IMPORT WHATEVER IS NEEDED
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5 import QtGui
from auxiliaries import auxiliaries as auxi

class abstract_module_m(QObject):
    __slots__ = ["None"]
    SigModelXXX = pyqtSignal()

    #TODO: replace all gui by respective state references if appropriate
    def __init__(self):
        super().__init__()
        # Constants
        self.CONST_SAMPLE = 0 # sample constant
        self.mdl = {}
        self.mdl["sample"] = 0

class abstract_module_c(QObject):
    """_view method
    """
    __slots__ = ["contvars"]

    SigAny = pyqtSignal()

    def __init__(self, abstract_module_m): #TODO: remove gui
        super().__init__()

    # def __init__(self, *args, **kwargs): #TEST 09-01-2024
    #     super().__init__(*args, **kwargs)
        viewvars = {}
        #self.set_viewvars(viewvars)
        self.m = abstract_module_m.mdl
        

class abstract_module_v(QObject):
    """_view methods for resampling module
    TODO: gui.wavheader --> something less general ?
    """
    __slots__ = ["viewvars"]

    SigAny = pyqtSignal()
    SigCancel = pyqtSignal()
    SigUpdateGUI = pyqtSignal(object)
    SigSyncGUIUpdatelist = pyqtSignal(object)

    def __init__(self, gui, abstract_module_c, abstract_module_m):
        super().__init__()

        #viewvars = {}
        #self.set_viewvars(viewvars)
        self.m = abstract_module_m.mdl
        self.DATABLOCKSIZE = 1024*32
        self.gui = gui #gui_state["gui_reference"]#system_state["gui_reference"]

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
        print("abstract_module: updateGUIelements")
        #self.gui.DOSOMETHING

    def update_GUI(self,_key): #TODO TODO: is this method still needed ? reorganize. gui-calls should be avoided, better only signalling and gui must call the routenes itself
        print(" view spectra updateGUI: new updateGUI in view spectra module reached")
        self.SigUpdateGUI.disconnect(self.update_GUI)
        if _key.find("ext_update") == 0:
            #update resampler gui with all elements
            #TODO: fetch model values and re-fill all tab fields
            print("abstract_module update_GUI reached")
            pass
        #other key possible: "none"
        #DO SOMETHING
        self.SigUpdateGUI.connect(self.update_GUI)

