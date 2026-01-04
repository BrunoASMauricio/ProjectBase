from menus.menu import Menu
from data.settings import Settings, CLONE_TYPE
from data.colors import ColorFormat, Colors
from processes.project import Project
from dependency_graph import BuildGraph, VisualizeGraph
from processes.project import CleanPBCache, PurgePB

def current_speed_entry():
    if Settings["active"]["Speed"] == "Fast":
        return "Change from Fast to Safe"
    else:
        return "Change from Safe to Fast"    

def toggle_speed():
    current_type = Settings["active"]["Speed"]
    if Settings["active"]["Speed"] == "Fast":
        Settings["active"]["Speed"] = "Safe"
    else:
        Settings["active"]["Speed"] = "Fast"

    if current_type != Settings["active"]["Speed"]:
        Settings.save_persisted_settings()

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
    graph = BuildGraph(Project.GetRepositories(), "dependencies")
    VisualizeGraph(graph, "dependencies")

def create_api_graph():
    graph = BuildGraph(Project.GetRepositories(), "API")
    VisualizeGraph(graph, "API")

def print_repo(repo):
    print(f"{repo["repo name"]}")
    if len(repo["flags"]) == 0:
        print(f"\tNo flags")
    else:
        print(f"\tFlags: {repo["flags"]}")
    print(f"\tURL: {repo["url"]}")
    print(f"\tComittish: {repo["commitish"]}")
    # print(f"\tURL: {repo["flags"]}")

def show_repositories():
    repos = Project.GetRepositories()
    for repo in repos:
        print_repo(repos[repo])

SettingsMenu = Menu("Settings Menu")
SettingsMenu.prologue = settings_prologue
SettingsMenu.AddCallbackEntry(current_mode_entry, toggle_mode, "Toggle release type")
SettingsMenu.AddCallbackEntry(current_clone_type_entry, toggle_clone_type, "Toggle how clone is performed")
SettingsMenu.AddCallbackEntry(current_speed_entry, toggle_speed, "Toggle fast vs stable behaviors")
SettingsMenu.AddCallbackEntry("Create dependency graph", create_dependency_graph, "Create a graph based on repo dependencies")
SettingsMenu.AddCallbackEntry("Create API graph", create_api_graph, "Create a graph based on repo API")
SettingsMenu.AddCallbackEntry("Show repositories", show_repositories, "Print PB view of the projects' repos")
SettingsMenu.AddCallbackEntry("Clean project cache", CleanPBCache, "Clean cache (will have to reload from disk)")
SettingsMenu.AddCallbackEntry("Purge ALL projects (DANGEROUS)", PurgePB, "Fully remove all PB data. Equivalent to clean clone")
