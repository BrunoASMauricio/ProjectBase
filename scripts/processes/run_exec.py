import sys
import os
import sys
from data.settings import Settings
from data.common import StringIsNumber
from data.colors import *
from data.print import *
from processes.process import _LaunchCommand, SetupLocalEnvVars
from processes.process import LaunchSilentProcess, ProcessError, RunInThreadsWithProgress
from menus.menu import GetNextInput, MenuExit, PeekNextInput, PopNextInput
from data.paths import JoinPaths
from processes.flamegraph import *

exec_menu_mesg = ""

def SetExecMenuMessage(msg):
    global exec_menu_mesg
    exec_menu_mesg = msg

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

def __SetupPrefix(name, cmd, desc):
    return {
        "name": name,
        "cmd": cmd,
        "desc": desc
    }

exec_prefix = "!"
"""
The modifiers below describe which programs exist that can be used to modify execution.
The key is the value used to identify a modifier
The second argument is the actual command, and can be a string, which will have the
 $EXEC and $ARGS replaced with the appropriate executable and arguments, OR a function
 that receives the executable and arguments and returns the command to execute
"""
modifiers = {
    "g": __SetupPrefix("GDB",
                       "gdb $EXEC $ARGS",
                       "Base debugger"
    ),
    "G": __SetupPrefix("GDB",
                       "gdb $EXEC --args $ARGS",
                       "Debugger with arguments from command line"
    ),
    "v": __SetupPrefix("Valgrind",
                       "valgrind $EXEC $ARGS",
                       "Run valgrind to check for memory errors and leaks"
    ),
    "V": __SetupPrefix("Valgrind",
                       "valgrind --fair-sched=yes -s --leak-check=full --show-leak-kinds=all --track-origins=yes $EXEC $ARGS",
                       "Run valgrind to check for memory errors and leaks, with deep analytics options"
    ),
    "c": __SetupPrefix("Callgrind",
                       "valgrind --tool=callgrind $EXEC $ARGS",
                       "Valgrinds' callgrind tool for recording function calls"
    ),
    "C": __SetupPrefix("Callgrind",
                       "valgrind --tool=callgrind  --inclusive=yes --tree=both --cache-sim=yes --branch-sim=yes --dump-instr=yes --collect-jumps=yes $EXEC $ARGS",
                       "Valgrinds' callgrind tool for recording function calls, with deep analytics options"
    ),
    "F": __SetupPrefix("Flamegraph",
                       RunFlamegraph,
                       "Run the program, and generate a graph of the time spent on each function call"
    )
}

"""
Check for modifier
If it exsists, return it alongside truncated input list
"""
def __GetModifier(input_list):
    modifier_id = input_list[0]
    modifier = None
    if len(modifier_id) == 2 and modifier_id[0] == exec_prefix:
        if modifier_id[1] not in modifiers.keys():
            PrintError(f"Unknown modifier {modifier_id[1]}")
            return None, None
        modifier = modifiers[modifier_id[1]]
        # Remove modifier from input list
        input_list = input_list[1:]
    return modifier, input_list

"""
Locate the actual executable used and return its' path
"""
def __LocateExecutable(executable, executables_available):
    if StringIsNumber(executable):
        exec_ind = int(executable)
        if exec_ind > len(executables_available):
            PrintWarning(f"Out of bounds index {exec_ind}/{len(executables_available)}")
            return None
        path_to_exec = executables_available[exec_ind]
    else:
        raise Exception("Unimplemented. First implement proper executable presentation per module and alphabetical")

    return path_to_exec

"""
Parse user input and extract prefix and the actual user input
"""
def __ParseInput(og_user_input, executables_available):
    args = None
    input_list = og_user_input.split(" ")

    modifier, input_list = __GetModifier(input_list)
    if input_list == None:
        return None

    # Locate executable. After modifier has been parsed out, the executable is the first element
    executable = __LocateExecutable(input_list[0], executables_available)
    if executable == None:
        PrintError(f"Executable not found for input: {og_user_input}")
        return None

    # Check for Python scripts
    if executable.endswith(".py"):
        # Specify venvs' python executable, to keep the same Venv
        #  across python executables (i.e. pip installations and modules available)
        executable = f"{sys.executable} {executable}"

    # Is there an automated next command? If so check if it is for arguments
    next_inp = PeekNextInput()
    if next_inp != None:
        if next_inp.startswith("--args="):
            PopNextInput()
            args = next_inp.replace("--args=", "").split(" ")

    # Is there an interactive next argument?
    if len(input_list) > 1:
        if args != None:
            raise Exception("Unexpected arguments from both next automated command ({args}) and interactive ({og_user_input})")
        args = [x for x in input_list[1:] if x != ""]

    # Either assemble full command based on modifier, or by itself
    if modifier != None:
        if type(modifier["cmd"]) == type(__ParseInput):
            full_command, msg = modifier["cmd"](executable, args)
            if msg != None:
                SetExecMenuMessage(msg)
        else:
            # Text based modifier, just append
            if args != None:
                args = ' '.join(args)
            else:
                args = ' '

            full_command = modifier["cmd"].replace("$EXEC", executable).replace("$ARGS", args)
    else:
        full_command = f"{executable} {args}"

    return full_command

def SetupExecHelp():
    msg = """=== Exec help menu ===
To run an executable, input its' index from the displayed list.
There are some "modifiers" to the execution environment that can be used.
To use a modifier, start the command with '!' followed by the modifier identifier.
The available modifiers are:
"""
    for modifier_id in modifiers:
        modifier = modifiers[modifier_id]
        msg += f"=== {modifier["name"]} (id: {modifier_id}) ===\n"
        msg += f"\tdescription: {modifier["desc"]}\n"
        if type(modifier["cmd"]) == type(SetupExecHelp):
            msg += f"\tcommand executed: defined by function {modifier["cmd"]}\n"
        else:
            msg += f"\tcommand executed: {modifier["cmd"]}\n"
    msg += "Example invocation: '!g binary_to_test arg0 arg1 arg2'"
    msg += "When inputs are received via command line, to pass arguments use `--args`` like --args='\"arg number 0\" arg1 arg2'"

    SetExecMenuMessage(msg)

def ParseInput(og_user_input, executables_available):
    # No input (Enter pressed) or Exit this menu
    if len(og_user_input) == 0 or MenuExit(og_user_input):
        return None

    # Help menu?
    if og_user_input in ["help", "?"]:
        SetupExecHelp()
        return None

    # Check extra program prefix
    return __ParseInput(og_user_input, executables_available)

def ExecuteMenu(PathToScan):
    global exec_menu_mesg
    while True:
        executables_available = __GetAvailableExecutables(PathToScan)
        if len(executables_available) == 0:
            PrintWarning("No executables found")
            return

        PrintInfo("Executables available in "+PathToScan+":")
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
                    PrintInfo(ColorFormat(Colors.Yellow, "\t<" + repo + ">"))
                    previous_repo_name = repo
                print("["+str(index)+"]" +ColorFormat(Colors.Blue, name))
            else:
                print("["+str(index)+"] "+ColorFormat(Colors.Yellow, "<" + repo + ">"))

        if exec_menu_mesg != "":
            print(exec_menu_mesg)
            exec_menu_mesg = ""
        print()

        print("Input 'help' or '?' for exec launch information")
        print("exit or Ctr+D to exit")
        try:
            # Properly parse input
            full_command = ParseInput(GetNextInput(single_string=True), executables_available)
            if full_command == None:
                continue

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
