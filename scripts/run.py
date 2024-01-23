from completer import *
from git import *
import traceback
import argparse
import sys

from common import *

from run_executable import runProjectExecutable
from run_tests import runProjectTests
from gitall import runGitall

from project import Project

def menu(project_url, project_path):
    print(Fore.YELLOW+"""
 ______              __              __   ______                    
|   __ \.----.-----.|__|.-----.----.|  |_|   __ \.---.-.-----.-----.
|    __/|   _|  _  ||  ||  -__|  __||   _|   __ <|  _  |__ --|  -__|
|___|   |__| |_____||  ||_____|____||____|______/|___._|_____|_____|
                   |___|                                            
"""+Style.RESET_ALL+"""
("""+project_url+""")
("""+project_path+""")
First argument must be the URL of the target project
1) Generate project (build/pull from templates and configs)
2) Build project (launches the build environment for this purpose)
3) Run project executable
4) Run all tests
5) Run single test
8) Run gitall.sh script
9) Clean binaries (remove all object and executable files, as well as the CMakeLists cache)
"""+Fore.GREEN+"Ctrl + D to exit"+Style.RESET_ALL)


def parse_arguments():
    # Initialize parser
    parser = argparse.ArgumentParser()

    # Adding optional argument
    parser.add_argument("-u", "--url", help = "Root repository's URL", default=None, required=False)

    parser.add_argument("-c", "--commit",
                        help = "Root repository's commit",
                        default=None, required=False, nargs=1)

    parser.add_argument("-b", "--branch",
                        help = "Root repository's branch",
                        default=None, required=False, type=str, nargs=1)

    # Read arguments from command line
    return parser.parse_known_args()


if __name__ != "__main__":
    print("This script is not meant to be imported, please run directly")
    sys.stdout.flush()
    sys.exit(-1)

# Configure logging
logging.basicConfig(stream = sys.stdout, level = logging.INFO)
# logging.basicConfig(stream = sys.stdout, level = logging.DEBUG)

#               Setup project (main repository) data
# Parse arguments
project_args, action_args = parse_arguments()

# Commit or branch
if project_args.commit != None and project_args.branch != None:
    print("Please use either commit or branch, not both")
    sys.exit(0)

if project_args.url == None and (project_args.commit != None or project_args.branch != None):
    print("If you provide a commit/branch, you also need to provide a URL")
    sys.exit(0)

if project_args.url == None:
    project_url = userChooseProject()
else:
    project_url = project_args.url

project_branch = project_args.branch
project_commit = project_args.commit

project = Project(project_url, project_branch, project_commit)

# Setup auto complete
histfile = project.paths["project_base"]+"/projectbase_configs/executables_history"
old_len = setup_completer(histfile)

# Setup necessary loop variables
pwd = os.getcwd()
next_input = -1
condition = True

while condition == True:
    # Reset directory
    os.chdir(pwd)

    menu(project_url, project.paths["project_main"])

    if next_input != -1:
        print("Previous command: "+str(next_input))

    try:

        # Provide automated option selection from command line, as well as normal input
        if len(action_args) != 0:
            next_input = action_args[0]
            del action_args[0]
        else:
            next_input = input("[<] ")

        #                       Setup project
        if next_input == "1":
            project.load()
            project.setup()

        #                       Build project
        elif next_input == "2":
            project.load()
            project.build()

        #                     Run executable
        elif next_input == "3":
            runProjectExecutable(project_url, project_branch, project_commit, project.paths["executables"])

        #                      Run all tests
        elif next_input == "4":
            runProjectTests(project_url, project_branch, project_commit)

        #                    Run single test
        elif next_input == "5":
            runProjectExecutable(project_url, project_branch, project_commit, project.paths["tests"])

        #                       Run gitall
        elif next_input == "8":
            # Only run load here if there was no previous load
            if len(project.loaded_repos) == 0:
                project.load()

            runGitall(project.loaded_repos)

        #                   Clean project binaries
        elif next_input == "9":
            project.clean()

        else:
            print("Unkown option "+str(next_input))

        readline.append_history_file(readline.get_current_history_length() - old_len, histfile)

        old_len = readline.get_current_history_length()

    except KeyboardInterrupt:
        print("\nKeyboard Interrupt. Press Ctrl+D to exit")

    except EOFError:
        sys.exit(0)

    except Exception as ex:
        print("Exception caught: "+str(ex))
        # printing stack trace
        traceback.print_exc()


