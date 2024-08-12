from menus.menu import Menu
from processes.versioning import DirectlyManageSingleRepository, PrintProjectStatus, CleanAllUnsaved, GlobalSave, ResetToLatestSync, UndoChanges
from git import *
from processes.project import DeleteProject

SyncMenu = Menu("Sync Menu")
SyncMenu.add_callback_entry("Pull data from remote", None)
SyncMenu.add_callback_entry("Push data to remote", None)

ResetMenu = Menu("Reset Menu")
ResetMenu.add_callback_entry("Clean unsaved files and folders", CleanAllUnsaved)
ResetMenu.add_callback_entry("Undo changes", UndoChanges)
# ResetMenu.add_callback_entry("Soft reset to latest tagged save (dont remove changes)", None)
# ResetMenu.add_callback_entry("Hard reset to latest tagged save (remove changes)", None)
ResetMenu.add_callback_entry("Reset files to latest sync", ResetToLatestSync)
# ResetMenu.add_callback_entry(ColorFormat(Colors.Red, ">> !!Delete Project!! <<"), DeleteProject)

VersioningMenu = Menu("Version Menu")

VersioningMenu.prologue = ColorFormat(Colors.Yellow, ">> Versioning control <<\n")
# Get status of the repositories
VersioningMenu.add_callback_entry("Status", PrintProjectStatus)
# Print the merged commit history of the managed repositories in the project in a pager program, via a temporary file (maybe a pipe to ProjectBase?)
# VersioningMenu.add_callback_entry("Get project commit history", None)
# Normal add + commit
VersioningMenu.add_callback_entry("Save changes", GlobalSave)
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
VersioningMenu.add_callback_entry("Manage single repository (spawn console)", DirectlyManageSingleRepository)
# Use above menu for a single repository
# VersioningMenu.add_callback_entry("Manage single repository (via ProjectBase)", None)
