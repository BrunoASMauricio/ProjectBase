
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

    DefaultProjectSettings = {
        ActiveProjectName: {
            "Mode": "Debug"
        }
    }

    ProjectSettings =  LoadJsonFile(Project.Paths["project settings"], DefaultProjectSettings)
    ActiveSettings = ProjectSettings[ActiveProjectName]

def UpdateSettings(Project):
    global ProjectSettings
    DumpJsonFile(ProjectSettings, Project.Paths["project settings"])

def __ToggleMode(Project):
    global ActiveSettings
    if ActiveSettings["Mode"] == "Release":
        ActiveSettings["Mode"] = "Debug"
    else:
        ActiveSettings["Mode"] = "Release"

Settings = {}

def PrintSettings():
    global Settings
    for key in Settings:
        print("\t"+key+") "+Settings[key][1])
    print("\t"+ColorFormat(Colors.Green, "Ctrl+C to exit"))

def MainSettingsMenu(Project):

    if ActiveSettings["Mode"] == "Release":
        Settings["1"] = [__ToggleMode , "Change from Release to Debug"]
    else:
        Settings["1"] = [__ToggleMode , "Change from Debug to Release"]

    PrintSettings()
    Setting = input("[<] ")

    Settings[Setting][0](Project)
