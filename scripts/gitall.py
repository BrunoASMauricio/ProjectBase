from time import sleep
import sys

from common import *
from git import *

def runOnAllGitRepos(path_to_dir, function_on_repo, list_arguments={}):
    operation_status = []

    if not os.path.isdir(path_to_dir):
        raise Exception(path_to_dir+" is not a valid directory")

    cwd = os.getcwd()
    os.chdir(path_to_dir)

    if launchSilentProcess("find -maxdepth 1 -name .git")["stdout"] != "":
        result = function_on_repo(**list_arguments)
        if result != None:
            operation_status.append(result)
        sleep(0.05)

    os.chdir(cwd)

    for inode in os.listdir(path_to_dir):
        if os.path.isdir(path_to_dir+"/"+inode) and inode != ".git":
            result_list = runOnAllGitRepos(path_to_dir+"/"+inode, function_on_repo, list_arguments)
            if len(result_list) > 0:
                operation_status = operation_status + result_list

    return operation_status

def __handleGitStatus(path):
    dirty = runOnAllGitRepos(path, getStatus)

    message = "\nProject is: "  
    if dirty == None or len(dirty) == 0:
        message += ColorFormat(Colors.Green, "clean")
    else:
        message += ColorFormat(Colors.Red, "dirty ("+str(len(dirty))+": "+', '.join(dirty)+")")
    
    print(message)

def __handleGitResetHard(path):
    runOnAllGitRepos(path, Git.resetHard)

def __handleGitCleanUntracked(path):
    runOnAllGitRepos(path, Git.cleanUntracked)

def __handleGitCheckout(path):
    if len(sys.argv) > 3:
        branch = sys.argv[3]
    else:
        branch = input("branch: ")

    runOnAllGitRepos(path, checkoutBranch, {"branch":branch})

def __handleDirtyGitUpdate(path):
    runOnAllGitRepos(path, fullDirtyUpdate)

def __handleCleanGitUpdate(path):
    runOnAllGitRepos(path, fullCleanUpdate)

def __handleGlobalCommit(path):
    if len(sys.argv) > 3:
        commit_message = sys.argv[3]
    else:
        commit_message = input("commit message: ")

    if commit_message == "":
        print("Commit message cannot be empty")
    else:
        runOnAllGitRepos(path, globalCommit, {"commit_message":commit_message})

def __handleGlobalPush(path):
    runOnAllGitRepos(path, globalPush)

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

def runGitall(path):
    if path[-1] == "/":
        path = path[:-1]

    path = os.path.abspath(path)

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
            GitallOperations[option][0](path)

        else:
            again = True
        option = None

        # If this script was called standalone and without arguments (assumed manual, )
        if len(sys.argv) == 2 and __name__ == "__main__":
            # An option was selected, print options again
            again = True

if __name__ == "__main__":
    # What path to run it in
    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        path = input("path to project directory: ")

    runGitall(path)

