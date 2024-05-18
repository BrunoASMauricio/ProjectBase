from project import *
from common import *

def printOptions():
    for key in linterallOperations:
        print("\t"+key+") "+linterallOperations[key][1])
    print("\t"+ColorFormat(Colors.Green, "Ctrl+C to exit"))

def check_project_json(Project):
    compile_commands_json = Project.Paths["project_main"] + "/compile_commands.json"
    if not os.path.exists(compile_commands_json ):
      print("File compile_commands.json does not exist in " + compile_commands_json )
      return 0
    return 1

def __runlinter(Project):
  if(check_project_json(Project)):
      # Allow python scripts to use ProjectBase scripts
    PrepareExecEnvironment(Project)
    runClangTidy = "cd " +Project.Paths["project_main"]+ "  &&  python ../../scripts/run-clang-tidy.py -use-color -format -style Microsoft -mythmode=linter"
    LaunchVerboseProcess( runClangTidy )

def __runformat(Project):
  if(check_project_json(Project)):
      # Allow python scripts to use ProjectBase scripts
    PrepareExecEnvironment(Project)
    runClangTidy = "cd " +Project.Paths["project_main"]+ "  &&  python ../../scripts/run-clang-tidy.py -use-color -format -style Microsoft -mythmode=format"
    LaunchVerboseProcess( runClangTidy )

def __cleanfiles(Project):
  if(check_project_json(Project)):
      # Allow python scripts to use ProjectBase scripts
    PrepareExecEnvironment(Project)
    runClangTidy = "cd " +Project.Paths["project_main"]+ "  &&  python ../../scripts/run-clang-tidy.py -use-color -format -style Microsoft -mythmode=clean"
    LaunchVerboseProcess( runClangTidy )

linterallOperations = {
    "0": [__runlinter             , "Runs clang-tidy linter in all project files"],
    "1": [__runformat           , "Runs clang-format in all project files creating tmp files when they exist format unconformities"],
    "2": [__cleanfiles               , "Clean all tmp_files created by option 2"]
}

def runLinter(Project):
    again = True
    while again:
        again = False
        printOptions()
        NextInput = GetNextOption()

        if NextInput in linterallOperations.keys():
            linterallOperations[NextInput][0](Project)
        else:
            print("Unrecognized input: " + NextInput)
            again = True

        # If this script was called standalone and without arguments (assumed manual, )
        if len(sys.argv) == 2 and __name__ == "__main__":
            # An option was selected, print options again
            again = True


if __name__ == "__main__":
    Abort("Do not run this script as a standalone")