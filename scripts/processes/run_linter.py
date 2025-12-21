import os
from data.settings import Settings
from processes.process import SetupLocalEnvVars, LaunchVerboseProcess

def RunClangTidy(ClangCommand):
    compile_commands_json = Settings["paths"]["project main"] + "/compile_commands.json"
    if not os.path.exists(compile_commands_json ):
        print("File compile_commands.json does not exist in " + compile_commands_json )
    else:
        SetupLocalEnvVars()
        LaunchVerboseProcess(ClangCommand)

def RunLinter():
    RunClangTidy("cd "  + Settings["paths"]["project main"] + "  &&  python ../../scripts/run-clang-tidy.py -use-color -format -style Microsoft -mythmode=linter")

def RunFormat():
    RunClangTidy("cd " + Settings["paths"]["project main"]+ "  &&  python ../../scripts/run-clang-tidy.py -use-color -format -style Microsoft -mythmode=format")

def CleanLinterFiles():
    RunClangTidy("cd " + Settings["paths"]["project main"]+ "  &&  python ../../scripts/run-clang-tidy.py -use-color -format -style Microsoft -mythmode=clean")
