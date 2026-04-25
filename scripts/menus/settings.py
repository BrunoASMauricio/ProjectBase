from menus.menu import Menu
from data.settings import Settings, CLONE_TYPE
from data.colors import ColorFormat, Colors
from processes.project import Project
from dependency_graph import BuildGraph, VisualizeGraph
from processes.project import CleanPBCache, PurgePB
from data.settings import ToggleCloneType, ToggleSpeed, ToggleMode, CycleLogLevel, GetLogLevel, ToggleThreading
from processes.PB_debug_terminal import PBTerminal
from data.print import SetLogLevel, LogLevels

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

def CurrentThreadingEntry():
    if Settings["active"].get("Threading", "Multi") == "Multi":
        return "Change from Multi Thread to Single Thread"
    else:
        return "Change from Single Thread to Multi Thread"

def CurrentCloneTypeEntry():
    if Settings["active"]["Clone Type"] == CLONE_TYPE.HTTPS.value:
        return "Change from " + CLONE_TYPE.HTTPS.value + " to " + CLONE_TYPE.SSH.value
    else:
        return "Change from " + CLONE_TYPE.SSH.value + " to " + CLONE_TYPE.HTTPS.value

_log_level_to_enum = {
    "Error":   LogLevels.ERR,
    "Warning": LogLevels.WARN,
    "Notice":  LogLevels.NOTICE,
    "Info":    LogLevels.INFO,
}

def CurrentLogLevelEntry():
    return f"Log level: {GetLogLevel()} (click to cycle)"

def _CycleLogLevel():
    new_level = CycleLogLevel()
    if new_level in _log_level_to_enum:
        SetLogLevel(_log_level_to_enum[new_level])

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

    prologue += "/"

    threading_mode = ActiveSettings.get("Threading", "Multi")
    if threading_mode == "Multi":
        prologue += ColorFormat(Colors.Blue, "Multi Thread")
    else:
        prologue += ColorFormat(Colors.Yellow, "Single Thread")

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
SettingsMenu.AddCallbackEntry(CurrentLogLevelEntry, _CycleLogLevel, "Cycle log verbosity: Error → Warning → Notice → Info")
SettingsMenu.AddCallbackEntry(CurrentCloneTypeEntry, _ToggleCloneType, "Toggle how clone is performed")
SettingsMenu.AddCallbackEntry(CurrentSpeedEntry, ToggleSpeed, "Toggle fast vs stable behaviors")
SettingsMenu.AddCallbackEntry(CurrentThreadingEntry, ToggleThreading, "Toggle between multi-threaded and single-threaded execution")
SettingsMenu.AddCallbackEntry("Create dependency graph", CreateDependencyGraph, "Create a graph based on repo dependencies")
SettingsMenu.AddCallbackEntry("Create API graph", CreateApiGraph, "Create a graph based on repo API")
SettingsMenu.AddCallbackEntry("Show repositories", ShowRepositories, "Print PB view of the projects' repos")
SettingsMenu.AddCallbackEntry("Clean project cache", CleanPBCache, "Clean cache (will have to reload from disk)")
SettingsMenu.AddCallbackEntry("Purge ALL projects (DANGEROUS)", PurgePB, "Fully remove all PB data. Equivalent to clean clone")
SettingsMenu.AddCallbackEntry("Launch PB Debug console", PBTerminal, "Console for performing introspection into PB")
