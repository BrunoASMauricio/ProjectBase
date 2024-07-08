import sys
import logging
import traceback
from git import *
from processes.project import Project

from data.settings import settings

if __name__ != "__main__":
    Abort("This script is not meant to be imported, please run directly")

# Configure logging
# logging.basicConfig(stream = sys.stdout, level = logging.DEBUG)
logging.basicConfig(stream = sys.stdout, level = logging.INFO)

# Initialize parser
settings.parse_arguments()

# Commit or branch
if settings["commit"] != None and settings["branch"] != None:
    Abort("Please use either commit or branch, not both")

if settings["url"] == None and (settings["commit"] != None or settings["branch"] != None):
    Abort("If you provide a commit/branch, you also need to provide a URL")

# Set base project settings
if settings["url"] == None:
    settings["url"] = UserChooseProject()


Project.init()

settings["ProjectName"]  = Project.name
settings["paths"] = Project.paths

from menus.main import MainMenu

settings.load_persistent_settings()

MainMenu.handle_input()

print("\nBye :)")
sys.exit(0)








from completer import *
from settings import *
from common import *

from gitall import runGitall

LoadSettings(Project)

# Setup necessary loop variables
next_input = -1
Condition = True

while Condition == True:
    # Reset directory
    os.chdir(StarterDirectory)

    PrintMenu(ProjectUrl, Project.Paths["project_main"])

    if next_input != -1:
        print("Previous command: "+str(next_input))

    try:
        next_input = GetNextOption()

        #                       Setup project
        if next_input == "1":
            Project.Load()
            Project.Setup()
            Project.MakeCompileJson()

        #                       Build project
        elif next_input == "2":
            Project.Load()
            Project.Build()

        #                     Run executable
        elif next_input == "3":
            runProjectExecutable(ProjectUrl, Projectbranch, ProjectCommit, Project.Paths["executables"])

        #                      Run all tests
        elif next_input == "4":
            runProjectTests(ProjectUrl, Projectbranch, ProjectCommit)

        #                    Run single test
        elif next_input == "5":
            runProjectExecutable(ProjectUrl, Projectbranch, ProjectCommit, Project.Paths["tests"])

        elif next_input == "6":
            # Only run load here if there was no previous load
            if len(Project.LoadedRepos) == 0:
                Project.Load()

            runLinter(Project)

        #                       Run gitall
        elif next_input == "8":
            # Only run load here if there was no previous load
            if len(Project.LoadedRepos) == 0:
                Project.Load()

            runGitall(Project)

        readline.append_history_file(readline.get_current_history_length() - OldHistoryLength, HistoryFile)

        OldHistoryLength = readline.get_current_history_length()

    except KeyboardInterrupt:
        print("\nKeyboard Interrupt. Press Ctrl+D to exit")

    except EOFError:
        print("Exiting ProjectBase")
        sys.exit(0)

    except Exception as Ex:
        print("Exception caught: "+str(Ex))
        # printing stack trace
        traceback.print_exc()


