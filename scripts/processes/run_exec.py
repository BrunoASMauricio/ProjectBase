import os
from data.settings import Settings
from data.common import StringIsNumber
from data.colors import *
from processes.process import RunExecutable, PrepareExecEnvironment
from processes.git import GetRepositoryName
from menus.menu import GetNextOption
import traceback

"""
scan path_to_scan for appropriate executables
Return a list with the executables
"""
def __get_available_executables(path_to_scan):
    executables_available = []
    os.chdir(Settings["paths"]["project main"])
    print("Executables available in "+path_to_scan+":")

    index = 0
    for entry in os.scandir(path_to_scan):
        # Must be fully executable
        if entry.stat().st_mode & 0o111 != 0o111:
            continue
        # Must be a file
        if not entry.is_file():
            continue

        executables_available.append(entry.name)
        index += 1

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
def __locate_executable(user_input, executables_available, path_to_scan):
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

def execute_menu(path_to_scan):
    # Allow python scripts to use ProjectBase scripts
    PrepareExecEnvironment()

    while True:
        executables_available = __get_available_executables(path_to_scan)
        if len(executables_available) == 0:
            print("No executables found")
            return
        
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

            # Check extra program prefix
            prefix, user_input = __parse_input(og_user_input)
            if "exit" == user_input:
                return

            # Locate executable
            path_to_exec, input_list = __locate_executable(user_input, executables_available, path_to_scan)
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
            print("\nCtrl+C exits running operations. Press Ctrl+D to back out of ProjectBase")
            continue
        except EOFError:
            break

def run_single_test():
    execute_menu(Settings["paths"]["tests"])

def run_single_executable():
    execute_menu(Settings["paths"]["executables"])

def run_all_tests():
    error_names = []
    successes = 0
    tests = __get_available_executables(Settings["paths"]["tests"])

    print("Running " + str(len(tests)) + " tests in " + Settings["paths"]["tests"].replace(Settings["paths"]["project base"], ""))

    # Allow python scripts to use ProjectBase scripts
    PrepareExecEnvironment()

    for test_name in tests:
        try:
            print(ColorFormat(Colors.Blue, "\n\tRUNNING "+test_name))

            try:
                Result = RunExecutable(Settings["paths"]["tests"] + "/" + test_name)
                if Result.returncode != 0:
                    print(ColorFormat(Colors.Red, '"' + test_name + '" returned code = '+str(Result.returncode)))
                else:
                    print(ColorFormat(Colors.Green, '"' + test_name + '" returned code = '+str(Result.returncode)))
            except KeyboardInterrupt:
                print("Keyboard Interrupt")

            # Result = subprocess.run(Project.Paths["tests"]+"/"+test_name, shell=True)

            print(ColorFormat(Colors.Blue, "\t"+test_name+" finished"))

            if Result.returncode != 0:
                print(ColorFormat(Colors.Red, "Return code = "+str(Result.returncode)))
                error_names.append(test_name)
            else:
                print(ColorFormat(Colors.Green, "Return code = "+str(Result.returncode)))
                successes = successes + 1

        except Exception as ex:
            print("Error in running the executable\nException caught: "+str(ex))
            traceback.print_exc()

    print("\n")

    if len(error_names) == 0:
        print(ColorFormat(Colors.Green, "No errors on "+str(successes)+" tests!"))
    else:
        print(ColorFormat(Colors.Red, ("="*40)+"\n          Some errors reported\n"+("="*40)))
        print(ColorFormat(Colors.Green, "successes: ["+str(successes)+"]"))
        print(ColorFormat(Colors.Red, "Errors: ["+str(len(error_names))+"]\n"+"\n".join(error_names)))
