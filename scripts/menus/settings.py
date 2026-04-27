from menus.menu import Menu
from data.settings import Settings, CLONE_TYPE
from data.colors import ColorFormat, Colors
from processes.project import Project
from dependency_graph import BuildGraph, VisualizeGraph
from processes.project import CleanPBCache, PurgePB
from data.settings import ToggleCloneType, ToggleSpeed, ToggleMode, CycleLogLevel, GetLogLevel, ToggleThreading
from processes.PB_debug_terminal import PBTerminal
from data.print import SetLogLevel, LogLevels

# Single source of truth for setting color mappings (used here and in main menu)
SPEED_COLORS = {"Fast": Colors.Yellow, "Safe": Colors.Green}
MODE_COLORS = {"Release": Colors.Blue, "Debug": Colors.Yellow}
THREADING_COLORS = {"Multi Thread": Colors.Blue, "Single Thread": Colors.Yellow}
CLONE_COLORS = {CLONE_TYPE.SSH.value: Colors.Magenta, CLONE_TYPE.HTTPS.value: Colors.Cyan}
LOG_LEVEL_COLORS = {"Error": Colors.Red, "Warning": Colors.Magenta, "Notice": Colors.Blue, "Info": Colors.Green}

def _colored_toggle(current, other, color_map):
    return "Change from " + ColorFormat(color_map[current], current) + " to " + ColorFormat(color_map[other], other)

def CurrentSpeedEntry():
    if Settings["active"]["Speed"] == "Fast":
        return _colored_toggle("Fast", "Safe", SPEED_COLORS)
    else:
        return _colored_toggle("Safe", "Fast", SPEED_COLORS)

def CurrentModeEntry():
    if Settings["active"]["Mode"] == "Release":
        return _colored_toggle("Release", "Debug", MODE_COLORS)
    else:
        return _colored_toggle("Debug", "Release", MODE_COLORS)

def _ToggleCloneType():
    if ToggleCloneType():
        Project.SetCloneType(Settings["active"]["Clone Type"])

def CurrentThreadingEntry():
    if Settings["active"].get("Threading", "Multi") == "Multi":
        return _colored_toggle("Multi Thread", "Single Thread", THREADING_COLORS)
    else:
        return _colored_toggle("Single Thread", "Multi Thread", THREADING_COLORS)

def CurrentCloneTypeEntry():
    if Settings["active"]["Clone Type"] == CLONE_TYPE.HTTPS.value:
        return _colored_toggle(CLONE_TYPE.HTTPS.value, CLONE_TYPE.SSH.value, CLONE_COLORS)
    else:
        return _colored_toggle(CLONE_TYPE.SSH.value, CLONE_TYPE.HTTPS.value, CLONE_COLORS)

_log_level_to_enum = {
    "Error":   LogLevels.ERR,
    "Warning": LogLevels.WARN,
    "Notice":  LogLevels.NOTICE,
    "Info":    LogLevels.INFO,
}

def CurrentLogLevelEntry():
    level = GetLogLevel()
    color = LOG_LEVEL_COLORS.get(level, Colors.Grey)
    return f"Log level: {ColorFormat(color, level)} (click to cycle)"

def _CycleLogLevel():
    new_level = CycleLogLevel()
    if new_level in _log_level_to_enum:
        SetLogLevel(_log_level_to_enum[new_level])

def SettingsPrologue():
    ActiveSettings = Settings["active"]

    mode = ActiveSettings["Mode"]
    prologue = ColorFormat(MODE_COLORS[mode], mode)

    prologue += "/"

    clone = ActiveSettings["Clone Type"]
    prologue += ColorFormat(CLONE_COLORS[clone], clone)

    prologue += "/"

    threading = "Multi Thread" if ActiveSettings.get("Threading", "Multi") == "Multi" else "Single Thread"
    prologue += ColorFormat(THREADING_COLORS[threading], threading)

    return prologue + "\n"


def CreateDependencyGraph():
    graph = BuildGraph(Project.GetRepositories(), "dependencies")
    VisualizeGraph(graph, "dependencies")

def CreateApiGraph():
    graph = BuildGraph(Project.GetRepositories(), "API")
    VisualizeGraph(graph, "API")

def PrintRepo(repo):
    print(f"{repo["repo name"]}")
    print(f"\tPath: {repo.get("local path", "")}")
    if len(repo["flags"]) == 0:
        print(f"\tNo flags")
    else:
        print(f"\tFlags: {repo["flags"]}")
    print(f"\tURL: {repo["url"]}")
    print(f"\tComittish: {repo["commitish"]}")

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
