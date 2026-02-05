import os
import logging
from data.settings import Settings
from processes.process import *
from data.common import IsEmpty, RemoveEmpty, RemoveSequentialDuplicates
from data.print import *
from data.git import *
from data.paths import GetNewTemporaryPath
from processes.filesystem import *
from data.settings import Settings, CLONE_TYPE
from processes.git_operations import *

UNKNOWN_ERR = f"Unknown issue. Please send this message in a ticket for better error handling in the future!"

class GIT_CMD():
    def __init__(self, command, path):
        if path == None:
            path = os.getcwd()

        self.command = command
        self.path = command

        self.legacy_return = None

        self.proc_error = None

        self.success = False
        self.success_nessage = None
        self.error_nessage = None

        try:
            self.returned = LaunchProcess(command, path, False)
            self.legacy_return = self.returned
            self.success = True
        except ProcessError as ex:
            self.legacy_return = ex
            self.proc_error = ex
            self.returned = ex.returned

        if Settings["debug"]:
            logging.debug(f"Git Operation return: {self.returned}")

    def __str__(self):
        return f"cmd: {self.command}\npath: {self.path}\nreturned: {self.returned}\n"

def ParseGitResult(git_command, path):
    return GIT_CMD(git_command, path).returned["out"]


# ================= GET operations =================

"""
Obtain the URL of the repository located at path
"""
def GetRepositoryUrl(path = None):
    if path == None:
        path = os.getcwd()

    url = ParseGitResult("git config --get remote.origin.url", path)
    # Validate that we are currently at the top level (otherwise git will search backwards)
    top_level = GetGitTopLevel(path)
    if top_level != path:
        return ""
    return url

def GetRepoNameFromPath(path):
    url = GetRepositoryUrl(path)
    if IsEmpty(url):
        raise Exception(f"Could not retrieve Name from path \"{path}\"")

    return GetRepoNameFromURL(url)

def GetGitTopLevel(path = None):
    top_level = ParseGitResult("git rev-parse --show-toplevel", path)
    # Failure in bare gits
    if "fatal: this operation must be run in a work tree" in str(top_level):
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

        if parts[2] == f"[{branch_name}]" or parts[2] == f"[{branch_name} " or parts[2] == f"[{branch_name}:":
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

    PrintNotice(f"Deleted remote branch: {branch_name}")
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
        PrintNotice(f"Deleted local branch (PB generated branch): {branch_name}")
    else:
        if len(local_branches) > 0:
            PrintWarning(f"Failed to delete local branch {branch_name} for {path}: {ret}\nlocal_branches: {local_branches}")
        else:
            # Couldnt find any local branch. It is likely a branch that exists as is (not created by PB)
            ret.append(ParseGitResult(f"git branch -D {branch_name}", path))
            PrintNotice(f"Deleted local branch (normal branch): {branch_name}")

    return ret

def GitFastForwardFetch(path, current):
    code = """
# Update remote-tracking refs first
# NEVER use  --prune. We set our own upstreams that might NOT be on the remote
git fetch --all

cur_branch=$(git rev-parse --abbrev-ref HEAD)

git for-each-ref refs/heads --format='%(refname:short) %(upstream:short)' |
while read -r branch upstream; do
    [ -n "$branch" ] || continue
    [ -n "$upstream" ] || continue
    if [ "$branch" = "$cur_branch" ]; then
"""
    if current:
        code += """
        # Merge current branch only if fast forward is possible
        git merge --ff-only "$upstream";"""
    else:
        code += """
        # Do nothing"""

    code += """
    else
        # For other branches, update the remote reference
        remote=${upstream%%/*}
        rbranch=${upstream#*/}
        git fetch "$remote" "$rbranch:refs/heads/$branch"
    fi
done"""
    ret = GIT_CMD(code, path)
    if ret.proc_error != None:
        status = GetRepoStatus(path)
        if "Diverging branches" in ret.returned["stderr"]:
            ret.error_nessage =f"Branches diverged, can't pull (merge) in {path}. Need manual intervention!"
        elif "both modified" in status:
            # TODO: Dont use status
            ret.error_nessage = f"Code needs merge in {path}"
        else:
            # Not sure what the error was, just print it
            ret.error_nessage = f"{UNKNOWN_ERR}: {ret}"
        # elif "both modified" in status:
        #     PrintWarning(f"Code needs merge in {path}")

    ret.error_nessage
    return ret

def GitRebaseOrMergeBranch(path, branch, operation):
    local_branches = FindLocalBranchForRemote(path, branch)
    result = GIT_CMD(f"git {operation} {local_branches[0]}", path)

    if result.proc_error != None:
        if operation == "merge":
            if CheckMergeOperationConflict(result.returned["out"]):
                result.error_nessage = f"Merge conflict in {path} when merging branch {branch}"
            elif not CheckMergeOperationSuccess(result.returned["out"]):
                result.error_nessage = f"{UNKNOWN_ERR}: {result}"
        else:
            if CheckRebaseOperationConflict(result.returned["out"]):
                result.error_nessage = f"Rebase conflict in {path} when merging branch {branch}"
            elif not CheckRebaseOperationSuccess(result.returned["out"]):
                result.error_nessage = f"{UNKNOWN_ERR}: {result}"

    return result

def GitMergeBranch(path, branch_to_merge):
    return GitRebaseOrMergeBranch(path, branch_to_merge, "merge")

def GitRebaseBranch(path, branch_to_rebase):
    return GitRebaseOrMergeBranch(path, branch_to_rebase, "rebase")

def GitRebaseOrMergeAbort(path, operation):
    return ParseGitResult(f"git {operation} --abort", path)

def GitGetHeadCommit(path):
    return ParseGitResult(f"git rev-parse HEAD", path)

"""
Get amount of commits desynced
returns a list
first element contains amount of local commits not in remote
second element contains amount of remote commits not in local branch
"""
def GitGetRevDiff(path = None):
    res = GIT_CMD("git rev-list --left-right --count HEAD...@{upstream}", path)
    if res.returned["code"] != 0:
        return None

    return res.returned["out"].split("\t")

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
        msg  = f"There are multiple local branches pointing to the same remote: {new_branch}. Manual intervention is recommended\n"
        msg += f"Branches found: {local_branches}\n"
        msg += f"Branch to use: {local_branches[0]}"
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
    return ParseGitResult("git rev-parse --abbrev-ref HEAD", path)

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

def GetRepoUrl(path = None):
    """
    origin	<URL A> (fetch)
    origin	<URL B> (push)
    """
    result = ParseGitResult("git remote -v", path)
    result = result.split('\n')[0]
    result = result.split(' ')[1]
    return result

def GetFirstCommit(path = None):
    return ParseGitResult("git rev-list --max-parents=0 HEAD", path)

def GetRepoStatus(path = None):
    return ParseGitResult("git status", path)

def __GetUntrackedFilesDiff(path):
    return GIT_CMD("git ls-files --others --exclude-standard -z | xargs -0 -n 1 git --no-pager diff --stat /dev/null", path).returned["stdout"]

def __GetUntrackedDiff(path):
    return GIT_CMD("git ls-files --others --exclude-standard -z | xargs -0 -n 1 git --no-pager diff /dev/null", path).returned["stdout"]

def GetGitFileDiff(path = None):
    untracked = __GetUntrackedFilesDiff(path)
    tracked = GIT_CMD("git --no-pager diff --stat", path).returned["stdout"]
    return tracked + "\n" + untracked

def GetGitDiff(path = None):
    untracked = __GetUntrackedDiff(path)
    tracked = GIT_CMD("git --no-pager diff", path).returned["stdout"]
    return tracked + "\n" + untracked

def GetRepoRemote(path = None):
    return ParseGitResult("git remote show", path)

def GetCurrentBranchsUpstream(path = None):
    return ParseGitResult("git for-each-ref --format='%(upstream:short)' $(git symbolic-ref -q HEAD)", path)

def GetRepoDefaultBranch(path = None):
    remote = GetRepoRemote(path)
    default_branch = ParseGitResult(f"git remote show {remote} 2>/dev/null | sed -n '/HEAD branch/s/.*: //p'", path)
    if default_branch == "(unknown)" or IsEmpty(default_branch):
        Message =  f"No default branch for {GetRepositoryUrl(path)} for remote {remote} at {path}.\n"
        Message += f"You may need to add an initial commit with some data.\ni.e.:\n"
        Message += f"echo '# Project Title' > README.md\n"
        Message += f"git add .\ngit commit -m 'Initial commit'\ngit push -u origin master"
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
    # Only pull if it is not a commit
    if GetRepoLocalBranch(path) != "HEAD":
        ret = GitFastForwardFetch(path, True)
    else:
        ret = GitFastForwardFetch(path, False)
    
    if ret.error_nessage != None:
        PrintWarning(ret.error_nessage)
    # ParseGitResult("git pull origin --rebase", path)
    # ParseGitResult("git fetch --all", path)
    # ParseGitResult("git rebase", path)

def RepoPush(path = None):
    # Push to bare git
    # If repo has no changes between local local and remote local, it means it doesnt need to be pushed
    rev = GitGetRevDiff(path)
    if rev != None:
        if rev[0] == "0":
            PrintDebug(f"Not pushing \"empty\" branch for {GetRepositoryName(path)}")
            return

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

"""
Fix url so it is according to settings
"""
def FixUrl(url):
    if Settings["active"]["Clone Type"] == CLONE_TYPE.SSH.value:
        url = url_HTTPS_to_SSH(url)
    elif Settings["active"]["Clone Type"] == CLONE_TYPE.HTTPS.value:
        url = url_SSH_to_HTTPS(url)
    else:
        raise Exception("No mode selected is not acceptable: " + str(Settings["active"]["Clone Type"]))
    
    if url[-1] == '/':
        url = url[:-1]
    return url

"""
Obtain the name of the repository located at path
"""
def GetRepositoryName(path):
    url = GetRepositoryUrl(path)
    return GetRepoNameFromURL(url)

def RepositoryIsClean(path = None):
    return "nothing to commit, working tree clean" in GetRepoStatus(path)

"""
Recursively scan a folder for a .git repository whose url matches the provided repo_url
If commit is not None, will only match exact commit
"""
def FindGitRepo(base_path, repo_url, repo_commitish = None, depth=-1):
    if depth == 0:
        logging.debug("Not found in desired depth")
        return None

    # multiple threads mean base_path can be randomly deleted
    if not os.path.isdir(base_path):
        return None

    try:
        url_base_path = GetRepositoryUrl(base_path)
        if SameUrl(repo_url,  url_base_path ):
            if repo_commitish != None:
                # Look into commit
                if repo_commitish["type"] == "commit":
                    commit = GetRepoLocalCommit(base_path)
                    if commit == repo_commitish["commit"]:
                        return RemoveSequentialDuplicates(base_path, "/")
                # Look into branch
                elif repo_commitish["type"] == "branch":
                    branch = GetRepoLocalBranch(base_path)
                    if SameBranch(branch, repo_commitish["branch"]):
                        return RemoveSequentialDuplicates(base_path, "/")
                else:
                    raise Exception("Invalid commitish: "+str(repo_commitish))
            else:
                return RemoveSequentialDuplicates(base_path, "/")
    except Exception as ex:
        # If the folder got removed during iteration, just return None
        if "No such path" in str(ex):
            return None

    # multiple threads mean base_path can be randomly deleted
    if not os.path.isdir(base_path):
        logging.warning("Folder disappeared during operation")
        return None

    # Nothing can be found inside baregits
    if FolderIsBareGit(base_path):
        return None

    # Now look at their files
    for sub_folder in os.listdir(base_path):
        full_path = JoinPaths(base_path, sub_folder)
        # Only look for directories that are git repositories (worktrees/bare gits)
        if not os.path.isdir(full_path):
            continue
        # Do not follow symbolic links to avoid infinite loops
        if os.path.islink(full_path):
            continue
        if depth == -1: # No depth limitation
            Result = FindGitRepo(full_path, repo_url, repo_commitish)
        else:
            Result = FindGitRepo(full_path, repo_url, repo_commitish, depth - 1)

        if Result != None:
            return Result

    return None

def GetAllGitRepos(path_to_search, depth=-1):
    git_repos = []
    if not os.path.isdir(path_to_search):
        logging.error(path_to_search+" is not a valid directory")
        return None

    if depth == 0:
        return None

    if FolderIsGit(path_to_search):
        git_repos.append(path_to_search)

    for Inode in os.listdir(path_to_search):
        NextPath = JoinPaths(path_to_search, Inode)
        if os.path.isdir(NextPath) and Inode != ".git":
            # Do not follow symbolic links to avoid infinite loops
            if os.path.islink(NextPath):
                continue
            if depth == -1: # No depth limitation
                git_repos = git_repos + GetAllGitRepos(NextPath)
            else:
                git_repos = git_repos + GetAllGitRepos(NextPath, depth - 1)

    return git_repos

def SetupBareData(repo_url):
    bare_git = GetRepoBareTreePath(Settings["paths"]["bare gits"], repo_url)
    clone_command = 'git clone "' + repo_url + '" "' + bare_git + '" --bare'
    logging.debug("Cloning bare git with: " + clone_command)
    try:
        LaunchProcess(clone_command)
    except ProcessError as ex:
        ex.RaiseIfNotInOutput("already exists")

    # Setup some configs
    msg = "New branches track the remote of the current local branch"
    LaunchGitCommandAt("git config branch.autoSetupMerge always", bare_git, msg)

    msg = "Configuring which name the pushed branch has"
    """
    nothing: Refuse to push unless a remote/branch is explicitly specified (not useful for automation).
    matching: Push all local branches that have a matching remote branch (deprecated in Git 2.0+ due to safety risks).
    upstream (or tracking): Push the current branch to its upstream (tracking) branch (requires prior tracking setup).
    simple (default in Git 2.0+): Push the current branch to a remote branch with the same name only if the local branch is already tracking an upstream branch. If no upstream exists, it errors (the "fatal: no upstream branch" scenario we saw earlier).
    current: Push the current branch to a remote branch with the exact same name, creating the remote branch if it doesn’t exist.
    """
    LaunchGitCommandAt("git config push.default upstream", bare_git, msg)

    msg = "Pull will rebase instead of merge"
    LaunchGitCommandAt("git config pull.rebase true", bare_git, msg)

    msg = "Auto stash before pull and apply afterwards"
    LaunchGitCommandAt("git config rebase.autoStash true", bare_git, msg)

    remote = GetRepoRemote(bare_git)
    LaunchGitCommandAt(f"git config --add remote.{remote}.fetch \"+refs/heads/*:refs/remotes/{remote}/*\"", bare_git, "Setup worktree to get all references")
    # Ensure we are fetching all branches of the remote
    LaunchGitCommandAt(f"git fetch --all", bare_git, f"Fetch all branches")

    if False == os.path.isdir(bare_git):
        Abort("Bare git " + bare_git + " could not be pulled")
    return bare_git

def GetBareGit(repo_url):
    repo_url  = FixUrl(repo_url)
    # TODO: Calculate the path and try to check for it directly first
    # Here we might not even need to do Find for baregit at all
    bare_git  = FindGitRepo(Settings["paths"]["bare gits"], repo_url)
    if bare_git == None:
        bare_git = SetupBareData(repo_url)

    return bare_git

def LaunchGitCommandAt(command, path=None, message=None):
    if message != None:
        logging.debug(message)
        logging.debug(command + " at " + str(path))

    result_code = LaunchProcess(command, path)
    if result_code["code"] != 0:
        raise Exception("Could not run " + command)

    if message != None:
        logging.debug(result_code)
"""
Adds a worktree at target_path
Returns path to worktree: target_path + "/" + wortkree_name
"""
def AddWorkTree(bare_path, repo_url, repo_commitish, target_path):
    existing_tree  = FindGitRepo(target_path, repo_url, repo_commitish)
    if existing_tree != None and GetParentPath(existing_tree) == target_path:
        # Already exists, skip
        return existing_tree

    # --track: Set remote and merge configurations to track upstream
    # --force: Override safe guards and allow same branch name to be checked out by multiple worktrees
    # 
    repo_name = GetRepoNameFromURL(repo_url)
    new_repo_path = JoinPaths(target_path, repo_name)

    # In case we stopped before, remove existing temporary
    # LaunchProcessAt("git worktree remove " + new_repo_path, bare_path)
    LaunchProcess("rm -rf " + new_repo_path)
    LaunchGitCommandAt('git worktree prune', bare_path)
    # If commit is defined, set it detached (it wont be updated)
    if repo_commitish != None and repo_commitish["type"] == "commit":
        worktree_command = "git worktree add --force --detach " + new_repo_path + " " + repo_commitish["commit"]
        LaunchGitCommandAt(worktree_command, bare_path)
        logging.debug("\tAdding git commit worktree with: " + worktree_command + " from bare at " + bare_path)
    else: # Branch comitish
        if repo_commitish == None:
            branch_to_follow = GetRepoDefaultBranch(bare_path)
            local_branch_name = GenerateLocalBranchName(branch_to_follow)
        # If branch is defined, create a new random branch and make it follow the remote (it will be updated)
        elif repo_commitish["type"] == "branch":
            branch_to_follow = repo_commitish["branch"]
            local_branch_name = GenerateLocalBranchName(branch_to_follow)
        else:
            raise Exception("Invalid commitish: "+str(repo_commitish))

        remote = GetRepoRemote(bare_path)

        # Setup worktree already on branch (otherwise, an automatic path related branch appears)
        LaunchGitCommandAt(f"git worktree add -b {local_branch_name} {new_repo_path}", bare_path, "Adding git branch worktree")
        # Fetch all branches
        LaunchGitCommandAt(f"git fetch --all", new_repo_path, f"Fetch all branches")
        # Setup appropriate upstream
        LaunchGitCommandAt(f"git branch --set-upstream-to={remote}/{branch_to_follow}", new_repo_path, f"Following branch {branch_to_follow}")

        # LaunchGitCommandAt(f"git checkout -b {local_branch_name} {remote}/{branch_to_follow}", new_repo_path, f"Following branch {branch_to_follow}")
        # LaunchGitCommandAt(f"git branch --set-upstream-to=origin/{branch_to_follow} {local_branch_name}", new_repo_path)

    if not os.path.isdir(new_repo_path):
        raise Exception(f"Could not add worktree for {repo_url} at {target_path} from bare git at {bare_path}")

    new_tree_path = FindGitRepo(new_repo_path, repo_url, repo_commitish, depth=1)
    if new_tree_path == None or new_tree_path != new_repo_path:
        raise Exception(f"Could not add correct worktree for {repo_url} at {target_path} from bare git at {bare_path}.\nGot {new_tree_path} instead of {new_repo_path}")

    return new_repo_path

def RemoveWorkTree(bare_path, target_path):
    LaunchProcess(f"git worktree remove --force {target_path}", bare_path)

"""
Move worktree from from_path to to_path
TODO: dont just remove and add, also copy changes over
`bare_path`: The bare path location of the repo
`from_path`: Current parent
`to_path`:   Target parent for the repository
"""
def MoveWorkTree(bare_path, from_path, to_path):
    logging.debug("Moving worktree")

    repo_name = GetRepoNameFromPath(bare_path)

    temp_path = GetNewTemporaryPath()

    CreateDirectory(temp_path)

    LaunchProcess(f"git worktree move {from_path} {temp_path}", bare_path)

    temp_repo = JoinPaths(temp_path, repo_name)
    CreateDirectory(to_path)

    LaunchProcess(f"git worktree move {temp_repo} {to_path}", bare_path)

    RemoveDirectory(temp_path)

    # GitStash(from_path)
    # to_path = '/'.join(new_repo_path.split("/")[:-1])
    # AddWorkTree(bare_path, repo_url, repo_commitish, to_path)
    # RemoveWorkTree(bare_path, from_path)
    # GitStashPop(new_repo_path)

# Marker to identify stashes created by ProjectBase
STASH_MARKER = "[PB-MANAGED]"

"""
Create a stash with a custom or timestamped message.
If no message is provided, uses a timestamp as the default message.
Adds the STASH_MARKER prefix to identify ProjectBase-managed stashes.
"""
def GitStashCreate(path=None, message=None):
    timestamp = GetTime()
    if IsEmpty(message):
        # Generate timestamped default message
        message = "Auto-stash"

    # Add marker to identify ProjectBase-managed stashes
    full_message = f"{STASH_MARKER} {message} at {timestamp}"

    try:
        ParseGitResult(f'git stash push -m "{full_message}"', path)
    except ProcessError as ex:
        ex.RaiseIfNotInOutput("No local changes to save")

def StashIsPBManaged(stash_message):
    return stash_message.startswith(STASH_MARKER)

"""
List all stashes in the repository.
Returns a list of tuples: (index, stash_ref, is_pb_managed, message)
"""
def GitStashList(path=None):
    try:
        stash_output = ParseGitResult("git stash list", path)
        if not stash_output or stash_output.strip() == "":
            return []

        stashes = []
        for line in stash_output.strip().split('\n'):
            # Parse stash line format: stash@{0}: On branch: message
            if not line.strip():
                continue

            # Extract stash reference and message
            parts = line.split(':', 2)
            if len(parts) >= 3:
                stash_ref = parts[0].strip()  # e.g., "stash@{0}"
                stash_message = parts[2].strip()  # The actual message

                # Extract index from stash_ref
                index_str = stash_ref.split('{')[1].split('}')[0]
                index = int(index_str)

                # Remove marker from display message if present
                stash_message = stash_message.strip()

                stashes.append((index, stash_message))

        return stashes
    except ProcessError as ex:
        # No stashes exist
        return []

"""
Delete a stash by index.
"""
def GitStashDrop(path=None, stash_index=0):
    try:
        ParseGitResult(f"git stash drop stash@{{{stash_index}}}", path)
    except ProcessError as ex:
        ex.RaiseIfNotInOutput("No stash entries found")

"""
Apply a stash by index without removing it from the stash list.
"""
def GitStashApply(path=None, stash_index=0):
    try:
        ParseGitResult(f"git stash apply stash@{{{stash_index}}}", path)
    except ProcessError as ex:
        # Re-raise if it's not a simple "no stash" error
        if "No stash entries found" not in str(ex):
            raise ex

"""
Pop (apply and delete) a stash by index.
"""
def GitStashPopByIndex(path=None, stash_index=0):
    try:
        # Git doesn't have a direct "pop by index" command, so we apply then drop
        GitStashApply(path, stash_index)
        GitStashDrop(path, stash_index)
    except ProcessError as ex:
        ex.RaiseIfNotInOutput("No stash entries found")