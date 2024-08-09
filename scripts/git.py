from processes.process import *
from common import *
import datetime
import os

# Olds return data for git operations
OperationStatus = None

class Git():
    """
    Add a worktree of repo at TargetPath
    """
    @staticmethod
    def addWorktree(Repo, TargetPath):
        # Check required data (commit and branch
        CommitIsh = None
        CommitIshType = None
        DefaultBranch = Git.GetDefaultBranch(Repo["bare path"])
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
            CDLaunchReturn("git worktree add "+Repo["source"]+" --track -f --checkout -b "+LocalName+" "+CommitIsh, Repo["bare path"])

            CDLaunchReturn('git config --add remote.origin.fetch "+refs/heads/*:refs/remotes/origin/*"', Repo["source"])
            CDLaunchReturn("git fetch origin '*:*'", Repo["source"])

            # Ensure git push is for upstream
            CDLaunchReturn("git config push.default upstream", Repo["source"])

            # Make `git branch/switch/checkout` always merge from the starting point branch
            CDLaunchReturn("git config branch.autoSetupMerge always", Repo["source"])
            CDLaunchReturn("git config pull.rebase true", Repo["source"])

            #git config branch.branchB.merge refs/heads/branchB

        # Commit worktrees cant be updated (currently) so we snip the .git
        elif CommitIshType == "commit":
            logging.info("Adding new commit based worktree ("+CommitIsh+")")
            CDLaunchReturn("git worktree add "+Repo["source"]+" -f --detach "+CommitIsh, Repo["bare path"])
            # Will not be able to commit but cant remove remote, otherwise we
            # will not be able to figure out what URL the bare_git is related to

        else:
            raise Exception("Something went wrong figuring out worktree CommitIsh value")

    @staticmethod
    def DelWorktree(Repo):
        CDLaunchReturn("git worktree remove "+Repo["source"], Repo["bare path"])

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

def GetGitPaths(BasePath):
    GitRepos = []
    if not os.path.isdir(BasePath):
        logging.error(BasePath+" is not a valid directory")
        return

    CurrentDirectory = os.getcwd()
    sys.exit(0)
    os.chdir(BasePath)

    if LaunchSilentProcess("find -maxdepth 1 -name .git")["output"] != "":
        GitRepos.append(BasePath)

    os.chdir(CurrentDirectory)

    for Inode in os.listdir(BasePath):
        if os.path.isdir(BasePath+"/"+Inode) and Inode != ".git":
            GitRepos = GitRepos + GetGitPaths(BasePath+"/"+Inode)

    return GitRepos
