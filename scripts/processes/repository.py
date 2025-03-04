import sys
import logging
from time import sleep
from data.git import GetRepoNameFromURL
from processes.git import *
from data.common import SetupTemplateScript
from data.settings import Settings
from data.json import dump_json_file, load_json_file
from processes.repository_configs import LoadConfigs, MergeConfigs, ParseConfigs, UpdateState
from data.common import GetValueOrDefault
from processes.filesystem import CreateDirectory
from processes.progress_bar import PrintProgressBar
from threading import Thread, Lock
from data.paths import JoinPaths

repositories_lock = Lock()
dependencies = {}
repositories = None
StateChangedDetected = False

def SaveReposToCache(_repositories, path):
    global repositories
    repositories = _repositories
    dump_json_file(_repositories, path)

def LoadReposFromCache(path):
    global repositories
    repositories = load_json_file(path, {})
    return repositories

def SetDetectedStateChange():
    global StateChangedDetected
    StateChangedDetected = True

def ResetDetectedStateChange():
    global StateChangedDetected
    StateChangedDetected = False

def DetectedStateChanged():
    global StateChangedDetected
    return StateChangedDetected

def GetRepoId(repo_configs):
    url = url_SSH_to_HTTPS(repo_configs["url"])
    return url
    # return str(repo_configs["url"]) + " " + str(repo_configs["branch"]) + " " + str(repo_configs["commit"])

"""
Based on the imposed_configs, make sure the repository is checked out
at the expected path
"""
def __LoadRepositoryFolder(imposed_configs):
    global repositories
    global repositories_lock
    repo_id = GetRepoId(imposed_configs)
    # imposed_configs["repo_id"] = repo_id
    current_local_path = None

    # We already have cached metadata on this repo
    if repo_id in repositories.keys() and repositories[repo_id] != None and repositories[repo_id]["reloaded"] == True:
        repository = repositories[repo_id]
        # Is the repository where we expect it to be?
        current_local_path  = FindGitRepo(repository["full worktree path"], imposed_configs["url"], imposed_configs["commitish"], depth=1)
        if current_local_path == None:
            logging.warning("Repo " + imposed_configs["name"] + " is not in the expected path of: " + repository["full worktree path"])
            SetDetectedStateChange()
            # Delete previous data. Cant trust it
            del repositories[repo_id]
    else:
        SetDetectedStateChange()

    # Repo path unknown, or not where expected. Find repository
    if current_local_path == None:
        current_local_path = FindGitRepo(Settings["paths"]["project code"], imposed_configs["url"], imposed_configs["commitish"])

    # Repo nowhere to be found, add it
    if current_local_path == None:
        # Setup helper worktree
        helper_path = AddWorkTree(imposed_configs["bare path"], imposed_configs["url"], imposed_configs["commitish"], Settings["paths"]["temporary"])
        repository  = MergeConfigs(imposed_configs, LoadConfigs(helper_path))

        expected_local_path = JoinPaths(Settings["paths"]["project code"], repository["local path"])

        # Move worktree to appropriate place
        CreateDirectory(expected_local_path)
        MoveWorkTree(repository["bare path"], helper_path, expected_local_path)
        current_local_path = expected_local_path
        SetDetectedStateChange()

    else: # Repository present at current_local_path
        # logging.debug("Repo " + imposed_configs["name"] + " found at " + current_local_path)
        repository = MergeConfigs(imposed_configs, LoadConfigs(current_local_path))

        # Is that the expected path?
        expected_local_path = JoinPaths(Settings["paths"]["project code"], repository["local path"])
        repo_path = JoinPaths(expected_local_path, repository["name"])

        if current_local_path != repo_path:
            logging.warning("Repository not in expected place (at \"" + current_local_path + "\" instead of \"" + repo_path + "\"). Moving it")
            MoveWorkTree(repository["bare path"], current_local_path, expected_local_path)
            current_local_path = repo_path
            SetDetectedStateChange()
        current_local_path = expected_local_path

    # repository dict exists containing configs, repo is at current_local_path and congruent with the path requested in configs
    repository["full worktree path"] = current_local_path
    repository["repo path"]  = JoinPaths(current_local_path, repository["name"])
    repository["repo name"]  = GetRepositoryName(repository["repo path"])
    repository["build path"] = repository["repo path"].replace(Settings["paths"]["project code"], Settings["paths"]["build env"])
    UpdateState(repository["configs path"])

    return repository

def __RepoHasFlagSet(repository, flag):
    return flag in repository["flags"]


"""
Expected commands format:
{
    "command block name": {
        "condition to proceed": "false",
        "command list": [
            "command 1",
            "command 2",
            "command 3"
        ]
    }
}
"""
def __RunRepoCommands(command_set_name, commands):
    if len(commands) > 0:
        logging.info("Running " + command_set_name + " commands")
        for block_name in commands:
            logging.info("\t Command block:" + block_name)
            command_block     = commands[block_name]
            proceed_condition = command_block["condition to proceed"]
            command_list      = command_block["command list"]
            result = ParseProcessResponse(LaunchProcess(proceed_condition))
            if result != "":
                logging.info("\t Condition to proceed: '" + proceed_condition + "' is False, skipping " + str(len(command_list)) + " commands")
                return

            logging.info("\t Condition to proceed: '" + proceed_condition + "' is True, running " + str(len(command_list)) + " commands")
            # TODO: after console merge, run these one at a time and explicitly check return value?
            LaunchVerboseProcess("set -xe && "+' && '.join(command_list))

def __CurrentlyLoadedRepoAmount():
    global repositories
    return len([x for x in repositories if repositories[x]["reloaded"] == True])

def __PrintLoadProgress():
    current_progress = __CurrentlyLoadedRepoAmount()
    total_repos      = len(repositories) + len(dependencies)
    if current_progress != total_repos:
        PrintProgressBar(current_progress, total_repos, prefix = 'Loading Repositories:', suffix = "Loading " + str(current_progress) + "/" + str(total_repos) + " Repositories")

def LoadRepositories(root_configs, cache_path):
    global repositories
    global dependencies

    root_repo_id = GetRepoId(root_configs)
    ResetDetectedStateChange()
    repositories = LoadReposFromCache(cache_path)

    if len(repositories) == 0:
        repositories[root_repo_id] = root_configs
        repositories[root_repo_id]["reloaded"] = False
    else:
        for repo_id in repositories:
            repositories[repo_id]["reloaded"] = False

    unloaded = 1
    loaded_amount = 0
    dependencies.clear()
    while unloaded > 0:
        loaded_amount = 0

        print(f"\n{unloaded} unloaded dependencies found")
        # For each unloaded repository, load it
        repo_args = []
        for repo_id in repositories:
            if repositories[repo_id]["reloaded"] == False:
                repo_args.append((repositories[repo_id],))
            else:
                loaded_amount += 1

        # Load remaining repositories
        RunInThreadsWithProgress(LoadRepository, repo_args, __PrintLoadProgress)

        # Merge dependencies with existing repositories
        unloaded = 0
        for dependency in dependencies:
            dep_configs = dependencies[dependency]
            repo_id = GetRepoId(dep_configs)
            if repo_id not in repositories:
                repositories[repo_id] = dep_configs
                repositories[repo_id]["reloaded"] = False
                SetDetectedStateChange()
                unloaded += 1
        dependencies.clear()
        PrintProgressBar(len(repositories), len(repositories), prefix = 'Loading Repositories:', suffix = "Loaded " + str(len(repositories)) + "/" + str(len(repositories)) + " Repositories")
        print("\nFinished dependency round")

    if DetectedStateChanged():
        logging.debug("SAVING "+str(len(repositories))+" repositories in cache")
        SaveReposToCache(repositories, cache_path)
    return repositories


def LoadRepository(imposed_configs):
    global repositories
    global dependencies
    global repositories_lock

    imposed_configs["name"] = GetRepoNameFromURL(imposed_configs["url"])
    repo_id = GetRepoId(imposed_configs)

    imposed_configs["bare path"] = SetupBareData(imposed_configs["url"])

    imposed_configs = __LoadRepositoryFolder(imposed_configs)
    imposed_configs["reloaded"] = True
    repositories[repo_id] = imposed_configs

    config_variable_data = {
        "PROJECT_PATH": Settings["paths"]["project main"],
        "REPO_PATH":    imposed_configs["repo path"],
        "REPOPATH":     imposed_configs["repo path"]
    }

    # Reload metadata
    imposed_configs = ParseConfigs(imposed_configs, config_variable_data)

    repositories[repo_id]["reloaded"] = True
    # Load dependencies
    for dependency in imposed_configs["dependencies"]:
        base_dependency = imposed_configs["dependencies"][dependency]
        if "configs" in base_dependency:
            dependency_configs = base_dependency["configs"].copy()
        else:
            dependency_configs = {}

        dependency_configs["url"] = GetValueOrDefault(base_dependency, "url", dependency)
        dependency_configs["reloaded"] = False
        if "commit" in base_dependency and base_dependency["commit"] != None:
            dependency_configs["commitish"] = {}
            dependency_configs["commitish"]["type"] = "commit"
            dependency_configs["commitish"]["commit"] = base_dependency["commit"]
        elif "branch" in base_dependency and base_dependency["branch"] != None:
            dependency_configs["commitish"] = {}
            dependency_configs["commitish"]["type"] = "branch"
            dependency_configs["commitish"]["branch"] = base_dependency["branch"]
        else:
            dependency_configs["commitish"] = None

        dep_repo_id = GetRepoId(dependency_configs)
        repositories_lock.acquire()
        # if dep_repo_id in dependencies??
        if dep_repo_id not in repositories and dep_repo_id not in dependencies:
            dependencies[dep_repo_id] = dependency_configs
        repositories_lock.release()

def __SetupCMake(repositories):
    public_header_folders = []
    ObjectsToLink       = []
    ReposToBuild        = []
    for repo_id in repositories:
        try:
            repository = repositories[repo_id]
            # Fetch all public headers
            if len(repository["public headers"]) > 0:
                # build_dir = __RepoPathToBuild(repository)
                public_header_folders += [JoinPaths(repository["repo path"], x) for x in repository["public headers"]]

            # Fetch all objects to link
            if not __RepoHasFlagSet(repository, "independent project") and not __RepoHasFlagSet(repository, "no auto build"):
                ObjectsToLink.append(repository["name"]+'_lib')
        except Exception as ex:
            traceback.print_exc()
            print(str(ex))
            print(repositories[repo_id])
    # print([repositories[x]["full worktree path"] for x in repositories])
    # sys.exit(0)
    for repo_id in repositories:
        try:
            repository = repositories[repo_id]
            if __RepoHasFlagSet(repository, "no auto build"):
                continue

            if __RepoHasFlagSet(repository, "independent project"):
                # TODO Throw error if CMakeLists.txt does not exist in sub_dire
                IncludeEntry = 'add_subdirectory("' + repository["build path"] + '")'
            else:
                IncludeEntry = 'include("' + JoinPaths(repository["build path"], "CMakeLists.txt") + '")'
            ReposToBuild.append(IncludeEntry)

            repo_cmake_lists = JoinPaths(repository["build path"], "CMakeLists.txt")

            public_headers  = public_header_folders.copy()
            if len(repository["public headers"]) > 0:
                public_headers += [JoinPaths(repository["repo path"], x) for x in repository["public headers"]]

            private_headers = []
            if len(repository["private headers"]) > 0:
                private_headers += [JoinPaths(repository["repo path"], x) for x in repository["private headers"]]

            test_headers = []
            if len(repository["test headers"]) > 0:
                test_headers += [JoinPaths(repository["repo path"], x) for x in repository["test headers"]]

            # Check if there is already a CMakeLists and it isn't ours
            if os.path.isfile(repo_cmake_lists):
                can_delete = False
                with open(repo_cmake_lists) as f:
                    content = f.readlines()

                if len(content) > 0 and "# PROJECTBASE" in content[0]:
                    can_delete = True

                if can_delete:
                    os.unlink(repo_cmake_lists)

            temp_objects_to_link = [x for x in ObjectsToLink if x != repository["name"]+'_lib']
            if not os.path.isfile(repo_cmake_lists):
                SetupTemplateScript("repository/CMakeLists.txt", repo_cmake_lists, {
                    "ADD_LIBRARY_TYPE": "",
                    "TARGET_INCLUDE_TYPE": "PUBLIC",
                    "PUBLIC_INCLUDES":  '\n'.join(public_headers),
                    "PRIVATE_INCLUDES": '\n'.join(private_headers),
                    "TESTS_INCLUDES":   '\n'.join(test_headers),
                    "LINK_DEPENDENCIES": '\n'.join(temp_objects_to_link),
                    "REPO_SOURCES": repository["repo path"],
                    "REPO_NAME": repository["repo name"]
                })
        except Exception as ex:
            traceback.print_exc()
            print(str(ex))
            sys.exit(0)

    SetupTemplateScript("project/CMakeLists.txt", JoinPaths(Settings["paths"]["build env"], "CMakeLists.txt"), {
        "INCLUDE_REPOSITORY_CMAKELISTS":'\n'.join(ReposToBuild),
        "PROJECT_PATH": Settings["paths"]["project main"]
    })


def Setup(repositories):
    # Get CMakeLists ready
    __SetupCMake(repositories)

    # Run setup scripts
    for repo_id in repositories:
        repository = repositories[repo_id]
        logging.info(f"Setting up repo {repository['name']}")
        __RunRepoCommands("setup", repository["setup"])

def Build(repositories, build_command):
    for repo_id in repositories:
        repository = repositories[repo_id]
        __RunRepoCommands("before build", repository["before build"])

    logging.info(f"Building project with {build_command}")
    LaunchVerboseProcess(build_command)

    for repo_id in repositories:
        repository = repositories[repo_id]
        __RunRepoCommands("after build", repository["after build"])


