import os
from processes.process import MultipleCDLaunch
from data.git import GetRepoNameFromURL
from data.common import IsEmpty

def GetGitResult(git_command, path):
    if path == None:
        path = os.getcwd()
    return MultipleCDLaunch(git_command, path, False, 1)

# ================= GET operations =================

"""
Obtain the URL of the repository located at path
"""
def GetRepositoryUrl(path = None):
    import sys
    url = GetGitResult("git config --get remote.origin.url", path)
    if "brunoasmauricio/ProjectBase" in url:
        print("fuck")
        sys.exit(-1)
    return url

def GetRepoLocalCommit(path = None):
    return GetGitResult("git rev-parse HEAD", path)

def GetRepoLocalBranch(path = None):
    return GetGitResult("git rev-parse --abbrev-ref HEAD", path)

def GetRepoRemoteCommit(path = None):
    return GetGitResult("git rev-parse `git branch -r --sort=committerdate | tail -1`", path)

def GetRepoStatus(path = None):
    return GetGitResult("git status", path)

def GetRepoRemote(path = None):
    return GetGitResult("git remote show", path)

def GetRepoDefaultBranch(path = None):
    RemoteResult = GetRepoRemote(path)
    if RemoteResult["code"] != 0:
        Message  = "No remote setup, cant fetch default branch for "
        Message += GetRepositoryUrl(path) + " at " + path
        Message += "Code: " + str(RemoteResult["code"]) + "\n"
        Message += "Output: " + str(RemoteResult["stdout"]) + "\n"
        raise Exception(Message)

    DefaultBranch = GetGitResult("git remote show " + RemoteResult["stdout"] + " 2>/dev/null | sed -n '/HEAD branch/s/.*: //p'")
    if IsEmpty(DefaultBranch):
        Message  = "No default branch for "
        Message += GetRepositoryUrl(path) + " at " + path + "\n"
        Message += "Code: " + str(DefaultBranch["code"]) + "\n"
        Message += "Output: " + str(DefaultBranch["stdout"]) + "\n"
        raise Exception(Message)

    return DefaultBranch.split("/")[-1].strip()

# ================= SET operations =================

def RepoResetHard(path = None):
    return GetGitResult("git reset --hard", path)


def RepoCleanUntracked(path = None):
    return GetGitResult("git clean -fdx", path)

# ================= Update operations =================

def RepoFetch(path = None):
    GetGitResult("git fetch origin '*:*'", path)
