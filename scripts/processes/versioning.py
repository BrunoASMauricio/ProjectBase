from data.settings     import Settings
from processes.project import Project
from data.colors       import ColorFormat, Colors
from processes.git     import GetAllGitRepos, GetRepoNameFromPath, RepoIsClean
from processes.process import OpenBashOnDirectoryAndWait

def GetPresentPaths():
    repos = Project.GetRepositories()
    known_paths   = [repos[repo]["full worktree path"] for repo in repos]
    all_git_repos = GetAllGitRepos(Settings["paths"]["project main"])

    unknown_paths = [repo for repo in all_git_repos if repo not in known_paths]
    all_paths = known_paths + unknown_paths
    return all_paths, known_paths, unknown_paths

def DirectlyManageSingleRepository():
    all_paths, known_paths, _ = GetPresentPaths()

    print("What repo to manage:")
    for path_ind in range(len(all_paths)):
        path = all_paths[path_ind]
        Message =  "[" + str(path_ind) + "] "
        Message += GetRepoNameFromPath(path) + " ("

        if RepoIsClean(path):
            Message += ColorFormat(Colors.Green, "clean")
        else:
            Message += ColorFormat(Colors.Red, "dirty")
        Message += ") "

        # Managed or Unmanaged
        if path in known_paths:
            Message += ColorFormat(Colors.Yellow, " (managed)")
        else:
            Message += ColorFormat(Colors.Magenta, " (unmanaged)")
        
        # Print path (relative to cwd)
        Message += "." + path.replace(Settings["paths"]["project main"], "")
        print(Message)

    UserInput = input("[<] ")
    OpenBashOnDirectoryAndWait(all_paths[int(UserInput)])

from data.common import RemoveNone, IsEmpty
from processes.process import RunOnFolders
from processes.git_operations import GetRepoStatus

def PrintProjectStatus():
    _, known_paths, unknown_paths = GetPresentPaths()

    print("\nManaged repositories:")
    known_repo_status = RunOnFolders(known_paths, GetRepoStatus)
    known_repo_status = RemoveNone(known_repo_status)

    print("\nUnmanaged repositories:")
    unknown_repo_status = RunOnFolders(unknown_paths, GetRepoStatus)
    unknown_repo_status = RemoveNone(unknown_repo_status)

    print("\nProject is ", end="")
    if IsEmpty(known_repo_status):
        print(ColorFormat(Colors.Green, "clean"))
    else:
        print(ColorFormat(Colors.Red, "dirty ("+str(len(known_repo_status))+": "+', '.join(known_repo_status)+")"))

    if not IsEmpty(unknown_repo_status):
        print("There are dirty unknown git repositories:")
        print(ColorFormat(Colors.Red, "dirty ("+str(len(unknown_repo_status))+": "+', '.join(unknown_repo_status)+")"))

