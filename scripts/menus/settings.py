from menus.menu import Menu
from data.settings import settings
from data.colors import ColorFormat, Colors
from processes.project import Project, SetCloneType

def current_mode_entry():
    if settings["active"]["Mode"] == "Release":
        return "Change from Release to Debug"
    else:
        return "Change from Debug to Release"

def toggle_mode():
    current_type = settings["active"]["Mode"]
    if settings["active"]["Mode"] == "Release":
        settings["active"]["Mode"] = "Debug"
    else:
        settings["active"]["Mode"] = "Release"

    if current_type != settings["active"]["Mode"]:
        settings.save_persisted_settings()

def current_clone_type_entry():
    if settings["active"]["Clone Type"] == "https":
        return "Change from https to ssh"
    else:
        return "Change from ssh to http"

def toggle_clone_type():
    current_type = settings["active"]["Clone Type"]
    if current_type == "https":
        settings["active"]["Clone Type"] = "ssh"
    else:
        settings["active"]["Clone Type"] = "https"
    
    if current_type != settings["active"]["Clone Type"]:
        settings.save_persisted_settings()
        SetCloneType(current_type)

def settings_prologue():
    prologue = ""
    ActiveSettings = settings["active"]
    if ActiveSettings["Mode"] == "Release":
        prologue = ColorFormat(Colors.Blue, "Release")
    else:
        prologue = ColorFormat(Colors.Yellow, "Debug")
    
    prologue += "/"

    if ActiveSettings["Clone Type"] == "ssh":
        prologue += ColorFormat(Colors.Magenta, "ssh")
    else:
        prologue += ColorFormat(Colors.Cyan, "https")
    
    return prologue + "\n"

SettingsMenu = Menu("Settings Menu")
SettingsMenu.prologue = settings_prologue
SettingsMenu.add_callback_entry(current_mode_entry, toggle_mode)
SettingsMenu.add_callback_entry(current_clone_type_entry, toggle_clone_type)
