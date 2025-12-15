import sys
import argparse
from data.common import *
from data.json import *
from data.git import GetRepoNameFromURL
from enum import Enum

class CLONE_TYPE(Enum):
    HTTPS = "https"
    SSH   = "ssh"
    NONE  = "none"

ActiveSettings ={}
ActiveProjectName = ""

class SETTINGS(dict):
    def init(self):
        # Initialize parser
        self.parse_arguments()

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

        parser.add_argument("-c", "--commit",
                            help = "Root repository's commit",
                            default=None, required=False, nargs=1)

        parser.add_argument("-b", "--branch",
                            help = "Root repository's branch",
                            default=None, required=False, type=str, nargs=1)

        parser.add_argument("-s", "--single_thread",
                            help = "Do not run PB in multiple threads",
                            default=False, required=False, action=argparse.BooleanOptionalAction)

        parser.add_argument("-e", "--exit", action='store_true', help = "Exit after running command line arguments", default=False, required=False)

        parser.add_argument("-d", "--debug", action='store_true', help = "Increase log verbosity to debug ProjectBase", default=False, required=False)

        parser.add_argument("-f", "--fast", action='store_true', help = "Cache Repositories in pickle and do not consider config changes, deactivate to consider if needed", default=False, required=False)

        project_args, action_args = parser.parse_known_args()

        self["url"]           = project_args.url
        self["commit"]        = project_args.commit
        self["branch"]        = project_args.branch
        self["exit"]          = project_args.exit
        self["single thread"] = project_args.single_thread
        self["debug"]         = project_args.debug
        self["fast"]          = project_args.fast
        # Trailing unknown arguments
        self["action"] = action_args

    def save_persisted_settings(self):
        dump_json_file(self["persisted"], self["paths"]["configs"] + "/project_cache/settings")

    def load_persistent_settings(self):
        global ActiveSettings

        project_name = self["ProjectName"]

        default_settings = {
            "Speed":      "Safe", 
            "Mode":       "Debug",
            "Clone Type": CLONE_TYPE.SSH.value
        }

        default_project_settings = {
            project_name: default_settings
        }

        # Get persisted project settings
        persisted_settings = load_json_file(self["paths"]["configs"]+"/project_cache/settings", default_project_settings)

        if project_name not in persisted_settings.keys():
            persisted_settings[project_name] = default_settings

        self["persisted"] = persisted_settings
        self["active"]    = persisted_settings[project_name]
        # self["active"]    = GetValueOrDefault(persisted_settings[ProjectName][""])

Settings = SETTINGS()
