import os
import sys
import json
import difflib
import traceback
from time import sleep

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
        sys.exit(0)

        Result = FunctionToRun(**ListArguments)
        OperationStatus.append(Result)
        # Sleep to prevent what?
        sleep(0.05)

    os.chdir(CurrentDirectory)
    sys.exit(0)

    return OperationStatus

def SetupScript(SourceFile, TargetFile, variable_substitutions={}):
    WholeScript = ""

    # Get rest of script
    with open(SourceFile, 'r') as f:
        WholeScript += f.read()

    # Perform variable substitutions
    for variable_name in variable_substitutions:
        WholeScript = WholeScript.replace("$$"+variable_name+"$$", variable_substitutions[variable_name])

    # Write script back
    with open(TargetFile, 'w') as f:
        f.write(WholeScript)
