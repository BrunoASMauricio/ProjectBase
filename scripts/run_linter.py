from project import *
from common import *

def runLinter(RemoteRepoUrl, ProjectBranch, ProjetCommit):
    #global completer
    Project = PROJECT(RemoteRepoUrl, ProjectBranch, ProjetCommit)

    compile_commands_json = Project.Paths["project_main"] + "/compile_commands.json"
    if not os.path.exists(compile_commands_json ):
      print("File compile_commands.json does not exist in " + compile_commands_json )

    # Allow python scripts to use ProjectBase scripts
    PrepareExecEnvironment(Project)

    print("Select linting options")

    print("[1] Runs clang-tidy in all project files")
    print("[2] TODO Runs clang-tidy in dirty project files")

    print("[4] TODO Runs clang-format in all project files without performing changes")
    print("[5] TODO Runs clang-format in dirty project files without performing changes")

    print("[7] TODO Runs clang-format in all project files performing changes")
    print("[8] TODO Runs clang-format in dirty project files performing changes")
    # Run linter On all Files
    runClangTidy = "cd " +Project.Paths["project_main"]+ "  &&  python ../../scripts/run-clang-tidy.py -use-color -export-fixes clang_tidy_fixes.yaml"

    # Appply fixes (Apply clang-formated in all files)
   
    LaunchVerboseProcess( runClangTidy )

if __name__ == "__main__":
    logging.basicConfig(stream = sys.stdout, level = logging.WARNING)
    # Get project repository
    RemoteRepoUrl = GetRepoURL()

    runLinter(RemoteRepoUrl)