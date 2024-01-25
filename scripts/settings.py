
from common import *

ProjectSettings = {}
ActiveSettings ={}
ActiveProjectName = ""

def getActiveSettings():
    global ActiveProjectName
    return ProjectSettings[ActiveProjectName]

def loadSettings(project):
    global ProjectSettings
    global ActiveSettings
    global ActiveProjectName

    ActiveProjectName = project["project_repo_name"]

    DefaultProjectSettings = {
        ActiveProjectName: {
            "Mode": "Debug"
        }
    }
    
    ProjectSettings =  loadJsonFile(project.paths["project settings"], DefaultProjectSettings)
    ActiveSettings = ProjectSettings[ActiveProjectName]

def updateSettings(project):
    global ProjectSettings
    dumpJsonFile(ProjectSettings, project.paths["project settings"])

def __toggleMode(project):
    global ActiveSettings
    if ActiveSettings["Mode"] == "Release":
        ActiveSettings["Mode"] = "Debug"
    else:
        ActiveSettings["Mode"] = "Release"

Settings = {}

def printSettings():
    global Settings
    for key in Settings:
        print("\t"+key+") "+Settings[key][1])
    print("\t"+ColorFormat(Colors.Green, "Ctrl+C to exit"))

def mainSettingsMenu(project):

    if ActiveSettings["Mode"] == "Release":
        Settings["1"] = [__toggleMode , "Change from Release to Debug"]
    else:
        Settings["1"] = [__toggleMode , "Change from Debug to Release"]

    printSettings()
    setting = input("[<] ")

    Settings[setting][0](project)
