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
    return glob.glob(os.path.join(directory, pattern))