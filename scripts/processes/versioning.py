from data.settings     import Settings
from data.colors       import ColorFormat, Colors
from data.common import RemoveEmpty, CLICenterString, RemoveSequentialDuplicates
from data.git import GetRepoNameFromURL
from processes.project import Project
from processes.git     import GetAllGitRepos, GetRepoNameFromPath, RepoIsClean, CheckIfStatusIsClean
from processes.process import OpenBashOnDirectoryAndWait, RunOnFolders
from processes.git_operations import RepoPull, RepoPush, RepoFetch, GetRepoStatus, GetRepositoryUrl, RepoCleanUntracked, RepoSaveChanges, RepoResetToLatestSync, RepoHardReset
from menus.menu import GetNextOption
from processes.repository import __RepoHasFlagSet

def GetKnownAndUnknownGitRepos():
    repos = Project.GetRepositories()
    known_paths   = [repos[repo]["repo path"] for repo in repos]
    all_git_repos = GetAllGitRepos(Settings["paths"]["project main"])

    unknown_paths = [repo for repo in all_git_repos if repo not in known_paths]
    all_paths = known_paths + unknown_paths
    return all_paths, known_paths, unknown_paths

def RunOnAllRepos(callback, arguments={}):
    _, known_paths, _ = GetKnownAndUnknownGitRepos()
    return RunOnFolders(known_paths, callback, arguments)

def RunOnAllManagedRepos(callback, arguments={}):
    repos = Project.GetRepositories()
    known_paths   = [repos[repo]["repo path"] for repo in repos if False == __RepoHasFlagSet(repos[repo], "no commit")]

    return RunOnFolders(known_paths, RepoPush, {})

def DirectlyManageSingleRepository():
    all_paths, known_paths, _ = GetKnownAndUnknownGitRepos()

    dynamic_entries = []
    for path_ind in range(len(all_paths)):
        new_entry = []
        path = all_paths[path_ind]
        path = RemoveSequentialDuplicates(path, "/")
        message =  " ("

        if RepoIsClean(path):
            message += ColorFormat(Colors.Green, "clean")
        else:
            message += ColorFormat(Colors.Red, "dirty")
        message += ") "

        # Managed or Unmanaged
        if path in known_paths:
            message += ColorFormat(Colors.Yellow, " (managed)")
        else:
            message += ColorFormat(Colors.Magenta, " (unmanaged)")
        
        # Print path (relative to cwd)
        message += " " + ColorFormat(Colors.Blue, GetRepoNameFromPath(path))
        message += " ." + path.replace(Settings["paths"]["project main"], "")
        # print(Message)
        new_entry = [message, OpenBashOnDirectoryAndWait, {"working_directory":all_paths[path_ind]}]
        dynamic_entries.append(new_entry)

    return dynamic_entries

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
            status_message += "\n\t" + path
            status_message += "\n\t" + ColorFormat(Colors.Yellow, status).replace("\n", "\n\t") + "\n\n"
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
    RunOnAllRepos(RepoCleanUntracked)

def UndoChanges():
    RunOnAllRepos(RepoHardReset)

def FetchAll():
    RunOnAllRepos(RepoFetch)

def PullAll():
    RunOnAllRepos(RepoPull)

def PushAll():
    RunOnAllManagedRepos(RepoPush)

def GlobalSave():
    commit_message = GetNextOption("[commit message <] ")

    if commit_message == "":
        print("Commit message cannot be empty")
    else:
        try:
            RunOnAllRepos(RepoSaveChanges, {"commit_message":commit_message})
        except:
            print("Unacceptable commit message")

def ResetToLatestSync():
    RunOnAllRepos(RepoResetToLatestSync)

