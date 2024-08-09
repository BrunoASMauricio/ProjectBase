from processes.process import LaunchProcess
from data.paths import GetParentPath

def Remove(target):
    LaunchProcess('rm -rf ' + target)

def create_directory(path):
    LaunchProcess('mkdir -p "' + path + '"')

def CreateParentDirectory(path_to_child):
    create_directory(GetParentPath(path_to_child))
