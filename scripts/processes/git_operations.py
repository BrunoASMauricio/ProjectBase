import os
from processes.process import ProcessError, ParseProcessResponse, LaunchProcessAt
from data.common import IsEmpty

def ParseGitResult(git_command, path):
    if path == None:
        path = os.getcwd()
    return ParseProcessResponse(LaunchProcessAt(git_command, path, False))

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


def GetRepoLocalCommit(path = None):
    return ParseGitResult("git rev-parse HEAD", path)

def GetRepoLocalBranch(path = None):
    return ParseGitResult("git rev-parse --abbrev-ref HEAD", path)

def GetRepoRemoteCommit(path = None):
    return ParseGitResult("git rev-parse `git branch -r --sort=committerdate | tail -1`", path)

def GetRepoStatus(path = None):
    return ParseGitResult("git status", path)

def GetRepoRemote(path = None):
    return ParseGitResult("git remote show", path)

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
    if GetRepoLocalBranch(path) != "HEAD":
        ParseGitResult("git rebase", path)
        ParseGitResult("git pull", path)
        ParseGitResult("git pull origin", path)

def RepoPush(path = None):
    # Push to bare git
    ParseGitResult("git push", path)
    # Push to remote server
    ParseGitResult("git push origin HEAD:$(git for-each-ref --format='%(upstream:short)' $(git symbolic-ref -q HEAD))", path)

def GenAutoCommitMessage():
    return ""

"""
Stages all changes, within the current directory and its subdirectories.
"""
def RepoSaveChanges(path, commit_message=None):
    try:
        ParseGitResult('git add -A; git commit -m "' + commit_message + '"', path)
        print(f"Saved changes for {path}")
    except ProcessError as ex:
        ex.RaiseIfNotInOutput("nothing to commit, working tree clean")

def GetAllCommits(path):
    return ParseGitResult("git log --pretty='format:%H %s'", path)

def RepoResetToLatestSync(path=None):
    url = GetRepositoryUrl(path)
    branch = GetRepoLocalBranch(path)
    ParseGitResult("git reset --hard origin/" + branch, path)
    if path == None:
        path = os.getcwd()
    print("ON "+url+" resetting to origin/" + branch + " in "+path)

