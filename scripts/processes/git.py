from processes.process import *
from data.settings import Settings, CLONE_TYPE
from data.common import RemoveSequentialDuplicates
from data.git import *
from processes.git_operations import *
from data.paths import GetParentPath, GetCurrentFolderName

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
Current folder ends in .git (weak way to check)
"""
def FolderIsBareGit(path):
    return GetCurrentFolderName(path).endswith(".git")

"""
Current folder has a .git file
"""
def FolderIsWorktree(path):
    return os.path.isdir(path + "/.git") or os.path.isfile(path + "/.git")

"""
Folder is either baregit or worktree
"""
def FolderIsGit(path):
    return FolderIsWorktree(path) or FolderIsBareGit(path)

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
        return None

    # multiple threads mean base_path can be randomly deleted
    if not os.path.isdir(base_path):
        return None

    # TODO: Is this really the better option?? Just blindly assume the flipped url is valid
    if SameUrl(repo_url, GetRepositoryUrl(base_path)):
        if repo_commitish != None:
            # Look into commit
            if repo_commitish["type"] == "commit":
                commit = GetRepoLocalCommit(base_path)
                if commit == repo_commitish["commit"]:
                    return RemoveSequentialDuplicates(base_path, "/")
            # Look into branch
            elif repo_commitish["type"] == "branch":
                branch = GetRepoLocalBranch(base_path)
                if branch == repo_commitish["branch"]:
                    return RemoveSequentialDuplicates(base_path, "/")
            else:
                raise Exception("Invalid commitish: "+str(repo_commitish))
        else:
            return RemoveSequentialDuplicates(base_path, "/")

    # multiple threads mean base_path can be randomly deleted
    if not os.path.isdir(base_path):
        return None

    # Now look at their files
    for sub_folder in os.listdir(base_path):
        full_path = base_path + "/" + sub_folder
        # Only look for directories that are git repositories (worktrees/bare gits)
        if not os.path.isdir(full_path):
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
        if os.path.isdir(path_to_search+"/"+Inode) and Inode != ".git":
            if depth == -1: # No depth limitation
                git_repos = git_repos + GetAllGitRepos(path_to_search+"/"+Inode)
            else:
                git_repos = git_repos + GetAllGitRepos(path_to_search+"/"+Inode, depth - 1)

    return git_repos

def SetupBareData(repo_url):
    repo_url       = FixUrl(repo_url)
    # ActiveSettings = Settings["active"]
    bare_gits      = Settings["paths"]["bare gits"]
    bare_git       = FindGitRepo(bare_gits, repo_url)
    
    if bare_git == None:
        bare_tree_name = GetRepoBareTreePath(repo_url)
        logging.debug("Cloning " + repo_url + " into " + bare_gits + "/" + bare_tree_name)
        LaunchProcess('git clone "' + repo_url + '" "' + bare_gits + "/" + bare_tree_name + '" --bare')
        bare_git = bare_gits + "/" + bare_tree_name

        if False == os.path.isdir(bare_git):
            print("Bare git " + bare_git + " could not be pulled")
            exit(-1)

    return bare_git

"""
Adds a worktree at target_path
Returns path to worktree: target_path + "/" + wortkree_name
"""
def AddWorkTree(bare_path, repo_url, repo_commitish, target_path):
    existing_tree  = FindGitRepo(target_path, repo_url, repo_commitish)
    if existing_tree != None and GetParentPath(existing_tree) == target_path:
        # Already exists, skip
        return existing_tree
    
    LaunchProcessAt('git worktree prune', bare_path)
    # --track: Set remote and merge configurations to track upstream
    # --force: Override safe guards and allow same branch name to be checked out by multiple worktrees
    # 
    repo_name = GetRepoNameFromURL(repo_url)
    new_repo_path = RemoveSequentialDuplicates(target_path + "/" + repo_name, "/")

    # In case we stopped before, remove existing temporary
    LaunchProcessAt("git worktree remove " + new_repo_path, bare_path)
    LaunchProcessAt("rm -rf " + new_repo_path)

    if repo_commitish != None:
        # If commit is defined, set it detached (it wont be updated)
        if repo_commitish["type"] == "commit":
            # print("git worktree add --force --detach " + new_repo_path + " " + repo_commitish["commit"])
            LaunchProcessAt("git worktree add --force --detach " + new_repo_path + " " + repo_commitish["commit"], bare_path)
        # If branch is defined, create a new random branch and make it follow the remote (it will be updated)
        elif repo_commitish["type"] == "branch":
            LaunchProcessAt("git worktree add --force  " + new_repo_path + " " + repo_commitish["branch"], bare_path)
            # # Setup so we can have a remote branch checked out in multiple local worktrees
            # # -b so the $local_branch is created
            # # --track so the $local_branch tracks the $remote_branch

            # # -f so it overrides any previous worktrees defined in the same path
            # # (project might have been present before and removed)
            # LaunchProcessAt("git worktree add "+Repo["source"]+" --track -f --checkout -b "+LocalName+" "+CommitIsh, Repo["bare path"])

            # LaunchProcessAt('git config --add remote.origin.fetch "+refs/heads/*:refs/remotes/origin/*"', Repo["source"])
            # LaunchProcessAt("git fetch origin '*:*'", Repo["source"])

            # # Ensure git push is for upstream
            # LaunchProcessAt("git config push.default upstream", Repo["source"])

            # # Make `git branch/switch/checkout` always merge from the starting point branch
            # LaunchProcessAt("git config branch.autoSetupMerge always", Repo["source"])
            # LaunchProcessAt("git config pull.rebase true", Repo["source"])
        else:
            raise Exception("Invalid commitish: "+str(repo_commitish))
    else:
        LaunchProcessAt("git worktree add --force " + new_repo_path, bare_path)

    # default_branch = GetRepoDefaultBranch()
    if not os.path.isdir(new_repo_path):
        raise Exception("Could not add worktree for " + repo_url + " at " + target_path + " from bare git at " + bare_path)
    
    # print("parent_path "+ parent_path)
    new_tree_path = FindGitRepo(new_repo_path, repo_url, repo_commitish, depth=1)
    if new_tree_path == None or new_tree_path != new_repo_path:
        raise Exception("Could not add correct worktree for " + repo_url + " at " + target_path + " from bare git at " + bare_path + ".\nGot " + str(new_tree_path) + " instead of "+str(new_repo_path))

    return new_repo_path

def RemoveWorkTree(bare_path, target_path):
    LaunchProcessAt("git worktree remove --force " + target_path, bare_path)

"""
Move worktree from from_path to to_path
TODO: dont just remove and add, also copy changes over
"""
def MoveWorkTree(bare_path, repo_url, repo_commitish, from_path, to_path):
    AddWorkTree(bare_path, repo_url, repo_commitish, to_path)
    RemoveWorkTree(bare_path, from_path)

def RepoIsClean(path):
    return "nothing to commit, working tree clean" in GetRepoStatus(path)

def GetRepoNameFromPath(Path):
    url = GetRepositoryUrl()
    if IsEmpty(url):
        raise Exception("Could not retrieve Name from path \"" + Path + "\"")

    return GetRepoNameFromURL(url["stdout"])