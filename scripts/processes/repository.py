import logging
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
import kconfiglib

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

def GetRepoIdFromURL(repo_url):
    url = url_SSH_to_HTTPS(repo_url)
    return url

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

    # Try to see if repository is still on the cached localization
    if current_location == None: # Do a guess of the correct place
        if("repo source" in imposed_configs):
            repo_path_cached = imposed_configs["repo source"]
            if(repo_path_cached != ""):
                cached_url = GetRepositoryUrl(repo_path_cached)
                if(SameUrl(cached_url,imposed_configs["url"])):
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

        SetDetectedStateChange()

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
            SetDetectedStateChange()
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
                ParseProcessResponse(LaunchProcess(proceed_condition))
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
    imposed_configs["repo id"] = repo_id

    imposed_configs["bare path"] = SetupBareData(imposed_configs["url"])

    configs = __LoadRepositoryFolder(imposed_configs)
    configs["reloaded"] = True

    config_variable_data = {
        "PROJECT_PATH": Settings["paths"]["project main"],
        "REPO_SRC_PATH":    configs["repo source"],
        # "REPOPATH":     configs["repo source"],
        # Repos specific paths for non-assisted build
        ## For intermediary build objects
        "REPO_BUILD_PATH":  configs["build path"],
        "REPO_EXEC_PATH":   configs["executables"],
        "REPO_TESTS_PATH":  configs["tests"],
        "REPO_LIB_PATH":    configs["libraries"],
    }

    # Reload metadata
    configs = ParseConfigs(configs, config_variable_data)

    repositories[repo_id] = configs
    repositories[repo_id]["reloaded"] = True

    # Load dependencies
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
            logging.error(f"dependency_configs of {configs["name"]} for {dep_repo_id}")
            logging.error(pformat(dependency_configs))
            repositories_lock.acquire()
            # if dep_repo_id in dependencies??
            if dep_repo_id not in repositories and dep_repo_id not in dependencies:
                dependencies[dep_repo_id] = dependency_configs
            repositories_lock.release()
    except Exception as ex:
        logging.error(f"Failed to load {pformat(configs)}")
        raise ex

# Main reposability is on adding on repositories global information on 
# which repos do have kconfigs, and creatint the target directory where they will be present
def __InitKconfigRepoSettings(repositories):
    root = {}
    logging.error(f"kconfig repositiories {repositories}")
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
            logging.error(f"kconfig path path {kconfig_path}")
            if not os.path.isfile(kconfig_path):
                continue
            repository["kconfig"] = kconfig_path
            project_code = Settings["paths"]["project code"]
            project_suffix = repository["kconfig"][len(project_code)+1:]
            repository["kconfig_target"] = JoinPaths(Settings["paths"]["project configs"], project_suffix)

        root[repository["name"]] = kconfig_path
    
    logging.error(f"kconfig root {root}")
    return root


# Generate Kconfigs for the directories that actually have those files
# Returns the kconfigs that are target that were cactually created
def __GenerateMainKConfigs(repositories) -> list[str]:
    target_kconfigs : list[str] = []
    for repo_path in repositories:
        repo = repositories[repo_path]
        if("kconfig" not in repo):
            continue 
        repo_original_kconfig = repo["kconfig"]
        repo_target_kconfig = repo["kconfig_target"]

        os.makedirs(os.path.dirname(repo_target_kconfig), exist_ok=True)
        with open(repo_target_kconfig, "w") as f:
            f.write(f'source "{repo_original_kconfig}"\n')

        target_kconfigs.append(repo_target_kconfig)
    return target_kconfigs

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
    """Create .config from the root Kconfig using kconfiglib (alldefconfig semantics)."""
    config_dir = Settings["paths"]["project configs"]
    root_kconfig = JoinPaths(config_dir, "Kconfig")
    config_file = JoinPaths(config_dir, ".config")

    if not os.path.isfile(config_file):
        try:
            kconf = kconfiglib.Kconfig(root_kconfig)
            kconf.load_config(None)
            kconf.write_config(config_file)
            logging.info(f"Generated default .config at {config_file} via kconfiglib")
        except Exception as e:
            logging.error(f"Failed to generate .config via kconfiglib: {e}")
            return

    # Try to generate autogen header using kconfiglib if available
    try:
        kconf = kconfiglib.Kconfig(root_kconfig)
        kconf.load_config(config_file)   # populate symbol values from .config
        header_path = JoinPaths(Settings["paths"]["autogened headers"], "autogen.h")
        # kconfiglib provides write_autoconf(header_path) which writes the C header
        kconf.write_autoconf(header_path)
        logging.info(f"Wrote autoconf header via kconfiglib to {header_path}")

    except Exception as e:
        logging.error(f"kconfiglib autoconf generation failed: {e}")
        logging.error("Falling back to ConvertKconfigToHeader()")
        ConvertKconfigToHeader()

import processes.kconfig_generaton as kconf
def __SetupKConfig(repositories):
    logging.info("Setting up KConfig")
    __InitKconfigRepoSettings(repositories)
    base_kconfigs_paths = __GenerateMainKConfigs(repositories)
    base_path = JoinPaths(Settings["paths"]["project configs"])
    kconf_tree = kconf.Tree(base_path)
    for path in base_kconfigs_paths:
        kconf_tree.add_path(path)
    #kconfig_info = kconf_tree.get_kconfigs_info_flat()
    kconfig_info = kconf_tree.get_kconfigs_info_organized()
    logging.error(f"KCONF INFO: {kconfig_info}")
    kconf.create_kconfigs(kconfig_info)

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
        "REPO_NAME":       repository["repo name"],
        "REPO_ID":         repository["repo id"],
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
            print(str(ex))
            print(repositories[repo_id])
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
        logging.error(pformat(repository))

        print(f"{repo_id} {repository["url"]}")
        # logging.error(repository)
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


