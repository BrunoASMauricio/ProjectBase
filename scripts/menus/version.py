from menus.menu import Menu
from processes.versioning import DirectlyManageSingleRepository, PrintProjectStatus, CleanAllUnsaved, ResetToLatestSync, UndoChanges
from processes.versioning import FetchAll, PullAll, PushAll
from processes.versioning import GlobalFixedCommit, GlobalTemporaryCommit
from processes.project import DeleteProject
from data.colors import ColorFormat, Colors

#       Save Menu
SaveMenu = Menu("Save Menu")
SaveMenu.add_callback_entry("Create global commit (squashes previous temporary commits)", GlobalFixedCommit)
SaveMenu.add_callback_entry("Create global temporary commit", GlobalTemporaryCommit)
# GlobalSave
# SaveMenu.add_callback_entry("Stash global state", None)
# SaveMenu.add_callback_entry("See global stash", None)

#       Sync Menu
SyncMenu = Menu("Sync Menu")
# SyncMenu.add_callback_entry("Fetch data from remote", FetchAll)
# SyncMenu.add_callback_entry("Merge local data with fetched data", PullAll)
SyncMenu.add_callback_entry("Pull data from remote", PullAll)
SyncMenu.add_callback_entry("Push data to remote", PushAll)

#       Reset Menu
ResetMenu = Menu("Reset Menu")
ResetMenu.add_callback_entry("Clean unsaved files and folders", CleanAllUnsaved)
ResetMenu.add_callback_entry("Undo changes", UndoChanges)
# ResetMenu.add_callback_entry("Soft reset to latest tagged save (dont remove changes)", None)
# ResetMenu.add_callback_entry("Hard reset to latest tagged save (remove changes)", None)
ResetMenu.add_callback_entry("Reset files to latest sync", ResetToLatestSync)
# ResetMenu.add_callback_entry(ColorFormat(Colors.Red, ">> !!Delete Project!! <<"), DeleteProject)

#       Direct repo manipulation
DirectSingleRepoManageMenu = Menu("What repo to manage:", stay_in_menu=True)
DirectSingleRepoManageMenu.add_dynamic_entries(DirectlyManageSingleRepository)

#       Main versioning menu
VersioningMenu = Menu("Version Menu", stay_in_menu=True)

VersioningMenu.prologue = ColorFormat(Colors.Yellow, ">> Versioning control <<\n")
# Get status of the repositories
VersioningMenu.add_callback_entry("Project Status", PrintProjectStatus)
# Print the merged commit history of the managed repositories in the project in a pager program, via a temporary file (maybe a pipe to ProjectBase?)
# VersioningMenu.add_callback_entry("Get project commit history", None)
# Normal add + commit
VersioningMenu.add_submenu_entry("Save changes", SaveMenu)
# Save all changes and auto commit them
# VersioningMenu.add_callback_entry("Temporary save (automatic commit)", None)
# Squash current changes with previous automatic commits, and commit with a message
# VersioningMenu.add_callback_entry("Save changes and squash previous temporary saves", None)

# Get all information from the server (do not merge/pull, only fetch)
# Should print what changed (X branch has new changes, Y branch is new, Z branch has a conflict)
VersioningMenu.add_submenu_entry("Sync", SyncMenu)
# 
VersioningMenu.add_submenu_entry("Reset", ResetMenu)
# Spawn a console on the repository's directory
VersioningMenu.add_submenu_entry("Manage single repository (spawn console)", DirectSingleRepoManageMenu)
# Use above menu for a single repository
# VersioningMenu.add_callback_entry("Manage single repository (via ProjectBase)", None)
