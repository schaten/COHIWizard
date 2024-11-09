# How to add a new tab(module)

## extend the file structure

create a new subfolder /my_module and /my_module/ressources as subdirectories of ~/sources

create a new subfolder /my_module/icons as subdirectories of ~/sources if pngs, svg's are to be used

## create a PyQT widget `my_module_widget.py`

**Method 1: writing from scratch**

move to /my_module and create a file `my_module_widget.py` containing the following structure:

	from PyQt5 import QtCore, QtGui, QtWidgets
	
	class Ui_my_module_widget(object):
    	  def setupUi(self, my_module_widget):
		  your code

**Method 2: using QTDesigner**

1. Create a new object of the class 'Widget'

2. Name the widget (ObjectName) 'my_module_widget', my_module standing for the name of your new module and set windowTitle to ""

3. Add a grid layout and name it 'my_module_gridlayout'.

3. Add all needed GUI elements and subwidgets to the gridlayout and name their ObjectNames appropriately

4. set horisontal/vertical size policy to 'minimum' in most items, sometimes to 'maximum', only exceptionally to fixed  (--> resizeable)

5. Convert the ui-File to a py-script typing `pyuic5 -x ~/sources/my_module/my_module_widget.ui -o ~/sources/my_module/my_module_widget.py`


## write your new module `my_module.py`

1. Modify a copy of the abstract module `abstract_module.py` to `my_module.py`

`my_module.py` must contain the classes

	`my_module_m` (model)
	`my_module_c` (controller)
	`my_module_v` (view)

2. Write your code

3. Access other modules by standard signalling and the standard self.m["..."] items provided via core as well as the rxhandler rxh(self)

4. OPTIONAL: in my_module_v(self), if wanted, add new canvas for embedding plots:

* add the following line to rxh(self):

		if _value[0].find("canvasbuild") == 0:
		  self.canvasbuild(_value[1])

* add method:
    	
		def canvasbuild(self,gui):
		  self.cref = auxi.generate_canvas(self,self.gui.my_module_gridlayout,[row_index, col_index, line_span, col_span],[trow_index, tcol_index, tline_span, tcol_span],gui)

	
For plotting into this canvas reference all 'ax' and 'canvas' operations to self.cref: self.cref["ax"], self.cref["canvas"]

		[row_index, col_index, line_span, col_span]: coordinates and extension of the plot canvas
		[trow_index, tcol_index, tline_span, tcol_span]: coordinates and extension of the canvas toolbar, if wanted
		if trow < 0 --> no toolbar is being assigned

## connect your new module with the core module:


1. open the module COHIWizard.py and go to the last section `if __name__ == '__main__'`:

2. add the import command:

		from my_module import my_module

3. just before the comment ### ADD NEW MODULES HERE ### add the following block:

    	if 'my_module' in sys.modules: 
          from my_module import my_module_widget
          tabUI_my_module = my_module_widget.Ui_my_module_widget()
          tab_my_module_widget = QtWidgets.QWidget()
          tab_my_module_widget.setObjectName("tab_my_module_widget")
          tab_my_module_widget.setWindowTitle("my_module")
          tab_my_module_widget.setWindowIconText("my_module")
          tabUI_my_module.setupUi(tab_my_module_widget)
          a = gui.gui.tabWidget.addTab(tab_my_module_widget, "")
          gui.gui.tabWidget.setTabText(a,"my_module")


4. just before the comment ###  ADD NEW MODULE TABDICTSYNTESIS HERE ### add the following block:


    	if 'my_module' in sys.modules:
          my_module_m = my_module.my_module_m()
          my_module_c = my_module.my_module_c(my_module_m)
          my_module_v = my_module.my_module_v(tabUI_annotator,my_module_c,my_module_m)
          tab_dict["list"].append("my_module")
          tab_dict["tabname"].append("my_module")


General: when using QT file dialogues always use self.m["QTMAINWINDOWparent"] as reference like:

QFileDialog.getSaveFileName(self.m["QTMAINWINDOWparent"], 
                                                   "Save File", 
                                                   "*.proj",  # Standardmäßig kein voreingestellter Dateiname
                                                   "proj Files (*.proj);;All Files (*)",  # Filter für Dateitypen
                                                   options=options)

