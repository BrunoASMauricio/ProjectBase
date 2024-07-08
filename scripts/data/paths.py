import os

def GetRepoNameFromURL(Url):
    if Url == None or len(Url) == 0:
        raise Exception("Requested URL ("+Url+") is empty")

    if Url[-1] == '/':
        Url = Url[:-1]
    return Url.split('/')[-1].strip()

# Assume scripts is on the base folder
def GetProjectBasePath():
    ProjectBaseScriptsPath = os.path.dirname(os.path.realpath(__file__))
    return ProjectBaseScriptsPath.replace("/scripts", "")

def GetBasePaths():
    ProjectBasePath = GetProjectBasePath()

    # Setup paths
    Paths = {
        "project_base": ProjectBasePath,
    }

    Paths["scripts"] = Paths["project_base"]+"/scripts"
    Paths["templates"] = Paths["project_base"]+"/templates"

    Paths["configs"] = Paths["project_base"]+"/configs"
    Paths["history"] = Paths["configs"]+"/history"

    # Where the .git files are located
    Paths[".gits"] =        Paths["project_base"]+"/bare_gits"
    Paths["temporary"] =    Paths["project_base"]+"/temporary"

    return Paths

def GetProjectPaths(ProjectName):
    """
    Builds and returns a dictionary with a projects' directory structure
    indexed by a string describing each paths' purpose
    """
    Paths = GetBasePaths()

    # Projects main directory
    Paths["project_main"] = Paths["project_base"]+"/projects/" + ProjectName + ".ProjectBase"

    # Projects cmake cache
    Paths["cmake"] =        Paths["project_main"]+"/cmake"

    # Project output binaries
    Paths["binaries"] =     Paths["project_main"]+"/binaries"

    # Project repository worktrees
    Paths["project_code"] = Paths["project_main"]+'/code'

    # Path for repositories that don't specify local_path
    Paths["general_repository"] = ''

    # Path for output binaries
    Paths["objects"]     = Paths["binaries"]+"/objects"
    Paths["executables"] = Paths["objects"]+"/executables"
    Paths["tests"]       = Paths["objects"]+"/tests"
    Paths["libraries"]   = Paths["binaries"]+"/libs"

    # Path for whatever data might be used/needed
    Paths["data"]        = Paths["project_main"]+"/data"

    return Paths