import subprocess
import traceback
import logging
import sys

from git import GetRepoURL
from project import *
from common import *


def runProjectTests(RemoteRepoUrl, ProjectBranch, ProjetCommit):
    #global completer
    Project = PROJECT(RemoteRepoUrl, ProjectBranch, ProjetCommit)

    ErrorNames = []
    Successes = 0
    Tests = list(os.scandir(Project.Paths["tests"]))

    print("Running " + str(len(Tests)) + " tests in " + Project.Paths["tests"])

    for test in Tests:
        TestName = test.name
        try:
            print(ColorFormat(Colors.Blue, "\n\tRUNNING "+TestName))

            Result = subprocess.run(Project.Paths["tests"]+"/"+TestName, shell=True)

            print(ColorFormat(Colors.Blue, "\t"+TestName+" finished"))

            if Result.returncode != 0:
                print(ColorFormat(Colors.Red, "Return code = "+str(Result.returncode)))
                ErrorNames.append(TestName)
            else:
                print(ColorFormat(Colors.Green, "Return code = "+str(Result.returncode)))
                Successes = Successes + 1

        except Exception as ex:
            print("Error in running the executable\nException caught: "+str(ex))
            traceback.print_exc()

    print("\n")

    if len(ErrorNames) == 0:
        print(ColorFormat(Colors.Green, "No errors on "+str(Successes)+" tests!"))
    else:
        print(ColorFormat(Colors.Red, ("="*40)+"\n          Some errors reported\n"+("="*40)))
        print(ColorFormat(Colors.Green, "Successes: ["+str(Successes)+"]"))
        print(ColorFormat(Colors.Red, "Errors: ["+str(len(ErrorNames))+"]\n"+"\n".join(ErrorNames)))

if __name__ == "__main__":
    logging.basicConfig(stream = sys.stdout, level = logging.WARNING)
    # Get project repository
    RemoteRepoUrl = GetRepoURL()

    runProjectTests(RemoteRepoUrl)