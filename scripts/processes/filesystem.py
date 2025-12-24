import os
import glob
import random
import string
import pathlib
import shutil

def Remove(target):
    os.remove(target)

def RemoveDirectory(path):
    shutil.rmtree(path)

def CreateDirectory(path):
    pathlib.Path(path).mkdir(parents=True, exist_ok=True)

def CreateParentDirectory(path_to_child):
    CreateDirectory(GetParentPath(path_to_child))

def GetCurrentFolderName(path_to_child):
    return path_to_child.split("/")[-2]

def GetParentFolderName(path_to_child):
    return path_to_child.split("/")[-2]

def GetParentPath(path_to_child):
    return '/'.join(path_to_child.split("/")[:-1])

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

def JoinPaths(*paths):
    final_path = []
    for path in paths:
        final_path.append(path)

    final_path = '/'.join(final_path)

    while "//" in final_path:
        final_path = final_path.replace("//", "/")
    return final_path

def NewRandomName():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=12))


def GetNewTemporaryPath(paths):
    while True:
        random_name = NewRandomName()
        path = JoinPaths(paths["temporary"], random_name)
        if not os.path.exists(path):
            return path

# Create all directories in the `paths` list provided
def CreateDirs(paths):
    for path in paths:
        CreateDirectory(path)
