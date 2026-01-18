from menus.menu import Menu
from data.colors import ColorFormat, Colors
from processes.project import Project
from data.settings import CLONE_TYPE, Settings, GetBranch

from menus.run import RunMenu
from menus.settings import SettingsMenu
from menus.analyze import AnalysisMenu
from menus.clean import CleanMenu
from menus.version import VersioningMenu
from menus.kconfig import RunMenuConfig
from menus.ci import CIMenu

from data.paths import GetProjectBasePath
from processes.git_operations import GitGetHeadCommit



def main_description():
    active_settings = Settings["active"]
    if active_settings["Mode"] == "Release":
        build_type = ColorFormat(Colors.Blue, "Release build")
    else:
        build_type = ColorFormat(Colors.Yellow, "Debug build")
    
    if active_settings["Clone Type"] == CLONE_TYPE.SSH.value:
        clone_type = ColorFormat(Colors.Magenta, "ssh access")
    else:
        clone_type = ColorFormat(Colors.Cyan, "http[s] access")
    
    if active_settings["Speed"] == "Safe":
        speed_type = ColorFormat(Colors.Green, "Safe")
    else:
        speed_type = ColorFormat(Colors.Yellow, "Fast")

    branch = GetBranch()
    if branch != None:
        checkedout_branch = ColorFormat(Colors.Magenta, branch)
    else:
        checkedout_branch = ColorFormat(Colors.Grey, "No project wide branch checkedout")

    PB_commit = GitGetHeadCommit(GetProjectBasePath())

    return ColorFormat(Colors.Yellow, r"""
 ______              __              __   ______
|   __ \.----.-----.|__|.-----.----.|  |_|   __ \.---.-.-----.-----.
|    __/|   _|  _  ||  ||  -__|  __||   _|   __ <|  _  |__ --|  -__|
|___|   |__| |_____||  ||_____|____||____|______/|___._|_____|_____|
                   |___|
""" ) + PB_commit + f"\n{build_type} - {checkedout_branch}\n({Settings["url"]})\n({clone_type} - {speed_type})\n({Settings["paths"]["project main"]})\n"

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
