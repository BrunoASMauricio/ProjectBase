import re
import os
import sys
import shutil
import curses
import logging
import traceback
import difflib
import unicodedata

from datetime import datetime
import socket # for gethostname
import getpass # for getuser

from data.paths import GetBasePaths
from data.colors import ColorFormat, Colors
from data.paths import CreateParentPath

def ErrorCheckLogs(exception):
    print("ERROR: Check logs at /tmp/project_base.log for more information")
    logging.error(f"Uncaught exception: {type(exception)} {exception}")
    logging.error(traceback.format_exc())

def RemoveDuplicates(lst):
    return list(set(lst))

def AppendToEnvVariable(env_variable, new_value):
    if new_value == None:
        new_value = ""

    if env_variable not in os.environ.keys():
        os.environ[env_variable] = new_value
    else:
        # Only append if not already present
        BasicList = os.environ[env_variable].split(os.pathsep)
        if new_value not in BasicList:
            os.environ[env_variable] = new_value + os.pathsep + os.environ[env_variable]

def PrintableCharacterLength(string):
    return len(RemoveAnsiEscapeCharacters(RemoveControlCharacters(string)))

def CLICenterString(string, pad=" "):
    # Color characters count for length :()
    string_len = PrintableCharacterLength(string)
    cols, _ = shutil.get_terminal_size(fallback=(string_len, 1))
    padding_len = int((cols - string_len) / 2)
    return pad * padding_len + string + pad * padding_len

def GetTextDiff(Text1, Text2):
    diff = difflib.ndiff(Text1.split("\n"), Text2.split("\n"))
    return ''.join(diff)

def RemoveControlCharacters(str):
    """
    Removes control characters. Keeps \\n except if trailing
    """
    allowed_CCs = ['\n', '\t']
    new_str = "".join(ch for ch in str if (unicodedata.category(ch)[0] != "C" or ch in allowed_CCs))
    return new_str.rstrip()

def RemoveAnsiEscapeCharacters(str):
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub("", str)

def RemoveSequentialDuplicates(str, sub_str):
    List = str.split(sub_str)
    List = [list_el for list_el in List if len(list_el) != 0]

    NewStr = sub_str.join(List)

    # Special cases for starting/ending with sub_str (will lead to empty
    # element on either side, without being sequential duplicate)
    if str[0] == sub_str:
        NewStr = sub_str + NewStr

    if str[-1] == sub_str:
        NewStr = NewStr + sub_str

    return NewStr

def IsEmpty(object):
    if object == None:
        return True

    if type(object) == type({}):
        return len(object.keys()) == 0

    if type(object) == type([]) or type(object) == type(""):
        return len(object) == 0

    raise Exception("Unknown type for IsEmpty: " + str(type(object)))

def RemoveNonAlfanumeric(string):
    return re.sub(r'[^A-Za-z0-9]+', '', string)

def ValueNotEmpty(list, name):
    if name in list and False == IsEmpty(list[name]):
        return True
    return False

"""
Gets the value from the dict if Name exists, or
Default is returned if it does not exist
"""
def GetValueOrDefault(dict, name, default = None):
    if name in dict.keys():
        # If there is a default value, enforce the type is the same to the
        # existing value
        if default != None and type(default) != type(dict[name]):
            raise Exception(f"Incorrect type \"{type(dict[name])}\" for value named {name}. Should be {type(default)}")
        return dict[name]
    return default

"""
Abort running program
"""
def Abort(message):
    print(ColorFormat(Colors.Red, message))
    sys.stdout.flush()
    sys.exit(-1)

"""
Abort if a condition is false
"""
def Assert(condition, message=None):
    if not condition:
        if message == None:
            Abort("Failed condition")
        else:
            Abort(message)

"""
Remove 'None' elements from a list
"""
def RemoveEmpty(iterable):
    if type(iterable) == type(list()):
        return [list_el for list_el in iterable if IsEmpty(list_el) == False]
    else:
        new_dict = {}
        for key in iterable:
            if IsEmpty(iterable[key]) == False:
                new_dict[key] = iterable[key]
        return new_dict
def StringIsNumber(Str):
    number_regex = '^[0-9]+$'
    if(re.search(number_regex, Str)):
        return True
    return False

def LoadFromFile(file_path, default=None):
    if os.path.isfile(file_path):
        with open(file_path, "r") as file:
            return file.read()
    return default

def DumpToFile(file_path, data, mode='w'):
    with open(file_path, mode) as file:
        file.write(data)

"""
Present Message to user and return True if the response is y or Y, False if n or N
Loop if response is not in nNyY
"""
def UserYesNoChoice(message):
    while True:
        print(message)
        answer = input("("+ColorFormat(Colors.Green,"Yy")+"/"+ColorFormat(Colors.Red,"Nn")+"): ")
        if answer in ["y", "Y"]:
            answer = True
            break
        elif answer in ["n", "N"]:
            answer = False
            break
        else:
            continue
    return answer

# Sets up a script according to its template and the target variable substitutions
def SetupTemplateScript(script_name, target_file, variable_substitutions={}):
    whole_script = ""
    project_base_paths = GetBasePaths()

    if script_name.endswith(".sh"):
        # Get bash header
        with open(project_base_paths["templates"]+"/scriptHeader.sh", 'r') as f:
            whole_script = f.read()+"\n\n"

    # Get rest of script
    with open(project_base_paths["templates"]+"/"+script_name, 'r') as f:
        whole_script += f.read()
    # Perform variable substitutions
    for variable_name in variable_substitutions:
        whole_script = whole_script.replace("$$"+variable_name+"$$", variable_substitutions[variable_name])

    # Write script back
    CreateParentPath(target_file)
    with open(target_file, 'w') as f:
        f.write(whole_script)

"""
If obj is string, returns it
Otherwise assumes it is a function that returns a string, calls that function and returns the result
"""
def GetText(obj):
    if obj == None:
        return ""
    # Only accept strings or functions
    if type(obj) == type(""):
        return obj

    # Non-function is ok to fail here
    return obj()

def GetNow():
    return str(datetime.now())

def GetTime():
    current_datetime = datetime.now()
    return str(current_datetime.strftime("%m/%d/%Y %H:%M:%S"))

def GetHost():
    return f"{getpass.getuser()}@{socket.gethostname()}"

def ResetTerminal():
    # Initialize curses
    stdscr = curses.initscr()

    # Set terminal back to normal mode
    curses.endwin()
    del stdscr