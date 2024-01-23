import sys

from common import *
from git import *

def runOnLoadedRepos(loaded_repos, function_to_run):
    paths = GetRepositoryPaths(loaded_repos)
    return runOnFolders(paths, function_to_run)

def __handleGitStatus(loaded_repos):
    dirty = runOnLoadedRepos(loaded_repos, getStatus)
    dirty = RemoveNone(dirty)

    message = "\nProject is: "  
    if dirty == None or len(dirty) == 0:
        message += ColorFormat(Colors.Green, "clean")
    else:
        message += ColorFormat(Colors.Red, "dirty ("+str(len(dirty))+": "+', '.join(dirty)+")")

    print(message)

def __handleGitResetHard(loaded_repos):
    runOnLoadedRepos(loaded_repos, Git.resetHard)

def __handleGitCleanUntracked(loaded_repos):
    runOnLoadedRepos(loaded_repos, Git.cleanUntracked)

def __handleGitCheckout(loaded_repos):
    if len(sys.argv) > 3:
        branch = sys.argv[3]
    else:
        branch = input("branch: ")

    runOnLoadedRepos(loaded_repos, checkoutBranch, {"branch":branch})

def __handleDirtyGitUpdate(path):
    runOnLoadedRepos(loaded_repos, fullDirtyUpdate)

def __handleCleanGitUpdate(path):
    runOnLoadedRepos(loaded_repos, fullCleanUpdate)

def __handleGlobalCommit(loaded_repos):
    if len(sys.argv) > 3:
        commit_message = sys.argv[3]
    else:
        commit_message = input("commit message: ")

    if commit_message == "":
        print("Commit message cannot be empty")
    else:
        runOnLoadedRepos(loaded_repos, globalCommit, {"commit_message":commit_message})

def __handleGlobalPush(loaded_repos):
    runOnLoadedRepos(loaded_repos, globalPush)

GitallOperations = {
    "1": [__handleGitStatus           , "Get status"],
    "2": [__handleGitResetHard        , "Fully reset/Clean"],
    "3": [__handleGitCleanUntracked   , "Clean untracked"],
    "4": [__handleGitCheckout         , "Checkout a branch where it exists"],
    "5": [__handleDirtyGitUpdate      , "Pull only the clean repos"],
    "6": [__handleCleanGitUpdate      , "Clean and Pull everything"],
    "7": [__handleGlobalCommit        , "Add, Commit and Local push"],
    "8": [__handleGlobalPush          , "Push to remote repositories"]
}

def printOptions():
    for key in GitallOperations:
        print("\t"+key+") "+GitallOperations[key][1])
    print("\t"+ColorFormat(Colors.Green, "Ctrl+C to exit"))

def runGitall(loaded_repos):
    option = None

    # What option to run
    if len(sys.argv) > 2:
        option = sys.argv[2]

    again = True
    while again:
        again = False
        if option == None:
            printOptions()
            option = input("Option:")

        if option in GitallOperations.keys():
            GitallOperations[option][0](loaded_repos)

        else:
            again = True
        option = None

        # If this script was called standalone and without arguments (assumed manual, )
        if len(sys.argv) == 2 and __name__ == "__main__":
            # An option was selected, print options again
            again = True

if __name__ == "__main__":
    print("Do not run this script as a standalone")
    sys.exit(0)

