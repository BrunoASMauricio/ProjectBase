import os
import sys
import pty
import traceback
import threading
from time import time
import subprocess

from time import sleep
from threading import Thread, Lock
from data.settings import Settings, ErrorCheckLogs
from data.colors import ColorFormat, Colors
from processes.progress_bar import PrintProgressBar
from data.common import *
from data.print import *
from processes.filesystem import WriteFile

#                           PROCESS OPERATIONS

def PrintProgressWhileWaitOnThreads(thread_data, max_delay=None, print_function=None, print_arguments=None):
    threads, callback, args = thread_data
    if print_arguments is None:
        print_arguments = {}

    def PrintProgress():
        if print_function is not None:
            print_function(**print_arguments)
        else:
            progress = len(threads) - threads_alive
            PrintProgressBar(progress, len(threads), prefix = 'Running:', suffix = 'Threads finished ' + str(progress) + '/' + str(len(threads)))

    # Wait for all threads
    threads_alive = len(threads)
    progress = 0
    prev_alive = threads_alive
    initial_timestamp = time()
    timeout_count = 0
    auto_policy = None
    policy_initial_count = 0

    while threads_alive != progress:
        threads_alive = len(threads)
        for thread in threads:
            if thread.is_alive():
                continue
            threads_alive -= 1
        if prev_alive != threads_alive:
            PrintProgress()
            prev_alive = threads_alive

        if max_delay is not None and time() - initial_timestamp > max_delay:
            timeout_count += 1

            alive_descriptions = []
            for thread_ind in range(len(threads)):
                if threads[thread_ind].is_alive():
                    alive_descriptions.append(str(args[thread_ind]))

            # Check if an auto-policy is active
            if auto_policy is not None:
                policy_secs, policy_max, policy_action = auto_policy
                if timeout_count >= policy_initial_count + policy_max:
                    # Policy exhausted, execute the final action
                    action_name = _ACTION_NAMES.get(policy_action, "unknown")
                    print(f"\n[Auto-policy] Exhausted — executing '{action_name}'.")
                    for desc in alive_descriptions:
                        print(f"  - {desc}")
                    if policy_action == TIMEOUT_STOP_ALL:
                        auto_policy = None
                        _kill_all_active_processes()
                        sleep(0.5)
                        break
                    elif policy_action == TIMEOUT_INDEFINITELY:
                        auto_policy = None
                        max_delay = None
                    # TIMEOUT_STOP_CURRENT not applicable in multi-thread
                else:
                    _print_auto_policy_timeout(timeout_count, policy_max, policy_initial_count, policy_secs, policy_action, alive_descriptions)
                    max_delay = policy_secs
                    initial_timestamp = time()
                continue

            choice = _prompt_timeout_action(alive_descriptions, timeout_count)
            if choice == TIMEOUT_INDEFINITELY:
                max_delay = None
            elif choice == TIMEOUT_STOP_ALL:
                _kill_all_active_processes()
                sleep(0.5)
                break
            elif isinstance(choice, tuple):
                policy_secs, policy_max, policy_action = choice
                auto_policy = choice
                policy_initial_count = timeout_count
                max_delay = policy_secs
                initial_timestamp = time()
            else:
                max_delay = choice
                initial_timestamp = time()

        # Keep flushing log
        FlushthreadLog()
        sleep(0.05)

    PrintProgress()

operation_status = {}
operation_lock = Lock()

def __PrintRunOnFoldersProgress(paths):
    current_progress = len(operation_status)
    total_repos      = len(paths)
    if total_repos == current_progress:
        PrintProgressBar(current_progress, total_repos, prefix = 'Running:', suffix = 'Ran on ('+str(current_progress)+') folders')
    else:
        PrintProgressBar(current_progress, total_repos, prefix = 'Running:', suffix = "Done on " + str(current_progress) + "/" + str(total_repos) + " folders")

thread_return = {}

# Registry of active subprocess.Popen objects, keyed by thread ID.
# Allows the main thread to kill subprocesses running in worker threads.
active_processes = {}
active_processes_lock = Lock()
killed_threads = set()

def _register_process(proc):
    with active_processes_lock:
        active_processes[threading.get_ident()] = proc

def _unregister_process():
    with active_processes_lock:
        active_processes.pop(threading.get_ident(), None)

def was_killed():
    """Check if the current thread's process was killed by a timeout."""
    return threading.get_ident() in killed_threads

def _kill_all_active_processes():
    with active_processes_lock:
        for tid, proc in active_processes.items():
            killed_threads.add(tid)
            try:
                # Kill the entire process group (includes child processes)
                os.killpg(proc.pid, 9)
            except OSError:
                pass

# Timeout action constants
TIMEOUT_STOP_ALL     = 0
TIMEOUT_INDEFINITELY = -1
TIMEOUT_STOP_CURRENT = -2

_ACTION_NAMES = {
    TIMEOUT_STOP_ALL: "stop all",
    TIMEOUT_INDEFINITELY: "wait indefinitely",
    TIMEOUT_STOP_CURRENT: "stop current",
}

def _print_auto_policy_timeout(timeout_count, policy_max, policy_initial_count, policy_secs, policy_action, alive_descriptions):
    remaining = policy_initial_count + policy_max - timeout_count
    action_name = _ACTION_NAMES.get(policy_action, "unknown")
    print(f"\n[Auto-policy] Timeout {timeout_count} — {remaining} remaining before '{action_name}'. Waiting {policy_secs}s.")
    for desc in alive_descriptions:
        print(f"  - {desc}")

def _parse_timeout_choice(choice, single_thread=False):
    """
    Parse a timeout prompt answer.
    Returns: seconds (int >0), TIMEOUT_INDEFINITELY, TIMEOUT_STOP_ALL,
             TIMEOUT_STOP_CURRENT, a (seconds, max_count, action) tuple, or None (invalid).
    """
    parts = choice.split()
    if len(parts) == 1:
        if parts[0] == "0":
            return 30
        if parts[0] == "1":
            return TIMEOUT_INDEFINITELY
        if parts[0] == "2":
            return TIMEOUT_STOP_ALL
        if parts[0] == "4" and single_thread:
            return TIMEOUT_STOP_CURRENT
    if len(parts) == 2 and parts[0] == "3":
        if StringIsNumber(parts[1]) and int(parts[1]) > 0:
            return int(parts[1])
    # Option 5: "5 <seconds> <max_count> <action>"
    # e.g. "5 30 3 stop_current" → wait 30s, up to 3 times, then stop current
    if len(parts) == 4 and parts[0] == "5":
        if StringIsNumber(parts[1]) and StringIsNumber(parts[2]):
            secs = int(parts[1])
            count = int(parts[2])
            action_map = {
                "stop_current": TIMEOUT_STOP_CURRENT,
                "stop_all":     TIMEOUT_STOP_ALL,
                "wait":         TIMEOUT_INDEFINITELY,
            }
            if secs > 0 and count > 0 and parts[3] in action_map:
                return (secs, count, action_map[parts[3]])
    return None  # invalid

def _prompt_timeout_action(alive_descriptions, timeout_count=0, single_thread=False):
    """
    Prompt user for what to do about stuck tests/tasks.
    Returns: seconds (>0), TIMEOUT_INDEFINITELY, TIMEOUT_STOP_ALL,
             TIMEOUT_STOP_CURRENT, or a (seconds, max_count, action) policy tuple.
    """
    # Non-interactive mode: auto-stop
    if Settings.get("exit", False) and len(Settings.get("action", [])) == 0:
        print("  (non-interactive mode: auto-stopping)")
        return TIMEOUT_STOP_ALL

    print(f"\nThe following tests are still running (timed out {timeout_count} time{'s' if timeout_count != 1 else ''}):")
    for desc in alive_descriptions:
        print(f"  - {desc}")
    print("Please choose:")
    print("  0 - Wait for 30 seconds")
    print("  1 - Wait indefinitely")
    print("  2 - Stop them all")
    print("  3 <N> - Wait for N more seconds (e.g. 3 300)")
    if single_thread:
        print("  4 - Stop current test (continue with next)")
    action_names = "stop_current/stop_all/wait"
    print(f"  5 <secs> <max_count> <action> - Auto-apply (e.g. 5 30 3 stop_current)")
    print(f"      actions: {action_names}")

    # Check automated-input queue
    if len(Settings.get("action", [])) > 0:
        answer = Settings["action"][0]
        del Settings["action"][0]
        print(f"  [< Auto timeout choice <] {{{answer}}}")
        return _parse_timeout_choice(answer, single_thread)

    while True:
        try:
            choice = input("> ").strip()
            result = _parse_timeout_choice(choice, single_thread)
            if result is not None:
                return result
            print("Invalid choice")
        except (EOFError, KeyboardInterrupt):
            return TIMEOUT_STOP_ALL

# Wrapper for threads
def ThreadWrapper(run_callback, run_arg):
    global thread_return
    try:
        run_callback(*run_arg)
        return_val = True
    except KeyboardInterrupt as ex:
        PrintNotice("Keyboard Interrupt, stopping")
        raise ex
    except ProcessError as ex:
        return_val = False
        # ProcessError happened return error code on Settings
        AddTothreadLog(str(ex))
        print(str(ex.simple_message))
    except Exception as ex:
        # Store exception in log, but don't print it just yet
        # Ctrl+C will create exceptions on all threads, so those logs must be cleared and not printed
        AddTothreadLog(f"{ex}\n{"="*30}\nStack trace:\n\n{traceback.format_exc()}{"="*30}\n")
        return_val = False
    thread_return[GetThreadId()] = return_val

"""
Run run_callback in a separate thread for each argument in run_args (which is also passed to that thread)
"""
def RunInThreads(run_callback, run_args):
    threads = []
    for run_arg in run_args:
        thread = Thread(target=ThreadWrapper, args=[run_callback,run_arg], daemon=True)
        threads.append(thread)
        thread.start()
    return threads

"""
Run run_callback with each argument in run_args, in separate threads or
sequentially if "single thread" mode is on
If print_callback is present, it will be called to register the operation progress
"""
def RunInThreadsWithProgress(run_callback, run_args, max_delay=None, print_callback=None, print_args=None):
    global thread_return

    thread_return.clear()
    killed_threads.clear()
    if len(run_args) == 0:
        return

    PrintProgressBar(0, len(run_args), prefix = 'Starting...', suffix = '0/' + str(len(run_args)))
    ClearThreadLog()
    ToggleThreading(True)

    try:
        if Settings["single thread"]:
            stop_all = False
            auto_policy = None
            policy_initial_count = 0
            for run_arg_ind, run_arg in enumerate(run_args):
                if stop_all:
                    thread_return[run_arg_ind] = False
                    continue

                # Clear killed state from previous test
                killed_threads.clear()

                # Run in a temporary thread so we can apply timeout
                worker = Thread(target=ThreadWrapper, args=[run_callback, run_arg], daemon=True)
                worker.start()

                start_time = time()
                current_delay = auto_policy[0] if auto_policy else max_delay
                timeout_count = 0
                policy_initial_count = 0
                while worker.is_alive():
                    if current_delay is not None and time() - start_time > current_delay:
                        timeout_count += 1

                        # Check if an auto-policy is active
                        alive_desc = [str(run_arg)]
                        if auto_policy is not None:
                            policy_secs, policy_max, policy_action = auto_policy
                            if timeout_count >= policy_initial_count + policy_max:
                                # Policy exhausted, execute the final action
                                action_name = _ACTION_NAMES.get(policy_action, "unknown")
                                print(f"\n[Auto-policy] Exhausted — executing '{action_name}'.")
                                for desc in alive_desc:
                                    print(f"  - {desc}")
                                if policy_action == TIMEOUT_STOP_ALL:
                                    auto_policy = None
                                    _kill_all_active_processes()
                                    stop_all = True
                                    sleep(0.5)
                                    break
                                elif policy_action == TIMEOUT_STOP_CURRENT:
                                    # Keep auto_policy for next test
                                    _kill_all_active_processes()
                                    sleep(0.5)
                                    break
                                elif policy_action == TIMEOUT_INDEFINITELY:
                                    auto_policy = None
                                    current_delay = None
                            else:
                                _print_auto_policy_timeout(timeout_count, policy_max, policy_initial_count, policy_secs, policy_action, alive_desc)
                                current_delay = policy_secs
                                start_time = time()
                            continue

                        choice = _prompt_timeout_action([str(run_arg)], timeout_count, single_thread=True)
                        if choice == TIMEOUT_INDEFINITELY:
                            current_delay = None
                        elif choice == TIMEOUT_STOP_ALL:
                            _kill_all_active_processes()
                            stop_all = True
                            sleep(0.5)
                            break
                        elif choice == TIMEOUT_STOP_CURRENT:
                            _kill_all_active_processes()
                            sleep(0.5)
                            break
                        elif isinstance(choice, tuple):
                            policy_secs, policy_max, policy_action = choice
                            auto_policy = choice
                            policy_initial_count = timeout_count
                            current_delay = policy_secs
                            start_time = time()
                        else:
                            current_delay = choice
                            start_time = time()
                    sleep(0.05)

                if print_callback is not None:
                    if print_args is not None:
                        print_callback(print_args)
                    else:
                        print_callback()
                else:
                    PrintProgressBar(run_arg_ind + 1, len(run_args), prefix = 'Running:', suffix = 'Work finished ' + str(run_arg_ind + 1) + '/' + str(len(run_args)))
                thread_return[run_arg_ind] = thread_return.get(worker.ident, True)
        else:
            threads = RunInThreads(run_callback, run_args)
            PrintProgressWhileWaitOnThreads((threads, run_callback, run_args), max_delay, print_callback, print_args)
    except Exception as ex:
        AddTothreadLog(str(ex))
        thread_return[run_arg_ind] = False
        raise
    except KeyboardInterrupt:
        PrintNotice("Keyboard Interrupt, stopping")
    finally:
        _kill_all_active_processes()
        FlushthreadLog()
        ToggleThreading(False)

    for val in thread_return.values():
        if val is False:
            raise SlimError(f"One of the threads errored out with {val}")

def __RunOnFoldersThreadWrapper(callback, path, arguments = None):
    global operation_lock
    global operation_status

    try:
        if arguments is None:
            raise Exception("Arguments must not be None")

        # Different arguments per call?
        if type(arguments) == type([]):
            separate_arguments = arguments[0]
            assert path == separate_arguments["path"]
            del arguments[0]
            arguments = separate_arguments
        elif type(arguments) != dict:
            arguments = [arguments]
            raise Exception(f"Invalid arguments type of {type(arguments)}, must be dictionary")

        arguments["path"] = path

        result = callback(**arguments)

        operation_lock.acquire()
        operation_status[path] = result
        operation_lock.release()
    except ProcessError as exception:
        operation_lock.acquire()
        operation_status[path] = exception
        operation_lock.release()
    except Exception as exception:
        ErrorCheckLogs(exception)

"""
For each path, change directory to it, execute the provided function with the
provided arguments, concatenate result into list and return said list
"""
def RunOnFolders(paths, callback, arguments={}):
    global operation_status

    if len(paths) == 0:
        return {}

    operation_status.clear()
    current_dir = os.getcwd()
    run_args = []

    for path in paths:
        if not os.path.isdir(path):
            raise Exception(path+" is not a valid directory, cannot perform "+str(callback)+"("+str(arguments)+")")
        run_args.append((callback, path, arguments,))

    RunInThreadsWithProgress(__RunOnFoldersThreadWrapper, run_args, 20, __PrintRunOnFoldersProgress, {"paths":paths})
    os.chdir(current_dir)

    return operation_status

class ProcessError(Exception):
    def __init__(self, simple_message, trace_message, returned):
        # Call the base class constructor with the parameters it needs
        message  = f"\n\t========================= Process failed (start) ({GetNow()}) ({threading.get_ident()}) =========================\n"
        message += f"{simple_message}\nTrace:\n{trace_message}"
        message += "\n\t========================= Process failed (end) =========================\n"

        returned_str = "\n".join(f"  {k}: {v}" for k, v in returned.items())
        self.message = f"Message:{message}\nReturned:\n{returned_str}"
        super().__init__(self.message)
        self.returned = returned
        self.simple_message = simple_message

    def __str__(self):
        return self.message

    def __repr__(self):
        return self.message

    def RaiseIfNotInOutput(self, data):
        if data in self.returned["stdout"] or data in self.returned["stderr"]:
            return
        raise self

def GetEnvVars():
    env = {}
    # Settings["paths"] may not be initialized (e.g. in standalone test processes)
    if "paths" in Settings:
        env["PYTHONPATH"] = Settings["paths"]["scripts"]
        env["BIN_PATH"]  = Settings["paths"]["binaries"]
    if "name" in Settings:
        env["PB_ROOT_NAME"] = Settings["name"]
    # The ':' in `Settings["url"]` is creating serious issues. Commenting for now
    # "PB_ROOT_URL":      Settings["url"],
    return env

# Setup necessary/useful environment variables
def SetupLocalEnvVars():
    # PYTHONPATH enables a script to import modules
    for var, val in GetEnvVars().items():
        AppendToEnvVariable(var, val)

def GetEnvVarExports():
    return "; ".join(f"export {var}='{val}'" for var, val in GetEnvVars().items())

def _LaunchCommand(command, path=None, interactive=False):
    if path is None:
        path = os.getcwd()
    else:
        if not os.path.isdir(path):
            raise Exception(f"No such path ({path}) for executing command ({command}) ")

    returned = {
        "stdout": "",
        "stderr": "",
        # TODO: Replace stdout/stderr with plain out. There are too many programs that send errors to stderr
        "out": "",
        "code": -1,
        "path": path,
        "command": command
    }

    if command == "":
        return returned

    command = f"cd '{path}'; {command}"

    if interactive is True:
        print(ColorFormat(Colors.Blue, command))
        output_bytes = []
        def read(fd):
            data = os.read(fd, 1024)
            output_bytes.append(data)
            # If stdout changed, the spawned process will not have the same stdout
            # Need to explicitly print the data into the scripts stdout
            if sys.stdout != sys.__stdout__:
                print(data.decode('utf-8'), end='')
            return data

        # Remove all types of whitespace repetitions `echo  \t  a` -> `echo a`
        command = " ".join(command.split())

        returned["code"] = int(pty.spawn(['bash', '-c', command], read))

        print(ColorFormat(Colors.Blue, "Returned " + str(returned["code"])))

        if len(output_bytes) != 0:
            output_bytes = b''.join(output_bytes)
            output_utf8 = output_bytes.decode('utf-8')
            no_escape_utf8 = RemoveAnsiEscapeCharacters(output_utf8)
            clean_utf8 = RemoveControlCharacters(no_escape_utf8)

            returned["stdout"] = output_utf8
            returned["out"] = clean_utf8
        else:
            returned["stdout"] = ""
    else:
        proc = subprocess.Popen(['bash', '-c', command],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                start_new_session=True)
        _register_process(proc)
        try:
            stdout_bytes, stderr_bytes = proc.communicate()
        finally:
            _unregister_process()

        returned["command"] = command
        returned["stdout"]  = stdout_bytes.decode('utf-8', errors='replace').rstrip()
        returned["stderr"]  = stderr_bytes.decode('utf-8', errors='replace').rstrip()
        returned["code"]    = int(proc.returncode)

        returned["out"] = f"{returned["stdout"]}{returned["stderr"]}"
        returned["out"] = RemoveNonAscii(RemoveControlCharacters(returned["out"]))
    return returned

"""
Changes to the given directory, launches the Command in a forked process and
returns the { "stdout": "..." , "code": "..."  } dictionary
"""
def LaunchProcess(command, path=None, interactive=False):
    """
    Launch new process

    interactive: whether to have an interactive TTY session or just run as a process and return output

    Returns:
        _type_: {"stdout":"<stdout>", "code": return code}
    """

    # Setup relevant environment variables
    command = f"{GetEnvVarExports()}; {command}"
    # Fail on first error
    command = f"set -e; {command}"
    # Allow python scripts to use ProjectBase scripts
    SetupLocalEnvVars()

    returned = _LaunchCommand(command, path, interactive)

    if returned["code"] != 0:
        simple_message = "\t\tProcess returned failure (" + ColorFormat(Colors.Yellow, str(returned["code"])) + "):\n"
        simple_message += ColorFormat(Colors.Yellow, f"at {path}\n")
        simple_message += ColorFormat(Colors.Cyan,   f"{command}\n")
        simple_message += ColorFormat(Colors.Blue,   f"stdout: {returned["stdout"]}\n")
        simple_message += ColorFormat(Colors.Red,    f"stderr: {returned["stderr"]}\n")
        simple_message += "Current stack:\n"

        trace_message = ""
        trace = traceback.format_stack()[:-1]
        for Line in trace:
            Pieces = Line.strip().split("\n")
            if len(Pieces) == 2:
                file, callback = Pieces
                function  = file.split(" in ")[-1]
                # Line NUMBER, .. # Get NUMBER, .. # Remove .. # Remove ,
                file_Line = file.lower().split(" line ")[-1].split(" ")[0][:-1]
                trace_message += function + "() Line " + str(file_Line) + "\n" +ColorFormat(Colors.Green, callback) + "\n"
            else:
                trace_message += Line
        raise ProcessError(simple_message, trace_message, returned)

    return returned

def OpenBashOnDirectoryAndWait(working_directory):
    print("Opening new slave terminal")
    print("Close when finished (hit Ctrl+D or type exit)")
    # Open a new Bash shell in the specified working directory
    process = subprocess.Popen(['bash'], cwd=working_directory)

    # Wait for the Bash shell to be closed by the user
    process.wait()

#                           PROCESS OUTPUT

def LaunchSilentProcess(command, path=None):
    return LaunchProcess(command, path, False)

def LaunchVerboseProcess(command, path=None):
    return LaunchProcess(command, path, True)


def AssertProcessRun(Process, ExpectedCode, ExpectedOutput):
    Result = LaunchSilentProcess(Process)
    if Result["code"] != ExpectedCode:
        Message  = "Wrong code for process"
        Message += "\n\tExpected " + str(ExpectedCode)
        Message += "\n\tGot " + str(Result["code"])
        Abort(Message)

    if Result["stdout"] != ExpectedOutput:
        TextDiff = GetTextDiff(ExpectedOutput, Result["stdout"])
        Message  = "Wrong output for process"
        Message += ''.join(TextDiff)
        Message += "\t\nExpected (" + str(len(Result["stdout"])) + " characters)"
        Message += "="*30 + "\n>"+Result["stdout"]+"<"
        Message += "\t\nGot (" + str(len(ExpectedOutput)) + " characters)"
        Message += "="*30 + "\n>"+ExpectedOutput+"<"
        Abort(Message)

def LaunchPager(data, path=None):
    file = "/tmp/PB.pager.data"
    WriteFile(file, data)
    LaunchProcess(f"less -f < {file}", path, True)
