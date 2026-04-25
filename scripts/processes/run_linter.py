import os
from data.settings import Settings
from processes.process import SetupLocalEnvVars, LaunchVerboseProcess

def _clang_tidy_base_command():
    """Build the common prefix for clang-tidy invocations, respecting single-thread mode."""
    j_flag = "-j 1" if Settings.get("single thread", False) else ""
    return (
        f"cd {Settings["paths"]["build cache"]} && "
        f"python {Settings["paths"]["scripts"]}/run-clang-tidy.py "
        f"-use-color -format -style Microsoft {j_flag}"
    ).strip()

def RunClangTidy(ClangCommand):
    compile_commands_json = Settings["paths"]["build cache"] + "/compile_commands.json"
    if not os.path.exists(compile_commands_json ):
        print("File compile_commands.json does not exist in " + compile_commands_json )
    else:
        SetupLocalEnvVars()
        LaunchVerboseProcess(ClangCommand)

def RunLinter():
    RunClangTidy(f"{_clang_tidy_base_command()} -mythmode=linter")

def RunFormat():
    RunClangTidy(f"{_clang_tidy_base_command()} -mythmode=format")

def CleanLinterFiles():
    RunClangTidy(f"{_clang_tidy_base_command()} -mythmode=clean")
