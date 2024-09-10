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

"""
Load configurations from a repository at `repo_path`
"""
def LoadConfigs(current_repo_path):
    configs_path = current_repo_path + "/configs"
    if not os.path.isdir(configs_path):
        configs = {}
    else:
        configs = load_json_file(configs_path + "/configs.json", {})
    
    # TODO: Remove this after all repos have _ replaced with spaces
    # print(configs)
    configs = TEMP_fix_configs(configs)
    # print(configs)

    basic_headers = ["headers", "inc", "include"]

    # Headers to include when linking against this repository (or compiling as part of it)
    public_headers = []
    for header in basic_headers:
        public_headers.append("code/" + header)
        public_headers.append(header)
    __FindRepoFolders(current_repo_path, configs, "public headers", public_headers)

    # Headers to include when compiling as part of this repository
    private_headers = []
    private_headers.append("code/")
    private_headers.append("code/source")
    for header in basic_headers:
        private_headers.append("tests/" + header)
        private_headers.append("execs/" + header)
        private_headers.append("execs/tests/" + header)
    __FindRepoFolders(current_repo_path, configs, "private headers", private_headers)

    configs["local path"] = GetValueOrDefault(configs, "local path", Settings["paths"]["default local path"])
    # configs["local path"] = GetValueOrDefault(configs, "local path", Settings["paths"]["general repository"])
    configs["flags"] = GetValueOrDefault(configs, "flags", [])
    configs["dependencies"] = GetValueOrDefault(configs, "dependencies", {})
    # Repository commands
    configs["setup"]        = GetValueOrDefault(configs, "setup", {})
    configs["before build"] = GetValueOrDefault(configs, "before build", {})
    configs["after build"]  = GetValueOrDefault(configs, "after build", {})
    configs["test_headers"] = GetValueOrDefault(configs, "test_headers", [])
    configs["executables"] = GetValueOrDefault(configs, "executables", [])
    # print(configs)

    #     if "commit" not in configs["dependencies"][Dependency]:
    #         configs["dependencies"][Dependency]["commit"] = None

    #     if "branch" not in configs["dependencies"][Dependency]:
    #         configs["dependencies"][Dependency]["branch"] = None

    #     if "configs" not in configs["dependencies"][Dependency]:
    #         configs["dependencies"][Dependency]["configs"] = None

    return configs