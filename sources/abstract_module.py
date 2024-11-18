#IMPORT WHATEVER IS NEEDED
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5 import QtGui
import logging
from auxiliaries import auxiliaries as auxi     #access some auxiliary methods
from auxiliaries import WAVheader_tools         #access methods for reading, writing and changing SDR-wav-headers
import logging
import other stuff #TODO

class abstract_module_m(QObject):
    #__slots__ = ["None"]

    ########## TODO module specific individual signals: #################
    SigModel_mysig = pyqtSignal() #sample signal

    def __init__(self):
        super().__init__()

        ######################  Mandatory part, do not remove: ###############
        self.mdl = {}
        # Create a custom logger
        logging.getLogger().setLevel(logging.DEBUG)
        # Create aLogger with the name of the module
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
        #####################################################################

        ###################### TODO Individual part: ########################
        # TODO initialize your own individual constants #####################
        self.CONST_SAMPLE = 0 # sample constant

        ########### TODO initialize your own individual variables: ######
        self.mdl["my_var1"] = 0 #sample variable
        self.mdl["my_var2"] = False #sample variable
        # .......
        #################################################################


class abstract_module_c(QObject):
    """_view method
    """
    #__slots__ = ["contvars"]

    ########## mandatory Signals, do not remove ####################
    SigActivateOtherTabs = pyqtSignal(str,str,object)
    SigRelay = pyqtSignal(str,object)
    ################################################################

    ########## TODO module specific individual signals: #############
    SigController_mysigc1 = pyqtSignal() #any other signal ...
    SigController_mysigc2 = pyqtSignal() #any other signal ...
    ################################################################


    def __init__(self, abstract_module_m): #TODO: remove gui
        super().__init__()

        ############# mandatory variables, do not remove: ##########
        self.m = abstract_module_m.mdl
        self.logger = abstract_module_m.logger
        ############################################################

        ########### TODO initialize your own individual variables: ######
        self.myvarc1 = 0     #sample variable
        self.myvarc2 = True  #sample variable
        # .......
        #################################################################

    def dummy(self):
        print("hello from superclass")
        

class abstract_module_v(QObject):
    """_view methods for resampling module
    TODO: gui.wavheader --> something less general ?
    """
    #__slots__ = ["viewvars"]

    ########## mandatory Signals, do not remove ####################
    SigUpdateGUI = pyqtSignal(object)
    SigActivateOtherTabs = pyqtSignal(str,str,object)
    SigRelay = pyqtSignal(str,object)
    ################################################################

    # module specific new signals:
    ########## TODO module specific individual signals: #################
    SigController_mysigv1 = pyqtSignal() #any other signal ...
    SigController_mysigv2 = pyqtSignal() #any other signal ...
    ####################################################################


    def __init__(self, gui, abstract_module_c, abstract_module_m):
        super().__init__()

        ######################  Mandatory part, do not remove: ###############
        self.m = abstract_module_m.mdl
        self.abstract_module_c = abstract_module_c
        self.gui = gui # is assigned by core ! mandatory
        self.logger = abstract_module_m.logger
        self.abstract_module_c.SigRelay.connect(self.rxhandler)
        self.abstract_module_c.SigRelay.connect(self.SigRelay.emit)
        self.init_abstractmodule_ui()
        self.abstract_module_c.SigRelay.connect(self.SigRelay.emit)
        ######################################################################

        ########### TODO initialize your own individual variables: ######
        self.myvarv1 = 0     #sample variable
        self.myvarv2 = True  #sample variable
        # .......
        #################################################################

    def init_abstractmodule_ui(self):
        #TODO your code for initializing the GUI, establish connections, set UI elements ... goes here ###################
        #self.gui.GUIMETHOD(dosomething) or self.gui.GUIELEMENT.property = something
        #self.gui.GUIMETHOD.connect(self.related_method) #EXAMPLE
        pass


    def rxhandler(self,_key,_value):
        """
        handles remote calls from other modules via Signal SigRX(_key,_value)
        :param : _key
        :type : str
        :param : _value
        :type : object
        :raises [ErrorType] : [ErrorDescription]
        :returns : none
        :rtype : none
        """
        #TODO: replace all instances of 'abstract_module' by name of your module 'my_module' ##########
        ########### mandatory part accessed by core via signalling, do not remove: ##################
        if _key.find("cm_abstract_module") == 0 or _key.find("cm_all_") == 0:
            #set mdl-value
            self.m[_value[0]] = _value[1]
        if _key.find("cui_abstract_module") == 0:
            _value[0](_value[1]) #still unused, reserved for future applications
        if _key.find("cexex_abstract_module") == 0  or _key.find("cexex_all_") == 0:
            if  _value[0].find("updateGUIelements") == 0:
                self.updateGUIelements()
            if  _value[0].find("reset_GUI") == 0:
                self.reset_GUI()
            if  _value[0].find("logfilehandler") == 0:
                self.logfilehandler(_value[1])
            if  _value[0].find("canvasbuild") == 0:
                self.canvasbuild(_value[1])
        ##############################################################################################

            ########TODO handle individual new method ##################
            # if  _value[0].find("plot_spectrum") == 0: #EXAMPLE
            #     self.plot_spectrum(0,_value[1])   #EXAMPLE

    def canvasbuild(self,gui):
        """
        sets up a canvas to which graphs can be plotted
        Use: calls the method auxi.generate_canvas with parameters self.gui.gridlayoutX to specify where the canvas 
        should be placed, the coordinates and extensions in the grid and a reference to the QMainwidget Object
        generated by __main__ during system startup. This object is relayed via signal to all modules at system initialization 
        and is automatically available (see rxhandler method)
        the reference to the canvas object is written to self.cref
        :param : gui
        :type : QMainWindow
        :raises [ErrorType]: [ErrorDescription]
        :return: none
        :rtype: none
        """
        #TODO your code goes here ###################
        ###### TODO: activate call correctly, this is just an example ##########
        #self.cref = auxi.generate_canvas(self,self.gui.gridLayout_5,[6,0,6,4],[-1,-1,-1,-1],gui)
        pass


    def logfilehandler(self,_value):
        # standard logfile handler, can be extended ad libidum
        #TODO: replace all instances of 'abstract_module' by name of your module 'my_module' ##########
        if _value is False:
            self.logger.debug("abstract module: INACTIVATE LOGGING")
            self.logger.setLevel(logging.ERROR)
        else:
            self.logger.debug("abstract module: REACTIVATE LOGGING")
            self.logger.setLevel(logging.DEBUG)
        #TODO your code goes here ###################

    def updateGUIelements(self):
        """
        updates GUI elements , usually triggered by a Signal SigTabsUpdateGUIs to which 
        this method is connected in the __main__ of the core module. Updating can also handle 
        values from other modules via the respective signals
        :param : none
        :type : none
        :raises [ErrorType]: [ErrorDescription]
        :return: flag False or True, False on unsuccessful execution
        :rtype: Boolean
        """
        print("abstract_module: updateGUIelements")
        #TODO: self.gui.DOSOMETHING
        #TODO your code goes here ###################
        return #TODO: return something ?

    def reset_GUI(self):
        """
        resets GUI of this module. 
        :param : none
        :type : none
        :raises [ErrorType]: [ErrorDescription]
        :return: flag False or True, False on unsuccessful execution
        :rtype: Boolean
        """
        pass
        #TODO your code goes here ###################
        return #TODO: return something ?