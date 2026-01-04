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
from processes.repository import __RepoHasFlagSet, GetRepoIdFromURL
from processes.git     import GetAllGitRepos, GetRepoNameFromPath
from processes.git     import CheckIfStatusIsClean, CheckIfStatusIsDiverged, CheckIfStatusIsAhead, CheckIfStatusIsBehind, CheckIfStatusIsUpToDate
from processes.git     import GetAllCommits

from processes.repository import __RepoHasSomeFlagSet

from dataclasses import dataclass
@dataclass
class ProjectStatusInfo:
    repo_status: list[str]
    dirty: list[str]
    dirty_id: list[str]
    desynced: list[str]
    desynced_id: list[str]
    ahead_id: list[str]
    messages: list[str]


# Flags are the flags to check for before adding, or to check for before ignoring
def GetKnownAndUnknownGitRepos(flags_to_include=[],flags_to_exclude=[]):
    repos = Project.GetRepositories()
    known_paths = []
    for repo in repos:
        # Ignore if the repo does not contain an expected flag
        if len(flags_to_include) != 0 and not __RepoHasSomeFlagSet(repos[repo], flags_to_include):
            print("Ignored 1 "+str(repo))
            continue
        # Ignore if the repo contains a flag to ignore
        if len(flags_to_exclude) != 0 and __RepoHasSomeFlagSet(repos[repo], flags_to_exclude):
            print("Ignored 2 "+str(repo))
            continue
        known_paths.append(repos[repo]["repo source"])

    all_git_repos = GetAllGitRepos(Settings["paths"]["project main"])

    unknown_paths = [repo for repo in all_git_repos if repo not in known_paths]
    all_paths = known_paths + unknown_paths
    return all_paths, known_paths, unknown_paths

def RunOnAllRepos(callback, arguments={}):
    _, known_paths, _ = GetKnownAndUnknownGitRepos()
    return RunOnFolders(known_paths, callback, arguments)

def RunOnAllManagedRepos(callback, arguments={}):
    repos = Project.GetRepositories()
    known_paths   = [repos[repo]["repo source"] for repo in repos if False == __RepoHasFlagSet(repos[repo], "no commit")]

    return RunOnFolders(known_paths, callback, arguments)

def DirectlyManageSingleRepository():
    all_paths, known_paths, _ = GetKnownAndUnknownGitRepos()
    repos = Project.GetRepositories()

    dynamic_entries = []
    for path_ind in range(len(all_paths)):
        new_entry = []
        path = all_paths[path_ind]
        repo_url  = GetRepositoryUrl(path)
        repo_id   = GetRepoIdFromURL(repo_url)
        path = RemoveSequentialDuplicates(path, "/")

        status = GetRepoStatus(path)
        message = "\t"
        if CheckIfStatusIsClean(status):
            message += ColorFormat(Colors.Green, "(clean)")
        else:
            message += ColorFormat(Colors.Red, "(dirty)")

        message += "\t"

        if CheckIfStatusIsUpToDate(status):
            message += ColorFormat(Colors.Blue, "(synced)")
        else:
            message += ColorFormat(Colors.Red, "(desynced)")

        message += "\t"

        # Managed or Unmanaged
        if path in known_paths:
            message += ColorFormat(Colors.Yellow, " (managed)")
        else:
            message += ColorFormat(Colors.Magenta, " (unmanaged)")

        # Ignored or not
        if repo_id in repos.keys() and __RepoHasFlagSet(repos[repo_id], "no commit"):
            message += ColorFormat(Colors.Yellow, "(`no commit` flag set) ")

        # Print path (relative to cwd)
        message += " " + ColorFormat(Colors.Blue, GetRepoNameFromPath(path))
        message += " ." + path.replace(Settings["paths"]["project main"], "")
        # print(Message)
        new_entry = [message, OpenBashOnDirectoryAndWait, {"working_directory":all_paths[path_ind]}]
        dynamic_entries.append(new_entry)

    return dynamic_entries

def __AssembleReposStatusMessage(statuses)-> ProjectStatusInfo:
    status_message: str = ""
    dirty: list[str] = []
    dirty_id: list[str] = []
    desynced: list[str] = []
    desynced_id: list[str] = []

    ahead_id : list[str] = []

    repos = Project.GetRepositories()
    for path in statuses:
        status    = statuses[path]
        repo_url  = GetRepositoryUrl(path)
        repo_id   = GetRepoIdFromURL(repo_url)
        relevant_path = ColorFormat(Colors.Grey, f"(at {GetRelevantPath(path)})")
        repo_name : str = f"{GetRepoNameFromURL(repo_url)} {relevant_path}"

        status_message += "---"
        status_message += repo_name + " is "

        desynced.append(repo_name)
        desynced_id.append(repo_id)
        if CheckIfStatusIsDiverged(status):
            status_message += ColorFormat(Colors.Magenta, "diverged (fix manually)")
        elif CheckIfStatusIsAhead(status):
            ahead_id.append(repo_id)
            status_message += ColorFormat(Colors.Blue, "ahead (fix with sync push)")
        elif CheckIfStatusIsBehind(status):
            status_message += ColorFormat(Colors.Yellow, "behind (fix with sync pull)")
        else:
            status_message += ColorFormat(Colors.Green, "synced")
            desynced = desynced[:-1]
            desynced_id = desynced_id[:-1]

        status_message += " and "

        ignored = False

        if repo_id in repos.keys() and __RepoHasFlagSet(repos[repo_id], "no commit"):
            status_message += ColorFormat(Colors.Yellow, "(`no commit` flag set) ")
            ignored = True

        if CheckIfStatusIsClean(status):
            status_message += ColorFormat(Colors.Green, "clean")
        else:
            # Symptom of not having standardized way to identify repos
            # TODO: Remove this if after a proper ID is created/found
            if repo_id in repos.keys():

                status_message += ColorFormat(Colors.Red, "dirty ")

                if not ignored:
                    status_message += "\n" + CLICenterString(" " + ColorFormat(Colors.Red, repo_name), ColorFormat(Colors.Red, "="))
                    status_message += "\n\t" + path
                    status_message += "\n\t" + ColorFormat(Colors.Yellow, status).replace("\n", "\n\t") + "\n\n"
                    status_message += "\n" + CLICenterString("", ColorFormat(Colors.Red, "="))
                    dirty.append(repo_name)
                    dirty_id.append(repo_id)


        status_message +=  "\n"

    return ProjectStatusInfo(
        repo_status=statuses,
        dirty=dirty,
        dirty_id=dirty_id,
        desynced=desynced,
        desynced_id=desynced_id,
        ahead_id=ahead_id,
        messages = status_message,
    )


# Returns 
def getProjectStatusInfo():
    _, known_paths, unknown_paths = GetKnownAndUnknownGitRepos(flags_to_exclude="independent project")

    # Obtain status for known and unknown repos
    known_repo_status = RunOnFolders(known_paths, GetRepoStatus)
    known_repo_status = RemoveEmpty(known_repo_status)

    unknown_repo_status = RunOnFolders(unknown_paths, GetRepoStatus)
    unknown_repo_status = RemoveEmpty(unknown_repo_status)

    # Create and print status messa
    known_project_status = __AssembleReposStatusMessage(known_repo_status)
    unknown_project_status= __AssembleReposStatusMessage(unknown_repo_status)


    return known_project_status, unknown_project_status


def PrintProjectStatus():
    knownProjStat, unknownProjStatus = getProjectStatusInfo()

    if len(knownProjStat.messages) > 0:
        print(CLICenterString(" Known Repos ", ColorFormat(Colors.Yellow, "=")))
        print(f"\n{knownProjStat.messages}")
        print(CLICenterString("", ColorFormat(Colors.Yellow, "=")))

    if len(unknownProjStatus.messages) > 0:
        print()
        print(CLICenterString(" Unknown Repos ", ColorFormat(Colors.Yellow, "=")))
        print(f"\n{unknownProjStatus.messages}")
        print(CLICenterString("", ColorFormat(Colors.Yellow, "=")))

    # Print project status
    print()
    print(CLICenterString(ColorFormat(Colors.Cyan, "Project Status"), "="))

    def PrintDirty(message, repos):
        if len(repos) == 0:
            print(ColorFormat(Colors.Green, f"There are no {message} repos"))
        elif len(repos) == 1:
            print(ColorFormat(Colors.Red, f"There is 1 {message} repo: ") + repos[0])
        else:
            print(ColorFormat(Colors.Red, f"There are {len(repos)} {message} repos:") + "\n--" + '\n--'.join(repos))

    print("\n\tProject is ", end="")
    if len(knownProjStat.dirty) == 0 and len(unknownProjStatus.dirty) == 0:
        print(ColorFormat(Colors.Green, "clean"))
    else:
        print(ColorFormat(Colors.Red, "dirty"))
        PrintDirty("dirty managed", knownProjStat.dirty)
        PrintDirty("dirty unknown", unknownProjStatus.dirty)

    print("\n\tProject is ", end="")
    if len(knownProjStat.desynced) == 0 and len(unknownProjStatus.desynced) == 0:
        print(ColorFormat(Colors.Blue, "synced"))
    else:
        print(ColorFormat(Colors.Yellow, "desynced"))
        PrintDirty("desynced managed", knownProjStat.desynced)
        PrintDirty("desynced unknown", unknownProjStatus.desynced)

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

from data.settings import Settings
from menus.ci import RunCIScratch, RunCIType

def PushAll():
    
    if(not Settings.ci_was_runned):
        print("🔍 Running CI to check whether your changes break anything...")
        val = RunCIScratch(RunCIType.TOP)
        if(val != 0):
            print(
              "⚠️ CI checks failed. Push stopped.\n"
              "Retrying from the menu will let you push anyway.\n"
              "This is the part where you knowingly break CI.\n"
              "No judgment. (Okay, some judgment.)"
            )
            return
    if Settings.ci_was_runned_and_passed:
        print("✅ CI passed. Pushing all managed repositories...")
    else:
        print(
            "⚠️ CI did not pass, but the push was forced.\n"
            "Proceeding to push all managed repositories.\n"
            "May the CI gods forgive you."
        )
    RunOnAllManagedRepos(RepoPush)

TempCommitMessage = "==== Temporary ProjectBase save commit (to be squashed into a fixed commit) ===="

def __GetCurrentTemporaryCommits():
    global TempCommitMessage
    # Get all commits: 
    all_commits = RunOnAllManagedRepos(GetAllCommits)

    # Get initial commits in sequence that match temporary commit message
    temporary_commmits = {}
    for path in all_commits.keys():
        temporary_commmits[path] = []
        # We get the commits in a single multi line string
        all_commits[path] = all_commits[path].split('\n')

        for commit in all_commits[path]:
            hash, msg = commit.split(" ", 1)
            if TempCommitMessage != msg:
                break
            temporary_commmits[path].append(hash)

        if len(temporary_commmits[path]) == 0:
            del temporary_commmits[path]

    return temporary_commmits

def __CountTemporaryCommits(temporary_commmits):
    total = 0
    for path in temporary_commmits.keys():
        total += len(temporary_commmits[path])
    return total

def GlobalTemporaryCommit():
    global TempCommitMessage


    temporary_commmits = __GetCurrentTemporaryCommits()
    print(f"\nCurrent amount of temporary commits: {__CountTemporaryCommits(temporary_commmits)}")

    commit_message = f"{TempCommitMessage}"
    RunOnAllManagedRepos(RepoSaveChanges, {"commit_message":commit_message})

    temporary_commmits = __GetCurrentTemporaryCommits()
    print(f"\nNew amount of temporary commits: {__CountTemporaryCommits(temporary_commmits)}")

def GlobalFixedCommit():

    temp_commit_count = []

    try:
        temporary_commmits = __GetCurrentTemporaryCommits()
        temp_commit_count = __CountTemporaryCommits(temporary_commmits)
    finally:
        if temp_commit_count == 0:
            print("There are no temporary commits. Direct global commit message")
            commit_message = GetNextOption("[ fixed commit message ][<] ", True)
            RunOnAllManagedRepos(RepoSaveChanges, {"commit_message":commit_message})
            return

    paths = temporary_commmits.keys()
    status_message = f"\nMerging in {len(paths)} repositories"

    for path in paths:
        status_message += f"\n\t* {len(temporary_commmits[path])} commits from {path.split("/")[-1]}"

    print(status_message)
    commit_message = GetNextOption("[ fixed commit message ][<] ", True)
    print(commit_message)

    arguments = []
    for path in paths:
        arguments.append({"path": path, "commit_message": commit_message, "oldest_commit": temporary_commmits[path][-1]})

    RunOnFolders(paths, SquashUntilSpecifiedCommit, arguments)

def GetCurrentTemporaryCommits():
    temporary_commmits = __GetCurrentTemporaryCommits()
    paths = temporary_commmits.keys()

    if len(paths) > 0:
        status_message = f"\nTemporary commits found in {len(paths)} repositories"
        for path in paths:
            status_message += f"\n\t* {len(temporary_commmits[path])} commits from {path.split("/")[-1]}"
        print(status_message)
    else:
        print("\nNo temporary commits found")

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

