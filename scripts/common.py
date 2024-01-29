import os
import sys
import json
import difflib
import traceback
from time import sleep
from colorama import Fore, Style

def GetTextDiff(Text1, Text2):
    diff = difflib.ndiff(Text1.split("\n"), Text2.split("\n"))
    return ''.join(diff)

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

def GetProjetBasePath():
    ProjectBaseScriptsPath = os.path.dirname(os.path.realpath(__file__))
    return ProjectBaseScriptsPath.replace("/scripts", "")

def GetProjectBasePaths():
    ProjectBasePath = GetProjetBasePath()

    # Setup paths
    Paths = {
        "project_base": ProjectBasePath,
    }

    Paths["scripts"] = Paths["project_base"]+"/scripts"
    Paths["templates"] = Paths["project_base"]+"/templates"

    Paths["configs"] = Paths["project_base"]+"/configs"
    Paths["project settings"] = Paths["configs"]+"/settings"
    Paths["history"] = Paths["configs"]+"/history"

    # Where the .git files are located
    Paths[".gits"] =        Paths["project_base"]+"/bare_gits"
    Paths["temporary"] =    Paths["project_base"]+"/temporary"

    return Paths

def GetProjectPaths(ProjectName):
    """
    Builds and returns a dictionary with a projects' directory structure
    indexed by a string describing each paths' purpose
    """
    Paths = GetProjectBasePaths()

    # Projects main directory
    Paths["project_main"] = Paths["project_base"]+"/projects/" + ProjectName + ".ProjectBase"

    # Projects cmake cache
    Paths["cmake"] =        Paths["project_main"]+"/cmake"

    # Project output binaries
    Paths["binaries"] =     Paths["project_main"]+"/binaries"

    # Project repository worktrees
    Paths["project_code"] = Paths["project_main"]+'/code'

    # Path for repositories that don't specify local_path
    Paths["general_repository"] = ''

    # Path for output binaries
    Paths["objects"]     = Paths["binaries"]+"/objects"
    Paths["executables"] = Paths["objects"]+"/executables"
    Paths["tests"]       = Paths["objects"]+"/tests"
    Paths["libraries"]   = Paths["binaries"]+"/libs"

    # Path for whatever data might be used/needed
    Paths["data"]        = Paths["project_main"]+"/data"

    return Paths

def Abort(Message):
    print(ColorFormat(Colors.Red, Message))
    sys.stdout.flush()
    sys.exit(-1)

def Assert(Message, Condition):
    if not Condition:
        Abort(Message)

def RemoveDuplicates(Str, SubStr):
    List = Str.split(SubStr)
    List = [ListEl for ListEl in List if len(ListEl) != 0]

    NewStr = SubStr.join(List)

    # Special cases for string starting/ending with SubStr (will lead to empty
    # element on either side
    if Str[0] == SubStr:
        NewStr = SubStr + NewStr

    if Str[-1] == SubStr:
        NewStr = NewStr + SubStr

    return NewStr

def GetRepositoryPaths(LoadedRepos):
    AllRepositories = []
    for RepoId in LoadedRepos:
        Repo = LoadedRepos[RepoId]
        if not Repo.HasFlag("no commit"):
            AllRepositories.append(Repo['full_local_path'])
    return AllRepositories

"""
Remove 'None' elements from a list
"""
def RemoveNone(List):
    return [ListEl for ListEl in List if ListEl != None]

def IsEmptyOrNone(Container):
    return (Container == None or len(Container) == 0)

"""
For each path, change directory to it, execute the provided function with the
provided arguments, concatenate result into list and return said list
"""
def RunOnFolders(Paths, FunctionToRun, ListArguments={}):
    OperationStatus = []
    CurrentDirectory = os.getcwd()

    for Path in Paths:
        if not os.path.isdir(Path):
            raise Exception(Path+" is not a valid directory, cannot perform "+str(FunctionToRun))

        os.chdir(Path)

        Result = FunctionToRun(**ListArguments)
        OperationStatus.append(Result)
        # Sleep to prevent what?
        sleep(0.05)

    os.chdir(CurrentDirectory)

    return OperationStatus

def SetupScript(SourceFile, TargetFile, VariableSubstitutions={}):
    WholeScript = ""

    # Get rest of script
    with open(SourceFile, 'r') as f:
        WholeScript += f.read()

    # Perform variable substitutions
    for VariableName in VariableSubstitutions:
        WholeScript = WholeScript.replace("$$"+VariableName+"$$", VariableSubstitutions[VariableName])

    # Write script back
    with open(TargetFile, 'w') as f:
        f.write(WholeScript)

# Sets up a script according to its template and the target variable substitutions
def SetupTemplateScript(ScriptName, TargetFile, VariableSubstitutions={}):
    WholeScript = ""
    ProjectBasePaths = GetProjectBasePaths()

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

def LoadJsonFile(Path, ErrorValue=None, VariableSubstitutions={}):
    """
    Returns the json from the given file, or ErrorValue in cas of an error
    Parameters
    ----------
    file : string
        The target file path
    ErrorValue : Object
        The object returned in case there is an error loading the json file
        If Object is None, the exception is thrown
    """
    try:
        with open(Path, 'r') as File:
            JsonData = json.load(File)

        for VariableName in VariableSubstitutions:
            JsonData = JsonData.replace("$$"+VariableName+"$$", VariableSubstitutions[VariableName])

        return JsonData

    except Exception as Ex:
        if ErrorValue == None:
            raise Exception("Could not load json from file "+Path+" "+traceback.format_exc())
    return ErrorValue

def DumpJsonFile(JsonData, Path):
    with open(Path, 'w') as file:
        json.dump(JsonData, file)

from enum import Enum

class Colors(Enum):
    Red = 1
    Blue = 2
    Yellow = 3
    Green = 4
    Magenta = 5

ColorDict = {
    Colors.Red: Fore.RED,
    Colors.Blue: Fore.BLUE,
    Colors.Yellow: Fore.YELLOW,
    Colors.Green: Fore.GREEN,
    Colors.Magenta: Fore.MAGENTA
}

def ColorFormat(Color, Message):
    return ColorDict[Color] + Message + Style.RESET_ALL

def UserYesNoChoice(Message):
    try:
        print(Message)
        Answer = input("("+ColorFormat(Colors.Green,"Yy")+"/"+ColorFormat(Colors.Red,"Nn")+"): ")
        if Answer in ["y", "Y"]:
            Answer = True
        else:
            Answer = False

    except Exception as Ex:
        Answer = False

    return Answer
