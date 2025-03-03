import os
from data.settings import Settings
from data.common import StringIsNumber
from data.colors import *
from processes.process import RunExecutable, PrepareExecEnvironment
from processes.process import LaunchSilentProcess, ProcessError, RunInThreadsWithProgress
from menus.menu import GetNextOption, MenuExit
import traceback

"""
scan PathToScan for appropriate executables
Return a list with the executables
"""
def __get_available_executables(PathToScan):
    executables_available = []
    os.chdir(Settings["paths"]["project main"])

    for entry in os.scandir(PathToScan):
        # Must be fully executable
        if entry.stat().st_mode & 0o111 != 0o111:
            continue
        # Must be a file
        if not entry.is_file():
            continue

        executables_available.append(entry.name)
    return executables_available

"""
Parse user input and extract prefix and the actual user input
"""
def __parse_input(og_user_input):
    prefix = ""
    user_prefix = og_user_input[0:2]
    prefixes = {
        "!G": "gdb --args ",
        "!S": "gdbserver 127.0.0.1:6175 ",
        "!V": "valgrind --fair-sched=yes -s --leak-check=full --track-origins=yes",
        "!g": "gdb",
        "!s": "gdbserver",
        "!v": "valgrind"
    }

    if user_prefix in prefixes:
        prefix = prefixes[user_prefix]
        user_input = og_user_input[2:]
    else:
        user_input = og_user_input
    return prefix, user_input

"""
Locate the actual executable used and return its' path
"""
def __locate_executable(user_input, executables_available, PathToScan):
    input_list = user_input.split(' ')
    executable = input_list[0]
    if StringIsNumber(executable):
        exec_ind = int(executable)
        if exec_ind > len(executables_available):
            print("Out of bounds index: " + user_input)
            return None, None
        path_to_exec = PathToScan + "/" + executables_available[exec_ind]
    else:
        # By name
        if os.path.isfile(PathToScan + "/" + executable):
            path_to_exec = PathToScan + "/" + executable
        # By absolute path
        elif os.path.isfile(executable):
            path_to_exec = executable
        else:
            print("Unknown executable: " + executable)
            return None, None
    return path_to_exec, input_list

def execute_menu(PathToScan):
    # Allow python scripts to use ProjectBase scripts
    PrepareExecEnvironment()

    while True:
        executables_available = __get_available_executables(PathToScan)
        if len(executables_available) == 0:
            print("No executables found")
            return

        print("Executables available in "+PathToScan+":")
        executables_available.sort()
        PreviousRepoName = ""
        for Index in range(len(executables_available)):
            Exploded = executables_available[Index].split("_")
            Repo = Exploded[0]
            Name = '_'.join(Exploded[1:])
            if PreviousRepoName != Repo:
                print(ColorFormat(Colors.Yellow, "\t<" + Repo + ">"))
                PreviousRepoName = Repo
            print("["+str(Index)+"]" +ColorFormat(Colors.Blue, Name))
        print()

        
        print("!V for valgrind. !G for GDB. !S for GDB server @ 127.0.0.1:6175")
        print("Upper case (V,G,S) uses default parameters, lower case doesn't.")
        print("[![G|V|S]]<INDEX [0-9]+> [Space separated argument list]")
        print("exit or Ctr+D to exit")
        try:
            og_user_input = GetNextOption()
            # No input (Enter pressed)
            if len(og_user_input) == 0:
                print("No input")
                continue

            if MenuExit(og_user_input):
                return
            # Check extra program prefix
            prefix, user_input = __parse_input(og_user_input)

            # Locate executable
            path_to_exec, input_list = __locate_executable(user_input, executables_available, PathToScan)
            if path_to_exec == None:
                print("Executable not found")
                continue

            # Assemble command and run
            arguments = ' '.join([x for x in input_list[1:] if x != ""])
            full_command = path_to_exec + " " + arguments
            if prefix != "":
                full_command = prefix + " " + full_command
            print("Running: \"" + full_command + "\"")

            try:
                Result = RunExecutable(full_command)
                if Result.returncode != 0:
                    print(ColorFormat(Colors.Red, '"' + full_command + '" returned code = '+str(Result.returncode)))
                else:
                    print(ColorFormat(Colors.Green, '"' + full_command + '" returned code = '+str(Result.returncode)))
                return
            except KeyboardInterrupt:
                print("Keyboard Interrupt")

        except KeyboardInterrupt:
            print("\nCtrl+C interrupts running operations and enter goes to the previous menu. Press Ctrl+D to back out of ProjectBase")
            continue
        except EOFError:
            break

def run_single_test():
    execute_menu(Settings["paths"]["tests"])

def run_single_executable():
    execute_menu(Settings["paths"]["executables"])

def _RunAllTests(Prefix=""):
    AllOutputs = []
    Tests = __get_available_executables(Settings["paths"]["tests"])

    print("Running " + str(len(Tests)) + " tests in " + Settings["paths"]["tests"].replace(Settings["paths"]["project base"], ""))
    # Allow python scripts to use ProjectBase scripts
    PrepareExecEnvironment()

    def Run(TestPath, TestName):
        Command = Prefix + " " + TestPath + "/" + TestName
        try:
            Result = LaunchSilentProcess(Command)
        except ProcessError as ex:
            Result = ex.Returned
        Result["test name"] = TestName
        AllOutputs.append(Result)

    TestsArgs = []
    for TestIndex in range(len(Tests)):
        TestName = Tests[TestIndex]
        TestsArgs.append((Settings["paths"]["tests"] + "/", TestName, ))

    RunInThreadsWithProgress(Run, TestsArgs)
    print("\n")

    return AllOutputs

def run_all_tests():
    Errors = 0
    AllOutputs = _RunAllTests()
    for Output in AllOutputs:
        if Output["code"] != 0:
            Errors += 1
            print(ColorFormat(Colors.Red, Output["test name"] + " ( " + str(Output["code"]) + " )"))
            if len(Output["stdout"]) != 0:
                print(ColorFormat(Colors.Blue, "\t\tSTDOUT\n") + Output["stdout"])
            if len(Output["stderr"]) != 0:
                print(ColorFormat(Colors.Yellow, "\t\tSTDERR\n") + Output["stderr"])
        else:
            print(ColorFormat(Colors.Green, '"' + Output["test name"] + '" returned code = '+str(Output["code"])))

    if Errors == 0:
        print(ColorFormat(Colors.Green, "All "+str(len(AllOutputs))+" tests successful!"))
        return

    print(ColorFormat(Colors.Red, ("="*40)+"\n          " + str(Errors) + " Errors reported\n"+("="*40)))
    print(ColorFormat(Colors.Green, "Successes: ["+str(len(AllOutputs) - Errors)+"]"))

def run_all_tests_on_valgrind():
    Errors = 0
    AllOutputs = _RunAllTests("valgrind --fair-sched=yes -s --leak-check=full --track-origins=yes")
    for Output in AllOutputs:
        # print(Output["stderr"])
        if "ERROR SUMMARY: 0 errors from 0 contexts" not in Output["stderr"]:
            print(ColorFormat(Colors.Red, "\t" + Output["test name"] + " (" + str(Output["code"]) + ")"))
            if len(Output["stderr"]) != 0:
                print(ColorFormat(Colors.Yellow, "\t\tSTDERR"))
                print(Output["stderr"])

            if len(Output["stdout"]) != 0:
                print(ColorFormat(Colors.Blue, "\t\tSTDOUT"))
                print(Output["stdout"])
            Errors = Errors+ 1
        else:
            print(ColorFormat(Colors.Green, "\t" + Output["test name"] + " is clean"))

    if Errors == 0:
        print(ColorFormat(Colors.Green, "No leaks found in "+str(len(AllOutputs))+" tests!"))
    else:
        # ErrorSentence = "Leaks found in " + str(Errors) + " tests"
        # print(ColorFormat(Colors.Red, ("="*40)+"\n          " + ErrorSentence + "\n"+("="*40)))
        print(ColorFormat(Colors.Green, "Clean:\t["+str(len(AllOutputs) - Errors)+"]"))
        print(ColorFormat(Colors.Red, "Leaks:\t["+str(Errors)+"]"))
