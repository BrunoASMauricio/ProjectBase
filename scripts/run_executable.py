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



    if index == 0:
        print("No executables found")
        return

    print("Use G or V as a prefix (G0/V0) to run with GDB or Valgrind respectively")
    print("Every space separated word in front of the first one will be passed as a parameter")

    try:

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