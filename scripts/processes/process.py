import os
import pty
import traceback
import threading
import subprocess

from time import sleep
from threading import Thread, Lock
from data.settings import Settings
from data.colors import ColorFormat, Colors
from processes.progress_bar import PrintProgressBar
from data.common import Abort, AppendToEnvVariable, RemoveControlCharacters, RemoveAnsiEscapeCharacters
from data.common import ErrorCheckLogs, SlimError, GetNow

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
        print(thread_log,end="")
        thread_log = ""

def PrintProgressWhileWaitOnThreads(threads, print_function=None, print_arguments=None):
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
    while threads_alive != progress:
        threads_alive = len(threads)
        for thread in threads:
            if thread.is_alive():
                continue
            threads_alive -= 1
        if prev_alive != threads_alive:
            PrintProgress()

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
def RunInThreadsWithProgress(run_callback, run_args, print_callback=None, print_args=None):
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
            PrintProgressWhileWaitOnThreads(threads, print_callback, print_args)
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

        Result = callback(**arguments)

        operation_lock.acquire()
        operation_status[path] = Result
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

    RunInThreadsWithProgress(__RunOnFoldersThreadWrapper, run_args, __PrintRunOnFoldersProgress, {"paths":paths})
    os.chdir(current_dir)

    return operation_status

def RunExecutable(CommandString):
    return subprocess.run(CommandString, shell=True)

class ProcessError(Exception):
    def __init__(self, Message, Returned):
        # Call the base class constructor with the parameters it needs
        super().__init__(f"Message:{Message}\nReturned: {Returned}")
        self.Returned = Returned
    def RaiseIfNotInOutput(self, Data):
        if Data in self.Returned["stdout"] or Data in self.Returned["stderr"]:
            return
        raise self

"""
Changes to the given directory, launches the Command in a forked process and
returns the { "stdout": "..." , "code": "..."  } dictionary
"""
def LaunchProcess(Command, path=None, to_print=False):
    """
    Launch new process

    to_print: whether to print the output (process thinks it is in a TY)

    Returns:
        _type_: {"stdout":"<stdout>", "code": return code}
    """

    if path != None:
        Command = f"cd {path}; {Command}"

    Returned = {"stdout": "", "stderr": "", "code": ""}

    if Command == "":
        return {"stdout": "", "stderr": "", "code": ""}

    if to_print == True:
        print(ColorFormat(Colors.Blue, Command))
        OutputBytes = []
        def read(fd):
            Data = os.read(fd, 1024)
            OutputBytes.append(Data)
            return Data

        # Remove all types of whitespace repetitions `echo  \t  a` -> `echo a`
        Command = " ".join(Command.split())

        Returned["code"] = int(pty.spawn(['bash', '-c', Command], read))

        if to_print == True:
            print(ColorFormat(Colors.Blue, "Returned " + str(Returned["code"])))

        if len(OutputBytes) != 0:
            OutputBytes = b''.join(OutputBytes)
            OutputUTF8 = OutputBytes.decode('utf-8')
            NoEscapeUTF8 = RemoveAnsiEscapeCharacters(OutputUTF8)
            CleanUTF8 = RemoveControlCharacters(NoEscapeUTF8)

            Returned["stdout"] = CleanUTF8
        else:
            Returned["stdout"] = ""
    else:
        Result = subprocess.run(['bash', '-c', Command],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        Returned["command"] = Command
        Returned["stdout"]  = Result.stdout.decode('utf-8')
        Returned["stderr"]  = Result.stderr.decode('utf-8')
        Returned["code"]    = int(Result.returncode)

    if Returned["code"] != 0:
        Message  = f"\n\t========================= Process failed (start) ({GetNow()}) =========================\n"
        Message += "\t\tProcess returned failure (" + ColorFormat(Colors.Yellow, str(Returned["code"])) + "):\n"
        if path != None:
            Message += ColorFormat(Colors.Yellow, f"at {path}\n")
        else:
            Message += ColorFormat(Colors.Yellow, f"at {os.getcwd()}\n")
        Message += ColorFormat(Colors.Cyan,   f"{Command}\n")
        Message += ColorFormat(Colors.Blue,   f"stdout: {Returned["stdout"]}\n")
        Message += ColorFormat(Colors.Red,    f"stderr: {Returned["stderr"]}\n")
        Message += "Current stack:\n"

        trace = traceback.format_stack()[:-1]
        for Line in trace:
            Pieces = Line.strip().split("\n")
            if len(Pieces) == 2:
                file, callback = Pieces
                function  = file.split(" in ")[-1]
                # Line NUMBER, .. # Get NUMBER, .. # Remove .. # Remove ,
                file_Line = file.lower().split(" line ")[-1].split(" ")[0][:-1]
                Message += function + "() Line " + str(file_Line) + "\n" +ColorFormat(Colors.Green, callback) + "\n"
            else:
                Message += Line
        Message += "\n\t========================= Process failed (end) =========================\n"
        raise ProcessError(Message, Returned)

    return Returned

def ParseProcessResponse(Response):
    return RemoveControlCharacters(Response["stdout"].rstrip())

def OpenBashOnDirectoryAndWait(working_directory):
    print("Opening new slave terminal")
    print("Close when finished (hit Ctrl+D or type exit)")
    # Open a new Bash shell in the specified working directory
    Process = subprocess.Popen(['bash'], cwd=working_directory)

    # Wait for the Bash shell to be closed by the user
    Process.wait()

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

def PrepareExecEnvironment():
    AppendToEnvVariable("PYTHONPATH",       Settings["paths"]["scripts"])
    AppendToEnvVariable("PB_ROOT_NAME",     Settings["name"])
    AppendToEnvVariable("PB_ROOT_URL",      Settings["url"])
