import sys
import os
import sys
from data.settings import Settings
from data.common import StringIsNumber
from data.colors import *
from processes.process import _LaunchCommand, SetupLocalEnvVars
from processes.process import LaunchSilentProcess, ProcessError, RunInThreadsWithProgress
from menus.menu import GetNextInput, MenuExit, PeekNextInput, PopNextInput
from data.paths import JoinPaths

"""
scan PathToScan for appropriate executables
Return a list with the executables
"""
def __GetAvailableExecutables(PathToScan, CurrentAvailables=[]):
    executables_available = []
    os.chdir(Settings["paths"]["project main"])

    for entry in os.scandir(PathToScan):
        ExecPath = JoinPaths(PathToScan, entry.name)
        # Must be fully executable
        if entry.stat().st_mode & 0o111 != 0o111:
            continue
        # Do not follow symbolic links to avoid infinite loops
        if os.path.islink(ExecPath):
            continue
        # Must be a file
        if not entry.is_file():
            executables_available = executables_available + __GetAvailableExecutables(ExecPath, CurrentAvailables)
            continue

        executables_available.append(ExecPath)
    return executables_available

"""
Parse user input and extract prefix and the actual user input
"""
def __ParseInput(og_user_input):
    prefix = ""
    user_prefix = og_user_input[0:2]
    prefixes = {
        "!G": "gdb --args ",
        "!S": "gdbserver 127.0.0.1:6175 ",
        "!V": "valgrind --fair-sched=yes -s --leak-check=full --show-leak-kinds=all --track-origins=yes",
        "!C": "valgrind --tool=callgrind",
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
def __LocateExecutable(user_input, executables_available):
    input_list = user_input.split(' ')
    executable = input_list[0]
    if StringIsNumber(executable):
        exec_ind = int(executable)
        if exec_ind > len(executables_available):
            print("Out of bounds index: " + user_input)
            return None, None
        path_to_exec = executables_available[exec_ind]
    else:
        raise Exception("Unimplemented. First implement proper executable presentation per module and alphabetical")
    return path_to_exec, input_list

def ExecuteMenu(PathToScan):
    while True:
        executables_available = __GetAvailableExecutables(PathToScan)
        if len(executables_available) == 0:
            print("No executables found")
            return

        print("Executables available in "+PathToScan+":")
        executables_available.sort()
        previous_repo_name = ""
        for index in range(len(executables_available)):
            exploded = executables_available[index].split("_")
            repo = exploded[0]
            name = '_'.join(exploded[1:])
            # Parse out path
            exploded = repo.split("/")
            repo = exploded[-1]

            if len(name) != 0:
                if previous_repo_name != repo:
                    print(ColorFormat(Colors.Yellow, "\t<" + repo + ">"))
                    previous_repo_name = repo
                print("["+str(index)+"]" +ColorFormat(Colors.Blue, name))
            else:
                print("["+str(index)+"] "+ColorFormat(Colors.Yellow, "<" + repo + ">"))

        print()

        
        print("!V for valgrind. !G for GDB. !S for GDB server @ 127.0.0.1:6175")
        print("Upper case (V,G,S) uses default parameters, lower case doesn't.")
        print("[![G|V|S]]<INDEX [0-9]+> [Space separated argument list]")
        print("exit or Ctr+D to exit")
        try:
            og_user_input = GetNextInput(single_string=True)
            # No input (Enter pressed)
            if len(og_user_input) == 0:
                print("No input")
                continue

            if MenuExit(og_user_input):
                return
            # Check extra program prefix
            prefix, user_input = __ParseInput(og_user_input)

            # Locate executable
            path_to_exec, input_list = __LocateExecutable(user_input, executables_available)
            if path_to_exec == None:
                print("Executable not found")
                continue

            # Assemble command and run
            arguments = ' '.join([x for x in input_list[1:] if x != ""])
            full_command = path_to_exec + " " + arguments
            if prefix != "":
                full_command = prefix + " " + full_command

            if path_to_exec.endswith(".py"):
                # Specify venvs' python executable, to keep the same Venv
                #  across python executables (i.e. pip installations and modules available)
                full_command = f"{sys.executable} {full_command}"

            next_inp = PeekNextInput()
            if next_inp != None:
                # There is an automated next command
                arg_name = "--args="
                if next_inp.startswith(arg_name):
                    PopNextInput()
                    args = next_inp.replace(arg_name, "")
                    full_command = f"{full_command} {args}"

            print("Running: \"" + full_command + "\"")

            try:
                # Allow python scripts to use ProjectBase scripts
                SetupLocalEnvVars()
                result = _LaunchCommand(full_command, path=None, interactive=True)
                print(result["stdout"])
                if len(result["stderr"]) > 0:
                    print(result["stderr"])

                if result["code"] != 0:
                    print(ColorFormat(Colors.Red, '"' + full_command + '" returned code = '+str(result["code"])))
                else:
                    print(ColorFormat(Colors.Green, '"' + full_command + '" returned code = '+str(result["code"])))
                return
            except KeyboardInterrupt:
                print("Keyboard Interrupt")
                break

        except KeyboardInterrupt:
            print("\nCtrl+C interrupts running operations and enter goes to the previous menu. Press Ctrl+D to back out of ProjectBase")
            break
        except EOFError:
            break

def RunSingleTest():
    ExecuteMenu(Settings["paths"]["tests"])

def RunSingleExecutable():
    ExecuteMenu(Settings["paths"]["executables"])

def _RunAllTests(Prefix=""):
    all_outputs = []
    tests = __GetAvailableExecutables(Settings["paths"]["tests"])

    print("Running " + str(len(tests)) + " tests in " + Settings["paths"]["tests"].replace(Settings["paths"]["project base"], ""))
    # Allow python scripts to use ProjectBase scripts
    SetupLocalEnvVars()

    def Run(TestPath):
        Command = Prefix + " " + TestPath
        if TestPath.endswith(".py"):
            # Specify venvs' python executable, to keep the same Venv
            #  across python executables (i.e. pip installations and modules available)
            Command = f"{sys.executable} {Command}"

        try:
            Result = LaunchSilentProcess(Command)
        except ProcessError as ex:
            Result = ex.returned
        Result["test name"] = TestPath.split(" ")[-1]
        all_outputs.append(Result)

    tests_args = []
    for test_index in range(len(tests)):
        test_name = tests[test_index]
        tests_args.append((test_name, ))

    RunInThreadsWithProgress(Run, tests_args, None)
    print("\n")

    return all_outputs

def RunAllTests():
    errors = []
    all_outputs = _RunAllTests()
    for output in all_outputs:
        if output["code"] != 0:
            header_msg = ColorFormat(Colors.Red, output["test name"] + " ( " + str(output["code"]) + " )")
            errors.append(header_msg)
            print(header_msg)
            if len(output["stdout"]) != 0:
                print(ColorFormat(Colors.Blue, "\t\tSTDOUT\n") + output["stdout"])
            if len(output["stderr"]) != 0:
                print(ColorFormat(Colors.Yellow, "\t\tSTDERR\n") + output["stderr"])
        else:
            print(ColorFormat(Colors.Green, '"' + output["test name"] + '" returned code = '+str(output["code"])))

    if len(errors) == 0:
        print(ColorFormat(Colors.Green, "All "+str(len(all_outputs))+" tests successful!"))
        return

    if(len(errors) > 0):
        Settings.return_code = len(errors)

    print(ColorFormat(Colors.Red, f"\nErrors reported {len(errors)}\n" + ("="*40)+"\n" + '\n'.join(errors) + "\n" + ("="*40)))
    print(ColorFormat(Colors.Green, "Successes: ["+str(len(all_outputs) - len(errors))+"]"))

def RunAllTestsWithValgrind():
    errors = 0
    all_outputs = _RunAllTests("valgrind --fair-sched=yes -s --leak-check=full --track-origins=yes")
    summary_leaks = ""
    summary_no_leaks = ""
    for output in all_outputs:
        if "ERROR SUMMARY: 0 errors from 0 contexts" not in output["stderr"]:
            print(ColorFormat(Colors.Red, f"\t{output["test name"]} ({str(output["code"])})"))
            if len(output["stderr"]) != 0:
                print(ColorFormat(Colors.Yellow, "\t\tSTDERR"))
                print(output["stderr"])

            if len(output["stdout"]) != 0:
                print(ColorFormat(Colors.Blue, "\t\tSTDOUT"))
                print(output["stdout"])
            errors = errors+ 1
            summary_leaks += ColorFormat(Colors.Red, f"  {output["test name"]} is leaking\n")
        else:
            summary_no_leaks += ColorFormat(Colors.Green, f"  {output["test name"]} is not leaking\n")

    if errors == 0:
        print(ColorFormat(Colors.Green, "No leaks found in "+str(len(all_outputs))+" tests!"))
    else:
        # ErrorSentence = "Leaks found in " + str(errors) + " tests"
        # print(ColorFormat(Colors.Red, ("="*40)+"\n          " + ErrorSentence + "\n"+("="*40)))
        print(ColorFormat(Colors.Green, "Clean:\t["+str(len(all_outputs) - errors)+"]"))
        print(ColorFormat(Colors.Red, "Leaks:\t["+str(errors)+"]\n"))
        print(summary_no_leaks)
        print(summary_leaks)
