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
            print(Fore.BLUE+"\n\tRUNNING "+test_name+Style.RESET_ALL)

            result = subprocess.run(project.paths["tests"]+"/"+test_name, shell=True)

            print(Fore.BLUE+"\t"+test_name+" finished"+Style.RESET_ALL)

            if result.returncode != 0:
                print(Fore.RED+"Return code = "+str(result.returncode)+Style.RESET_ALL)
                error_names.append(test_name)
            else:
                print(Fore.GREEN+"Return code = "+str(result.returncode)+Style.RESET_ALL)
                successes = successes + 1

        except Exception as ex:
            print("Error in running the executable\nException caught: "+str(ex))
            traceback.print_exc()

    print("\n")

    if len(error_names) == 0:
        print(Fore.GREEN+"No errors on "+str(successes)+" tests!"+Style.RESET_ALL)
    else:
        print(Fore.RED+("="*40)+"\n          Some errors reported\n"+("="*40)+Style.RESET_ALL)
        print(Fore.GREEN+"Successes: ["+str(successes)+"]"+Style.RESET_ALL)
        print(Fore.RED+"Errors: ["+str(len(error_names))+"]")
        print("\n".join(error_names))
        print(Style.RESET_ALL)

if __name__ == "__main__":
    logging.basicConfig(stream = sys.stdout, level = logging.WARNING)
    # Get project repository
    remote_repo_url = getRepoURL()
    
    runProjectTests(remote_repo_url)