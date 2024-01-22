from git import *
from common import *
import logging
from time import time
import os

def repo_identifier(url, branch, commit, configs):
    return str(url) + " " + str(branch) + " " + str(commit)+" "+str(configs)
    # Use hash of configs??

"""
Performs operations on a single repository
Is represented by a simple dictionary
"""
class Repository(dict):
    def reset(self, project, url, branch, commit):
        key_list = list(self.keys())

        for key in key_list:
            del self[key]

        self.project = project
        self.paths = self.project.paths

        self["url"] = url
        self["name"] = getRepoNameFromURL(url)
        self["bare_tree_path"] = getRepoBareTreePath(url)
        self["branch"] = branch
        self["commit"] = commit

        # Where this repos source can be found
        self["source"] = None
        
        # Where a .git can be found for this repo
        self["bare_path"] = None


    def __init__(self, project, url, branch=None, commit=None):
        self.reset(project, url, branch, commit)

    """
    Checks if a given name and value pair exist in the configuration of this repository
    If value is None, just checks if it exists
    """
    def checkConfig(self, name, value = None):
        if value == None:
            return name in self.keys()
        return ((name in self.keys()) and (self[name] == value))

    """
    Load and parse a repositories configurations
    """
    def loadRepo(self, dependent_configs=None):
        logging.info("Loading repository "+self["name"])

        # Set/Get bare data
        Git.setupBareData(self.paths[".gits"], self)

        # Check if repo is present in project structure
        source_path = Git.findGitRepo(self.paths["project_code"], self["url"], self["commit"])

        if source_path == None:
            # No source exists, create temporary worktree to extract configs
            temp_repo_clone, temp_project_clone = createTemporaryRepository(self, dependent_configs)

            # Relocate repository according to configs in temporary source
            self["source"] = temp_repo_clone["source"]
            self.loadConfigs(dependent_configs)

            print(self, end="\n\n")

            os.makedirs(self["full_local_path"], exist_ok=True)

            Git.addWorktree(self, self["full_local_path"])

            deleteTemporaryRepository(temp_repo_clone, temp_project_clone)

            source_path = self["full_local_path"]

        # Reload metadata (only keep source)
        self.reset(self.project, self["url"], self["branch"], self["commit"])
        self["source"] = source_path

        self.loadConfigs(dependent_configs)

        self.__parseConfigs(self)

    # Load .json and set default variables
    def loadConfigs(self, dependent_configs=None):
        # Try and load known configuration files appropriately
        if os.path.isdir(self["source"]+"/configs"):
            confs = loadJsonFile(self["source"]+"/configs/configs.json", {})
            if len(confs) != 0:
                self.update(confs)
            print(confs)

            confs = loadJsonFile(self["source"]+"/configs/build_configs.json", {})
            if len(confs) != 0:
                self.update(confs)

            # No official release and already have backward compatibility issues :')
            legacy_dependencie_config = loadJsonFile(self["source"]+"/configs/dependencies.json", {})
            if len(legacy_dependencie_config) != 0:
                self.update({"dependencies":legacy_dependencie_config})

        # Use dependent configs if available
        if dependent_configs != None and len(dependent_configs) != 0:
            logging.warning(self["name"]+" repository could not load configurations but has dependent configs. Using these")
            self.update(dependent_configs)

        # Check for the defaults
        if not self.checkConfig("headers"):
            self["headers"] = "code/headers"

        if not self.checkConfig("test_headers"):
            self["test_headers"] = "executables,executables/tests,tests"

        if not self.checkConfig("local_path") or self["local_path"] == "":
            self["local_path"] = self.paths["general_repository"]

        if not self.checkConfig("flags") or self["flags"] == "":
            self["flags"] = ""

        self["full_local_path"] = self.paths["project_code"]+"/"+self["local_path"]+"/"+self["name"]
        self["full_local_path"] = self["full_local_path"].replace(" ","\ ")

        if not self.checkConfig("dependencies") or self["dependencies"] == "":
            self["dependencies"] = {}

        # Set dependency data appropriately
        for dependency in self["dependencies"]:
            if type(self["dependencies"][dependency]) != type({}):
                logging.warning("Dependency "+dependency+" of "+self["name"]+" has wrong type: "+str(type(self["dependencies"][dependency]))+". Assuming its legacy and setting to empty commit and branch.")
                self["dependencies"][dependency] = dict()

            self["dependencies"][dependency]["url"] = dependency

            if "commit" not in self["dependencies"][dependency]:
                self["dependencies"][dependency]["commit"] = None

            if "branch" not in self["dependencies"][dependency]:
                self["dependencies"][dependency]["branch"] = None

            if "configs" not in self["dependencies"][dependency]:
                self["dependencies"][dependency]["configs"] = None

    """
    Replace all config variables appropriately
    """
    def __parseConfigs(self, configs):
        logging.debug("\nparse configs for "+str(configs)+"\n")

        if type(configs) == type([]):
            for i in range(len(configs)):
                config = configs[i]
                if type(config) == type(""):
                    config = self.__parseVariables(config)
                    configs[i] = config

                elif type(config) == type([]):
                    self.__parseConfigs(config)

                elif type(config) == type({}):
                    self.__parseConfigs(config)

                elif config == None:
                    pass
                else:
                    logging.warning("unkown type "+str(type(config))+" for config "+str(config))

        elif type(configs) == type({}) or type(configs) == Repository:
            for i in configs:
                if i == "dependencies": # Dependency configs are taken care by them
                    continue

                config = configs[i]
                if type(config) == type(""):
                    config = self.__parseVariables(config)
                    configs[i] = config

                elif type(config) == type([]):
                    self.__parseConfigs(config)

                elif type(config) == type({}):
                    self.__parseConfigs(config)

                elif config == None:
                    pass
                else:
                    logging.warning("unkown type "+str(type(config))+" for config "+str(config))

    # Replace known variables (surrounded with '$$') by the known values
    def __parseVariables(self, data):
        logging.debug("parsing variable "+str(data))
        project_variables = {
            "PROJECTPATH":  self.paths["project_main"]
        }

        for variable_name, variable_value in project_variables.items():
            data = data.replace("$$"+variable_name+"$$", variable_value)

        if self != None:
            repository_variables = {
                "REPOPATH":     self["full_local_path"],
                "DATAPATH":     self.paths["data"]
            }
            for variable_name, variable_value in repository_variables.items():
                data = data.replace("$$"+variable_name+"$$", variable_value)

        return data

    def setup(self,):
        print("Setting up repository: "+self["url"])

        self.__setupCommandList()
        self.__setupCMakeLists()
        if self.hasFlag("no commit") and os.path.isdir(self["full_local_path"]+"/.git"):
            os.removedirs(self["full_local_path"]+"/.git")

    def hasFlag(self, flag):
        if flag in self["flags"]:
            return True
        return False

    def __runCommandList(self, command_list):
        for command_set_name in command_list:
            command_set = command_list[command_set_name]
            print("Command check: "+str(command_set["condition to proceed"]))

            if parseProcessResponse(launchVerboseProcess(command_set["condition to proceed"])) == "":
                print("Running commands "+str(command_set["command list"]))
                launchVerboseProcess("set -xe && "+' && '.join(command_set["command list"]))

    def __setupCommandList(self):
        if self.checkConfig("setup"):
            self.__runCommandList(self["setup"])

    def before_build(self):
        if self.checkConfig("before_build"):
            self.__runCommandList(self["before_build"])

    def after_build(self):
        if self.checkConfig("after_build"):
            self.__runCommandList(self["after_build"])

    def __setupCMakeLists(self):
        if self.hasFlag("no auto build"):
           return

        directory_includes = [self["full_local_path"]+'/'+self["headers"]]

        link_libraries = []

        for repo_id in self.project.loaded_repos:
            url = repo_id.split(" ")[0]
            # Do not self-import
            if url == self["url"]:
                continue

            repository = self.project.loaded_repos[repo_id]
            include_entry = '\t'+repository["full_local_path"].replace(" ","\ ")+"/"+repository["headers"]

            # Do not import twice
            if include_entry in directory_includes:
                continue

            if repository["headers"] != "":
                directory_includes.append(include_entry)


            if not repository.hasFlag("independent project") and not repository.hasFlag("no auto build"):
                link_libraries.append(repository["name"]+'_lib')

        if self["test_headers"] != "":
            test_headers = self["test_headers"].split(",")
            test_headers = [self["full_local_path"]+"/"+header for header in test_headers]
        else:
            test_headers = ""


        # Only add repo-wide CMakeLists.txt if one isn't already present
        # The function readlines() reads the file.
        can_delete = False
        repo_cmakelists = self["full_local_path"]+"/CMakeLists.txt"
        if os.path.isfile(repo_cmakelists):
            with open(repo_cmakelists) as f:
                content = f.readlines()

            if len(content) > 0 and "# PROJECTBASE" in content[0]:
                can_delete = True

            if can_delete:
                os.unlink(repo_cmakelists)

        if not os.path.isfile(repo_cmakelists):
            setupScript("repository/CMakeLists.txt", repo_cmakelists, {
                    "ADDLIBRARYTYPE": "",
                    "TARGETINCLUDETYPE": "PUBLIC",
                    "INCLUDEREPOSITORYDIRECTORIES": '\n'.join(directory_includes),
                    "LINKDEPENDENCIES": '\n'.join(link_libraries),
                    "TEST_HEADER_INCLUDES": '\n'.join(test_headers)
                })

class FakeProject(dict):
    def __init__(self, url, branch, commit):

        name = getRepoNameFromURL(url)

        self.paths = get_paths(name)
        self.paths["project_code"] = self.paths["temporary"] + "/" + name + ".ProjectBase"

        self.update({
            "project_repo_name":    name,
            "project_repo_url":     url,
            "project_repo_branch":  branch,
            "project_repo_commit":  commit,
        })
        self.loaded_repos = {}

def createTemporaryRepository(repo, dependent_configs):
    # Setup temp project
    url = repo["url"]
    branch= repo["branch"]
    commit = repo["commit"]

    temp_project = FakeProject(url, branch, commit)
    temp_repo = Repository(temp_project, url, branch, commit)
    temp_repo.paths["project_code"]
    #temp_repo.copy(repo)
    temp_repo["bare_path"] = repo["bare_path"]

    Git.addWorktree(temp_repo, repo.paths["temporary"]+"/"+repo["name"]+"_"+str(time()))

    # Load metadata
    temp_repo.loadConfigs(dependent_configs)
    return temp_repo, temp_project

import shutil

def deleteTemporaryRepository(temp_repo, temp_project):
    global a
    # Relocate repository according to metadata
    Git.delWorktree(temp_repo)
    try:
        shutil.rmtree(temp_project.paths["project_code"])
    except:
        pass

    del temp_project
    del temp_repo
