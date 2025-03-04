import os
import glob

from processes.process import LaunchProcess
from data.paths import GetParentPath

def Remove(target):
    LaunchProcess(f'rm -rf {target}')

def CreateDirectory(path):
    LaunchProcess(f'mkdir -p "{path}"')

def CcreateParentDirectory(path_to_child):
    CreateDirectory(GetParentPath(path_to_child))

def FindInodeByPattern(directory, pattern):
    if directory[-1] != "/":
        directory = f"{directory}/"
    directory = f"{directory}**"
    return glob.glob(os.path.join(directory, f"*/{pattern}"), recursive=True, include_hidden=True)