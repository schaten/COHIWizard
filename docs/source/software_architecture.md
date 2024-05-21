# Software architecture

The software contains a core module and, for each tab of the GUI, an individual additional module which handles all the methods required under a tab. Additionally there are auxiliary modules which implement helper classes which are accessed by one or more of the tab modules.

The software architecture is built up according to the design pattern model-view-controller. This means that each module X contains three base classes X_m, X_c and X_v, '_m', '_c' and '_v' standing for 'model', 'control' and 'view'. They are instantiated in the __main__ section as:

        X_m = X.X_m()
        X_c = X.X_c(X_m)
        X_v = X.X_v(core.gui,X_c,X_m)

There may also be additional classes for thread workers, as several long-lasting processes need to be carried out in separate threads, apart from the main thread of the GUI.