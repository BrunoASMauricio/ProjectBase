from process import *
from common import *
import datetime
import os

# Olds return data for git operations
OperationStatus = None

class Git():
    @staticmethod
    def GetURL(TargetDirectory=""):
        return MultipleCDLaunch("git config --get remote.origin.url", TargetDirectory, 1)

    @staticmethod
    def GetDefaultBranch(TargetDirectory=""):
        DefaultBranch = MultipleCDLaunch("git branch", TargetDirectory, 1)
        if DefaultBranch == "":
            raise Exception("There is no default branch for " + Git.GetURL(TargetDirectory) + " cannot proceed")
        return DefaultBranch.split("\n")[0].split(" ")[1]

    @staticmethod
    def GetLocalCommit(TargetDirectory=""):
        return ParseProcessResponse(CDLaunchReturn("git rev-parse HEAD", TargetDirectory))

    @staticmethod
    def GetRemoteCommit(TargetDirectory=""):
        return ParseProcessResponse(CDLaunchReturn("git rev-parse `git branch -r --sort=committerdate | tail -1`", TargetDirectory))
    @staticmethod
    def GetStatus(TargetDirectory=""):
        return MultipleCDLaunch("git status", TargetDirectory, 10)

    @staticmethod
    def ResetHard(TargetDirectory=""):
        CDLaunchReturn("git reset --hard", TargetDirectory)

    @staticmethod
    def CleanUntracked(TargetDirectory=""):
        CDLaunchReturn("git clean -fdx", TargetDirectory)

    @staticmethod
    def IsRepositoryClean():
        return "nothing to commit, working tree clean" in Git.GetStatus()

    @staticmethod
    def FindGitRepo(BaseFolder, Url, Commit=None):
        for SubFolder in os.listdir(BaseFolder):
            FullPath = BaseFolder+"/"+SubFolder
            # Only look for directories
            if os.path.isdir(FullPath):
                # Only search if has .git folder or ends with .git
                # So we can filter and only look in repositories and BareGits
                if os.path.isfile(FullPath+"/.git") or SubFolder.endswith(".git"):
                    # Assume url is the same (until we can suppress username and
                    # pass request
                    PathUrl = Git.GetURL(FullPath)
                    if Url == PathUrl:
                        PathCommit = Git.GetLocalCommit(FullPath)
                        if Commit == None:
                            return FullPath
                        elif Commit == PathCommit:
                            return FullPath
                # For other types of folders, recursively call FindGitRepo
                else:
                    Result = Git.FindGitRepo(FullPath, Url, Commit)
                    if Result != None:
                        return Result
        return None

    @staticmethod
    # Setup a git repositorys' bare data
    def SetupBareData(BareGits, Repo):
        BareGit = Git.FindGitRepo(BareGits, Repo["url"])
        if BareGit == None:
            logging.info('Cloning repository data into '+BareGits)
            LaunchProcess('git clone "'+Repo["url"]+'" "'+BareGits+"/"+Repo["bare_tree_path"]+'" --bare')

            Repo["bare_path"] = BareGits + "/" + Repo["bare_tree_path"]

            if False == os.path.isdir(Repo["bare_path"]):
                print("Bare git "+Repo["bare_path"]+" could not be pulled")
                exit(-1)

        else:
            Repo["bare_path"] = BareGit

    """
    Add a worktree of repo at TargetPath
    """
    @staticmethod
    def addWorktree(Repo, TargetPath):
        # Check required data (commit and branch
        CommitIsh = None
        CommitIshType = None
        DefaultBranch = Git.GetDefaultBranch(Repo["bare_path"])
        Repo["source"] = TargetPath

        if Repo["branch"] != None:
            CommitIsh = Repo["branch"]
            CommitIshType = "branch"

        if Repo["commit"] != None:
            if CommitIsh != None:
                logging.warning("Both branch and commit were defined for "+Repo["name"]+", but only one can be used. Choosing commit. PLEASE ONLY USE ONE")
            CommitIsh = Repo["commit"]
            CommitIshType = "commit"

        # Default to default branch
        if CommitIsh == None:
            CommitIsh = DefaultBranch
            CommitIshType = "branch"

        # Worktree already exists
        if os.path.isdir(TargetPath+"/.git"):
            # It is NOT the same Repository, abort!
            if Git.GetURL(TargetPath) != Repo["url"]:
                # or Git.GetLocalCommit(TargetPath) != Repo["commit"]:
                Message = "Worktree add coincides with different repo worktree!\n"
                Message += Git.GetURL(TargetPath) + " != " + Repo["url"]+"\n"
                Message += " OR \n"
                Message += Repo["source"] + "!=" + TargetPath
                raise Exception(Message)
            else:
                return

        # Assume current time will lead to a unique branch
        Now = str(datetime.datetime.now()).replace(" ", "_").replace(":","_").replace(".","_").replace("-","_")
        LocalName = CommitIsh + "_Local_" + Now

        LaunchProcess("rm -rf " + Repo["source"])
        if CommitIshType == "branch":
            logging.info("Adding new branch based worktree (" + CommitIsh + ")")
            # add new worktree

            # Setup so we can have a remote branch checked out in multiple local worktrees
            # -b so the $local_branch is created
            # --track so the $local_branch tracks the $remote_branch

            # -f so it overrides any previous worktrees defined in the same path
            # (project might have been present before and removed)
            CDLaunchReturn("git worktree add "+Repo["source"]+" --track -f --checkout -b "+LocalName+" "+CommitIsh, Repo["bare_path"])

            CDLaunchReturn('git config --add remote.origin.fetch "+refs/heads/*:refs/remotes/origin/*"', Repo["source"])

            # Ensure git push is for upstream
            CDLaunchReturn("git config push.default upstream", Repo["source"])

            # Make `git branch/switch/checkout` always merge from the starting point branch
            CDLaunchReturn("git config branch.autoSetupMerge always", Repo["source"])
            CDLaunchReturn("git config pull.rebase true", Repo["source"])

            #git config branch.branchB.merge refs/heads/branchB

        # Commit worktrees cant be updated (currently) so we snip the .git
        elif CommitIshType == "commit":
            logging.info("Adding new commit based worktree ("+CommitIsh+")")
            CDLaunchReturn("git worktree add "+Repo["source"]+" -f --detach "+CommitIsh, Repo["bare_path"])
            # Will not be able to commit but cant remove remote, otherwise we
            # will not be able to figure out what URL the bare_git is related to

        else:
            raise Exception("Something went wrong figuring out worktree CommitIsh value")

    @staticmethod
    def DelWorktree(Repo):
        CDLaunchReturn("git worktree remove "+Repo["source"], Repo["bare_path"])

def GetStatus():
    """
    Retrieves the status of the current repository
    """

    Url = Git.GetURL()
    RepositoryName = GetRepoNameFromURL(Url)
    LocalCommit = Git.GetLocalCommit()
    RemoteCommit = Git.GetRemoteCommit()

    Lines = list()
    OperationStatus = None

    StatusString = "\t|"+ColorFormat(Colors.Blue, RepositoryName)
    if Git.IsRepositoryClean():
        StatusString += " ("+ColorFormat(Colors.Green, "clean")+")"
        StatusString += ColorFormat(Colors.Yellow, " URL: ") + Url
        Lines.append(StatusString)
        print(''.join(Lines))
    else:
        StatusString += " ("+ColorFormat(Colors.Red,"dirty")+")"
        Lines.append(StatusString)
        Lines.append("\n\t|"+Git.GetStatus().replace("\n","\n\t|"))
        OperationStatus = RepositoryName

        if LocalCommit == RemoteCommit:
            Lines.append(ColorFormat(Colors.Yellow, "Commit: ")+LocalCommit)
        else:
            Lines.append(ColorFormat(Colors.Red, "Commit: ")+LocalCommit+" != "+RemoteCommit)

        Lines.append(ColorFormat(Colors.Yellow, "URL: ")+Url)
        Lines.append(ColorFormat(Colors.Yellow, "Local Path: ")+os.getcwd())

        print("\t"+"-"*50)
        print('\n\t|'.join(Lines))
        print("\t"+"-"*50)

    return OperationStatus


def CheckoutBranch(Branch):
    logging.info("Cleaning up "+GetRepoNameFromPath(os.getcwd()))

    LaunchProcess("git pull")
    Result = LaunchProcess("git checkout "+Branch)
    if Result["output"] != "":
        RepoName = GetRepoNameFromURL(LaunchProcess("git config --get remote.origin.url")["output"][:-1])
        print(RepoName+": "+Result["output"])

def FullCleanUpdate():
    """
    Fully cleans the repository before pulling
    """
    logging.info("Cleaning up "+GetRepoNameFromPath(os.getcwd()))
    Git.ResetHard()
    Git.CleanUntracked()
    LaunchVerboseProcess("git pull")

def FullDirtyUpdate():
    """
    Updates the repository without reset (NEED TO SETUP FAST FORWARD)
    """
    #if Git.IsRepositoryClean():
    LaunchVerboseProcess("git pull")

def GlobalCommit(CommitMessage=""):
    """
    Performs a commit with the given message on all repos
    """
    if not Git.IsRepositoryClean():
        # Add normal files
        LaunchVerboseProcess("git add *")
        # Add dotfiles
        LaunchVerboseProcess("git add .")
        # Include removed/moved files
        LaunchVerboseProcess("git add -u")
        LaunchVerboseProcess('git commit -m "'+CommitMessage+'"')

def GlobalPush():
    logging.info("Pushing "+GetRepoNameFromPath(os.getcwd()))
    PushStatus = LaunchVerboseProcess("git push -u origin $(git branch --show-current)")

    if PushStatus["code"] != 0:
        # TODO Add possibility to open a terminal on that git
        logging.error("Could not push (" + ColorFormat(Colors.Yellow, str(PushStatus["code"])) + ")!\n "+ColorFormat(Colors.Red, PushStatus["output"]))
        logging.error("Local path: "+ColorFormat(Colors.Yellow, os.getcwd()))
        ForcePush = UserYesNoChoice("Try force push?")
        if ForcePush == True:
            PushStatus = LaunchVerboseProcess("git push -u origin $(git branch --show-current) -f")
            if PushStatus["code"] != 0:
                logging.error(ColorFormat(Colors.Red, "Could not force push ("+str(PushStatus["code"])+"): "+PushStatus["output"]))

def UserChooseProject():
    """
    Print currently available projects and ask user
    to choose one of them
    """

    Index = 0
    ProjectsAvailable = []
    print("Installed projects:")
    for Entry in os.scandir("projects"):
        if Entry.name == "" or Entry.name == ".gitignore":
            continue

        """
        Repositories can have the same name (different URLs)
        As such, we cannot rely on the name of the project to
        """

        if not Entry.is_dir():
            print("Unexpected file in projects "+Entry.path+"/"+Entry.name)
            continue

        Url = ""
        FolderPath = Entry.path
        FilePath = os.path.join(FolderPath, "root_url.txt")

        if os.path.isfile(FilePath):
            with open(FilePath, "r") as file:
                Url = file.read()[:-1].strip()
        else:
            print(ColorFormat(Colors.Red, "Cannot open project "+Entry.name+", root_url.txt not found"))
            continue

        if Url == "":
            continue

        Name = GetRepoNameFromURL(Url)
        print("\t["+str(Index)+"] "+ColorFormat(Colors.Blue, Name)+" : "+Url)
        ProjectsAvailable.append(Url)
        Index += 1
    if Index == 0:
        UserInput = input("Remote project repository URL: ")
    else:
        UserInput = input("Insert a number to choose from the existing projects, or a URL to download a new one: ")

    try:
        InsertedIndex = int(UserInput)
        # User chose an Index
        RemoteRepoUrl = ProjectsAvailable[InsertedIndex]
    except Exception as Ex:
        # Not an Index, assume URL
        RemoteRepoUrl = UserInput

    return RemoteRepoUrl

def GetRepoNameFromURL(Url):
    if Url == None or len(Url) == 0:
        raise Exception("Requested URL ("+Url+") is empty")

    if Url[-1] == '/':
        Url = Url[:-1]
    return Url.split('/')[-1].strip()

def GetRepoNameFromPath(Path):
    CurrentDirectory = os.getcwd()

    os.chdir(Path)

    UrlOutput = LaunchProcess("git config --get remote.origin.url")
    os.chdir(CurrentDirectory)
    if UrlOutput == None or len(UrlOutput["output"]) == 0:
        raise Exception("Could not retrieve Name from path \"" + Path + "\"")

    return GetRepoNameFromURL(UrlOutput["output"])

def GetRepoBareTreePath(Url):
    if Url[-1] == '/':
        Url = Url[:-1]
    Url = Url.replace("https://","")
    Url = Url.replace("http://","")
    return Url+".git"

def GetRepoURL():
    if len(sys.argv) > 1:
        return sys.argv[1]
    else:
        return UserChooseProject()

def GetGitPaths(BasePath):
    GitRepos = []
    if not os.path.isdir(BasePath):
        logging.error(BasePath+" is not a valid directory")
        return

    CurrentDirectory = os.getcwd()
    os.chdir(BasePath)

    if LaunchSilentProcess("find -maxdepth 1 -name .git")["output"] != "":
        GitRepos.append(BasePath)

    os.chdir(CurrentDirectory)

    for Inode in os.listdir(BasePath):
        if os.path.isdir(BasePath+"/"+Inode) and Inode != ".git":
            GitRepos = GitRepos + GetGitPaths(BasePath+"/"+Inode)

    return GitRepos
