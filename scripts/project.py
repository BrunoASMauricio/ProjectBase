from repository import *
from common import *
from git import *

"""
Performs operations on a project
Each project is built from a single repository
Is represented by a simple dictionary
"""
class Project(dict):
    # Load constant and known variables
    def __init__(self, url, branch, commit):

        name = getRepoNameFromURL(url)

        self.paths = get_paths(name)

        self.update({
            "project_repo_name":    name,
            "project_repo_url":     url,
            "project_repo_branch":  branch,
            "project_repo_commit":  commit,
        })
        self.loaded_repos = {}
        # Check and generate project structure if necessary
        for path_name in self.paths:
            launchProcess('mkdir -p "'+self.paths[path_name]+'"')

        launchProcess('''echo  "''' + self["project_repo_url"] + ''' " >  ''' + self.paths["project_main"]+"/root_url.txt")

    # Load project data
    def load(self):
        # Clean project cache
        del self.loaded_repos
        self.loaded_repos = {}

        # Recursive repository generation starting with main
        self.__load_repo(self["project_repo_url"], self["project_repo_branch"], self["project_repo_commit"])

    def __load_repo(self, url, branch, commit, configs=None):
        new_repo_id = repo_identifier(url, branch, commit, configs)

        # Already loaded, skip
        if new_repo_id in self.loaded_repos.keys():
            #print("Reloading repo from "+url) 
            #repo = self.loaded_repos[new_repo_id]
            return
        #else:
        print("Loading repo from "+url)
        repo = Repository(self, url, branch, commit)

        repo.loadRepo(configs)

        self.loaded_repos[new_repo_id] = repo
        
        for dependency_url in repo["dependencies"]:
            dependency = repo["dependencies"][dependency_url]

            self.__load_repo(dependency["url"], dependency["branch"], dependency["commit"], dependency["configs"])

    # Setup project scripts
    def setup(self):
        for repo_id in self.loaded_repos:
            self.loaded_repos[repo_id].setup()

        self.__setupCMakeLists()

    def build(self):
        for repo_id in self.loaded_repos:
            self.loaded_repos[repo_id].before_build()

        launchVerboseProcess('cmake --debug-output -DCMAKE_COLOR_MAKEFILE=ON -S '+self.paths["project_main"]+' -B '+self.paths["cmake"]+' && cmake --build '+self.paths["cmake"])


        for repo_id in self.loaded_repos:
            self.loaded_repos[repo_id].after_build()

    # Delete project binaries and cached build artifacts
    def clean(self):
        launchVerboseProcess("rm -rf "+self.paths["cmake"]+"/*")
        launchVerboseProcess("rm -rf "+self.paths["executables"]+"/*")
        launchVerboseProcess("rm -rf "+self.paths["tests"]+"/*")
        launchVerboseProcess("rm -rf "+self.paths["libraries"]+"/*")

    def __setupCMakeLists(self):
        # Install project wide CMakeLists
        present_repos = {}
        for repo_id in self.loaded_repos:
            repo = self.loaded_repos[repo_id]
            if  repo.hasFlag("no auto build"):
                continue

            if repo.hasFlag("independent project"):
                # TODO Throw error if CMakeLists.txt does not exist in sub_dire
                include_entry = 'add_subdirectory("'+repo["full_local_path"]+'")'
            else:
                include_entry = 'include("'+repo["full_local_path"]+'/CMakeLists.txt")'

            # Do not include duplicates (due to multiple imported)
            if repo["full_local_path"] in present_repos:
                # TODO
                # If the duplicate has a different import definition, throw error
                #if repo["full_local_path"] != include_entry:
                #    logging.fatal("Same repository included with diferring \"independent project\" flag status")
                #    logging.fatal(repo["full_local_path"])
                #    logging.fatal(include_entry)
                #    sys.exit(0)

                continue

            present_repos[repo["full_local_path"]] = include_entry

        setupScript("project/CMakeLists.txt", self.paths["project_main"]+"/CMakeLists.txt", {
            "INCLUDEREPOSITORYCMAKELISTS":'\n'.join(present_repos.values())
        })



