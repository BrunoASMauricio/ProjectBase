import traceback
import logging
import sys

from completer import *
from settings import *
from common import *
from git import *

from run_executable import runProjectExecutable
from run_tests import runProjectTests
from run_linter import runLinter
from gitall import runGitall

from project import PROJECT

def PrintMenu(ProjectUrl, ProjectPath):
    ActiveSettings = GetActiveSettings()
    BuildBanner = ""
    if ActiveSettings["Mode"] == "Release":
        BuildBanner = ColorFormat(Colors.Blue, "Release build")
    else:
        BuildBanner = ColorFormat(Colors.Yellow, "Debug build")
    
    if ActiveSettings["Clone Type"] == "ssh":
        CloneType = ColorFormat(Colors.Magenta, "ssh access")
    else:
        CloneType = ColorFormat(Colors.Cyan, "http[s] access")

    print(ColorFormat(Colors.Yellow, """
 ______              __              __   ______
|   __ \.----.-----.|__|.-----.----.|  |_|   __ \.---.-.-----.-----.
|    __/|   _|  _  ||  ||  -__|  __||   _|   __ <|  _  |__ --|  -__|
|___|   |__| |_____||  ||_____|____||____|______/|___._|_____|_____|
                   |___|
""" ) + BuildBanner + """
("""  + ProjectUrl  + """ - """+CloneType+""")
("""  + ProjectPath + """)
First argument must be the URL of the target project
1) Generate project (build/pull from templates and configs)
2) Build project (launches the build environment for this purpose)
3) Run project executable
4) Run all tests
5) Run single test
6) Run linter
8) Run gitall.sh script
9) Clean binaries (remove all object and executable files, as well as the CMakeLists cache)
0) Project settings
"""+ColorFormat(Colors.Green, "Ctrl + D to exit") )

if __name__ != "__main__":
    Abort("This script is not meant to be imported, please run directly")

# Configure logging
logging.basicConfig(stream = sys.stdout, level = logging.INFO)
# logging.basicConfig(stream = sys.stdout, level = logging.DEBUG)

#               Setup project (main repository) data

# Parse arguments
ProjectArgs, ActionArgs = GetArguments()

# Commit or branch
if ProjectArgs.commit != None and ProjectArgs.branch != None:
    Abort("Please use either commit or branch, not both")

if ProjectArgs.url == None and (ProjectArgs.commit != None or ProjectArgs.branch != None):
    Abort("If you provide a commit/branch, you also need to provide a URL")

if ProjectArgs.url == None:
    ProjectUrl = UserChooseProject()
else:
    ProjectUrl = ProjectArgs.url

Projectbranch = ProjectArgs.branch
ProjectCommit = ProjectArgs.commit

Project = PROJECT(ProjectUrl, Projectbranch, ProjectCommit)

LoadSettings(Project)

# Setup auto complete
HistoryFile = Project.Paths["history"]+"/commands"
OldHistoryLength = setup_completer(HistoryFile)

# Setup necessary loop variables
StarterDirectory = os.getcwd()
NextInput = -1
Condition = True

while Condition == True:
    # Reset directory
    os.chdir(StarterDirectory)

    PrintMenu(ProjectUrl, Project.Paths["project_main"])

    if NextInput != -1:
        print("Previous command: "+str(NextInput))

    try:

        NextInput = GetNextOption()

        #                       Setup project
        if NextInput == "1":
            Project.Load()
            Project.Setup()
            Project.MakeCompileJson()

        #                       Build project
        elif NextInput == "2":
            Project.Load()
            Project.Build()

        #                     Run executable
        elif NextInput == "3":
            runProjectExecutable(ProjectUrl, Projectbranch, ProjectCommit, Project.Paths["executables"])

        #                      Run all tests
        elif NextInput == "4":
            runProjectTests(ProjectUrl, Projectbranch, ProjectCommit)

        #                    Run single test
        elif NextInput == "5":
            runProjectExecutable(ProjectUrl, Projectbranch, ProjectCommit, Project.Paths["tests"])

        elif NextInput == "6":
            # Only run load here if there was no previous load
            if len(Project.LoadedRepos) == 0:
                Project.Load()

            runLinter(Project)

        #                       Run gitall
        elif NextInput == "8":
            # Only run load here if there was no previous load
            if len(Project.LoadedRepos) == 0:
                Project.Load()

            runGitall(Project)

        #                   Clean project binaries
        elif NextInput == "9":
            Project.Clean()

        #                   Project settings
        elif NextInput == "0":
            MainSettingsMenu(Project)
            UpdateSettings(Project)

        else:
            print("Unkown option "+str(NextInput))

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


