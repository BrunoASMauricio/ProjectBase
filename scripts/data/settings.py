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
        Parser = argparse.ArgumentParser()
        Parser.description = "Extra command line arguments are treated as commands for ProjectBase"

        # Adding optional argument
        Parser.add_argument("-u", "--url", help = "Root repository's URL", default=None, required=False)

        Parser.add_argument("-c", "--commit",
                            help = "Root repository's commit",
                            default=None, required=False, nargs=1)

        Parser.add_argument("-b", "--branch",
                            help = "Root repository's branch",
                            default=None, required=False, type=str, nargs=1)

        Parser.add_argument("-s", "--single_thread",
                            help = "Do not run PB in multiple threads",
                            default=False, required=False, type=bool, action=argparse.BooleanOptionalAction)

        Parser.add_argument("-e", "--exit", action='store_true', help = "Exit after running command line arguments", default=False, required=False)

        ProjectArgs, ActionArgs = Parser.parse_known_args()

        self["url"]           = ProjectArgs.url
        self["commit"]        = ProjectArgs.commit
        self["branch"]        = ProjectArgs.branch
        self["exit"]          = ProjectArgs.exit
        self["single_thread"] = ProjectArgs.single_thread
        self["action"] = ActionArgs

    def save_persisted_settings(self):
        dump_json_file(self["persisted"], self["paths"]["configs"] + "/project_cache/settings")

    def load_persistent_settings(self):
        global ActiveSettings

        ProjectName = self["ProjectName"]

        DefaultSettings = {
            "Mode":       "Debug",
            "Clone Type": CLONE_TYPE.SSH.value
        }

        DefaultProjectSettings = {
            ProjectName: DefaultSettings
        }

        # Get persisted project settings
        persisted_settings = load_json_file(self["paths"]["configs"]+"/project_cache/settings", DefaultProjectSettings)

        if ProjectName not in persisted_settings.keys():
            persisted_settings[ProjectName] = DefaultSettings

        self["persisted"] = persisted_settings
        self["active"]    = persisted_settings[ProjectName]
        # self["active"]    = GetValueOrDefault(persisted_settings[ProjectName][""])

Settings = SETTINGS()
