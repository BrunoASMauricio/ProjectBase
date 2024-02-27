from repository import *
from settings import GetActiveSettings
from common import *
from git import *

"""
Performs operations on a project
Each project is built from a single repository
Is represented by a simple dictionary
"""
class PROJECT(dict):
    # Load constant and known variables
    def __init__(self, Url, Branch, Commit):

        Name = GetRepoNameFromURL(Url)

        self.Paths = GetProjectPaths(Name)

        self.update({
            "ProjectRepoName":    Name,
            "ProjectRepoUrl":     Url,
            "ProjectRepoBranch":  Branch,
            "ProjectRepoCommit":  Commit,
        })
        self.LoadedRepos = {}
        # Check and generate project structure if necessary
        for PathName in self.Paths:
            LaunchProcess('mkdir -p "'+self.Paths[PathName]+'"')

        LaunchProcess('''echo  "''' + self["ProjectRepoUrl"] + ''' " >  ''' + self.Paths["project_main"]+"/root_url.txt")

    # Load project data
    def Load(self):
        # Clean project cache
        del self.LoadedRepos
        self.LoadedRepos = {}

        # Recursive repository generation starting with main
        self.__LoadRepo(self["ProjectRepoUrl"], self["ProjectRepoBranch"], self["ProjectRepoCommit"])

    def __LoadRepo(self, Url, Branch, Commit, configs=None):
        NewRepoId = RepoIdentifier(Url, Branch, Commit, configs)

        # Already loaded, skip
        if NewRepoId in self.LoadedRepos.keys():
            return

        Repo = REPOSITORY(self, NewRepoId, Url, Branch, Commit)

        Repo.LoadRepo(configs)

        self.LoadedRepos[NewRepoId] = Repo

        for DependencyUrl in Repo["dependencies"]:
            Dependency = Repo["dependencies"][DependencyUrl]

            self.__LoadRepo(Dependency["url"], Dependency["branch"], Dependency["commit"], Dependency["configs"])

    # Setup project scripts
    def Setup(self):
        for RepoId in self.LoadedRepos:
            self.LoadedRepos[RepoId].Setup()

        self.__SetupCMakeLists()

    def Build(self):
        for RepoId in self.LoadedRepos:
            self.LoadedRepos[RepoId].BeforeBuild()

        ActiveSettings = GetActiveSettings()

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
    
    def SetCloneType(self, CloneType):
        logging.info("Changing project repositories to "+CloneType)
        AllRepos = GetGitPaths(self.Paths["project_main"])

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

    # Delete project binaries and cached build artifacts
    def Clean(self):
        LaunchVerboseProcess("rm -rf "+self.Paths["cmake"]+"/*")
        LaunchVerboseProcess("rm -rf "+self.Paths["executables"]+"/*")
        LaunchVerboseProcess("rm -rf "+self.Paths["tests"]+"/*")
        LaunchVerboseProcess("rm -rf "+self.Paths["libraries"]+"/*")

    def __SetupCMakeLists(self):
        # Install project wide CMakeLists
        PresentRepos = {}
        for RepoId in self.LoadedRepos:
            Repo = self.LoadedRepos[RepoId]
            if  Repo.HasFlag("no auto build"):
                continue

            if Repo.HasFlag("independent project"):
                # TODO Throw error if CMakeLists.txt does not exist in sub_dire
                IncludeEntry = 'add_subdirectory("'+Repo["full_local_path"]+'")'
            else:
                IncludeEntry = 'include("'+Repo["full_local_path"]+'/CMakeLists.txt")'

            # Do not include duplicates (due to multiple imported)
            if Repo["full_local_path"] in PresentRepos:
                # TODO
                # If the duplicate has a different import definition, throw error
                #if repo["full_local_path"] != IncludeEntry:
                #    logging.fatal("Same repository included with diferring \"independent project\" flag status")
                #    logging.fatal(repo["full_local_path"])
                #    logging.fatal(IncludeEntry)
                #    sys.exit(0)

                continue

            PresentRepos[Repo["full_local_path"]] = IncludeEntry

        SetupTemplateScript("project/CMakeLists.txt", self.Paths["project_main"]+"/CMakeLists.txt", {
            "INCLUDEREPOSITORYCMAKELISTS":'\n'.join(PresentRepos.values())
        })



