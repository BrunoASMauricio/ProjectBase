from menus.menu import Menu
from data.settings import Settings, CLONE_TYPE
from data.colors import ColorFormat, Colors
from processes.project import Project
from dependency_graph import BuildGraph, VisualizeGraph
from processes.project import CleanPBCache, PurgePB
from data.settings import ToggleCloneType, ToggleSpeed, ToggleMode

def CurrentSpeedEntry():
    if Settings["active"]["Speed"] == "Fast":
        return "Change from Fast to Safe"
    else:
        return "Change from Safe to Fast"

def CurrentModeEntry():
    if Settings["active"]["Mode"] == "Release":
        return "Change from Release to Debug"
    else:
        return "Change from Debug to Release"

def _ToggleCloneType():
    if ToggleCloneType():
        Project.SetCloneType(Settings["active"]["Clone Type"])

def CurrentCloneTypeEntry():
    if Settings["active"]["Clone Type"] == CLONE_TYPE.HTTPS.value:
        return "Change from " + CLONE_TYPE.HTTPS.value + " to " + CLONE_TYPE.SSH.value
    else:
        return "Change from " + CLONE_TYPE.SSH.value + " to " + CLONE_TYPE.HTTPS.value

def SettingsPrologue():
    prologue = ""
    ActiveSettings = Settings["active"]
    if ActiveSettings["Mode"] == "Release":
        prologue = ColorFormat(Colors.Blue, "Release")
    else:
        prologue = ColorFormat(Colors.Yellow, "Debug")
    
    prologue += "/"

    if ActiveSettings["Clone Type"] == CLONE_TYPE.SSH.value:
        prologue += ColorFormat(Colors.Magenta, CLONE_TYPE.SSH.value)
    else:
        prologue += ColorFormat(Colors.Cyan, CLONE_TYPE.HTTPS.value)
    
    return prologue + "\n"


def CreateDependencyGraph():
    graph = BuildGraph(Project.GetRepositories(), "dependencies")
    VisualizeGraph(graph, "dependencies")

def CreateApiGraph():
    graph = BuildGraph(Project.GetRepositories(), "API")
    VisualizeGraph(graph, "API")

def PrintRepo(repo):
    print(f"{repo["repo name"]}")
    if len(repo["flags"]) == 0:
        print(f"\tNo flags")
    else:
        print(f"\tFlags: {repo["flags"]}")
    print(f"\tURL: {repo["url"]}")
    print(f"\tComittish: {repo["commitish"]}")
    # print(f"\tURL: {repo["flags"]}")

def ShowRepositories():
    repos = Project.GetRepositories()
    for repo in repos:
        PrintRepo(repos[repo])

SettingsMenu = Menu("Settings Menu")
SettingsMenu.prologue = SettingsPrologue
SettingsMenu.AddCallbackEntry(CurrentModeEntry, ToggleMode, "Toggle release type")
SettingsMenu.AddCallbackEntry(CurrentCloneTypeEntry, _ToggleCloneType, "Toggle how clone is performed")
SettingsMenu.AddCallbackEntry(CurrentSpeedEntry, ToggleSpeed, "Toggle fast vs stable behaviors")
SettingsMenu.AddCallbackEntry("Create dependency graph", CreateDependencyGraph, "Create a graph based on repo dependencies")
SettingsMenu.AddCallbackEntry("Create API graph", CreateApiGraph, "Create a graph based on repo API")
SettingsMenu.AddCallbackEntry("Show repositories", ShowRepositories, "Print PB view of the projects' repos")
SettingsMenu.AddCallbackEntry("Clean project cache", CleanPBCache, "Clean cache (will have to reload from disk)")
SettingsMenu.AddCallbackEntry("Purge ALL projects (DANGEROUS)", PurgePB, "Fully remove all PB data. Equivalent to clean clone")
