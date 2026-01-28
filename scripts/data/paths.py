import os

from processes.filesystem import JoinPaths, GetTemporaryPath

# Assume scripts is on the base folder
def GetProjectBasePath():
    project_base_scripts_path = os.path.dirname(os.path.realpath(__file__))
    return project_base_scripts_path.replace("/scripts/data", "")

# Provide base paths that must exist, and can be used internally
def GetBasePaths():
    project_base_path = GetProjectBasePath()

    # Setup paths
    paths = {
        "project base": project_base_path,
    }
    # Where the ProjectBase scripts are
    paths["scripts"] = paths["project base"]+"/scripts"
    # Where the templates for build systems are
    paths["templates"] = paths["scripts"]+"/templates"
    # ProjectBase information (history, bare gits, cache, etc) is
    paths["configs"] = paths["project base"]+"/configs"

    ## Where histoy is stored
    paths["history"]   = paths["configs"]+"/history"
    ## What temporary folder to use for setting up projects
    paths["temporary"] = paths["configs"]+"/temporary"
    ## Where the .git files are located
    paths["bare gits"] = paths["configs"]+"/bare_gits"

    paths["caches"] = JoinPaths(paths["configs"], "project_cache", "repositories")

    return paths


def GetNewTemporaryPath():
    return GetTemporaryPath(GetBasePaths()["temporary"])

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
