import subprocess
import traceback
import logging
import sys
import re

from common import *
from project import *


def runProjectExecutable(RemoteRepoUrl, ProjectBranch, ProjectCommit, Path):
    #global completer
    Project = PROJECT(RemoteRepoUrl, ProjectBranch, ProjectCommit)

    executables_available = []

    os.chdir(Project.Paths["project_main"])

    index = 0
    print("Available executables to run, found in "+Path+" (Ctrl-C to exit):")
    for entry in os.scandir(Path):
        # Must be fully executable
        if entry.stat().st_mode & 0o111 != 0o111:
            continue

        if not entry.is_file():
            continue

        print("\t["+str(index)+"] "+ColorFormat(Colors.Blue, entry.name))
        executables_available.append(entry.name)
        index += 1

    if index == 0:
        print("No executables found")
        return

    print("Use G or V as a prefix (G0/V0) to run with GDB or Valgrind respectively")
    print("Every space separated word in front of the first one will be passed as a parameter")

    try:
        user_input = GetNextOption()
        PrepareExecEnvironment(Project)

        # No input (Enter pressed)
        if len(user_input) == 0:
            return

        prefix = ""
        if user_input[0].upper() == "G":
            prefix = "gdb --args "
            user_input = user_input[1:]
        elif user_input[0].upper() == "S":
            prefix = "gdbserver 127.0.0.1:6175 "
            user_input = user_input[1:]
        elif user_input[0].upper() == "V":
            prefix = "valgrind --fair-sched=yes -s --leak-check=full --track-origins=yes"
            user_input = user_input[1:]

        number_regex = '^[0-9]+$'

        BaseInput = user_input.split(' ')[0]

        # Allow python scripts to use ProjectBase scripts
        AppendToEnvVariable("PYTHONPATH", Project.Paths["scripts"])

        # Obtain target executable
        if(re.search(number_regex, BaseInput)):
            # By index
            executable = Path+"/"+executables_available[int(BaseInput)]
        else:
            # By name
            if os.path.isfile(Path+"/"+BaseInput):
                executable = Path+"/"+BaseInput
            # By relative Project name
            elif os.path.isfile(Project.Paths["project_main"]+"/"+BaseInput):
                executable = Project.Paths["project_main"]+"/"+BaseInput
            # By absolute Project name
            elif os.path.isfile(BaseInput):
                executable = BaseInput
            else:
                print("Unkown executable: "+BaseInput)
                return

        # Setup base commands and its arguments
        BaseArguments = ' '.join([x for x in user_input.split(' ')[1:] if x != ""])

        logging.debug("Executable: "+executable)
        logging.debug("Base arguments: "+BaseArguments)

        # Theres a prefix, base command and arguments are a single argument
        CommandFragments = prefix+ " " + executable+" "+BaseArguments

        try:
            Result = subprocess.run(CommandFragments, shell=True)
            if Result.returncode != 0:
                print(ColorFormat(Colors.Red, CommandFragments+" returned code = "+str(Result.returncode)))
            else:
                print(ColorFormat(Colors.Green, CommandFragments+" returned code = "+str(Result.returncode)))
        except KeyboardInterrupt:
            print("Keyboard Interrupt")

    except Exception as ex:
        print("Error in running the executable\nException caught: "+str(ex))
        traceback.print_exc()

if __name__ == "__main__":
    logging.basicConfig(stream = sys.stdout, level = logging.WARNING)
    # Get Project repository
    RemoteRepoUrl = GetRepoURL()

    runProjectExecutable(RemoteRepoUrl)