import logging
from enum import Enum

from pprint import pformat
from data.git import GetRepoNameFromURL
from processes.git import *
from data.common import SetupTemplate
from data.settings import Settings
from data.json import dump_json_file, load_json_file
from processes.repository_configs import LoadConfigs, MergeConfigs, ParseConfigs, UpdateState
from data.common import GetValueOrDefault
from processes.filesystem import CreateDirectory, CreateParentDirectory, FindFiles
from processes.progress_bar import PrintProgressBar
from threading import Lock
from data.paths import JoinPaths

# Repository operation lock
repositories_lock = Lock()

# Dependencies to load on the next loop
next_dependencies = {}
# Total URLs loaded (used to prevent infinite dependency cycles)
loaded_urls = []
# The repos currently being loaded
repos_being_loaded = []
# Helper map between URLs and IDs
url_to_id = {}

repositories = None
# Root configs. Used to kickstart further loads without searching
root_data = None
# Whether a full load has happened or not (i.e. it was interrupted)
full_load = False
# Whether there was an incoherency between internal and external state
state_changed_detected = False

def GetFullLoad():
    return full_load

class RepoFlags(Enum):
    NO_COMMIT = 1
    INDEPENDENT_PROJ = 2
    NO_AUTO_BUILD = 3
    EXECS_ONLY = 4

def SaveReposToCache(_repositories, path):
    global repositories
    repositories = _repositories
    dump_json_file(_repositories, path)

def LoadReposFromCache(path):
    global repositories
    repositories = load_json_file(path, {})

def GetRepoIdFromPath(path):
    return GetFirstCommit(path)
    # if repo_location == None:
    #     return None
    # return

# def GetRepoId(repo_configs):
#     # url = url_SSH_to_HTTPS(repo_configs["url"])
#     # return url
#     print(repo_configs)
#     return GetFirstCommit(repo_configs["full worktree path"])
#     # return str(repo_configs["url"]) + " " + str(repo_configs["branch"]) + " " + str(repo_configs["commit"])

def GetRepoIdFromURL(repo_url):
    return GetFirstCommit(FindGitRepo(Settings["paths"]["bare gits"], repo_url))
    # url = url_SSH_to_HTTPS(repo_url)
    # return url

"""
Based on the imposed_configs, make sure the repository is checked out
at the expected path
"""
def __LoadRepositoryFolder(imposed_configs):
    global repositories
    global state_changed_detected

    repo_id = imposed_configs["repo ID"]

    # Current full path to the repository
    current_location = None

    # We already have cached metadata on this repo
    if repo_id in repositories.keys() and repositories[repo_id] != None and repositories[repo_id]["reloaded"] == True:
        repository = repositories[repo_id]
        # Is the repository where we expect it to be?
        current_location  = FindGitRepo(repository["full worktree path"], imposed_configs["url"], imposed_configs["commitish"], depth=1)
        if current_location == None:
            logging.warning(f"Repo {imposed_configs["name"]} is not in the expected path of: {repository["full worktree path"]}")
            state_changed_detected = True

            # Delete previous data. Cant trust it
            del repositories[repo_id]

    else:
        state_changed_detected = True

    # Try to see if repository is still on the cached localization
    if current_location == None:
        if "repo source" in imposed_configs:
            repo_path_cached = imposed_configs["repo source"]
            if repo_path_cached != "":
                cached_url = GetRepositoryUrl(repo_path_cached)
                if SameUrl(cached_url,imposed_configs["url"]):
                    current_location = repo_path_cached

    # Repo path unknown, or not where expected. Find repository
    if current_location == None:
        current_location = FindGitRepo(Settings["paths"]["project code"], imposed_configs["url"], imposed_configs["commitish"])

    # Repo nowhere to be found, add it
    if current_location == None:
        logging.info(f"Repository {imposed_configs} not found")
        # Setup helper worktree
        helper_path = AddWorkTree(imposed_configs["bare path"], imposed_configs["url"], imposed_configs["commitish"], Settings["paths"]["temporary"])
        repository  = MergeConfigs(LoadConfigs(helper_path), imposed_configs)

        expected_local_path = JoinPaths(Settings["paths"]["project code"], repository["local path"])

        # Move worktree to appropriate place
        CreateDirectory(expected_local_path)
        MoveWorkTree(repository["bare path"], helper_path, expected_local_path)
        # current_location = expected_local_path
        current_location = JoinPaths(expected_local_path, repository["name"])

        state_changed_detected = True

    else: # Repository present at current_location
        # logging.debug("Repo " + imposed_configs["name"] + " found at " + current_location)
        repository = MergeConfigs(LoadConfigs(current_location), imposed_configs)
        # Is that the expected path?
        expected_local_path = JoinPaths(Settings["paths"]["project code"], repository["local path"])
        repo_path = JoinPaths(expected_local_path, repository["name"])

        if current_location != repo_path:
            logging.warning(f"Repository not in expected place (at \"{current_location}\" instead of \"{repo_path}\"). Moving it")
            MoveWorkTree(repository["bare path"], current_location, expected_local_path)
            current_location = repo_path
            state_changed_detected = True
        current_location = repo_path

    # From this point on:
    # 1. Repository dict exists containing configs
    # 2. Repo is at current_location
    # 3. expected_local_path contains the parent of the repo
    # 4. Path is consistent with the path requested in configs
    repository["full worktree path"] = expected_local_path
    repository["repo source"]  = current_location
    repository["commitish"] = imposed_configs["commitish"]
    repository["url"] = imposed_configs["url"]
    repository["repo name"]  = GetRepositoryName(repository["repo source"])
    repository["build path"] = repository["repo source"].replace(Settings["paths"]["project code"], Settings["paths"]["build env"])
    repository["libraries"]   = JoinPaths(Settings["paths"]["libraries"],   repository["repo name"])
    repository["executables"] = JoinPaths(Settings["paths"]["executables"], repository["repo name"])
    repository["tests"]       = JoinPaths(Settings["paths"]["tests"],       repository["repo name"])

    UpdateState(repository["configs path"])

    return repository

def __RepoHasNoCode(repository):
    logging.debug(repository["repo source"])
    files = FindFiles(repository["repo source"], "CMakeLists.txt")
    return len(files) == 0

# Check if the repository has at least one of the flags presented
def __RepoHasSomeFlagSet(repository, flags):
    for flag in flags:
        if flag in repository["flags"]:
            return True
    return False

# Check if the repository has the flag presented
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
            try:
                LaunchProcess(proceed_condition)
                result = True
            except ProcessError as proc_error:
                if proc_error.returned["code"] == 1:
                    result = False
            if result == False:
                logging.info("\t Condition to proceed: '" + proceed_condition + "' is False, skipping " + str(len(command_list)) + " commands")
                return

            logging.info("\t Condition to proceed: '" + proceed_condition + "' is True, running " + str(len(command_list)) + " commands")
            # TODO: after console merge, run these one at a time and explicitly check return value?
            LaunchVerboseProcess("set -xe && "+' && '.join(command_list))

def __PrintLoadProgress():
    global new_repos
    global repos_being_loaded

    total_repos      = len(repos_being_loaded)
    current_progress = new_repos
    if current_progress != total_repos:
        PrintProgressBar(current_progress, total_repos, prefix = 'Loading Repositories:', suffix = "Loading " + str(current_progress) + "/" + str(total_repos) + " Repositories")

"""
Check if new dependency configs conflict with either already setup configs
 or with configs ready to be setup
Return true if there is a conflict and current operation must stop, false otherwise
Throws if there are incompatible conflicts
"""
def ConflictsPresent(dependency_configs):
    def __ConflictingConfigs(configA, configB):
        # Any key that exists on both besides "url", which isnt the same, is problematic
        keys = ['after build', 'bare path', 'before build', 'commitish', 'dependencies', 'flags', 'local path', 'name', 'private headers', 'public headers', 'repo name', 'setup', 'test headers', 'url']
        for key in keys:
            if key not in configA or key not in configB:
                continue

            if configA[key] != configB[key]:
                return True
        return False

    dep_url = dependency_configs["url"]
    msg = None
    conflict = False

    # Conditions that can lead to issues

    ## If it was already loaded
    if dep_url in loaded_urls:
        conflict = True
        configs = repositories[url_to_id[dep_url]]

        if __ConflictingConfigs(dependency_configs, configs) == True:
            msg = CLICenterString(f"Incompatible configs for url {dep_url} (1)", "X")
            msg = f"{msg}\nA: {pformat(dependency_configs)}\nB: {pformat(configs)}"

    ## It is setup to be loaded next
    if dep_url in next_dependencies.keys():
        conflict = True
        if __ConflictingConfigs(dependency_configs, next_dependencies[dep_url]) == True:
            msg = CLICenterString(f"Incompatible configs for url {dep_url} (2)", "X")
            msg = f"{msg}\nA: {pformat(dependency_configs)}\nB: {pformat(next_dependencies[dep_url])}"

    if msg != None:
        raise Exception(msg)

    return conflict

"""
Prepare dependency to be fully setup
"""
def __AddNewDependency(dependency_configs):
    global repositories_lock
    global next_dependencies

    with repositories_lock:
        if ConflictsPresent(dependency_configs) == True:
            return

        next_dependencies[dependency_configs["url"]] = dependency_configs

def _LoadRepository(imposed_configs):
    global repositories
    global loaded_urls
    global new_repos

    imposed_configs["name"]      = GetRepoNameFromURL(imposed_configs["url"])
    imposed_configs["bare path"] = GetBareGit(imposed_configs["url"])
    imposed_configs["repo ID"]   = GetRepoIdFromPath(imposed_configs["bare path"])

    with repositories_lock:
        # Check if repo ID has been loaded
        repo_id = imposed_configs["repo ID"]
        if repo_id in repositories.keys() and repositories[repo_id]["url"] in loaded_urls:
            PrintNotice(f"Repeated ID {repo_id} found for {imposed_configs["name"]}")
            return

    configs = __LoadRepositoryFolder(imposed_configs)

    # Parse configs with appropriate variable values
    configs = ParseConfigs(configs, GetRepositoryVariables(configs))

    # Register repository appropriately
    with repositories_lock:
        new_repos += 1
        loaded_urls.append(configs["url"])
        repositories[configs["repo ID"]] = configs
        url_to_id[configs["url"]] = configs["repo ID"]

    # Get dependencies ready to be loaded
    try:
        for dependency in configs["dependencies"]:
            base_dependency = configs["dependencies"][dependency]

            if "configs" in base_dependency:
                dependency_configs = base_dependency["configs"].copy()
            else:
                dependency_configs = {}

            dependency_configs["url"] = GetValueOrDefault(base_dependency, "url", dependency)
            if(Settings["isCI"]):
                if(dependency_configs["url"] in Settings["commitJson"]):
                    # This means that settings should use the path ont he file system that has commits not in the remote in CI build
                    dependency_configs["url"] = Settings["commitJson"][dependency_configs["url"]]

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

            __AddNewDependency(dependency_configs)
    except Exception as ex:
        logging.error(f"Failed to load {pformat(configs)}")
        raise ex

"""
repo ID can only be obtained after load
To avoid infinite loop, store all loaded URLs

Set root as current "dep

Load from the dependencies into the repositories

"""
def LoadRepositories(root_configs, cache_path):
    global repositories
    global root_data
    global full_load
    global loaded_urls
    global next_dependencies
    global new_repos
    global repos_being_loaded
    global state_changed_detected

    repos_being_loaded.clear()
    loaded_urls.clear()
    next_dependencies.clear()
    state_changed_detected = False
    full_load = False

    # Load repositories from cache (if any)
    LoadReposFromCache(cache_path)

    if root_data == None:
        # No root set. Configure it (first load)
        root_configs["bare path"] = GetBareGit(root_configs["url"])
        root_configs["repo ID"]   = GetRepoIdFromPath(root_configs["bare path"])
        root_data = root_configs

    # Root is the starting point of the loop
    if root_data["repo ID"] not in repositories:
        repositories[root_data["repo ID"]] = root_configs
    else:
        # Always reset the root configs to what comes from the command line args
        # Even if it differs from the internal state (i.e/ invoked with different
        #  commit/branch from cached load). Needs to be done one by one in case there
        #  are preexisting keys that dont exst anymore
        for key in root_configs.keys():
            repositories[root_data["repo ID"]][key] = root_configs[key]

    # Setup all repositories to be reloaded and copy them over to be dependencies
    for repo_id in repositories:
        repositories[repo_id]["reloaded"] = False
    
    for x, y in repositories.items():
        next_dependencies[x] = y

    while len(next_dependencies) > 0:
        new_repos = 0

        # For each unloaded repository, get ready to load it
        repo_args = []

        repos_being_loaded = [x for x in next_dependencies.values()]

        next_dependencies.clear()
        for config in repos_being_loaded:
            # Check if repo was loaded in a previous operation, need to block it here as well
            if config["url"] not in loaded_urls:
                repo_args.append((config,))

        if len(repo_args) == 0:
            Print("Nothing more to load")
            break

        Print(f"{len(repo_args)} unloaded dependencies found")

        # Load remaining repositories
        RunInThreadsWithProgress(_LoadRepository, repo_args, None, __PrintLoadProgress)

        PrintProgressBar(len(repos_being_loaded), len(repos_being_loaded), prefix = 'Loading Repositories:', suffix = "Loaded " + str(len(repos_being_loaded)) + "/" + str(len(repos_being_loaded)) + " Repositories")
        Print("Finished dependency round")
        repos_being_loaded.clear()

    if state_changed_detected == True:
        PrintInfo("Saving "+str(len(repositories))+" repositories in cache")
        SaveReposToCache(repositories, cache_path)

    full_load = True

    return repositories

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
            if os.path.isfile(JoinPaths(file_path, "Kconfig")):
                LaunchProcess(f"unlink Kconfig", file_path)
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
            f.write(f'menu "{src}"\n')
            f.write(f'source "{Settings["paths"]["project configs"]}/{src}/Kconfig"\n')
            f.write(f'\nendmenu\n')

def ConvertKconfigToHeader():
    # LaunchProcess(f"cat .config | kconfig-config2h > {JoinPaths(Settings["paths"]["project configs"], "autogen.h")}", )
    # Have to do by hand. If there is a better way, please rewrite this
    kconfig_path = JoinPaths(Settings["paths"]["project configs"], ".config")
    header_path = JoinPaths(Settings["paths"]["autogened headers"], "autogen.h")
    with open(kconfig_path, "r") as config, open(header_path, "w") as header:
        header.write("#ifndef AUTOGEN_H\n")
        header.write("#define AUTOGEN_H\n")
        header.write("/* Auto-generated config header */\n\n")

        for line in config:
            line = line.strip()
            logging.error(line)

            if not line or line.startswith("#"):
                continue

            if line.startswith("CONFIG_"):
                key, val = line.split("=", 1)

                if val == "y":
                    header.write(f"#define {key} 1\n")
                elif val == "n":
                    header.write(f"/* #undef {key} */\n")
                else:
                    # handle strings and integers
                    if val.startswith('"') and val.endswith('"'):
                        header.write(f"#define {key} {val}\n")
                    else:
                        header.write(f"#define {key} {val}\n")
        header.write("\n#endif\n")

def __GenerateDefaultKconfig():
    # kconfig is to be removed it is an unmaitained project that is very hard to download
    #if not os.path.isfile(JoinPaths(Settings["paths"]["project configs"], ".config")):
    #    LaunchProcess("kconfig-conf --alldefconfig Kconfig", Settings["paths"]["project configs"])
    #ConvertKconfigToHeader()
    pass

def __SetupKConfig(repositories):
    logging.info("Setting up KConfig")
    menu_root = __GenerateFullMenu(repositories)
    collapsed_menus = __CollapseSingleEntryMenus(menu_root)
    __GenerateKConfigs(collapsed_menus, Settings["paths"]["project configs"])
    __CreateRootKConfig(collapsed_menus)
    logging.error(collapsed_menus)
    __GenerateDefaultKconfig()

def DependencyOf(repo, target):
    for dependency_url in repo["dependencies"].keys():
        if SameUrl(dependency_url, target["url"]):
            # logging.error(f"{target["name"]} is a dependency of {repo["name"]}")
            return True
    # logging.error(f"{target["name"]} is not a dependency of {repo["name"]}")
    return False

def GetProjectVariables():
    return {
        "AUTOGEN_HEADERS_PATH": Settings["paths"]["autogened headers"],
        "PROJ_NAME": Settings["ProjectName"],
        "PROJ_PATH": Settings["paths"]["project main"],
        "PROJ_BUILD_PATH":   Settings["paths"]["build"],
        "PROJ_BIN_PATH":     Settings["paths"]["binaries"],
        "PROJ_LIB_PATH":     Settings["paths"]["libraries"],
        "PROJ_OBJS_PATH":    Settings["paths"]["objects"],
        "PROJ_EXECS_PATH":   Settings["paths"]["executables"],
        "PROJ_TESTS_PATH":   Settings["paths"]["tests"]
    }

def GetRepositoryVariables(repository):
    return {
        "PROJECT_PATH":    Settings["paths"]["project main"],
        "REPO_NAME":       repository["repo name"],
        "REPO_ID":         repository["repo ID"],
        "REPO_SRC_PATH":   repository["repo source"],
        "REPO_BUILD_PATH": repository["build path"],
        "REPO_EXEC_PATH":  repository["executables"],
        "REPO_TESTS_PATH": repository["tests"],
        "REPO_LIB_PATH":   repository["libraries"]
    }

def __FetchAllPublicHeaders(repositories):
    public_header_folders = {}
    objects_to_link = {}
    for repo_id in repositories:
        try:
            repository = repositories[repo_id]
            # Fetch all public headers
            if len(repository["public headers"]) > 0:
                # build_dir = __RepoPathToBuild(repository)
                new_public_headers = [JoinPaths(repository["repo source"], x) for x in repository["public headers"]]
                new_public_headers = [x for x in new_public_headers if os.path.isdir(x) and len(x) != 0]
                if repo_id not in public_header_folders and len(new_public_headers) != 0:
                    public_header_folders[repo_id] = []

                if repo_id in public_header_folders:
                    public_header_folders[repo_id] += list(set(new_public_headers))

            # Fetch all objects to link
            will_link = not __RepoHasNoCode(repository)
            will_link = will_link and not __RepoHasFlagSet(repository, "no auto build")
            will_link = will_link and not __RepoHasFlagSet(repository, "independent project")
            # TODO: execs only should be infered by the build environment not having ".c"s to compile
            # however it is planned for an overhaul of the build system (abstract away from cmake only)
            # which would enable this change
            will_link = will_link and not __RepoHasFlagSet(repository, "execs only")
            if will_link:
                objects_to_link[repo_id] = repository["name"]+'_lib'

        except Exception as ex:
            traceback.print_exc()
            PrintError(str(ex))
            PrintDebug(repositories[repo_id])
            logging.error(str(ex))
    return objects_to_link, public_header_folders

def __SetupCMake(repositories):
    logging.info("Setting up CMake")
    global a
    repos_to_build = []

    objects_to_link, public_header_folders = __FetchAllPublicHeaders(repositories)

    # Build CMake for each repository
    for repo_id in repositories.keys():
        repository = repositories[repo_id]

        if __RepoHasFlagSet(repository, "no auto build") or __RepoHasNoCode(repository):
            logging.info(f"Skipping CMake setup for {repo_id}")
            continue

        if __RepoHasFlagSet(repository, "independent project"):
            # TODO Throw error if CMakeLists.txt does not exist in sub_dire
            IncludeEntry = f'add_subdirectory("{repository["repo source"]}" "{repository["build path"]}")'
        else:
            IncludeEntry = 'include("' + JoinPaths(repository["build path"], "CMakeLists.txt") + '")'

        repo_cmake_lists = JoinPaths(repository["build path"], "CMakeLists.txt")
        CreateParentDirectory(repo_cmake_lists)

        # Only import headers that are direct and/or indirect dependencies
        # Only link objects that are direct dependencies
        def GetDependencyData(repositories, starting_repo_id):
            dependencies = list(repositories.keys())
            dependencies.reverse()
            return dependencies
            # dependencies = [starting_repo_id]
            # starting_dependency_amount = len(dependencies)
            # current_dependency_amount = 0
            # first_iteration = 1
            # # direct_dependencies = []
            # # While the amount of dependencies changed
            # while starting_dependency_amount != current_dependency_amount:
            #     starting_dependency_amount = len(dependencies)
            #     # For all of the current dependencies
            #     for dependency in dependencies:
            #         # Find a dependency that hasn't yet been added
            #         for repo_id in repositories:
            #             # Already exists
            #             if repo_id in dependencies:
            #                 continue
            #             # Does not exist. Is it a dependency?
            #             if DependencyOf(repositories[dependency], repositories[repo_id]):
            #                 dependencies.append(repo_id)

            #     if first_iteration == 1:
            #         # direct_dependencies = dependencies.copy()
            #         first_iteration = 2
            #     current_dependency_amount = len(dependencies)
            #     break
            # # return direct_dependencies, dependencies
            # # Return the latest dependencies first
            # dependencies.reverse()
            # return dependencies

        # Unfortunately, linking only direct dependencies does not work due to transitive dependency failure
        # direct_dependencies, dependencies = GetDependencyData(repositories, repo_id)
        dependencies = GetDependencyData(repositories, repo_id)
        # Only import from dependencies
        public_headers       = []
        test_headers         = []
        private_headers      = []
        temp_objects_to_link = []
        # For indirect dependencies, also include headers (due to headers including headers)
        for dep_repo_id in dependencies:
            if dep_repo_id in public_header_folders:
                public_headers += public_header_folders[dep_repo_id]

        # For direct dependencies, only perform linking
        # for dep_repo_id in direct_dependencies:
        for dep_repo_id in dependencies:
            if repo_id == dep_repo_id:
                continue
            if dep_repo_id in objects_to_link:
                dep = repositories[dep_repo_id]
                if __RepoHasFlagSet(dep, "no auto build") or __RepoHasNoCode(dep):
                    continue
                temp_objects_to_link.append(objects_to_link[dep_repo_id])

        if len(repository["public headers"]) > 0:
            public_headers += [JoinPaths(repository["repo source"], x) for x in repository["public headers"]]

        if len(repository["private headers"]) > 0:
            private_headers += [JoinPaths(repository["repo source"], x) for x in repository["private headers"]]

        if len(repository["test headers"]) > 0:
            test_headers += [JoinPaths(repository["repo source"], x) for x in repository["test headers"]]

        # Check if there is already a CMakeLists and it isn't ours
        if os.path.isfile(repo_cmake_lists):
            can_delete = False
            with open(repo_cmake_lists) as f:
                content = f.readlines()

            if len(content) > 0 and "# PROJECTBASE" in content[0]:
                can_delete = True

            if can_delete:
                os.unlink(repo_cmake_lists)


        # if not os.path.isfile(repo_cmake_lists):
        # logging.error(f"{repository["name"]} {repository["current repo path"]} repo_cmake_lists {repo_cmake_lists}")
        repo_vars  = {
            "ADD_LIBRARY_TYPE": "",
            "TARGET_INCLUDE_TYPE": "PUBLIC",
            "PUBLIC_INCLUDES":   '\n'.join(public_headers),
            "PRIVATE_INCLUDES":  '\n'.join(private_headers),
            "TESTS_INCLUDES":    '\n'.join(test_headers),
            "LINK_DEPENDENCIES": '\n'.join(temp_objects_to_link),
        } | GetRepositoryVariables(repository)
        try:
            SetupTemplate("repository/CMakeLists.txt", repo_cmake_lists, repo_vars)
        except FileNotFoundError:
            logging.error(f"Warning. Repo {repository["name"]} does not have a CMake file. If this is expected, please add the `no auto build` to the configs")
            continue

        repos_to_build.append(IncludeEntry)

    project_vars = {"INCLUDE_REPOSITORY_CMAKELISTS":'\n'.join(repos_to_build)} | GetProjectVariables()
    SetupTemplate("project/CMakeLists.txt", JoinPaths(Settings["paths"]["build env"], "CMakeLists.txt"), project_vars)


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
        __RunRepoCommands(f"before build ({repository['name']})", repository["before build"])

    logging.info(f"Building project with {build_command}")
    returned = LaunchVerboseProcess(build_command)
    if(returned["code"] != 0):
        Settings.return_code = 1

    for repo_id in repositories:
        repository = repositories[repo_id]
        __RunRepoCommands(f"after build ({repository['name']})", repository["after build"])


