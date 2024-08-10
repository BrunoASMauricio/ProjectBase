from menus.menu import Menu
from processes.versioning import DirectlyManageSingleRepository, PrintProjectStatus
from git import *

SyncMenu = Menu()
SyncMenu.add_callback_entry("Pull data from remote", None)
SyncMenu.add_callback_entry("Push data to remote", None)

ResetMenu = Menu()
ResetMenu.add_callback_entry("Clean not saved", None)
ResetMenu.add_callback_entry("Reset to latest tagged save", None)
ResetMenu.add_callback_entry("Reset to latest sync", None)

VersioningMenu = Menu("Version Menu")

VersioningMenu.prologue = ColorFormat(Colors.Yellow, ">> Versioning control <<\n")
# Spawn a console on the repositorys' directory
VersioningMenu.add_callback_entry("Directly manage single repository", DirectlyManageSingleRepository)
# Get status of the repositories
VersioningMenu.add_callback_entry("Status", PrintProjectStatus)
# Save all changes and Commit currently saved changes
VersioningMenu.add_callback_entry("Save and Tag currently saved changes (commit)", None)

# Get all information from the server (do not merge/pull, only fetch)
# Should print what changed (X branch has new changes, Y branch is new, Z branch has a conflict)
VersioningMenu.add_submenu_entry("Sync", SyncMenu)
# 
VersioningMenu.add_submenu_entry("Reset", ResetMenu)
