import sys
import argparse
from data.common import *
from data.json import *

Settings = {}
ActiveSettings ={}
ActiveProjectName = ""

class Settings(dict):
    def __init__(self):
        pass
    
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

        Parser.add_argument("-e", "--exit", action='store_true', help = "Exit after running command line arguments", default=False, required=False)

        ProjectArgs, ActionArgs = Parser.parse_known_args()

        self["url"]    = ProjectArgs.url
        self["commit"] = ProjectArgs.commit
        self["branch"] = ProjectArgs.branch
        self["exit"]   = ProjectArgs.exit
        self["action"] = ActionArgs

    def save_persisted_settings(self):
        DumpJsonFile(settings["persisted"], settings["paths"]["configs"]+"/settings")

    def load_persistent_settings(self):
        global ActiveSettings

        ProjectName = settings["ProjectName"]

        DefaultSettings = {
            "Mode":       "Debug",
            "Clone Type": "https"
        }

        DefaultProjectSettings = {
            ProjectName: DefaultSettings
        }

        # Get persisted project settings
        persisted_settings = LoadJsonFile(settings["paths"]["configs"]+"/settings", DefaultProjectSettings)

        if ProjectName not in persisted_settings.keys():
            persisted_settings[ProjectName] = DefaultSettings

        settings["persisted"] = persisted_settings
        settings["active"]    = persisted_settings[ProjectName]

settings = Settings()

def get_active_settings():
    global ActiveProjectName
    if ActiveProjectName not in Settings.keys():
        print("'" + ActiveProjectName + "' is not an existing project")
        sys.exit(0)
    return Settings[ActiveProjectName]

def MainSettingsMenu(Project):
    global ActiveSettings

    OptionIndex = 0
    for OptionKey in SettingsOptions.keys():
        MenuText = ""
        # Possible values
        OptionValues = SettingsOptions[OptionKey][1]
        MenuText += "\t" + str(OptionIndex) + ") [" + OptionKey + "]\t"

        # If set, choose the appropriate text
        # Otherwise just choose the first one
        if OptionKey in ActiveSettings.keys():
            MenuText += OptionValues[ActiveSettings[OptionKey]]
        else:
            MenuText += list(OptionValues.values())[0]

        print(MenuText)

        OptionIndex = OptionIndex + 1

    Setting = int(input("[<] "))

    list(SettingsOptions.values())[Setting][0](Project)
