from data.settings     import Settings
from data.colors       import ColorFormat, Colors
from data.git import GetRepoNameFromURL
from data.common import RemoveEmpty, CLICenterString
from processes.project import Project
from processes.git     import GetAllGitRepos, GetRepoNameFromPath, RepoIsClean, CheckIfStatusIsClean
from processes.process import OpenBashOnDirectoryAndWait, RunOnFolders
from processes.git_operations import GetRepoStatus, GetRepositoryUrl, RepoCleanUntracked, RepoSaveChanges, RepoResetToLatestSync, RepoHardReset
from menus.menu import GetNextOption

def GetKnownAndUnknownGitRepos():
    repos = Project.GetRepositories()
    known_paths   = [repos[repo]["full worktree path"] for repo in repos]
    all_git_repos = GetAllGitRepos(Settings["paths"]["project main"])

    unknown_paths = [repo for repo in all_git_repos if repo not in known_paths]
    all_paths = known_paths + unknown_paths
    return all_paths, known_paths, unknown_paths

def RunOnAllManagedRepos(callback, arguments={}):
    _, known_paths, _ = GetKnownAndUnknownGitRepos()
    print(known_paths)
    return RunOnFolders(known_paths, callback, arguments)

def DirectlyManageSingleRepository():
    all_paths, known_paths, _ = GetKnownAndUnknownGitRepos()

    print("What repo to manage:")
    for path_ind in range(len(all_paths)):
        path = all_paths[path_ind]
        Message =  "[" + str(path_ind) + "] "
        Message += GetRepoNameFromPath(path) + " ("

        if RepoIsClean(path):
            Message += ColorFormat(Colors.Green, "clean")
        else:
            Message += ColorFormat(Colors.Red, "dirty")
        Message += ") "

        # Managed or Unmanaged
        if path in known_paths:
            Message += ColorFormat(Colors.Yellow, " (managed)")
        else:
            Message += ColorFormat(Colors.Magenta, " (unmanaged)")
        
        # Print path (relative to cwd)
        Message += "." + path.replace(Settings["paths"]["project main"], "")
        print(Message)

    UserInput = input("[<] ")
    OpenBashOnDirectoryAndWait(all_paths[int(UserInput)])

def __AssembleReposStatusMessage(statuses):
    status_message = ""
    dirty = 0
    for path in statuses:
        status    = statuses[path]
        repo_url  = GetRepositoryUrl(path)
        repo_name = GetRepoNameFromURL(repo_url)

        if CheckIfStatusIsClean(status):
            status_message += ColorFormat(Colors.Green, repo_name + " is clean") + "\n"
        else:
            status_message += "\n" + CLICenterString(" " + ColorFormat(Colors.Red, repo_name + " is dirty "), "=")
            status_message += "\n\t" +ColorFormat(Colors.Yellow, status).replace("\n", "\n\t") + "\n\n"
            status_message += "\n" + CLICenterString("", "=")
            dirty += 1
    return dirty, status_message

def PrintProjectStatus():
    _, known_paths, unknown_paths = GetKnownAndUnknownGitRepos()

    # print("\nManaged repositories:")
    known_repo_status = RunOnFolders(known_paths, GetRepoStatus)
    known_repo_status = RemoveEmpty(known_repo_status)

    # print("\nUnmanaged repositories:")
    unknown_repo_status = RunOnFolders(unknown_paths, GetRepoStatus)
    unknown_repo_status = RemoveEmpty(unknown_repo_status)

    known_dirty,   known_repos_message   = __AssembleReposStatusMessage(known_repo_status)
    unknown_dirty, unknown_repos_message = __AssembleReposStatusMessage(unknown_repo_status)

    if known_dirty == 0 and unknown_dirty == 0:
        print("\nProject is " + ColorFormat(Colors.Green, "clean"))
    else:
        print(ColorFormat(Colors.Red, "there are "+str(known_dirty)+" dirty managed repos"))
        print(known_repos_message)
        if unknown_dirty == 0:
            print(CLICenterString(" There are " + str(unknown_dirty) +" dirty unknown git repositories "))
        print(unknown_repos_message)

"""
Remove all uncommited (unsaved) files and folders
"""
def CleanAllUnsaved():
    RunOnAllManagedRepos(RepoCleanUntracked)

def UndoChanges():
    RunOnAllManagedRepos(RepoHardReset)

def GlobalSave():
    commit_message = GetNextOption("[commit message <] ")

    if commit_message == "":
        print("Commit message cannot be empty")
    else:

        try:
            RunOnAllManagedRepos(RepoSaveChanges, {"commit_message":commit_message})
        except:
            print("Unacceptable commit message")

def ResetToLatestSync():
    RunOnAllManagedRepos(RepoResetToLatestSync)

