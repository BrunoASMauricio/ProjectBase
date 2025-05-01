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
from processes.filesystem import CreateDirectory, FindInodeByPattern
from processes.progress_bar import PrintProgressBar
from threading import Lock
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

    # Current full path to the repository
    current_location = None

    # We already have cached metadata on this repo
    if repo_id in repositories.keys() and repositories[repo_id] != None and repositories[repo_id]["reloaded"] == True:
        repository = repositories[repo_id]
        # Is the repository where we expect it to be?
        current_location  = FindGitRepo(repository["full worktree path"], imposed_configs["url"], imposed_configs["commitish"], depth=1)
        if current_location == None:
            logging.warning(f"Repo {imposed_configs["name"]} is not in the expected path of: {repository["full worktree path"]}")
            SetDetectedStateChange()
            # Delete previous data. Cant trust it
            del repositories[repo_id]
    else:
        SetDetectedStateChange()

    # Repo path unknown, or not where expected. Find repository
    if current_location == None:
        current_location = FindGitRepo(Settings["paths"]["project code"], imposed_configs["url"], imposed_configs["commitish"])

    # Repo nowhere to be found, add it
    if current_location == None:
        logging.info(f"Repository {imposed_configs} not found")
        # Setup helper worktree
        helper_path = AddWorkTree(imposed_configs["bare path"], imposed_configs["url"], imposed_configs["commitish"], Settings["paths"]["temporary"])
        repository  = MergeConfigs(imposed_configs, LoadConfigs(helper_path))

        expected_local_path = JoinPaths(Settings["paths"]["project code"], repository["local path"])

        # Move worktree to appropriate place
        CreateDirectory(expected_local_path)
        MoveWorkTree(repository["bare path"], helper_path, expected_local_path)
        # current_location = expected_local_path
        current_location = JoinPaths(expected_local_path, repository["name"])

        SetDetectedStateChange()

    else: # Repository present at current_location
        # logging.debug("Repo " + imposed_configs["name"] + " found at " + current_location)
        repository = MergeConfigs(imposed_configs, LoadConfigs(current_location))

        # Is that the expected path?
        expected_local_path = JoinPaths(Settings["paths"]["project code"], repository["local path"])
        repo_path = JoinPaths(expected_local_path, repository["name"])

        if current_location != repo_path:
            logging.warning(f"Repository not in expected place (at \"{current_location}\" instead of \"{repo_path}\"). Moving it")
            MoveWorkTree(repository["bare path"], current_location, expected_local_path)
            current_location = repo_path
            SetDetectedStateChange()
        current_location = repo_path

    # From this point on:
    # 1. Repository dict exists containing configs
    # 2. Repo is at current_location
    # 3. expected_local_path contains the parent of the repo
    # 4. Path is consistent with the path requested in configs
    repository["full worktree path"] = expected_local_path
    repository["repo path"]  = current_location
    repository["repo name"]  = GetRepositoryName(repository["repo path"])
    repository["build path"] = repository["repo path"].replace(Settings["paths"]["project code"], Settings["paths"]["build env"])
    UpdateState(repository["configs path"])

    return repository

def __RepoHasNoCode(repository):
    files = FindInodeByPattern(repository["repo path"], "CMakeLists.txt")
    return len(files) == 0

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
        if loaded_amount == 0:
            print(f"\n{len(repositories)} unloaded dependencies found")
        else:
            print(f"\n{unloaded} unloaded dependencies found")
        loaded_amount = 0

        # For each unloaded repository, load it
        repo_args = []
        for repo_id in repositories:
            if repositories[repo_id]["reloaded"] == False:
                repo_args.append((repositories[repo_id],))
            else:
                loaded_amount += 1

        # Load remaining repositories
        RunInThreadsWithProgress(LoadRepository, repo_args, None, __PrintLoadProgress)

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

def __GenerateFullMenu(repositories):
    root = {}
    for repo_id in repositories:
        repository = repositories[repo_id]
        kconfig_path = None

        if "kconfig" in repository:
            kconfig_path = repository["kconfig"]
            if not os.path.isfile(kconfig_path):
                logging.error(f"Invalid Kconfig file path {kconfig_path}")
                kconfig_path = None

        if kconfig_path == None:
            kconfig_path = JoinPaths(repository['current repo path'], "configs", "Kconfig")
            if not os.path.isfile(kconfig_path):
                continue

        # Use local_path to derive menu name
        parts = repository["local path"].split("/")
        menu = root
        logging.error(f"For repository {repository["name"]}")

        for part in parts:
            if part not in menu:
                menu[part] = {}

            menu = menu[part]
        menu[repository["name"]] = kconfig_path
    logging.error("root")
    logging.error(root)
    return root

# Receives the root menu and its' name
# Returns the collapsed root menu
# input = {'Core': {'Core': "path to Core kconfig"}, 'Runtime': {'Data': {'Memory': {'Val1': "path to Val1 kconfig"}, 'Map': "path to Map kconfig"}, 'Binary': "path to Binary kconfig"}}
# outputs: {'Core/Core': "path to Core kconfig", 'Runtime': {'Data': {'Memory/Val1': "path to Val1 kconfig", 'Map': "path to Map kconfig"}, 'Binary': "path to Binary kconfig"}}
def __CollapseSingleEntryMenus(root):
    result = {}
    def RecursivelyCollapse(key, value):
        if isinstance(value, str):
            return value

        # Collapse dictionary
        if len(value.keys()) == 1:
            return key + "/" + list(value.keys())[0]

        to_return = {}
        for subkey, subval in value.items():
            # Other leaves remain
            if isinstance(subval, str):
                to_return[subkey] = subval
                continue

            # Investigate sub dictionaries
            collapsed = RecursivelyCollapse(subkey, subval)
            if isinstance(collapsed, dict):
                to_return[subkey] = collapsed
            elif collapsed != None:
                # Child collapsed
                to_return[collapsed] = list(subval.values())[0]
        return to_return

    for key, value in root.items():
        to_root = RecursivelyCollapse(key, value)
        if isinstance(to_root, dict):
            # Child is dict, keep it as is
            result[key] = to_root
        else:
            # Child collapsed
            result[to_root] = list(value.values())[0]
    return result

def __GenerateKConfigs(config_dict, menu_path=""):
    for key, value in config_dict.items():
        current_path = JoinPaths(menu_path, key)
        file_path = JoinPaths(Settings["paths"]["project configs"], current_path)

        if isinstance(value, str):
            # Link Kconfig
            os.makedirs(file_path, exist_ok=True)
            LaunchProcess(f"ln -s {value} Kconfig", file_path)
        elif isinstance(value, dict):
            # Create Kconfig submenu
            os.makedirs(file_path, exist_ok=True)
            # Generate a menu with nested includes
            with open(file_path + "/Kconfig", "w") as f:
                f.write(f'menu "{key}"\n\n')
                for subkey in value:
                    subpath = JoinPaths(current_path, subkey).replace("/", os.sep)
                    if isinstance(value[subkey], dict):
                        f.write(f'source "{subpath}/Kconfig"\n')
                    else:
                        f.write(f'source "{subpath}/Kconfig"\n')
                f.write(f'\nendmenu\n')
            # Recurse into submenus
            __GenerateKConfigs(value, current_path)

def __CreateRootKConfig(menus):
    root_kconfig_path = JoinPaths(Settings["paths"]["project configs"], "Kconfig")
    with open(root_kconfig_path, "w") as f:
        for src in menus:
            f.write(f'source "{Settings["paths"]["project configs"]}/{src}/Kconfig"\n')

def __SetupKConfig(repositories):
    menu_root = __GenerateFullMenu(repositories)
    collapsed_menus = __CollapseSingleEntryMenus(menu_root)
    __GenerateKConfigs(collapsed_menus, Settings["paths"]["project configs"])
    __CreateRootKConfig(collapsed_menus)
    logging.error(collapsed_menus)
    # __CollapseEmptyMenus()

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
            if not __RepoHasFlagSet(repository, "independent project") and not (__RepoHasFlagSet(repository, "no auto build") or __RepoHasNoCode(repository)):
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
            if __RepoHasFlagSet(repository, "no auto build") or __RepoHasNoCode(repository):
                continue

            if __RepoHasFlagSet(repository, "independent project"):
                # TODO Throw error if CMakeLists.txt does not exist in sub_dire
                IncludeEntry = f'add_subdirectory("{repository["repo path"]}" "{repository["build path"]}")'
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
    # Get KConfig ready
    __SetupKConfig(repositories)

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


