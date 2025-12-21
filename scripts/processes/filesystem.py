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
    # WARNING: Can be VERY slow on deep folder structures
    return glob.glob(os.path.join(directory, f"*/{pattern}"), recursive=True, include_hidden=True)

def FindFiles(search_path, filename):
    result = []
    for root, dirs, files in os.walk(search_path):
        if filename in files:
            result.append(os.path.join(root, filename))
    return result
