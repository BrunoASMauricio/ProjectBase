import sys
from common import *
from git import *

def runOnAllGitRepos(path_to_dir, function_on_repo, list_arguments={}):
    global operation_status

    if not os.path.isdir(path_to_dir):
        logging.error(path_to_dir+" is not a valid directory")
        return

    cwd = os.getcwd()
    os.chdir(path_to_dir)

    if launchSilentProcess("find -maxdepth 1 -name .git")["stdout"] != "":
        function_on_repo(**list_arguments)
        sleep(0.05)

    os.chdir(cwd)

    for inode in os.listdir(path_to_dir):
        if os.path.isdir(path_to_dir+"/"+inode) and inode != ".git":
            runOnAllGitRepos(path_to_dir+"/"+inode, function_on_repo, list_arguments)

    return operation_status

def __handleGitStatus(path):
    dirty = runOnAllGitRepos(path, getStatus)

    message = "\nProject is: "  
    if dirty == None or dirty[0] == False:
        message += Fore.GREEN+"clean"+Style.RESET_ALL
    else:
        message += Fore.RED+"dirty ("+str(dirty[1])+" "+','.join(dirty[2])+")"+Style.RESET_ALL
    
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
    "7": [__handleGlobalCommit        , "Add and Push"],
    "8": [__handleGlobalPush          , "Push"]
}

def printOptions():
    for key in GitallOperations:
        print("\t"+key+") "+GitallOperations[key][1])
    print("\t"+Fore.GREEN+"Ctrl+C to exit"+Style.RESET_ALL)

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
        resetOperationStatus()
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

