import sys
import logging
import traceback
from git import *
from data.settings import Settings
from processes.project import Project, UserChooseProject
from data.common import ValueNotEmpty

if __name__ != "__main__":
    Abort("This script is not meant to be imported, please run directly")

# Configure logging
# logging.basicConfig(stream = sys.stdout, level = logging.DEBUG)
logging.basicConfig(filename="/tmp/project_base.log",
                    filemode='a',
                            format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                            datefmt='%H:%M:%S', level = logging.DEBUG)

# logging.basicConfig(stream = sys.stdout, level = logging.INFO)

logging.info("=============== PROJECTBASE start ===============")
Settings.init()
if False == ValueNotEmpty(Settings, "url"):
    Settings["url"] = UserChooseProject()

Settings.start()
Project.init()

# Include here so paths are already ready in settings (find better way)
from menus.main import MainMenu

Settings.load_persistent_settings()

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

    PrintMenu(ProjectUrl, Project.Paths["project main"])

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


