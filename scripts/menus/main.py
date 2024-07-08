from menus.menu import Menu
from data.settings import *
from data.colors import ColorFormat, Colors
from processes.project import Generate, Build

from menus.run import RunMenu
from menus.settings import SettingsMenu
from menus.analyze import AnalysisMenu
from menus.clean import CleanMenu
from menus.version import VersioningMenu


def main_description():
    ActiveSettings = settings["active"]
    BuildBanner = ""
    if ActiveSettings["Mode"] == "Release":
        BuildBanner = ColorFormat(Colors.Blue, "Release build")
    else:
        BuildBanner = ColorFormat(Colors.Yellow, "Debug build")
    
    if ActiveSettings["Clone Type"] == "ssh":
        CloneType = ColorFormat(Colors.Magenta, "ssh access")
    else:
        CloneType = ColorFormat(Colors.Cyan, "http[s] access")
    
    return ColorFormat(Colors.Yellow, r"""
 ______              __              __   ______
|   __ \.----.-----.|__|.-----.----.|  |_|   __ \.---.-.-----.-----.
|    __/|   _|  _  ||  ||  -__|  __||   _|   __ <|  _  |__ --|  -__|
|___|   |__| |_____||  ||_____|____||____|______/|___._|_____|_____|
                   |___|
""" ) + BuildBanner + "\n(" + settings["url"]  + " - " + CloneType + ")\n("  + settings["paths"]["project_main"] + ")\n"

MainMenu = Menu("Main Menu", True)
MainMenu.prologue = main_description
MainMenu.epilogue = ColorFormat(Colors.Green, "Ctrl + D to exit")
MainMenu.add_callback_entry("Generate project (build/pull from templates and configs)", Generate)
MainMenu.add_callback_entry("Build project (launches the build environment for this purpose)", Build)
MainMenu.add_submenu_entry("Run", RunMenu)
MainMenu.add_submenu_entry("Analyze", AnalysisMenu)
MainMenu.add_submenu_entry("Versioning", VersioningMenu)
MainMenu.add_submenu_entry("Clean", CleanMenu)
MainMenu.add_submenu_entry("Project settings", SettingsMenu)
