from menus.menu import Menu
from data.settings import Settings
from data.colors import ColorFormat, Colors
from processes.project import Project
from data.settings import CLONE_TYPE

from menus.run import RunMenu
from menus.settings import SettingsMenu
from menus.analyze import AnalysisMenu
from menus.clean import CleanMenu
from menus.version import VersioningMenu
from menus.kconfig import RunMenuConfig

def main_description():
    ActiveSettings = Settings["active"]
    BuildBanner = ""
    if ActiveSettings["Mode"] == "Release":
        BuildBanner = ColorFormat(Colors.Blue, "Release build")
    else:
        BuildBanner = ColorFormat(Colors.Yellow, "Debug build")
    
    if ActiveSettings["Clone Type"] == CLONE_TYPE.SSH.value:
        CloneType = ColorFormat(Colors.Magenta, "ssh access")
    else:
        CloneType = ColorFormat(Colors.Cyan, "http[s] access")
    
    return ColorFormat(Colors.Yellow, r"""
 ______              __              __   ______
|   __ \.----.-----.|__|.-----.----.|  |_|   __ \.---.-.-----.-----.
|    __/|   _|  _  ||  ||  -__|  __||   _|   __ <|  _  |__ --|  -__|
|___|   |__| |_____||  ||_____|____||____|______/|___._|_____|_____|
                   |___|
""" ) + BuildBanner + "\n(" + Settings["url"]  + " - " + CloneType + ")\n("  + Settings["paths"]["project main"] + ")\n"

def generate_project_description():
    return "Load project (" + str(len(Project.repositories)) + " loaded repositories)"

MainMenu = Menu("Main Menu", True)
MainMenu.prologue = main_description
MainMenu.epilogue = ColorFormat(Colors.Green, "Ctrl + D to exit")
MainMenu.AddCallbackEntry(generate_project_description, Project.setup)
MainMenu.AddCallbackEntry("Build project (launches the build environment for this purpose)", Project.build)
MainMenu.AddSubmenuEntry("Run", RunMenu)
MainMenu.AddSubmenuEntry("Analyze", AnalysisMenu)
MainMenu.AddSubmenuEntry("Versioning", VersioningMenu)
MainMenu.AddSubmenuEntry("Clean", CleanMenu)
MainMenu.AddCallbackEntry("Configure Project", RunMenuConfig)
MainMenu.AddSubmenuEntry("ProjectBase settings", SettingsMenu)
