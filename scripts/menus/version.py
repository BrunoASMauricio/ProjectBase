from menus.menu import Menu
from processes.versioning import DirectlyManageSingleRepository, PrintProjectStatus, CleanAllUnsaved, ResetToLatestSync, UndoChanges
from processes.versioning import FetchAll, PullAll, PushAll, PrintCheckedoutState
from processes.versioning import GlobalFixedCommit, GlobalTemporaryCommit, GetCurrentTemporaryCommits
from processes.project import DeleteProject
from data.colors import ColorFormat, Colors

#       Save Menu
SaveMenu = Menu("Save Menu")
SaveMenu.AddCallbackEntry("Create global commit (squashes previous temporary commits)", GlobalFixedCommit)
SaveMenu.AddCallbackEntry("Create global temporary commit", GlobalTemporaryCommit)
SaveMenu.AddCallbackEntry("View current temporary commits", GetCurrentTemporaryCommits)
# GlobalSave
# SaveMenu.AddCallbackEntry("Stash global state", None)
# SaveMenu.AddCallbackEntry("See global stash", None)

#       Sync Menu
SyncMenu = Menu("Sync Menu")
# SyncMenu.AddCallbackEntry("Fetch data from remote", FetchAll)
# SyncMenu.AddCallbackEntry("Merge local data with fetched data", PullAll)
SyncMenu.AddCallbackEntry("Pull data from remote", PullAll)
SyncMenu.AddCallbackEntry("Push data to remote", PushAll)

#       Reset Menu
BranchMenu = Menu("Branch Menu")
BranchMenu.AddCallbackEntry("See checked out state", PrintCheckedoutState)
BranchMenu.AddCallbackEntry("Checkout branch", None)

#       Reset Menu
ResetMenu = Menu("Reset Menu")
ResetMenu.AddCallbackEntry("Clean unsaved files and folders", CleanAllUnsaved)
ResetMenu.AddCallbackEntry("Undo changes", UndoChanges)
# ResetMenu.AddCallbackEntry("Soft reset to latest tagged save (dont remove changes)", None)
# ResetMenu.AddCallbackEntry("Hard reset to latest tagged save (remove changes)", None)
ResetMenu.AddCallbackEntry("Reset files to latest sync", ResetToLatestSync)
# ResetMenu.AddCallbackEntry(ColorFormat(Colors.Red, ">> !!Delete Project!! <<"), DeleteProject)

#       Direct repo manipulation
DirectSingleRepoManageMenu = Menu("What repo to manage:", stay_in_menu=True)
DirectSingleRepoManageMenu.AddDynamicEntries(DirectlyManageSingleRepository)

#       Main versioning menu
VersioningMenu = Menu("Version Menu", stay_in_menu=True)

VersioningMenu.prologue = ColorFormat(Colors.Yellow, ">> Versioning control <<\n")
# Get status of the repositories
VersioningMenu.AddCallbackEntry("Project Status", PrintProjectStatus)
# Print the merged commit history of the managed repositories in the project in a pager program, via a temporary file (maybe a pipe to ProjectBase?)
# VersioningMenu.AddCallbackEntry("Get project commit history", None)
# Normal add + commit
VersioningMenu.AddSubmenuEntry("Save changes", SaveMenu)
# Save all changes and auto commit them
# VersioningMenu.AddCallbackEntry("Temporary save (automatic commit)", None)
# Squash current changes with previous automatic commits, and commit with a message
# VersioningMenu.AddCallbackEntry("Save changes and squash previous temporary saves", None)

# Get all information from the server (do not merge/pull, only fetch)
# Should print what changed (X branch has new changes, Y branch is new, Z branch has a conflict)
VersioningMenu.AddSubmenuEntry("Sync", SyncMenu)
VersioningMenu.AddSubmenuEntry("Branches", BranchMenu)
# 
VersioningMenu.AddSubmenuEntry("Reset", ResetMenu)
# Spawn a console on the repository's directory
VersioningMenu.AddSubmenuEntry("Manage single repository (spawn console)", DirectSingleRepoManageMenu)
# Use above menu for a single repository
# VersioningMenu.AddCallbackEntry("Manage single repository (via ProjectBase)", None)
