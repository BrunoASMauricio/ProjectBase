from data.settings     import Settings, SetBranch
from data.colors       import ColorFormat, Colors
from data.common import RemoveEmpty, CLICenterString, RemoveSequentialDuplicates, AssembleTable
from data.git import GetRepoNameFromURL, IsValidGitBranch
from processes.project import Project, GetRelevantPath
from processes.process import OpenBashOnDirectoryAndWait, RunOnFolders
from processes.git_operations import *
from menus.menu import GetNextInput
from processes.git     import *
from processes.repository import __RepoHasFlagSet, GetRepoIdFromURL, __RepoHasSomeFlagSet
from data.common import YES_NO_PROMPT, UserYesNoChoice

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


"""
Create a list of all unique branches from the provided per repository branches
Effectively invert the dictionary. Instead of being branches per repo, make them repos per branch
"""
def GetBranches(repo_branches):
    def AddReposToBranch(branches, repo, lst):
        for branch in branches:
            if branch not in lst:
                lst[branch] = []
            if repo not in lst[branch]:
                lst[branch].append(repo)
        return lst

    branches = {}

    for repo, state in repo_branches.items():
        repo_name = ColorFormat(Colors.Yellow, GetRepoNameFromURL(repo))

        for branch_type in state.keys():
            repo_branches = state[branch_type]
            if branch_type not in branches:
                branches[branch_type] = {}
            branches[branch_type] = AddReposToBranch(repo_branches, repo_name, branches[branch_type])
    return branches

# Flags are the flags to check for before adding, or to check for before ignoring
def GetKnownAndUnknownGitRepos(flags_to_include=[],flags_to_exclude=[]):
    repos = Project.GetRepositories()
    known_paths = []
    for repo in repos:
        # Ignore if the repo does not contain an expected flag
        if len(flags_to_include) != 0 and not __RepoHasSomeFlagSet(repos[repo], flags_to_include):
            continue
        # Ignore if the repo contains a flag to ignore
        if len(flags_to_exclude) != 0 and __RepoHasSomeFlagSet(repos[repo], flags_to_exclude):
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


def SelectBranch(branches, callback):
    repo_branches = RunOnAllManagedRepos(GetAllRepoBranches)
    repo_branches = GetBranches(repo_branches)[branches]

    dynamic_entries = []
    branch_names = list(repo_branches.keys())
    for branch_name in branch_names:
        new_entry = [branch_name, callback, {"branch_name":branch_name}]
        dynamic_entries.append(new_entry)

    return dynamic_entries

def DeleteLocalBranch(branch_name):
    repo_branches = RunOnAllManagedRepos(GetAllRepoBranches)
    repo_branches = GetBranches(repo_branches)["checkedout"]

    # Check if the branch is checked out anywhere
    for branch in repo_branches.keys():
        if BranchesMatch(branch_name, branch):
            PrintWarning(f"\nBranch {branch_name} is already checked out in: ", end=" ")
            for repo in repo_branches[branch_name]:
                print(repo, end=" ")
            print("\n")
            PrintError(ColorFormat(Colors.Red, "\nCannot delete. Please check out a different branch and then retry"))
            return

    # Check if there is any repo with that branch currently checked out
    RunOnAllManagedRepos(GitDeleteLocalBranch, {"branch_name": branch_name})
    
def SelectLocalBranchToDelete():
    return SelectBranch("locals", DeleteLocalBranch)



def DeleteRemoteBranch(branch_name):
    RunOnAllManagedRepos(GitDeleteRemoteBranch, {"branch_name": branch_name})

def SelectRemoteBranchToDelete():
    return SelectBranch("remotes", DeleteRemoteBranch)


def SwitchBranch(branch_name):
    SetBranch(branch_name)
    RunOnAllManagedRepos(GitCheckoutBranch, {"new_branch": branch_name})

def SelectBranchToCheckout():
    return SelectBranch("locals", SwitchBranch)


MANUAL_INTERVENTION_MSG = f"There was an issue that might require manual intervention!!"
from data.common import PrintError, PrintWarning

def __AbortRebaseOrMerge(outputs, operation):
    for path, output in outputs.items():
        if output.error_nessage != None:
            if operation == "rebase":
                if CheckRebaseOperationConflict(output.returned["out"]):
                    GitRebaseOrMergeAbort(path, operation)
            else:
                if CheckMergeOperationConflict(output.returned["out"]):
                    GitRebaseOrMergeAbort(path, operation)
            print(f"Reverted {path}")

def _RebaseOrMergeBranch(branch_name, operation):
    # Check if all status are ok
    statuses = RunOnAllManagedRepos(GetRepoStatus)
    bad_stats = []
    for path, status in statuses.items():
        if CheckIfStatusIsClean(status) == False:
            bad_stats.append(path)

    if len(bad_stats) != 0:
        print(f"Cannot {operation}. Status not clean in {', '.join(bad_stats)}")
        return

    if operation == "rebase":
        outputs = RunOnAllManagedRepos(GitRebaseBranch, {"branch_to_rebase": branch_name})
    elif operation == "merge":
        outputs = RunOnAllManagedRepos(GitMergeBranch, {"branch_to_merge": branch_name})
    else:
        raise Exception(f"Uknown operation {operation}")

    issue = False
    for path, output in outputs.items():
        if output.error_nessage != None:
            issue = True

    if issue:
        print("\n"+ColorFormat(Colors.Red, MANUAL_INTERVENTION_MSG))
        print(f"Do you want to revert the conflicting changes? {YES_NO_PROMPT}")
        answer = GetNextInput()
        if UserYesNoChoice(answer, True):
            __AbortRebaseOrMerge(outputs, operation)
            Printnotice(f"{operation} with branch {branch_name} completed with success")
        else:
            PrintWarning(f"{operation} with branch {branch_name} completed with issues")
    else:
        PrintNotice(f"\n{operation} with branch {branch_name} completed with success")

def MergeBranch(branch_name):
    _RebaseOrMergeBranch(branch_name, "merge")

def SelectBranchToMerge():
    return SelectBranch("locals", MergeBranch)

def RebaseBranch(branch_name):
    _RebaseOrMergeBranch(branch_name, "rebase")

def SelectBranchToRebase():
    return SelectBranch("locals", RebaseBranch)

def GetFilesDiff():
    results = RunOnAllRepos(GetGitFileDiff)
    for path, diff in results.items():
        if len(diff) > 1:
            print(CLICenterString(path))
            print(diff)

def GetDiff():
    results = RunOnAllRepos(GetGitDiff)
    for path, diff in results.items():
        if len(diff) > 1:
            print(CLICenterString(path))
            print(diff)

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
            if CheckIfStatusIsUpToDate(status):
                status_message += ColorFormat(Colors.Green, "synced")
            else:
                status_message += ColorFormat(Colors.Red, "desynced (unknown reason)")
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

def CheckoutBranch():
    branch = GetNextInput("New branch name: ")
    while IsValidGitBranch(branch) == False:
        print("Invalid git branch")
        branch = GetNextInput("New branch name: ")

    repo_branches = RunOnAllManagedRepos(GitCheckoutBranch, {"new_branch": branch})
    SetBranch(branch)


def PrintAllBranches():
    repo_branches = RunOnAllManagedRepos(GetAllRepoBranches)
    # There is a high likelihood that the same branches will be present on multiple repos
    # Print by branch and not by repo
    repo_branches = GetBranches(repo_branches)

    def PrintBranches(branches):
        for branch, repos in branches.items():
            print(f"{branch}: {', '.join(sorted (repos))}")

    print(CLICenterString(" Checkedout branches ", ColorFormat(Colors.Blue, "=")))
    PrintBranches(repo_branches["checkedout"])

    print(CLICenterString(" Local branches ", ColorFormat(Colors.Blue, "=")))
    PrintBranches(repo_branches["locals"])

    # TODO: Print if remote has been pushed or not
    print(CLICenterString(" Remote/Tracked branches ", ColorFormat(Colors.Magenta, "=")))
    PrintBranches(repo_branches["remotes"])

    if len(repo_branches["not pushed"]) != 0:
        print(CLICenterString(" Non pushed branches ", ColorFormat(Colors.Red, "=")))
        print("These branches require a push to be properly set remotely")
        PrintBranches(repo_branches["not pushed"])


def PrintCheckedoutState():
    repo_branches = RunOnAllManagedRepos(GetAllRepoBranches)
    print(CLICenterString(" Repository state ", ColorFormat(Colors.Yellow, "=")))

    rows = []
    for repo, state in repo_branches.items():
        local_branch = state["checkedout"][0]
        # Remove unique naming for managed branches
        local_branch = ColorFormat(Colors.Cyan, local_branch)

        remote_branch = state["remote"][0]
        remote_branch = ColorFormat(Colors.Magenta, remote_branch)

        status = ""
        if not CheckIfStatusIsClean(state["status"]):
            status = ColorFormat(Colors.Red, "DIRTY")

        repo_name = ColorFormat(Colors.Yellow, GetRepoNameFromURL(repo))

        rows.append([status, repo_name, local_branch, remote_branch])

    print(AssembleTable(rows, headers=["Status", "Repo", "Local", "Remote"]))

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
            commit_message = GetNextInput("[ fixed commit message ][<] ", True)
            RunOnAllManagedRepos(RepoSaveChanges, {"commit_message":commit_message})
            return

    paths = temporary_commmits.keys()
    status_message = f"\nMerging in {len(paths)} repositories"

    for path in paths:
        status_message += f"\n\t* {len(temporary_commmits[path])} commits from {path.split("/")[-1]}"

    print(status_message)
    commit_message = GetNextInput("[ fixed commit message ][<] ", True)
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
    commit_message = GetNextInput("[commit message <] ")

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

