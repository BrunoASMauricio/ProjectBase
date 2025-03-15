import os
from data.settings import Settings
from data.common import StringIsNumber
from data.colors import *
from processes.process import RunExecutable, PrepareExecEnvironment
from processes.process import LaunchSilentProcess, ProcessError, RunInThreadsWithProgress
from menus.menu import GetNextOption, MenuExit

"""
scan path_to_scan for appropriate executables
Return a list with the executables
"""
def __GetAvailableExecutables(path_to_scan):
    executables_available = []
    os.chdir(Settings["paths"]["project main"])

    for entry in os.scandir(path_to_scan):
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
def __ParseInput(og_user_input):
    prefix = ""
    user_prefix = og_user_input[0:2]
    prefixes = {
        "!G": "gdb --args ",
        "!S": "gdbserver 127.0.0.1:6175 ",
        "!V": "valgrind --fair-sched=yes -s --leak-check=full --show-leak-kinds=all --track-origins=yes",
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
def __LocateExecutable(user_input, executables_available, path_to_scan):
    input_list = user_input.split(' ')
    executable = input_list[0]
    if StringIsNumber(executable):
        exec_ind = int(executable)
        if exec_ind > len(executables_available):
            print("Out of bounds index: " + user_input)
            return None, None
        path_to_exec = path_to_scan + "/" + executables_available[exec_ind]
    else:
        # By name
        if os.path.isfile(path_to_scan + "/" + executable):
            path_to_exec = path_to_scan + "/" + executable
        # By absolute path
        elif os.path.isfile(executable):
            path_to_exec = executable
        else:
            print("Unknown executable: " + executable)
            return None, None
    return path_to_exec, input_list

def ExecuteMenu(path_to_scan):
    # Allow python scripts to use ProjectBase scripts
    PrepareExecEnvironment()

    while True:
        executables_available = __GetAvailableExecutables(path_to_scan)
        if len(executables_available) == 0:
            print("No executables found")
            return

        print("Executables available in "+path_to_scan+":")
        executables_available.sort()
        previous_repo_name = ""
        for index in range(len(executables_available)):
            exploded = executables_available[index].split("_")
            repo = exploded[0]
            name = '_'.join(exploded[1:])
            if previous_repo_name != repo:
                print(ColorFormat(Colors.Yellow, "\t<" + repo + ">"))
                previous_repo_name = repo
            print("["+str(index)+"]" +ColorFormat(Colors.Blue, name))
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
            prefix, user_input = __ParseInput(og_user_input)

            # Locate executable
            path_to_exec, input_list = __LocateExecutable(user_input, executables_available, path_to_scan)
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
                result = RunExecutable(full_command)
                if result.returncode != 0:
                    print(ColorFormat(Colors.Red, '"' + full_command + '" returned code = '+str(result.returncode)))
                else:
                    print(ColorFormat(Colors.Green, '"' + full_command + '" returned code = '+str(result.returncode)))
                return
            except KeyboardInterrupt:
                print("Keyboard Interrupt")

        except KeyboardInterrupt:
            print("\nCtrl+C interrupts running operations and enter goes to the previous menu. Press Ctrl+D to back out of ProjectBase")
            continue
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
    PrepareExecEnvironment()

    def Run(TestPath, TestName):
        Command = Prefix + " " + TestPath + "/" + TestName
        try:
            Result = LaunchSilentProcess(Command)
        except ProcessError as ex:
            Result = ex.returned
        Result["test name"] = TestName
        all_outputs.append(Result)

    tests_args = []
    for test_index in range(len(tests)):
        test_name = tests[test_index]
        tests_args.append((Settings["paths"]["tests"] + "/", test_name, ))

    RunInThreadsWithProgress(Run, tests_args, 20)
    print("\n")

    return all_outputs

def RunAllTests():
    errors = 0
    all_outputs = _RunAllTests()
    for output in all_outputs:
        if output["code"] != 0:
            errors += 1
            print(ColorFormat(Colors.Red, output["test name"] + " ( " + str(output["code"]) + " )"))
            if len(output["stdout"]) != 0:
                print(ColorFormat(Colors.Blue, "\t\tSTDOUT\n") + output["stdout"])
            if len(output["stderr"]) != 0:
                print(ColorFormat(Colors.Yellow, "\t\tSTDERR\n") + output["stderr"])
        else:
            print(ColorFormat(Colors.Green, '"' + output["test name"] + '" returned code = '+str(output["code"])))

    if errors == 0:
        print(ColorFormat(Colors.Green, "All "+str(len(all_outputs))+" tests successful!"))
        return

    print(ColorFormat(Colors.Red, ("="*40)+"\n          " + str(errors) + " Errors reported\n"+("="*40)))
    print(ColorFormat(Colors.Green, "Successes: ["+str(len(all_outputs) - errors)+"]"))

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
