# from repository import *
# from settings import get_active_settings
# from common import *
# from git import *
from data.settings        import Settings
from data.paths           import GetProjectPaths
from data.git             import GetRepoNameFromURL
from processes.repository import LoadRepositories, Setup, Build
from processes.process    import LaunchProcess
from data.git                  import *
from git                  import *
# from git                  import *
from processes.git_operations import GetRepositoryUrl
from processes.filesystem import create_directory
from processes.run_linter import CleanLinterFiles
from data.settings import Settings, CLONE_TYPE

"""
Performs operations on a project
Each project is built from a single repository
Is represented by a simple dictionary
"""
class PROJECT(dict):
    # Load constant and known variables
    def init(self):

        self.name = GetRepoNameFromURL(Settings["url"])
        self.repositories = {}

        self.paths = GetProjectPaths(self.name)

        # LaunchProcess('''echo  "''' + self["ProjectRepoUrl"] + ''' " >  ''' + self.Paths["project main"]+"/root_url.txt")
        # Check and generate project structure if necessary
        for PathName in self.paths:
            LaunchProcess('mkdir -p "'+self.paths[PathName]+'"')

        Settings["ProjectName"] = self.name
        Settings["paths"]       = self.paths
        self.cache_path = Settings["paths"]["configs"] + "/project_cache/repositories/" + self.name
        create_directory(Settings["paths"]["configs"] + "/project_cache/repositories/")

    def load(self):
        # Build root repo configs from CLI
        self.root_repo_base_config = {"url": Settings["url"]}

        if "commit" in Settings and Settings["commit"] != None:
            self.root_repo_base_config["commitish"] = {}
            self.root_repo_base_config["commitish"]["type"] = "commit"
            self.root_repo_base_config["commitish"]["commit"] = Settings["commit"]
        elif "branch" in Settings and Settings["branch"] != None:
            self.root_repo_base_config["commitish"] = {}
            self.root_repo_base_config["commitish"]["type"] = "branch"
            self.root_repo_base_config["commitish"]["branch"] = Settings["branch"]
        else:
            self.root_repo_base_config["commitish"] = None

        self.repositories = LoadRepositories(self.root_repo_base_config, self.cache_path)

    def setup(self):
        Setup(self.GetRepositories())
    
    def build(self):
        CMakeCommand =  'cmake'
        # Dont complain about unused -D parameters, they are not mandatory
        CMakeCommand += ' --no-warn-unused-cli'
        CMakeCommand += ' -S ' + self.paths["project main"]
        CMakeCommand += ' -B ' + self.paths["cmake"]
        # CMakeCommand += ' -DBUILD_MODE='+ActiveSettings["Mode"]
        CMakeCommand += ' -DPROJECT_NAME=' + self.name
        CMakeCommand += ' -DPROJECT_BASE_SCRIPT_PATH=' + self.paths["scripts"]
        CMakeCommand += ' && cmake --build ' + self.paths["cmake"] + ' -- -j $(nproc)'

        Build(self.GetRepositories(), CMakeCommand)
    
    def SetCloneType(self, clone_type):
        repos = self.GetRepositories()
        for url_id in repos:
            repository = repos[url_id]
            prev_url = GetRepositoryUrl(repository["full worktree path"])
            if clone_type == CLONE_TYPE.SSH.value:
                url = url_HTTPS_to_SSH(prev_url)
            else:
                url = url_SSH_to_HTTPS(prev_url)

            CDLaunchReturn("git remote rm origin; git remote add origin " + url, repository["full worktree path"])

    def GetRepositories(self):
        # Not loaded, load before returning
        if len(self.repositories) == 0:
            self.load()
        return self.repositories

Project = PROJECT()

def UserChooseProject():
    """
    Print currently available projects and ask user
    to choose one of them
    """

    Index = 0
    ProjectsAvailable = []
    print("Installed projects:")
    for Entry in os.scandir("projects"):
        if Entry.name == "" or Entry.name == ".gitignore":
            continue

        """
        Repositories can have the same name (different URLs)
        As such, we cannot rely on the name of the project to
        """

        if not Entry.is_dir():
            print("Unexpected file in projects "+Entry.path+"/"+Entry.name)
            continue

        Url = ""
        FolderPath = Entry.path
        # Yo Alvaro, qual era a razao para este file?
        # FilePath = os.path.join(FolderPath, "root_url.txt")
        # if os.path.isfile(FilePath):
        #     with open(FilePath, "r") as file:
        #         Url = file.read()[:-1].strip()
        # else:
        #     print(ColorFormat(Colors.Red, "Cannot open project "+Entry.name+", root_url.txt not found"))
        #     continue
        Url = GetRepositoryUrl(FolderPath)
        if Url == "":
            continue

        Name = GetRepoNameFromURL(Url)
        print("\t["+str(Index)+"] "+ColorFormat(Colors.Blue, Name)+" : "+Url)
        ProjectsAvailable.append(Url)
        Index += 1
    if Index == 0:
        UserInput = input("Remote project repository URL: ")
    else:
        UserInput = input("Insert a number to choose from the existing projects, or a URL to download a new one: ")

    while True:
        try:
            InsertedIndex = int(UserInput)
            # User chose an Index
            RemoteRepoUrl = ProjectsAvailable[InsertedIndex]
            break
        except Exception as Ex:
            # Not an Index, assume URL
            RemoteRepoUrl = UserInput

    return RemoteRepoUrl

def CleanRunnables():
    LaunchVerboseProcess("rm -rf " + Settings["paths"]["executables"]+"/*")
    LaunchVerboseProcess("rm -rf " + Settings["paths"]["tests"]+"/*")

def CleanCompiled():
    LaunchVerboseProcess("rm -rf " + Settings["paths"]["libraries"]+"/*")
    CleanRunnables()

def CleanAll():
    LaunchVerboseProcess("rm -rf " + Settings["paths"]["cmake"]+"/*")
    CleanCompiled()
    CleanLinterFiles()