import os
import pty
import logging
import traceback
import threading
from time import time
import subprocess

from time import sleep
from threading import Thread, Lock
from data.settings import Settings
from data.colors import ColorFormat, Colors
from processes.progress_bar import PrintProgressBar
from data.common import Abort, AppendToEnvVariable, RemoveControlCharacters, RemoveAnsiEscapeCharacters
from data.common import ErrorCheckLogs, SlimError, GetNow, RemoveNonAscii

#                           PROCESS OPERATIONS

import threading
thread_log = ""
thread_log_lock = threading.Lock()

def GetThreadId():
    return threading.get_ident()

def AddTothreadLog(message):
    global thread_log
    global thread_log_lock

    with thread_log_lock:
        thread_log += f"({GetThreadId()}) {message}\n"

def ClearThreadLog():
    global thread_log
    global thread_log_lock
    with thread_log_lock:
        thread_log = ""

def Flushthread_log():
    global thread_log
    global thread_log_lock
    with thread_log_lock:
        if len(thread_log) > 0:
            print(thread_log,end="")
            logging.info(thread_log)
        thread_log = ""

def PrintProgressWhileWaitOnThreads(thread_data, max_delay=None, print_function=None, print_arguments=None):
    threads, callback, args = thread_data
    if print_arguments == None:
        print_arguments = {}

    def PrintProgress():
        if print_function != None:
            print_function(**print_arguments)
        else:
            progress = len(threads) - threads_alive
            PrintProgressBar(progress, len(threads), prefix = 'Running:', suffix = 'Threads finished ' + str(progress) + '/' + str(len(threads)))

    # Wait for all threads
    threads_alive = len(threads)
    progress = 0
    prev_alive = threads_alive
    initial_timestamp = time()

    while threads_alive != progress:
        threads_alive = len(threads)
        for thread in threads:
            if thread.is_alive():
                continue
            threads_alive -= 1
        if prev_alive != threads_alive:
            PrintProgress()
            prev_alive = threads_alive

        if max_delay != None and time() - initial_timestamp > max_delay:
            initial_timestamp = time()
            print(f"\n{threads_alive - progress} threads are taking more time than expected ({max_delay}s). Currently running threads:")
            for thread_ind in range(len(threads)):
                thread = threads[thread_ind]
                if not thread.is_alive():
                    continue

                print(f"Thread alive for {callback} with arguments: {args[thread_ind]}")
            # Ask user if we should kill, reset timer, or ignore

        # Keep flushing log
        Flushthread_log()
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

# Wrapper for threads
def ThreadWrapper(run_callback, run_arg):
    global thread_return
    try:
        run_callback(*run_arg)
        return_val = True
    except KeyboardInterrupt as ex:
        print("Keyboard Interrupt, stopping")
        raise ex
    except ProcessError as ex:
        return_val = False
        AddTothreadLog(str(ex))

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
        thread = Thread(target=ThreadWrapper, args=[run_callback,run_arg])
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
    if len(run_args) == 0:
        return

    PrintProgressBar(0, len(run_args), prefix = 'Starting...', suffix = '0/' + str(len(run_args)))
    ClearThreadLog()
    if Settings["single thread"]:
        for run_arg_ind in run_args:
            run_arg = run_args[run_arg_ind]
            try:
                run_callback(*run_arg)
                if print_callback != None:
                    if print_args != None:
                        print_callback(print_args)
                    else:
                        print_callback()
                else:
                    PrintProgressBar(run_arg_ind, len(run_args), prefix = 'Running:', suffix = 'Work finished ' + str(run_arg_ind) + '/' + str(len(run_args)))
                thread_return[run_arg_ind] = True
            except KeyboardInterrupt:
                print("Keyboard Interrupt, stopping")
                ClearThreadLog()
                return
            except Exception as ex:
                AddTothreadLog(str(ex))
                thread_return[run_arg_ind] = False
    else:
        try:
            threads = RunInThreads(run_callback, run_args)
            PrintProgressWhileWaitOnThreads((threads, run_callback, run_args), max_delay, print_callback, print_args)
        except KeyboardInterrupt:
            print("Keyboard Interrupt, stopping threads")
            for thread in threads:
                if thread.is_alive():
                    # thread.raise_exception()
                    thread._stop()
            ClearThreadLog()

    Flushthread_log()

    for val in thread_return.values():
        if val == False:
            raise SlimError("One of the threads errored out")

def __RunOnFoldersThreadWrapper(callback, path, arguments = None):
    global operation_lock
    global operation_status

    try:
        if arguments == None:
            raise Exception("Arguments must not be None")

        # Different arguments per call?
        if type(arguments) == type([]):
            separate_arguments = arguments[0]
            assert path == separate_arguments["path"]
            del arguments[0]
            arguments = separate_arguments
            print(arguments)

        arguments["path"] = path

        result = callback(**arguments)

        operation_lock.acquire()
        operation_status[path] = result
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

def RunExecutable(command_string):
    return subprocess.run(command_string, shell=True)

class ProcessError(Exception):
    def __init__(self, message, returned):
        # Call the base class constructor with the parameters it needs
        super().__init__(f"Message:{message}\nReturned: {returned}")
        self.returned = returned
    def RaiseIfNotInOutput(self, data):
        if data in self.returned["stdout"] or data in self.returned["stderr"]:
            return
        raise self

def GetEnvVars():
    return {
        "PYTHONPATH":       Settings["paths"]["scripts"],
        "PB_ROOT_NAME":     Settings["name"],
        "PB_ROOT_URL":      Settings["url"],
    }

# Setup necessary/useful environment variables
def SetupLocalEnvVars():
    # PYTHONPATH enables a script to import modules
    for var, val in GetEnvVars().items():
        AppendToEnvVariable(var, val)

def GetEnvVarExports():
    return "; ".join(f"export {var}='{val}'" for var, val in GetEnvVars().items())

"""
Changes to the given directory, launches the Command in a forked process and
returns the { "stdout": "..." , "code": "..."  } dictionary
"""
def LaunchProcess(command, path=None, to_print=False):
    """
    Launch new process

    to_print: whether to print the output (process thinks it is in a TY)

    Returns:
        _type_: {"stdout":"<stdout>", "code": return code}
    """

    if path == None:
        path = os.getcwd()
    else:
        if not os.path.isdir(path):
            raise Exception(f"No such path ({path}) for executing command ({command}) ")

    returned = {
        "stdout": "",
        "stderr": "",
        "code": "",
        "path": path,
        "command": command
    }

    if command == "":
        return returned

    # Setup relevant environment variables
    # command = f"{GetEnvVarExports()}; {command}"
    # Need to cd for each git, because doing os.chdir changes the cwd for ALL threads
    command = f"cd '{path}'; {command}"
    # Fail on first error
    command = f"set -e; {command}"

    if to_print == True:
        print(ColorFormat(Colors.Blue, command))
        output_bytes = []
        def read(fd):
            Data = os.read(fd, 1024)
            output_bytes.append(Data)
            return Data

        # Remove all types of whitespace repetitions `echo  \t  a` -> `echo a`
        command = " ".join(command.split())

        returned["code"] = int(pty.spawn(['bash', '-c', command], read))

        if to_print == True:
            print(ColorFormat(Colors.Blue, "Returned " + str(returned["code"])))

        if len(output_bytes) != 0:
            output_bytes = b''.join(output_bytes)
            output_utf8 = output_bytes.decode('utf-8')
            no_escape_utf8 = RemoveAnsiEscapeCharacters(output_utf8)
            clean_utf8 = RemoveControlCharacters(no_escape_utf8)

            returned["stdout"] = clean_utf8
        else:
            returned["stdout"] = ""
    else:
        result = subprocess.run(['bash', '-c', command],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        returned["command"] = command
        try:
            returned["stdout"]  = result.stdout.decode('utf-8')
            returned["stderr"]  = result.stderr.decode('utf-8')
        except UnicodeDecodeError as Ex:
            print(f"Decoding error: {Ex}")
            try:
                returned["stdout"]  = RemoveNonAscii(RemoveControlCharacters(result.stdout))
                returned["stderr"]  = RemoveNonAscii(RemoveControlCharacters(result.stderr))
            except Exception as Ex:
                print(f"Exception trying to handle decoding error: {Ex}")
                returned["stdout"] = result.stdout
                returned["stderr"] = result.stderr

        returned["code"]    = int(result.returncode)

    if returned["code"] != 0:
        message  = f"\n\t========================= Process failed (start) ({GetNow()}) =========================\n"
        message += "\t\tProcess returned failure (" + ColorFormat(Colors.Yellow, str(returned["code"])) + "):\n"
        message += ColorFormat(Colors.Yellow, f"at {path}\n")
        message += ColorFormat(Colors.Cyan,   f"{command}\n")
        message += ColorFormat(Colors.Blue,   f"stdout: {returned["stdout"]}\n")
        message += ColorFormat(Colors.Red,    f"stderr: {returned["stderr"]}\n")
        message += "Current stack:\n"

        trace = traceback.format_stack()[:-1]
        for Line in trace:
            Pieces = Line.strip().split("\n")
            if len(Pieces) == 2:
                file, callback = Pieces
                function  = file.split(" in ")[-1]
                # Line NUMBER, .. # Get NUMBER, .. # Remove .. # Remove ,
                file_Line = file.lower().split(" line ")[-1].split(" ")[0][:-1]
                message += function + "() Line " + str(file_Line) + "\n" +ColorFormat(Colors.Green, callback) + "\n"
            else:
                message += Line
        message += "\n\t========================= Process failed (end) =========================\n"
        raise ProcessError(message, returned)

    return returned

def ParseProcessResponse(response):
    return RemoveControlCharacters(response["stdout"].rstrip())

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

