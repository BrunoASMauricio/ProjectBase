import sys

from common import *
from process import openBashOnDirectoryAndWait
from git import Git
from git import GetGitPaths, getStatus, checkoutBranch, fullDirtyUpdate
from git import fullCleanUpdate, globalCommit, globalPush, getRepoNameFromPath

def runOnLoadedRepos(project, function_to_run):
    paths = GetRepositoryPaths(project.loaded_repos)
    return runOnFolders(paths, function_to_run)

def __handleGitStatus(project):
    known_paths = GetRepositoryPaths(project.loaded_repos)
    all_paths = GetGitPaths(project.paths["project_main"])
    unknown_paths = [repo for repo in all_paths if repo not in known_paths]

    print("\nManaged repositories:")
    dirty_known_repos = runOnFolders(known_paths, getStatus)
    if IsEmptyOrNone(dirty_known_repos):
        print("\tNone")

    dirty_known_repos = RemoveNone(dirty_known_repos)

    print("\nUnmanaged repositories:")
    dirty_unknown_repos = runOnFolders(unknown_paths, getStatus)
    if IsEmptyOrNone(dirty_unknown_repos):
        print("\tNone")

    dirty_unknown_repos = RemoveNone(dirty_unknown_repos)

    print("\nProject is ", end="")
    if IsEmptyOrNone(dirty_known_repos):
        print(ColorFormat(Colors.Green, "clean"))
    else:
        print(ColorFormat(Colors.Red, "dirty ("+str(len(dirty_known_repos))+": "+', '.join(dirty_known_repos)+")"))

    if not IsEmptyOrNone(dirty_unknown_repos):
        print("There are dirty unknown git repositories:")
        print(ColorFormat(Colors.Red, "dirty ("+str(len(dirty_unknown_repos))+": "+', '.join(dirty_unknown_repos)+")"))


def __handleGitResetHard(project):
    runOnLoadedRepos(project.loaded_repos, Git.resetHard)

def __handleGitCleanUntracked(project):
    runOnLoadedRepos(project.loaded_repos, Git.cleanUntracked)

def __handleGitCheckout(project):
    if len(sys.argv) > 3:
        branch = sys.argv[3]
    else:
        branch = input("branch: ")

    runOnLoadedRepos(project.loaded_repos, checkoutBranch, {"branch":branch})

def __handleDirtyGitUpdate(project):
    runOnLoadedRepos(project.loaded_repos, fullDirtyUpdate)

def __handleCleanGitUpdate(project):
    runOnLoadedRepos(project.loaded_repos, fullCleanUpdate)

def __handleGlobalCommit(project):
    if len(sys.argv) > 3:
        commit_message = sys.argv[3]
    else:
        commit_message = input("commit message: ")

    if commit_message == "":
        print("Commit message cannot be empty")
    else:
        runOnLoadedRepos(project.loaded_repos, globalCommit, {"commit_message":commit_message})

def __handleGlobalPush(project):
    runOnLoadedRepos(project.loaded_repos, globalPush)

def __manageGitRepo(project):
    known_paths = GetRepositoryPaths(project.loaded_repos)
    all_paths = GetGitPaths(project.paths["project_main"])
    unknown_paths = [repo for repo in all_paths if repo not in known_paths]
    all_paths = known_paths + unknown_paths

    print("What repo to manage:")
    cwd = os.getcwd()
    for path_id in range(len(all_paths)):
        msg =  "[" + str(path_id) + "] "
        msg += getRepoNameFromPath(all_paths[path_id]) + " ("

        os.chdir(all_paths[path_id])
        if Git.isRepositoryClean():
            msg += ColorFormat(Colors.Green, "clean")
        else:
            msg += ColorFormat(Colors.Red, "dirty")

        print(msg + ")")

    os.chdir(cwd)
    user_input = input(": ")
    openBashOnDirectoryAndWait(all_paths[int(user_input)])

GitallOperations = {
    "0": [__manageGitRepo             , "Manage single repo"],
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

def runGitall(project):
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
            GitallOperations[option][0](project)

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

