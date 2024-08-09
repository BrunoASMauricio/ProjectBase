import os
from data.settings     import Settings
from processes.project import Project
from data.colors       import ColorFormat, Colors
from processes.git     import GetAllGitRepos, GetRepoNameFromPath, RepoIsClean
from processes.process import OpenBashOnDirectoryAndWait

def DirectlyManageSingleRepository():
    repos = Project.GetRepositories()
    known_paths   = [repos[repo]["full worktree path"] for repo in repos]
    all_git_repos = GetAllGitRepos(Settings["paths"]["project main"])

    unknown_paths = [repo for repo in all_git_repos if repo not in known_paths]
    all_paths = known_paths + unknown_paths

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