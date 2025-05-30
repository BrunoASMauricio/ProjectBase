import os
import logging

from data.settings import Settings, CLONE_TYPE
from data.paths    import GetProjectPaths, JoinPaths
from data.git      import GetRepoNameFromURL, url_HTTPS_to_SSH, url_SSH_to_HTTPS
from data.common   import LoadFromFile, DumpToFile

from processes.repository_configs     import ConfigsChanged, ResetConfigsState

from processes.repository     import LoadRepositories, Setup, Build
from processes.process        import LaunchProcess, LaunchVerboseProcess
from data.colors              import ColorFormat, Colors
from processes.git_operations import GetRepositoryUrl
from processes.filesystem     import CreateDirectory
from processes.run_linter     import CleanLinterFiles

"""
Performs operations on a project
Each project is built from a single repository
Is represented by a simple dictionary
"""
class PROJECT(dict):
    # Load constant and known variables
    def ResetRepositories(self):
        self.repositories = {}

    def init(self):
        self.ResetRepositories()

        self.name = GetRepoNameFromURL(Settings["url"])
        self.paths = GetProjectPaths(self.name)

        # Check and generate project structure if necessary
        for path_name in self.paths:
            path = self.paths[path_name]
            # There are relative empty paths that symbolize "here"
            if path != "":
                LaunchProcess('mkdir -p "'+self.paths[path_name]+'"')

        DumpToFile(JoinPaths(self.paths["project main"], "root_url.txt"), Settings["url"])

        Settings["ProjectName"] = self.name
        Settings["paths"]       = self.paths
        self.repo_cache_path = JoinPaths(Settings["paths"]["configs"], "project_cache", "repositories")
        Settings["paths"]["cache path"] = JoinPaths(self.repo_cache_path, self.name)
        CreateDirectory(self.repo_cache_path)

    def load(self):
        # Reset configs state
        ResetConfigsState()

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

        self.repositories = LoadRepositories(self.root_repo_base_config, Settings["paths"]["cache path"])
        print("Project loaded")

    def setup(self):
        logging.info("Setting up project")
        print("Setting up project")

        Setup(self.GetRepositories())
        logging.info("Finished setting up project")
        print("Finished setting up project")

    def build(self):
        logging.info("Building project")

        CMakeCommand =  'cmake -DCMAKE_BUILD_TYPE=Debug'
        # Dont complain about unused -D parameters, they are not mandatory
        CMakeCommand += ' --no-warn-unused-cli'
        # Add compile.json for better IDE support
        CMakeCommand += ' -DCMAKE_EXPORT_COMPILE_COMMANDS=1'
        # Include generated configuration
        # CMakeCommand += f' -I{self.paths["project configs"]}/.config'
        CMakeCommand += f' -S {self.paths["build env"]}'
        CMakeCommand += f' -B {self.paths["build cache"]}'
        # CMakeCommand += ' -DBUILD_MODE='+ActiveSettings["Mode"]
        CMakeCommand += f' -DPROJECT_NAME={self.name}'
        CMakeCommand += f' -DPROJECT_BASE_SCRIPT_PATH={self.paths["scripts"]}'
        CMakeCommand += f' && cmake --build {self.paths["build cache"]}'
        # Enable multi process
        CMakeCommand += ' -- -j $(nproc)'

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

            LaunchProcess("git remote rm origin; git remote add origin " + url, repository["full worktree path"])

    def GetRepositories(self):
        # Not loaded, load and return
        if len(self.repositories) == 0:
            self.load()
            return self.repositories

        # Single change in configs must trigger full reloading of configs
        for repository in self.repositories:
            config_change = ConfigsChanged(self.repositories[repository]["configs path"])
            if config_change != None:
                print(f"Config change detected ({self.repositories[repository]["configs path"]}: {config_change}), reloading")
                self.load()
                break

        return self.repositories

Project = PROJECT()

def GetRelevantPath(path):
    return path.replace(Project.paths["project code"], "")

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
            import sys
            print(f"{__file__}")
            sys.exit(0)
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

def CleanPBCache():
    global Project
    LaunchVerboseProcess(f"rm -rf {Settings["paths"]["cache path"]}")
    LaunchVerboseProcess(f"rm -rf {Settings["paths"]["temporary"]}/*")
    Project.ResetRepositories()
