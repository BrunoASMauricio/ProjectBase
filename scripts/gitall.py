import sys

from common import *
from git import *

def __handleGitStatus(paths):
    dirty = runOnFolders(paths, getStatus)
    dirty = RemoveNone(dirty)

    message = "\nProject is: "  
    if dirty == None or len(dirty) == 0:
        message += ColorFormat(Colors.Green, "clean")
    else:
        message += ColorFormat(Colors.Red, "dirty ("+str(len(dirty))+": "+', '.join(dirty)+")")

    print(message)

def __handleGitResetHard(paths):
    runOnFolders(paths, Git.resetHard)

def __handleGitCleanUntracked(paths):
    runOnFolders(paths, Git.cleanUntracked)

def __handleGitCheckout(paths):
    if len(sys.argv) > 3:
        branch = sys.argv[3]
    else:
        branch = input("branch: ")

    runOnFolders(paths, checkoutBranch, {"branch":branch})

def __handleDirtyGitUpdate(path):
    runOnFolders(paths, fullDirtyUpdate)

def __handleCleanGitUpdate(path):
    runOnFolders(paths, fullCleanUpdate)

def __handleGlobalCommit(paths):
    if len(sys.argv) > 3:
        commit_message = sys.argv[3]
    else:
        commit_message = input("commit message: ")

    if commit_message == "":
        print("Commit message cannot be empty")
    else:
        runOnFolders(paths, globalCommit, {"commit_message":commit_message})

def __handleGlobalPush(paths):
    runOnFolders(paths, globalPush)

GitallOperations = {
    "1": [__handleGitStatus           , "Get status"],
    "2": [__handleGitResetHard        , "Fully reset/Clean"],
    "3": [__handleGitCleanUntracked   , "Clean untracked"],
    "4": [__handleGitCheckout         , "Checkout a branch where it exists"],
    "5": [__handleDirtyGitUpdate      , "Pull only the clean repos"],
    "6": [__handleCleanGitUpdate      , "Clean and Pull everything"],
    "7": [__handleGlobalCommit        , "Add and Commit"],
    "8": [__handleGlobalPush          , "Push"]
}

def printOptions():
    for key in GitallOperations:
        print("\t"+key+") "+GitallOperations[key][1])
    print("\t"+ColorFormat(Colors.Green, "Ctrl+C to exit"))

def runGitall(paths):
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
            GitallOperations[option][0](paths)

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

