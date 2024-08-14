import os
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
    ProjectBaseScriptsPath = os.path.dirname(os.path.realpath(__file__))
    return ProjectBaseScriptsPath.replace("/scripts/data", "")

def GetBasePaths():
    ProjectBasePath = GetProjectBasePath()

    # Setup paths
    Paths = {
        "project base": ProjectBasePath,
    }

    Paths["scripts"] = Paths["project base"]+"/scripts"
    Paths["templates"] = Paths["scripts"]+"/templates"

    Paths["configs"] = Paths["project base"]+"/configs"

    Paths["history"]   = Paths["configs"]+"/history"
    Paths["temporary"] = Paths["configs"]+"/temporary"
    # Where the .git files are located
    Paths["bare gits"] = Paths["configs"]+"/bare_gits"

    return Paths

def GetProjectPaths(ProjectName):
    """
    Builds and returns a dictionary with a projects' directory structure
    indexed by a string describing each paths' purpose
    """
    Paths = GetBasePaths()

    # Projects main directory
    Paths["project main"] = Paths["project base"]+"/projects/" + ProjectName + ".ProjectBase"

    # Projects build directory
    Paths["build"]       = Paths["project main"] + "/build"
    # Cache for the build artifacts
    Paths["build cache"] = Paths["build"] + "/cache"
    Paths["build env"]   = Paths["build"] + "/cmake"

    # Project output binaries
    Paths["binaries"] =     Paths["project main"]+"/binaries"

    # Project repository worktrees
    Paths["project code"] = Paths["project main"]+'/code'
    # 
    Paths["default local path"] = ""

    # Path for repositories that don't specify local_path
    Paths["general repository"] = ""

    # Path for output binaries
    Paths["objects"]     = Paths["binaries"]+"/objects"
    Paths["executables"] = Paths["objects"]+"/executables"
    Paths["tests"]       = Paths["objects"]+"/tests"
    Paths["libraries"]   = Paths["binaries"]+"/libs"

    # Path for whatever data might be used/needed
    Paths["data"]        = Paths["project main"]+"/data"

    return Paths

def JoinPaths(*paths):
    final_path = ""
    for path in paths:
        final_path = os.path.join(final_path, path)
    return final_path
