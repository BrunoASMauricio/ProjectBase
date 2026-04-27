import argparse
from data.json import *
from data.error import *
from data.common import *
from data.git import GetRepoNameFromURL
from enum import Enum
import json

class CLONE_TYPE(Enum):
    HTTPS = "https"
    SSH   = "ssh"
    NONE  = "none"

ActiveSettings ={}
ActiveProjectName = ""

DEFAULT_SETTINGS = {
    "Speed":      "Safe",
    "Mode":       "Debug",
    "Clone Type": CLONE_TYPE.SSH.value,
    "Log Level":  "Error",
    "Threading":  "Multi"
}

LOG_LEVEL_OPTIONS = ["Error", "Warning", "Notice", "Info"]

def ToggleSpeed():
    current_type = Settings["active"]["Speed"]
    if Settings["active"]["Speed"] == "Fast":
        Settings["active"]["Speed"] = "Safe"
    else:
        Settings["active"]["Speed"] = "Fast"

    if current_type != Settings["active"]["Speed"]:
        Settings.save_persisted_settings()

def SetBranch(branch):
    Settings["active"]["Branch"] = branch
    Settings.save_persisted_settings()

def GetBranch():
    if "Branch" in Settings["active"].keys() and Settings["active"]["Branch"] is not None:
        return Settings["active"]["Branch"]
    # No project-wide branch configured
    return None

def ToggleMode():
    current_type = Settings["active"]["Mode"]
    if Settings["active"]["Mode"] == "Release":
        Settings["active"]["Mode"] = "Debug"
    else:
        Settings["active"]["Mode"] = "Release"

    if current_type != Settings["active"]["Mode"]:
        Settings.save_persisted_settings()

def GetLogLevel():
    return Settings["active"].get("Log Level", "Error")

def CycleLogLevel():
    current = GetLogLevel()
    try:
        idx = LOG_LEVEL_OPTIONS.index(current)
    except ValueError:
        idx = 0
    next_level = LOG_LEVEL_OPTIONS[(idx + 1) % len(LOG_LEVEL_OPTIONS)]
    Settings["active"]["Log Level"] = next_level
    Settings.save_persisted_settings()
    return next_level

def ToggleThreading():
    current = Settings["active"]["Threading"]
    if current == "Multi":
        Settings["active"]["Threading"] = "Single"
    else:
        Settings["active"]["Threading"] = "Multi"

    if current != Settings["active"]["Threading"]:
        Settings["single thread"] = (Settings["active"]["Threading"] == "Single")
        Settings.save_persisted_settings()

"""
Return True if the clone type changed
"""
def ToggleCloneType():
    current_type = Settings["active"]["Clone Type"]
    if current_type == CLONE_TYPE.HTTPS.value:
        Settings["active"]["Clone Type"] = CLONE_TYPE.SSH.value
    else:
        Settings["active"]["Clone Type"] = CLONE_TYPE.HTTPS.value

    if current_type != Settings["active"]["Clone Type"]:
        Settings.save_persisted_settings()
        # Change existing repositories' URL
        return True
    return False

class SETTINGS(dict):
    def init(self):
        # Initialize parser
        self.parse_arguments()
        self.return_code = 0
        self.ci_was_runned_and_passed = False
        self.ci_was_runned = False

    def start(self):
        # Commit or branch
        if self["commit"] is not None and self["branch"] is not None:
            Abort("Please use either commit or branch, not both")

        if self["url"] is None and (self["commit"] is not None or self["branch"] is not None):
            Abort("If you provide a commit/branch, you also need to provide a URL")

        # Set base project settings
        self["name"] = GetRepoNameFromURL(self["url"])

    def parse_arguments(self):
        parser = argparse.ArgumentParser()
        parser.description = "Extra command line arguments are treated as commands for ProjectBase"

        # Adding optional argument
        parser.add_argument("-u", "--url", help = "Root repository's URL", default=None, required=False)
        parser.add_argument("-o", "--out_file", help = "Output to file", default="", required=False)
        parser.add_argument("-l", "--log_file", help = "Pipe internal logs to file", default="/tmp/project_base/run.log", required=False)

        parser.add_argument("-c", "--commit",
                            help = "Root repository's commit",
                            default=None, required=False, nargs=1)

        parser.add_argument("-b", "--branch",
                            help = "Root repository's branch",
                            default=None, required=False, type=str)

        parser.add_argument("-s", "--single_thread",
                            help = "Do not run PB in multiple threads",
                            default=False, required=False, action=argparse.BooleanOptionalAction)

        parser.add_argument("--self", action='store_true', dest='use_self', help="Use the current working directory as the project URL (shorthand for --url=<cwd>)", default=False, required=False)

        parser.add_argument("--selftest", action='store_true', help="Run a full self-test: setup, build, and run all tests using cwd as the project URL, then exit with an appropriate error code", default=False, required=False)

        parser.add_argument("-e", "--exit", action='store_true', help = "Exit after running command line arguments. Performs early exit in case one of the operations ends in error", default=False, required=False)

        parser.add_argument("-d", "--debug", action='store_true', help = "Increase log verbosity to debug ProjectBase", default=False, required=False)

        parser.add_argument("-f", "--fast", action='store_true', help = "Cache Repositories in pickle and do not consider config changes, deactivate to consider if needed", default=False, required=False)

        parser.add_argument("--force-menus", action='store_true', dest='force_menus', help = "Always display full menus, even during automated runs", default=False, required=False)

        # Configurations for CI infrastructure
        parser.add_argument("-ci", "--commitJsonPath", help = "JSON Information with all the repos that have commit changes, that have to be commit copied instead of usual by remote copy", default=None, required=False)

        # --exec="...." is accepted for launching executables, but it is not handled here

        project_args, action_args = parser.parse_known_args()

        self["log_file"]      = project_args.log_file
        self["out_file"]      = project_args.out_file

        if project_args.selftest:
            # Full self-test: setup, build, run all tests, then exit.
            # Clean any cached project state so we always test from scratch
            # with the latest committed code.
            import shutil
            from data.git import GetRepoNameFromURL, GetRepoBareTreePath
            from data.paths import GetBasePaths
            url = os.getcwd()
            project_name = GetRepoNameFromURL(url)
            base_paths = GetBasePaths()
            project_dir = f"{base_paths['project base']}/projects/{project_name}.ProjectBase"
            cache_dir = f"{base_paths['caches']}/{project_name}"
            bare_git_dir = GetRepoBareTreePath(base_paths["bare gits"], url)
            for path in [project_dir, bare_git_dir]:
                if os.path.isdir(path):
                    shutil.rmtree(path)
            if os.path.exists(cache_dir):
                os.remove(cache_dir)

            self["url"]           = url
            self["commit"]        = None
            self["branch"]        = None
            self["exit"]          = True
            self["single thread"] = False
            self["debug"]         = False
            self["fast"]          = False
            self["force menus"]   = True
            self["action"]        = ["1", "2", "3", "4"]
        else:
            if project_args.use_self:
                self["url"]       = os.getcwd()
            else:
                self["url"]       = project_args.url
            self["commit"]        = project_args.commit
            self["branch"]        = project_args.branch
            self["exit"]          = project_args.exit
            self["single thread"] = project_args.single_thread
            self["debug"]         = project_args.debug
            self["fast"]          = project_args.fast
            self["force menus"]   = project_args.force_menus
            # Trailing unknown arguments
            self["action"]        = action_args

        # CI Build options (they will mimick original options with extra commit Json option)
        self["commitJsonPath"] = project_args.commitJsonPath
        self["isCI"] = False
        if self["commitJsonPath"]:
            self["isCI"] = True
            with open(self["commitJsonPath"], "r") as f:
               self["commitJson"] = json.load(f)

            if self["url"] is None:
                raise ValueError("In CI Build, url should always be provided")

    def save_persisted_settings(self):
        dump_json_file(self["persisted"], self["paths"]["configs"] + "/project_cache/settings")

    def reset_settings(self):
        self["active"] = DEFAULT_SETTINGS

    def load_persistent_settings(self):
        global ActiveSettings

        project_name = self["ProjectName"]

        default_project_settings = {
            project_name: DEFAULT_SETTINGS
        }

        # Get persisted project settings
        persisted_settings = load_json_file(self["paths"]["configs"]+"/project_cache/settings", default_project_settings)

        if project_name not in persisted_settings.keys():
            persisted_settings[project_name] = DEFAULT_SETTINGS

        self["persisted"] = persisted_settings
        self["active"]    = persisted_settings[project_name]
        # self["active"]    = GetValueOrDefault(persisted_settings[ProjectName][""])

        # Ensure the Threading key exists for older persisted settings
        if "Threading" not in self["active"]:
            self["active"]["Threading"] = DEFAULT_SETTINGS["Threading"]

        # CLI --single_thread overrides persisted setting;
        # otherwise, sync from the persisted Threading value.
        if not self["single thread"]:
            self["single thread"] = (self["active"]["Threading"] == "Single")

Settings = SETTINGS()

def ErrorCheckLogs(exception):
    print(f"ERROR: Check logs at {Settings["log_file"]} for more information")
    logging.error(f"Exception: {type(exception)} {exception}")
    logging.error(get_full_traceback(exception))

"""
Prompt the user with a yes/no question and return True only if they answer y/Y.
Default is No (returns False) unless answered affirmatively.
Respects the automated-input queue (Settings["action"]) so that integration
tests and command-line automation can supply the answer.
"""
def UserPromptConfirm(message, default_no = False):

    prompt = ColorFormat(Colors.Yellow, f"{message} {YES_NO_PROMPT}: ")

    # Check automated-input queue first
    if len(Settings.get("action", [])) > 0:
        answer = Settings["action"][0]
        del Settings["action"][0]
        print(f"[< Auto confirm <] {{{answer}}}")
    elif Settings.get("exit", False):
        # Running in non-interactive exit mode with no queued answer (safe default)
        print(f"[< Auto confirm (exit mode) <] {{n}}")
        answer = "n"
    else:
        try:
            answer = input(prompt).strip()
        except EOFError:
            return False

    return UserYesNoChoice(answer, default_no)

