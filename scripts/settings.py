
from common import *

ProjectSettings = {}
ActiveSettings ={}
ActiveProjectName = ""

def GetActiveSettings():
    global ActiveProjectName
    return ProjectSettings[ActiveProjectName]

def LoadSettings(Project):
    global ProjectSettings
    global ActiveSettings
    global ActiveProjectName

    ActiveProjectName = Project["ProjectRepoName"]

    DefaultSettings = {
        "Mode": "Debug",
        "Clone Type": "https"
    }

    DefaultProjectSettings = {
        ActiveProjectName: DefaultSettings
    }

    ProjectSettings =  LoadJsonFile(Project.Paths["configs"]+"/settings", DefaultProjectSettings)
    if ActiveProjectName not in ProjectSettings.keys():
        ProjectSettings[ActiveProjectName] = DefaultSettings
    ActiveSettings = ProjectSettings[ActiveProjectName]

def UpdateSettings(Project):
    global ProjectSettings
    DumpJsonFile(ProjectSettings, Project.Paths["configs"]+"/settings")

def __ToggleMode(Project):
    global ActiveSettings
    if ActiveSettings["Mode"] == "Release":
        ActiveSettings["Mode"] = "Debug"
    else:
        ActiveSettings["Mode"] = "Release"

def __ToggleSSH(Project):
    global ActiveSettings

    if ActiveSettings["Clone Type"] == "https":
        ActiveSettings["Clone Type"] = "ssh"
    else:
        ActiveSettings["Clone Type"] = "https"

    Project.SetCloneType(ActiveSettings["Clone Type"])

SettingsOptions = {
    "Mode": [__ToggleMode, {
                            "Release": "Change from Release to Debug",
                            "Debug":   "Change from Debug to Release"
                            }
            ],
    "Clone Type":   [__ToggleSSH,   {
                                    "https": "Change from http to git",
                                    "ssh":   "Change from git to http"
                                    }
                    ]
}


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
