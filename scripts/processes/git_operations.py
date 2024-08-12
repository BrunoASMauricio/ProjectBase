import os
from processes.process import MultipleCDLaunch
from data.common import IsEmpty

def ParseGitResult(git_command, path):
    if path == None:
        path = os.getcwd()
    return MultipleCDLaunch(git_command, path, False, 1)

# ================= GET operations =================

"""
Obtain the URL of the repository located at path
"""
def GetRepositoryUrl(path = None):
    import sys
    url = ParseGitResult("git config --get remote.origin.url", path)
    # if "brunoasmauricio/ProjectBase" in url:
    #     print("fuck")
    #     sys.exit(-1)
    return url

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
    ParseGitResult("git pull", path)

def RepoPush(path = None):
    ParseGitResult("git push", path)

def GenAutoCommitMessage():
    return ""

"""
Stages all changes, within the current directory and its subdirectories.
"""
def RepoSaveChanges(path = None, commit_message=""):
    if len(commit_message) == 0:
        commit_message = GenAutoCommitMessage()
    ParseGitResult("git add .; git commit -m " + commit_message, path)

def RepoResetToLatestSync(path=None):
    url = GetRepositoryUrl(path)
    branch = GetRepoLocalBranch(path)
    ParseGitResult("git reset --hard origin/" + branch, path)
    if path == None:
        path = os.getcwd()
    print("ON "+url+" resetting to origin/" + branch + " in "+path)

