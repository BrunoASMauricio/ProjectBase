from data.settings import settings
from data.common import StringIsNumber
from processes.process import RunExecutable

def execute(executable):
    # Allow python scripts to use ProjectBase scripts
    # PrepareExecEnvironment(Project)
    # AppendToEnvVariable("PYTHONPATH", Project.Paths["scripts"])
    pass

"""
scan path_to_scan for appropriate executables
Return a list with the executables
"""
def __get_available_executables(path_to_scan):
    executables_available = []
    os.chdir(settings["paths"]["project_main"])
    print("Executables available in "+path_to_scan+":")

    index = 0
    for entry in os.scandir(path_to_scan):
        # Must be fully executable
        if entry.stat().st_mode & 0o111 != 0o111:
            continue
        # Must be a file
        if not entry.is_file():
            continue

        print("\t["+str(index)+"] "+ColorFormat(Colors.Blue, entry.name))
        executables_available.append(entry.name)
        index += 1
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
def __locate_executable(user_input, executables_available):
    input_list = user_input.split(' ')
    executable = input_list[0]
    if StringIsNumber(executable):
        exec_ind = int(executable)
        if exec_ind > len(executables_available):
            print("Out of bounds index: " + og_user_input)
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

def run(path_to_scan):
    executables_available = __get_available_executables()
    if len(executables_available) == 0:
        print("No executables found")
        return
    
    print("!V for valgrind. !G for GDB. !S for GDB server @ 127.0.0.1:6175")
    print("Upper case (V,G,S) uses default parameters, lower case doesn't.")
    print("[![G|V|S]]<INDEX [0-9]+> [Space separated argument list]")

    while True:
        try:
            og_user_input = GetNextOption()
            # No input (Enter pressed)
            if len(og_user_input) == 0:
                print("Incorrect input '" + user_input + "'")
                continue

            # Check extra program prefix
            prefix, user_input = __parse_input(og_user_input)

            # Locate executable
            path_to_exec, input_list = __locate_executable(user_input, executables_available)
            if path_to_exec == None:
                continue

            # Assemble command and run
            arguments = ' '.join([x for x in input_list[1:] if x != ""])
            full_command = executable + " " + arguments
            if prefix != "":
                full_command = prefix + " " + full_command
            print("Running: \"" + full_command + "\"")

            try:
                Result = RunExecutable(full_command)
                if Result.returncode != 0:
                    print(ColorFormat(Colors.Red, '"' + full_command + '" returned code = '+str(Result.returncode)))
                else:
                    print(ColorFormat(Colors.Green, '"' + full_command + '" returned code = '+str(Result.returncode)))
            except KeyboardInterrupt:
                print("Keyboard Interrupt")

        except KeyboardInterrupt:
            print("\nCtrl+C exits running operations. Press Ctrl+D to back out of ProjectBase")
            continue
        except EOFError:
            break

def run_single_test():
    run_single(settings["paths"]["tests"])

def run_single_executable():
    run_single(settings["paths"]["executables"])

def run_all_tests():
    pass
