import sys

from common import *
from process import OpenBashOnDirectoryAndWait
from git import Git
from git import GetGitPaths, GetStatus, CheckoutBranch, FullDirtyUpdate
from git import FullCleanUpdate, GlobalCommit, GlobalPush, GetRepoNameFromPath

def runOnLoadedRepos(project, function_to_run):
    Paths = GetRepositoryPaths(project.LoadedRepos)
    return RunOnFolders(Paths, function_to_run)

def __handleGitStatus(project):
    KnownPaths = GetRepositoryPaths(project.LoadedRepos)
    AllPaths = GetGitPaths(project.Paths["project_main"])
    UnknownPaths = [repo for repo in AllPaths if repo not in KnownPaths]

    print("\nManaged repositories:")
    DirtyKnownRepos = RunOnFolders(KnownPaths, GetStatus)
    if IsEmptyOrNone(DirtyKnownRepos):
        print("\tNone")

    DirtyKnownRepos = RemoveNone(DirtyKnownRepos)

    print("\nUnmanaged repositories:")
    DirtyUnknownRepos = RunOnFolders(UnknownPaths, GetStatus)
    if IsEmptyOrNone(DirtyUnknownRepos):
        print("\tNone")

    DirtyUnknownRepos = RemoveNone(DirtyUnknownRepos)

    print("\nProject is ", end="")
    if IsEmptyOrNone(DirtyKnownRepos):
        print(ColorFormat(Colors.Green, "clean"))
    else:
        print(ColorFormat(Colors.Red, "dirty ("+str(len(DirtyKnownRepos))+": "+', '.join(DirtyKnownRepos)+")"))

    if not IsEmptyOrNone(DirtyUnknownRepos):
        print("There are dirty unknown git repositories:")
        print(ColorFormat(Colors.Red, "dirty ("+str(len(DirtyUnknownRepos))+": "+', '.join(DirtyUnknownRepos)+")"))


def __handleGitResetHard(Project):
    runOnLoadedRepos(Project.LoadedRepos, Git.ResetHard)

def __handleGitCleanUntracked(Project):
    runOnLoadedRepos(Project.LoadedRepos, Git.CleanUntracked)

def __handleGitCheckout(Project):
    if len(sys.argv) > 3:
        Branch = sys.argv[3]
    else:
        Branch = input("branch: ")

    runOnLoadedRepos(Project.LoadedRepos, CheckoutBranch, {"branch":Branch})

def __handleDirtyGitUpdate(Project):
    runOnLoadedRepos(Project.LoadedRepos, FullDirtyUpdate)

def __handleCleanGitUpdate(Project):
    runOnLoadedRepos(Project.LoadedRepos, FullCleanUpdate)

def __handleGlobalCommit(Project):
    if len(sys.argv) > 3:
        CommitMessage = sys.argv[3]
    else:
        CommitMessage = input("commit message: ")

    if CommitMessage == "":
        print("Commit message cannot be empty")
    else:
        runOnLoadedRepos(Project.LoadedRepos, GlobalCommit, {"commit_message":CommitMessage})

def __handleGlobalPush(project):
    runOnLoadedRepos(project.LoadedRepos, GlobalPush)

def __manageGitRepo(project):
    KnownPaths = GetRepositoryPaths(project.LoadedRepos)
    AllPaths = GetGitPaths(project.Paths["project_main"])
    UnknownPaths = [repo for repo in AllPaths if repo not in KnownPaths]
    AllPaths = KnownPaths + UnknownPaths

    print("What repo to manage:")
    CurrentDirectory = os.getcwd()
    for PathId in range(len(AllPaths)):
        Message =  "[" + str(PathId) + "] "
        Message += GetRepoNameFromPath(AllPaths[PathId]) + " ("

        os.chdir(AllPaths[PathId])
        if Git.IsRepositoryClean():
            Message += ColorFormat(Colors.Green, "clean")
        else:
            Message += ColorFormat(Colors.Red, "dirty")

        print(Message + ")")

    os.chdir(CurrentDirectory)
    UserInput = input("[<] ")
    OpenBashOnDirectoryAndWait(AllPaths[int(UserInput)])

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
    Option = None

    # What option to run
    if len(sys.argv) > 2:
        Option = sys.argv[2]

    again = True
    while again:
        again = False
        if Option == None:
            printOptions()
            Option = input("Option:")

        if Option in GitallOperations.keys():
            GitallOperations[Option][0](project)

        else:
            again = True
        Option = None

        # If this script was called standalone and without arguments (assumed manual, )
        if len(sys.argv) == 2 and __name__ == "__main__":
            # An option was selected, print options again
            again = True

if __name__ == "__main__":
    Abort("Do not run this script as a standalone")

