# from repository import *
# from settings import get_active_settings
# from common import *
# from git import *
from data.settings import settings
from data.paths import GetRepoNameFromURL, GetProjectPaths
from processes.process import LaunchProcess
from git import *

"""
Performs operations on a project
Each project is built from a single repository
Is represented by a simple dictionary
"""
class PROJECT(dict):
    # Load constant and known variables
    def init(self):

        self.name = GetRepoNameFromURL(settings["url"])

        self.paths = GetProjectPaths(self.name)

        self.LoadedRepos = {}

        # LaunchProcess('''echo  "''' + self["ProjectRepoUrl"] + ''' " >  ''' + self.Paths["project_main"]+"/root_url.txt")
        # Check and generate project structure if necessary
        for PathName in self.paths:
            LaunchProcess('mkdir -p "'+self.paths[PathName]+'"')

Project = PROJECT()

def SetCloneType(CloneType):
    AllRepos = GetGitPaths(project.paths["project_main"])

    for Repo in AllRepos:
        PrevUrl = Git.GetURL(Repo)

        if CloneType == "ssh":
            # Already in git
            if PrevUrl.startswith("git@"):
                continue
            Url = UrlToSSH(PrevUrl)
        else:
            # Already in https
            if PrevUrl.startswith("https"):
                continue
            Url = SSHToUrl(PrevUrl)

        CDLaunchReturn("git remote rm origin; git remote add origin " + Url, Repo, True)

        # for RepoId in self.LoadedRepos:
        #     self.LoadedRepos[RepoId].Setup()

def LoadAllRepos():
    pass

# Setup project scripts
def Generate():
    for RepoId in self.LoadedRepos:
        self.LoadedRepos[RepoId].Setup()

    self.__SetupCMakeLists()

def Build():
    for RepoId in self.LoadedRepos:
        self.LoadedRepos[RepoId].BeforeBuild()

    ActiveSettings = get_active_settings()

    CMakeCommand =  'cmake'
    # Dont complain about unused -D parameters, they are not mandatory
    CMakeCommand += ' --no-warn-unused-cli'
    CMakeCommand += ' -S '+self.Paths["project_main"]
    CMakeCommand += ' -B '+self.Paths["cmake"]
    CMakeCommand += ' -DBUILD_MODE='+ActiveSettings["Mode"]
    CMakeCommand += ' -DPROJECT_NAME='+self["ProjectRepoName"]
    CMakeCommand += ' -DPROJECT_BASE_SCRIPT_PATH='+self.Paths["scripts"]
    CMakeCommand += ' && cmake --build '+self.Paths["cmake"]

    LaunchVerboseProcess(CMakeCommand)

    for RepoId in self.LoadedRepos:
        self.LoadedRepos[RepoId].AfterBuild()

def CleanRunnables():
    LaunchVerboseProcess("rm -rf "+self.Paths["executables"]+"/*")
    LaunchVerboseProcess("rm -rf "+self.Paths["tests"]+"/*")

def CleanCompiled():
    LaunchVerboseProcess("rm -rf "+self.Paths["libraries"]+"/*")
    CleanRunnables()

def CleanAll():
    LaunchVerboseProcess("rm -rf "+self.Paths["cmake"]+"/*")
    CleanCompiled()