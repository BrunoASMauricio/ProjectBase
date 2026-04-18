import sys
import os
import sys
from data.settings import Settings
from data.common import StringIsNumber
from data.colors import *
from data.print import *
from processes.process import _LaunchCommand, SetupLocalEnvVars
from processes.process import LaunchSilentProcess, ProcessError, RunInThreadsWithProgress
from menus.menu import GetNextInput, MenuExit
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

    if modifier_id[0] == exec_prefix and len(modifier_id) >= 2:
        # Acceptable options: '!g<ID>' or '!g <ID'>
        expected_modifier = modifier_id[1]
        input_list = input_list[1:]

        if len(modifier_id) != 2:
            input_list.insert(0, modifier_id[2:].strip())
    else:
        return None, input_list

    if expected_modifier not in modifiers.keys():
        PrintError(f"Unknown modifier {expected_modifier}")
        return None, None

    modifier = modifiers[expected_modifier]
    # Remove modifier from input list
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
        # Name-based lookup: match against the exec name (part after the repo prefix)
        matches = []
        for idx, path in enumerate(executables_available):
            basename = os.path.basename(path)
            # Try exact basename match first
            if basename == executable:
                matches.append(idx)
                continue
            # Try matching just the name part (after first underscore = repo prefix)
            parts = basename.split("_", 1)
            exec_name = parts[1] if len(parts) > 1 else parts[0]
            if exec_name == executable:
                matches.append(idx)

        if len(matches) == 1:
            path_to_exec = executables_available[matches[0]]
        elif len(matches) > 1:
            PrintWarning(
                f"Ambiguous name '{executable}': matches {[os.path.basename(executables_available[i]) for i in matches]}"
            )
            return None
        else:
            PrintWarning(f"No executable found matching '{executable}'")
            return None
    return path_to_exec

"""
Parse user input and extract prefix and the actual user input
"""
def __ParseInput(og_user_input, executables_available):
    args = ""

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

    # Is there an interactive next argument?
    if len(input_list) > 1:
        if len(args) != 0:
            raise Exception("Unexpected arguments from both next automated command ({args}) and interactive ({og_user_input})")
        args = ' '.join([x for x in input_list[1:] if x != ""])

    # Either assemble full command based on modifier, or by itself
    if modifier != None:
        if type(modifier["cmd"]) == type(__ParseInput):
            full_command, msg = modifier["cmd"](executable, args)
            if msg != None:
                SetExecMenuMessage(msg)
        else:
            # Text based modifier, just append
            if len(args) != 0:
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
    msg += "When inputs are received via command line, to pass arguments use `'` like '\"arg number 0\" arg1 arg2'"

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

        # Pad index prefix to a fixed width so names align across rows
        idx_width = len(str(len(executables_available) - 1))

        # Group executables by repo for columnar display
        grouped = {}
        ungrouped = []
        for index in range(len(executables_available)):
            exploded = executables_available[index].split("_")
            repo = exploded[0]
            name = '_'.join(exploded[1:])
            repo = repo.split("/")[-1]

            prefix = f"[{index:>{idx_width}}] "
            if len(name) != 0:
                if repo not in grouped:
                    grouped[repo] = []
                grouped[repo].append(prefix + ColorFormat(Colors.Blue, name))
            else:
                ungrouped.append(prefix + ColorFormat(Colors.Yellow, "<" + repo + ">"))

        # Assemble all groups for a single aligned render
        layout_input = []
        if ungrouped:
            layout_input.append((None, ungrouped))
        for repo, items in grouped.items():
            layout_input.append((ColorFormat(Colors.Yellow, "\t<" + repo + ">"), items))
        if layout_input:
            PrintInColumns(layout_input, header_fn=PrintInfo)

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

def _RunAllTests(Prefix="", module_filter=None):
    all_outputs = []
    tests = __GetAvailableExecutables(Settings["paths"]["tests"])

    # Apply module filter when requested
    if module_filter is not None:
        tests = [t for t in tests if _GetTestModule(t) == module_filter]
        if not tests:
            print(ColorFormat(Colors.Yellow,
                  f"No tests found in module '{module_filter}'."))
            return []

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

def RunAllTests(module_filter=None):
    errors = []
    all_outputs = _RunAllTests(module_filter=module_filter)
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

def _GetTestModule(test_name):
    """Extract module/repo name from a test path like /path/to/RepoName_TestName."""
    basename = os.path.basename(test_name)
    parts = basename.split("_", 1)
    return parts[0]

def RunModuleTests():
    """Show all installed modules with test counts, let user select one, then run its tests."""
    tests = __GetAvailableExecutables(Settings["paths"]["tests"])
    if not tests:
        print(ColorFormat(Colors.Yellow, "No tests found."))
        return

    # Group tests by module (the repo prefix of each test binary)
    module_tests = {}
    for test in sorted(tests):
        module = _GetTestModule(test)
        if module not in module_tests:
            module_tests[module] = []
        module_tests[module].append(test)

    modules = sorted(module_tests.keys())
    print("Available modules:")
    items = []
    for idx, module in enumerate(modules):
        count = len(module_tests[module])
        test_word = "test" if count == 1 else "tests"
        items.append(f"  [{idx}] {ColorFormat(Colors.Yellow, module)} - {count} {test_word}")
    PrintInColumns(items)

    print("\nSelect a module by index or name (exit/Ctrl+D to cancel):")
    try:
        raw = GetNextInput(single_string=True)
    except EOFError:
        return

    if MenuExit(raw) or not raw.strip():
        return

    if StringIsNumber(raw.strip()):
        idx = int(raw.strip())
        if idx < 0 or idx >= len(modules):
            PrintError(f"Index {idx} out of range")
            return
        selected_module = modules[idx]
    else:
        selected_module = raw.strip()
        if selected_module not in module_tests:
            PrintError(f"Module '{selected_module}' not found")
            return

    RunAllTests(module_filter=selected_module)

import re as _re
def _ParseValgrindStats(stderr):
    """Parse valgrind stderr output and return dict with errors and bytes_lost counts."""
    errors = 0
    bytes_lost = 0

    error_match = _re.search(r"ERROR SUMMARY:\s*(\d+)\s+errors", stderr)
    if error_match:
        errors = int(error_match.group(1))

    def_lost_match = _re.search(r"definitely lost:\s*([\d,]+)\s+bytes", stderr)
    if def_lost_match:
        bytes_lost += int(def_lost_match.group(1).replace(",", ""))

    ind_lost_match = _re.search(r"indirectly lost:\s*([\d,]+)\s+bytes", stderr)
    if ind_lost_match:
        bytes_lost += int(ind_lost_match.group(1).replace(",", ""))

    return {"errors": errors, "bytes_lost": bytes_lost}

def RunAllTestsWithValgrind():
    errors = 0
    all_outputs = _RunAllTests("valgrind --fair-sched=yes -s --leak-check=full --track-origins=yes")
    summary_leaks = ""
    summary_no_leaks = ""
    # Group by module
    modules = {}
    for output in all_outputs:
        module = _GetTestModule(output["test name"])
        if module not in modules:
            modules[module] = []
        stats = _ParseValgrindStats(output.get("stderr", ""))
        output["_valgrind_errors"] = stats["errors"]
        output["_valgrind_bytes_lost"] = stats["bytes_lost"]
        modules[module].append(output)

    for module, tests in modules.items():
        print(ColorFormat(Colors.Yellow, f"=== Module: {module} ==="))
        for output in tests:
            if "ERROR SUMMARY: 0 errors from 0 contexts" not in output["stderr"]:
                print(ColorFormat(Colors.Red, f"\t{output["test name"]} ({str(output["code"])})"))
                if len(output["stderr"]) != 0:
                    print(ColorFormat(Colors.Yellow, "\t\tSTDERR"))
                    print(output["stderr"])

                if len(output["stdout"]) != 0:
                    print(ColorFormat(Colors.Blue, "\t\tSTDOUT"))
                    print(output["stdout"])
                errors = errors + 1
                summary_leaks += ColorFormat(Colors.Red, f"  {output["test name"]} is leaking\n")
            else:
                summary_no_leaks += ColorFormat(Colors.Green, f"  {output["test name"]} is not leaking\n")

    if errors == 0:
        print(ColorFormat(Colors.Green, "No leaks found in "+str(len(all_outputs))+" tests!"))
    else:
        print(ColorFormat(Colors.Green, "Clean:\t["+str(len(all_outputs) - errors)+"]"))
        print(ColorFormat(Colors.Red, "Leaks:\t["+str(errors)+"]\n"))
        print(summary_no_leaks)
        print(summary_leaks)

    # Print valgrind stats table
    if all_outputs:
        print(ColorFormat(Colors.Yellow, "\n=== Valgrind Stats Summary ==="))
        header = f"{'TestName':<50} {'Errors':>8} {'BytesLost':>12}"
        print(header)
        print("-" * len(header))
        for output in all_outputs:
            name = os.path.basename(output["test name"])
            err_count = output.get("_valgrind_errors", 0)
            bytes_lost = output.get("_valgrind_bytes_lost", 0)
            row = f"{name:<50} {err_count:>8} {bytes_lost:>12}"
            if err_count > 0 or bytes_lost > 0:
                print(ColorFormat(Colors.Red, row))
            else:
                print(ColorFormat(Colors.Green, row))