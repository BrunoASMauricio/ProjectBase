import re
import os
import sys
import unicodedata
from data.colors import ColorFormat, Colors
from data.paths import GetBasePaths

def AppendToEnvVariable(EnvVariable, NewValue):
    if NewValue == None:
        NewValue = ""

    if EnvVariable not in os.environ.keys():
        os.environ[EnvVariable] = NewValue
    else:
        # Only append if not already present
        BasicList = os.environ[EnvVariable].split(os.pathsep)
        if NewValue not in BasicList:
            os.environ[EnvVariable] = NewValue + os.pathsep + os.environ[EnvVariable]

def GetTextDiff(Text1, Text2):
    diff = difflib.ndiff(Text1.split("\n"), Text2.split("\n"))
    return ''.join(diff)

def RemoveControlCharacters(Str):
    """
    Removes control characters. Keeps \\n except if trailing
    """
    AllowedCCs = ['\n', '\t']
    NewStr = "".join(Ch for Ch in Str if (unicodedata.category(Ch)[0] != "C" or Ch in AllowedCCs))
    return NewStr.rstrip()

def RemoveAnsiEscapeCharacters(Str):
    AnsiEscape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return AnsiEscape.sub("", Str)

def RemoveSequentialDuplicates(Str, SubStr):
    List = Str.split(SubStr)
    List = [ListEl for ListEl in List if len(ListEl) != 0]

    NewStr = SubStr.join(List)

    # Special cases for starting/ending with SubStr (will lead to empty
    # element on either side, without being sequential duplicate)
    if Str[0] == SubStr:
        NewStr = SubStr + NewStr

    if Str[-1] == SubStr:
        NewStr = NewStr + SubStr

    return NewStr

def IsEmpty(Object):
    if Object == None:
        return True

    if type(Object) == type({}):
        return len(Object.keys()) == 0

    if type(Object) == type([]) or type(Object) == type(""):
        return len(Object) == 0

    raise Exception("Unknown type for IsEmpty: " + str(type(Object)))

def RemoveNonAlfanumeric(String):
    return re.sub(r'[^A-Za-z0-9]+', '', String)

def ValueNotEmpty(list, name):
    if name in list and False == IsEmpty(list[name]):
        return True
    return False

"""
Gets the value from the dict if Name exists, or
Default is returned if it does not exist
"""
def GetValueOrDefault(Dict, Name, Default = None):
    if Name in Dict.keys():
        return Dict[Name]
    return Default

"""
Abort running program
"""
def Abort(Message):
    print(ColorFormat(Colors.Red, Message))
    sys.stdout.flush()
    sys.exit(-1)

"""
Abort if a condition is false
"""
def Assert(Condition, Message=None):
    if not Condition:
        if Message == None:
            Abort("Failed condition")
        else:
            Abort(Message)

"""
Remove 'None' elements from a list
"""
def RemoveNone(List):
    return [ListEl for ListEl in List if ListEl != None]

"""
True if Value is None or 0
TODO: Remove
"""
def IsEmptyOrNone(Value):
    return (Value == None or len(Value) == 0)

def StringIsNumber(Str):
    number_regex = '^[0-9]+$'
    if(re.search(number_regex, Str)):
        return True
    return False

"""
Present Message to user and return True if the response is y or Y, False if n or N
Loop if response is not in nNyY
"""
def UserYesNoChoice(Message):
    while True:
        print(Message)
        Answer = input("("+ColorFormat(Colors.Green,"Yy")+"/"+ColorFormat(Colors.Red,"Nn")+"): ")
        if Answer in ["y", "Y"]:
            Answer = True
            break
        elif Answer in ["n", "N"]:
            Answer = False
            break
        else:
            continue
    return Answer

# Sets up a script according to its template and the target variable substitutions
def SetupTemplateScript(ScriptName, TargetFile, VariableSubstitutions={}):
    WholeScript = ""
    ProjectBasePaths = GetBasePaths()

    if ScriptName.endswith(".sh"):
        # Get bash header
        with open(ProjectBasePaths["templates"]+"/scriptHeader.sh", 'r') as f:
            WholeScript = f.read()+"\n\n"

    # Get rest of script
    with open(ProjectBasePaths["templates"]+"/"+ScriptName, 'r') as f:
        WholeScript += f.read()
    # Perform variable substitutions
    for VariableName in VariableSubstitutions:
        WholeScript = WholeScript.replace("$$"+VariableName+"$$", VariableSubstitutions[VariableName])

    # Write script back
    with open(TargetFile, 'w') as f:
        f.write(WholeScript)
