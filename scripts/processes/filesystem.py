import glob
import os

from processes.process import LaunchProcess
from data.paths import GetParentPath

def remove(target):
    LaunchProcess('rm -rf ' + target)

def CreateDirectory(path):
    LaunchProcess('mkdir -p "' + path + '"')

def create_parent_directory(path_to_child):
    CreateDirectory(GetParentPath(path_to_child))

def FindInodeByPattern(directory, pattern):
    return glob.glob(os.path.join(directory, pattern))