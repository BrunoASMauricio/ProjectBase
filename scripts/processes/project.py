import os
import logging
import pickle

from data.settings import Settings, CLONE_TYPE
from data.paths    import GetProjectPaths, JoinPaths
from data.git      import GetRepoNameFromURL, url_HTTPS_to_SSH, url_SSH_to_HTTPS
from data.common   import LoadFromFile, DumpToFile, PrintNotice

from processes.repository_configs     import ConfigsChanged, ResetConfigsState

from processes.repository     import LoadRepositories, Setup, Build, full_load
from processes.process        import LaunchProcess, LaunchVerboseProcess, LaunchSilentProcess
from data.colors              import ColorFormat, Colors
from processes.git_operations import GetRepositoryUrl
from processes.process        import GetEnvVarExports
from processes.run_linter     import CleanLinterFiles
from processes.filesystem     import CreateParentDirs
"""
Performs operations on a project
Each project is built from a single repository
Is represented by a simple dictionary
"""
class PROJECT(dict):
    # Load constant and known variables
    def DeleteRepositories(self):
        for repo in self.repositories:
            del repo
        del self.repositories
        self.ResetRepositories()

    def ResetRepositories(self):
        self.repositories = {}

    def init(self):
        self.ResetRepositories()

        Settings["ProjectName"] = GetRepoNameFromURL(Settings["url"])
        Settings["paths"]  = GetProjectPaths(Settings["ProjectName"])
        # Setup project specific paths
        ## Cache
        Settings["cache file"]  = JoinPaths(Settings["paths"]["caches"], Settings["ProjectName"])

        # Setup all folders
        CreateParentDirs(Settings["paths"].values())

        ## root url for automatic project detection
        DumpToFile(JoinPaths(Settings["paths"]["project main"], "root_url.txt"), Settings["url"])

        # Clean temporary at startup
        LaunchSilentProcess(f"rm -rf {Settings["paths"]["temporary"]}/*")

    def load(self):
        logging.info("Loading repositories")
        # Reset configs state
        ResetConfigsState()

        # Check and generate project structure if necessary
        for path_name in Settings["paths"]:
            path = Settings["paths"][path_name]
            # There are relative empty paths that symbolize "here"
            if path != "":
                LaunchProcess('mkdir -p "'+Settings["paths"][path_name]+'"')

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

        PrintNotice(f"Loading repositories with the following parameters: {self.root_repo_base_config}")
        self.repositories = LoadRepositories(self.root_repo_base_config, Settings["cache file"])
        print("Project loaded")

    def setup(self):
        logging.info("Setting up project")
        print("Setting up project")

        Setup(self.GetRepositories())
        logging.info("Finished setting up project")
        print("Finished setting up project")

    def build(self):
        logging.info("Building project")
        repositories = self.GetRepositories()

        CMakeCommand = f'{GetEnvVarExports()}; '
        CMakeCommand += 'cmake -DCMAKE_BUILD_TYPE=Debug'
        # Dont complain about unused -D parameters, they are not mandatory
        CMakeCommand += ' --no-warn-unused-cli'
        # Add compile.json for better IDE support
        CMakeCommand += ' -DCMAKE_EXPORT_COMPILE_COMMANDS=1'
        # Include generated configuration
        # CMakeCommand += f' -I{self.paths["project configs"]}/.config'
        CMakeCommand += f' -S {Settings["paths"]["build env"]}'
        CMakeCommand += f' -B {Settings["paths"]["build cache"]}'
        # CMakeCommand += ' -DBUILD_MODE='+ActiveSettings["Mode"]
        CMakeCommand += f' -DPROJECT_NAME={Settings["ProjectName"]}'
        CMakeCommand += f' -DPROJECT_BASE_SCRIPT_PATH={Settings["paths"]["scripts"]}'
        CMakeCommand += f' && cmake --build {Settings["paths"]["build cache"]}'
        # Enable multi process
        CMakeCommand += ' -- -j $(nproc) -k'

        Build(repositories, CMakeCommand)

    def SetCloneType(self, clone_type):
        repos = self.GetRepositories()
        for url_id in repos:
            repository = repos[url_id]
            prev_url = GetRepositoryUrl(repository["full worktree path"])
            if clone_type == CLONE_TYPE.SSH.value:
                url = url_HTTPS_to_SSH(prev_url)
            else:
                url = url_SSH_to_HTTPS(prev_url)

            LaunchProcess("git remote rm origin; git remote add origin " + url, repository["full worktree path"])

    def GetRepositories(self):
        global full_load
        # See if saved cache exist 
        base_path = "configs/project_cache/"
        load_file = base_path + Settings["ProjectName"] + "_load_project.pkl"
        if(Settings["active"]["Speed"] == "Fast"):
            if os.path.exists(load_file):
                with open(load_file, "rb") as f:
                    loaded = pickle.load(f)
                    self.__dict__.update(loaded.__dict__)
                    self.update(loaded)
                    logging.info("Loaded project from pickle.")
                    print("Loaded project from pickle.")
            
        # Not loaded, load and return
        if len(self.repositories) == 0 or full_load == False:
            self.load()
            return self.repositories

        if Settings["active"]["Speed"] == "Safe":
            # Single change in configs must trigger full reloading of configs
            # Also internally this code is slower than it shoud there are proably ways to
            # speed it up. TODO 
            for repository in self.repositories:
                config_change = ConfigsChanged(self.repositories[repository]["configs path"])
                if config_change != None:
                    print(f"Config change detected ({self.repositories[repository]["configs path"]}: {config_change}), reloading")
                    self.load()
                    break

        if(Settings["active"]["Speed"] == "Fast"):       
            with open(load_file, "wb") as f:
                pickle.dump(self, f)
                logging.info("Saved project to pickle.")
                print("Saved project to pickle.")

        return self.repositories

Project = PROJECT()

def GetRelevantPath(path):
    return path.replace(Settings["paths"]["project code"], "")

def UserChooseProject():
    """
    Print currently available projects and ask user
    to choose one of them
    """

    Index = 0
    projects_available = []
    print("Installed projects:")
    if(os.path.exists("projects")):
        for entry in  os.scandir("projects"):
            if entry.name == "" or entry.name == ".gitignore":
                continue

            """
            Repositories can have the same name (different URLs)
            As such, we cannot rely on the name of the project to
            """

            if not entry.is_dir():
                print("Unexpected file in projects "+entry.path+"/"+entry.name)
                continue

            url = LoadFromFile(JoinPaths(entry.path, "root_url.txt"), None)
            if url == None:
                logging.error("Invalid project at " + entry.path + ", cannot load root_url.txt")
                continue

            # Url = file.read()[:-1].strip()

            name = GetRepoNameFromURL(url)
            print("\t["+str(Index)+"] " + ColorFormat(Colors.Blue, name) + " : " + url)
            projects_available.append(url)
            Index += 1
    if Index == 0:
        UserInput = input("Remote project repository URL: ")
    else:
        UserInput = input("Insert a number to choose from the existing projects, or a URL to download a new one: ")

    while True:
        try:
            InsertedIndex = int(UserInput)
            # User chose an Index
            RemoteRepoUrl = projects_available[InsertedIndex]
            break
        except Exception as Ex:
            # Not an Index, assume URL
            RemoteRepoUrl = UserInput
            break

    return RemoteRepoUrl

def CleanRunnables():
    LaunchVerboseProcess(f"rm -rf {Settings["paths"]["executables"]}/*")
    LaunchVerboseProcess(f"rm -rf {Settings["paths"]["tests"]}/*")

def CleanCompiled():
    LaunchVerboseProcess(f"rm -rf {Settings["paths"]["libraries"]}/*")
    CleanRunnables()

def CleanAll():
    LaunchVerboseProcess(f"rm -rf {Settings["paths"]["build cache"]}/*")
    CleanCompiled()
    CleanLinterFiles()

def DeleteProject():
    LaunchVerboseProcess(f"rm -rf {Settings["paths"]["project main"]}")

def _CleanPBCache():
    global Project
    LaunchVerboseProcess(f"rm -rf {Settings["cache file"]}")
    LaunchVerboseProcess(f"rm -rf {Settings["paths"]["temporary"]}/*")
    Project.DeleteRepositories()
    Settings.reset_settings()

def CleanPBCache():
    global Project
    _CleanPBCache()

    Settings.start()
    Project.init()

def PurgePB():
    global Project
    _CleanPBCache()

    LaunchVerboseProcess(f"rm -rf {Settings["paths"]["project base"]}/projects/*")
    LaunchVerboseProcess(f"rm -rf {Settings["paths"]["bare gits"]}/*")

    Settings.start()
    Project.init()