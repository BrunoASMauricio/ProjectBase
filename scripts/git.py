from colorama import Fore, Style
from time import sleep
from time import time
from process import *
from common import *
import datetime
import os

# Olds return data for git operations
operation_status = None

class Git():
    @staticmethod
    def getURL(target_directory=""):
        return multipleCDLaunch("git config --get remote.origin.url", target_directory, 10)

    @staticmethod
    def getDefaultBranch(target_directory=""):
        default_branch = multipleCDLaunch("git branch", target_directory, 5)
        if default_branch == "":
            raise Exception("There is no default branch for " + Git.getURL(target_directory) + " cannot proceed")
        return default_branch.split("\n")[0].split(" ")[1]

    @staticmethod
    def remoteBranchExists(branch, target_directory=""):
        branch = Git.getURL(target_directory)
        return "1" in parseProcessResponse(cdLaunchReturn("git ls-remote --heads "+branch+" "+branch+" | wc -l", target_directory))

    @staticmethod
    def getLocalBranch(target_directory=""):
        return parseProcessResponse(cdLaunchReturn("git rev-parse --abbrev-ref HEAD", target_directory))
    @staticmethod
    def getLocalCommit(target_directory=""):
        return parseProcessResponse(cdLaunchReturn("git rev-parse HEAD", target_directory))

    @staticmethod
    def getRemoteCommit(target_directory=""):
        return parseProcessResponse(cdLaunchReturn("git rev-parse `git branch -r --sort=committerdate | tail -1`", target_directory))
    @staticmethod
    def getStatus(target_directory=""):
        return multipleCDLaunch("git status", target_directory, 10)
        
    @staticmethod
    def resetHard(target_directory=""):
        cdLaunchReturn("git reset --hard", target_directory)

    @staticmethod
    def cleanUntracked(target_directory=""):
        cdLaunchReturn("git clean -fdx", target_directory)

    @staticmethod
    def isRepositoryClean():
        return "nothing to commit, working tree clean" in Git.getStatus()

    @staticmethod
    def findGitRepo(base_folder, url, commit=None):
        for sub_folder in os.listdir(base_folder):
            full_path = base_folder+"/"+sub_folder
            # Only look for directories
            if os.path.isdir(full_path):
                # Only search if has .git folder or ends with .git
                # So we can filter and only look in repositories and bare_gits
                if os.path.isfile(full_path+"/.git") or sub_folder.endswith(".git"):#os.path.isdir(full_path+".git"):
                    # Assume url is the same (until we can suppress username and
                    # pass request
                    path_url = Git.getURL(full_path)
                    if url == path_url:
                        if commit == None:
                            return full_path
                        
                        elif commit == Git.getLocalCommit(full_path):
                            return full_path
                # For other types of folders, recursively call findGitRepo
                else:
                    result = Git.findGitRepo(full_path, url, commit)
                    if result != None:
                        return result
        return None
    
    @staticmethod
    def repoMatches(repo, git_folder):
        path_url = Git.getURL(git_folder)
        if repo["url"] in path_url:
            if repo["commit"] == None:
                return True
            elif repo["commit"] == Git.getLocalCommit(git_folder):
                return True
        return False

    @staticmethod
    # Setup a git repositorys' bare data
    def setupBareData(bare_gits, repo):
        bare_git = Git.findGitRepo(bare_gits, repo["url"])
        if bare_git == None:
            logging.info('Cloning repository data into '+bare_gits)
            launchProcess('git clone "'+repo["url"]+'" "'+bare_gits+"/"+repo["bare_tree_path"]+'" --bare')

            repo["bare_path"] = bare_gits + "/" + repo["bare_tree_path"]

            if False == os.path.isdir(repo["bare_path"]):
                print("Bare git "+repo["bare_path"]+" could not be pulled")
                exit(-1)

        else:
            repo["bare_path"] = bare_git

    """
    Add a worktree of repo at target_path
    """
    @staticmethod
    def addWorktree(repo, target_path):
        # Check required data (commit and branch
        commit_ish = None
        commit_ish_type = None
        default_branch = Git.getDefaultBranch(repo["bare_path"])
        parent_path = "/".join(target_path.split("/")[:-1])
        repo["source"] = target_path

        if repo["branch"] != None:
            commit_ish = repo["branch"]
            commit_ish_type = "branch"

        if repo["commit"] != None:
            if commit_ish != None:
                logging.warning("Both branch and commit were defined for "+repo["name"]+", but only one can be used. Choosing commit. PLEASE ONLY USE ONE")
            commit_ish = repo["commit"]
            commit_ish_type = "commit"

        # Default to default branch
        if commit_ish == None:
            commit_ish = default_branch
            commit_ish_type = "branch"

        # Worktree already exists
        if os.path.isdir(target_path+"/.git"):
            # It is NOT the same repository, abort!
            if Git.getURL(target_path) != repo["url"]:
                # or Git.getLocalCommit(target_path) != repo["commit"]:
                message = "Worktree add coincides with different repo worktree!\n"
                message += Git.getURL(target_path) + " != " + repo["url"]+"\n"
                message += " OR \n"
                message += repo["source"] + "!=" + target_path
                raise Exception(message)
            else:
                return
        
        # Find repo
        #if Git.findGitRepo(parent_path, repo["url"], repo["commit"]) == None:
        # Or is not equal to repo["source"] ? Should never happen

        # Assume current time will lead to a unique branch
        now = str(datetime.datetime.now()).replace(" ", "_").replace(":","_").replace(".","_").replace("-","_")
        local_name = commit_ish+"_"+now

        launchProcess("rm -rf "+repo["source"])
        if commit_ish_type == "branch":
            logging.info("Adding new branch based worktree ("+commit_ish+")")
            # add new worktree

            # Setup so we can have a remote branch checked out in multiple local worktrees
            # -b so the $local_branch is created
            # --track so the $local_branch tracks the $remote_branch

            # -f so it overrides any previous worktrees defined in the same path
            # (project might have been present before and removed)
            cdLaunchReturn("git worktree add "+repo["source"]+" --track -f --checkout -b "+local_name+" "+commit_ish, repo["bare_path"])

            cdLaunchReturn('git config --add remote.origin.fetch "+refs/heads/*:refs/remotes/origin/*"', repo["source"])

            # Ensure git push is for upstream
            cdLaunchReturn("git config push.default upstream", repo["source"])

            # Make `git branch/switch/checkout` always merge from the starting point branch
            cdLaunchReturn("git config branch.autoSetupMerge always", repo["source"])
            cdLaunchReturn("git config pull.rebase true", repo["source"])

            #git config branch.branchB.merge refs/heads/branchB

        # Commit worktrees cant be updated (currently) so we snip the .git
        elif commit_ish_type == "commit":
            logging.info("Adding new commit based worktree ("+commit_ish+")")
            cdLaunchReturn("git worktree add "+repo["source"]+" --detach "+commit_ish, repo["bare_path"])
            cdLaunchReturn("git remote rm origin", repo["source"])

        else:
            raise Exception("Something went wrong figuring out worktree commit_ish value")
        
    @staticmethod
    def delWorktree(repo):
        cdLaunchReturn("git worktree remove "+repo["source"], repo["bare_path"])

def getStatus():
    """
    Retrieves the status of the current repository
    """
    
    url = Git.getURL()
    repository_name = getRepoName(url)
    local_commit = Git.getLocalCommit()
    remote_commit = Git.getRemoteCommit()

    lines = list()
    operation_status = None

    if Git.isRepositoryClean():
        lines.append("|"+Fore.BLUE+repository_name+Style.RESET_ALL+" ("+Fore.GREEN+"clean"+Style.RESET_ALL+")" + Fore.YELLOW + " URL: " + Style.RESET_ALL + url)
        print('\n|'.join(lines))
    else:
        lines.append("|"+Fore.BLUE+repository_name+Style.RESET_ALL+" ("+Fore.RED+"dirty"+Style.RESET_ALL+")")
        lines.append("\n|"+Git.getStatus().replace("\n","\n|"))
        operation_status = repository_name

        if local_commit == remote_commit:
            lines.append(Fore.YELLOW+"Commit: "+Style.RESET_ALL+local_commit)
        else:
            lines.append(Fore.RED+"Commit: "+Style.RESET_ALL+local_commit+" != "+remote_commit)

        lines.append(Fore.YELLOW+"URL: "+Style.RESET_ALL+url)
        lines.append(Fore.YELLOW+"Local Path: "+Style.RESET_ALL+os.getcwd())

        print("-"*79)
        print('\n|'.join(lines))
        print("-"*79)

    return operation_status


def checkoutBranch(branch):
    launchProcess("git pull")
    result = launchProcess("git checkout "+branch)
    if result["stdout"] != "":
        repo_name = getRepoName(launchProcess("git config --get remote.origin.url")["stdout"][:-1])
        print(repo_name+": "+result["stdout"])

def fullCleanUpdate():
    """
    Fully cleans the repository before pulling
    """
    Git.resetHard()
    Git.cleanUntracked()
    launchVerboseProcess("git pull")

def fullDirtyUpdate():
    """
    Updates the repository without reset (NEED TO SETUP FAST FORWARD)
    """
    #if Git.isRepositoryClean():
    launchVerboseProcess("git pull")

def globalCommit(commit_message=""):
    """
    Performs a commit with the given message on all repos
    """
    if not Git.isRepositoryClean():
        # Add normal files
        launchVerboseProcess("git add *")
        # Add dotfiles
        launchVerboseProcess("git add .")
        # Include removed/moved files
        launchVerboseProcess("git add -u")
        launchVerboseProcess('git commit -m "'+commit_message+'"')
        x = 0
        while Git.isRepositoryClean() == False:
            if x > 5:
                print(Fore.RED+"ERROR, failed to push changes after 5 attempts"+Style.RESET_ALL)
                return
            launchVerboseProcess("git push -f")
            x = x + 1

def globalPush():
    launchVerboseProcess("git push")

def registerDirtyRepo():
    operation_status = []

    if not Git.isRepositoryClean():
        url = Git.getURL()
        name = getRepoName(url)
        operation_status.append([name, url, os.getcwd()])
    return operation_status



def getAllStatus(path_to_dir):
    """
    Perform git status on all subsequent directories
    """

def userChooseProject():
    """
    Print currently available projects and ask user
    to choose one of them
    """
    
    index = 0
    projects_available = []
    print("Installed projects:")
    for entry in os.scandir("projects"):
        if entry.name == "" or entry.name == ".gitignore":
            continue

        """
        Repositories can have the same name (different URLs)
        As such, we cannot rely on the name of the project to
        """

        if not entry.is_dir():
            print("Unexpected file in projects "+entry.path+"/"+entry.name)
            continue

        url=""
        folder_path = entry.path
        file_path = os.path.join(folder_path, "root_url.txt")

        if os.path.isfile(file_path):
            with open(file_path, "r") as file:
                url = file.read()[:-1].strip()
        else:
            print(Fore.RED+"Cannot open project "+entry.name+", root_url.txt not found"+Style.RESET_ALL)
            continue

        if url == "":
            continue

        name = getRepoName(url)
        print("\t["+str(index)+"] "+Fore.BLUE+name+Style.RESET_ALL+" : "+url)
        projects_available.append(url)
        index += 1
    if index == 0:
        user_input = input("Remote project repository URL: ")
    else:
        user_input = input("Insert a number to choose from the existing projects, or a URL to download a new one: ")
    
    try:
        inserted_index = int(user_input)
        # User chose an index
        remote_repo_url = projects_available[inserted_index]
    except Exception as ex:
        remote_repo_url = user_input
    
    return remote_repo_url


def getRepoName(url):
    if len(url) == 0:
        logging.error("Empty URL")
        return

    if url[-1] == '/':
        url = url[:-1]
    return url.split('/')[-1]

def getRepoBareTreePath(url):
    if url[-1] == '/':
        url = url[:-1]
    url = url.replace("https://","")
    url = url.replace("http://","")
    return url+".git"

def getRepoURL():
    if len(sys.argv) > 1:
        return sys.argv[1]
    else:
        return userChooseProject()
