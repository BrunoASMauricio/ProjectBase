from data.settings     import Settings
from data.colors       import ColorFormat, Colors
from data.common import RemoveEmpty, CLICenterString, RemoveSequentialDuplicates
from data.git import GetRepoNameFromURL, FlipUrl
from processes.project import Project, GetRelevantPath
from processes.process import OpenBashOnDirectoryAndWait, RunOnFolders
from processes.git_operations import RepoPull, RepoPush, RepoFetch, GetRepoStatus, GetRepositoryUrl
from processes.git_operations import RepoCleanUntracked, RepoSaveChanges, RepoResetToLatestSync, RepoHardReset
from processes.git_operations import SquashUntilSpecifiedCommit
from menus.menu import GetNextOption
from processes.repository import __RepoHasFlagSet
from processes.git     import GetAllGitRepos, GetRepoNameFromPath, RepoIsClean
from processes.git     import CheckIfStatusIsClean, CheckIfStatusIsDiverged, CheckIfStatusIsAhead, CheckIfStatusIsBehind
from processes.git     import GetAllCommits

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

    return RunOnFolders(known_paths, callback, arguments)

def DirectlyManageSingleRepository():
    all_paths, known_paths, _ = GetKnownAndUnknownGitRepos()

    dynamic_entries = []
    for path_ind in range(len(all_paths)):
        new_entry = []
        path = all_paths[path_ind]
        path = RemoveSequentialDuplicates(path, "/")

        message = "\t"
        if RepoIsClean(path):
            message += ColorFormat(Colors.Green, "(clean)")
        else:
            message += ColorFormat(Colors.Red, "(dirty)")

        message += "\t"

        if RepoIsClean(path):
            message = ColorFormat(Colors.Blue, "(synced)")
        else:
            message = ColorFormat(Colors.Red, "(desynced)")

        message += "\t"

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
    dirty = []
    desynced = []
    repos = Project.GetRepositories()
    for path in statuses:
        status    = statuses[path]
        repo_url  = GetRepositoryUrl(path)
        relevant_path = ColorFormat(Colors.Grey, f"(at {GetRelevantPath(path)})")
        repo_name = f"{GetRepoNameFromURL(repo_url)} {relevant_path}"

        status_message += "---"
        status_message += repo_name + " is "

        if CheckIfStatusIsDiverged(status):
            status_message += ColorFormat(Colors.Magenta, "diverged (fix manually)")
            desynced.append(repo_name)
        elif CheckIfStatusIsAhead(status):
            status_message += ColorFormat(Colors.Blue, "ahead (fix with sync push)")
            desynced.append(repo_name)
        elif CheckIfStatusIsBehind(status):
            status_message += ColorFormat(Colors.Yellow, "behind (fix with sync pull)")
            desynced.append(repo_name)
        else:
            status_message += ColorFormat(Colors.Green, "synced")

        status_message += " and "
        if CheckIfStatusIsClean(status):
            status_message += ColorFormat(Colors.Green, "clean")
        else:
            # Symptom of not having standardized way to identify repos
            # TODO: Remove this if after a proper ID is created/found
            if FlipUrl(repo_url) in repos.keys():
                repo_url = FlipUrl(repo_url)

            if repo_url in repos.keys() and __RepoHasFlagSet(repos[repo_url], "no commit"):
                    status_message += ColorFormat(Colors.Red, "dirty (with `no commit` flag set) ")
            else:
                status_message += ColorFormat(Colors.Red, "dirty ")

            status_message += "\n" + CLICenterString(" " + ColorFormat(Colors.Red, repo_name), ColorFormat(Colors.Red, "="))
            status_message += "\n\t" + path
            status_message += "\n\t" + ColorFormat(Colors.Yellow, status).replace("\n", "\n\t") + "\n\n"
            status_message += "\n" + CLICenterString("", ColorFormat(Colors.Red, "="))
            dirty.append(repo_name)


        status_message +=  "\n"

    return dirty, desynced, status_message

def PrintProjectStatus():
    _, known_paths, unknown_paths = GetKnownAndUnknownGitRepos()

    # Obtain status for known and unknown repos
    known_repo_status = RunOnFolders(known_paths, GetRepoStatus)
    known_repo_status = RemoveEmpty(known_repo_status)

    unknown_repo_status = RunOnFolders(unknown_paths, GetRepoStatus)
    unknown_repo_status = RemoveEmpty(unknown_repo_status)

    # Create and print status messages
    known_dirty,   known_desynced_repos, known_repos_message   = __AssembleReposStatusMessage(known_repo_status)
    unknown_dirty, unknown_desynced_repos, unknown_repos_message = __AssembleReposStatusMessage(unknown_repo_status)

    if len(known_repos_message) > 0:
        print(CLICenterString(" Known Repos ", ColorFormat(Colors.Yellow, "=")))
        print(f"\n{known_repos_message}")
        print(CLICenterString("", ColorFormat(Colors.Yellow, "=")))

    if len(unknown_repos_message) > 0:
        print()
        print(CLICenterString(" Unknown Repos ", ColorFormat(Colors.Yellow, "=")))
        print(f"\n{unknown_repos_message}")
        print(CLICenterString("", ColorFormat(Colors.Yellow, "=")))

    # Print project status
    print()
    print(CLICenterString(ColorFormat(Colors.Cyan, "Project Status"), "="))

    def PrintDirty(message, repos):
        if len(repos) == 0:
            print(ColorFormat(Colors.Green, f"There are no {message} repos"))
        elif len(repos) == 1:
            print(ColorFormat(Colors.Red, f"There is 1 {message} repo: " + repos[0]))
        else:
            print(ColorFormat(Colors.Red, f"There are {len(repos)} {message} repos:") + "\n--" + '\n--'.join(repos))

    final_message =  "\nProject is "
    if len(known_dirty) == 0 and len(unknown_dirty) == 0:
        final_message += ColorFormat(Colors.Green, "clean")
    else:
        final_message += ColorFormat(Colors.Red, "dirty")

    final_message += " and "
    if len(known_desynced_repos) == 0 and len(unknown_desynced_repos) == 0:
        final_message += ColorFormat(Colors.Blue, "synced")
    else:
        final_message += ColorFormat(Colors.Yellow, "desynced")
    print(final_message)

    PrintDirty("dirty managed", known_dirty)
    PrintDirty("dirty unknown", unknown_dirty)
    PrintDirty("desynced managed", known_desynced_repos)
    PrintDirty("desynced unknown", unknown_desynced_repos)


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

TempCommitMessage = "==== Temporary ProjectBase save commit (to be squashed into a fixed commit) ===="
def GlobalTemporaryCommit():
    global TempCommitMessage
    commit_message = f"{TempCommitMessage}"
    RunOnAllManagedRepos(RepoSaveChanges, {"commit_message":commit_message})

def GlobalFixedCommit():
    global TempCommitMessage
    # Get all commits: 
    all_commits = RunOnAllManagedRepos(GetAllCommits)

    # Get initial commits in sequence that match temporary commit message
    matching_commits = {}
    for path in all_commits.keys():
        matching_commits[path] = []
        # We get the commits in a single multi line string
        all_commits[path] = all_commits[path].split('\n')

        for commit in all_commits[path]:
            hash, msg = commit.split(" ", 1)
            if TempCommitMessage != msg:
                break
            matching_commits[path].append(hash)

        if len(matching_commits[path]) == 0:
            del matching_commits[path]

    paths = matching_commits.keys()
    status_message = f"\nMerging in {len(paths)} repositories"
    for path in paths:
        status_message += f"\n\t* {len(matching_commits[path])} commits from {path.split("/")[-1]}"

    print(status_message)
    commit_message = GetNextOption("[ fixed commit message ][<] ")

    arguments = []
    for path in paths:
        arguments.append({"commit_message": commit_message, "oldest_commit": matching_commits[path][-1]})

    RunOnFolders(paths, SquashUntilSpecifiedCommit, arguments)
    # RunOnAllManagedRepos(RepoSaveChanges, {"commit_message":commit_message})

def GlobalSave():
    commit_message = GetNextOption("[commit message <] ")

    if commit_message == "":
        print("Commit message cannot be empty")
    else:
        try:
            RunOnAllManagedRepos(RepoSaveChanges, {"commit_message":commit_message})
        except Exception as ex:
            print("Unacceptable commit message: "+str(ex))
            import sys
            sys.exit(0)

def ResetToLatestSync():
    RunOnAllRepos(RepoResetToLatestSync)

