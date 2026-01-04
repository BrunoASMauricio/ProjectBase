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
from menus.ci import CIMenu

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
    
    if ActiveSettings["Speed"] == "Safe":
        SpeedType = ColorFormat(Colors.Green, "Safe")
    else:
        SpeedType = ColorFormat(Colors.Yellow, "Fast")

    return ColorFormat(Colors.Yellow, r"""
 ______              __              __   ______
|   __ \.----.-----.|__|.-----.----.|  |_|   __ \.---.-.-----.-----.
|    __/|   _|  _  ||  ||  -__|  __||   _|   __ <|  _  |__ --|  -__|
|___|   |__| |_____||  ||_____|____||____|______/|___._|_____|_____|
                   |___|
""" ) + f"{BuildBanner} \n({Settings["url"]})\n({CloneType} - {SpeedType})\n({Settings["paths"]["project main"]})\n"

def generate_project_description():
    return "Load project (" + str(len(Project.repositories)) + " loaded)"

MainMenu = Menu("Main Menu", True)
MainMenu.prologue = main_description
MainMenu.epilogue = ColorFormat(Colors.Green, "Ctrl + D to exit")
MainMenu.AddCallbackEntry(generate_project_description, Project.setup, "Download and setup the project")
MainMenu.AddCallbackEntry("Build project", Project.build, "Launch build (CMake). Craete executables and tests")
MainMenu.AddSubmenuEntry("Run", RunMenu, "Run an executable or test")
MainMenu.AddSubmenuEntry("Analyze", AnalysisMenu, "Run linter (clang-tidy)")
MainMenu.AddSubmenuEntry("Versioning", VersioningMenu, "Version manager menu")
MainMenu.AddSubmenuEntry("Clean", CleanMenu, "Clean project state (binaries, objects, artifacts, etc)")
MainMenu.AddSubmenuEntry("CI", CIMenu, "Launch CI")
MainMenu.AddCallbackEntry("Configure Project", RunMenuConfig, "Launch configs")
MainMenu.AddSubmenuEntry("ProjectBase settings", SettingsMenu, "Configure ProjectBase for the current project")
