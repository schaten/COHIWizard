from PyQt5.QtCore import QTimer
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *

class status(QObject):
    """data container class for TODO: future implementations
    this class has no methods except get and set, only data objects are represented here
    data:
        status: system variables which once changed should trigger a GUI update via a Signal self.SigUpdateStatus
        flags: flag variables which serve for rapid communication without releasing a trigger (Signal)
    :return: _description_
    :rtype: _type_
    """
    SigUpdateStatus = pyqtSignal()
    SigUpdateFlags = pyqtSignal()
    
    __slots__ = ["status","flags","progress"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Constants
        #self.status = {}    # Test Mode Flag for testing the App without a

    def set_status(self,_value):
        self.__slots__[0] = _value
        #print("set status reached")#TODO remove after tests
        self.SigUpdateStatus.emit()

    def get_status(self):
        return(self.__slots__[0])

    def set_flags(self,_value):
        self.__slots__[1] = _value
        #print("set status flags reached")#TODO remove after tests
        self.SigUpdateFlags.emit()

    def get_flags(self):
        return(self.__slots__[1])
    
    def set_progress(self,_value):
        self.__slots__[2] = _value

    def get_progress(self):
        return(self.__slots__[2])
        
class WIZ_auxiliaries():
    """contains many auxiliariy methods fo the COHIWizard
    :return: _description_
    :rtype: _type_
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dummy = True
        # Constants
        #self.status = {}    # Test Mode Flag for testing the App without a

    def standard_errorbox(errortext):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setText("Error")
        msg.setInformativeText(errortext)
        msg.setWindowTitle("Error")
        msg.exec_()

    def standard_infobox(infotext):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setText("ATTENTION")
        msg.setInformativeText(infotext)
        msg.setWindowTitle("ATTENTION")
        msg.exec_()