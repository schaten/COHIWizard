"""Make file for compiling the COHIWizard with pyinstaller importing hidden imports (submodules)
This is necessary for versions of the COHIWizard after introducing dynamic impot of the modules"""

import subprocess
import yaml
import importlib

def load_config_from_yaml(file_path):
    """load module configuration from yaml file"""
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)

def dynamic_import_from_config(config,sub_module):
    """Dynamic import of modules based on module configuration"""
    imported_modules = {}
    for directory, module in config[sub_module].items():
        try:
            # create path <directory>.<module>
            full_module_path = f"{directory}.{module}"
            # Importmodule dynamically
            imported_module = importlib.import_module(full_module_path)
            imported_modules[module] = imported_module
            print(f"Successfully imported {module} from {full_module_path}.")
        except ModuleNotFoundError as e:
            print(f"dynamic import Error importing {module} from {directory}: {e}")
    return imported_modules

print("################################################################################")
config = load_config_from_yaml("config_modules.yaml")
sub_module = "modules"
mod_base = {'player':'playrec'}
config['modules'] = {**mod_base, **config['modules']}
widget_base = {'player': 'Player'}
config['module_names'] = {**widget_base, **config['module_names']}
list_mvct_directories = list(config['modules'].keys())
#get list of corresponding mvct modules
list_mvct_modules = list(config['modules'].values())
#add dict of widget modules to config
aux_dict = {}
for ix in range(len(list_mvct_directories)):
    aux_dict[list_mvct_directories[ix]] = list_mvct_directories[ix] + "_widget"
config["widget"] = aux_dict
#print(f"__main__ 2nd if NEW: config, aux_dict: {config['widget']}")

#get list of corresponding widget modules
list_widget_modules = list(config['widget'].values())

# Baue den pyinstaller Befehl zusammen
#command = ['pyinstaller', ' --icon=COHIWizard_ico4.ico', '-F', 'COHIWizard.py']
command = 'pyinstaller --icon=COHIWizard_ico4.ico -F COHIWizard.py'#
##########################
# for ix in range(len(list_mvct_directories)): 
#     module = list_mvct_directories[ix] + "." + list_mvct_modules[ix] 
#     command.append(f'--hidden-import={module}')
# for ix in range(len(list_mvct_directories)): 
#     module = list_mvct_directories[ix] + "." + list_widget_modules[ix] 
#     command.append(f'--hidden-import={module}')

for ix in range(len(list_mvct_directories)): 
    module = list_mvct_directories[ix] + "." + list_mvct_modules[ix] 
    command += (f' --hidden-import={module}')
for ix in range(len(list_mvct_directories)): 
    module = list_mvct_directories[ix] + "." + list_widget_modules[ix] 
    command += (f' --hidden-import={module}')

# Führe den Befehl aus
#process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
subprocess.run(command)
# # Liest die Ausgaben und gibt sie in Echtzeit auf der Konsole aus
# for line in process.stdout:
#     print(line.decode(), end='')  # stdout Ausgabe

# for line in process.stderr:
#     print(line.decode(), end='')  # stderr Ausgabe

# process.wait()  # Warten bis der Prozess abgeschlossen ist

