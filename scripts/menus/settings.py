from menus.menu import Menu
from data.settings import Settings, CLONE_TYPE
from data.colors import ColorFormat, Colors
from processes.project import Project
from menus.kconfig import KconfigMenu
from dependency_graph import BuildDependencyGraph, VisualizeGraph

def current_mode_entry():
    if Settings["active"]["Mode"] == "Release":
        return "Change from Release to Debug"
    else:
        return "Change from Debug to Release"

def toggle_mode():
    current_type = Settings["active"]["Mode"]
    if Settings["active"]["Mode"] == "Release":
        Settings["active"]["Mode"] = "Debug"
    else:
        Settings["active"]["Mode"] = "Release"

    if current_type != Settings["active"]["Mode"]:
        Settings.save_persisted_settings()

def current_clone_type_entry():
    if Settings["active"]["Clone Type"] == CLONE_TYPE.HTTPS.value:
        return "Change from " + CLONE_TYPE.HTTPS.value + " to " + CLONE_TYPE.SSH.value
    else:
        return "Change from " + CLONE_TYPE.SSH.value + " to " + CLONE_TYPE.HTTPS.value

def toggle_clone_type():
    current_type = Settings["active"]["Clone Type"]
    if current_type == CLONE_TYPE.HTTPS.value:
        Settings["active"]["Clone Type"] = CLONE_TYPE.SSH.value
    else:
        Settings["active"]["Clone Type"] = CLONE_TYPE.HTTPS.value
    
    if current_type != Settings["active"]["Clone Type"]:
        Settings.save_persisted_settings()
        # Change existing repositories' URL
        Project.SetCloneType(Settings["active"]["Clone Type"])

def settings_prologue():
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


def create_dependency_graph():
    graph = BuildDependencyGraph(Project.GetRepositories())
    VisualizeGraph(graph)

SettingsMenu = Menu("Settings Menu")
SettingsMenu.prologue = settings_prologue
SettingsMenu.AddCallbackEntry(current_mode_entry, toggle_mode)
SettingsMenu.AddCallbackEntry(current_clone_type_entry, toggle_clone_type)
SettingsMenu.AddSubmenuEntry("Build Configuration (Kconfig)", KconfigMenu)
SettingsMenu.AddCallbackEntry("Create dependency graph", create_dependency_graph)
