import os
import logging
from data.settings import Settings
from processes.process import ProcessError, ParseProcessResponse, LaunchProcess
from data.common import IsEmpty, RemoveEmpty, PrintNotice, PrintWarning, PrintError
from data.git import GenerateLocalBranchName, PBBranchNameToNormalName

def ParseGitResult(git_command, path):
    if path == None:
        path = os.getcwd()

    response = "ERRORED OUT"
    try:
        response = ParseProcessResponse(LaunchProcess(git_command, path, False))
    finally:
        if Settings["debug"]:
            logging.debug(f"Git Operation return: {response}")
    return response

# ================= GET operations =================

"""
Obtain the URL of the repository located at path
"""
def GetRepositoryUrl(path = None):
    url = ParseGitResult("git config --get remote.origin.url", path)
    top_level = GetGitTopLevel(path)

    if path == None:
        path = os.getcwd()

    if top_level != path:
        return ""
    return url

def GetGitTopLevel(path = None):
    top_level = ""
    try:
        top_level = ParseGitResult("git rev-parse --show-toplevel", path)
    except Exception as ex:
        # Failure in bare gits
        if "fatal: this operation must be run in a work tree" in str(ex):
            top_level = path
    return top_level

def GitCheckRemoteBranchExists(path, branch):
    remote = GetRepoRemote(path)
    ret = ParseGitResult(f"git ls-remote --heads {remote} {branch}", path)
    if len(ret) == 0:
        return False
    return True

def GetAllRepoBranches(path = None):
    checked_out = None

    local = GetRepoLocalBranches(path)
    for branch in local.split("\n"):
        if branch.startswith("* "):
            checked_out = ParseBranch(branch)

    not_pushed = []
    local_branches = ParseBranches(local)
    for local_branch in local_branches:
        if GitCheckRemoteBranchExists(path, local_branch) == False:
            not_pushed.append(local_branch)


    remote_branches = GetParsedRepoRemoteBranches(path)

    return {
        "checkedout" : [checked_out],
        "locals"     : local_branches,
        "remotes"    : remote_branches,
        "status"     : GetRepoStatus(path),
        "remote"     : [PBBranchNameToNormalName(GetRepoRemoteBranch(path))],
        "not pushed" : not_pushed
    }

"""
Find all local branches that point to the requested remote branch
"""
def FindLocalBranchForRemote(path, branch_name):
    branch_name = f"{GetRepoRemote(path)}/{branch_name}"
    branches = GetRepoGetDetailedLocalBranches(path)

    local_branches = []
    for branch in branches.split('\n'):
        parts = branch[2:].split(" ")
        parts = RemoveEmpty(parts)

        if len(parts) < 3:
            continue

        if parts[2].startswith(f"[{branch_name}"):
            local_branches.append(parts[0])

    if len(local_branches) > 1:
        PrintWarning(f"More than one local branch found for {branch_name}")

    return local_branches

"""
Delete remote branch. No need to check name because remote names are the actual branch names
"""
def GitDeleteRemoteBranch(path=None, branch_name=None):
    remote = f"{GetRepoRemote(path)}/"
    if branch_name.startswith(remote):
        branch_name = branch_name.replace(remote, "", 1)

    PrintNotice(f"Deleted local branch: {branch_name}")
    return ParseGitResult(f"git push origin :refs/heads/{branch_name}", path)

"""
Delete all local branches that match the user requested branch
There should be only one, but do so just in case
"""
def GitDeleteLocalBranch(path=None, branch_name=None):
    local_branches = FindLocalBranchForRemote(path, branch_name)

    ret = []
    success = False
    for branch in local_branches:
        try:
            res = ParseGitResult(f"git branch -D {branch}", path)
            ret.append(res)
            success = "Deleted branch" in res
        except ProcessError as ex:
            ret.append(ex)
    if success:
        PrintNotice(f"Deleted local branch: {branch_name}")
    else:
        if len(local_branches) > 0:
            PrintWarning(f"Failed to delete local branch {branch_name} for {path}: {ret}\nlocal_branches: {local_branches}")
        else:
            # Couldnt find any local branch. It is likely a branch that exists as is (not created by PB)
            ret.append(ParseGitResult(f"git branch -D {branch_name}", path))

    return ret

def GitMergeBranch(path, branch_to_merge):
    local_branches = FindLocalBranchForRemote(path, branch_to_merge)
    return ParseGitResult(f"git merge {local_branches[0]}", path)

def GitRebaseBranch(path, branch_to_rebase):
    return ParseGitResult(f"git rebase {branch_to_rebase}", path)

def GitRebaseAbortBranch(path):
    return ParseGitResult(f"git rebase --abort", path)

def GitCheckoutBranch(path = None, new_branch=None):
    local_branches = FindLocalBranchForRemote(path, new_branch)

    if len(local_branches) == 0:
        local_branch_name = GenerateLocalBranchName(new_branch)
        remote = GetRepoRemote(path)
        # msg = f"git switch --create {local_branch_name} && git push -u {remote} {local_branch_name}:{new_branch}"
        PrintNotice(f"Creating local branch {new_branch}")
        # Create branch locally
        msg = f"git switch --create {local_branch_name} && "
        # Create ficticious remote reference without pushing it
        remote = GetRepoRemote(path)
        msg += f"git update-ref refs/remotes/{remote}/{new_branch} $(git rev-parse HEAD) && "
        # Set upstream to that reference
        msg += f"git branch --set-upstream-to={remote}/{new_branch}"
        return ParseGitResult(msg, path)

    # There is a local branch for this remote, just change to it

    if len(local_branches) > 1:
        # TODO: It might be possible to fix this automatically if the branches are at the same commit
        # Only give warning if this is not the case
        msg  = "There are multiple local branches pointing to the same remote: {new_branch}. Manual intervention is recommended"
        msg += f"Branch in use: {local_branches[0]}"
        PrintWarning(msg)

    return ParseGitResult(f"git switch {local_branches[0]}", path)

def GetRepoGetDetailedLocalBranches(path = None):
    return ParseGitResult("git branch -vv", path)

def GetRepoGetDetailedRemoteBranches(path = None):
    return ParseGitResult("git branch -vv --remotes", path)

def GetRepoLocalCommit(path = None):
    return ParseGitResult("git rev-parse HEAD", path)

def GetRepoLocalBranch(path = None):
    return ParseGitResult("git rev-parse --abbrev-ref HEAD", path)

def GetRepoRemoteBranch(path = None):
    return ParseGitResult("git for-each-ref --format='%(upstream:short)' \"$(git symbolic-ref -q HEAD)\"", path)

def GetRepoRemoteCommit(path = None):
    return ParseGitResult("git rev-parse `git branch -r --sort=committerdate | tail -1`", path)

def BranchesMatch(branchA, branchB):
    if branchA == branchB:
        return True
    if branchB.startswith(f"{branchA}_ProjectBase_") or branchA.startswith(f"{branchB}_ProjectBase_"):
        return True
    return False

def ParseBranch(branch):
    branch = branch[2:]
    branch = PBBranchNameToNormalName(branch)
    return branch

def ParseBranches(branches):
    new_branches = []
    for branch in branches.split("\n"):
        if " -> " in branch:
            continue
        if "no branch" in branch:
            continue

        branch = ParseBranch(branch)
        new_branches.append(branch)
    return new_branches

def GetRepoRemoteBranches(path = None):
    return ParseGitResult("git branch --remotes", path)
def GetParsedRepoRemoteBranches(path = None):
    return ParseBranches(GetRepoRemoteBranches(path))

def GetRepoLocalBranches(path = None):
    return ParseGitResult("git branch", path)
def GetParsedLocalBranches(path = None):
    return ParseBranches(GetRepoLocalBranches(path))

def GetRepoStatus(path = None):
    return ParseGitResult("git status", path)

def GetRepoRemote(path = None):
    return ParseGitResult("git remote show", path)

def GetCurrentBranchsUpstream(path = None):
    return ParseGitResult("git for-each-ref --format='%(upstream:short)' $(git symbolic-ref -q HEAD)", path)

def GetRepoDefaultBranch(path = None):
    remote = GetRepoRemote(path)
    default_branch = ParseGitResult("git remote show " + remote + " 2>/dev/null | sed -n '/HEAD branch/s/.*: //p'", path)
    if IsEmpty(default_branch):
        Message  = "No default branch for "
        Message += GetRepositoryUrl(path) + " at " + path + "\n"
        Message += "Code: " + str(default_branch) + "\n"
        Message += "Output: " + str(default_branch) + "\n"
        raise Exception(Message)

    return default_branch.split("/")[-1].strip()

# ================= SET operations =================

def RepoHardReset(path=None):
    return ParseGitResult("git reset --hard", path)

def RepoSoftReset(path = None):
    return ParseGitResult("git reset --soft HEAD~", path)

"""
Remove untracked files and folders, including those present in .gitignore
"""
def RepoCleanUntracked(path = None):
    return ParseGitResult("git clean -fdx", path)

# ================= Update operations =================

def RepoFetch(path = None):
    ParseGitResult("git fetch origin '*:*'", path)

def RepoPull(path = None):
    try:
        if GetRepoLocalBranch(path) != "HEAD":
            ParseGitResult("git pull origin --rebase", path)
            ParseGitResult("git fetch --all", path)
            ParseGitResult("git rebase", path)
    except ProcessError as ex:
        status = GetRepoStatus(path)
        if "both modified" in status:
            print(f"WARNING: Code needs merge in {path}")
        raise ex

def RepoPush(path = None):
    # Push to bare git
    ParseGitResult("git push", path)
    # Code below SHOULDNT be necessary again because remote ref is properly set
    # Leavign it for now just in case something fails and we need a bit more manual push
    # remote = GetRepoRemote(path)
    # # Get remote branch name and push to it
    # upstream_branch_name = GetCurrentBranchsUpstream(path)
    # # Remove origin
    # upstream_branch_name.replace(f"{remote}/", "", 1)
    # ParseGitResult(f"git push {remote} HEAD:{upstream_branch_name}", path)

def GenAutoCommitMessage():
    return ""

def SquashUntilSpecifiedCommit(path, commit_message, oldest_commit):
    ParseGitResult(f"git reset --soft {oldest_commit}~1", path)
    ParseGitResult(f"git commit -m '{commit_message}'", path)

"""
Stages all changes, within the current directory and its subdirectories.
"""
def RepoSaveChanges(path, commit_message=None):
    try:
        ParseGitResult(f'git add -A; git commit -m "{commit_message}"', path)
    except ProcessError as ex:
        ex.RaiseIfNotInOutput("nothing to commit, working tree clean")

def GitStash(path):
    return ParseGitResult("git stash", path)

def GitStashPop(path):
    try:
        ParseGitResult("git stash pop", path)
    except ProcessError as ex:
        ex.RaiseIfNotInOutput("No stash entries found")

def GetAllCommits(path):
    return ParseGitResult("git log --pretty='format:%H %s'", path)

def RepoResetToLatestSync(path=None):
    branch = GetCurrentBranchsUpstream(path)
    ParseGitResult(f"git reset --hard {branch}", path)
    if path == None:
        path = os.getcwd()

