import os
import logging
from data.settings import Settings
from data.json import load_json_file
from data.common import GetValueOrDefault, IsEmpty

"""
Merge overlay and original configs
On match, overlay takes precedent
"""
def MergeConfigs(original, overlay):
    new = original.copy()
    for key in overlay.keys():
        if False == IsEmpty(overlay[key]):
            new[key] = overlay[key]
        elif key not in new:
            new[key] = overlay[key]
    return new

"""
If the folder described by `name` is not present in configs, create list of the
defaults provided that exist in the system
"""
def __FindRepoFolders(current_repo_path, configs, name, default_folders):
    # Only search if value isn't already set
    configs[name] = []
    if name not in configs.keys() or IsEmpty(configs[name]):
        # Use default "headers" value, or first matching directory
        for default_folder in default_folders:
            if os.path.isdir(current_repo_path + "/" + default_folder):
                configs[name].append(default_folder)
    elif type(configs[name]) == type(""):
        # If present as string, change to list
        configs[name] = [configs[name]]

# Replace known variables (surrounded with '$$') by the known values
def __ParseVariables(data, variable_data):
    for name, value in variable_data.items():
        data = data.replace("$$" + name + "$$", value)
    return data

def ParseConfigs(configs, variable_data):
    if type(configs) == type([]):
        for i in range(len(configs)):
            config = configs[i]
            if type(config) == type(""):
                configs[i] = __ParseVariables(config, variable_data)

            elif type(config) == type([]):
                configs[i] = ParseConfigs(config, variable_data)

            elif type(config) == type({}):
                configs[i] = ParseConfigs(config, variable_data)

            elif config == None:
                pass
            else:
                pass
                # logging.warning("unknown type "+str(type(config))+" for config "+str(config))

    elif type(configs) == type({}):
        for key in configs:
            # Dependency configs need to be parsed in each of their own context
            if key == "dependencies":
                continue

            config = configs[key]
            if type(config) == type(""):
                # print("YEEEEEEY3 "+configs[key])
                configs[key] = __ParseVariables(config, variable_data)
                # print("YEEEEEEY4 "+configs[key])

            elif type(config) == type([]):
                configs[key] = ParseConfigs(config, variable_data)

            elif type(config) == type({}):
                configs[key] = ParseConfigs(config, variable_data)

            elif config == None:
                pass
            else:
                pass
                # logging.warning("unknown type "+str(type(config))+" for config "+str(config))
    return configs

# TODO: Remove after all configs were fixed (space instead of _)
def TEMP_fix_configs(configs):
    gen_config = None
    if type(configs) == type([]):
        gen_config = []
        for i in range(len(configs)):
            config = configs[i]
            if type(config) == type(""):
                gen_config.append(config)
            else:
                gen_config.append(TEMP_fix_configs(config))

    elif type(configs) == type({}):
        gen_config = {}
        for key in configs:
            # Dependency configs need to be parsed in each of their own context
            config = configs[key]
            if type(config) == type(""):
                gen_config[key.replace("_", " ")] = config

            else:
                gen_config[key] = TEMP_fix_configs(config)

    return gen_config

def __GetConfigsFolderState(folder_path):
    current_state = {}

    if not os.path.exists(folder_path):
        return None

    for root, _, files in os.walk(folder_path):
        for name in files:
            file_path = os.path.join(root, name)
            current_state[file_path] = os.path.getmtime(file_path)

    # Save the folder's own modified time
    current_state[folder_path] = os.path.getmtime(folder_path)
    return current_state

global_configs_state = {}

def UpdateState(folder_path, current_state=None):
    global global_configs_state

    if current_state == None:
        current_state = __GetConfigsFolderState(folder_path)

    global_configs_state[folder_path] = current_state

"""
Check if configs changed
"""
def ConfigsChanged(folder_path):
    global global_configs_state

    # Configs dont exist
    if not os.path.isdir(folder_path):
        # Did they exist before?
        if folder_path in global_configs_state.keys():
            # Delete and return confirmation of change
            return True
        return False

    current_state = __GetConfigsFolderState(folder_path)

    # Configs exist, are they already loaded?
    if folder_path not in global_configs_state.keys():
        return True

    # Configs existed, load current and previous state
    previous_state = global_configs_state[folder_path]

    current_state_paths  = current_state.keys()
    previous_state_paths = previous_state.keys()

    # Different amounts of timestamps
    if len(current_state_paths) != len(previous_state_paths):
        return True

    for path in current_state_paths:
        # Check if all paths exist in both lists
        if path not in previous_state_paths:
            return True

        current_timestamp  = current_state[path]
        previous_timestamp = previous_state[path]
        # Validate last modification time
        if current_timestamp != previous_timestamp:
            return True

    return False

def ResetConfigsState():
    global global_configs_state
    del global_configs_state
    global_configs_state = {}

"""
Load configurations from a repository at `repo_path`
"""
def LoadConfigs(current_repo_path):
    global global_configs_state

    configs_path = current_repo_path + "/configs"

    if os.path.isdir(configs_path):
        # if current_repo_path not in current_state.keys():
        global_configs_state[current_repo_path] = __GetConfigsFolderState(current_repo_path)
        configs = load_json_file(configs_path + "/configs.json", {})
    else:
        configs = {}

    configs["current repo path"] = current_repo_path
    configs["configs path"] = configs_path

    # TODO: Remove this after all repos have _ replaced with spaces
    configs = TEMP_fix_configs(configs)

    basic_headers = ["headers", "inc", "include"]

    # TODO: Generalize 3 cases below into a single function
    private_headers = GetValueOrDefault(configs, "private headers", [])
    public_headers  = GetValueOrDefault(configs, "public headers", [])
    test_headers    = GetValueOrDefault(configs, "test headers", [])

    # If no headers specified, attempt to auto detect
    if len(public_headers) == 0:
        for header in basic_headers:
            public_headers.append("code/" + header)
            public_headers.append(header)
        __FindRepoFolders(current_repo_path, configs, "public headers", public_headers)
    else:
        configs["public headers"]  = public_headers


    # If no headers specified, attempt to auto detect
    if len(private_headers) == 0:
        private_headers.append("code/")
        private_headers.append("code/source")
        for header in basic_headers:
            private_headers.append("execs/" + header)
        __FindRepoFolders(current_repo_path, configs, "private headers", private_headers)
    else:
        configs["private headers"] = private_headers

    # If no headers specified, attempt to auto detect
    if len(test_headers) == 0:
        test_headers.append("tests/")
        test_headers.append("tests/source")
        for header in basic_headers:
            test_headers.append("tests/" + header)
            test_headers.append("execs/tests/" + header)
        __FindRepoFolders(current_repo_path, configs, "test headers", test_headers)
    else:
        configs["test headers"]    = test_headers
        logging.error("YEEEYAH " + str(test_headers))

    configs["local path"] = GetValueOrDefault(configs, "local path", Settings["paths"]["default local path"])
    configs["flags"] = GetValueOrDefault(configs, "flags", [])
    configs["dependencies"] = GetValueOrDefault(configs, "dependencies", {})
    # Repository commands
    configs["setup"]        = GetValueOrDefault(configs, "setup", {})
    configs["before build"] = GetValueOrDefault(configs, "before build", {})
    configs["after build"]  = GetValueOrDefault(configs, "after build", {})
    configs["test_headers"] = GetValueOrDefault(configs, "test_headers", [])
    configs["executables"] = GetValueOrDefault(configs, "executables", [])

    return configs