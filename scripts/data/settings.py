import argparse
from data.common import *
from data.json import *
from data.git import GetRepoNameFromURL
from enum import Enum
import json

class CLONE_TYPE(Enum):
    HTTPS = "https"
    SSH   = "ssh"
    NONE  = "none"

ActiveSettings ={}
ActiveProjectName = ""

DEFAULT_SETTINGS = {
    "Speed":      "Safe",
    "Mode":       "Debug",
    "Clone Type": CLONE_TYPE.SSH.value
}

def ErrorCheckLogs(exception):
    print(f"ERROR: Check logs at {Settings["log_file"]} for more information")
    logging.error(f"Exception: {type(exception)} {exception}")
    logging.error(get_full_traceback(exception))

def ToggleSpeed():
    current_type = Settings["active"]["Speed"]
    if Settings["active"]["Speed"] == "Fast":
        Settings["active"]["Speed"] = "Safe"
    else:
        Settings["active"]["Speed"] = "Fast"

    if current_type != Settings["active"]["Speed"]:
        Settings.save_persisted_settings()

def SetBranch(branch):
    Settings["active"]["Branch"] = branch
    Settings.save_persisted_settings()

def GetBranch():
    if "Branch" in Settings["active"].keys() and Settings["active"]["Branch"] != None:
        return Settings["active"]["Branch"]
    # No project-wide branch configured
    return None

def ToggleMode():
    current_type = Settings["active"]["Mode"]
    if Settings["active"]["Mode"] == "Release":
        Settings["active"]["Mode"] = "Debug"
    else:
        Settings["active"]["Mode"] = "Release"

    if current_type != Settings["active"]["Mode"]:
        Settings.save_persisted_settings()

"""
Return True if the clone type changed
"""
def ToggleCloneType():
    current_type = Settings["active"]["Clone Type"]
    if current_type == CLONE_TYPE.HTTPS.value:
        Settings["active"]["Clone Type"] = CLONE_TYPE.SSH.value
    else:
        Settings["active"]["Clone Type"] = CLONE_TYPE.HTTPS.value

    if current_type != Settings["active"]["Clone Type"]:
        Settings.save_persisted_settings()
        # Change existing repositories' URL
        return True
    return False

class SETTINGS(dict):
    def init(self):
        # Initialize parser
        self.parse_arguments()
        self.return_code = 0
        self.ci_was_runned_and_passed = False
        self.ci_was_runned = False

    def start(self):
        # Commit or branch
        if self["commit"] != None and self["branch"] != None:
            Abort("Please use either commit or branch, not both")

        if self["url"] == None and (self["commit"] != None or self["branch"] != None):
            Abort("If you provide a commit/branch, you also need to provide a URL")

        # Set base project settings
        self["name"] = GetRepoNameFromURL(self["url"])

    def parse_arguments(self):
        parser = argparse.ArgumentParser()
        parser.description = "Extra command line arguments are treated as commands for ProjectBase"

        # Adding optional argument
        parser.add_argument("-u", "--url", help = "Root repository's URL", default=None, required=False)
        parser.add_argument("-o", "--out_file", help = "Output to file", default="", required=False)
        parser.add_argument("-l", "--log_file", help = "Pipe internal logs to file", default="/tmp/project_base.log", required=False)

        parser.add_argument("-c", "--commit",
                            help = "Root repository's commit",
                            default=None, required=False, nargs=1)

        parser.add_argument("-b", "--branch",
                            help = "Root repository's branch",
                            default=None, required=False, type=str)

        parser.add_argument("-s", "--single_thread",
                            help = "Do not run PB in multiple threads",
                            default=False, required=False, action=argparse.BooleanOptionalAction)

        parser.add_argument("-e", "--exit", action='store_true', help = "Exit after running command line arguments. Performs early exit in case one of the operations ends in error", default=False, required=False)

        parser.add_argument("-d", "--debug", action='store_true', help = "Increase log verbosity to debug ProjectBase", default=False, required=False)

        parser.add_argument("-f", "--fast", action='store_true', help = "Cache Repositories in pickle and do not consider config changes, deactivate to consider if needed", default=False, required=False)

        # Configurations for CI infrastructure 
        parser.add_argument("-ci", "--commitJsonPath", help = "JSON Information with all the repos that have commit changes, that have to be commit copied instead of usual by remote copy", default=None, required=False)

        # --args="...." is accepted for launching executables, but it is not handled here

        project_args, action_args = parser.parse_known_args()

        self["log_file"]      = project_args.log_file
        self["out_file"]      = project_args.out_file
        self["url"]           = project_args.url
        self["commit"]        = project_args.commit
        self["branch"]        = project_args.branch
        self["exit"]          = project_args.exit
        self["single thread"] = project_args.single_thread
        self["debug"]         = project_args.debug
        self["fast"]          = project_args.fast
        # Trailing unknown arguments
        self["action"] = action_args

        # CI Build options (they will mimick original options with extra commit Json option)
        self["commitJsonPath"] = project_args.commitJsonPath
        self["isCI"] = False
        if(self["commitJsonPath"]):
            self["isCI"] = True
            with open(self["commitJsonPath"], "r") as f:
               self["commitJson"] = json.load(f)

            if(self["url"] is None):
                raise ValueError("In CI Build, url should always be provided")

    def save_persisted_settings(self):
        dump_json_file(self["persisted"], self["paths"]["configs"] + "/project_cache/settings")

    def reset_settings(self):
        self["active"] = DEFAULT_SETTINGS

    def load_persistent_settings(self):
        global ActiveSettings

        project_name = self["ProjectName"]

        default_project_settings = {
            project_name: DEFAULT_SETTINGS
        }

        # Get persisted project settings
        persisted_settings = load_json_file(self["paths"]["configs"]+"/project_cache/settings", default_project_settings)

        if project_name not in persisted_settings.keys():
            persisted_settings[project_name] = DEFAULT_SETTINGS

        self["persisted"] = persisted_settings
        self["active"]    = persisted_settings[project_name]
        # self["active"]    = GetValueOrDefault(persisted_settings[ProjectName][""])

Settings = SETTINGS()
