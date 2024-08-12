import sys

from common import *
from process import OpenBashOnDirectoryAndWait
from git import Git
from git import GetGitPaths, GetStatus, CheckoutBranch, FullDirtyUpdate
from git import FullCleanUpdate, GlobalCommit, GlobalPush, GetRepoNameFromPath

def runOnLoadedRepos(LoadedRepos, function_to_run, ListArguments={}):
    Paths = GetRepositoryPaths(LoadedRepos)
    return RunOnFolders(Paths, function_to_run, ListArguments)

def __handleFetch(Project):
    runOnLoadedRepos(Project.LoadedRepos, Git.Fetch)

def __handleGitResetHard(Project):
    runOnLoadedRepos(Project.LoadedRepos, Git.ResetHard)

def __handleGitCleanUntracked(Project):
    runOnLoadedRepos(Project.LoadedRepos, Git.CleanUntracked)

def __handleGitCheckout(Project):
    if len(sys.argv) > 3:
        Branch = sys.argv[3]
    else:
        Branch = input("branch: ")

    runOnLoadedRepos(Project.LoadedRepos, CheckoutBranch, {"Branch":Branch})

def __handleDirtyGitUpdate(Project):
    runOnLoadedRepos(Project.LoadedRepos, FullDirtyUpdate)

def __handleCleanGitUpdate(Project):
    runOnLoadedRepos(Project.LoadedRepos, FullCleanUpdate)

def __handleGlobalPush(project):
    runOnLoadedRepos(project.LoadedRepos, GlobalPush)

def __manageGitRepo(project):
    KnownPaths = GetRepositoryPaths(project.LoadedRepos)
    AllPaths = GetGitPaths(project.Paths["project main"])
    UnknownPaths = [repo for repo in AllPaths if repo not in KnownPaths]
    AllPaths = KnownPaths + UnknownPaths

    print("What repo to manage:")
    CurrentDirectory = os.getcwd()
    for PathId in range(len(AllPaths)):
        Path = AllPaths[PathId]
        Message =  "[" + str(PathId) + "] "
        Message += GetRepoNameFromPath(Path) + " ("

        sys.exit(0)
        os.chdir(Path)
        if Git.IsRepositoryClean():
            Message += ColorFormat(Colors.Green, "clean")
        else:
            Message += ColorFormat(Colors.Red, "dirty")
        Message += ") "

        # Managed or Unmanaged
        if Path in KnownPaths:
            Message += ColorFormat(Colors.Yellow, " (managed)")
        else:
            Message += ColorFormat(Colors.Magenta, " (unmanaged)")
        
        # Print path (relative to cwd)
        Message += "." + Path.replace(project.Paths["project main"], "")
        print(Message)

    sys.exit(0)
    os.chdir(CurrentDirectory)
    UserInput = input("[<] ")
    OpenBashOnDirectoryAndWait(AllPaths[int(UserInput)])
