import os

from data.settings     import Settings, SetBranch
from data.colors       import ColorFormat, Colors
from data.common import RemoveEmpty, CLICenterString, RemoveSequentialDuplicates, AssembleTable, YES_NO_PROMPT, UserYesNoChoice
from data.git import GetRepoNameFromURL, IsValidGitBranch
from processes.project import Project, GetRelevantPath
from processes.process import OpenBashOnDirectoryAndWait, RunOnFolders, LaunchPager
from processes.git_operations import *
from menus.menu import GetNextInput
from processes.git_operations import *
from processes.repository import __RepoHasFlagSet, GetRepoIdFromPath, __RepoHasSomeFlagSet
from data.print import *

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
def OrganizeBranches(repo_branches):
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
    repo_branches = OrganizeBranches(repo_branches)[branches]

    dynamic_entries = []
    branch_names = list(repo_branches.keys())
    for branch_name in branch_names:
        new_entry = [branch_name, callback, {"branch_name":branch_name}]
        dynamic_entries.append(new_entry)

    return dynamic_entries

def DeleteLocalBranch(branch_name):
    repo_branches = RunOnAllManagedRepos(GetAllRepoBranches)
    repo_branches = OrganizeBranches(repo_branches)["checkedout"]

    # Check if the branch is checked out anywhere
    for branch in repo_branches.keys():
        if BranchesMatch(branch_name, branch):
            msg = f"\nBranch {branch_name} is already checked out in: "
            for repo in repo_branches[branch_name]:
                msg += repo + " "
            PrintWarning(msg)
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
        if output.error_nessage is not None:
            if operation == "rebase":
                if CheckRebaseOperationConflict(output.returned["out"]):
                    GitRebaseOrMergeAbort(path, operation)
            else:
                if CheckMergeOperationConflict(output.returned["out"]):
                    GitRebaseOrMergeAbort(path, operation)
            PrintInfo(f"Reverted {path}")

def _RebaseOrMergeBranch(branch_name, operation):
    # Check if all status are ok
    statuses = RunOnAllManagedRepos(GetRepoStatus)
    bad_stats = []
    for path, status in statuses.items():
        if CheckIfStatusIsClean(status) is False:
            bad_stats.append(path)

    if len(bad_stats) != 0:
        PrintWarning(f"Cannot {operation}. Status not clean in {', '.join(bad_stats)}")
        return

    if operation == "rebase":
        outputs = RunOnAllManagedRepos(GitRebaseBranch, {"branch_to_rebase": branch_name})
    elif operation == "merge":
        outputs = RunOnAllManagedRepos(GitMergeBranch, {"branch_to_merge": branch_name})
    else:
        raise Exception(f"Uknown operation {operation}")

    issue = False
    for path, output in outputs.items():
        if output.error_nessage is not None:
            issue = True

    if issue:
        msg = f"\n{ColorFormat(Colors.Red, MANUAL_INTERVENTION_MSG)}\nDo you want to revert the conflicting changes? {YES_NO_PROMPT}"
        PrintNotice(msg)
        answer = GetNextInput()
        if UserYesNoChoice(answer, True):
            __AbortRebaseOrMerge(outputs, operation)
            PrintInfo(f"{operation} with branch {branch_name} completed with success")
        else:
            PrintWarning(f"{operation} with branch {branch_name} completed with issues")
    else:
        PrintInfo(f"\n{operation} with branch {branch_name} completed with success")

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
            PrintInfo(CLICenterString(path))
            PrintInfo(diff)

def GetDiff():
    results = RunOnAllManagedRepos(GetGitDiff)
    msg = ""
    for path, diff in results.items():
        if len(diff) > 1:
            msg += f"{CLICenterString(path)}\n"
            msg += f"{diff}\n"
    LaunchPager(msg)
from menus.menu import GetNextInput, MenuExit

def _SelectModuleRepo():
    """
    Present all managed repositories as numbered choices and return the
    (repo_name, repo_path) tuple for the one the user selects.
    Returns None if the user cancels.
    """
    repos = Project.GetRepositories()

    # Build a name -> repo_id mapping so we display names, not hash IDs
    name_to_id = {}
    for repo_id, repo_data in repos.items():
        name_to_id[repo_data["name"]] = repo_id
    modules = sorted(name_to_id.keys())

    if not modules:
        PrintError("No managed repositories found")
        return None

    print("Available modules:")
    items = [f"  [{idx}] {ColorFormat(Colors.Yellow, name)}" for idx, name in enumerate(modules)]
    PrintInColumns(items)

    print("\nSelect a module by index or name (exit/Ctrl+D to cancel):")
    try:
        raw = GetNextInput(single_string=True)
    except EOFError:
        return None

    if MenuExit(raw) or not raw.strip():
        return None

    if StringIsNumber(raw.strip()):
        idx = int(raw.strip())
        if idx < 0 or idx >= len(modules):
            PrintError(f"Index {idx} out of range")
            return None
        selected = modules[idx]
    else:
        selected = raw.strip()
        if selected not in name_to_id:
            PrintError(f"Module '{selected}' not found")
            return None

    repo_id = name_to_id[selected]
    return selected, repos[repo_id]["repo source"]

def GetFilesDiffForModule():
    """Show file-statistics diff (--stat) for a single user-selected module."""
    result = _SelectModuleRepo()
    if result is None:
        return
    repo_name, repo_path = result
    diff = GetGitFileDiff(repo_path)
    if len(diff) > 1:
        PrintInfo(CLICenterString(repo_name))
        PrintInfo(diff)
    else:
        print(ColorFormat(Colors.Yellow, f"No changes in {repo_name}"))

def GetDiffForModule():
    """Show full content diff for a single user-selected module, via pager."""
    result = _SelectModuleRepo()
    if result is None:
        return
    repo_name, repo_path = result
    diff = GetGitDiff(repo_path)
    if len(diff) > 1:
        msg = f"{CLICenterString(repo_name)}\n{diff}\n"
        LaunchPager(msg)
    else:
        print(ColorFormat(Colors.Yellow, f"No changes in {repo_name}"))

def DirectlyManageSingleRepository():
    all_paths, known_paths, _ = GetKnownAndUnknownGitRepos()
    repos = Project.GetRepositories()

    dynamic_entries = []
    for path_ind in range(len(all_paths)):
        new_entry = []
        path = all_paths[path_ind]
        repo_id   = GetRepoIdFromPath(path)
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

def RunCustomCommandOnAllRepos():
    """Prompt for a shell command and run it on every known repo path."""
    try:
        cmd = input("Command to run on all repos: ").strip()
    except EOFError:
        return
    if not cmd:
        return

    results = []
    def _RunCmd(path=None):
        lock = threading.Lock()
        with lock:
            try:
                result = LaunchProcess(cmd, path, False)
                # PrintInfo(f"[{path}] OK")
                results.append(f"{path}$ {cmd}\n{result["stdout"]} {result["stderr"]}\n")
            except ProcessError as ex:
                PrintError(f"[{path}] FAILED: {ex}")

    RunOnAllRepos(_RunCmd)
    print('\n'.join(results))

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
        repo_id   = GetRepoIdFromPath(path)
        relevant_path = ColorFormat(Colors.Grey, f"(at {GetRelevantPath(path)})")
        repo_name : str = f"{GetRepoNameFromPath(path)} {relevant_path}"

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
    while IsValidGitBranch(branch) is False:
        PrintWarning("Invalid git branch")
        branch = GetNextInput("New branch name: ")

    repo_branches = RunOnAllManagedRepos(GitCheckoutBranch, {"new_branch": branch})
    SetBranch(branch)


def PrintAllBranches():
    repo_branches = RunOnAllManagedRepos(GetAllRepoBranches)
    # There is a high likelihood that the same branches will be present on multiple repos
    # Print by branch and not by repo
    repo_branches = OrganizeBranches(repo_branches)

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

    temp_commit_count = 0

    try:
        temporary_commmits = __GetCurrentTemporaryCommits()
        temp_commit_count = __CountTemporaryCommits(temporary_commmits)
    finally:
        if temp_commit_count == 0:
            print("There are no temporary commits. Direct global commit message")
            commit_message = GetNextInput("[ fixed commit message ][<] ", True)
            RunOnAllManagedRepos(RepoSaveChanges, {"commit_message":commit_message})

    paths = temporary_commmits.keys()
    status_message = f"\nMerging in {len(paths)} repositories"

    for path in paths:
        status_message += f"\n\t* {len(temporary_commmits[path])} commits from {path.split("/")[-1]}"

    PrintNotice(status_message)
    commit_message = GetNextInput("[ fixed commit message ][<] ", True)
    PrintNotice(commit_message)

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
        PrintNotice(status_message)
    else:
        PrintNotice("\nNo temporary commits found")

def GlobalSave():
    commit_message = GetNextInput("[commit message <] ")

    if commit_message == "":
        PrintWarning("Commit message cannot be empty")
    else:
        try:
            RunOnAllManagedRepos(RepoSaveChanges, {"commit_message":commit_message})
        except Exception as ex:
            Abort(f"Unacceptable commit message: {str(ex)}")

def ResetToLatestSync():
    RunOnAllRepos(RepoResetToLatestSync)

"""
Create a stash across all managed repositories with a custom or timestamped message.
"""
def GlobalStashCreate():
    print(CLICenterString(ColorFormat(Colors.Cyan, "Create Global Stash"), "="))
    print("\nThis will create a stash in all managed repositories.")
    message = GetNextInput("[stash message (leave empty for timestamp) <] ")

    if message.strip() == "":
        print(ColorFormat(Colors.Yellow, "Using timestamped default message"))

    # Create stash in all managed repos
    stash_results = RunOnAllManagedRepos(GitStashCreate, {"message": message if message.strip() else None})

    # Count successful stashes
    repos_stashed = sum(1 for result in stash_results.values() if result is not None)

    print(f"\n{ColorFormat(Colors.Green, f'Stashed changes in {repos_stashed} repositories')}")

def __PrintStashes(print_indices):
    # Get stashes from all managed repos
    all_stashes = RunOnAllManagedRepos(GitStashList)

    total_stashes = 0
    pb_managed_count = 0

    org_stashes = {}

    for path, stashes in all_stashes.items():
        if not stashes:
            continue
        for index, message in stashes:
            if message not in org_stashes:
                total_stashes += 1
                if StashIsPBManaged(message):
                    pb_managed_count += 1
                org_stashes[message] = []

            org_stashes[message].append((path, index))

    if total_stashes == 0:
        print(ColorFormat(Colors.Yellow, "\nNo stashes found in any repository"))
    else:
        print(f"\n{CLICenterString('', '=')}")
        print(f"Total: {total_stashes} stashes ({pb_managed_count} managed by ProjectBase)")

    ind = 0
    for stash_message, stashes in org_stashes.items():
        msgs = []
        for path, index in stashes:
            repo_name = GetRepoNameFromPath(path)
            msgs.append(ColorFormat(Colors.Blue, f"{repo_name}"))

        msg = ""
        if print_indices:
            msg += f"[{ind}] "

        if StashIsPBManaged(stash_message):
            stash_message = stash_message[len(STASH_MARKER):].strip()
            msg += ColorFormat(Colors.Green, "Managed")
        else:
            msg += ColorFormat(Colors.Yellow, "UnManaged")

        msg += f" stash \"{stash_message}\" at: {', '.join(msgs)}"

        print(msg)
        ind += 1

    return org_stashes

"""
List all stashes across all managed repositories.
"""
def GlobalStashList():
    print(CLICenterString(ColorFormat(Colors.Cyan, "Global Stash List"), "="))
    __PrintStashes(False)

"""
Helper function to display stashes and get user selection.
Returns a dict mapping paths to selected stash indices.
"""
def __SelectStashesFromRepos():
    all_stashes = __PrintStashes(True)

    print(f"\n{CLICenterString('', '=')}")

    # Get user selection

    selection = int(GetNextInput("[stash <] "))
    if selection >= len(all_stashes):
        PrintError(f"Incorrect index {selection}/{len(all_stashes)}")
        return

    message = list(all_stashes.keys())[selection]

    if not StashIsPBManaged(message):
        PrintError(f"Refusing to touch unmanaged stash. Please use direct repo manipulation")
        return

    return all_stashes[message]

"""
Delete selected stashes from repositories.
"""
def GlobalStashDelete():
    print(CLICenterString(ColorFormat(Colors.Cyan, "Delete Stashes"), "="))

    selected = __SelectStashesFromRepos()
    if selected is None:
        return

    # Confirm deletion TODO: Put confirmation in common for general purpose use
    print(f"\n{ColorFormat(Colors.Red, 'WARNING:')} About to delete {len(selected)} stash(es)")
    confirm = GetNextInput("[Type 'yes' to confirm <] ")

    if confirm.lower() != 'yes':
        print(ColorFormat(Colors.Yellow, "Deletion cancelled"))
        return

    # Delete stashes
    for path, stash_idx in selected:
        try:
            GitStashDrop(path, stash_idx)
            repo_name = GetRepoNameFromPath(path)
            print(f"{ColorFormat(Colors.Green, 'v')} Deleted stash {stash_idx} from {repo_name}")
        except Exception as ex:
            repo_name = GetRepoNameFromPath(path)
            print(f"{ColorFormat(Colors.Red, 'x')} Failed to delete stash from {repo_name}: {ex}")

"""
Apply selected stashes to repositories (without removing them).
"""
def GlobalStashApply():
    print(CLICenterString(ColorFormat(Colors.Cyan, "Apply Stashes"), "="))

    selected = __SelectStashesFromRepos()
    if selected is None:
        return

    # Apply stashes
    for path, index in selected:
        try:
            GitStashApply(path, index)
            repo_name = GetRepoNameFromPath(path)
            print(f"{ColorFormat(Colors.Green, 'v')} Applied stash {index} to {repo_name}")
        except Exception as ex:
            repo_name = GetRepoNameFromPath(path)
            print(f"{ColorFormat(Colors.Red, 'x')} Failed to apply stash to {repo_name}: {ex}")

"""
Pop (apply and delete) selected stashes from repositories.
"""
def GlobalStashPop():
    print(CLICenterString(ColorFormat(Colors.Cyan, "Pop Stashes"), "="))

    selected = __SelectStashesFromRepos()
    if selected is None:
        return

    # Pop stashes
    for path, stash_idx in selected:
        try:
            GitStashPopByIndex(path, stash_idx)
            repo_name = GetRepoNameFromPath(path)
            print(f"{ColorFormat(Colors.Green, 'v')} Popped stash {stash_idx} from {repo_name}")
        except Exception as ex:
            repo_name = GetRepoNameFromPath(path)
            print(f"{ColorFormat(Colors.Red, 'x')} Failed to pop stash from {repo_name}: {ex}")


# Header/footer used to delimit per-repository sections inside a combined diff file.
# Format:  # === PB-REPO: <repo_name> | <repo_path> ===
_DIFF_SECTION_HEADER_PREFIX = "# === PB-REPO:"
_DIFF_SECTION_FOOTER        = "# === END-REPO ==="

def _MakeDiffSectionHeader(repo_name, repo_path):
    return f"{_DIFF_SECTION_HEADER_PREFIX} {repo_name} | {repo_path} ==="

def _ParseDiffSections(combined_diff):
    """
    Parse a combined diff file produced by GlobalDiffCreate.
    Returns a list of (repo_name, repo_path, diff_text) tuples.
    """
    sections = []
    current_name = None
    current_path = None
    current_lines = []

    for line in combined_diff.splitlines(keepends=True):
        stripped = line.strip()
        if stripped.startswith(_DIFF_SECTION_HEADER_PREFIX):
            # Save previous section if any
            if current_path is not None:
                sections.append((current_name, current_path, "".join(current_lines)))
            # Parse: "# === PB-REPO: <name> | <path> ==="
            inner = stripped[len(_DIFF_SECTION_HEADER_PREFIX):].strip().rstrip("=").strip()
            parts = inner.split("|", 1)
            current_name = parts[0].strip()
            current_path = parts[1].strip() if len(parts) > 1 else None
            current_lines = []
        elif stripped == _DIFF_SECTION_FOOTER:
            if current_path is not None:
                sections.append((current_name, current_path, "".join(current_lines)))
            current_name = None
            current_path = None
            current_lines = []
        else:
            if current_path is not None:
                current_lines.append(line)

    # Handle file not ending with a footer
    if current_path is not None and current_lines:
        sections.append((current_name, current_path, "".join(current_lines)))

    return sections


"""
Create a single unified diff file combining the current changes
(staged, unstaged, and untracked) from every managed repository.
"""
def GlobalDiffCreate():
    print(CLICenterString(ColorFormat(Colors.Cyan, "Create Global Diff"), "="))

    default_path = os.path.join(os.getcwd(), "project.patch")
    output_path = GetNextInput(f"[output file (default: {default_path}) <] ").strip()
    if not output_path:
        output_path = default_path

    repos = Project.GetRepositories()
    known_paths = [repos[r]["repo source"] for r in repos]

    sections = []
    repos_with_changes = 0

    for repo_path in known_paths:
        try:
            repo_name = GetRepoNameFromPath(repo_path)
        except Exception:
            repo_name = os.path.basename(repo_path)

        diff_text = GetGitFullDiff(repo_path)

        if not diff_text.strip():
            PrintDebug(f"No changes in {repo_name}, skipping")
            continue

        header = _MakeDiffSectionHeader(repo_name, repo_path)
        sections.append(f"{header}\n{diff_text}\n{_DIFF_SECTION_FOOTER}\n")
        repos_with_changes += 1
        print(f"  {ColorFormat(Colors.Green, 'v')} {repo_name}: captured diff")

    if repos_with_changes == 0:
        print(ColorFormat(Colors.Yellow, "No changes found in any repository — diff file not written"))
        return

    combined = "\n".join(sections)

    try:
        with open(output_path, "w") as f:
            f.write(combined)
        print(f"\n{ColorFormat(Colors.Green, 'Diff written to:')} {output_path}")
        print(f"Captured changes from {repos_with_changes} repository/repositories")
    except IOError as ex:
        PrintError(f"Could not write diff file: {ex}")


"""
Apply a combined diff file (created by GlobalDiffCreate) back to the
corresponding managed repositories using `git apply`.
"""
def GlobalDiffApply():
    import os
    print(CLICenterString(ColorFormat(Colors.Cyan, "Apply Global Diff"), "="))

    patch_path = GetNextInput("[patch file path <] ").strip()
    if not patch_path:
        PrintError("No path provided")
        return

    if not os.path.isfile(patch_path):
        PrintError(f"File not found: {patch_path}")
        return

    with open(patch_path, "r") as f:
        combined_diff = f.read()

    sections = _ParseDiffSections(combined_diff)
    if not sections:
        PrintError("No repository sections found in patch file")
        return

    print(f"Found {len(sections)} section(s) in patch file\n")

    repos = Project.GetRepositories()
    known_paths = {repos[r]["repo source"] for r in repos}

    for repo_name, repo_path, diff_text in sections:
        if not diff_text.strip():
            print(f"  {ColorFormat(Colors.Yellow, '-')} {repo_name}: empty diff, skipping")
            continue

        if repo_path not in known_paths:
            PrintWarning(f"Repository path not found in current project: {repo_path} ({repo_name}) — skipping")
            continue

        try:
            GitApplyPatch(diff_text, repo_path)
            print(f"  {ColorFormat(Colors.Green, 'v')} {repo_name}: patch applied successfully")
        except Exception as ex:
            print(f"  {ColorFormat(Colors.Red, 'x')} {repo_name}: failed to apply patch — {ex}")

