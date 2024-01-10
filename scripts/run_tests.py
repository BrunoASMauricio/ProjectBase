import logging
import traceback
import sys

from common import *
from project import *


def runProjectTests(remote_repo_url, project_branch, project_commit):
    #global completer
    project = Project(remote_repo_url, project_branch, project_commit)

    error_names = []
    successes = 0
    tests = list(os.scandir(project.paths["tests"]))

    print("Running "+str(len(tests))+" tests in "+project.paths["tests"])

    for test in tests:
        test_name = test.name
        try:
            print(ColorFormat(Colors.Blue, "\n\tRUNNING "+test_name))

            result = subprocess.run(project.paths["tests"]+"/"+test_name, shell=True)

            print(ColorFormat(Colors.Blue, "\t"+test_name+" finished"))

            if result.returncode != 0:
                print(ColorFormat(Colors.Red, "Return code = "+str(result.returncode)))
                error_names.append(test_name)
            else:
                print(ColorFormat(Colors.Green, "Return code = "+str(result.returncode)))
                successes = successes + 1

        except Exception as ex:
            print("Error in running the executable\nException caught: "+str(ex))
            traceback.print_exc()

    print("\n")

    if len(error_names) == 0:
        print(ColorFormat(Colors.Green, "No errors on "+str(successes)+" tests!"))
    else:
        print(ColorFormat(Colors.Red, ("="*40)+"\n          Some errors reported\n"+("="*40)))
        print(ColorFormat(Colors.Green, "Successes: ["+str(successes)+"]"))
        print(ColorFormat(Colors.Red, "Errors: ["+str(len(error_names))+"]\n"+"\n".join(error_names)))

if __name__ == "__main__":
    logging.basicConfig(stream = sys.stdout, level = logging.WARNING)
    # Get project repository
    remote_repo_url = getRepoURL()
    
    runProjectTests(remote_repo_url)