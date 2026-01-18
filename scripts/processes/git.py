import logging

from processes.process import *
from data.settings import Settings, CLONE_TYPE
from data.common import RemoveSequentialDuplicates
from data.git import *
from processes.filesystem import CreateDirectory, RemoveDirectory
from processes.git_operations import *
from processes.filesystem import JoinPaths, GetNewTemporaryPath, GetParentPath

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
        logging.warning("Folder disappeared during operation")
        return None

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



import os
def SetupBareData(repo_url):
    repo_url       = FixUrl(repo_url)
    # ActiveSettings = Settings["active"]

    bare_gits      = Settings["paths"]["bare gits"]

    # This called takes time 

    repo_url_base = url_SSH_to_HTTPS(repo_url)
    bare_git_probable_path = bare_gits + "/" + repo_url_base[8:] + ".git"

    if(os.path.exists(bare_git_probable_path)):
        bare_git = bare_git_probable_path 
    else:
        bare_git  = FindGitRepo(bare_gits, repo_url)

    if bare_git == None:
        bare_tree_name = GetRepoBareTreePath(repo_url)
        clone_command = 'git clone "' + repo_url + '" "' + JoinPaths(bare_gits, bare_tree_name) + '" --bare'
        logging.debug("Cloning bare git with: " + clone_command)
        try:
            LaunchProcess(clone_command)
        except ProcessError as ex:
            ex.RaiseIfNotInOutput("already exists")
        bare_git = JoinPaths(bare_gits, bare_tree_name)

        # Setup some configs
        msg = "New branches track the remote of the current local branch"
        LaunchGitCommandAt("git config branch.autoSetupMerge always", bare_git, msg)

        msg = "Configuring branch.autoSetupMerge"
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
            print("Bare git " + bare_git + " could not be pulled")
            exit(-1)

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
        # print("git worktree add --force --detach " + new_repo_path + " " + repo_commitish["commit"])
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

    # print("parent_path "+ parent_path)
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

    temp_path = GetNewTemporaryPath(Settings["paths"])

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

