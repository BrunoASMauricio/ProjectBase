
from common import *

ProjectSettings = {}
ActiveSettings ={}

def loadSettings(project):
    global ProjectSettings
    global ActiveSettings

    DefaultProjectSettings = {
        project["project_repo_name"]: {
            "Mode": "Debug"
        }
    }
    
    ProjectSettings =  loadJsonFile(project.paths["project settings"], DefaultProjectSettings)
    ActiveSettings = ProjectSettings[project["project_repo_name"]]

def updateSettings(project):
    global ProjectSettings
    dumpJsonFile(ProjectSettings, project.paths["project settings"])

def __toggleMode(project):
    global ActiveSettings
    if ActiveSettings["Mode"] == "Release":
        ActiveSettings["Mode"] = "Debug"
    else:
        ActiveSettings["Mode"] = "Release"

def mainSettingsMenu(project):
    Settings = {}

    if ActiveSettings["Mode"] == "Release":
        Settings["0"] = [__toggleMode , "Change from Release to Debug"]
    else:
        Settings["0"] = [__toggleMode , "Change from Debug to Release"]
  