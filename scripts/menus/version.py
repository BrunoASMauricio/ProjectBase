from menus.menu import Menu
from processes.versioning import DirectlyManageSingleRepository, PrintProjectStatus, CleanAllUnsaved, ResetToLatestSync, UndoChanges
from processes.versioning import FetchAll, PullAll, PushAll, PrintCheckedoutState, SwitchBranch, CheckoutBranch
from processes.versioning import GlobalFixedCommit, GlobalTemporaryCommit, GetCurrentTemporaryCommits
from processes.versioning import SelectLocalBranchToDelete, SelectRemoteBranchToDelete, PrintAllBranches, SelectBranchToMerge, SelectBranchToCheckout
from processes.project import DeleteProject
from data.colors import ColorFormat, Colors

#       Save Menu
SaveMenu = Menu("Save Menu")
SaveMenu.AddCallbackEntry("Create global commit", GlobalFixedCommit, "Squash previous temporary commits into new commit")
SaveMenu.AddCallbackEntry("Create temporary commit", GlobalTemporaryCommit, "Auto commit which can be squashed automatically later")
SaveMenu.AddCallbackEntry("View current temporary commits", GetCurrentTemporaryCommits, "Get amount of temporary commits on each repo")
# GlobalSave
# SaveMenu.AddCallbackEntry("Stash global state", None)
# SaveMenu.AddCallbackEntry("See global stash", None)

#       Sync Menu
SyncMenu = Menu("Sync Menu")
# SyncMenu.AddCallbackEntry("Fetch data from remote", FetchAll)
# SyncMenu.AddCallbackEntry("Merge local data with fetched data", PullAll)
SyncMenu.AddCallbackEntry("Pull data from remote", PullAll, "Pull data from remote (might lead to conflicts)")
SyncMenu.AddCallbackEntry("Push data to remote", PushAll, "Push data to remote (might fail if there are conflicts)")


## Delete local branch
DeleteLocalBranchMenu = Menu("Delete local branch:")
DeleteLocalBranchMenu.AddDynamicEntries(SelectLocalBranchToDelete)

## Delete remote branch
DeleteRemoteBranchMenu = Menu("Delete remote branch:")
DeleteRemoteBranchMenu.AddDynamicEntries(SelectRemoteBranchToDelete)

## Merge branch to current
MergeBranchToCurrentMenu = Menu("What merge to branch into the current one:")
MergeBranchToCurrentMenu.AddDynamicEntries(SelectBranchToMerge)

## Switch to an existing branch
SwitchBranchMenu = Menu("What branch to check out:")
SwitchBranchMenu.AddDynamicEntries(SelectBranchToCheckout)

#       Reset Menu
BranchMenu = Menu("Branch Menu")
BranchMenu.AddCallbackEntry("See checked out state", PrintCheckedoutState, "Get current branches (local and the remotes)")
BranchMenu.AddCallbackEntry("See all branches", PrintAllBranches, "Get current branches (local and the remotes)")
BranchMenu.AddSubmenuEntry("Switch branch", SwitchBranchMenu, "Checkout a branch on all clean, managed repos")
BranchMenu.AddCallbackEntry("Checkout branch", CheckoutBranch, "Checkout a branch on all clean, managed repos")
BranchMenu.AddSubmenuEntry("Merge", MergeBranchToCurrentMenu, "Select branch to merge into current")
BranchMenu.AddSubmenuEntry("Delete local branch", DeleteLocalBranchMenu, "Delete a local branch")
BranchMenu.AddSubmenuEntry("Delete remote branch", DeleteRemoteBranchMenu, "Delete a remote branch")

#       Reset Menu
ResetMenu = Menu("Reset Menu")
ResetMenu.AddCallbackEntry("Clean unsaved files and folders", CleanAllUnsaved)
ResetMenu.AddCallbackEntry("Undo changes", UndoChanges, "Remove all changes that are not committed")
# ResetMenu.AddCallbackEntry("Soft reset to latest tagged save (dont remove changes)", None)
# ResetMenu.AddCallbackEntry("Hard reset to latest tagged save (remove changes)", None)
ResetMenu.AddCallbackEntry("Reset files to latest sync", ResetToLatestSync, "Reset changes to the state of the upstream branch")
# ResetMenu.AddCallbackEntry(ColorFormat(Colors.Red, ">> !!Delete Project!! <<"), DeleteProject)

#       Direct repo manipulation
DirectSingleRepoManageMenu = Menu("What repo to manage:", stay_in_menu=True)
DirectSingleRepoManageMenu.AddDynamicEntries(DirectlyManageSingleRepository)

#       Main versioning menu
VersioningMenu = Menu("Version Menu", stay_in_menu=True)

VersioningMenu.prologue = ColorFormat(Colors.Yellow, ">> Versioning control <<\n")
# Get status of the repositories
VersioningMenu.AddCallbackEntry("Project Status", PrintProjectStatus, "Show local vs remote status per repo")
# Print the merged commit history of the managed repositories in the project in a pager program, via a temporary file (maybe a pipe to ProjectBase?)
# VersioningMenu.AddCallbackEntry("Get project commit history", None)
# Normal add + commit
VersioningMenu.AddSubmenuEntry("Save changes", SaveMenu, "Select how to save changes (locally)")
# Save all changes and auto commit them
# VersioningMenu.AddCallbackEntry("Temporary save (automatic commit)", None)
# Squash current changes with previous automatic commits, and commit with a message
# VersioningMenu.AddCallbackEntry("Save changes and squash previous temporary saves", None)

# Get all information from the server (do not merge/pull, only fetch)
# Should print what changed (X branch has new changes, Y branch is new, Z branch has a conflict)
VersioningMenu.AddSubmenuEntry("Sync", SyncMenu, "Synchronize changes between remote and local")
VersioningMenu.AddSubmenuEntry("Branches", BranchMenu, "Manage branch state across all of the project")
# 
VersioningMenu.AddSubmenuEntry("Reset", ResetMenu, "Reset changes (saved, unsaved, etc)")
# Spawn a console on the repository's directory
VersioningMenu.AddSubmenuEntry("Manage single repository (spawn console)", DirectSingleRepoManageMenu, "Spawn terminal on specific repo")
# Use above menu for a single repository
# VersioningMenu.AddCallbackEntry("Manage single repository (via ProjectBase)", None)
