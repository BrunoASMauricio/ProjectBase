import os
import random
import string
from pathlib import Path

def GetCurrentFolderName(path_to_child):
    return path_to_child.split("/")[-2]

def GetParentFolderName(path_to_child):
    return path_to_child.split("/")[-2]

def GetParentPath(path_to_child):
    return '/'.join(path_to_child.split("/")[:-1])

def CreateParentPath(path_to_child):
    parent_path = GetParentPath(path_to_child)
    Path(parent_path).mkdir(parents=True, exist_ok=True)

# Assume scripts is on the base folder
def GetProjectBasePath():
    project_base_scripts_path = os.path.dirname(os.path.realpath(__file__))
    return project_base_scripts_path.replace("/scripts/data", "")

def GetBasePaths():
    project_base_path = GetProjectBasePath()

    # Setup paths
    paths = {
        "project base": project_base_path,
    }

    paths["scripts"] = paths["project base"]+"/scripts"
    paths["templates"] = paths["scripts"]+"/templates"

    paths["configs"] = paths["project base"]+"/configs"

    paths["history"]   = paths["configs"]+"/history"
    paths["temporary"] = paths["configs"]+"/temporary"
    # Where the .git files are located
    paths["bare gits"] = paths["configs"]+"/bare_gits"

    return paths

def GetProjectPaths(project_name):
    """
    Builds and returns a dictionary with a projects' directory structure
    indexed by a string describing each paths' purpose
    """
    paths = GetBasePaths()

    # Projects main directory
    paths["project main"] = paths["project base"]+"/projects/" + project_name + ".ProjectBase"

    # Projects configs directory
    paths["project configs"]   = paths["project main"] + "/configs"
    paths["autogened headers"] = paths["project configs"] + "/autogened_headers"

    # Projects build directory
    paths["build"]       = paths["project main"] + "/build"
    # Cache for the build artifacts
    paths["build cache"] = paths["build"] + "/cache"
    paths["build env"]   = paths["build"] + "/cmake"

    # Project output binaries
    paths["binaries"]    = paths["project main"] + "/binaries"
    paths["libraries"]   = paths["binaries"]     + "/libs"
    paths["objects"]     = paths["binaries"]     + "/objects"
    paths["executables"] = paths["objects"]      + "/executables"
    paths["tests"]       = paths["objects"]      + "/tests"

    # Project repository worktrees
    paths["project code"] = paths["project main"]+'/code'
    # 
    paths["default local path"] = ""

    # Path for repositories that don't specify local_path
    paths["general repository"] = ""

    # Path for whatever data might be used/needed
    paths["data"]        = paths["project main"]+"/data"

    return paths

def JoinPaths(*paths):
    final_path = []
    for path in paths:
        final_path.append(path)

    final_path = '/'.join(final_path)

    while "//" in final_path:
        final_path = final_path.replace("//", "/")
    return final_path

def GetNewTemporaryPath(paths):
    while True:
        random_name = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
        path = JoinPaths(paths["temporary"], random_name)
        if not os.path.exists(path):
            return path
