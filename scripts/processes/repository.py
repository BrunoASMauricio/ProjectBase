import sys
import logging
from data.git import GetRepoNameFromURL
from processes.git import *
from data.common import RemoveSequentialDuplicates, SetupTemplateScript, IsEmpty
from data.settings import Settings
from data.json import dump_json_file, load_json_file
from processes.repository_configs import LoadConfigs, MergeConfigs, ParseConfigs
from data.common import GetValueOrDefault
from processes.filesystem import create_directory
from processes.progress_bar import printProgressBar
from threading import Thread, Lock

repositories_lock = Lock()
dependencies = {}
repositories = None
StateChangedDetected = False

def save_repos_to_cache(_repositories, path):
    global repositories
    repositories = _repositories
    dump_json_file(_repositories, path)

def load_repos_from_cache(path):
    global repositories
    repositories = load_json_file(path, {})
    return repositories

def set_detected_state_change():
    global StateChangedDetected
    StateChangedDetected = True

def reset_detected_state_change():
    global StateChangedDetected
    StateChangedDetected = False

def detected_state_changed():
    global StateChangedDetected
    return StateChangedDetected

def GetRepoId(repo_configs):
    url = url_SSH_to_HTTPS(repo_configs["url"])
    return url.lower()
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
            set_detected_state_change()
            # Delete previous data. Cant trust it
            del repositories[repo_id]
    else:
        set_detected_state_change()

    # Repo path unknown, or not where expected. Find repository
    if current_local_path == None:
        current_local_path = FindGitRepo(Settings["paths"]["project code"], imposed_configs["url"], imposed_configs["commitish"])

    # Repo nowhere to be found, add it
    if current_local_path == None:
        # Setup helper worktree
        helper_path = AddWorkTree(imposed_configs["bare path"], imposed_configs["url"], imposed_configs["commitish"], Settings["paths"]["temporary"])
        repository  = MergeConfigs(imposed_configs, LoadConfigs(helper_path))

        expected_local_path = Settings["paths"]["project code"] + "/" + repository["local path"]
        expected_local_path = RemoveSequentialDuplicates(expected_local_path, "/")

        # Move worktree to appropriate place
        create_directory(expected_local_path)
        MoveWorkTree(repository["bare path"], repository["url"], repository["commitish"], helper_path, expected_local_path)
        current_local_path = expected_local_path
        set_detected_state_change()

    else: # Repository present at current_local_path
        # logging.debug("Repo " + imposed_configs["name"] + " found at " + current_local_path)
        repository = MergeConfigs(imposed_configs, LoadConfigs(current_local_path))

        # Is that the expected path?
        expected_local_path = Settings["paths"]["project code"] + "/" + repository["local path"] + "/" + repository["name"]
        expected_local_path = RemoveSequentialDuplicates(expected_local_path, "/")

        if current_local_path != expected_local_path:
            logging.warning("Repository not in expected place (at \"" + current_local_path + "\" instead of \"" + expected_local_path + "\"). Moving it")
            MoveWorkTree(repository["bare path"], repository["url"], repository["commitish"], current_local_path, expected_local_path)
            current_local_path = expected_local_path
            set_detected_state_change()

    # repository dict exists containing configs, repo is at current_local_path and congruent with the path requested in configs
    repository["full worktree path"] = current_local_path
    repository["repo path"] = current_local_path + "/" + repository["name"]

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
            logging.info(block_name)
            command_block     = commands[block_name]
            proceed_condition = command_block["condition to proceed"]
            command_list      = command_block["command list"]
            result = ParseProcessResponse(LaunchVerboseProcess(proceed_condition))
            if result != "":
                logging.info(proceed_condition + " is False, skipping " + str(len(command_list)) + " commands")
                return

            logging.info(proceed_condition + " is True, running " + str(len(command_list)) + " commands")
            # TODO: after console merge, run these one at a time and explicitly check return value?
            LaunchVerboseProcess("set -xe && "+' && '.join(command_list))

def LoadRepositories(root_configs, cache_path):
    global repositories
    global dependencies

    root_repo_id = GetRepoId(root_configs)
    reset_detected_state_change()
    repositories = load_repos_from_cache(cache_path)

    if len(repositories) == 0:
        repositories[root_repo_id] = root_configs
        repositories[root_repo_id]["reloaded"] = False
    else:
        for repo_id in repositories:
            repositories[repo_id]["reloaded"] = False

    unloaded = True
    loaded_amount = 0
    while unloaded == True:
        printProgressBar(loaded_amount, len(repositories), prefix = 'Loading Repositories:', suffix = "Loading " + str(len(repositories)) + " repositories", length = len(repositories))
        loaded_amount = 0
        dependencies.clear()
        threads = []

        # For each unloaded repository, load it
        for repo_id in repositories:
            if repositories[repo_id]["reloaded"] == False:
                print("Loading "+repo_id)
                if Settings["single_thread"]:
                    LoadRepository(repositories[repo_id])
                else:
                    thread = Thread(target=LoadRepository, args=(repositories[repo_id],))
                    threads.append(thread)
                    thread.start()
            else:
                loaded_amount += 1

        # Wait for all threads
        if Settings["single_thread"] == False:
            for thread in threads:
                thread.join()

        # Merge dependencies with existing repositories
        unloaded = False
        for dependency in dependencies:
            dep_configs = dependencies[dependency]
            repo_id = GetRepoId(dep_configs)
            if repo_id not in repositories:
                repositories[repo_id] = dep_configs
                repositories[repo_id]["reloaded"] = False
                set_detected_state_change()
                unloaded = True
    printProgressBar(len(repositories), len(repositories), prefix = 'Loading Repositories:', suffix = 'Loaded ('+str(len(repositories))+') repositories', length = len(repositories))

    if detected_state_changed():
        logging.debug("SAVING "+str(len(repositories))+" repositories in cache")
        save_repos_to_cache(repositories, cache_path)
    return repositories


def LoadRepository(imposed_configs):
    global repositories
    global repositories_lock

    imposed_configs["name"] = GetRepoNameFromURL(imposed_configs["url"])
    repo_id = GetRepoId(imposed_configs)

    imposed_configs["bare path"] = SetupBareData(imposed_configs["url"])

    imposed_configs = __LoadRepositoryFolder(imposed_configs)
    imposed_configs["reloaded"] = True
    repositories[repo_id] = imposed_configs

    config_variable_data = {
        "PROJECT_PATH":  Settings["paths"]["project main"],
        "REPO_PATH":     imposed_configs["full worktree path"],
        "REPOPATH":     imposed_configs["full worktree path"]
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
        dependencies[dep_repo_id] = dependency_configs
        repositories_lock.release()

def __SetupCMake(repositories):
    PublicHeaderFolders = []
    ObjectsToLink       = []
    ReposToBuild        = []
    for repo_id in repositories:
        try:
            repository = repositories[repo_id]
            # Fetch all public headers
            if len(repository["public headers"]) > 0:
                PublicHeaderFolders += [repository["full worktree path"] + "/" + x for x in repository["public headers"]]

            # Fetch all objects to link
            if not __RepoHasFlagSet(repository, "independent project") and not __RepoHasFlagSet(repository, "no auto build"):
                ObjectsToLink.append(repository["name"]+'_lib')
        except Exception as ex:
            traceback.print_exc()
            print(repositories[repo_id])

    for repo_id in repositories:
        try:
            repository = repositories[repo_id]
            if __RepoHasFlagSet(repository, "no auto build"):
                continue

            if __RepoHasFlagSet(repository, "independent project"):
                # TODO Throw error if CMakeLists.txt does not exist in sub_dire
                IncludeEntry = 'add_subdirectory("' + repository["full worktree path"] + '")'
            else:
                IncludeEntry = 'include("' + repository["full worktree path"] + '/CMakeLists.txt")'
            ReposToBuild.append(IncludeEntry)

            RepoCmakeLists = repository["full worktree path"] + "/CMakeLists.txt"
            PrivateHeaderFolders = []
            if len(repository["private headers"]) > 0:
                PrivateHeaderFolders += [repository["full worktree path"] + "/" + x for x in repository["public headers"]]

            # Check if there is already a CMakeLists and it isn't ours
            if os.path.isfile(RepoCmakeLists):
                CanDelete = False
                with open(RepoCmakeLists) as f:
                    Content = f.readlines()

                if len(Content) > 0 and "# PROJECTBASE" in Content[0]:
                    CanDelete = True

                if CanDelete:
                    os.unlink(RepoCmakeLists)

            TempObjectsToLink = [x for x in ObjectsToLink if x != repository["name"]+'_lib']
            TestHeaders = [repository["full worktree path"] + "/" + Header for Header in repository["test_headers"]]
            if len(TestHeaders) > 0:
                print("TestHeaders")
                print(TestHeaders)
            if not os.path.isfile(RepoCmakeLists):
                SetupTemplateScript("repository/CMakeLists.txt", RepoCmakeLists, {
                    "ADDLIBRARYTYPE": "",
                    "TARGETINCLUDETYPE": "PUBLIC",
                    "INCLUDEREPOSITORYDIRECTORIES": '\n'.join(PublicHeaderFolders),
                    "LINKDEPENDENCIES": '\n'.join(TempObjectsToLink),
                    "TEST_HEADER_INCLUDES": '\n'.join(TestHeaders)
                })
        except Exception as ex:
            traceback.print_exc()
            sys.exit(0)

    SetupTemplateScript("project/CMakeLists.txt", Settings["paths"]["project main"]+"/CMakeLists.txt", {
        "INCLUDEREPOSITORYCMAKELISTS":'\n'.join(ReposToBuild)
    })


def Setup(repositories):
    # Get CMakeLists ready
    __SetupCMake(repositories)

    # Run setup scripts
    for repo_id in repositories:
        repository = repositories[repo_id]
        __RunRepoCommands("setup", repository["setup"])

def Build(repositories, build_command):
    for repo_id in repositories:
        repository = repositories[repo_id]
        __RunRepoCommands("before build", repository["before build"])

    LaunchVerboseProcess(build_command)

    for repo_id in repositories:
        repository = repositories[repo_id]
        __RunRepoCommands("after build", repository["after build"])

