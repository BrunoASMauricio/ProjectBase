import os
import re

from data.common import GetNow
from processes.filesystem import GetCurrentFolderName, JoinPaths

def GenerateLocalBranchName(branch):
    now = GetNow().replace(" ", "_").replace(":","_").replace(".","_").replace("-","_")
    return branch + "_ProjectBase_" + now

def PBBranchNameToNormalName(branch):
    if "_ProjectBase_" in branch:
        return branch.split("_ProjectBase_")[0]
    return branch

"""
From: https://<git repo>/<path el 1>/<path el 2>/<path el 3>/<path el 4>
To: git@<git repo>:<path el 1>/<path el 2>/<path el 3>/<path el 4>.git
"""
def url_HTTPS_to_SSH(url):
    if not url.startswith("https"):
        if not url.startswith("git@"):
            # Special case. url type is not recognized, so just use it as is
            return url
            # raise Exception(f"Cannot convert: {url}")
        else:
            # Already in ssh format
            return url

    if url.endswith(".git"):
        url = url[:-4]

    # split and remove repeated  '/'
    split_url = [ x for x in url.split("/") if len(x) != 0]
    return f"git@{split_url[1]}:{'/'.join(split_url[2:])}.git"

"""
From: git@<git repo>:<path el 1>/<path el 2>/<path el 3>/<path el 4>.git
To: https://<git repo>/<path el 1>/<path el 2>/<path el 3>/<path el 4>
"""
def url_SSH_to_HTTPS(url):
    if not url.startswith("git@"):
        if not url.startswith("https"):
            # Special case. url type is not recognized, so just use it as is
            return url
        else:
            # Already in ssh format
            return url

    head, path = url.split(":")
    remote = head.split("@")[1]

    if path.endswith(".git"):
        path = path[:-4]

    return f"https://{remote}/{path}"

"""
Flip url. If ssh url, change to HTTP and vice-versa
"""
def FlipUrl(url):
    if url.startswith("git@"):
        return url_SSH_to_HTTPS(url)
    elif url.startswith("https"):
        return url_HTTPS_to_SSH(url)
    else:
        return url
        # raise Exception(f"Cannot convert: {url}")

# Compiled once for efficiency
_GIT_BRANCH_RE = re.compile(
    r"""
    ^                       # start
    (?![/.])                # cannot start with . or /
    (?!.*\.\.)              # no ..
    (?!.*//)                # no //
    (?!.*@\{)               # no @{
    (?!.*\.lock$)           # cannot end with .lock
    (?!.*[ \x00-\x1F\x7F~^:?*\[\\])  # no forbidden chars / control chars / space
    [^/]+(?:/[^/]+)*        # slash-separated components
    (?<![/.])               # cannot end with . or /
    $                       # end
    """,
    re.VERBOSE,
)

def IsValidGitBranch(name):
    return isinstance(name, str) and bool(_GIT_BRANCH_RE.match(name))


def GetRepoNameFromURL(url):
    if url == None or len(url) == 0:
        raise Exception("Requested URL ("+url+") is empty")
    url = url_SSH_to_HTTPS(url)

    if url[-1] == '/':
        url = url[:-1]

    url = url.split('/')[-1].strip()
    if url.endswith(".git"):
        url = url[:-4]
    return url

def GetRepoBareTreePath(base_path, url):
    url = url_SSH_to_HTTPS(url)
    if url[-1] == '/':
        url = url[:-1]
    url = url.replace("https://","")
    url = url.replace("http://","")
    if not url.endswith(".git"):
        url = url+".git"
    return JoinPaths(base_path, url)

def SameUrl(url1, url2):
    try:
        equal = url_SSH_to_HTTPS(url1) == url_SSH_to_HTTPS(url2)
        return equal
    except:
        return False

"""
Local branches have custom unique names so they don't clash when checked out in multiple
projects
"""
def SameBranch(branch1, branch2):
    real_branch1 = branch1.split("_ProjectBase")[0]
    real_branch2 = branch2.split("_ProjectBase")[0]
    return real_branch1 == real_branch2

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

def CheckMergeOperationSuccess(ret):
    return True

def CheckMergeOperationConflict(ret):
    return "Merge conflict" in ret

def CheckRebaseOperationConflict(ret):
    return "could not apply" in ret

def CheckRebaseOperationOnGoing(ret):
    return "It seems that there is already a rebase-merge directory" in ret

def CheckRebaseOperationSuccess(ret):
    return "is up to date" in ret or "Successfully rebased" in ret


def CheckStatusIsRebaseOnGoing(status):
    return "use \"git rebase --abort\" to check out the original branch" in status

def CheckStatusConflict(status):
    return "both added" in ret


def CheckIfStatusIsClean(status):
    return "nothing to commit, working tree clean" in status

def CheckIfStatusIsDiverged(status):
    return "have diverged" in status

def CheckIfStatusIsAhead(status):
    return "branch is ahead" in status

def CheckIfStatusIsBehind(status):
    return "branch is behind" in status

def CheckIfStatusIsUpToDate(status):
    return "up to date" in status

def RepoIsClean(path):
    return CheckIfStatusIsClean(GetRepoStatus(path))


